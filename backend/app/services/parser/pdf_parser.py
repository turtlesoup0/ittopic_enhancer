"""PDF document parser."""
import pdfplumber
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class PDFParser:
    """PDF document parser using pdfplumber."""

    def __init__(self):
        """Initialize PDF parser."""
        self.encoding_errors = "ignore"

    def parse(self, file_path: str) -> dict:
        """
        Parse PDF file and extract text content.

        Args:
            file_path: Path to PDF file

        Returns:
            Dictionary containing parsed content and metadata
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        if not path.suffix.lower() == ".pdf":
            raise ValueError(f"File is not a PDF: {file_path}")

        content_parts = []
        metadata = {
            "title": path.stem,
            "pages": 0,
            "author": None,
            "created": None,
        }

        try:
            with pdfplumber.open(path) as pdf:
                # Extract metadata
                if pdf.metadata:
                    metadata["author"] = pdf.metadata.get("Author")
                    metadata["created"] = pdf.metadata.get("CreationDate")
                    metadata["title"] = pdf.metadata.get("Title", path.stem)

                metadata["pages"] = len(pdf.pages)

                # Extract text from each page
                for i, page in enumerate(pdf.pages):
                    try:
                        text = page.extract_text()
                        if text:
                            content_parts.append(f"--- Page {i + 1} ---\n{text}")
                    except Exception as e:
                        logger.warning(f"Failed to extract page {i + 1}: {e}")
                        continue

                # Extract tables if present
                tables_text = self._extract_tables(pdf)
                if tables_text:
                    content_parts.append("\n--- Tables ---\n")
                    content_parts.append(tables_text)

        except Exception as e:
            logger.error(f"Failed to parse PDF {file_path}: {e}")
            raise

        return {
            "content": "\n\n".join(content_parts),
            "metadata": metadata,
            "file_path": str(path),
            "file_name": path.name,
        }

    def _extract_tables(self, pdf) -> str:
        """Extract tables from PDF."""
        tables_parts = []

        for i, page in enumerate(pdf.pages):
            try:
                tables = page.extract_tables()
                if tables:
                    for j, table in enumerate(tables):
                        table_text = self._format_table(table)
                        tables_parts.append(f"Table {j + 1} (Page {i + 1}):\n{table_text}")
            except Exception as e:
                logger.debug(f"Failed to extract tables from page {i + 1}: {e}")
                continue

        return "\n\n".join(tables_parts)

    def _format_table(self, table: list) -> str:
        """Format table data as text."""
        if not table:
            return ""

        rows = []
        for row in table:
            row_text = " | ".join(str(cell) if cell else "" for cell in row)
            rows.append(row_text)

        return "\n".join(rows)

    def extract_by_keywords(self, file_path: str, keywords: list[str]) -> dict[str, str]:
        """
        Extract content sections based on keywords.

        Args:
            file_path: Path to PDF file
            keywords: List of keywords to search for

        Returns:
            Dictionary mapping keywords to extracted content
        """
        path = Path(file_path)
        results = {keyword: [] for keyword in keywords}

        try:
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        for keyword in keywords:
                            if keyword.lower() in text.lower():
                                results[keyword].append(text)

        except Exception as e:
            logger.error(f"Failed to extract by keywords: {e}")

        return {k: "\n\n".join(v) for k, v in results.items()}

    def is_searchable(self, file_path: str) -> bool:
        """Check if PDF contains searchable text."""
        path = Path(file_path)

        try:
            with pdfplumber.open(path) as pdf:
                if not pdf.pages:
                    return False

                first_page = pdf.pages[0]
                text = first_page.extract_text()

                # If we got meaningful text, it's searchable
                return bool(text and len(text.strip()) > 50)

        except Exception:
            return False
