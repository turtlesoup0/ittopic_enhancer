"""Markdown document parser for .txt reference files."""
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def _strip_file_extension(name: str) -> str:
    """
    Strip file extension from name.

    Args:
        name: Filename with or without extension

    Returns:
        Name without extension
    """
    if "." in name:
        return name.rsplit(".", 1)[0]
    return name


class MarkdownParser:
    """Markdown document parser for .txt reference files.

    Parses Korean language markdown files from 서브노트_통합 directory.
    Extracts title, content, and metadata from header lines.
    """

    # Header metadata patterns
    HEADER_PATTERNS = {
        "instructor": "=== 강사:",
        "sheet": "=== 시트:",
        "domain": "=== 도메인:",
        "topic": "=== 토픽:",
        "keywords": "=== 키워드:",
    }

    def __init__(self):
        """Initialize markdown parser."""
        self.encoding_errors = "replace"

    def parse(self, file_path: str) -> dict:
        """
        Parse markdown file and extract text content.

        Args:
            file_path: Path to .txt markdown file

        Returns:
            Dictionary containing:
                - content: Full file text content
                - metadata: {title, instructor, domain, topic, keywords}
                - file_path: Absolute path string
                - file_name: Filename with extension

        Raises:
            FileNotFoundError: If file does not exist
            ValueError: If file is not a .txt file
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Markdown file not found: {file_path}")

        if path.suffix.lower() != ".txt":
            raise ValueError(f"File is not a .txt file: {file_path}")

        try:
            # Read file with UTF-8 encoding
            with open(path, "r", encoding="utf-8", errors=self.encoding_errors) as f:
                content = f.read()

            # Extract metadata from content
            metadata = self._extract_metadata(content)

            # Extract title (priority: first line > filename > "Untitled")
            title = self._extract_title(content, path.stem)
            metadata["title"] = title

            return {
                "content": content,
                "metadata": metadata,
                "file_path": str(path),
                "file_name": path.name,
            }

        except UnicodeDecodeError as e:
            logger.error(f"Failed to decode markdown file {file_path}: {e}")
            # Retry with error handling
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            metadata = self._extract_metadata(content)
            title = self._extract_title(content, path.stem)
            metadata["title"] = title
            return {
                "content": content,
                "metadata": metadata,
                "file_path": str(path),
                "file_name": path.name,
            }
        except Exception as e:
            logger.error(f"Failed to parse markdown file {file_path}: {e}")
            raise

    def _extract_title(self, content: str, fallback_name: str) -> str:
        """
        Extract title from content.

        Priority (per SPEC FR-003):
        1. First line starting with # (markdown heading, with # removed)
        2. Fallback name (filename without extension)
        3. "Untitled" if all else fails

        Args:
            content: File content
            fallback_name: Filename to use as fallback (extension will be stripped)

        Returns:
            Extracted title
        """
        lines = content.strip().split("\n") if content else []

        # Find first line starting with # (markdown heading)
        for line in lines:
            line = line.strip()
            if line and line.startswith("#"):
                return line.lstrip("#").strip()

        # Fallback to filename without extension
        if fallback_name:
            return _strip_file_extension(fallback_name)

        return "Untitled"

    def _extract_metadata(self, content: str) -> dict:
        """
        Extract metadata from header lines.

        Header format:
        === 강사: {instructor} ===
        === 시트: {sheet} ===
        === 도메인: {domain} ===
        === 토픽: {topic} ===
        === 키워드: {keywords} ===

        Args:
            content: File content

        Returns:
            Dictionary with metadata fields
        """
        metadata = {
            "instructor": "",
            "domain": "",
            "topic": "",
            "keywords": "",
        }

        lines = content.split("\n")

        for i, line in enumerate(lines):
            line_stripped = line.strip()

            # Check each header pattern
            if line_stripped.startswith(self.HEADER_PATTERNS["instructor"]):
                metadata["instructor"] = self._extract_header_value(line_stripped, self.HEADER_PATTERNS["instructor"])
            elif line_stripped.startswith(self.HEADER_PATTERNS["sheet"]):
                # Sheet is similar to domain, can be used as domain fallback
                sheet_value = self._extract_header_value(line_stripped, self.HEADER_PATTERNS["sheet"])
                if not metadata["domain"]:
                    metadata["domain"] = sheet_value
            elif line_stripped.startswith(self.HEADER_PATTERNS["domain"]):
                metadata["domain"] = self._extract_header_value(line_stripped, self.HEADER_PATTERNS["domain"])
            elif line_stripped.startswith(self.HEADER_PATTERNS["topic"]):
                # Topic may span multiple lines
                metadata["topic"] = self._extract_multiline_header(lines, i)
            elif line_stripped.startswith(self.HEADER_PATTERNS["keywords"]):
                # Keywords may span multiple lines
                metadata["keywords"] = self._extract_multiline_header(lines, i)

        return metadata

    def _extract_header_value(self, line: str, prefix: str) -> str:
        """
        Extract value from header line.

        Args:
            line: Header line
            prefix: Header prefix pattern

        Returns:
            Extracted value without === markers
        """
        # Remove prefix
        value = line[len(prefix):].strip()
        # Remove trailing ===
        if value.endswith("==="):
            value = value[:-3].strip()
        return value

    def _extract_multiline_header(self, lines: list, start_index: int) -> str:
        """
        Extract header value that may span multiple lines.

        Some headers like topic and keywords can have:
        === 토픽: XP
        (eXtreme Programming)
        Agile 방법론 ===

        Args:
            lines: All content lines
            start_index: Starting line index

        Returns:
            Combined multiline value
        """
        first_line = lines[start_index].strip()

        # Extract from first line
        for prefix in self.HEADER_PATTERNS.values():
            if first_line.startswith(prefix):
                value = first_line[len(prefix):].strip()
                break
        else:
            value = first_line

        # Check if value ends with === (single line header)
        if value.endswith("==="):
            return value[:-3].strip()

        # Multiline header: collect lines until ===
        parts = [value]
        for i in range(start_index + 1, len(lines)):
            line = lines[i].strip()
            # Check for new header first (before checking for ending ===)
            if line.startswith("===") and not line.endswith("==="):
                # New header starts, end current extraction
                break
            elif line.endswith("==="):
                # Last line of multiline header
                last_part = line[:-3].strip()
                if last_part:
                    parts.append(last_part)
                break
            elif line and not line.startswith("==="):
                # Middle line of multiline header
                parts.append(line)

        return " ".join(parts)
