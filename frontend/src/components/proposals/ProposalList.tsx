import { useMemo } from 'react';
import { FileText, Filter } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ProposalCard } from './ProposalCard';
import type { Proposal } from '@/types/api';

interface ProposalListProps {
  proposals: Proposal[];
  filterPriority?: string;
  onFilterChange?: (priority: string | undefined) => void;
  onApply?: (proposalId: string) => void;
  onReject?: (proposalId: string) => void;
}

export function ProposalList({
  proposals,
  filterPriority,
  onFilterChange,
  onApply,
  onReject,
}: ProposalListProps) {
  // 필터링된 제안 목록
  const filteredProposals = useMemo(() => {
    return proposals.filter((proposal) => {
      return !filterPriority || proposal.priority === filterPriority;
    });
  }, [proposals, filterPriority]);

  // 우선순위별 개수
  const priorityCounts = useMemo(() => {
    return {
      critical: proposals.filter((p) => p.priority === 'critical').length,
      high: proposals.filter((p) => p.priority === 'high').length,
      medium: proposals.filter((p) => p.priority === 'medium').length,
      low: proposals.filter((p) => p.priority === 'low').length,
    };
  }, [proposals]);

  return (
    <div className="space-y-4">
      {/* 필터 바 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 flex-wrap">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm text-muted-foreground">필터:</span>
          <Button
            variant={filterPriority === undefined ? 'default' : 'outline'}
            size="sm"
            onClick={() => onFilterChange?.(undefined)}
          >
            전체
          </Button>
          <Button
            variant={filterPriority === 'critical' ? 'default' : 'outline'}
            size="sm"
            onClick={() => onFilterChange?.(filterPriority === 'critical' ? undefined : 'critical')}
          >
            매우 중요 ({priorityCounts.critical})
          </Button>
          <Button
            variant={filterPriority === 'high' ? 'default' : 'outline'}
            size="sm"
            onClick={() => onFilterChange?.(filterPriority === 'high' ? undefined : 'high')}
          >
            중요 ({priorityCounts.high})
          </Button>
          <Button
            variant={filterPriority === 'medium' ? 'default' : 'outline'}
            size="sm"
            onClick={() => onFilterChange?.(filterPriority === 'medium' ? undefined : 'medium')}
          >
            보통 ({priorityCounts.medium})
          </Button>
          <Button
            variant={filterPriority === 'low' ? 'default' : 'outline'}
            size="sm"
            onClick={() => onFilterChange?.(filterPriority === 'low' ? undefined : 'low')}
          >
            낮음 ({priorityCounts.low})
          </Button>
        </div>
      </div>

      {/* 제안 목록 */}
      {filteredProposals.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <FileText className="mb-4 h-12 w-12 text-muted-foreground opacity-50" />
          <p className="text-muted-foreground">
            {proposals.length === 0
              ? '아직 제안이 없습니다. 토픽을 검증하세요.'
              : '선택한 필터에 해당하는 제안이 없습니다.'}
          </p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredProposals.map((proposal) => (
            <ProposalCard
              key={proposal.id}
              proposal={proposal}
              onApply={onApply}
              onReject={onReject}
            />
          ))}
        </div>
      )}
    </div>
  );
}
