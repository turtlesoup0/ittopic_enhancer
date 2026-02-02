import { useEffect, useState, useMemo } from 'react';
import { Activity, CheckCircle, Clock, FileText } from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useAppStore, useValidationStore } from '@/lib/store';
import { topicsApi, validationApi, proposalsApi, healthApi } from '@/lib/api';
import { useToast } from '@/components/ui/use-toast';
import { StatsCard } from './StatsCard';
import { CompletionChart } from './CompletionChart';
import { TopicList } from '@/components/topics/TopicList';
import { ValidationPanel } from '@/components/validation/ValidationPanel';
import { ProposalList } from '@/components/proposals/ProposalList';
import type { Topic, ValidationResult, Proposal, DomainEnum } from '@/types/api';

export function Dashboard() {
  const { toast } = useToast();
  const { selectedDomain, setSelectedDomain } = useAppStore();
  const { taskId, setTaskId, results, setResults } = useValidationStore();

  // 로컬 상태
  const [topics, setTopics] = useState<Topic[]>([]);
  const [validationResult, setValidationResult] = useState<ValidationResult | undefined>();
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterPriority, setFilterPriority] = useState<string | undefined>();
  const [selectedTopic, setSelectedTopic] = useState<Topic | undefined>();
  const [isLoading, setIsLoading] = useState(false);
  const [isValidationPending, setIsValidationPending] = useState(false);

  // 데이터 로드
  useEffect(() => {
    const loadData = async () => {
      try {
        setIsLoading(true);
        const [topicsData] = await Promise.all([
          topicsApi.list(),
        ]);
        setTopics(topicsData.data);
      } catch (error) {
        console.error('Failed to load data:', error);
        toast({
          variant: 'destructive',
          title: '데이터 로드 실패',
          description: error instanceof Error ? error.message : '데이터를 불러오지 못했습니다.',
        });
      } finally {
        setIsLoading(false);
      }
    };

    loadData();
  }, [toast]);

  // 검증 결과 폴링
  useEffect(() => {
    if (!taskId) return;

    const pollResult = async () => {
      try {
        const response = await validationApi.getResult(taskId);
        if (response.data.status === 'completed') {
          setValidationResult(response.data.results[0]);
          setIsValidationPending(false);
          setTaskId(null);

          // 제안 로드
          if (response.data.results[0]?.topic_id) {
            const proposalsResponse = await proposalsApi.list(response.data.results[0].topic_id);
            setProposals(proposalsResponse.data);
          }

          toast({
            title: '검증 완료',
            description: '토픽 검증이 완료되었습니다.',
          });
        }
      } catch (error) {
        console.error('Failed to poll result:', error);
      }
    };

    const interval = setInterval(pollResult, 2000);
    return () => clearInterval(interval);
  }, [taskId, setTaskId, toast]);

  // 통계 계산
  const statsData = useMemo(() => {
    return {
      totalTopics: topics.length,
      completedTopics: topics.filter((t) => {
        const completion = Object.values(t.completion).filter(Boolean).length;
        return completion === 5;
      }).length,
      validatedTopics: topics.filter((t) => t.validation_score !== undefined).length,
      pendingProposals: proposals.filter((p) => !p.applied && !p.rejected).length,
    };
  }, [topics, proposals]);

  // 전체 완성률
  const overallCompletionRate = useMemo(() => {
    if (topics.length === 0) return 0;
    const totalCompletion = topics.reduce((sum, topic) => {
      const completion = Object.values(topic.completion).filter(Boolean).length;
      return sum + completion / 5;
    }, 0);
    return Math.round((totalCompletion / topics.length) * 100);
  }, [topics]);

  // 도메인별 통계
  const domainStats = useMemo(() => {
    const stats: Record<string, { total: number; completed: number; completionRate: number }> = {};

    topics.forEach((topic) => {
      const domain = topic.metadata.domain;
      if (!stats[domain]) {
        stats[domain] = { total: 0, completed: 0, completionRate: 0 };
      }
      stats[domain].total++;

      const completion = Object.values(topic.completion).filter(Boolean).length;
      if (completion === 5) {
        stats[domain].completed++;
      }
    });

    return Object.entries(stats).map(([domain, data]) => ({
      domain: domain as DomainEnum,
      total_topics: data.total,
      completed_count: data.completed,
      completion_rate: Math.round((data.completed / data.total) * 100),
    }));
  }, [topics]);

  // 토픽 검증 핸들러
  const handleValidate = async (topicIds: string[]) => {
    try {
      setIsValidationPending(true);
      const response = await validationApi.create({
        topic_ids: topicIds.length > 0 ? topicIds : topics.map((t) => t.id),
      });

      setTaskId(response.data.task_id);

      toast({
        title: '검증 시작',
        description: `토픽 검증이 시작되었습니다. 예상 소요시간: ${response.data.estimated_time}초`,
      });

      if (topicIds.length === 1) {
        setSelectedTopic(topics.find((t) => t.id === topicIds[0]));
      }
    } catch (error) {
      setIsValidationPending(false);
      toast({
        variant: 'destructive',
        title: '검증 실패',
        description: error instanceof Error ? error.message : '검증 요청 실패',
      });
    }
  };

  // 제안 적용 핸들러
  const handleApplyProposal = async (proposalId: string) => {
    try {
      const proposal = proposals.find((p) => p.id === proposalId);
      if (!proposal) return;

      await proposalsApi.apply({
        topic_id: proposal.topic_id,
        proposal_id: proposalId,
      });

      setProposals((prev) =>
        prev.map((p) => (p.id === proposalId ? { ...p, applied: true } : p))
      );

      toast({
        title: '제안 적용 완료',
        description: '제안이 성공적으로 적용되었습니다.',
      });
    } catch (error) {
      toast({
        variant: 'destructive',
        title: '제안 적용 실패',
        description: error instanceof Error ? error.message : '제안 적용 실패',
      });
    }
  };

  // 제안 거절 핸들러
  const handleRejectProposal = async (proposalId: string) => {
    try {
      const proposal = proposals.find((p) => p.id === proposalId);
      if (!proposal) return;

      await proposalsApi.reject(proposalId, proposal.topic_id);

      setProposals((prev) =>
        prev.map((p) => (p.id === proposalId ? { ...p, rejected: true } : p))
      );

      toast({
        title: '제안 거절',
        description: '제안이 거절되었습니다.',
      });
    } catch (error) {
      toast({
        variant: 'destructive',
        title: '제안 거절 실패',
        description: error instanceof Error ? error.message : '제안 거절 실패',
      });
    }
  };

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div>
        <h1 className="text-3xl font-bold">ITPE Topic Enhancement</h1>
        <p className="text-muted-foreground">토픽 검증 및 보강 제안 시스템</p>
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
          trend={{ value: overallCompletionRate, isPositive: true }}
        />
        <StatsCard
          title="검증된 토픽"
          value={statsData.validatedTopics}
          description="검증 완료"
          icon={Activity}
        />
        <StatsCard
          title="대기 중 제안"
          value={statsData.pendingProposals}
          description="적용 대기 중"
          icon={Clock}
        />
      </div>

      {/* 차트 */}
      {domainStats.length > 0 && (
        <div className="rounded-lg border p-6">
          <h2 className="mb-4 text-lg font-semibold">도메인별 현황</h2>
          <CompletionChart data={domainStats} />
        </div>
      )}

      {/* 메인 탭 */}
      <Tabs defaultValue="topics" className="space-y-4">
        <TabsList>
          <TabsTrigger value="topics">토픽 목록</TabsTrigger>
          <TabsTrigger value="proposals">제안 목록</TabsTrigger>
          <TabsTrigger value="validation">검증 결과</TabsTrigger>
          <TabsTrigger value="progress">진행 상황</TabsTrigger>
        </TabsList>

        <TabsContent value="topics">
          <TopicList
            topics={topics}
            filterDomain={selectedDomain || undefined}
            searchQuery={searchQuery}
            onDomainChange={(domain) => setSelectedDomain(domain || null)}
            onSearchChange={setSearchQuery}
            onTopicSelect={setSelectedTopic}
            onValidate={handleValidate}
            isValidationPending={isValidationPending}
          />
        </TabsContent>

        <TabsContent value="proposals">
          <ProposalList
            proposals={proposals}
            filterPriority={filterPriority}
            onFilterChange={setFilterPriority}
            onApply={handleApplyProposal}
            onReject={handleRejectProposal}
          />
        </TabsContent>

        <TabsContent value="validation">
          <ValidationPanel
            validationResult={validationResult}
            isLoading={isValidationPending}
          />
        </TabsContent>

        <TabsContent value="progress">
          <div className="rounded-lg border p-6">
            <h2 className="mb-4 text-lg font-semibold">진행 상황</h2>
            {isValidationPending ? (
              <div className="flex items-center gap-4">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
                <div>
                  <p className="font-medium">검증 진행 중...</p>
                  <p className="text-sm text-muted-foreground">
                    Task ID: {taskId}
                  </p>
                </div>
              </div>
            ) : (
              <p className="text-muted-foreground">진행 중인 작업이 없습니다.</p>
            )}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
