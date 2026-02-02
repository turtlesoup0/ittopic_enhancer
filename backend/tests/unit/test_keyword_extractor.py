"""Unit tests for KeywordExtractor module."""
import pytest
from pathlib import Path
from app.services.matching.keyword_extractor import KeywordExtractor, extract_keywords


class TestKeywordExtractor:
    """키워드 추출기 테스트."""

    @pytest.fixture
    def extractor(self, tmp_path):
        """KeywordExtractor fixture with test config."""
        # 테스트용 설정 파일 생성
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        # 테스트용 동의어 파일
        synonyms_data = {
            "네트워크": ["NW", "망", "network"],
            "TCP/IP": ["TCP IP", "TCPIP"],
            "REST API": ["RESTful API", "RESTful"],
            "데이터베이스": ["DB", "DBMS"],
        }

        synonyms_file = config_dir / "synonyms.yaml"
        import yaml
        with open(synonyms_file, "w", encoding="utf-8") as f:
            yaml.dump(synonyms_data, f, allow_unicode=True)

        # 테스트용 불용어 파일
        stopwords_data = {
            "korean_basic": ["이다", "있다", "하다"],
            "english_basic": ["the", "and", "is", "are"],
        }

        stopwords_file = config_dir / "stopwords.yaml"
        with open(stopwords_file, "w", encoding="utf-8") as f:
            yaml.dump(stopwords_data, f, allow_unicode=True)

        return KeywordExtractor(config_dir=str(config_dir))

    def test_extract_keywords_basic(self, extractor):
        """기본 키워드 추출 테스트."""
        text = """
        인공지능과 머신러닝은 데이터베이스 기술과 결합하여
        네트워크 보안 시스템을 개선한다. REST API를 통한
        통신은 TCP/IP 프로토콜을 사용한다.
        """

        keywords = extractor.extract_keywords(text, top_k=20)

        assert len(keywords) > 0
        # 중요 키워드 포함 확인
        text_lower = " ".join(keywords).lower()
        assert any(kw in text_lower for kw in ["인공지능", "머신러닝", "데이터베이스"])

    def test_compound_word_preservation(self, extractor):
        """복합어 보존 테스트 (TCP/IP, REST API 등)."""
        text = """
        TCP/IP 프로토콜은 OSI 7계층 모델을 따른다.
        REST API는 웹 서비스에서 널리 사용된다.
        NoSQL 데이터베이스는 비관계형 데이터 저장에 적합하다.
        CI/CD 파이프라인은 DevOps의 핵심이다.
        """

        keywords = extractor.extract_keywords(text, top_k=20)

        # 복합어가 분리되지 않고 유지되어야 함
        keyword_str = " ".join(keywords)

        # TCP/IP가 단일 키워드로 유지되어야 함
        assert "TCP/IP" in keyword_str or "tcp/ip" in keyword_str

        # REST API가 단일 키워드로 유지되어야 함
        assert "REST API" in keyword_str or "rest api" in keyword_str or "REST" in keyword_str

    def test_synonym_expansion(self, extractor):
        """동의어 확장 기능 테스트."""
        text = """
        네트워크 설정을 확인하세요. NW 연결 상태를 점검합니다.
        망 구성도를 검토하여 network 토폴로지를 설계합니다.
        """

        keywords = extractor.extract_keywords(text, top_k=30, use_synonyms=True)

        # 동의어 확장으로 인해 "네트워크"가 결과에 포함되어야 함
        keyword_str = " ".join(keywords).lower()
        # 원본 키워드 또는 동의어 중 하나가 있어야 함
        has_network = any(
            kw in keyword_str
            for kw in ["네트워크", "network", "nw", "망"]
        )
        assert has_network

    def test_stopword_filtering(self, extractor):
        """불용어 필터링 테스트."""
        text = """
        이것은 테스트입니다. 데이터베이스가 있다.
        the system is working and running.
        인공지능 기술이다.
        """

        # 불용어 필터링 사용
        keywords_with_filter = extractor.extract_keywords(
            text, top_k=20, use_stopwords=True
        )

        # 불용어가 제거되어야 함
        for kw in keywords_with_filter:
            assert kw.lower() not in ["이다", "있다", "하다", "the", "and", "is", "are"]

    def test_get_synonyms(self, extractor):
        """특정 키워드의 동의어 조회 테스트."""
        # "NW"의 동의어는 "네트워크"여야 함
        synonyms = extractor.get_synonyms("NW")
        assert "네트워크" in synonyms

        # "network"의 동의어는 "네트워크"여야 함
        synonyms = extractor.get_synonyms("network")
        assert "네트워크" in synonyms

    def test_normalize_keyword(self, extractor):
        """키워드 정규화 테스트."""
        # "NW"를 "네트워크"로 정규화
        normalized = extractor.normalize_keyword("NW")
        assert normalized == "네트워크"

        # "network"를 "네트워크"로 정규화
        normalized = extractor.normalize_keyword("network")
        assert normalized == "네트워크"

        # 동의어에 없는 키워드는 그대로 반환
        normalized = extractor.normalize_keyword("인공지능")
        assert normalized == "인공지능"

    def test_case_insensitive_matching(self, extractor):
        """대소문자 구분 없는 매칭 테스트."""
        text = """
        TCP/IP 통신과 rest api 호출을 확인합니다.
        Database 쿼리를 실행합니다.
        """

        keywords = extractor.extract_keywords(text, top_k=20)
        keyword_str = " ".join(keywords)

        # 대소문자와 관계없이 키워드가 추출되어야 함
        assert "TCP/IP" in keyword_str or "tcp/ip" in keyword_str
        assert any(api in keyword_str.lower() for api in ["rest", "api"])

    def test_empty_text(self, extractor):
        """빈 텍스트 처리 테스트."""
        keywords = extractor.extract_keywords("", top_k=10)
        assert keywords == []

    def test_korean_english_mixed(self, extractor):
        """한영 혼합 텍스트 처리 테스트."""
        text = """
        SW 아키텍처는 REST API와 GraphQL을 지원한다.
        DBMS는 SQL과 NoSQL을 모두 처리할 수 있다.
        DevOps 환경에서 CI/CD 파이프라인을 구축한다.
        """

        keywords = extractor.extract_keywords(text, top_k=20)

        # 한글과 영어 키워드가 모두 추출되어야 함
        assert len(keywords) > 0
        text_lower = " ".join(keywords).lower()

        # 한글 키워드 확인
        assert any(char in text_lower for char in "가나다라마바사")

        # 영어 키워드 확인
        assert any(char.isalpha() for char in text_lower)


class TestConvenienceFunctions:
    """편의 함수 테스트."""

    def test_extract_keywords_function(self, tmp_path):
        """extract_keywords 편의 함수 테스트."""
        # 기본 추출기 사용
        text = "인공지능과 머신러닝은 데이터베이스 기술을 활용한다."
        keywords = extract_keywords(text, top_k=10)

        assert len(keywords) > 0
        assert any("인공지능" in kw or "머신러닝" in kw for kw in keywords)
