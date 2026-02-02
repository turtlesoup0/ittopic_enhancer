import { useState } from 'react';
import { Clock, FileText, CheckCircle, XCircle } from 'lucide-react';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import type { Proposal } from '@/types/api';

interface ProposalCardProps {
  proposal: Proposal;
  onApply?: (proposalId: string) => void;
  onReject?: (proposalId: string) => void;
}

export function ProposalCard({ proposal, onApply, onReject }: ProposalCardProps) {
  const [showDetail, setShowDetail] = useState(false);

  const handleApply = () => {
    onApply?.(proposal.id);
    setShowDetail(false);
  };

  const handleReject = () => {
    onReject?.(proposal.id);
    setShowDetail(false);
  };

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

  return (
    <>
      <Card
        className="cursor-pointer transition-all hover:shadow-md"
        onClick={() => setShowDetail(true)}
      >
        <CardHeader>
          <div className="flex items-start justify-between">
            <div className="space-y-1">
              <CardTitle className="text-lg">{proposal.title}</CardTitle>
              <CardDescription className="line-clamp-2">{proposal.description}</CardDescription>
            </div>
            <Badge className={getPriorityColor(proposal.priority)}>
              {getPriorityLabel(proposal.priority)}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Clock className="h-4 w-4" />
              <span>예상 소요시간: {proposal.estimated_effort}분</span>
            </div>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <FileText className="h-4 w-4" />
              <span>신뢰도: {Math.round(proposal.confidence * 100)}%</span>
            </div>
            {proposal.applied && (
              <Badge variant="default" className="w-fit">적용 완료</Badge>
            )}
            {proposal.rejected && (
              <Badge variant="destructive" className="w-fit">거절됨</Badge>
            )}
          </div>
        </CardContent>
      </Card>

      {/* 상세 다이얼로그 */}
      <Dialog open={showDetail} onOpenChange={setShowDetail}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <div className="flex items-start justify-between">
              <div className="space-y-1">
                <DialogTitle>{proposal.title}</DialogTitle>
                <DialogDescription>{proposal.description}</DialogDescription>
              </div>
              <Badge className={getPriorityColor(proposal.priority)}>
                {getPriorityLabel(proposal.priority)}
              </Badge>
            </div>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {/* 현재 내용 */}
            <div>
              <p className="mb-2 text-sm font-medium">현재 내용</p>
              <div className="rounded-md border border-red-200 bg-red-50 p-4 dark:border-red-900 dark:bg-red-950">
                <p className="whitespace-pre-wrap text-sm text-red-900 dark:text-red-100">
                  {proposal.current_content || '(비어있음)'}
                </p>
              </div>
            </div>

            {/* 제안 내용 */}
            <div>
              <p className="mb-2 text-sm font-medium">제안 내용</p>
              <div className="rounded-md border border-green-200 bg-green-50 p-4 dark:border-green-900 dark:bg-green-950">
                <p className="whitespace-pre-wrap text-sm text-green-900 dark:text-green-100">
                  {proposal.suggested_content}
                </p>
              </div>
            </div>

            {/* 근거 설명 */}
            {proposal.reasoning && (
              <div>
                <p className="mb-2 text-sm font-medium">근거 설명</p>
                <div className="rounded-md border bg-muted p-4">
                  <p className="whitespace-pre-wrap text-sm text-muted-foreground">
                    {proposal.reasoning}
                  </p>
                </div>
              </div>
            )}

            {/* 참조 문서 */}
            {proposal.reference_sources.length > 0 && (
              <div>
                <p className="mb-2 text-sm font-medium">참조 문서</p>
                <div className="space-y-1">
                  {proposal.reference_sources.map((source, index) => (
                    <div key={index} className="flex items-center gap-2 text-sm text-muted-foreground">
                      <FileText className="h-4 w-4" />
                      <span>{source}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 메타 정보 */}
            <div className="flex gap-4 text-sm text-muted-foreground">
              <div className="flex items-center gap-1">
                <Clock className="h-4 w-4" />
                <span>{proposal.estimated_effort}분 소요 예상</span>
              </div>
              <div className="flex items-center gap-1">
                <FileText className="h-4 w-4" />
                <span>신뢰도 {Math.round(proposal.confidence * 100)}%</span>
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDetail(false)}>
              닫기
            </Button>
            {!proposal.applied && !proposal.rejected && (
              <>
                <Button variant="destructive" onClick={handleReject}>
                  <XCircle className="mr-2 h-4 w-4" />
                  거절
                </Button>
                <Button onClick={handleApply}>
                  <CheckCircle className="mr-2 h-4 w-4" />
                  적용
                </Button>
              </>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
