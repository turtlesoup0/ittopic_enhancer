"""
Metrics collection module for ITPE Topic Enhancement System.

This module provides metrics collection for:
- Keyword relevance metrics (Precision, Recall, F1 Score)
- Reference discovery metrics (Discovery Rate, Coverage Rate)
- Validation accuracy metrics
- System performance metrics (Response times, Throughput)

Usage:
    from app.core.metrics import get_metrics_collector

    metrics = get_metrics_collector()
    metrics.record_keyword_relevance(precision=0.8, recall=0.75, f1=0.775)
    metrics.record_reference_discovery(discovery_rate=0.9, coverage_rate=0.7)
"""

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class KeywordMetrics:
    """키워드 관련성 메트릭."""

    precision: float  # 정밀도: 제안된 키워드 중 실제 관련 비율
    recall: float  # 재현율: 전체 관련 키워드 중 발견 비율
    f1_score: float  # F1 점수: 정밀도와 재현율의 조화 평균
    timestamp: datetime = field(default_factory=datetime.now)
    domain: str | None = None  # 도메인별 메트릭


@dataclass
class ReferenceMetrics:
    """참조 문서 발견 메트릭."""

    discovery_rate: float  # 매칭된 토픽 비율
    coverage_rate: float  # 상위 3개 이상 매칭 비율
    avg_similarity_score: float  # 평균 유사도 점수
    avg_trust_score: float  # 평균 신뢰 점수
    timestamp: datetime = field(default_factory=datetime.now)
    domain: str | None = None


@dataclass
class ValidationMetrics:
    """검증 정확도 메트릭."""

    accuracy: float  # 정확한 Gap 탐지 비율
    false_positive_rate: float  # 잘못된 Gap 탐지 비율
    avg_validation_score: float  # 평균 검증 점수
    gap_distribution: dict[str, int] = field(default_factory=dict)  # Gap 타입별 분포
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class PerformanceMetrics:
    """시스템 성능 메트릭."""

    operation: str  # 작업 유형 (matching, validation, llm_generation, etc.)
    duration_ms: float  # 소요 시간 (밀리초)
    success: bool  # 성공 여부
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)


