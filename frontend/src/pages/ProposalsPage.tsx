import { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Filter, FileText, CheckCircle2, XCircle } from 'lucide-react'
import { proposalsApi, topicsApi } from '@/lib/api'
import { useToast } from '@/components/ui/use-toast'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ProposalCard } from '@/components/proposals/ProposalCard'
import type { Proposal, Topic } from '@/types/api'

export function ProposalsPage() {
  const { toast } = useToast()
  const queryClient = useQueryClient()

  // 상태 관리
  const [filterPriority, setFilterPriority] = useState<string>('')
  const [filterStatus, setFilterStatus] = useState<'pending' | 'applied' | 'rejected'>('pending')

  // 토픽 목록 조회 (제안을 위해 필요)
  const { data: topicsData } = useQuery({
    queryKey: ['topics'],
    queryFn: async () => {
      const response = await topicsApi.list()
      return response.data
    },
  })

  const topics = topicsData?.topics || []

  // 모든 토픽에 대한 제안 조회
  const proposalsQueries = useQuery({
    queryKey: ['proposals', 'all'],
    queryFn: async () => {
      // 각 토픽에 대한 제안을 병렬로 조회
      const promises = topics.map(async (topic) => {
        try {
          const response = await proposalsApi.list(topic.id)
          return { topicId: topic.id, topicName: topic.metadata.file_name, proposals: response.data.proposals || [] }
        } catch {
          return { topicId: topic.id, topicName: topic.metadata.file_name, proposals: [] }
        }
      })
      const results = await Promise.all(promises)
      return results.flatMap(r => r.proposals.map(p => ({ ...p, topicName: r.topicName })))
    },
    enabled: topics.length > 0,
  })

  const allProposals = (proposalsQueries.data || []) as Array<Proposal & { topicName: string }>

  // 제안 적용
  const applyMutation = useMutation({
    mutationFn: async (proposal: any) => {
      const response = await proposalsApi.apply({
        proposal_id: proposal.id,
        topic_id: proposal.topic_id,
      })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['proposals'] })
      toast({
        title: '제안 적용 완료',
        description: '제안이 성공적으로 적용되었습니다.',
      })
    },
    onError: (error: Error) => {
      toast({
        variant: 'destructive',
        title: '제안 적용 실패',
        description: error.message,
      })
    },
  })

  // 제안 거절
  const rejectMutation = useMutation({
    mutationFn: async (proposal: any) => {
      const response = await proposalsApi.reject(proposal.id, proposal.topic_id)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['proposals'] })
      toast({
        title: '제안 거절',
        description: '제안이 거절되었습니다.',
      })
    },
    onError: (error: Error) => {
      toast({
        variant: 'destructive',
        title: '제안 거절 실패',
        description: error.message,
      })
    },
  })

  // 필터링된 제안 목록
  const filteredProposals = useMemo(() => {
    return allProposals.filter((proposal) => {
      const matchPriority = !filterPriority || proposal.priority === filterPriority
      const matchStatus =
        filterStatus === 'pending' ? !proposal.applied && !proposal.rejected
        : filterStatus === 'applied' ? proposal.applied
        : proposal.rejected
      return matchPriority && matchStatus
    })
  }, [allProposals, filterPriority, filterStatus])

  // 우선순위별 개수
  const priorityCounts = useMemo(() => {
    return {
      critical: allProposals.filter((p) => p.priority === 'critical' && !p.applied && !p.rejected).length,
      high: allProposals.filter((p) => p.priority === 'high' && !p.applied && !p.rejected).length,
      medium: allProposals.filter((p) => p.priority === 'medium' && !p.applied && !p.rejected).length,
      low: allProposals.filter((p) => p.priority === 'low' && !p.applied && !p.rejected).length,
    }
  }, [allProposals])

  // 상태별 개수
  const statusCounts = useMemo(() => {
    return {
      pending: allProposals.filter((p) => !p.applied && !p.rejected).length,
      applied: allProposals.filter((p) => p.applied).length,
      rejected: allProposals.filter((p) => p.rejected).length,
    }
  }, [allProposals])

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div>
        <h2 className="text-3xl font-bold tracking-tight">제안 관리</h2>
        <p className="text-muted-foreground">
          보강 제안 확인 및 적용
        </p>
      </div>

      {/* 통계 카드 */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              대기 중
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <span className="text-2xl font-bold">{statusCounts.pending}</span>
              <Clock className="h-5 w-5 text-muted-foreground" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              적용 완료
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <span className="text-2xl font-bold">{statusCounts.applied}</span>
              <CheckCircle2 className="h-5 w-5 text-green-500" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              거절됨
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <span className="text-2xl font-bold">{statusCounts.rejected}</span>
              <XCircle className="h-5 w-5 text-red-500" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              매우 중요
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <span className="text-2xl font-bold">{priorityCounts.critical}</span>
              <Badge className="bg-red-500">Critical</Badge>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 필터 */}
      <Card>
        <CardContent className="pt-6">
          <Tabs value={filterStatus} onValueChange={(v) => setFilterStatus(v as any)}>
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="pending">
                대기 중 ({statusCounts.pending})
              </TabsTrigger>
              <TabsTrigger value="applied">
                적용 완료 ({statusCounts.applied})
              </TabsTrigger>
              <TabsTrigger value="rejected">
                거절됨 ({statusCounts.rejected})
              </TabsTrigger>
            </TabsList>
          </Tabs>
        </CardContent>
      </Card>

      {/* 우선순위 필터 */}
      {filterStatus === 'pending' && (
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 flex-wrap">
              <Filter className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">우선순위:</span>
              <Button
                variant={!filterPriority ? 'default' : 'outline'}
                size="sm"
                onClick={() => setFilterPriority('')}
              >
                전체
              </Button>
              <Button
                variant={filterPriority === 'critical' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setFilterPriority(filterPriority === 'critical' ? '' : 'critical')}
              >
                매우 중요 ({priorityCounts.critical})
              </Button>
              <Button
                variant={filterPriority === 'high' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setFilterPriority(filterPriority === 'high' ? '' : 'high')}
              >
                중요 ({priorityCounts.high})
              </Button>
              <Button
                variant={filterPriority === 'medium' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setFilterPriority(filterPriority === 'medium' ? '' : 'medium')}
              >
                보통 ({priorityCounts.medium})
              </Button>
              <Button
                variant={filterPriority === 'low' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setFilterPriority(filterPriority === 'low' ? '' : 'low')}
              >
                낮음 ({priorityCounts.low})
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 제안 목록 */}
      {proposalsQueries.isLoading ? (
        <Card>
          <CardContent className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="mb-4 h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent mx-auto" />
              <p className="text-sm text-muted-foreground">로딩 중...</p>
            </div>
          </CardContent>
        </Card>
      ) : filteredProposals.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12 text-center">
            <FileText className="mb-4 h-12 w-12 text-muted-foreground opacity-50" />
            <p className="text-muted-foreground">
              {allProposals.length === 0
                ? '아직 제안이 없습니다. 토픽을 검증하세요.'
                : '선택한 필터에 해당하는 제안이 없습니다.'}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredProposals.map((proposal) => (
            <ProposalCard
              key={proposal.id}
              proposal={proposal}
              onApply={() => applyMutation.mutate(proposal)}
              onReject={() => rejectMutation.mutate(proposal)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function Clock({ className }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <circle cx="12" cy="12" r="10" />
      <polyline points="12 6 12 12 16 14" />
    </svg>
  )
}
