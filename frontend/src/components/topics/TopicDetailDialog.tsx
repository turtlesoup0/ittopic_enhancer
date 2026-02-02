import { Copy, Check } from 'lucide-react'
import { useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { getDomainColor } from '@/lib/utils'
import type { Topic } from '@/types/api'

interface TopicDetailDialogProps {
  topic: Topic
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function TopicDetailDialog({ topic, open, onOpenChange }: TopicDetailDialogProps) {
  const [copied, setCopied] = useState(false)

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const completionRate = Object.values(topic.completion).filter(Boolean).length / 5 * 100

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {topic.metadata.file_name}
            <Badge className={getDomainColor(topic.metadata.domain)}>
              {topic.metadata.domain}
            </Badge>
          </DialogTitle>
          <DialogDescription>
            {topic.metadata.folder} • ID: {topic.id.slice(0, 8)}...
          </DialogDescription>
        </DialogHeader>

        <Tabs defaultValue="content" className="space-y-4">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="content">내용</TabsTrigger>
            <TabsTrigger value="metadata">메타데이터</TabsTrigger>
            <TabsTrigger value="status">상태</TabsTrigger>
          </TabsList>

          {/* 내용 탭 */}
          <TabsContent value="content" className="space-y-4">
            <div className="space-y-4">
              {/* 리드문 */}
              <div className="rounded-lg border p-4">
                <div className="mb-2 flex items-center justify-between">
                  <h4 className="font-medium">리드문</h4>
                  {topic.completion.리드문 ? (
                    <Badge variant="secondary">완료</Badge>
                  ) : (
                    <Badge variant="outline">미완료</Badge>
                  )}
                </div>
                <p className="text-sm whitespace-pre-wrap">{topic.content.리드문 || '(비어있음)'}</p>
              </div>

              {/* 정의 */}
              <div className="rounded-lg border p-4">
                <div className="mb-2 flex items-center justify-between">
                  <h4 className="font-medium">정의</h4>
                  {topic.completion.정의 ? (
                    <Badge variant="secondary">완료</Badge>
                  ) : (
                    <Badge variant="outline">미완료</Badge>
                  )}
                </div>
                <p className="text-sm whitespace-pre-wrap">{topic.content.정의 || '(비어있음)'}</p>
              </div>

              {/* 키워드 */}
              <div className="rounded-lg border p-4">
                <div className="mb-2 flex items-center justify-between">
                  <h4 className="font-medium">키워드</h4>
                  {topic.completion.키워드 ? (
                    <Badge variant="secondary">완료</Badge>
                  ) : (
                    <Badge variant="outline">미완료</Badge>
                  )}
                </div>
                <div className="flex flex-wrap gap-2">
                  {topic.content.키워드.length > 0 ? (
                    topic.content.키워드.map((keyword, index) => (
                      <Badge key={index} variant="outline">
                        {keyword}
                      </Badge>
                    ))
                  ) : (
                    <span className="text-sm text-muted-foreground">(비어있음)</span>
                  )}
                </div>
              </div>

              {/* 해시태그 */}
              <div className="rounded-lg border p-4">
                <div className="mb-2 flex items-center justify-between">
                  <h4 className="font-medium">해시태그</h4>
                  {topic.completion.해시태그 ? (
                    <Badge variant="secondary">완료</Badge>
                  ) : (
                    <Badge variant="outline">미완료</Badge>
                  )}
                </div>
                <p className="text-sm">{topic.content.해시태그 || '(비어있음)'}</p>
              </div>

              {/* 암기 */}
              <div className="rounded-lg border p-4">
                <div className="mb-2 flex items-center justify-between">
                  <h4 className="font-medium">암기</h4>
                  {topic.completion.암기 ? (
                    <Badge variant="secondary">완료</Badge>
                  ) : (
                    <Badge variant="outline">미완료</Badge>
                  )}
                </div>
                <p className="text-sm whitespace-pre-wrap">{topic.content.암기 || '(비어있음)'}</p>
              </div>
            </div>
          </TabsContent>

          {/* 메타데이터 탭 */}
          <TabsContent value="metadata" className="space-y-4">
            <div className="space-y-3">
              <div className="flex items-center justify-between rounded-lg border p-3">
                <span className="text-sm font-medium">파일 경로</span>
                <span className="text-sm text-muted-foreground font-mono">
                  {topic.metadata.file_path}
                </span>
              </div>
              <div className="flex items-center justify-between rounded-lg border p-3">
                <span className="text-sm font-medium">파일명</span>
                <span className="text-sm">{topic.metadata.file_name}</span>
              </div>
              <div className="flex items-center justify-between rounded-lg border p-3">
                <span className="text-sm font-medium">폴더</span>
                <span className="text-sm">{topic.metadata.folder}</span>
              </div>
              <div className="flex items-center justify-between rounded-lg border p-3">
                <span className="text-sm font-medium">도메인</span>
                <Badge className={getDomainColor(topic.metadata.domain)}>
                  {topic.metadata.domain}
                </Badge>
              </div>
              <div className="flex items-center justify-between rounded-lg border p-3">
                <span className="text-sm font-medium">시험 빈도</span>
                <Badge variant="outline">
                  {topic.metadata.exam_frequency === 'high' && '높음'}
                  {topic.metadata.exam_frequency === 'medium' && '보통'}
                  {topic.metadata.exam_frequency === 'low' && '낮음'}
                </Badge>
              </div>
              <div className="flex items-center justify-between rounded-lg border p-3">
                <span className="text-sm font-medium">생성일</span>
                <span className="text-sm text-muted-foreground">
                  {new Date(topic.created_at).toLocaleString('ko-KR')}
                </span>
              </div>
              <div className="flex items-center justify-between rounded-lg border p-3">
                <span className="text-sm font-medium">수정일</span>
                <span className="text-sm text-muted-foreground">
                  {new Date(topic.updated_at).toLocaleString('ko-KR')}
                </span>
              </div>
            </div>
          </TabsContent>

          {/* 상태 탭 */}
          <TabsContent value="status" className="space-y-4">
            <div className="space-y-4">
              {/* 완성도 */}
              <div className="rounded-lg border p-4">
                <h4 className="mb-3 font-medium">완성도</h4>
                <Progress value={completionRate} className="h-3 mb-2" />
                <p className="text-sm text-muted-foreground">
                  {Math.round(completionRate)}% 완료 ({Object.values(topic.completion).filter(Boolean).length}/5)
                </p>
              </div>

              {/* 필드별 완료 상태 */}
              <div className="rounded-lg border p-4">
                <h4 className="mb-3 font-medium">필드별 상태</h4>
                <div className="space-y-2">
                  {Object.entries(topic.completion).map(([field, completed]) => (
                    <div
                      key={field}
                      className="flex items-center justify-between rounded border p-2"
                    >
                      <span className="text-sm">{field}</span>
                      {completed ? (
                        <Badge variant="secondary" className="text-green-600">
                          완료
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="text-muted-foreground">
                          미완료
                        </Badge>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* 검증 정보 */}
              <div className="rounded-lg border p-4">
                <h4 className="mb-3 font-medium">검증 정보</h4>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm">검증 점수</span>
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
                      <span className="text-sm text-muted-foreground">미검증</span>
                    )}
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">마지막 검증</span>
                    <span className="text-sm text-muted-foreground">
                      {topic.last_validated
                        ? new Date(topic.last_validated).toLocaleString('ko-KR')
                        : '-'}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </TabsContent>
        </Tabs>

        {/* 버튼 */}
        <div className="flex justify-end gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleCopy(JSON.stringify(topic, null, 2))}
          >
            {copied ? (
              <>
                <Check className="mr-2 h-4 w-4" />
                복사됨
              </>
            ) : (
              <>
                <Copy className="mr-2 h-4 w-4" />
                JSON 복사
              </>
            )}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
