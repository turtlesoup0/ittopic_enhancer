import { useEffect, useState, useMemo } from 'react'
import { Activity, CheckCircle, Clock, FileText, TrendingUp } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { topicsApi, validationApi } from '@/lib/api'
import { useToast } from '@/components/ui/use-toast'
import { StatsCard } from '@/components/dashboard/StatsCard'
import { CompletionChart } from '@/components/dashboard/CompletionChart'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import type { Topic, DomainStats, ValidationResult } from '@/types/api'

export function DashboardPage() {
  const { toast } = useToast()
  const [validationResults, setValidationResults] = useState<ValidationResult[]>([])

  // 토픽 데이터 조회
  const { data: topicsData, isLoading } = useQuery({
    queryKey: ['topics'],
    queryFn: async () => {
      const response = await topicsApi.list()
      return response.data
    },
    retry: 1,
  })

  const topics = topicsData?.topics || []

  // 통계 계산
  const statsData = useMemo(() => {
    return {
      totalTopics: topics.length,
      completedTopics: topics.filter((t) => {
        const completion = Object.values(t.completion).filter(Boolean).length
        return completion === 5
      }).length,
      validatedTopics: topics.filter((t) => t.validation_score !== undefined).length,
      overallCompletionRate: topics.length > 0
        ? Math.round(
            (topics.reduce((sum, topic) => {
              const completion = Object.values(topic.completion).filter(Boolean).length
              return sum + completion / 5
            }, 0) / topics.length) * 100
          )
        : 0,
    }
  }, [topics])

  // 도메인별 통계
  const domainStats = useMemo(() => {
    const stats: Record<string, { total: number; completed: number }> = {}

    topics.forEach((topic) => {
      const domain = topic.metadata.domain
      if (!stats[domain]) {
        stats[domain] = { total: 0, completed: 0 }
      }
      stats[domain].total++

      const completion = Object.values(topic.completion).filter(Boolean).length
      if (completion === 5) {
        stats[domain].completed++
      }
    })

    return Object.entries(stats).map(([domain, data]) => ({
      domain: domain as any,
      total_topics: data.total,
      completed_count: data.completed,
      completion_rate: Math.round((data.completed / data.total) * 100),
    }))
  }, [topics])

  // 최근 검증 목록
  const recentValidations = useMemo(() => {
    return topics
      .filter((t) => t.last_validated)
      .sort((a, b) => {
        const aDate = new Date(a.last_validated!)
        const bDate = new Date(b.last_validated!)
        return bDate.getTime() - aDate.getTime()
      })
      .slice(0, 5)
  }, [topics])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <div className="mb-4 h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent mx-auto" />
          <p className="text-sm text-muted-foreground">로딩 중...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div>
        <h2 className="text-3xl font-bold tracking-tight">대시보드</h2>
        <p className="text-muted-foreground">
          ITPE 토픽 검증 및 보강 제안 시스템 개요
        </p>
      </div>

      {/* 통계 카드 */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatsCard
          title="전체 토픽"
          value={statsData.totalTopics}
          description="등록된 토픽 수"
          icon={FileText}
        />
        <StatsCard
          title="완성된 토픽"
          value={statsData.completedTopics}
          description="모든 필드 완료"
          icon={CheckCircle}
          trend={{ value: statsData.overallCompletionRate, isPositive: true }}
        />
        <StatsCard
          title="검증된 토픽"
          value={statsData.validatedTopics}
          description="검증 완료"
          icon={Activity}
        />
        <StatsCard
          title="평균 완성률"
          value={`${statsData.overallCompletionRate}%`}
          description="전체 토픽 기준"
          icon={TrendingUp}
        />
      </div>

      {/* 차트 */}
      {domainStats.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>도메인별 현황</CardTitle>
            <CardDescription>도메인별 토픽 완성도 통계</CardDescription>
          </CardHeader>
          <CardContent>
            <CompletionChart data={domainStats} />
          </CardContent>
        </Card>
      )}

      {/* 최근 검증 */}
      <Card>
        <CardHeader>
          <CardTitle>최근 검증된 토픽</CardTitle>
          <CardDescription>최근 검증이 완료된 토픽 목록</CardDescription>
        </CardHeader>
        <CardContent>
          {recentValidations.length === 0 ? (
            <p className="text-center text-muted-foreground py-8">
              아직 검증된 토픽이 없습니다.
            </p>
          ) : (
            <div className="space-y-4">
              {recentValidations.map((topic) => (
                <div
                  key={topic.id}
                  className="flex items-center justify-between rounded-lg border p-4"
                >
                  <div className="flex-1">
                    <p className="font-medium">{topic.metadata.file_name}</p>
                    <p className="text-sm text-muted-foreground">
                      {topic.metadata.domain} • {topic.last_validated && new Date(topic.last_validated).toLocaleDateString('ko-KR')}
                    </p>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <p className="text-sm text-muted-foreground">완성도</p>
                      <Progress
                        value={
                          (Object.values(topic.completion).filter(Boolean).length / 5) * 100
                        }
                        className="h-2 w-24"
                      />
                    </div>
                    {topic.validation_score !== undefined && (
                      <Badge
                        variant={
                          topic.validation_score >= 0.8
                            ? 'default'
                            : topic.validation_score >= 0.6
                            ? 'secondary'
                            : 'destructive'
                        }
                      >
                        {Math.round(topic.validation_score * 100)}점
                      </Badge>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* 빠른 작업 */}
      <Card>
        <CardHeader>
          <CardTitle>빠른 작업</CardTitle>
          <CardDescription>자주 사용하는 기능으로 빠르게 이동</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-3">
          <a
            href="/topics"
            className="flex items-center gap-3 rounded-lg border p-4 transition-colors hover:bg-muted"
          >
            <FileText className="h-5 w-5 text-primary" />
            <div>
              <p className="font-medium">토픽 관리</p>
              <p className="text-sm text-muted-foreground">토픽 업로드 및 편집</p>
            </div>
          </a>
          <a
            href="/validation"
            className="flex items-center gap-3 rounded-lg border p-4 transition-colors hover:bg-muted"
          >
            <Activity className="h-5 w-5 text-primary" />
            <div>
              <p className="font-medium">검증 요청</p>
              <p className="text-sm text-muted-foreground">토픽 내용 검증</p>
            </div>
          </a>
          <a
            href="/proposals"
            className="flex items-center gap-3 rounded-lg border p-4 transition-colors hover:bg-muted"
          >
            <Clock className="h-5 w-5 text-primary" />
            <div>
              <p className="font-medium">제안 관리</p>
              <p className="text-sm text-muted-foreground">보강 제안 확인</p>
            </div>
          </a>
        </CardContent>
      </Card>
    </div>
  )
}
