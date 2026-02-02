import { useState } from 'react'
import { Upload, FileText, X } from 'lucide-react'
import { topicsApi } from '@/lib/api'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Progress } from '@/components/ui/progress'
import type { DomainEnum } from '@/types/api'

interface TopicUploadModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess: () => void
}

export function TopicUploadModal({ open, onOpenChange, onSuccess }: TopicUploadModalProps) {
  const [jsonContent, setJsonContent] = useState('')
  const [domain, setDomain] = useState<DomainEnum>('신기술')
  const [isUploading, setIsUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)

  const handleUpload = async () => {
    try {
      setIsUploading(true)
      setUploadProgress(10)

      // JSON 파싱
      let topics
      try {
        topics = JSON.parse(jsonContent)
      } catch {
        setUploadProgress(0)
        setIsUploading(false)
        return
      }

      // 배열로 변환
      const topicsArray = Array.isArray(topics) ? topics : [topics]
      setUploadProgress(50)

      // 도메인 설정
      const topicsWithDomain = topicsArray.map((topic: any) => ({
        ...topic,
        domain,
        exam_frequency: topic.exam_frequency || 'medium',
      }))

      // API 호출
      const response = await topicsApi.upload(topicsWithDomain)
      setUploadProgress(100)

      setTimeout(() => {
        onSuccess()
        setJsonContent('')
        setUploadProgress(0)
        setIsUploading(false)
      }, 500)
    } catch (error: any) {
      setUploadProgress(0)
      setIsUploading(false)
      console.error('Upload failed:', error)
    }
  }

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    const reader = new FileReader()
    reader.onload = (e) => {
      const content = e.target?.result as string
      setJsonContent(content)
    }
    reader.readAsText(file)
  }

  const isValidJson = () => {
    try {
      JSON.parse(jsonContent)
      return true
    } catch {
      return false
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>토픽 업로드</DialogTitle>
          <DialogDescription>
            Obsidian Dataview JSON 내보내기 파일을 업로드하세요.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* 파일 업로드 */}
          <div className="space-y-2">
            <Label htmlFor="file-upload">파일 선택</Label>
            <div className="flex items-center gap-2">
              <Input
                id="file-upload"
                type="file"
                accept=".json"
                onChange={handleFileUpload}
                disabled={isUploading}
              />
              <Button variant="outline" size="icon" disabled={isUploading}>
                <Upload className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {/* 도메인 선택 */}
          <div className="space-y-2">
            <Label htmlFor="domain">도메인</Label>
            <Select value={domain} onValueChange={(v) => setDomain(v as DomainEnum)}>
              <SelectTrigger id="domain">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="신기술">신기술</SelectItem>
                <SelectItem value="정보보안">정보보안</SelectItem>
                <SelectItem value="네트워크">네트워크</SelectItem>
                <SelectItem value="데이터베이스">데이터베이스</SelectItem>
                <SelectItem value="SW">SW</SelectItem>
                <SelectItem value="프로젝트관리">프로젝트관리</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* JSON 입력 */}
          <div className="space-y-2">
            <Label htmlFor="json-content">JSON 내용</Label>
            <div className="relative">
              <textarea
                id="json-content"
                className={`w-full min-h-[300px] rounded-md border p-3 text-sm font-mono ${
                  jsonContent && !isValidJson()
                    ? 'border-red-500 focus:border-red-500'
                    : 'focus:border-primary'
                }`}
                placeholder='[{"file_path": "...", "file_name": "...", ...}]'
                value={jsonContent}
                onChange={(e) => setJsonContent(e.target.value)}
                disabled={isUploading}
              />
              {jsonContent && (
                <Button
                  variant="ghost"
                  size="icon"
                  className="absolute top-2 right-2 h-6 w-6"
                  onClick={() => setJsonContent('')}
                  disabled={isUploading}
                >
                  <X className="h-4 w-4" />
                </Button>
              )}
            </div>
            {jsonContent && !isValidJson() && (
              <p className="text-sm text-red-500">유효하지 않은 JSON 형식입니다.</p>
            )}
          </div>

          {/* 진행률 */}
          {isUploading && (
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span>업로드 중...</span>
                <span>{uploadProgress}%</span>
              </div>
              <Progress value={uploadProgress} />
            </div>
          )}

          {/* 미리보기 */}
          {jsonContent && isValidJson() && (
            <div className="rounded-md border p-4">
              <p className="mb-2 text-sm font-medium">미리보기</p>
              <p className="text-sm text-muted-foreground">
                {Array.isArray(JSON.parse(jsonContent))
                  ? `${JSON.parse(jsonContent).length}개 토픽`
                  : '1개 토픽'}{' '}
               가 감지되었습니다.
              </p>
            </div>
          )}
        </div>

        {/* 버튼 */}
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isUploading}>
            취소
          </Button>
          <Button
            onClick={handleUpload}
            disabled={!jsonContent || !isValidJson() || isUploading}
          >
            {isUploading ? '업로드 중...' : '업로드'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
