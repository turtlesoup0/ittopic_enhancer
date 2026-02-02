"""Configuration loader for validation rules."""
from typing import Dict, Any, Optional
import yaml
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class ValidationConfigLoader:
    """Load and cache validation configuration from YAML."""

    _instance: Optional["ValidationConfigLoader"] = None
    _config: Optional[Dict[str, Any]] = None

    def __new__(cls, config_path: str | None = None) -> "ValidationConfigLoader":
        """Singleton pattern to avoid loading config multiple times."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize(config_path)
        return cls._instance

    def _initialize(self, config_path: str | None = None) -> None:
        """Initialize configuration loader.

        Args:
            config_path: Path to validation_rules.yaml. If None, uses default path.
        """
        if config_path is None:
            # Default path: project root / config / validation_rules.yaml
            project_root = Path(__file__).parent.parent.parent.parent
            config_path = str(project_root / "config" / "validation_rules.yaml")

        self._config_path = Path(config_path)
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from YAML file."""
        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f)
            logger.info(f"Loaded validation config from {self._config_path}")
        except FileNotFoundError:
            logger.warning(f"Config file not found: {self._config_path}, using defaults")
            self._config = self._get_default_config()
        except yaml.YAMLError as e:
            logger.error(f"Failed to parse config file: {e}")
            self._config = self._get_default_config()

    def reload(self) -> None:
        """Reload configuration from file."""
        self._load_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration when file is not available."""
        return {
            "field_completeness": {
                "리드문": {"min_length": 30, "max_length": 200},
                "정의": {"min_length": 50, "max_length": 500},
                "키워드": {"min_count": 3, "max_count": 10},
                "해시태그": {"min_count": 1},
                "암기": {"min_length": 50},
            },
            "content_accuracy": {
                "reference_match": {"threshold": 0.7},
                "similarity": {
                    "inaccurate_threshold": 0.6,
                    "needs_improvement_threshold": 0.8,
                },
            },
            "quality_scoring": {
                "weights": {
                    "field_completeness": 0.3,
                    "content_accuracy": 0.4,
                    "reference_coverage": 0.2,
                    "technical_depth": 0.1,
                },
                "thresholds": {
                    "excellent": 0.9,
                    "good": 0.75,
                    "acceptable": 0.6,
                    "needs_improvement": 0.4,
                    "poor": 0.0,
                },
            },
            "coverage_scoring": {
                "log_scale": {
                    "high_quality_weight": 0.3,
                    "medium_quality_weight": 0.2,
                },
            },
            "domain_specific_rules": {
                "default": {
                    "required_elements": [],
                    "technical_depth": "중간",
                },
            },
        }

    def get_field_completeness_rules(self, field_name: str) -> Dict[str, Any]:
        """Get field-specific completeness rules.

        Args:
            field_name: Field name (리드문, 정의, 키워드, etc.)

        Returns:
            Dictionary with min_length, max_length, min_count, etc.
        """
        if self._config is None:
            return {}
        return self._config.get("field_completeness", {}).get(field_name, {})

    def get_accuracy_thresholds(self) -> Dict[str, float]:
        """Get accuracy scoring thresholds.

        Returns:
            Dictionary with inaccurate_threshold and needs_improvement_threshold.
        """
        if self._config is None:
            return {"inaccurate_threshold": 0.6, "needs_improvement_threshold": 0.8}
        return (
            self._config
            .get("content_accuracy", {})
            .get("similarity", {})
        )

    def get_quality_weights(self) -> Dict[str, float]:
        """Get quality scoring weights.

        Returns:
            Dictionary with field_completeness, content_accuracy, reference_coverage, technical_depth weights.
        """
        if self._config is None:
            return {
                "field_completeness": 0.3,
                "content_accuracy": 0.4,
                "reference_coverage": 0.2,
                "technical_depth": 0.1,
            }
        return self._config.get("quality_scoring", {}).get("weights", {})

    def get_coverage_log_weights(self) -> Dict[str, float]:
        """Get coverage log scaling weights.

        Returns:
            Dictionary with high_quality_weight and medium_quality_weight.
        """
        if self._config is None:
            return {"high_quality_weight": 0.3, "medium_quality_weight": 0.2}
        return (
            self._config
            .get("coverage_scoring", {})
            .get("log_scale", {})
        )

    def get_domain_rules(self, domain: str) -> Dict[str, Any]:
        """Get domain-specific validation rules.

        Args:
            domain: Domain name (네트워크, 정보보안, SW공학, 데이터베이스, 신기술)

        Returns:
            Dictionary with required_elements, technical_depth, etc.
        """
        if self._config is None:
            return {}
        domain_rules = self._config.get("domain_specific_rules", {})
        return domain_rules.get(domain, domain_rules.get("default", {}))

    def get_field_lengths(self) -> Dict[str, int]:
        """Get minimum field lengths for completeness check.

        Returns:
            Dictionary mapping field names to minimum lengths.
        """
        if self._config is None:
            return {"리드문": 30, "정의": 50}
        return {
            "리드문": self._config
            .get("field_completeness", {})
            .get("리드문", {})
            .get("min_length", 30),
            "정의": self._config
            .get("field_completeness", {})
            .get("정의", {})
            .get("min_length", 50),
        }

    def get_min_keyword_count(self) -> int:
        """Get minimum keyword count.

        Returns:
            Minimum number of keywords required.
        """
        if self._config is None:
            return 3
        return (
            self._config
            .get("field_completeness", {})
            .get("키워드", {})
            .get("min_count", 3)
        )

    def get_quality_thresholds(self) -> Dict[str, float]:
        """Get quality score thresholds.

        Returns:
            Dictionary with excellent, good, acceptable, needs_improvement, poor thresholds.
        """
        if self._config is None:
            return {"excellent": 0.9, "good": 0.75, "acceptable": 0.6, "needs_improvement": 0.4, "poor": 0.0}
        return self._config.get("quality_scoring", {}).get("thresholds", {})


# Global config loader instance
_config_loader: Optional[ValidationConfigLoader] = None


def get_validation_config() -> ValidationConfigLoader:
    """Get or create global validation config loader instance.

    Returns:
        ValidationConfigLoader instance
    """
    global _config_loader
    if _config_loader is None:
        _config_loader = ValidationConfigLoader()
    return _config_loader
