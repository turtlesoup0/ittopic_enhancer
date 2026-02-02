"""LLM-based proposal generator with retry logic and keyword extraction."""
from openai import AsyncOpenAI
from typing import List, Optional, Dict, Set, Tuple
from dataclasses import dataclass
from pathlib import Path
import logging
import json
import yaml
import re
import hashlib

from app.models.validation import ValidationResult, ContentGap, GapType
from app.models.proposal import EnhancementProposal, ProposalPriority
from app.core.config import get_settings
from app.core.errors import LLMError, OpenAIError, DegradedError
from app.core.resilience import with_retry, get_circuit_breaker, with_circuit_breaker
from app.core.logging import get_logger, log_error
from app.core.cache import CacheManager, get_cache_manager

logger = get_logger(__name__)
settings = get_settings()


@dataclass
class KeywordScore:
    """키워드 품질 점수."""
    keyword: str
    domain_relevance: float  # 도메인 관련성 (0-1)
    exam_frequency: float    # 출제 빈도 (0-1)
    originality: float       # 독창성 (0-1)
    total_score: float       # 총점 (0-1)
    category: str            # 도메인 분류


class ProposalGenerator:
    """Generate enhancement proposals using LLM with keyword extraction."""

    def __init__(self):
        """Initialize proposal generator."""
        self.client = None
        self._circuit_breaker = None
        self._domain_terms: Dict[str, dict] = {}
        self._compound_terms: Dict[str, str] = {}
        self._stopwords: Set[str] = set()
        self._cache_manager: Optional[CacheManager] = None

        # Load domain terms and stopwords
        self._load_domain_terms()
        self._load_stopwords()

        if settings.llm_provider == "openai":
            try:
                self.client = AsyncOpenAI(api_key=settings.openai_api_key)
                self._circuit_breaker = get_circuit_breaker(
                    service_name="openai",
                    failure_threshold=5,
                    recovery_timeout=60.0,
                )
                logger.info("openai_client_initialized")
            except Exception as e:
                logger.error("openai_client_init_failed", error=str(e))
                # Don't raise, allow degraded mode
                self._circuit_breaker = get_circuit_breaker("openai")

    async def _initialize_cache(self):
        """캐시 매니저 초기화."""
        if self._cache_manager is None:
            self._cache_manager = await get_cache_manager()

    def _make_llm_cache_key(self, topic_name: str, current_content: str, field_name: str) -> str:
        """
        LLM 키워드 생성용 캐시 키를 생성합니다.

        Args:
            topic_name: 토픽 이름
            current_content: 현재 내용
            field_name: 필드 이름

        Returns:
            캐시 키
        """
        content = f"{topic_name}:{current_content[:200]}:{field_name}"
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
        return f"llm:keywords:{content_hash}"

    def _make_llm_prompt_cache_key(self, topic_name: str, current_content: str, reference_content: str) -> str:
        """
        LLM 내용 생성용 캐시 키를 생성합니다.

        Args:
            topic_name: 토픽 이름
            current_content: 현재 내용
            reference_content: 참조 내용

        Returns:
            캐시 키
        """
        content = f"{topic_name}:{current_content[:200]}:{reference_content[:200]}"
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
        return f"llm:generation:{content_hash}"

    def _load_domain_terms(self) -> None:
        """도메인별 기술 용어 사전 로드."""
        config_path = Path(__file__).parent.parent.parent.parent / "config" / "domain_terms.yaml"
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                
            # Load domain terms
            for domain_name, domain_data in data.items():
                if domain_name == "복합어":
                    # Load compound terms separately
                    for term_info in domain_data.get("terms", []):
                        self._compound_terms[term_info["term"]] = term_info["category"]
                else:
                    # Load regular domain terms
                    self._domain_terms[domain_name] = domain_data
                    
            logger.info(
                "domain_terms_loaded",
                domains=len(self._domain_terms),
                compound_terms=len(self._compound_terms)
            )
        except Exception as e:
            logger.error("domain_terms_load_failed", error=str(e))
            # Use empty dict as fallback
            self._domain_terms = {}
            self._compound_terms = {}

    def _load_stopwords(self) -> None:
        """불용어 목록 로드."""
        stopwords_path = Path(__file__).parent.parent.parent.parent / "config" / "stopwords.yaml"
        try:
            with open(stopwords_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                
            # Collect all stopwords
            for category, words in data.items():
                if isinstance(words, list):
                    self._stopwords.update(words)
                    
            logger.info("stopwords_loaded", count=len(self._stopwords))
        except Exception as e:
            logger.error("stopwords_load_failed", error=str(e))
            # Use empty set as fallback
            self._stopwords = set()

    async def generate_proposals(
        self,
        validation_result: ValidationResult,
    ) -> List[EnhancementProposal]:
        """
        Generate enhancement proposals from validation result.

        Args:
            validation_result: Validation result with gaps

        Returns:
            List of enhancement proposals
        """
        proposals = []
        seen_titles = set()

        for gap in validation_result.gaps:
            # Skip if we already have a proposal for this field
            if gap.field_name in seen_titles:
                continue
            seen_titles.add(gap.field_name)

            # For MISSING_KEYWORDS gap type, generate keywords using LLM
            suggested_content = gap.suggested_value
            if gap.gap_type == GapType.MISSING_KEYWORDS:
                keywords = await self.generate_keywords_with_llm(
                    topic_name=validation_result.topic_id,
                    current_content=gap.current_value,
                    field_name=gap.field_name
                )
                if keywords:
                    suggested_content = ", ".join(keywords)

            proposal = EnhancementProposal(
                id=f"prop-{validation_result.topic_id}-{gap.field_name}",
                topic_id=validation_result.topic_id,
                priority=self._determine_priority(gap),
                title=self._generate_title(gap),
                description=self._generate_description(gap),
                current_content=gap.current_value,
                suggested_content=suggested_content,
                reasoning=gap.reasoning,
                reference_sources=[gap.reference_id] if gap.reference_id else [],
                estimated_effort=self._estimate_effort(gap),
                confidence=gap.confidence,
            )
            proposals.append(proposal)

        # If no gaps, generate improvement suggestions
        if not proposals and validation_result.overall_score < 0.9:
            proposals.append(
                EnhancementProposal(
                    id=f"prop-{validation_result.topic_id}-improve",
                    topic_id=validation_result.topic_id,
                    priority=ProposalPriority.LOW,
                    title="내용 보강 권장",
                    description="전체 내용이 잘 작성되었으나, 추가 개선이 가능합니다.",
                    current_content="현재 내용",
                    suggested_content="추가 예시나 최신 트렌드 내용을 보강하세요.",
                    reasoning="기술사 시험 대비를 위해 더 상세한 내용이 권장됩니다.",
                    reference_sources=[],
                    estimated_effort=15,
                    confidence=0.6,
                )
            )

        return proposals

    def _determine_priority(self, gap: ContentGap) -> ProposalPriority:
        """Determine proposal priority based on gap type."""
        priority_map = {
            GapType.MISSING_FIELD: ProposalPriority.CRITICAL,
            GapType.INCOMPLETE_DEFINITION: ProposalPriority.HIGH,
            GapType.MISSING_KEYWORDS: ProposalPriority.HIGH,
            GapType.OUTDATED_CONTENT: ProposalPriority.MEDIUM,
            GapType.INACCURATE_INFO: ProposalPriority.CRITICAL,
        }
        return priority_map.get(gap.gap_type, ProposalPriority.MEDIUM)

    def _generate_title(self, gap: ContentGap) -> str:
        """Generate proposal title from gap."""
        titles = {
            GapType.MISSING_FIELD: f"{gap.field_name} 필드 누락",
            GapType.INCOMPLETE_DEFINITION: f"{gap.field_name} 내용 보강 필요",
            GapType.MISSING_KEYWORDS: f"{gap.field_name} 추가 필요",
            GapType.OUTDATED_CONTENT: f"{gap.field_name} 최신화 필요",
            GapType.INACCURATE_INFO: f"{gap.field_name} 정확성 검증 필요",
        }
        return titles.get(gap.gap_type, f"{gap.field_name} 개선 제안")

    def _generate_description(self, gap: ContentGap) -> str:
        """Generate proposal description from gap."""
        descriptions = {
            GapType.MISSING_FIELD: f"{gap.field_name} 필드가 비어있거나 불충분합니다. 기술사 시험 필수 내용입니다.",
            GapType.INCOMPLETE_DEFINITION: f"{gap.field_name}의 내용이 기술사 수준에 미달합니다. 더 상세하고 정확한 내용이 필요합니다.",
            GapType.MISSING_KEYWORDS: f"핵심 키워드가 부족합니다. 기술 용어를 추가하세요.",
            GapType.OUTDATED_CONTENT: "최신 기술 동향을 반영하여 내용을 업데이트하세요.",
            GapType.INACCURATE_INFO: "내용의 정확성을 검증하고 수정이 필요합니다.",
        }
        return descriptions.get(gap.gap_type, gap.reasoning)

    def _estimate_effort(self, gap: ContentGap) -> int:
        """Estimate effort in minutes based on gap type."""
        efforts = {
            GapType.MISSING_FIELD: 20,
            GapType.INCOMPLETE_DEFINITION: 30,
            GapType.MISSING_KEYWORDS: 10,
            GapType.OUTDATED_CONTENT: 15,
            GapType.INACCURATE_INFO: 25,
        }
        return efforts.get(gap.gap_type, 15)

    @with_retry(max_attempts=3, wait_min=1.0, wait_max=10.0)
    async def generate_keywords_with_llm(
        self,
        topic_name: str,
        current_content: str,
        field_name: str,
        topic_id: Optional[str] = None,
    ) -> List[str]:
        """
        Generate keywords using LLM with quality scoring.

        Args:
            topic_name: Name of the topic
            current_content: Current topic content
            field_name: Field name for context
            topic_id: Optional topic ID for logging

        Returns:
            List of scored and sorted keywords
        """
        # 캐시 초기화
        await self._initialize_cache()

        # 캐시 확인
        if self._cache_manager and self._cache_manager.enabled:
            try:
                cache_key = self._make_llm_cache_key(topic_name, current_content, field_name)
                cached = await self._cache_manager._in_memory.get(cache_key) if self._cache_manager._in_memory else None
                if cached:
                    import json
                    data = json.loads(cached)
                    logger.debug(f"llm_keyword_cache_hit: {cache_key}")
                    return data.get("keywords", [])
            except Exception as e:
                logger.warning(f"Failed to get cached keywords: {e}")

        if not self.client:
            logger.warning("llm_not_available_keyword_extraction", topic_id=topic_id)
            # Fallback: extract keywords from domain terms
            return self._extract_keywords_from_domain(current_content)

        async def _call_llm():
            try:
                prompt = self._build_keyword_prompt(topic_name, current_content, field_name)

                response = await self.client.chat.completions.create(
                    model=settings.openai_model,
                    messages=[
                        {
                            "role": "system",
                            "content": "당신은 정보관리기술사 시험 출제 경험이 있는 전문가입니다. "
                            "토픽과 관련된 핵심 기술 용어를 추출하세요. "
                            "복합어(예: TCP/IP, REST API, OSI 7계층)를 반드시 보존하세요."
                        },
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,  # Lower temperature for more focused extraction
                    max_tokens=1000,
                )

                result_text = response.choices[0].message.content
                keywords = self._parse_llm_keywords(result_text)
                
                # Score and filter keywords
                scored_keywords = self._score_keywords(keywords, topic_name)
                
                # Sort by total score and return top keywords
                sorted_keywords = sorted(
                    scored_keywords,
                    key=lambda x: x.total_score,
                    reverse=True
                )
                
                # Return top 10 keywords
                result_keywords = [kw.keyword for kw in sorted_keywords[:10]]

                # 결과 캐싱
                try:
                    if self._cache_manager and self._cache_manager.enabled:
                        cache_key = self._make_llm_cache_key(topic_name, current_content, field_name)
                        import json
                        data = {"keywords": result_keywords}
                        ttl = self._cache_manager._ttl.LLM_RESPONSE
                        await self._cache_manager._in_memory.set(cache_key, json.dumps(data), ttl) if self._cache_manager._in_memory else None
                        logger.debug(f"llm_keyword_cached: {cache_key}, ttl={ttl}")
                except Exception as cache_err:
                    logger.warning(f"Failed to cache keywords: {cache_err}")

                return result_keywords

            except Exception as e:
                # Check for rate limit errors (429)
                if hasattr(e, 'status') and e.status == 429:
                    raise OpenAIError(
                        message=f"OpenAI rate limit exceeded: {e}",
                        operation="chat.completions.create",
                        topic_id=topic_id,
                        original_error=e,
                    )

                # Check for authentication errors
                if hasattr(e, 'status') and e.status == 401:
                    raise LLMError(
                        message=f"OpenAI authentication failed: {e}",
                        operation="chat.completions.create",
                        topic_id=topic_id,
                        original_error=e,
                    )

                # Check for server errors (5xx) - these are transient
                if hasattr(e, 'status') and 500 <= e.status < 600:
                    raise OpenAIError(
                        message=f"OpenAI server error: {e}",
                        operation="chat.completions.create",
                        topic_id=topic_id,
                        original_error=e,
                    )

                # Other errors
                raise LLMError(
                    message=f"LLM keyword extraction failed: {e}",
                    operation="generate_keywords_with_llm",
                    topic_id=topic_id,
                    original_error=e,
                )

        try:
            # Use circuit breaker for LLM calls
            if self._circuit_breaker:
                return await with_circuit_breaker("openai", _call_llm)
            else:
                return await _call_llm()
        except Exception as e:
            log_error(
                logger,
                LLMError(
                    message=f"LLM keyword extraction failed after retries: {e}",
                    operation="generate_keywords_with_llm",
                    topic_id=topic_id,
                    original_error=e,
                ),
            )
            # Return fallback: extract keywords from domain terms
            return self._extract_keywords_from_domain(current_content)

    def _build_keyword_prompt(
        self,
        topic_name: str,
        current_content: str,
        field_name: str,
    ) -> str:
        """Build prompt for keyword extraction."""
        domain_list = ", ".join(self._domain_terms.keys())
        
        return f"""토픽: {topic_name}
필드: {field_name}

현재 내용:
{current_content[:1500]}

관련 도메인: {domain_list}

위 정보를 바탕으로 기술사 시험 관점에서 중요한 기술 용어(키워드)를 추출하세요.

지침:
1. 복합어를 반드시 보존하세요 (예: TCP/IP, REST API, OSI 7계층, CI/CD, Machine Learning)
2. 기술사 시험에 자주 나오는 용어 우선
3. 구체적인 기술 용어 선택
4. 최대 15개 키워드 추출

답변 형식 (쉼표로 구분):
키워드1, 키워드2, 키워드3, ...
"""

    def _parse_llm_keywords(self, result_text: str) -> List[str]:
        """Parse LLM output to extract keywords."""
        # Remove common prefixes
        text = result_text.strip()
        
        # Remove markdown code blocks
        text = re.sub(r'```(?:json)?\n?', '', text)
        
        # Extract comma-separated keywords or newline-separated keywords
        # Try comma-separated first
        if ',' in text:
            keywords = [k.strip() for k in text.split(',')]
        else:
            # Try newline-separated
            keywords = [k.strip() for k in text.split('\n')]
            # Remove bullet points and numbering
            keywords = [re.sub(r'^[\d\-\*\•]+\s*', '', k) for k in keywords]
        
        # Filter out empty strings and common non-keyword phrases
        filtered_keywords = []
        skip_phrases = [
            '키워드', '다음과 같습니다', '입니다', '추천합니다',
            '답변', '입니다', '입니다', '추천', '기술 용어'
        ]
        
        for kw in keywords:
            kw = kw.strip()
            if kw and len(kw) > 1:
                # Skip if it's a meta phrase
                if not any(phrase in kw for phrase in skip_phrases):
                    filtered_keywords.append(kw)
        
        return filtered_keywords

    def _score_keywords(
        self,
        keywords: List[str],
        topic_name: str
    ) -> List[KeywordScore]:
        """Score keywords based on domain relevance, exam frequency, and originality."""
        scored_keywords = []
        
        for keyword in keywords:
            # Skip if it's a stopword
            if keyword.lower() in self._stopwords:
                continue
                
            score = self._calculate_keyword_score(keyword, topic_name)
            scored_keywords.append(score)
        
        return scored_keywords

    def _calculate_keyword_score(self, keyword: str, topic_name: str) -> KeywordScore:
        """Calculate quality score for a single keyword."""
        # 1. Domain Relevance (도메인 관련성)
        domain_relevance = self._calculate_domain_relevance(keyword)
        
        # 2. Exam Frequency (출제 빈도) - based on priority in domain terms
        exam_frequency = self._calculate_exam_frequency(keyword)
        
        # 3. Originality (독창성) - compound words or specific technical terms score higher
        originality = self._calculate_originality(keyword)
        
        # Calculate weighted total score
        total_score = (
            domain_relevance * 0.5 +
            exam_frequency * 0.3 +
            originality * 0.2
        )
        
        # Determine category
        category = self._categorize_keyword(keyword)
        
        return KeywordScore(
            keyword=keyword,
            domain_relevance=domain_relevance,
            exam_frequency=exam_frequency,
            originality=originality,
            total_score=total_score,
            category=category
        )

    def _calculate_domain_relevance(self, keyword: str) -> float:
        """Calculate domain relevance score (0-1)."""
        # Check if keyword is in domain terms
        for domain_name, domain_data in self._domain_terms.items():
            terms = domain_data.get("terms", [])
            for term_info in terms:
                term = term_info.get("term", "")
                related = term_info.get("related_terms", [])
                
                if keyword == term:
                    # Exact match with domain term
                    priority = term_info.get("priority", 5)
                    return min(priority / 10.0, 1.0)
                
                if keyword in related:
                    # Related term
                    return 0.7
        
        # Check compound terms
        if keyword in self._compound_terms:
            return 0.8
        
        # Partial match (keyword contains domain term or vice versa)
        for domain_name, domain_data in self._domain_terms.items():
            terms = domain_data.get("terms", [])
            for term_info in terms:
                term = term_info.get("term", "")
                if term in keyword or keyword in term:
                    return 0.5
        
        # Low relevance for unknown terms
        return 0.3

    def _calculate_exam_frequency(self, keyword: str) -> float:
        """Calculate exam frequency score (0-1)."""
        # High-priority domain terms are more likely to appear on exams
        for domain_name, domain_data in self._domain_terms.items():
            terms = domain_data.get("terms", [])
            for term_info in terms:
                term = term_info.get("term", "")
                priority = term_info.get("priority", 5)
                
                if keyword == term:
                    return min(priority / 10.0, 1.0)
        
        # Compound terms often appear on exams
        if keyword in self._compound_terms:
            return 0.7
        
        # Default score
        return 0.5

    def _calculate_originality(self, keyword: str) -> float:
        """Calculate originality score (0-1)."""
        score = 0.5  # Base score
        
        # Compound words score higher
        if any(separator in keyword for separator in ['/', '-', ' ']):
            score += 0.3
        
        # Longer technical terms (3+ characters in Korean or 5+ in English)
        korean_chars = len(re.findall(r'[가-힣]', keyword))
        english_chars = len(re.findall(r'[a-zA-Z]', keyword))
        
        if korean_chars >= 3 or english_chars >= 5:
            score += 0.1
        
        # Mixed Korean-English terms are often technical
        if re.search(r'[가-힣]', keyword) and re.search(r'[a-zA-Z]', keyword):
            score += 0.1
        
        # Acronyms (all caps, 2+ characters)
        if re.match(r'^[A-Z]{2,}$', keyword):
            score += 0.1
        
        return min(score, 1.0)

    def _categorize_keyword(self, keyword: str) -> str:
        """Categorize keyword into domain."""
        # Check compound terms first
        if keyword in self._compound_terms:
            return self._compound_terms[keyword]
        
        # Check domain terms
        for domain_name, domain_data in self._domain_terms.items():
            terms = domain_data.get("terms", [])
            for term_info in terms:
                term = term_info.get("term", "")
                related = term_info.get("related_terms", [])
                
                if keyword == term or keyword in related:
                    return domain_name
        
        return "기타"

    def _extract_keywords_from_domain(self, content: str) -> List[str]:
        """Fallback: Extract keywords from domain terms based on content."""
        found_keywords = []
        content_lower = content.lower()
        
        for domain_name, domain_data in self._domain_terms.items():
            terms = domain_data.get("terms", [])
            for term_info in terms:
                term = term_info.get("term", "")
                # Check if term or related terms appear in content
                if term.lower() in content_lower:
                    found_keywords.append((term, term_info.get("priority", 5)))
        
        # Sort by priority and return top keywords
        found_keywords.sort(key=lambda x: x[1], reverse=True)
        return [kw[0] for kw in found_keywords[:10]]

    @with_retry(max_attempts=3, wait_min=1.0, wait_max=10.0)
    async def generate_with_llm(
        self,
        topic_name: str,
        current_content: str,
        reference_content: str,
        topic_id: Optional[str] = None,
    ) -> str:
        """
        Generate enhanced content using LLM with retry logic.

        Args:
            topic_name: Name of the topic
            current_content: Current topic content
            reference_content: Reference document content
            topic_id: Optional topic ID for logging

        Returns:
            Generated enhanced content

        Raises:
            LLMError: LLM generation 실패 시
        """
        # 캐시 초기화
        await self._initialize_cache()

        # 캐시 확인
        if self._cache_manager and self._cache_manager.enabled:
            try:
                cache_key = self._make_llm_prompt_cache_key(topic_name, current_content, reference_content)
                cached = await self._cache_manager._in_memory.get(cache_key) if self._cache_manager._in_memory else None
                if cached:
                    import json
                    data = json.loads(cached)
                    logger.debug(f"llm_generation_cache_hit: {cache_key}")
                    return data.get("content", "")
            except Exception as e:
                logger.warning(f"Failed to get cached generation: {e}")

        if not self.client:
            # Fallback: return reference content (degraded mode)
            log_error(
                logger,
                DegradedError(
                    message="OpenAI client not initialized, using fallback",
                    service="llm",
                    operation="generate_with_llm",
                    topic_id=topic_id,
                ),
            )
            return reference_content[:500]

        async def _call_llm():
            try:
                prompt = self._build_llm_prompt(topic_name, current_content, reference_content)

                response = await self.client.chat.completions.create(
                    model=settings.openai_model,
                    messages=[
                        {
                            "role": "system",
                            "content": "당신은 정보관리기술사 시험 준비를 돕는 조교입니다. "
                            "기술사 관점에서 정확하고 상세한 답변을 제공하세요."
                        },
                        {"role": "user", "content": prompt}
                    ],
                    temperature=settings.llm_temperature,
                    max_tokens=settings.llm_max_tokens,
                )

                logger.info(
                    "llm_generation_success",
                    topic_id=topic_id,
                    model=settings.openai_model,
                )

                result_content = response.choices[0].message.content

                # 결과 캐싱
                try:
                    if self._cache_manager and self._cache_manager.enabled:
                        cache_key = self._make_llm_prompt_cache_key(topic_name, current_content, reference_content)
                        import json
                        data = {"content": result_content}
                        ttl = self._cache_manager._ttl.LLM_RESPONSE
                        await self._cache_manager._in_memory.set(cache_key, json.dumps(data), ttl) if self._cache_manager._in_memory else None
                        logger.debug(f"llm_generation_cached: {cache_key}, ttl={ttl}")
                except Exception as cache_err:
                    logger.warning(f"Failed to cache generation: {cache_err}")

                return result_content

            except Exception as e:
                # Check for rate limit errors (429)
                if hasattr(e, 'status') and e.status == 429:
                    raise OpenAIError(
                        message=f"OpenAI rate limit exceeded: {e}",
                        operation="chat.completions.create",
                        topic_id=topic_id,
                        original_error=e,
                    )

                # Check for authentication errors
                if hasattr(e, 'status') and e.status == 401:
                    raise LLMError(
                        message=f"OpenAI authentication failed: {e}",
                        operation="chat.completions.create",
                        topic_id=topic_id,
                        original_error=e,
                    )

                # Check for server errors (5xx) - these are transient
                if hasattr(e, 'status') and 500 <= e.status < 600:
                    raise OpenAIError(
                        message=f"OpenAI server error: {e}",
                        operation="chat.completions.create",
                        topic_id=topic_id,
                        original_error=e,
                    )

                # Other errors
                raise LLMError(
                    message=f"LLM generation failed: {e}",
                    operation="generate_with_llm",
                    topic_id=topic_id,
                    original_error=e,
                )

        try:
            # Use circuit breaker for LLM calls
            if self._circuit_breaker:
                return await with_circuit_breaker("openai", _call_llm)
            else:
                return await _call_llm()
        except Exception as e:
            log_error(
                logger,
                LLMError(
                    message=f"LLM generation failed after retries: {e}",
                    operation="generate_with_llm",
                    topic_id=topic_id,
                    original_error=e,
                ),
            )
            # Return fallback content in degraded mode
            return reference_content[:500]

    def _build_llm_prompt(
        self,
        topic_name: str,
        current_content: str,
        reference_content: str,
    ) -> str:
        """Build prompt for LLM."""
        return f"""토픽: {topic_name}

현재 내용:
{current_content[:1000]}

참조 문서:
{reference_content[:2000]}

위 정보를 바탕으로 기술사 시험 관점에서:
1. 누락된 핵심 내용
2. 부정확한 정보
3. 보강이 필요한 부분

을 분석하고 개선된 내용을 작성해주세요.

답변 형식:
- 개선된 내용을 상세히 작성
- 기술 용어를 정확히 사용
- 기술사 시험 수준에 맞춰 작성"""


# Global proposal generator instance
_proposal_generator: ProposalGenerator | None = None


def get_proposal_generator() -> ProposalGenerator:
    """Get or create global proposal generator instance."""
    global _proposal_generator
    if _proposal_generator is None:
        _proposal_generator = ProposalGenerator()
    return _proposal_generator
