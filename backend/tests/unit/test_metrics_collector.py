"""Unit tests for MetricsCollector service."""

import time

import pytest

from app.core.metrics import (
    MetricsCollector,
    MetricsTimer,
    get_metrics_collector,
)

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def metrics_collector():
    """MetricsCollector fixture."""
    collector = MetricsCollector()
    # Clear any existing data
    with collector._lock:
        collector._keyword_metrics.clear()
        collector._reference_metrics.clear()
        collector._validation_metrics.clear()
        collector._performance_metrics.clear()
    return collector


# =============================================================================
# Metrics Recording Tests
# =============================================================================


class TestRecordMetrics:
    """Test metrics recording methods."""

    def test_record_keyword_relevance(self, metrics_collector):
        """Test recording keyword relevance metrics."""
        metrics_collector.record_keyword_relevance(
            precision=0.85,
            recall=0.75,
            f1_score=0.8,
            domain="SW",
        )

        assert len(metrics_collector._keyword_metrics) == 1

        metric = metrics_collector._keyword_metrics[0]
        assert metric.precision == 0.85
        assert metric.recall == 0.75
        assert metric.f1_score == 0.8
        assert metric.domain == "SW"

    def test_record_reference_discovery(self, metrics_collector):
        """Test recording reference discovery metrics."""
        metrics_collector.record_reference_discovery(
            discovery_rate=0.9,
            coverage_rate=0.7,
            avg_similarity_score=0.85,
            avg_trust_score=0.95,
            domain="SW",
        )

        assert len(metrics_collector._reference_metrics) == 1

        metric = metrics_collector._reference_metrics[0]
        assert metric.discovery_rate == 0.9
        assert metric.coverage_rate == 0.7
        assert metric.avg_similarity_score == 0.85
        assert metric.avg_trust_score == 0.95
        assert metric.domain == "SW"

    def test_record_validation_accuracy(self, metrics_collector):
        """Test recording validation accuracy metrics."""
        metrics_collector.record_validation_accuracy(
            accuracy=0.85,
            false_positive_rate=0.1,
            avg_validation_score=0.8,
            gap_distribution={"MISSING_FIELD": 2, "MISSING_KEYWORDS": 3},
        )

        assert len(metrics_collector._validation_metrics) == 1

        metric = metrics_collector._validation_metrics[0]
        assert metric.accuracy == 0.85
        assert metric.false_positive_rate == 0.1
        assert metric.avg_validation_score == 0.8
        assert metric.gap_distribution == {"MISSING_FIELD": 2, "MISSING_KEYWORDS": 3}

    def test_record_performance(self, metrics_collector):
        """Test recording performance metrics."""
        metrics_collector.record_performance(
            operation="validate_topic",
            duration_ms=150,
            success=True,
            metadata={"topic_id": "test_topic_1"},
        )

        assert len(metrics_collector._performance_metrics) == 1

        metric = metrics_collector._performance_metrics[0]
        assert metric.operation == "validate_topic"
        assert metric.duration_ms == 150
        assert metric.success is True
        assert metric.metadata == {"topic_id": "test_topic_1"}


# =============================================================================
# Metrics Summary Tests
# =============================================================================


