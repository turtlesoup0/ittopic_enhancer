import { Card, CardContent } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import type { ValidationTaskStatus } from '@/types/api'

interface ValidationProgressProps {
  status: ValidationTaskStatus
  total: number
  current: number
  progress: number
}

export function ValidationProgress({ status, total, current, progress }: ValidationProgressProps) {
  const getStatusMessage = () => {
    switch (status.status) {
      case 'queued':
        return '대기 중...'
      case 'processing':
        return `검증 중... (${current}/${total})`
      case 'completed':
        return '완료'
      case 'failed':
        return '실패'
      default:
        return '알 수 없음'
    }
  }

  const getStatusVariant = () => {
    switch (status.status) {
      case 'queued':
        return 'secondary'
      case 'processing':
        return 'default'
      case 'completed':
        return 'default' // green
      case 'failed':
        return 'destructive'
      default:
        return 'secondary'
    }
  }

  return (
    <div className="space-y-4">
      {/* 진행률 표시 */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-sm">
          <span className="font-medium">{getStatusMessage()}</span>
          <span className="text-muted-foreground">{progress}%</span>
        </div>
        <Progress value={progress} className="h-2" />
      </div>

      {/* 상태 정보 */}
      <div className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <span className="text-muted-foreground">총 토픽:</span>
          <span className="ml-2 font-medium">{total}</span>
        </div>
        <div>
          <span className="text-muted-foreground">완료:</span>
          <span className="ml-2 font-medium">{current}</span>
        </div>
        <div>
          <span className="text-muted-foreground">남음:</span>
          <span className="ml-2 font-medium">{total - current}</span>
        </div>
        <div>
          <span className="text-muted-foreground">Task ID:</span>
          <span className="ml-2 font-mono text-xs">{status.task_id.slice(0, 8)}...</span>
        </div>
      </div>

      {/* 에러 메시지 */}
      {status.error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 dark:border-red-800 dark:bg-red-950">
          <p className="text-sm text-red-800 dark:text-red-200">
            <strong>에러:</strong> {status.error}
          </p>
        </div>
      )}
    </div>
  )
}
