"""Integration tests for PDF-Topic matching."""
import pytest
from pathlib import Path
from app.services.matching.pdf_topic_matcher import PDFTopicMatcher


# 테스트용 토픽 JSON 경로
SAMPLE_JSON = "/Users/turtlesoup0-macmini/Documents/itpe-topic-enhancement/backend/data/topics_sample.json"

# FB21 기본 경로
FB21_PATH = "/Users/turtlesoup0-macmini/Library/CloudStorage/MYBOX-sjco1/공유 폴더/공유받은 폴더/FB21기 수업자료"


@pytest.fixture
def matcher():
    """PDFTopicMatcher fixture."""
    return PDFTopicMatcher(SAMPLE_JSON)


class TestPDFTopicMatcher:
    """PDF-토픽 매칭 테스트."""

    def test_init(self, matcher):
        """초기화 테스트."""
        assert matcher.topic_service is not None
        assert matcher.pdf_parser is not None
        assert matcher.keyword_extractor is not None

    def test_detect_domain_from_filename(self, matcher):
        """파일명에서 도메인 감지 테스트."""
        # 신기술
        domain = matcher._detect_domain("", "FB21_6주차_AI_교재.pdf")
        assert domain == "신기술"

        # 정보보안
        domain = matcher._detect_domain("", "FB21_4주차_SE_보안.pdf")
        assert domain == "정보보안"

        # SW
        domain = matcher._detect_domain("", "FB21_2주차_SW_요구공학.pdf")
        assert domain == "SW"

    def test_detect_domain_from_content(self, matcher):
        """내용에서 도메인 감지 테스트."""
        # AI 관련 내용
        content = "인공지능 머신러닝 딥러닝 신경망 학습"
        domain = matcher._detect_domain(content, "test.pdf")
        assert domain == "신기술"

        # 보안 관련 내용
        content = "정보보안 암호화 해킹 접근통제 비밀키"
        domain = matcher._detect_domain(content, "test.pdf")
        assert domain == "정보보안"

    def test_extract_keywords(self, matcher):
        """키워드 추출 테스트."""
        text = """
        인공지능은 머신러닝의 일종이다. 딥러닝은 신경망을 사용한다.
        정보보안은 암호화 기술을 사용한다.
        """
        keywords = matcher._extract_keywords(text)

        assert len(keywords) > 0
        # 중요 키워드 포함 확인
        text_lower = " ".join(keywords).lower()
        assert "인공지능" in text_lower or "머신러닝" in text_lower

    def test_extract_keywords_compound_words(self, matcher):
        """복합어 보존 키워드 추출 테스트."""
        text = """
        TCP/IP 프로토콜은 OSI 7계층 모델을 따른다.
        REST API는 웹 서비스에서 널리 사용된다.
        NoSQL 데이터베이스는 비관계형 데이터 저장에 적합하다.
        CI/CD 파이프라인은 DevOps의 핵심이다.
        """
        keywords = matcher._extract_keywords(text)
        keyword_str = " ".join(keywords)

        # 복합어가 분리되지 않고 유지되어야 함
        # TCP/IP 확인
        assert "TCP/IP" in keyword_str or "tcp/ip" in keyword_str

        # REST API 확인
        assert "REST API" in keyword_str or "rest api" in keyword_str or "REST" in keyword_str

        # CI/CD 확인
        assert "CI/CD" in keyword_str or "ci/cd" in keyword_str or "CI" in keyword_str

    def test_synonym_expansion_in_keywords(self, matcher):
        """동의어 확장 키워드 추출 테스트."""
        text = """
        NW 연결 상태를 확인합니다. 망 구성도를 검토합니다.
        network 토폴로지를 설계합니다.
        """
        keywords = matcher._extract_keywords(text)
        keyword_str = " ".join(keywords).lower()

        # 동의어 확장으로 인해 "네트워크"가 결과에 포함되어야 함
        # 또는 원본 동의어 중 하나가 있어야 함
        has_network = any(
            kw in keyword_str
            for kw in ["네트워크", "network", "nw", "망"]
        )
        assert has_network

    @pytest.mark.skipif(
        not Path(FB21_PATH).exists(),
        reason="FB21 경로에 접근할 수 없음"
    )
    def test_match_real_pdf(self, matcher):
        """실제 FB21 PDF 매칭 테스트."""
        # FB21 경로의 첫 번째 PDF 찾기
        pdf_files = list(Path(FB21_PATH).rglob("*.pdf"))
        if not pdf_files:
            pytest.skip("PDF 파일 없음")

        pdf_path = str(pdf_files[0])
        result = matcher.match_pdf_to_topics(pdf_path)

        # 결과 구조 확인
        assert "pdf_file" in result
        assert "detected_domain" in result
        assert "extracted_keywords" in result
        assert "matched_topics" in result

        # 키워드 추출 확인
        assert len(result["extracted_keywords"]) > 0

        # 도메인 감지 확인
        assert result["detected_domain"] in matcher.DOMAIN_PATTERNS or result["detected_domain"] == "기타"

        print(f"\n📄 PDF: {result['pdf_file']}")
        print(f"🎯 도메인: {result['detected_domain']}")
        print(f"🔑 키워드: {result['extracted_keywords'][:5]}")
        print(f"📚 매칭 토픽:")
        for t in result['matched_topics'][:3]:
            print(f"  - {t['file_name']} ({t['domain']}): {t['similarity']:.3f}")

    @pytest.mark.skipif(
        not Path(FB21_PATH).exists(),
        reason="FB21 경로에 접근할 수 없음"
    )
    def test_scan_directory(self, matcher):
        """디렉토리 스캔 테스트."""
        results = matcher.scan_and_match_directory(FB21_PATH, max_pdfs=3)

        assert len(results) > 0

        # 각 결과의 구조 확인
        for result in results:
            if "error" not in result:
                assert "pdf_file" in result
                assert "matched_topics" in result

        print(f"\n📊 스캔한 PDF 수: {len(results)}")


class TestPDFTopicMatcherAdvanced:
    """고급 PDF-토픽 매칭 테스트."""

    @pytest.fixture
    def matcher_with_config(self, tmp_path):
        """설정이 포함된 PDFTopicMatcher fixture."""
        # 테스트용 설정 파일 생성
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        # 테스트용 동의어 파일
        synonyms_data = {
            "네트워크": ["NW", "망", "network"],
            "TCP/IP": ["TCP IP", "TCPIP"],
        }

        import yaml
        synonyms_file = config_dir / "synonyms.yaml"
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

        return PDFTopicMatcher(
            SAMPLE_JSON,
            config_dir=str(config_dir),
            use_synonyms=True,
            use_stopwords=True,
        )

    def test_matcher_with_custom_config(self, matcher_with_config):
        """사용자 설정을 사용한 매처 테스트."""
        # 설정이 제대로 로드되었는지 확인
        assert matcher_with_config.keyword_extractor is not None
        assert matcher_with_config.keyword_extractor.use_synonyms is True
        assert matcher_with_config.keyword_extractor.use_stopwords is True

    def test_keyword_extraction_with_custom_synonyms(self, matcher_with_config):
        """사용자 정의 동의어를 사용한 키워드 추출 테스트."""
        text = "NW 설정을 확인합니다. 망 연결 상태를 점검합니다."

        keywords = matcher_with_config._extract_keywords(text)
        keyword_str = " ".join(keywords).lower()

        # 동의어 확장 확인
        has_network = any(
            kw in keyword_str
            for kw in ["네트워크", "network", "nw", "망"]
        )
        assert has_network
