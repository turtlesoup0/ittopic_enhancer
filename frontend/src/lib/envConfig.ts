/**
 * 중앙화된 환경변수 설정 모듈
 *
 * 보안 규칙:
 * - 모든 환경변수는 이 모듈을 통해서만 접근해야 합니다
 * - import.meta.env를 직접 사용하는 것을 금지합니다
 * - 유효성 검사와 기본값을 중앙에서 관리합니다
 *
 * @module envConfig
 */

/**
 * 애플리케이션 환경설정 인터페이스
 */
interface AppConfig {
  apiBaseUrl: string
  apiKey: string
  isDevelopment: boolean
  isProduction: boolean
}

/**
 * 필수 환경변수가 누락된 경우 발생하는 에러
 */
class EnvConfigError extends Error {
  constructor(missingKeys: string[]) {
    super(`필수 환경변수가 누락되었습니다: ${missingKeys.join(', ')}`)
    this.name = 'EnvConfigError'
  }
}

/**
 * 환경변수 유효성을 검증하고 기본값을 적용합니다
 *
 * @param key - 환경변수 키
 * @param defaultValue - 기본값 (선택)
 * @param required - 필수 여부 (기본: false)
 * @returns 환경변수 값
 * @throws {EnvConfigError} 필수 환경변수가 누락된 경우
 */
function getEnvVar(
  key: string,
  defaultValue?: string,
  required: boolean = false
): string {
  const value = import.meta.env[key]

  if (value === undefined || value === '') {
    if (required && defaultValue === undefined) {
      throw new EnvConfigError([key])
    }
    return defaultValue || ''
  }

  return value
}

/**
 * 애플리케이션 설정을 로드합니다
 *
 * 주의: 이 함수는 앱 시작 시 한 번만 호출되어야 합니다
 */
function loadConfig(): AppConfig {
  // API 기본 URL (필수)
  const apiBaseUrl = getEnvVar(
    'VITE_API_BASE_URL',
    '/api/v1',
    false // 기본값이 있으므로 선택사항
  )

  // API 키 (선택 - 개발용)
  const apiKey = getEnvVar('VITE_API_KEY', '', false)

  // 환경 감지
  const isDevelopment = import.meta.env.DEV || false
  const isProduction = import.meta.env.PROD || false

  return {
    apiBaseUrl,
    apiKey,
    isDevelopment,
    isProduction,
  }
}

/**
 * 애플리케이션 설정 싱글톤 인스턴스
 */
let config: AppConfig | null = null

/**
 * 애플리케이션 설정을 가져옵니다
 *
 * @returns 애플리케이션 설정
 */
export function getEnvConfig(): AppConfig {
  if (!config) {
    config = loadConfig()
  }
  return config
}

/**
 * 설정을 다시 로드합니다 (테스트용)
 */
export function resetEnvConfig(): void {
  config = null
}

/**
 * 애플리케이션 설정 (내보내기용)
 */
export const envConfig = getEnvConfig()
