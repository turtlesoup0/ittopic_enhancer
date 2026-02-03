"""Content validation engine."""
from typing import List, Optional
from datetime import datetime
import logging
import hashlib

from app.models.topic import Topic
from app.models.reference import MatchedReference
from app.models.validation import ValidationResult, ContentGap, GapType
from app.core.cache import CacheManager, get_cache_manager

logger = logging.getLogger(__name__)


class ValidationEngine:
    """Engine for validating topic content against references."""

    def __init__(self):
        """Initialize validation engine."""
        self.min_field_lengths = {
            "리드문": 30,
            "정의": 50,
        }
        self.min_keyword_count = 3
        self._cache_manager: Optional[CacheManager] = None

    async def _initialize_cache(self):
        """캐시 매니저 초기화."""
        if self._cache_manager is None:
            self._cache_manager = await get_cache_manager()

    def _make_cache_key(self, topic: Topic, references: List[MatchedReference]) -> str:
        """
        검증 결과용 캐시 키를 생성합니다.

        Args:
            topic: 토픽
            references: 매칭된 참조 문서 목록

        Returns:
            캐시 키
        """
        # 토픽 콘텐츠 해시
        topic_content = f"{topic.content.리드문 or ''}|{topic.content.정의 or ''}|{','.join(topic.content.키워드 or [])}"
        topic_hash = hashlib.sha256(topic_content.encode("utf-8")).hexdigest()[:16]

        # 참조 문서 ID 해시
        ref_ids = "|".join(sorted([r.reference_id for r in references]))
        ref_hash = hashlib.sha256(ref_ids.encode("utf-8")).hexdigest()[:16] if ref_ids else "none"

        return f"validation:{topic.id}:{topic_hash}:{ref_hash}"

    async def validate(
        self,
        topic: Topic,
        references: List[MatchedReference],
    ) -> ValidationResult:
        """
        Validate topic content against reference documents.

        Args:
            topic: Topic to validate
            references: Matched reference documents

        Returns:
            Validation result with gaps and scores
        """
        # 캐시 초기화
        await self._initialize_cache()

        # 캐시 확인
        if self._cache_manager and self._cache_manager.enabled:
            try:
                cache_key = self._make_cache_key(topic, references)
                cached = await self._cache_manager._in_memory.get(cache_key) if self._cache_manager._in_memory else None
                if cached:
                    import json
                    data = json.loads(cached)
                    logger.debug(f"validation_cache_hit: {cache_key}")
                    # ValidationResult 복원
                    return ValidationResult(
                        topic_id=data["topic_id"],
                        overall_score=data["overall_score"],
                        gaps=[ContentGap(**gap) for gap in data["gaps"]],
                        matched_references=[MatchedReference(**ref) for ref in data["matched_references"]],
                        field_completeness_score=data.get("field_completeness_score", 0.0),
                        content_accuracy_score=data.get("content_accuracy_score", 0.0),
                        reference_coverage_score=data.get("reference_coverage_score", 0.0),
                    )
            except Exception as e:
                logger.warning(f"Failed to get cached validation: {e}")

        gaps = []

        # 1. Check field completeness
        gaps.extend(self._check_field_completeness(topic))

        # 2. Check content accuracy against references
        gaps.extend(self._check_content_accuracy(topic, references))

        # 3. Calculate scores
        field_score = self._calculate_field_completeness_score(topic)
        accuracy_score = self._calculate_accuracy_score(topic, references)
        coverage_score = self._calculate_coverage_score(topic, references)

        overall_score = (
            field_score * 0.3 +
            accuracy_score * 0.4 +
            coverage_score * 0.3
        )

        result = ValidationResult(
            id=f"validation-{topic.id}-{int(datetime.now().timestamp())}",
            topic_id=topic.id,
            overall_score=overall_score,
            gaps=gaps,
            matched_references=references,
            field_completeness_score=field_score,
            content_accuracy_score=accuracy_score,
            reference_coverage_score=coverage_score,
        )

        # 결과 캐싱
        if self._cache_manager and self._cache_manager.enabled:
            try:
                cache_key = self._make_cache_key(topic, references)
                import json
                from app.models.validation import ContentGap, GapType
                from app.models.reference import MatchedReference

                data = {
                    "topic_id": result.topic_id,
                    "overall_score": result.overall_score,
                    "gaps": [
                        {
                            "gap_type": gap.gap_type.value,
                            "field_name": gap.field_name,
                            "current_value": gap.current_value,
                            "suggested_value": gap.suggested_value,
                            "confidence": gap.confidence,
                            "reference_id": gap.reference_id,
                            "reasoning": gap.reasoning,
                            "missing_count": gap.missing_count,
                            "required_count": gap.required_count,
                            "gap_details": gap.gap_details,
                        }
                        for gap in result.gaps
                    ],
                    "matched_references": [
                        {
                            "reference_id": ref.reference_id,
                            "title": ref.title,
                            "source": ref.source.value if hasattr(ref.source, 'value') else ref.source,
                            "similarity_score": ref.similarity_score,
                            "relevant_snippet": ref.relevant_snippet,
                        }
                        for ref in result.matched_references
                    ],
                    "field_completeness_score": result.field_completeness_score,
                    "content_accuracy_score": result.content_accuracy_score,
                    "reference_coverage_score": result.reference_coverage_score,
                }
                ttl = self._cache_manager._ttl.VALIDATION
                await self._cache_manager._in_memory.set(cache_key, json.dumps(data), ttl) if self._cache_manager._in_memory else None
                logger.debug(f"validation_cached: {cache_key}, ttl={ttl}")
            except Exception as e:
                logger.warning(f"Failed to cache validation result: {e}")

        return result

    async def invalidate_topic_cache(self, topic_id: str):
        """
        토픽 관련 검증 캐시를 무효화합니다.

        Args:
            topic_id: 토픽 ID
        """
        if self._cache_manager and self._cache_manager.enabled:
            try:
                pattern = f"validation:{topic_id}:*"
                count = await self._cache_manager.invalidate_by_pattern(pattern)
                logger.info(f"Invalidated {count} validation caches for topic: {topic_id}")
            except Exception as e:
                logger.warning(f"Failed to invalidate validation cache: {e}")

    async def invalidate_reference_cache(self, reference_id: str):
        """
        참조 문서 관련 검증 캐시를 무효화합니다.

        Args:
            reference_id: 참조 문서 ID
        """
        if self._cache_manager and self._cache_manager.enabled:
            try:
                # 참조 문서가 변경되면 해당 참조를 사용하는 모든 검증 결과 무효화
                # (실제로는 참조 ID를 캐시 키의 일부로 사용)
                pattern = f"validation:*:*{reference_id}*"
                count = await self._cache_manager.invalidate_by_pattern(pattern)
                logger.info(f"Invalidated {count} validation caches for reference: {reference_id}")
            except Exception as e:
                logger.warning(f"Failed to invalidate reference cache: {e}")

    def _check_field_completeness(self, topic: Topic) -> List[ContentGap]:
        """Check if required fields are complete."""
        gaps = []

        # Check 리드문
        if not topic.content.리드문 or len(topic.content.리드문.strip()) < self.min_field_lengths["리드문"]:
            current_length = len(topic.content.리드문.strip()) if topic.content.리드문 else 0
            missing_length = max(0, self.min_field_lengths["리드문"] - current_length)
            gaps.append(ContentGap(
                gap_type=GapType.MISSING_FIELD,
                field_name="리드문",
                current_value=topic.content.리드문,
                suggested_value=self._suggest_lead_from_references(topic),
                confidence=0.8,
                reference_id="",
                reasoning=f"리드문은 {self.min_field_lengths['리드문']}자 이상이어야 합니다.",
                missing_count=1,  # 1 field missing/incomplete
                required_count=1,
                gap_details={"current_length": current_length, "required_length": self.min_field_lengths["리드문"]},
            ))

        # Check 정의
        if not topic.content.정의 or len(topic.content.정의.strip()) < self.min_field_lengths["정의"]:
            current_length = len(topic.content.정의.strip()) if topic.content.정의 else 0
            missing_length = max(0, self.min_field_lengths["정의"] - current_length)
            gaps.append(ContentGap(
                gap_type=GapType.INCOMPLETE_DEFINITION,
                field_name="정의",
                current_value=topic.content.정의,
                suggested_value=self._suggest_definition_from_references(topic),
                confidence=0.7,
                reference_id="",
                reasoning=f"정의는 {self.min_field_lengths['정의']}자 이상의 기술사 수준 내용이 필요합니다.",
                missing_count=1,  # 1 field incomplete
                required_count=1,
                gap_details={"current_length": current_length, "required_length": self.min_field_lengths["정의"]},
            ))

        # Check 키워드
        keyword_count = len(topic.content.키워드) if topic.content.키워드 else 0
        if keyword_count < self.min_keyword_count:
            missing_keywords = max(0, self.min_keyword_count - keyword_count)
            gaps.append(ContentGap(
                gap_type=GapType.MISSING_KEYWORDS,
                field_name="키워드",
                current_value=", ".join(topic.content.키워드) if topic.content.키워드 else "",
                suggested_value=f"기술 관련 핵심 용어 {self.min_keyword_count}개 이상 필요",
                confidence=0.9,
                reference_id="",
                reasoning=f"최소 {self.min_keyword_count}개 이상의 키워드가 필요합니다.",
                missing_count=missing_keywords,  # Actual missing keyword count
                required_count=self.min_keyword_count,
                gap_details={"current_count": keyword_count, "required_count": self.min_keyword_count},
            ))

        return gaps

    def _check_content_accuracy(
        self,
        topic: Topic,
        references: List[MatchedReference],
    ) -> List[ContentGap]:
        """Check content accuracy against references."""
        gaps = []

        if not references:
            # No references found - suggest adding content
            gaps.append(ContentGap(
                gap_type=GapType.MISSING_KEYWORDS,
                field_name="전체",
                current_value="",
                suggested_value="참조 문서를 찾을 수 없습니다. 내용을 보강하세요.",
                confidence=0.5,
                reference_id="",
                reasoning="관련 참조 문서를 찾을 수 없어 내용 검증이 불가능합니다.",
                missing_count=1,
                required_count=1,
                gap_details={"references_found": 0},
            ))
            return gaps

        # Check if reference content is better/more detailed
        for ref in references[:2]:  # Check top 2 references
            if ref.similarity_score > 0.8:
                # High similarity but might have better content
                current_length = len(topic.content.정의) if topic.content.정의 else 0
                ref_length = len(ref.relevant_snippet)
                length_ratio = ref_length / max(current_length, 1)

                if length_ratio > 1.5:
                    gaps.append(ContentGap(
                        gap_type=GapType.INCOMPLETE_DEFINITION,
                        field_name="정의",
                        current_value=topic.content.정의[:100],
                        suggested_value=ref.relevant_snippet[:200],
                        confidence=ref.similarity_score,
                        reference_id=ref.reference_id,
                        reasoning=f"참조 문서 '{ref.title}'에 더 상세한 내용이 있습니다.",
                        missing_count=1,
                        required_count=1,
                        gap_details={
                            "current_length": current_length,
                            "reference_length": ref_length,
                            "length_ratio": length_ratio,
                        },
                    ))

        return gaps

    def _calculate_field_completeness_score(self, topic: Topic) -> float:
        """Calculate field completeness score (0-1)."""
        scores = []

        # 리드문
        lead_score = min(1.0, len(topic.content.리드문) / self.min_field_lengths["리드문"]) if topic.content.리드문 else 0.0
        scores.append(lead_score)

        # 정의
        def_score = min(1.0, len(topic.content.정의) / self.min_field_lengths["정의"]) if topic.content.정의 else 0.0
        scores.append(def_score)

        # 키워드
        keyword_score = min(1.0, len(topic.content.키워드) / self.min_keyword_count) if topic.content.키워드 else 0.0
        scores.append(keyword_score)

        # 해시태그
        tag_score = 1.0 if topic.content.해시태그 else 0.5
        scores.append(tag_score)

        # 암기
        memory_score = 0.5 if topic.content.암기 else 0.0
        scores.append(memory_score)

        return sum(scores) / len(scores)

    def _calculate_accuracy_score(
        self,
        topic: Topic,
        references: List[MatchedReference],
    ) -> float:
        """Calculate content accuracy score based on reference matches."""
        if not references:
            return 0.5  # Neutral score if no references

        # Average similarity score of top references
        top_scores = [r.similarity_score for r in references[:3]]
        return sum(top_scores) / len(top_scores)

    def _calculate_coverage_score(
        self,
        topic: Topic,
        references: List[MatchedReference],
    ) -> float:
        """Calculate reference coverage score."""
        if not references:
            return 0.0

        # Score based on number of high-quality matches
        high_quality = sum(1 for r in references if r.similarity_score > 0.8)
        medium_quality = sum(1 for r in references if 0.7 < r.similarity_score <= 0.8)

        return min(1.0, (high_quality * 0.5 + medium_quality * 0.3))

    def _suggest_lead_from_references(self, topic: Topic) -> str:
        """Suggest lead sentence from topic content."""
        if topic.content.리드문:
            return topic.content.리드문
        if topic.content.정의:
            return topic.content.정의[:100]
        return f"{topic.metadata.file_name}에 대한 핵심 요약 (1-2문장)"

    def _suggest_definition_from_references(self, topic: Topic) -> str:
        """Suggest definition from topic content."""
        if topic.content.정의:
            return topic.content.정의
        return f"{topic.metadata.file_name} 기술사 수준 정의 (50자 이상)"


# Global validation engine instance
_validation_engine: ValidationEngine | None = None


def get_validation_engine() -> ValidationEngine:
    """Get or create global validation engine instance."""
    global _validation_engine
    if _validation_engine is None:
        _validation_engine = ValidationEngine()
    return _validation_engine
