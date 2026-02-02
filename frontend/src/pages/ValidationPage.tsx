import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Play, RefreshCw, CheckCircle2, XCircle, Clock } from 'lucide-react'
import { topicsApi, validationApi } from '@/lib/api'
import { useToast } from '@/components/ui/use-toast'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { ValidationProgress } from '@/components/validation/ValidationProgress'
import { ValidationResults } from '@/components/validation/ValidationResults'
import { getDomainColor } from '@/lib/utils'
import type { Topic, ValidationTaskStatus } from '@/types/api'

export function ValidationPage() {
  const { toast } = useToast()

  // 상태 관리
  const [selectedTopicIds, setSelectedTopicIds] = useState<Set<string>>(new Set())
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null)
  const [taskStatus, setTaskStatus] = useState<ValidationTaskStatus | null>(null)
  const [completedResults, setCompletedResults] = useState<any[]>([])

  // 토픽 목록 조회
  const { data: topicsData, isLoading } = useQuery({
    queryKey: ['topics'],
    queryFn: async () => {
      const response = await topicsApi.list()
      return response.data
    },
  })

  const topics = topicsData?.topics || []

  // 태스크 상태 폴링
  useEffect(() => {
    if (!currentTaskId) return

    const pollStatus = async () => {
      try {
        const response = await validationApi.getStatus(currentTaskId)
        const status = response.data

        setTaskStatus(status)

        if (status.status === 'completed') {
          // 결과 조회
          const resultsResponse = await validationApi.getResult(currentTaskId)
          setCompletedResults(resultsResponse.data)
          setCurrentTaskId(null)

          toast({
            title: '검증 완료',
            description: `${status.total}개 토픽 검증이 완료되었습니다.`,
          })
        } else if (status.status === 'failed') {
          setCurrentTaskId(null)
          toast({
            variant: 'destructive',
            title: '검증 실패',
            description: status.error || '검증 중 오류가 발생했습니다.',
          })
        }
      } catch (error) {
        console.error('Failed to poll status:', error)
      }
    }

    pollStatus()
    const interval = setInterval(pollStatus, 2000)

    return () => clearInterval(interval)
  }, [currentTaskId, toast])

  // 검증 시작 핸들러
  const handleStartValidation = async () => {
    if (selectedTopicIds.size === 0) {
      toast({
        variant: 'destructive',
        title: '토픽 미선택',
        description: '검증할 토픽을 선택해주세요.',
      })
      return
    }

    try {
      const response = await validationApi.create({
        topic_ids: Array.from(selectedTopicIds),
      })
      setCurrentTaskId(response.data.task_id)
      setTaskStatus({
        task_id: response.data.task_id,
        status: 'queued',
        progress: 0,
        total: selectedTopicIds.size,
        current: 0,
      })
      setSelectedTopicIds(new Set())
    } catch (error: any) {
      toast({
        variant: 'destructive',
        title: '검증 시작 실패',
        description: error.message,
      })
    }
  }

  // 전체 선택 토글
  const toggleSelectAll = () => {
    if (selectedTopicIds.size === topics.length) {
      setSelectedTopicIds(new Set())
    } else {
      setSelectedTopicIds(new Set(topics.map((t) => t.id)))
    }
  }

  // 개별 선택 토글
  const toggleSelectTopic = (topicId: string) => {
    const newSet = new Set(selectedTopicIds)
    if (newSet.has(topicId)) {
      newSet.delete(topicId)
    } else {
      newSet.add(topicId)
    }
    setSelectedTopicIds(newSet)
  }

  // 완성도 계산
  const calculateCompletionRate = (completion: any) => {
    const fields = Object.values(completion)
    const completed = fields.filter(Boolean).length
    return Math.round((completed / fields.length) * 100)
  }

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div>
        <h2 className="text-3xl font-bold tracking-tight">검증</h2>
        <p className="text-muted-foreground">
          토픽 내용을 참조 문서와 비교하여 검증
        </p>
      </div>

      {/* 진행 상황 */}
      {(taskStatus || completedResults.length > 0) && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              {taskStatus?.status === 'processing' || taskStatus?.status === 'queued' ? (
                <>
                  <RefreshCw className="h-5 w-5 animate-spin" />
                  검증 진행 중
                </>
              ) : (
                <>
                  <CheckCircle2 className="h-5 w-5 text-green-500" />
                  검증 완료
                </>
              )}
            </CardTitle>
            <CardDescription>
              {taskStatus?.status === 'processing' || taskStatus?.status === 'queued'
                ? `Task ID: ${taskStatus.task_id}`
                : `${completedResults.length}개 토픽 검증 완료`}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {taskStatus && taskStatus.status !== 'completed' && taskStatus.status !== 'failed' && (
              <ValidationProgress
                status={taskStatus}
                total={taskStatus.total}
                current={taskStatus.current}
                progress={taskStatus.progress}
              />
            )}
            {completedResults.length > 0 && (
              <ValidationResults results={completedResults} />
            )}
          </CardContent>
        </Card>
      )}

      {/* 토픽 선택 */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>검증할 토픽 선택</CardTitle>
              <CardDescription>
                {selectedTopicIds.size > 0
                  ? `${selectedTopicIds.size}개 토픽 선택됨`
                  : '검증할 토픽을 선택하세요'}
              </CardDescription>
            </div>
            {selectedTopicIds.size > 0 && (
              <Button onClick={handleStartValidation} disabled={!!currentTaskId}>
                <Play className="mr-2 h-4 w-4" />
                검증 시작 ({selectedTopicIds.size}개)
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <div className="mb-4 h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent mx-auto" />
                <p className="text-sm text-muted-foreground">로딩 중...</p>
              </div>
            </div>
          ) : topics.length === 0 ? (
            <p className="text-center text-muted-foreground py-8">
              검증할 토픽이 없습니다. 먼저 토픽을 업로드해주세요.
            </p>
          ) : (
            <div className="space-y-4">
              {/* 전체 선택 */}
              <div className="flex items-center gap-2 border-b pb-4">
                <Checkbox
                  id="select-all"
                  checked={selectedTopicIds.size === topics.length && topics.length > 0}
                  onCheckedChange={toggleSelectAll}
                />
                <label htmlFor="select-all" className="text-sm font-medium cursor-pointer">
                  전체 선택 ({topics.length}개)
                </label>
              </div>

              {/* 토픽 목록 */}
              <div className="space-y-2 max-h-[500px] overflow-y-auto">
                {topics.map((topic) => (
                  <div
                    key={topic.id}
                    className={`flex items-center gap-4 rounded-lg border p-4 transition-colors ${
                      selectedTopicIds.has(topic.id)
                        ? 'border-primary bg-primary/5'
                        : 'hover:bg-muted/50'
                    }`}
                  >
                    <Checkbox
                      checked={selectedTopicIds.has(topic.id)}
                      onCheckedChange={() => toggleSelectTopic(topic.id)}
                    />
                    <div className="flex-1 min-w-0">
                      <p className="font-medium truncate">{topic.metadata.file_name}</p>
                      <div className="flex items-center gap-2 mt-1">
                        <Badge className={getDomainColor(topic.metadata.domain)}>
                          {topic.metadata.domain}
                        </Badge>
                        <span className="text-xs text-muted-foreground">
                          완성도: {calculateCompletionRate(topic.completion)}%
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="w-24">
                        <Progress value={calculateCompletionRate(topic.completion)} className="h-2" />
                      </div>
                      {topic.validation_score !== undefined ? (
                        <Badge variant="secondary">
                          <CheckCircle2 className="mr-1 h-3 w-3" />
                          {Math.round(topic.validation_score * 100)}점
                        </Badge>
                      ) : (
                        <Badge variant="outline">
                          <Clock className="mr-1 h-3 w-3" />
                          미검증
                        </Badge>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
