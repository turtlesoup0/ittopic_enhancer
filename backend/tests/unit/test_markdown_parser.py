"""Unit tests for MarkdownParser."""
import pytest
from pathlib import Path
from app.services.parser.markdown_parser import MarkdownParser


class TestMarkdownParserInit:
    """MarkdownParser 초기화 테스트."""

    def test_init(self):
        """MarkdownParser 초기화 테스트."""
        parser = MarkdownParser()
        assert parser is not None
        assert parser.encoding_errors == "replace"


class TestMarkdownParserParse:
    """MarkdownParser 파싱 테스트."""

    @pytest.fixture
    def parser(self):
        """MarkdownParser 인스턴스 fixture."""
        return MarkdownParser()

    @pytest.fixture
    def sample_markdown_file(self, tmp_path):
        """샘플 마크다운 파일 fixture."""
        markdown_file = tmp_path / "0105_양_XP_eXtreme_Programming.txt"
        content = """=== 강사: 양재모 ===
=== 시트: SW ===
=== 도메인: SW ===
=== 토픽: XP
(eXtreme Programming) ===
=== 키워드: 5대 핵심 가치
(용단의피존)
(절) 구리반승리
12가지 실천사항
(개관구환) ===

[정의] 짧은 주기의 반복을 통해 요구사항을 신속히 대응, 고품질의 SW를 빠르게 전달하는 Agile개발방법론
[등장배경]
1.RUP의 산출물 부담과 신속한 개발의 어려움
2.Time to Market 실현과 Products의 적시 배포
[핵심가치] (용단의피존)
1. 용기 : 고객 요구 사항 능동 대처
2. 단순성 : 부가기능 불필요한 구조/알고리즘 배제
3. 의사소통 : 개발자, 관리자, 고객간의 원활한 의사 소통
4. 피드백 : 지속적인 테스트, 반복 결함 수정, 빠른 피드백
5. 존중 : 상호 존중
"""
        markdown_file.write_text(content, encoding="utf-8")
        return str(markdown_file)

    @pytest.fixture
    def minimal_markdown_file(self, tmp_path):
        """최소 내용 마크다운 파일 fixture."""
        markdown_file = tmp_path / "minimal.txt"
        markdown_file.write_text("Simple content", encoding="utf-8")
        return str(markdown_file)

    @pytest.fixture
    def empty_markdown_file(self, tmp_path):
        """빈 마크다운 파일 fixture."""
        markdown_file = tmp_path / "empty.txt"
        markdown_file.write_text("", encoding="utf-8")
        return str(markdown_file)

    def test_parse_valid_markdown_file(self, parser, sample_markdown_file):
        """유효한 마크다운 파일 파싱 테스트."""
        result = parser.parse(sample_markdown_file)

        # 결과 구조 검증
        assert "content" in result
        assert "metadata" in result
        assert "file_path" in result
        assert "file_name" in result

        # 콘텐츠 검증
        assert isinstance(result["content"], str)
        assert len(result["content"]) > 0
        # 한글 텍스트 보존 확인
        assert "정의" in result["content"]
        assert "Agile개발방법론" in result["content"]

        # 메타데이터 검증
        assert isinstance(result["metadata"], dict)
        assert "title" in result["metadata"]
        assert "instructor" in result["metadata"]
        assert "domain" in result["metadata"]

        # 헤더 메타데이터 값 검증
        assert result["metadata"]["instructor"] == "양재모"
        assert result["metadata"]["domain"] == "SW"

        # 파일 정보 검증
        assert result["file_path"] == sample_markdown_file
        assert result["file_name"] == "0105_양_XP_eXtreme_Programming.txt"

    def test_parse_nonexistent_file(self, parser):
        """존재하지 않는 파일 파싱 테스트."""
        with pytest.raises(FileNotFoundError):
            parser.parse("/nonexistent/file.txt")

    def test_parse_non_txt_file(self, parser, tmp_path):
        """.txt가 아닌 파일 파싱 테스트."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("Not a markdown")

        with pytest.raises(ValueError, match="File is not a .txt file"):
            parser.parse(str(pdf_file))

    def test_parse_minimal_content(self, parser, minimal_markdown_file):
        """최소 내용 파일 파싱 테스트."""
        result = parser.parse(minimal_markdown_file)

        assert result["content"] == "Simple content"
        # 헤더가 없는 경우 파일명에서 타이틀 추출
        assert result["metadata"]["title"] == "minimal"

    def test_parse_empty_file(self, parser, empty_markdown_file):
        """빈 파일 파싱 테스트."""
        result = parser.parse(empty_markdown_file)

        assert result["content"] == ""
        # 빈 파일인 경우 파일명을 타이틀로 사용
        assert result["metadata"]["title"] == "empty"

    def test_korean_text_preservation(self, parser, tmp_path):
        """한글 텍스트 보존 테스트."""
        markdown_file = tmp_path / "korean_test.txt"
        korean_content = """=== 강사: 테스트 강사 ===
