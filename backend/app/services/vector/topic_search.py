"""Topic similarity search service."""
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)


class TopicSearchService:
    """토픽 유사도 검색 서비스."""

    def __init__(self, json_path: Optional[str] = None):
        """
        토픽 검색 서비스 초기화.

        Args:
            json_path: Obsidian에서 내보낸 JSON 파일 경로
        """
        self.topics: List[Dict] = []
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.tfidf_matrix: Optional[np.ndarray] = None
        self._last_json_path: Optional[str] = None

        if json_path:
            self.load_from_json(json_path)

    def load_from_json(self, json_path: str) -> None:
        """
        JSON 파일에서 토픽 로드.

        Args:
            json_path: JSON 파일 경로
        """
        path = Path(json_path)
        if not path.exists():
            raise FileNotFoundError(f"JSON 파일 없음: {json_path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.topics = data.get("notes", [])
        self._build_index()
        self._last_json_path = str(path)

        logger.info(f"로드된 토픽 수: {len(self.topics)}")

    def load_from_dict(self, data: dict) -> None:
        """
        dict에서 토픽 로드.

        Args:
            data: 토픽 데이터 (notes 필드 포함)
        """
        self.topics = data.get("notes", [])
        self._build_index()
        logger.info(f"로드된 토픽 수: {len(self.topics)}")

    def _build_index(self) -> None:
        """TF-IDF 인덱스 구축."""
        # 각 토픽의 검색 텍스트 구성
        documents = []
        for topic in self.topics:
            parts = [
                topic.get("fileName", ""),
                topic.get("리드문", ""),
                topic.get("정의", ""),
                " ".join(topic.get("키워드", [])),
            ]
            documents.append(" ".join(parts))

        # TF-IDF 벡터화
        self.vectorizer = TfidfVectorizer(
            max_features=5000,
            ngram_range=(1, 2),
            min_df=1,
            max_df=0.95,
        )
        self.tfidf_matrix = self.vectorizer.fit_transform(documents)

    def search(
        self,
        query: str,
        top_k: int = 10,
        domain_filter: Optional[str] = None,
    ) -> List[Dict]:
        """
        토픽 검색.

        Args:
            query: 검색 쿼리
            top_k: 반환할 결과 수
            domain_filter: 도메인 필터 (선택)

        Returns:
            유사한 토픽 목록 (유사도 포함)
        """
        if not self.vectorizer or self.tfidf_matrix is None:
            return []

        # 쿼리 벡터화
        query_vec = self.vectorizer.transform([query])

        # 코사인 유사도 계산
        similarities = cosine_similarity(query_vec, self.tfidf_matrix)[0]

        # 결과 정렬
        indices = np.argsort(similarities)[::-1]

        results = []
        for idx in indices:
            if similarities[idx] < 0.01:  # 유사도 임계값
                break

            topic = self.topics[idx].copy()
            topic["similarity"] = float(similarities[idx])

            # 도메인 필터
            if domain_filter and topic.get("domain") != domain_filter:
                continue

            results.append(topic)

            if len(results) >= top_k:
                break

        return results

    def find_similar_topics(
        self,
        topic_file_path: str,
        top_k: int = 5,
        exclude_self: bool = True,
    ) -> List[Dict]:
        """
        특정 토픽과 유사한 다른 토픽 찾기.

        Args:
            topic_file_path: 기준 토픽 파일 경로
            top_k: 반환할 결과 수
            exclude_self: 자기 자신 제외 여부

        Returns:
            유사한 토픽 목록
        """
        # 기준 토픽 찾기
        target_topic = None
        target_idx = -1

        for i, topic in enumerate(self.topics):
            if topic.get("filePath") == topic_file_path:
                target_topic = topic
                target_idx = i
                break

        if target_topic is None:
            return []

        # 기준 토픽의 벡터
        if self.tfidf_matrix is None:
            return []

        target_vec = self.tfidf_matrix[target_idx]

        # 유사도 계산
        similarities = cosine_similarity(target_vec, self.tfidf_matrix)[0]

        # 결과 정렬
        indices = np.argsort(similarities)[::-1]

        results = []
        for idx in indices:
            # 자기 자신 제외
            if exclude_self and idx == target_idx:
                continue

            if similarities[idx] < 0.05:  # 유사도 임계값
                break

            topic = self.topics[idx].copy()
            topic["similarity"] = float(similarities[idx])
            results.append(topic)

            if len(results) >= top_k:
                break

        return results

    def get_topic_by_path(self, file_path: str) -> Optional[Dict]:
        """
        파일 경로로 토픽 찾기.

        Args:
            file_path: 토픽 파일 경로

        Returns:
            토픽 데이터 또는 None
        """
        for topic in self.topics:
            if topic.get("filePath") == file_path:
                return topic.copy()
        return None

    def get_stats(self) -> Dict:
        """통계 정보 반환."""
        domain_counts = {}
        for topic in self.topics:
            domain = topic.get("domain", "기타")
            domain_counts[domain] = domain_counts.get(domain, 0) + 1

        return {
            "total_topics": len(self.topics),
            "domain_counts": domain_counts,
        }
