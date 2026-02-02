# P1-SCORING 구현 완료

## 변경 사항 요약

### 1. 정확도 점수: 문자열 길이 비교 → 시맨틱 유사도 기반 계산

**변경 전:**
```python
def _calculate_accuracy_score(self, topic: Topic, references: List[MatchedReference]) -> float:
    if not references:
        return 0.5
    top_scores = [r.similarity_score for r in references[:3]]
    return sum(top_scores) / len(top_scores)
```

**변경 후:**
```python
def _calculate_accuracy_score(self, topic: Topic, references: List[MatchedReference]) -> float:
    """
    Calculate content accuracy score based on semantic similarity.
    Score classification:
    - similarity < 0.6: 부정확 (inaccurate)
    - 0.6 <= similarity < 0.8: 개선 필요 (needs improvement)
    - similarity >= 0.8: 정확 (accurate)
    """
    if not references:
        return 0.5
    
    semantic_similarities = []
    for ref in references:  # ALL references, not just top 3
        similarity = self._calculate_semantic_similarity(
            topic.content.정의, ref.relevant_snippet
        )
        semantic_similarities.append(similarity)
    
    # Weighted scoring based on thresholds
    # ... (implementation details)
```

**주요 변경:**
- 임베딩 기반 시맨틱 유사도 계산 (`_calculate_semantic_similarity` 메서드 추가)
- 모든 매치된 참조 문서 고려 ([:3] 하드코딩 제거)
- 유사도 임계값 기반 정확도 분류:
  - < 0.6: 부정확
  - 0.6-0.8: 개선 필요
  - > 0.8: 정확

### 2. 커버리지 점수: 로그 스케일링 적용

**변경 전:**
```python
def _calculate_coverage_score(self, topic: Topic, references: List[MatchedReference]) -> float:
    if not references:
        return 0.0
    high_quality = sum(1 for r in references if r.similarity_score > 0.8)
    medium_quality = sum(1 for r in references if 0.7 < r.similarity_score <= 0.8)
    return min(1.0, (high_quality * 0.5 + medium_quality * 0.3))  # 선형 증가, 포화 문제
```

**변경 후:**
```python
def _calculate_coverage_score(self, topic: Topic, references: List[MatchedReference]) -> float:
    """
    Calculate reference coverage score using log scaling.
    Formula: coverage = min(1.0, 0.3 * log2(1 + high) + 0.2 * log2(1 + medium))
    """
    if not references:
        return 0.0
    
    log_weights = self.config.get_coverage_log_weights()
    high_weight = log_weights.get("high_quality_weight", 0.3)
    medium_weight = log_weights.get("medium_quality_weight", 0.2)
    
    high_quality = sum(1 for r in references if r.similarity_score > 0.8)
    medium_quality = sum(1 for r in references if 0.7 < r.similarity_score <= 0.8)
    
    # Log scaling prevents saturation
    log_high = math.log2(1 + high_quality) if high_quality > 0 else 0
    log_medium = math.log2(1 + medium_quality) if medium_quality > 0 else 0
    
    coverage = min(1.0, high_weight * log_high + medium_weight * log_medium)
    return coverage
```

**주요 변경:**
- 로그 스케일링 (`log2`) 적용으로 포화 방지
- 가중치를 `validation_rules.yaml`에서 동적으로 로드
- 다수의 참조 문서가 있어도 점수가 과도하게 높아지는 것 방지

### 3. 도메인별 검증 임계값 로드

**새로운 파일: `app/core/config_loader.py`**
```python
class ValidationConfigLoader:
    """Load and cache validation configuration from YAML."""
    
    def get_accuracy_thresholds(self) -> Dict[str, float]:
        """Get accuracy scoring thresholds."""
        return self._config.get("content_accuracy", {}).get("similarity", {})
    
    def get_coverage_log_weights(self) -> Dict[str, float]:
        """Get coverage log scaling weights."""
        return self._config.get("coverage_scoring", {}).get("log_scale", {})
    
    def get_domain_rules(self, domain: str) -> Dict[str, Any]:
        """Get domain-specific validation rules."""
        domain_rules = self._config.get("domain_specific_rules", {})
        return domain_rules.get(domain, domain_rules.get("default", {}))
```

**`validation_rules.yaml` 업데이트:**
```yaml
content_accuracy:
  similarity:
    inaccurate_threshold: 0.6
    needs_improvement_threshold: 0.8
    description: "임베딩 유사도 기반 정확도 분류"

coverage_scoring:
  log_scale:
    high_quality_weight: 0.3
    medium_quality_weight: 0.2
    formula: "min(1.0, 0.3 * log2(1 + high) + 0.2 * log2(1 + medium))"
    description: "로그 스케일링을 통한 포화 방지"
```

### 4. 이진 필드 점수 → 단계적 점수

**변경 전 (이진 점수):**
```python
# 해시태그
tag_score = 1.0 if topic.content.해시태그 else 0.5

# 암기
memory_score = 0.5 if topic.content.암기 else 0.0
```

**변경 후 (단계적 점수):**
```python
# 해시태그 - 단계적 점수: 0.0 -> 0.7 -> 1.0
if topic.content.해시태그:
    tag_len = len(topic.content.해시태그.strip())
    if tag_len > 0:
        tag_score = min(1.0, 0.7 + min(0.3, tag_len / 20))
    else:
        tag_score = 0.3  # 부분 점수
else:
    tag_score = 0.0

# 암기 - 단계적 점수: 0.0 -> 0.5 -> 1.0
if topic.content.암기:
    mem_len = len(topic.content.암기.strip())
    mem_min = 50
    if mem_len >= mem_min:
        mem_score = min(1.0, 0.5 + (mem_len - mem_min) / mem_min * 0.5)
    else:
        mem_score = max(0.0, mem_len / mem_min * 0.5)
else:
    mem_score = 0.0
```

## 파일 변경 목록

1. **新增**: `app/core/config_loader.py` - YAML 설정 로더
2. **新增**: `app/core/__init__.py` - 코어 모듈 초기화
3. **수정**: `app/services/validation/engine.py` - 검증 엔진
   - `_calculate_accuracy_score()`: 시맨틱 유사도 기반
   - `_calculate_coverage_score()`: 로그 스케일링 적용
   - `_calculate_field_completeness_score()`: 단계적 점수화
   - `_calculate_semantic_similarity()`: 새로운 임베딩 유사도 계산 메서드
   - `_check_content_accuracy()`: 모든 참조 문서 고려
4. **수정**: `config/validation_rules.yaml` - 새로운 점수 설정 추가

## 테스트 방법

```bash
# Python 3.13 가상환경 사용
.venv/bin/python -c "
from app.services.validation.engine import get_validation_engine
from app.core.config_loader import get_validation_config

# 엔진 초기화
engine = get_validation_engine()

# 설정 확인
config = get_validation_config()
print('Accuracy thresholds:', config.get_accuracy_thresholds())
print('Coverage weights:', config.get_coverage_log_weights())

# 메서드 확인
print('Has semantic_similarity method:', hasattr(engine, '_calculate_semantic_similarity'))
"
```

## 다음 단계

1. 단위 테스트 작성 (`tests/test_validation_engine.py`)
2. 통합 테스트로 실제 토픽과 참조 문서로 검증
3. 임계값 튜닝 (실제 데이터 기반)
4. LSP/Type 검증 통과 확인

---

**완료일자**: 2026-02-02
**작업**: P1-SCORING (정확도/커버리지 점수화 개선)