class MetricsCollector:
    """
    메트릭 수집기.

    다음 메트릭을 수집하고 집계합니다:
    - 키워드 관련성 메트릭 (Precision/Recall/F1)
    - 참조 문서 발견 메트릭 (Discovery/Coverage Rate)
    - 검증 정확도 메트릭
    - 시스템 성능 메트릭

    Thread-safe implementation for concurrent operations.
    """

    def __init__(self):
        """메트릭 수집기 초기화."""
        self._lock = threading.Lock()

        # 메트릭 저장소
        self._keyword_metrics: list[KeywordMetrics] = []
        self._reference_metrics: list[ReferenceMetrics] = []
        self._validation_metrics: list[ValidationMetrics] = []
        self._performance_metrics: list[PerformanceMetrics] = []

        # 집계 메트릭
        self._operation_counts: dict[str, int] = defaultdict(int)
        self._operation_durations: dict[str, list[float]] = defaultdict(list)

        logger.info("metrics_collector_initialized")

    def record_keyword_relevance(
        self,
        precision: float,
        recall: float,
        f1_score: float,
        domain: str | None = None,
    ) -> None:
        """
        키워드 관련성 메트릭을 기록합니다.

        Args:
            precision: 정밀도 (0-1)
            recall: 재현율 (0-1)
            f1_score: F1 점수 (0-1)
            domain: 도메인 (선택)
        """
        with self._lock:
            metrics = KeywordMetrics(
                precision=precision,
                recall=recall,
                f1_score=f1_score,
                domain=domain,
            )
            self._keyword_metrics.append(metrics)

        logger.debug(
            "keyword_metrics_recorded",
            precision=precision,
            recall=recall,
            f1_score=f1_score,
            domain=domain,
        )

    def record_reference_discovery(
        self,
        discovery_rate: float,
        coverage_rate: float,
        avg_similarity_score: float,
        avg_trust_score: float,
        domain: str | None = None,
    ) -> None:
        """
        참조 문서 발견 메트릭을 기록합니다.

        Args:
            discovery_rate: 매칭된 토픽 비율 (0-1)
            coverage_rate: 상위 3개 이상 매칭 비율 (0-1)
            avg_similarity_score: 평균 유사도 점수 (0-1)
            avg_trust_score: 평균 신뢰 점수 (0-1)
            domain: 도메인 (선택)
        """
        with self._lock:
            metrics = ReferenceMetrics(
                discovery_rate=discovery_rate,
                coverage_rate=coverage_rate,
                avg_similarity_score=avg_similarity_score,
                avg_trust_score=avg_trust_score,
                domain=domain,
            )
            self._reference_metrics.append(metrics)

        logger.debug(
            "reference_metrics_recorded",
            discovery_rate=discovery_rate,
            coverage_rate=coverage_rate,
            domain=domain,
        )

    def record_validation_accuracy(
        self,
        accuracy: float,
        false_positive_rate: float,
        avg_validation_score: float,
        gap_distribution: dict[str, int] | None = None,
    ) -> None:
        """
        검증 정확도 메트릭을 기록합니다.

        Args:
            accuracy: 정확한 Gap 탐지 비율 (0-1)
            false_positive_rate: 잘못된 Gap 탐지 비율 (0-1)
            avg_validation_score: 평균 검증 점수 (0-1)
            gap_distribution: Gap 타입별 분포
        """
        with self._lock:
            metrics = ValidationMetrics(
                accuracy=accuracy,
                false_positive_rate=false_positive_rate,
                avg_validation_score=avg_validation_score,
                gap_distribution=gap_distribution or {},
            )
            self._validation_metrics.append(metrics)

        logger.debug(
            "validation_metrics_recorded",
            accuracy=accuracy,
            false_positive_rate=false_positive_rate,
        )

    def record_performance(
        self,
        operation: str,
        duration_ms: float,
        success: bool = True,
        metadata: dict | None = None,
    ) -> None:
        """
        성능 메트릭을 기록합니다.

        Args:
            operation: 작업 유형 (matching, validation, llm_generation, etc.)
            duration_ms: 소요 시간 (밀리초)
            success: 성공 여부
            metadata: 추가 메타데이터
        """
        with self._lock:
            metrics = PerformanceMetrics(
                operation=operation,
                duration_ms=duration_ms,
                success=success,
                metadata=metadata or {},
            )
            self._performance_metrics.append(metrics)

            # 집계 업데이트
            self._operation_counts[operation] += 1
            self._operation_durations[operation].append(duration_ms)

        logger.debug(
            "performance_metric_recorded",
            operation=operation,
            duration_ms=duration_ms,
            success=success,
        )

    def get_keyword_summary(self, domain: str | None = None) -> dict:
        """
        키워드 관련성 메트릭 요약을 반환합니다.

        Args:
            domain: 필터링할 도메인 (선택)

        Returns:
            메트릭 요약 (average precision, recall, f1_score)
        """
        with self._lock:
            metrics = self._keyword_metrics
            if domain:
                metrics = [m for m in metrics if m.domain == domain]

            if not metrics:
                return {
                    "total_keywords": 0,
                    "avg_precision": 0.0,
                    "avg_recall": 0.0,
                    "avg_f1_score": 0.0,
                }

            return {
                "total_keywords": len(metrics),
                "avg_precision": sum(m.precision for m in metrics) / len(metrics),
                "avg_recall": sum(m.recall for m in metrics) / len(metrics),
                "avg_f1_score": sum(m.f1_score for m in metrics) / len(metrics),
            }

    def get_reference_summary(self, domain: str | None = None) -> dict:
        """
        참조 문서 발견 메트릭 요약을 반환합니다.

        Args:
            domain: 필터링할 도메인 (선택)

        Returns:
            메트릭 요약 (average discovery_rate, coverage_rate, etc.)
        """
        with self._lock:
            metrics = self._reference_metrics
            if domain:
                metrics = [m for m in metrics if m.domain == domain]

            if not metrics:
                return {
                    "total_references": 0,
                    "avg_discovery_rate": 0.0,
                    "avg_coverage_rate": 0.0,
                    "avg_similarity_score": 0.0,
                    "avg_trust_score": 0.0,
                }

            return {
                "total_references": len(metrics),
                "avg_discovery_rate": sum(m.discovery_rate for m in metrics) / len(metrics),
                "avg_coverage_rate": sum(m.coverage_rate for m in metrics) / len(metrics),
                "avg_similarity_score": sum(m.avg_similarity_score for m in metrics) / len(metrics),
                "avg_trust_score": sum(m.avg_trust_score for m in metrics) / len(metrics),
            }

    def get_validation_summary(self) -> dict:
        """
        검증 정확도 메트릭 요약을 반환합니다.

        Returns:
            메트릭 요약 (average accuracy, false_positive_rate, etc.)
        """
        with self._lock:
            metrics = self._validation_metrics

            if not metrics:
                return {
                    "total_validations": 0,
                    "avg_accuracy": 0.0,
                    "avg_false_positive_rate": 0.0,
                    "avg_validation_score": 0.0,
                }

            # Gap 분포 집계
            gap_dist = defaultdict(int)
            for m in metrics:
                for gap_type, count in m.gap_distribution.items():
                    gap_dist[gap_type] += count

            return {
                "total_validations": len(metrics),
                "avg_accuracy": sum(m.accuracy for m in metrics) / len(metrics),
                "avg_false_positive_rate": sum(m.false_positive_rate for m in metrics)
                / len(metrics),
                "avg_validation_score": sum(m.avg_validation_score for m in metrics) / len(metrics),
                "gap_distribution": dict(gap_dist),
            }

    def get_performance_summary(self, operation: str | None = None) -> dict:
        """
        성능 메트릭 요약을 반환합니다.

        Args:
            operation: 필터링할 작업 유형 (선택)

        Returns:
            메트릭 요약 (P50, P95, P99 백분위 응답 시간, 처리량 등)
        """
        with self._lock:
            metrics = self._performance_metrics
            if operation:
                metrics = [m for m in metrics if m.operation == operation]

            if not metrics:
                return {
                    "total_records": 0,
                    "p50_ms": 0.0,
                    "p95_ms": 0.0,
                    "p99_ms": 0.0,
                    "avg_duration_ms": 0.0,
                    "success_rate": 1.0,
                }

            # 성공한 작업만 필터링 (백분위 계산용)
            successful = [m for m in metrics if m.success]

            if not successful:
                return {
                    "total_records": len(metrics),
                    "p50_ms": 0.0,
                    "p95_ms": 0.0,
                    "p99_ms": 0.0,
                    "avg_duration_ms": sum(m.duration_ms for m in metrics) / len(metrics),
                    "success_rate": 0.0,
                }

            durations = sorted(m.duration_ms for m in successful)

            # 백분위 계산
            def percentile(arr: list[float], p: float) -> float:
                k = (len(arr) - 1) * p
                f = int(k)
                c = f + 1 if f + 1 < len(arr) else f
                return arr[f] + (k - f) * (arr[c] - arr[f]) if c != f else arr[f]

            return {
                "total_records": len(metrics),
                "success_count": len(successful),
                "success_rate": len(successful) / len(metrics),
                "p50_ms": percentile(durations, 0.50),
                "p95_ms": percentile(durations, 0.95),
                "p99_ms": percentile(durations, 0.99),
                "avg_duration_ms": sum(m.duration_ms for m in metrics) / len(metrics),
                "min_ms": min(durations),
                "max_ms": max(durations),
            }

    def get_throughput(self, operation: str, window_seconds: int = 60) -> float:
        """
        처리량을 계산합니다 (초당 작업 수).

        Args:
            operation: 작업 유형
            window_seconds: 집계 윈도우 (초)

        Returns:
            초당 처리량
        """
        with self._lock:
            cutoff = datetime.now() - timedelta(seconds=window_seconds)
            recent = [
                m
                for m in self._performance_metrics
                if m.operation == operation and m.timestamp > cutoff
            ]

            if not recent:
                return 0.0

            return len(recent) / window_seconds

    def reset(self) -> None:
        """모든 메트릭을 초기화합니다."""
        with self._lock:
            self._keyword_metrics.clear()
            self._reference_metrics.clear()
            self._validation_metrics.clear()
            self._performance_metrics.clear()
            self._operation_counts.clear()
            self._operation_durations.clear()

        logger.info("metrics_reset")

    def get_all_summaries(self) -> dict:
        """
        모든 메트릭 요약을 반환합니다.

        Returns:
            모든 메트릭 카테고리의 요약
        """
        return {
            "keyword_relevance": self.get_keyword_summary(),
            "reference_discovery": self.get_reference_summary(),
            "validation_accuracy": self.get_validation_summary(),
            "system_performance": self.get_performance_summary(),
        }