class TestGetSummaries:
    """Test metrics summary methods."""

    def test_get_keyword_relevance_summary_empty(self, metrics_collector):
        """Test summary with no data."""
        summary = metrics_collector.get_keyword_summary()

        assert summary["total_keywords"] == 0
        assert summary["avg_precision"] == 0.0
        assert summary["avg_recall"] == 0.0
        assert summary["avg_f1_score"] == 0.0

    def test_get_keyword_relevance_summary_with_data(self, metrics_collector):
        """Test summary with keyword data."""
        # Record multiple metrics
        metrics_collector.record_keyword_relevance(0.9, 0.8, 0.85, "SW")
        metrics_collector.record_keyword_relevance(0.7, 0.7, 0.7, "SW")
        metrics_collector.record_keyword_relevance(0.8, 0.75, 0.775, "정보보안")

        summary = metrics_collector.get_keyword_summary()

        assert summary["total_keywords"] == 3
        assert summary["avg_precision"] == pytest.approx(0.8, 0.01)
        assert summary["avg_recall"] == pytest.approx(0.75, 0.01)
        assert summary["avg_f1_score"] == pytest.approx(0.775, 0.01)

    def test_get_reference_discovery_summary(self, metrics_collector):
        """Test reference discovery summary."""
        metrics_collector.record_reference_discovery(0.9, 0.8, 0.85, 0.95, "SW")
        metrics_collector.record_reference_discovery(0.6, 0.5, 0.7, 0.8, "SW")

        summary = metrics_collector.get_reference_summary()

        assert summary["total_references"] == 2
        assert summary["avg_discovery_rate"] == pytest.approx(0.75, 0.01)
        assert summary["avg_coverage_rate"] == pytest.approx(0.65, 0.01)

    def test_get_validation_accuracy_summary(self, metrics_collector):
        """Test validation accuracy summary."""
        metrics_collector.record_validation_accuracy(0.9, 0.1, 0.85, {"MISSING_FIELD": 1})
        metrics_collector.record_validation_accuracy(0.7, 0.3, 0.75, {"MISSING_KEYWORDS": 2})

        summary = metrics_collector.get_validation_summary()

        assert summary["total_validations"] == 2
        assert summary["avg_accuracy"] == pytest.approx(0.8, 0.01)

    def test_get_performance_summary(self, metrics_collector):
        """Test performance summary."""
        metrics_collector.record_performance("validate", 100, True)
        metrics_collector.record_performance("validate", 150, True)
        metrics_collector.record_performance("validate", 200, False)

        summary = metrics_collector.get_performance_summary()

        assert summary["total_records"] == 3
        assert summary["success_rate"] == pytest.approx(0.67, 0.01)
        assert summary["avg_duration_ms"] == pytest.approx(150, 0.01)


# =============================================================================
# Global Instance Tests
# =============================================================================


class TestGlobalInstance:
    """Test global metrics collector instance."""

    def test_get_metrics_collector_singleton(self):
        """Test that get_metrics_collector returns singleton."""
        collector1 = get_metrics_collector()
        collector2 = get_metrics_collector()

        assert collector1 is collector2


# =============================================================================
# MetricsTimer Tests
# =============================================================================


class TestMetricsTimer:
    """Test MetricsTimer context manager."""

    def test_metrics_timer_success(self, metrics_collector):
        """Test timer with successful operation."""
        with MetricsTimer(metrics_collector, "test_operation"):
            time.sleep(0.01)  # Simulate work

        summary = metrics_collector.get_performance_summary()
        assert summary["total_records"] >= 1
        # Last operation should be successful
        last_metric = metrics_collector._performance_metrics[-1]
        assert last_metric.operation == "test_operation"
        assert last_metric.success is True

    def test_metrics_timer_with_exception(self, metrics_collector):
        """Test timer with exception."""
        try:
            with MetricsTimer(metrics_collector, "failing_operation"):
                raise ValueError("Test error")
        except ValueError:
            pass

        summary = metrics_collector.get_performance_summary()
        assert summary["total_records"] >= 1
        # Last operation should have failed
        last_metric = metrics_collector._performance_metrics[-1]
        assert last_metric.operation == "failing_operation"
        assert last_metric.success is False


# =============================================================================
# Thread Safety Tests
# =============================================================================


class TestThreadSafety:
    """Test thread-safe operations."""

    def test_concurrent_metric_recording(self, metrics_collector):
        """Test concurrent metric recording is thread-safe."""
        import threading

        def record_metrics():
            for i in range(10):
                metrics_collector.record_keyword_relevance(0.8, 0.7, 0.75, "SW")

        threads = [threading.Thread(target=record_metrics) for _ in range(5)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # Should have 50 metrics (10 * 5 threads)
        assert len(metrics_collector._keyword_metrics) == 50


# =============================================================================
# Korean Language Tests
# =============================================================================


class TestKoreanLanguage:
    """Korean language support tests."""

    def test_korean_domain_recording(self, metrics_collector):
        """Test recording Korean domain names."""
        metrics_collector.record_keyword_relevance(0.85, 0.75, 0.8, domain="정보보안")

        assert len(metrics_collector._keyword_metrics) == 1
        assert metrics_collector._keyword_metrics[0].domain == "정보보안"

    def test_korean_gap_distribution(self, metrics_collector):
        """Test Korean gap type names."""
        metrics_collector.record_validation_accuracy(
            0.8,
            0.1,
            0.75,
            gap_distribution={"리드문_부족": 2, "키워드_누락": 3},
        )

        assert len(metrics_collector._validation_metrics) == 1
        assert metrics_collector._validation_metrics[0].gap_distribution == {
            "리드문_부족": 2,
            "키워드_누락": 3,
        }
