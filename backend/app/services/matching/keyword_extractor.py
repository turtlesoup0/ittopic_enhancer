"""키워드 추출 유틸리티 모듈.

이 모듈은 다음 기능을 제공합니다:
1. 복합어 보존 정규식 (TCP/IP, REST API 등의 분리 방지)
2. 동의어 확장 기능
3. 확장된 불용어 처리
"""
import re
import logging
from pathlib import Path
from typing import List, Dict, Set, Optional, Any
from collections import Counter

import yaml

logger = logging.getLogger(__name__)


class KeywordExtractor:
    """복합어 보존 및 동의어 확장을 지원하는 키워드 추출기."""

    # 복합어 패턴: 슬래시, 공백, 마침표, 하이픈으로 연결된 용어
    # 예: TCP/IP, REST API, Web Service, NoSQL
    COMPOUND_PATTERNS = [
        # 슬래시로 연결된 복합어 (TCP/IP, I/O, R/W)
        r"\b[A-Za-z]{2,}/[A-Za-z]{2,}(?:/[A-Za-z]{2,})*\b",
        # 점으로 연결된 복합어 (e.g., i.e., etc., U.S.A)
        r"\b[A-Za-z](?:\.[A-Za-z])+\.?\b",
        # 하이픈으로 연결된 복합어 (state-of-the-art, real-time)
        r"\b[A-Za-z]{2,}(?:-[A-Za-z]{2,})+\b",
        # 대문자 약어 (AI, REST, API, TCP, UDP)
        r"\b[A-Z]{2,}\b",
        # 한글 복합명사 (2글자 이상 한글)
        r"[가-힣]{2,}",
        # 일반 영어 단어 (3글자 이상)
        r"\b[a-z]{3,}\b",
    ]

    # 통합 정규식 패턴
    COMPOUND_REGEX = re.compile(
        "|".join(COMPOUND_PATTERNS),
        re.IGNORECASE | re.UNICODE
    )

    def __init__(
        self,
        config_dir: Optional[str] = None,
        use_synonyms: bool = True,
        use_stopwords: bool = True,
    ):
        """
        키워드 추출기 초기화.

        Args:
            config_dir: 설정 파일 디렉토리 (기본값: backend/config/)
            use_synonyms: 동의어 확장 사용 여부
            use_stopwords: 불용어 필터링 사용 여부
        """
        if config_dir is None:
            # 기본 설정 디렉토리
            current_dir = Path(__file__).parent.parent.parent.parent
            config_dir = current_dir / "config"

        self.config_dir = Path(config_dir)
        self.use_synonyms = use_synonyms
        self.use_stopwords = use_stopwords

        # 동의어 매핑 로드
        self.synonym_map: Dict[str, List[str]] = {}
        self._load_synonyms()

        # 불용어 세트 로드
        self.stopwords: Set[str] = set()
        self._load_stopwords()

    def _load_synonyms(self) -> None:
        """동의어 매핑 파일을 로드합니다."""
        synonyms_file = self.config_dir / "synonyms.yaml"

        if not synonyms_file.exists():
            logger.warning(f"동의어 파일을 찾을 수 없습니다: {synonyms_file}")
            return

        try:
            with open(synonyms_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

            # 역방향 매핑 생성: 동의어 -> 원본 용어
            self.synonym_map = {}
            for primary_term, synonyms in data.items():
                # 모든 동의어를 소문자로 변환하여 매핑
                primary_lower = primary_term.lower()
                synonym_list = synonyms if isinstance(synonyms, list) else [synonyms]
                
                for synonym in synonym_list:
                    synonym_lower = synonym.lower()
                    if synonym_lower not in self.synonym_map:
                        self.synonym_map[synonym_lower] = []
                    self.synonym_map[synonym_lower].append(primary_term)

                # 원본 용어도 자신의 동의어로 추가
                if primary_lower not in self.synonym_map:
                    self.synonym_map[primary_lower] = []
                self.synonym_map[primary_lower].append(primary_term)

            logger.info(f"동의어 매핑 로드 완료: {len(self.synonym_map)}개 항목")

        except Exception as e:
            logger.error(f"동의어 파일 로드 실패: {e}")

    def _load_stopwords(self) -> None:
        """불용어 파일을 로드합니다."""
        stopwords_file = self.config_dir / "stopwords.yaml"

        if not stopwords_file.exists():
            logger.warning(f"불용어 파일을 찾을 수 없습니다: {stopwords_file}")
            return

        try:
            with open(stopwords_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

            # 모든 불용어를 하나의 세트로 통합
            for category, words in data.items():
                if isinstance(words, list):
                    for word in words:
                        if isinstance(word, str):
                            self.stopwords.add(word.lower())

            logger.info(f"불용어 로드 완료: {len(self.stopwords)}개 항목")

        except Exception as e:
            logger.error(f"불용어 파일 로드 실패: {e}")

    def _expand_synonyms(self, keywords: List[str]) -> List[str]:
        """
        키워드의 동의어를 확장합니다.

        Args:
            keywords: 원본 키워드 목록

        Returns:
            동의어가 포함된 확장된 키워드 목록
        """
        if not self.use_synonyms or not self.synonym_map:
            return keywords

        expanded = list(keywords)  # 원본 키워드 포함

        for keyword in keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in self.synonym_map:
                # 해당 키워드의 동의어들 추가
                expanded.extend(self.synonym_map[keyword_lower])

        return list(set(expanded))  # 중복 제거

    def _filter_stopwords(self, keywords: List[str]) -> List[str]:
        """
        불용어를 필터링합니다.

        Args:
            keywords: 키워드 목록

        Returns:
            불용어가 제거된 키워드 목록
        """
        if not self.use_stopwords or not self.stopwords:
            return keywords

        filtered = [
            keyword for keyword in keywords
            if keyword.lower() not in self.stopwords
            and len(keyword) >= 2  # 1글자 키워드 제거
        ]

        return filtered

    def extract_keywords(
        self,
        text: str,
        top_k: int = 50,
        use_synonyms: bool = True,
        use_stopwords: bool = True,
    ) -> List[str]:
        """
        텍스트에서 키워드를 추출합니다.

        복합어 보존 정규식을 사용하여 TCP/IP, REST API와 같은
        복합어가 분리되지 않도록 합니다.

        Args:
            text: 분석할 텍스트
            top_k: 반환할 상위 키워드 수
            use_synonyms: 동의어 확장 사용 여부 (None이면 초기화 값 사용)
            use_stopwords: 불용어 필터링 사용 여부 (None이면 초기화 값 사용)

        Returns:
            추출된 키워드 목록 (빈도수 내림차순)
        """
        # 복합어 보존 정규식으로 토큰 추출
        tokens = self.COMPOUND_REGEX.findall(text)

        if not tokens:
            return []

        # 불용어 필터링
        if use_stopwords or (use_stopwords is None and self.use_stopwords):
            tokens = self._filter_stopwords(tokens)

        # 빈도수 계산
        counter = Counter(tokens)
        top_keywords = [word for word, _ in counter.most_common(top_k * 2)]

        # 동의어 확장
        if use_synonyms or (use_synonyms is None and self.use_synonyms):
            expanded = self._expand_synonyms(top_keywords)
        else:
            expanded = top_keywords

        # 최종 결과: 원본 키워드 + 동의어 중 상위 K개
        final_counter = Counter(expanded)
        return [word for word, _ in final_counter.most_common(top_k)]

    def get_synonyms(self, keyword: str) -> List[str]:
        """
        특정 키워드의 동의어를 반환합니다.

        Args:
            keyword: 조회할 키워드

        Returns:
            동의어 목록 (없으면 빈 리스트)
        """
        keyword_lower = keyword.lower()
        return self.synonym_map.get(keyword_lower, [])

    def normalize_keyword(self, keyword: str) -> str:
        """
        키워드를 정규화합니다 (동의어를 기본 용어로 변환).

        Args:
            keyword: 정규화할 키워드

        Returns:
            정규화된 키워드 (동의어가 없으면 원본 반환)
        """
        keyword_lower = keyword.lower()
        if keyword_lower in self.synonym_map and self.synonym_map[keyword_lower]:
            # 첫 번째 매핑된 용어를 기본 용어로 사용
            return self.synonym_map[keyword_lower][0]
        return keyword


# 편의 함수: 기본 추출기 인스턴스
_default_extractor: Optional[KeywordExtractor] = None


def get_extractor(config_dir: Optional[str] = None) -> KeywordExtractor:
    """
    기본 키워드 추출기 인스턴스를 반환합니다.

    Args:
        config_dir: 설정 파일 디렉토리 (선택사항)

    Returns:
        KeywordExtractor 인스턴스
    """
    global _default_extractor

    if _default_extractor is None or config_dir is not None:
        _default_extractor = KeywordExtractor(config_dir=config_dir)

    return _default_extractor


def extract_keywords(
    text: str,
    top_k: int = 50,
    config_dir: Optional[str] = None,
) -> List[str]:
    """
    텍스트에서 키워드를 추출하는 편의 함수.

    Args:
        text: 분석할 텍스트
        top_k: 반환할 상위 키워드 수
        config_dir: 설정 파일 디렉토리 (선택사항)

    Returns:
        추출된 키워드 목록
    """
    extractor = get_extractor(config_dir)
    return extractor.extract_keywords(text, top_k=top_k)