=== 도메인: SW ===

[정의] 한글 테스트입니다
[특징] 특수문자: 가나다라마바사아자차카타파하
"""
        markdown_file.write_text(korean_content, encoding="utf-8")

        result = parser.parse(str(markdown_file))

        # 한글이 정확히 보존되는지 확인
        assert "테스트 강사" == result["metadata"]["instructor"]
        assert "한글 테스트입니다" in result["content"]
        assert "가나다라마바사아자차카타파하" in result["content"]

    def test_metadata_extraction(self, parser, sample_markdown_file):
        """메타데이터 추출 테스트."""
        result = parser.parse(sample_markdown_file)

        # 헤더 메타데이터 추출 확인
        assert result["metadata"]["instructor"] == "양재모"
        assert result["metadata"]["domain"] == "SW"
        # 토픽은 여러 줄에 걸쳐 있을 수 있음
        assert "XP" in result["metadata"]["topic"]
        assert "eXtreme Programming" in result["metadata"]["topic"]
        # 키워드는 여러 줄에 걸쳐 있을 수 있음
        assert "5대 핵심 가치" in result["metadata"]["keywords"]

    def test_title_extraction_from_content(self, parser, tmp_path):
        """콘텐츠 첫 번째 줄에서 타이틀 추출 테스트."""
        markdown_file = tmp_path / "title_test.txt"
        content = """# First Level Heading
This is content
"""
        markdown_file.write_text(content, encoding="utf-8")

        result = parser.parse(str(markdown_file))

        # # 제거된 첫 번째 줄이 타이틀
        assert result["metadata"]["title"] == "First Level Heading"

    def test_title_fallback_to_filename(self, parser, minimal_markdown_file):
        """타이틀이 없는 경우 파일명 사용 테스트."""
        result = parser.parse(minimal_markdown_file)
        assert result["metadata"]["title"] == "minimal"

    def test_utf8_encoding_handling(self, parser, tmp_path):
        """UTF-8 인코딩 처리 테스트."""
        markdown_file = tmp_path / "utf8_test.txt"
        # 다양한 유니코드 문자 포함
        content = """=== 강사: 👨‍🏫 테스트 ===
=== 도메인: SW ===

[정의] 이모지: 🎉 🔥 ⭐
한글: 가나다라
특수문자: @#$%^&*()
"""
        markdown_file.write_text(content, encoding="utf-8")

        result = parser.parse(str(markdown_file))

        # 이모지와 특수문자가 정확히 보존되는지 확인
        assert "🎉" in result["content"]
        assert "🔥" in result["content"]
        assert "가나다라" in result["content"]


class TestMarkdownParserExtractionMethods:
    """MarkdownParser 내부 추출 메서드 테스트."""

    @pytest.fixture
    def parser(self):
        """MarkdownParser 인스턴스 fixture."""
        return MarkdownParser()

    def test_extract_title_from_header(self, parser):
        """헤더에서 타이틀 추출 테스트."""
        content = "# Title\n\nContent here"
        title = parser._extract_title(content, "fallback.txt")
        assert title == "Title"

    def test_extract_title_from_first_line(self, parser):
        """첫 번째 줄에서 타이틀 추출 테스트 (마크다운 헤딩인 경우)."""
        content = "# First line\nSecond line"
        title = parser._extract_title(content, "fallback.txt")
        assert title == "First line"

    def test_extract_title_fallback(self, parser):
        """타이틀 추출 실패 시 fallback 테스트."""
        content = ""
        title = parser._extract_title(content, "test_file.txt")
        assert title == "test_file"

    def test_extract_metadata_from_headers(self, parser):
        """헤더에서 메타데이터 추출 테스트."""
        content = """=== 강사: 테스트 강사 ===
=== 시트: SW ===
=== 도메인: 정보보안 ===
=== 토픽: 테스트 주제 ===
=== 키워드: 키워드1
키워드2 ===

