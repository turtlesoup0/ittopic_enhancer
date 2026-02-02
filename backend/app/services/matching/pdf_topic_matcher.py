"""PDF and topic matching service.

복합어 보존 키워드 추출 및 동의어 확장 기능이 포함됨.
"""
import logging
from pathlib import Path
from typing import List, Dict, Optional

from app.services.parser.pdf_parser import PDFParser
from app.services.vector.topic_search import TopicSearchService
from app.services.matching.keyword_extractor import KeywordExtractor

logger = logging.getLogger(__name__)


class PDFTopicMatcher:
    """PDF와 토픽을 매칭하는 서비스."""

    # 기술사 도메인 키워드 패턴
    DOMAIN_PATTERNS = {
        "SW": ["SW", "소프트웨어", "요구공학", "아키텍처", "설계", "테스트"],
        "정보보안": ["SE", "보안", "암호", "해킹", "접근통제", "CIA"],
        "신기술": ["AI", "인공지능", "머신러닝", "딥러닝", "블록체인"],
        "네트워크": ["NW", "네트워크", "OSI", "TCP/IP", "라우터", "스위치"],
        "데이터베이스": ["DB", "데이터베이스", "SQL", "NoSQL", "ACID"],
        "경영/IT관리": ["프로젝트", "Agile", "Scrum", "관리", "기획"],
    }

    def __init__(
        self,
        topic_json_path: str,
        config_dir: Optional[str] = None,
        use_synonyms: bool = True,
        use_stopwords: bool = True,
    ):
        """
        매처 초기화.

        Args:
            topic_json_path: Obsidian JSON 파일 경로
            config_dir: 동의어/불용어 설정 디렉토리 (기본값: backend/config/)
            use_synonyms: 동의어 확장 사용 여부
            use_stopwords: 불용어 필터링 사용 여부
        """
        self.topic_service = TopicSearchService(topic_json_path)
        self.pdf_parser = PDFParser()
        self.keyword_extractor = KeywordExtractor(
            config_dir=config_dir,
            use_synonyms=use_synonyms,
            use_stopwords=use_stopwords,
        )

    def match_pdf_to_topics(
        self,
        pdf_path: str,
        top_k: int = 5,
    ) -> Dict:
        """
        PDF를 파싱하여 관련 토픽 찾기.

        Args:
            pdf_path: PDF 파일 경로
            top_k: 반환할 토픽 수

        Returns:
            매칭 결과
        """
        # PDF 파싱
        pdf_result = self.pdf_parser.parse(pdf_path)
        content = pdf_result["content"]

        # 키워드 추출 (복합어 보존 + 동의어 확장)
        keywords = self.keyword_extractor.extract_keywords(
            content,
            top_k=50,
        )

        # 여러 키워드로 검색하여 결과 집계
        topic_scores = {}
        for keyword in keywords[:10]:  # 상위 10개 키워드
            results = self.topic_service.search(keyword, top_k=top_k * 2)
            for topic in results:
                topic_path = topic["filePath"]
                if topic_path not in topic_scores:
                    topic_scores[topic_path] = {
                        "topic": topic,
                        "score": 0,
                        "matched_keywords": [],
                    }
                topic_scores[topic_path]["score"] += topic["similarity"]
                topic_scores[topic_path]["matched_keywords"].append(keyword)

        # 점수순 정렬
        sorted_topics = sorted(
            topic_scores.values(),
            key=lambda x: x["score"],
            reverse=True,
        )[:top_k]

        # 도메인 감지
        detected_domain = self._detect_domain(content, pdf_result["file_name"])

        return {
            "pdf_file": pdf_result["file_name"],
            "pdf_path": pdf_path,
            "detected_domain": detected_domain,
            "extracted_keywords": keywords[:10],
            "matched_topics": [
                {
                    "file_name": t["topic"]["fileName"],
                    "file_path": t["topic"]["filePath"],
                    "domain": t["topic"]["domain"],
                    "similarity": t["topic"]["similarity"],
                    "matched_keywords": t["matched_keywords"],
                }
                for t in sorted_topics
            ],
            "pdf_preview": content[:500] + "..." if len(content) > 500 else content,
        }

    def _extract_keywords(self, text: str) -> List[str]:
        """
        텍스트에서 키워드 추출 (레거시 메서드, 내부적으로 KeywordExtractor 사용).

        Args:
            text: 분석할 텍스트

        Returns:
            키워드 목록
        """
        return self.keyword_extractor.extract_keywords(text)

    def _detect_domain(self, content: str, file_name: str) -> str:
        """
        PDF 내용에서 도메인 감지.

        Args:
            content: PDF 내용
            file_name: 파일명

        Returns:
            감지된 도메인
        """
        # 파일명 우선 확인
        for domain, patterns in self.DOMAIN_PATTERNS.items():
            if any(pattern in file_name for pattern in patterns):
                return domain

        # 내용 기반 확인
        content_lower = content.lower()
        domain_scores = {}

        for domain, patterns in self.DOMAIN_PATTERNS.items():
            score = sum(content_lower.count(pattern.lower()) for pattern in patterns)
            domain_scores[domain] = score

        if domain_scores:
            return max(domain_scores, key=domain_scores.get)

        return "기타"

    def scan_and_match_directory(
        self,
        directory: str,
        pattern: str = "*.pdf",
        max_pdfs: int = 10,
    ) -> List[Dict]:
        """
        디렉토리의 PDF를 스캔하며 매칭.

        Args:
            directory: 스캔할 디렉토리
            pattern: 파일 패턴
            max_pdfs: 최대 처리 PDF 수

        Returns:
            매칭 결과 목록
        """
        dir_path = Path(directory)
        if not dir_path.exists():
            raise FileNotFoundError(f"디렉토리 없음: {directory}")

        pdf_files = list(dir_path.rglob(pattern))[:max_pdfs]

        results = []
        for pdf_file in pdf_files:
            try:
                result = self.match_pdf_to_topics(str(pdf_file))
                results.append(result)
                logger.info(f"매칭 완료: {pdf_file.name}")
            except Exception as e:
                logger.error(f"매칭 실패 {pdf_file.name}: {e}")
                results.append({
                    "pdf_file": pdf_file.name,
                    "error": str(e),
                })

        return results
