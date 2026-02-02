"""Unit tests for PDFParser."""
import pytest
from pathlib import Path
from app.services.parser.pdf_parser import PDFParser


class TestPDFParser:
    """PDFParser 단위 테스트."""

    def test_init(self, pdf_parser):
        """PDFParser 초기화 테스트."""
        assert pdf_parser is not None
        assert pdf_parser.encoding_errors == "ignore"

    def test_parse_nonexistent_file(self, pdf_parser):
        """존재하지 않는 파일 파싱 테스트."""
        with pytest.raises(FileNotFoundError):
            pdf_parser.parse("/nonexistent/file.pdf")

    def test_parse_non_pdf_file(self, pdf_parser, tmp_path):
        """PDF가 아닌 파일 파싱 테스트."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("Not a PDF")

        with pytest.raises(ValueError, match="File is not a PDF"):
            pdf_parser.parse(str(txt_file))

    def test_is_searchable_nonexistent_file(self, pdf_parser):
        """존재하지 않는 파일 검색 가능성 테스트."""
        result = pdf_parser.is_searchable("/nonexistent/file.pdf")
        assert result is False

    def test_extract_by_keywords_nonexistent_file(self, pdf_parser):
        """존재하지 않는 파일 키워드 추출 테스트."""
        result = pdf_parser.extract_by_keywords("/nonexistent/file.pdf", ["test"])
        # 에러가 발생해도 빈 결과 반환
        assert isinstance(result, dict)
        assert "test" in result


class TestPDFParserIntegration:
    """PDFParser 통합 테스트 (실제 PDF 필요)."""

    @pytest.mark.skipif(
        not Path("/Users/turtlesoup0-macmini/Library/CloudStorage/MYBOX-sjco1/공유 폴더/공유받은 폴더/FB21기 수업자료").exists(),
        reason="FB21 경로에 접근할 수 없음"
    )
    def test_parse_fb21_pdf(self, pdf_parser, fb21_sample_files):
        """FB21 PDF 파일 파싱 테스트."""
        if not fb21_sample_files:
            pytest.skip("샘플 PDF 파일 없음")

        for pdf_path in fb21_sample_files[:1]:  # 첫 번째 파일만 테스트
            result = pdf_parser.parse(pdf_path)

            # 결과 구조 검증
            assert "content" in result
            assert "metadata" in result
            assert "file_path" in result
            assert "file_name" in result

            # 콘텐츠 검증
            assert isinstance(result["content"], str)
            assert len(result["content"]) > 0

            # 메타데이터 검증
            assert isinstance(result["metadata"], dict)
            assert "pages" in result["metadata"]
            assert result["metadata"]["pages"] > 0

    @pytest.mark.skipif(
        not Path("/Users/turtlesoup0-macmini/Library/CloudStorage/MYBOX-sjco1/공유 폴더/공유받은 폴더/FB21기 수업자료").exists(),
        reason="FB21 경로에 접근할 수 없음"
    )
    def test_is_searchable_fb21_pdf(self, pdf_parser, fb21_sample_files):
        """FB21 PDF 검색 가능성 테스트."""
        if not fb21_sample_files:
            pytest.skip("샘플 PDF 파일 없음")

        for pdf_path in fb21_sample_files[:1]:
            result = pdf_parser.is_searchable(pdf_path)
            assert isinstance(result, bool)

    @pytest.mark.skipif(
        not Path("/Users/turtlesoup0-macmini/Library/CloudStorage/MYBOX-sjco1/공유 폴더/공유받은 폴더/FB21기 수업자료").exists(),
        reason="FB21 경로에 접근할 수 없음"
    )
    def test_extract_by_keywords_fb21_pdf(self, pdf_parser, fb21_sample_files, domain_mapping):
        """FB21 PDF 키워드 추출 테스트."""
        if not fb21_sample_files:
            pytest.skip("샘플 PDF 파일 없음")

        # 첫 번째 도메인의 키워드로 테스트
        first_domain_keywords = list(domain_mapping.values())[0]
        keywords = first_domain_keywords[:2]  # 2개 키워드만

        for pdf_path in fb21_sample_files[:1]:
            result = pdf_parser.extract_by_keywords(pdf_path, keywords)

            # 결과 구조 검증
            assert isinstance(result, dict)
            for keyword in keywords:
                assert keyword in result

    def test_format_table(self, pdf_parser):
        """테이블 포맷팅 테스트."""
        sample_table = [
            ["Header1", "Header2", "Header3"],
            ["Row1Col1", "Row1Col2", "Row1Col3"],
            ["Row2Col1", None, "Row2Col3"],
        ]

        result = pdf_parser._format_table(sample_table)

        assert isinstance(result, str)
        assert "Header1" in result
        assert "Header2" in result
        assert "Row1Col1" in result
        # None은 빈 문자열로 처리
        assert " | " in result

    def test_format_empty_table(self, pdf_parser):
        """빈 테이블 포맷팅 테스트."""
        result = pdf_parser._format_table([])
        assert result == ""

    def test_format_none_table(self, pdf_parser):
        """None 테이블 포맷팅 테스트."""
        result = pdf_parser._format_table(None)
        assert result == ""
