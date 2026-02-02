"""Integration tests for TopicSearchService."""
import json
import pytest
from app.services.vector.topic_search import TopicSearchService


# 샘플 토픽 데이터
SAMPLE_TOPICS = {
    "exportDate": "2025-02-02T00:00:00.000Z",
    "totalCount": 5,
    "notes": [
        {
            "filePath": "1_Project/정보 관리 기술사/1_신기술/인공지능.md",
            "fileName": "인공지능",
            "domain": "신기술",
            "리드문": "인간의 학습, 추론, 자연어 이해 등 지능적 행위를 컴퓨터가 수행하는 기술",
            "정의": "기계가 인간의 지능적 행위를 모방하는 기술",
            "키워드": ["AI", "머신러닝", "딥러닝"],
            "해시태그": "#인공지능",
            "암기": "",
        },
        {
            "filePath": "1_Project/정보 관리 기술사/1_신기술/머신러닝.md",
            "fileName": "머신러닝",
            "domain": "신기술",
            "리드문": "데이터로부터 학습하여 예측 모델을 만드는 AI 기술",
            "정의": "기계가 데이터로부터 패턴을 학습하는 기술",
            "키워드": ["AI", "학습", "알고리즘"],
            "해시태그": "#머신러닝",
            "암기": "",
        },
        {
            "filePath": "1_Project/정보 관리 기술사/2_정보보안/암호.md",
            "fileName": "암호",
            "domain": "정보보안",
            "리드문": "정보를 보호하기 위한 암호화 기술",
            "정의": "데이터를 비밀키로 변환하여 보호하는 기술",
            "키워드": ["보안", "암호화", "키"],
            "해시태그": "#보안",
            "암기": "",
        },
        {
            "filePath": "1_Project/정보 관리 기술사/4_SW/요구공학.md",
            "fileName": "요구공학",
            "domain": "SW",
            "리드문": "소프트웨어 요구사항을 수집, 분석, 명세하는 공학",
            "정의": "이해관계자 요구를 체계적으로 관리하는 공학",
            "키워드": ["요구사항", "명세", "분석"],
            "해시태그": "#요구공학",
            "암기": "",
        },
        {
            "filePath": "1_Project/정보 관리 기술사/6_데이터베이스/SQL.md",
            "fileName": "SQL",
            "domain": "데이터베이스",
            "리드문": "데이터베이스 질의 언어",
            "정의": "관계형 데이터베이스에서 데이터를 조작하는 언어",
            "키워드": ["데이터", "쿼리", "DB"],
            "해시태그": "#데이터베이스",
            "암기": "",
        },
    ],
}


@pytest.fixture
def topic_search():
    """TopicSearchService fixture."""
    service = TopicSearchService()
    service.load_from_dict(SAMPLE_TOPICS)
    return service


class TestTopicSearchService:
    """TopicSearchService 테스트."""

    def test_init(self):
        """초기화 테스트."""
        service = TopicSearchService()
        assert service is not None
        assert len(service.topics) == 0

    def test_load_from_dict(self, topic_search):
        """dict 로드 테스트."""
        assert len(topic_search.topics) == 5
        assert topic_search.vectorizer is not None
        assert topic_search.tfidf_matrix is not None

    def test_search_ai(self, topic_search):
        """AI 검색 테스트."""
        results = topic_search.search("인공지능", top_k=3)

        assert len(results) > 0
        assert results[0]["fileName"] == "인공지능"
        assert "similarity" in results[0]
        # 유사도 임계값 조정 (TF-IDF 코사인 유사도는 보통 0.1~0.3 수준)
        assert results[0]["similarity"] > 0.1

    def test_search_with_domain_filter(self, topic_search):
        """도메인 필터 검색 테스트."""
        results = topic_search.search("AI", top_k=10, domain_filter="신기술")

        assert len(results) > 0
        for r in results:
            assert r["domain"] == "신기술"

    def test_search_no_results(self, topic_search):
        """결과 없는 검색 테스트."""
        results = topic_search.search("xyzabc123", top_k=10)
        assert len(results) == 0

    def test_find_similar_topics(self, topic_search):
        """유사 토픽 찾기 테스트."""
        results = topic_search.find_similar_topics(
            "1_Project/정보 관리 기술사/1_신기술/인공지능.md",
            top_k=3,
        )

        assert len(results) > 0
        # 머신러닝이 가장 유사해야 함
        assert results[0]["fileName"] == "머신러닝"

    def test_get_topic_by_path(self, topic_search):
        """경로로 토픽 찾기 테스트."""
        topic = topic_search.get_topic_by_path(
            "1_Project/정보 관리 기술사/1_신기술/인공지능.md"
        )

        assert topic is not None
        assert topic["fileName"] == "인공지능"

    def test_get_topic_by_path_not_found(self, topic_search):
        """없는 경로 테스트."""
        topic = topic_search.get_topic_by_path("없는/경로.md")
        assert topic is None

    def test_get_stats(self, topic_search):
        """통계 정보 테스트."""
        stats = topic_search.get_stats()

        assert stats["total_topics"] == 5
        assert "domain_counts" in stats
        assert stats["domain_counts"]["신기술"] == 2
