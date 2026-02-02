import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * 도메인별 색상 반환
 */
export function getDomainColor(domain: string): string {
  const colors: Record<string, string> = {
    '신기술': 'bg-blue-500',
    '정보보안': 'bg-green-500',
    '네트워크': 'bg-red-500',
    '데이터베이스': 'bg-purple-500',
    'SW': 'bg-indigo-500',
    '프로젝트관리': 'bg-pink-500',
  }
  return colors[domain] || 'bg-gray-500'
}