Content here
"""
        metadata = parser._extract_metadata(content)

        assert metadata["instructor"] == "테스트 강사"
        assert metadata["domain"] == "정보보안"
        assert "테스트 주제" in metadata["topic"]
        assert "키워드1" in metadata["keywords"]
        assert "키워드2" in metadata["keywords"]

    def test_extract_metadata_no_headers(self, parser):
        """헤더가 없는 경우 메타데이터 추출 테스트."""
        content = "Just content\nNo headers"
        metadata = parser._extract_metadata(content)

        # 기본값 반환 확인
        assert metadata["instructor"] == ""
        assert metadata["domain"] == ""
        assert metadata["topic"] == ""
        assert metadata["keywords"] == ""


class TestMarkdownParserEdgeCases:
    """MarkdownParser 엣지 케이스 테스트."""

    @pytest.fixture
    def parser(self):
        """MarkdownParser 인스턴스 fixture."""
        return MarkdownParser()

    def test_multiline_topic_extraction(self, parser, tmp_path):
        """여러 줄에 걸친 토픽 추출 테스트."""
        markdown_file = tmp_path / "multiline_topic.txt"
        content = """=== 강사: 테스트 ===
=== 토픽: XP
(eXtreme Programming)
Agile 방법론 ===

Content
"""
        markdown_file.write_text(content, encoding="utf-8")

        result = parser.parse(str(markdown_file))

        # 여러 줄의 토픽이 모두 추출되는지 확인
        assert "XP" in result["metadata"]["topic"]
        assert "eXtreme Programming" in result["metadata"]["topic"]
        assert "Agile 방법론" in result["metadata"]["topic"]

    def test_bullet_points_preserved(self, parser, tmp_path):
        """불릿 포인트 보존 테스트."""
        markdown_file = tmp_path / "bullets.txt"
        content = """=== 강사: 테스트 ===

- 항목 1
- 항목 2
- 항목 3
"""
        markdown_file.write_text(content, encoding="utf-8")

        result = parser.parse(str(markdown_file))

        # 불릿 포인트가 콘텐츠에 포함되는지 확인
        assert "- 항목 1" in result["content"]
        assert "- 항목 2" in result["content"]
        assert "- 항목 3" in result["content"]

    def test_definition_sections_preserved(self, parser, tmp_path):
        """정의 섹션 보존 테스트."""
        markdown_file = tmp_path / "definitions.txt"
        content = """=== 강사: 테스트 ===

[정의] 이것은 정의입니다
[특징] 이것은 특징입니다
[등장배경] 이것은 배경입니다
"""
        markdown_file.write_text(content, encoding="utf-8")

        result = parser.parse(str(markdown_file))

        # 정의 섹션들이 콘텐츠에 포함되는지 확인
        assert "[정의]" in result["content"]
        assert "[특징]" in result["content"]
        assert "[등장배경]" in result["content"]
        assert "이것은 정의입니다" in result["content"]

    def test_header_with_new_header_interrupting_multiline(self, parser, tmp_path):
        """멀티라인 헤더 종료 패턴 테스트."""
        markdown_file = tmp_path / "multiline_close.txt"
        content = """=== 토픽: First topic
Partial content
===

Content continues
"""
        markdown_file.write_text(content, encoding="utf-8")

        result = parser.parse(str(markdown_file))

        # 멀티라인 헤더가 ===로 종료되는지 확인
        assert "First topic" in result["metadata"]["topic"]
        assert "Partial content" in result["metadata"]["topic"]

    def test_title_untitled_fallback(self, parser):
        """타이틀 추출 실패 시 'Untitled' 반환 테스트."""
        # 빈 콘텐츠와 빈 fallback
        title = parser._extract_title("", "")
        assert title == "Untitled"

    def test_metadata_edge_case_no_matching_prefix(self, parser, tmp_path):
        """메타데이터 추출 시 일치하는 접두사가 없는 경우 테스트."""
        markdown_file = tmp_path / "no_prefix.txt"
        content = "Just content without headers"
        markdown_file.write_text(content, encoding="utf-8")

        result = parser.parse(str(markdown_file))

        # 빈 메타데이터 값 확인
        assert result["metadata"]["instructor"] == ""
        assert result["metadata"]["domain"] == ""
        assert result["metadata"]["topic"] == ""
        assert result["metadata"]["keywords"] == ""
