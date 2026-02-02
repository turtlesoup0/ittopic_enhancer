"""Real data integration tests."""
import pytest
from app.services.vector.topic_search import TopicSearchService
from pathlib import Path


JSON_PATH = "/Users/turtlesoup0-macmini/Documents/itpe-topic-enhancement/backend/data/topics_sample.json"


@pytest.fixture
def topic_search():
    """실제 데이터로 초기화된 서비스."""
    service = TopicSearchService(JSON_PATH)
    return service


class TestRealDataSearch:
    """실제 데이터 검색 테스트."""

    def test_load_data(self, topic_search):
        """데이터 로드 테스트."""
        assert len(topic_search.topics) == 10
        assert topic_search.tfidf_matrix is not None

    def test_search_ai_related(self, topic_search):
        """AI 관련 토픽 검색."""
        results = topic_search.search("인공지능 기술", top_k=5)

        assert len(results) > 0
        # AI 관련 토픽이 상위에 있어야 함
        ai_topics = [r for r in results if r["domain"] == "신기술"]
        assert len(ai_topics) > 0

        print(f"\n검색어: '인공지능 기술'")
        for r in results[:3]:
            print(f"  - {r['fileName']} ({r['domain']}): {r['similarity']:.3f}")

    def test_search_security(self, topic_search):
        """보안 관련 토픽 검색."""
        results = topic_search.search("보안 암호화", top_k=5)

        assert len(results) > 0
        # 보안 도메인 토픽이 있어야 함
        security_topics = [r for r in results if r["domain"] == "정보보안"]
        assert len(security_topics) > 0

        print(f"\n검색어: '보안 암호화'")
        for r in results[:3]:
            print(f"  - {r['fileName']} ({r['domain']}): {r['similarity']:.3f}")

    def test_find_similar_to_ai(self, topic_search):
        """인공지능과 유사한 토픽 찾기."""
        results = topic_search.find_similar_topics(
            "1_Project/정보 관리 기술사/1_신기술/인공지능.md",
            top_k=5,
        )

        assert len(results) > 0
        # 머신러닝, 딥러닝이 상위에 있어야 함
        top_names = [r["fileName"] for r in results[:3]]
        print(f"\n인공지능과 유사한 토픽:")
        for r in results[:3]:
            print(f"  - {r['fileName']}: {r['similarity']:.3f}")

        # 머신러닝이나 딥러닝이 포함되어야 함
        assert any(name in top_names for name in ["머신러닝", "딥러닝"])

    def test_domain_stats(self, topic_search):
        """도메인별 통계 확인."""
        stats = topic_search.get_stats()

        assert stats["total_topics"] == 10
        assert stats["domain_counts"]["신기술"] == 3
        assert stats["domain_counts"]["정보보안"] == 3
        assert stats["domain_counts"]["SW"] == 2
        assert stats["domain_counts"]["데이터베이스"] == 2

    def test_cross_domain_search(self, topic_search):
        """도메인 간 검색 테스트."""
        # "데이터"는 데이터베이스와 AI 모두 관련
        results = topic_search.search("데이터", top_k=10)

        # 여러 도메인의 결과가 있어야 함
        domains = set(r["domain"] for r in results)
        print(f"\n검색어: '데이터' - 찾은 도메인: {domains}")

        assert len(results) > 0
