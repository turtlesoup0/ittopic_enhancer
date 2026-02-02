import { useMemo } from 'react';
import { Search } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { getDomainColor } from '@/lib/utils';
import type { Topic } from '@/types/api';

interface TopicListProps {
  topics: Topic[];
  filterDomain?: string;
  searchQuery?: string;
  onDomainChange?: (domain: string | undefined) => void;
  onSearchChange?: (query: string) => void;
  onTopicSelect?: (topic: Topic) => void;
  onValidate?: (topicIds: string[]) => void;
  isValidationPending?: boolean;
}

export function TopicList({
  topics,
  filterDomain,
  searchQuery = '',
  onDomainChange,
  onSearchChange,
  onTopicSelect,
  onValidate,
  isValidationPending,
}: TopicListProps) {
  // 필터링된 토픽 목록
  const filteredTopics = useMemo(() => {
    return topics.filter((topic) => {
      const matchDomain = !filterDomain || topic.metadata.domain === filterDomain;
      const matchSearch =
        !searchQuery ||
        topic.metadata.file_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        topic.content.리드문.toLowerCase().includes(searchQuery.toLowerCase()) ||
        topic.content.정의.toLowerCase().includes(searchQuery.toLowerCase());
      return matchDomain && matchSearch;
    });
  }, [topics, filterDomain, searchQuery]);

  // 도메인 목록 (고유값)
  const domains = useMemo(() => {
    return Array.from(new Set(topics.map((t) => t.metadata.domain))).sort();
  }, [topics]);

  // 완성도 계산
  const calculateCompletionRate = (completion: Topic['completion']) => {
    const fields = Object.values(completion);
    const completed = fields.filter(Boolean).length;
    return Math.round((completed / fields.length) * 100);
  };

  return (
    <div className="space-y-4">
      {/* 필터 및 검색 */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="토픽명, 리드문, 정의 검색..."
            value={searchQuery}
            onChange={(e) => onSearchChange?.(e.target.value)}
            className="pl-9"
          />
        </div>
        <div className="flex gap-2 flex-wrap">
          <Button
            variant={!filterDomain ? 'default' : 'outline'}
            size="sm"
            onClick={() => onDomainChange?.(undefined)}
          >
            전체
          </Button>
          {domains.map((domain) => (
            <Button
              key={domain}
              variant={filterDomain === domain ? 'default' : 'outline'}
              size="sm"
              onClick={() => onDomainChange?.(filterDomain === domain ? undefined : domain)}
            >
              {domain}
            </Button>
          ))}
        </div>
      </div>

      {/* 토픽 테이블 */}
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[50px]">
                <input type="checkbox" className="h-4 w-4" />
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
                <TableRow
                  key={topic.id}
                  className="cursor-pointer hover:bg-muted/50"
                  onClick={() => onTopicSelect?.(topic)}
                >
                  <TableCell onClick={(e) => e.stopPropagation()}>
                    <input type="checkbox" className="h-4 w-4" />
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
                    {topic.last_validated ? new Date(topic.last_validated).toLocaleDateString('ko-KR') : '-'}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        onValidate?.([topic.id]);
                      }}
                      disabled={isValidationPending}
                    >
                      검증
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
