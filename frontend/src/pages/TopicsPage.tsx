import { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Search, Upload, Plus, RefreshCw } from 'lucide-react'
import { topicsApi, validationApi } from '@/lib/api'
import { useToast } from '@/components/ui/use-toast'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { TopicUploadModal } from '@/components/topics/TopicUploadModal'
import { TopicDetailDialog } from '@/components/topics/TopicDetailDialog'
import { getDomainColor } from '@/lib/utils'
import type { Topic, DomainEnum } from '@/types/api'

export function TopicsPage() {
  const { toast } = useToast()
  const queryClient = useQueryClient()

  // 상태 관리
  const [searchQuery, setSearchQuery] = useState('')
  const [filterDomain, setFilterDomain] = useState<DomainEnum | undefined>()
  const [selectedTopic, setSelectedTopic] = useState<Topic | null>(null)
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false)
  const [selectedTopicIds, setSelectedTopicIds] = useState<Set<string>>(new Set())

  // 토픽 목록 조회
  const { data: topicsData, isLoading } = useQuery({
    queryKey: ['topics', filterDomain],
    queryFn: async () => {
      const params = filterDomain ? { domain: filterDomain } : undefined
      const response = await topicsApi.list(params)
      return response.data
    },
  })

  const topics = topicsData?.topics || []

  // 검증 요청 뮤테이션
  const validateMutation = useMutation({
    mutationFn: async (topicIds: string[]) => {
      const response = await validationApi.create({ topic_ids: topicIds })
      return response.data
    },
    onSuccess: (data) => {
      toast({
        title: '검증 시작',
        description: `검증이 시작되었습니다. 예상 소요시간: ${data.estimated_time}초`,
      })
      setSelectedTopicIds(new Set())
    },
    onError: (error: Error) => {
      toast({
        variant: 'destructive',
        title: '검증 실패',
        description: error.message,
      })
    },
  })

  // 필터링된 토픽 목록
  const filteredTopics = useMemo(() => {
    return topics.filter((topic) => {
      const matchSearch =
        !searchQuery ||
        topic.metadata.file_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        topic.content.리드문.toLowerCase().includes(searchQuery.toLowerCase()) ||
        topic.content.정의.toLowerCase().includes(searchQuery.toLowerCase())
      return matchSearch
    })
  }, [topics, searchQuery])

  // 도메인 목록
  const domains = useMemo(() => {
    return Array.from(new Set(topics.map((t) => t.metadata.domain))) as DomainEnum[]
  }, [topics])

  // 완성도 계산
  const calculateCompletionRate = (completion: Topic['completion']) => {
    const fields = Object.values(completion)
    const completed = fields.filter(Boolean).length
    return Math.round((completed / fields.length) * 100)
  }

  // 전체 선택 토글
  const toggleSelectAll = () => {
    if (selectedTopicIds.size === filteredTopics.length) {
      setSelectedTopicIds(new Set())
    } else {
      setSelectedTopicIds(new Set(filteredTopics.map((t) => t.id)))
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

  // 선택된 토픽 검증
  const handleValidateSelected = () => {
    if (selectedTopicIds.size === 0) {
      toast({
        variant: 'destructive',
        title: '토픽 미선택',
        description: '검증할 토픽을 선택해주세요.',
      })
      return
    }
    validateMutation.mutate(Array.from(selectedTopicIds))
  }

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">토픽 관리</h2>
          <p className="text-muted-foreground">
            토픽 업로드, 조회, 검증 요청
          </p>
        </div>
        <Button onClick={() => setIsUploadModalOpen(true)}>
          <Upload className="mr-2 h-4 w-4" />
          토픽 업로드
        </Button>
      </div>

      {/* 필터 및 검색 */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="토픽명, 리드문, 정의 검색..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9"
              />
            </div>
            <div className="flex gap-2 flex-wrap">
              <Button
                variant={!filterDomain ? 'default' : 'outline'}
                size="sm"
                onClick={() => setFilterDomain(undefined)}
              >
                전체
              </Button>
              {domains.map((domain) => (
                <Button
                  key={domain}
                  variant={filterDomain === domain ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setFilterDomain(filterDomain === domain ? undefined : domain)}
                >
                  {domain}
                </Button>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 선택된 토픽 작업 */}
      {selectedTopicIds.size > 0 && (
        <Card className="border-primary">
          <CardContent className="flex items-center justify-between py-4">
            <p className="text-sm font-medium">
              {selectedTopicIds.size}개 토픽 선택됨
            </p>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setSelectedTopicIds(new Set())}
              >
                선택 해제
              </Button>
              <Button
                size="sm"
                onClick={handleValidateSelected}
                disabled={validateMutation.isPending}
              >
                <RefreshCw className={`mr-2 h-4 w-4 ${validateMutation.isPending ? 'animate-spin' : ''}`} />
                검증 시작
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 토픽 테이블 */}
      <Card>
        <CardHeader>
          <CardTitle>토픽 목록</CardTitle>
          <CardDescription>
            총 {filteredTopics.length}개 토픽
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <div className="mb-4 h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent mx-auto" />
                <p className="text-sm text-muted-foreground">로딩 중...</p>
              </div>
            </div>
          ) : (
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[50px]">
                      <input
                        type="checkbox"
                        className="h-4 w-4"
                        checked={selectedTopicIds.size === filteredTopics.length && filteredTopics.length > 0}
                        onChange={toggleSelectAll}
                      />
                    </TableHead>
                    <TableHead>토픽명</TableHead>
                    <TableHead>도메인</TableHead>
                    <TableHead>리드문</TableHead>
                    <TableHead>완성도</TableHead>
                    <TableHead>검증 점수</TableHead>
                    <TableHead>마지막 검증</TableHead>
                    <TableHead className="text-right">작업</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredTopics.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={8} className="h-24 text-center">
                        토픽이 없습니다.
                      </TableCell>
                    </TableRow>
                  ) : (
                    filteredTopics.map((topic) => (
                      <TableRow key={topic.id} className="cursor-pointer hover:bg-muted/50">
                        <TableCell onClick={(e) => e.stopPropagation()}>
                          <input
                            type="checkbox"
                            className="h-4 w-4"
                            checked={selectedTopicIds.has(topic.id)}
                            onChange={() => toggleSelectTopic(topic.id)}
                          />
                        </TableCell>
                        <TableCell className="font-medium">{topic.metadata.file_name}</TableCell>
                        <TableCell>
                          <Badge className={getDomainColor(topic.metadata.domain)}>
                            {topic.metadata.domain}
                          </Badge>
                        </TableCell>
                        <TableCell className="max-w-xs truncate text-muted-foreground">
                          {topic.content.리드문 || '-'}
                        </TableCell>
                        <TableCell>
                          <div className="space-y-1">
                            <Progress
                              value={calculateCompletionRate(topic.completion)}
                              className="h-2"
                            />
                            <span className="text-xs text-muted-foreground">
                              {calculateCompletionRate(topic.completion)}%
                            </span>
                          </div>
                        </TableCell>
                        <TableCell>
                          {topic.validation_score !== undefined ? (
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
                          ) : (
                            <span className="text-xs text-muted-foreground">미검증</span>
                          )}
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {topic.last_validated
                            ? new Date(topic.last_validated).toLocaleDateString('ko-KR')
                            : '-'}
                        </TableCell>
                        <TableCell className="text-right">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setSelectedTopic(topic)}
                          >
                            상세
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 모달들 */}
      <TopicUploadModal
        open={isUploadModalOpen}
        onOpenChange={setIsUploadModalOpen}
        onSuccess={() => {
          queryClient.invalidateQueries({ queryKey: ['topics'] })
          setIsUploadModalOpen(false)
          toast({
            title: '업로드 완료',
            description: '토픽이 성공적으로 업로드되었습니다.',
          })
        }}
      />

      {selectedTopic && (
        <TopicDetailDialog
          topic={selectedTopic}
          open={!!selectedTopic}
          onOpenChange={(open) => {
            if (!open) setSelectedTopic(null)
          }}
        />
      )}
    </div>
  )
}