class MetricsTimer:
    """
    성능 측정을 위한 컨텍스트 매니저.

    Usage:
        with MetricsTimer(metrics, "matching"):
            result = matching_service.find_references(topic)
    """

    def __init__(self, collector: MetricsCollector, operation: str, metadata: dict | None = None):
        """
        초기화.

        Args:
            collector: 메트릭 수집기
            operation: 작업 유형
            metadata: 추가 메타데이터
        """
        self.collector = collector
        self.operation = operation
        self.metadata = metadata or {}
        self.start_time = None
        self.success = True

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000
        self.success = exc_type is None

        self.collector.record_performance(
            operation=self.operation,
            duration_ms=duration_ms,
            success=self.success,
            metadata=self.metadata,
        )


# Global metrics collector instance
_metrics_collector: MetricsCollector | None = None
_lock = threading.Lock()


def get_metrics_collector() -> MetricsCollector:
    """
    전역 메트릭 수집기 인스턴스를 반환합니다.

    Returns:
        MetricsCollector 인스턴스
    """
    global _metrics_collector
    if _metrics_collector is None:
        with _lock:
            if _metrics_collector is None:
                _metrics_collector = MetricsCollector()
    return _metrics_collector


def record_keyword_metrics(
    true_positives: int,
    false_positives: int,
    false_negatives: int,
    domain: str | None = None,
) -> None:
    """
    TP/FP/FN 값으로부터 키워드 관련성 메트릭을 계산하고 기록합니다.

    Args:
        true_positives: 올바르게 제안된 키워드 수
        false_positives: 잘못 제안된 키워드 수
        false_negatives: 누락된 관련 키워드 수
        domain: 도메인 (선택)
    """
    precision = (
        true_positives / (true_positives + false_positives)
        if (true_positives + false_positives) > 0
        else 0.0
    )
    recall = (
        true_positives / (true_positives + false_negatives)
        if (true_positives + false_negatives) > 0
        else 0.0
    )
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    collector = get_metrics_collector()
    collector.record_keyword_relevance(
        precision=precision,
        recall=recall,
        f1_score=f1_score,
        domain=domain,
    )


def record_discovery_metrics(
    total_topics: int,
    matched_topics: int,
    high_quality_matches: int,  # 상위 3개 이상 매칭
    avg_similarity: float,
    avg_trust: float,
    domain: str | None = None,
) -> None:
    """
    참조 문서 발견 메트릭을 계산하고 기록합니다.

    Args:
        total_topics: 전체 토픽 수
        matched_topics: 매칭된 토픽 수
        high_quality_matches: 상위 3개 이상 매칭된 토픽 수
        avg_similarity: 평균 유사도 점수
        avg_trust: 평균 신뢰 점수
        domain: 도메인 (선택)
    """
    discovery_rate = matched_topics / total_topics if total_topics > 0 else 0.0
    coverage_rate = high_quality_matches / total_topics if total_topics > 0 else 0.0

    collector = get_metrics_collector()
    collector.record_reference_discovery(
        discovery_rate=discovery_rate,
        coverage_rate=coverage_rate,
        avg_similarity_score=avg_similarity,
        avg_trust_score=avg_trust,
        domain=domain,
    )
