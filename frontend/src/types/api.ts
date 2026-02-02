export type DomainEnum =
  | '신기술'
  | '정보보안'
  | '네트워크'
  | '데이터베이스'
  | 'SW'
  | '프로젝트관리'

export type ExamFrequencyEnum = 'high' | 'medium' | 'low'

export interface Topic {
  id: string
  metadata: {
    file_path: string
    file_name: string
    folder: string
    domain: DomainEnum
    exam_frequency: ExamFrequencyEnum
  }
  content: {
    리드문: string
    정의: string
    키워드: string[]
    해시태그: string
    암기: string
  }
  completion: {
    리드문: boolean
    정의: boolean
    키워드: boolean
    해시태그: boolean
    암기: boolean
  }
  validation_score?: number
  last_validated?: string
  created_at: string
  updated_at: string
}

export interface TopicCreate {
  file_path: string
  file_name: string
  folder: string
  domain: DomainEnum
  exam_frequency?: ExamFrequencyEnum
  리드문?: string
  정의?: string
  키워드?: string[]
  해시태그?: string
  암기?: string
}

export interface TopicListResponse {
  topics: Topic[]
  total: number
  page: number
  size: number
}

export interface DomainStats {
  domain: DomainEnum
  total_topics: number
  completed_count: number
  completion_rate: number
}

export interface ValidationResult {
  id: string
  topic_id: string
  overall_score: number
  gaps: ContentGap[]
  matched_references: MatchedReference[]
  field_completeness_score: number
  content_accuracy_score: number
  reference_coverage_score: number
  validation_timestamp: string
  created_at: string
  updated_at: string
}

export interface ContentGap {
  gap_type: string
  field_name: string
  current_value: string
  suggested_value: string
  confidence: number
  reference_id: string
  reasoning: string
}

export interface MatchedReference {
  reference_id: string
  title: string
  source_type: string
  similarity_score: number
  domain: string
  trust_score: number
  relevant_snippet: string
  created_at: string
  updated_at: string
}

export interface Proposal {
  id: string
  topic_id: string
  priority: 'critical' | 'high' | 'medium' | 'low'
  title: string
  description: string
  current_content: string
  suggested_content: string
  reasoning: string
  reference_sources: string[]
  estimated_effort: number
  confidence: number
  created_at: string
  updated_at: string
  applied: boolean
  rejected: boolean
}

export interface ValidationTask {
  task_id: string
  status: 'queued' | 'processing' | 'completed' | 'failed'
  estimated_time: number
}

export interface ValidationTaskStatus {
  task_id: string
  status: string
  progress: number
  total: number
  current: number
  error?: string
  results?: ValidationResult[]
}

export interface ProposalListResponse {
  proposals: Proposal[]
  total: number
  topic_id: string
}

export interface UploadResponse {
  uploaded_count: number
  failed_count: number
  topic_ids: string[]
}
