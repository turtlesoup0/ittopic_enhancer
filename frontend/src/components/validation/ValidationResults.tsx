import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { AlertCircle, CheckCircle2, ChevronDown, ChevronUp } from 'lucide-react'
import { useState } from 'react'
import type { ValidationResult } from '@/types/api'

interface ValidationResultsProps {
  results: ValidationResult[]
}

export function ValidationResults({ results }: ValidationResultsProps) {
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set())

  const toggleExpand = (id: string) => {
    const newSet = new Set(expandedIds)
    if (newSet.has(id)) {
      newSet.delete(id)
    } else {
      newSet.add(id)
    }
    setExpandedIds(newSet)
  }

  const getScoreInfo = (score: number) => {
    if (score >= 0.8) {
      return { color: 'text-green-600', label: '우수', icon: CheckCircle2 }
    } else if (score >= 0.6) {
      return { color: 'text-yellow-600', label: '보통', icon: AlertCircle }
    } else {
      return { color: 'text-red-600', label: '미흡', icon: AlertCircle }
    }
  }

  const getGapTypeLabel = (gapType: string): string => {
    const labels: Record<string, string> = {
      missing_field: '필드 누락',
      incomplete_definition: '정의 불완전',
      missing_keywords: '키워드 부족',
      outdated_content: '내용 구식',
      inaccurate_info: '정보 부정확',
      insufficient_depth: '내용 부족',
      missing_example: '예제 누락',
      inconsistent_content: '내용 불일치',
    }
    return labels[gapType] || gapType
  }

  const getPriorityColor = (gap: any): string => {
    if (gap.gap_type === 'missing_field' || gap.confidence < 0.5) {
      return 'text-red-600 bg-red-50 border-red-200 dark:text-red-400 dark:bg-red-950 dark:border-red-800'
    } else if (gap.gap_type === 'incomplete_definition' || gap.confidence < 0.7) {
      return 'text-orange-600 bg-orange-50 border-orange-200 dark:text-orange-400 dark:bg-orange-950 dark:border-orange-800'
    } else if (gap.gap_type === 'missing_keywords') {
      return 'text-yellow-600 bg-yellow-50 border-yellow-200 dark:text-yellow-400 dark:bg-yellow-950 dark:border-yellow-800'
    }
    return 'text-blue-600 bg-blue-50 border-blue-200 dark:text-blue-400 dark:bg-blue-950 dark:border-blue-800'
  }

  return (
    <div className="space-y-4">
      {results.map((result) => {
        const scoreInfo = getScoreInfo(result.overall_score)
        const ScoreIcon = scoreInfo.icon
        const isExpanded = expandedIds.has(result.id)

        return (
          <Card key={result.id}>
            <CardHeader>
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <span>토픽 ID: {result.topic_id.slice(0, 8)}...</span>
                    <Badge className="bg-primary/10 text-primary">
                      {Math.round(result.overall_score * 100)}점
                    </Badge>
                  </CardTitle>
                  <CardDescription>
                    {result.matched_references.length}개 참조 문서와 비교
                  </CardDescription>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => toggleExpand(result.id)}
                >
                  {isExpanded ? (
                    <ChevronUp className="h-4 w-4" />
                  ) : (
                    <ChevronDown className="h-4 w-4" />
                  )}
                </Button>
              </div>
            </CardHeader>

            {isExpanded && (
              <CardContent className="space-y-4">
                {/* 점수 요약 */}
                <div className="grid grid-cols-3 gap-4">
                  <div className="rounded-lg border p-3">
                    <p className="text-xs text-muted-foreground">필드 완성도</p>
                    <p className="text-lg font-bold">
                      {Math.round(result.field_completeness_score * 100)}%
                    </p>
                  </div>
                  <div className="rounded-lg border p-3">
                    <p className="text-xs text-muted-foreground">내용 정확도</p>
                    <p className="text-lg font-bold">
                      {Math.round(result.content_accuracy_score * 100)}%
                    </p>
                  </div>
                  <div className="rounded-lg border p-3">
                    <p className="text-xs text-muted-foreground">참조 커버리지</p>
                    <p className="text-lg font-bold">
                      {Math.round(result.reference_coverage_score * 100)}%
                    </p>
                  </div>
                </div>

                {/* 보강 항목 */}
                {result.gaps.length > 0 && (
                  <div className="space-y-3">
                    <h4 className="font-medium">보강 항목 ({result.gaps.length})</h4>
                    <div className="space-y-2">
                      {result.gaps.map((gap, index) => (
                        <div key={index} className="rounded-lg border p-3">
                          <div className="mb-2 flex items-center justify-between">
                            <Badge className={getPriorityColor(gap)}>
                              {getGapTypeLabel(gap.gap_type)}
                            </Badge>
                            <span className="text-xs text-muted-foreground">
                              신뢰도: {Math.round(gap.confidence * 100)}%
                            </span>
                          </div>
                          <p className="mb-1 text-sm font-medium">{gap.field_name}</p>
                          {gap.current_value && (
                            <div className="mb-2 rounded bg-muted p-2">
                              <p className="mb-1 text-xs text-muted-foreground">현재:</p>
                              <p className="text-sm">{gap.current_value}</p>
                            </div>
                          )}
                          <div className="mb-2 rounded bg-green-50 p-2 dark:bg-green-950">
                            <p className="mb-1 text-xs text-green-700 dark:text-green-300">제안:</p>
                            <p className="text-sm text-green-800 dark:text-green-200">{gap.suggested_value}</p>
                          </div>
                          {gap.reasoning && (
                            <div className="rounded border border-blue-200 bg-blue-50 p-2 dark:border-blue-800 dark:bg-blue-950">
                              <p className="mb-1 text-xs text-blue-700 dark:text-blue-300">근거:</p>
                              <p className="text-sm text-blue-800 dark:text-blue-200">{gap.reasoning}</p>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* 참조 문서 */}
                {result.matched_references.length > 0 && (
                  <div className="space-y-3">
                    <h4 className="font-medium">참조 문서 ({result.matched_references.length})</h4>
                    <div className="space-y-2">
                      {result.matched_references.map((ref, index) => (
                        <div key={index} className="rounded-lg border p-3">
                          <div className="flex items-start justify-between">
                            <div className="flex-1">
                              <p className="font-medium">{ref.title}</p>
                              <p className="text-xs text-muted-foreground mt-1">
                                {ref.source_type} • {ref.domain}
                              </p>
                              <div className="mt-2 rounded bg-muted p-2">
                                <p className="text-xs text-muted-foreground mb-1">관련 내용:</p>
                                <p className="text-sm line-clamp-2">{ref.relevant_snippet}</p>
                              </div>
                            </div>
                            <div className="ml-4 flex flex-col gap-2">
                              <Badge variant="outline">
                                유사도: {Math.round(ref.similarity_score * 100)}%
                              </Badge>
                              <Badge variant="secondary">
                                신뢰도: {Math.round(ref.trust_score * 100)}%
                              </Badge>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* 제안 생성 버튼 */}
                <div className="flex justify-end pt-2">
                  <Button variant="outline" size="sm">
                    제안 생성
                  </Button>
                </div>
              </CardContent>
            )}
          </Card>
        )
      })}
    </div>
  )
}
