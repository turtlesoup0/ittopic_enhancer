import { useMemo } from 'react';
import { AlertCircle, CheckCircle, FileText } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import type { ValidationResult, MatchedReference } from '@/types/api';

interface ValidationPanelProps {
  validationResult?: ValidationResult;
  isLoading?: boolean;
}

export function ValidationPanel({ validationResult, isLoading }: ValidationPanelProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>검증 결과</CardTitle>
          <CardDescription>토픽 검증 중...</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="mb-4 h-12 w-12 animate-spin rounded-full border-4 border-primary border-t-transparent mx-auto" />
              <p className="text-sm text-muted-foreground">토픽을 분석하고 있습니다...</p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!validationResult) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>검증 결과</CardTitle>
          <CardDescription>검증할 토픽을 선택하세요.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-12">
            <div className="text-center text-muted-foreground">
              <FileText className="mb-4 h-12 w-12 mx-auto opacity-50" />
              <p>토픽을 선택하고 검증을 시작하세요.</p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  // 점수별 색상 및 레이블
  const scoreInfo = useMemo(() => {
    const score = validationResult.overall_score;
    if (score >= 0.8) {
      return { color: 'text-green-600', label: '우수', icon: CheckCircle };
    } else if (score >= 0.6) {
      return { color: 'text-yellow-600', label: '보통', icon: AlertCircle };
    } else {
      return { color: 'text-red-600', label: '미흡', icon: AlertCircle };
    }
  }, [validationResult.overall_score]);

  const ScoreIcon = scoreInfo.icon;

  // 우선순위별 그룹화
  const groupedGaps = useMemo(() => {
    const groups: Record<string, typeof validationResult.gaps> = {
      critical: [],
      high: [],
      medium: [],
      low: [],
    };
    validationResult.gaps.forEach((gap) => {
      const priority =
        gap.gap_type === 'missing_field' || gap.confidence < 0.5
          ? 'critical'
          : gap.gap_type === 'incomplete_definition' || gap.confidence < 0.7
          ? 'high'
          : gap.gap_type === 'missing_keywords'
          ? 'medium'
          : 'low';
      groups[priority].push(gap);
    });
    return groups;
  }, [validationResult.gaps]);

  const getPriorityColor = (priority: string): string => {
    switch (priority) {
      case 'critical':
        return 'text-red-600 bg-red-50 border-red-200 dark:text-red-400 dark:bg-red-950 dark:border-red-800';
      case 'high':
        return 'text-orange-600 bg-orange-50 border-orange-200 dark:text-orange-400 dark:bg-orange-950 dark:border-orange-800';
      case 'medium':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200 dark:text-yellow-400 dark:bg-yellow-950 dark:border-yellow-800';
      case 'low':
        return 'text-blue-600 bg-blue-50 border-blue-200 dark:text-blue-400 dark:bg-blue-950 dark:border-blue-800';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const getPriorityLabel = (priority: string): string => {
    switch (priority) {
      case 'critical':
        return '매우 중요';
      case 'high':
        return '중요';
      case 'medium':
        return '보통';
      case 'low':
        return '낮음';
      default:
        return priority;
    }
  };

  const getGapTypeLabel = (gapType: string): string => {
    switch (gapType) {
      case 'missing_field':
        return '필드 누락';
      case 'incomplete_definition':
        return '정의 불완전';
      case 'missing_keywords':
        return '키워드 부족';
      case 'outdated_content':
        return '내용 구식';
      case 'inaccurate_info':
        return '정보 부정확';
      default:
        return gapType;
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>검증 결과</CardTitle>
        <CardDescription>
          {validationResult.matched_references.length}개 참조 문서와 비교 완료
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="overview" className="space-y-4">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="overview">개요</TabsTrigger>
            <TabsTrigger value="gaps">보강 항목</TabsTrigger>
            <TabsTrigger value="references">참조 문서</TabsTrigger>
          </TabsList>

          {/* 개요 탭 */}
          <TabsContent value="overview" className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">종합 점수</p>
                <p className="text-3xl font-bold">{Math.round(validationResult.overall_score * 100)}점</p>
              </div>
              <div className={`flex items-center gap-2 ${scoreInfo.color}`}>
                <ScoreIcon className="h-8 w-8" />
                <span className="text-lg font-semibold">{scoreInfo.label}</span>
              </div>
            </div>

            <Progress value={validationResult.overall_score * 100} className="h-3" />

            <div className="grid grid-cols-3 gap-4">
              <div className="rounded-lg border p-4">
                <p className="text-xs text-muted-foreground">필드 완성도</p>
                <p className="text-xl font-bold">{Math.round(validationResult.field_completeness_score * 100)}%</p>
              </div>
              <div className="rounded-lg border p-4">
                <p className="text-xs text-muted-foreground">내용 정확도</p>
                <p className="text-xl font-bold">{Math.round(validationResult.content_accuracy_score * 100)}%</p>
              </div>
              <div className="rounded-lg border p-4">
                <p className="text-xs text-muted-foreground">참조 커버리지</p>
                <p className="text-xl font-bold">{Math.round(validationResult.reference_coverage_score * 100)}%</p>
              </div>
            </div>

            {/* 우선순위별 요약 */}
            <div className="space-y-2">
              <p className="text-sm font-medium">우선순위별 요약</p>
              {Object.entries(groupedGaps).map(([priority, gaps]) => (
                <div key={priority} className="flex items-center justify-between text-sm">
                  <span className="capitalize">{getPriorityLabel(priority)}</span>
                  <Badge className={getPriorityColor(priority)}>{gaps.length}개</Badge>
                </div>
              ))}
            </div>
          </TabsContent>

          {/* 보강 항목 탭 */}
          <TabsContent value="gaps" className="space-y-4">
            {validationResult.gaps.length === 0 ? (
              <div className="flex items-center justify-center py-8">
                <div className="text-center text-muted-foreground">
                  <CheckCircle className="mb-2 h-12 w-12 mx-auto text-green-500" />
                  <p>모든 항목이 완벽합니다!</p>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                {validationResult.gaps.map((gap, index) => (
                  <div key={index} className="rounded-lg border p-4">
                    <div className="mb-2 flex items-center justify-between">
                      <Badge className={getPriorityColor(
                        gap.gap_type === 'missing_field' || gap.confidence < 0.5
                          ? 'critical'
                          : gap.gap_type === 'incomplete_definition' || gap.confidence < 0.7
                          ? 'high'
                          : 'medium'
                      )}>
                        {getGapTypeLabel(gap.gap_type)}
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        신뢰도: {Math.round(gap.confidence * 100)}%
                      </span>
                    </div>
                    <p className="mb-2 font-medium">{gap.field_name}</p>
                    <div className="mb-2 rounded-md bg-muted p-3">
                      <p className="mb-1 text-xs text-muted-foreground">현재 내용:</p>
                      <p className="text-sm">{gap.current_value || '(비어있음)'}</p>
                    </div>
                    <div className="rounded-md bg-green-50 p-3 dark:bg-green-950">
                      <p className="mb-1 text-xs text-green-700 dark:text-green-300">제안:</p>
                      <p className="text-sm text-green-800 dark:text-green-200">{gap.suggested_value}</p>
                    </div>
                    {gap.reasoning && (
                      <div className="mt-2 rounded-md border border-blue-200 bg-blue-50 p-3 dark:border-blue-800 dark:bg-blue-950">
                        <p className="mb-1 text-xs text-blue-700 dark:text-blue-300">근거:</p>
                        <p className="text-sm text-blue-800 dark:text-blue-200">{gap.reasoning}</p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </TabsContent>

          {/* 참조 문서 탭 */}
          <TabsContent value="references" className="space-y-4">
            {validationResult.matched_references.length === 0 ? (
              <div className="flex items-center justify-center py-8">
                <p className="text-sm text-muted-foreground">매칭된 참조 문서가 없습니다.</p>
              </div>
            ) : (
              <div className="space-y-2">
                {validationResult.matched_references.map((ref: MatchedReference, index: number) => (
                  <div key={index} className="rounded-lg border p-4">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <p className="font-medium">{ref.title}</p>
                        <p className="text-xs text-muted-foreground mt-1">
                          {ref.source_type} • {ref.domain}
                        </p>
                        <div className="mt-2 rounded-md bg-muted p-2">
                          <p className="text-xs text-muted-foreground mb-1">관련 내용:</p>
                          <p className="text-sm line-clamp-3">{ref.relevant_snippet}</p>
                        </div>
                      </div>
                      <div className="ml-4 flex flex-col items-end gap-2">
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
            )}
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
