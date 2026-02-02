#!/usr/bin/env python3
"""
Prompt Manager for ITPE Topic Enhancement
도메인별 프롬프트 관리 시스템
"""

import os
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional


class Domain(Enum):
    """9개 ITPE 도메인"""
    AI_TECH = "ai_tech"              # 신기술 (AI, ML, Cloud)
    SECURITY = "security"            # 정보보안
    NETWORK = "network"              # 네트워크
    DATABASE = "database"            # 데이터베이스
    SOFTWARE = "software"            # 소프트웨어 공학
    EMBEDDED = "embedded"            # 임베디드 시스템
    PROJECT_MGMT = "project_management"  # 프로젝트 관리
    OS = "os"                        # 운영체제
    ECOMMERCE = "ecommerce"          # 전자상거래

    @classmethod
    def from_keyword(cls, keyword: str) -> Optional['Domain']:
        """키워드로 도메인 매핑"""
        keyword_map = {
            # AI/ML/Cloud 키워드
            'ai': cls.AI_TECH,
            'ml': cls.AI_TECH,
            'machine learning': cls.AI_TECH,
            'deep learning': cls.AI_TECH,
            'cloud': cls.AI_TECH,
            'bigdata': cls.AI_TECH,

            # Security 키워드
            'security': cls.SECURITY,
            '암호': cls.SECURITY,
            'encryption': cls.SECURITY,
            'firewall': cls.SECURITY,
            'vpn': cls.SECURITY,

            # Network 키워드
            'network': cls.NETWORK,
            'osi': cls.NETWORK,
            'tcp': cls.NETWORK,
            'routing': cls.NETWORK,
            'switching': cls.NETWORK,

            # Database 키워드
            'database': cls.DATABASE,
            'sql': cls.DATABASE,
            'rdbms': cls.DATABASE,
            'nosql': cls.DATABASE,
            '정규화': cls.DATABASE,

            # Software 키워드
            'software': cls.SOFTWARE,
            'agile': cls.SOFTWARE,
            'scrum': cls.SOFTWARE,
            'testing': cls.SOFTWARE,
            'requirements': cls.SOFTWARE,

            # Embedded 키워드
            'embedded': cls.EMBEDDED,
            'mcu': cls.EMBEDDED,
            'rtos': cls.EMBEDDED,
            'firmware': cls.EMBEDDED,
            '임베디드': cls.EMBEDDED,

            # Project Management 키워드
            'project': cls.PROJECT_MGMT,
            'management': cls.PROJECT_MGMT,
            'risk': cls.PROJECT_MGMT,
            'schedule': cls.PROJECT_MGMT,
            'evm': cls.PROJECT_MGMT,

            # OS 키워드
            'os': cls.OS,
            'process': cls.OS,
            'memory': cls.OS,
            'filesystem': cls.OS,
            'deadlock': cls.OS,

            # E-commerce 키워드
            'commerce': cls.ECOMMERCE,
            'payment': cls.ECOMMERCE,
            'pg': cls.ECOMMERCE,
            'mobile payment': cls.ECOMMERCE,
            '전자상거래': cls.ECOMMERCE,
        }
        return keyword_map.get(keyword.lower())


class PromptType(Enum):
    """프롬프트 유형"""
    VALIDATION = "validation"  # 검증 프롬프트
    PROPOSAL = "proposals"     # 제안 프롬프트


class PromptManager:
    """프롬프트 관리자"""

    def __init__(self, base_path: str = "config/prompts"):
        self.base_path = Path(base_path)

    def get_prompt(self, domain: Domain, prompt_type: PromptType) -> str:
        """
        도메인별 프롬프트 로드

        Args:
            domain: 도메인 열거형
            prompt_type: 프롬프트 유형

        Returns:
            프롬프트 문자열
        """
        prompt_path = self.base_path / prompt_type.value / f"{domain.value}.txt"

        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt not found: {prompt_path}")

        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()

    def get_validation_prompt(self, domain: Domain) -> str:
        """검증 프롬프트 로드"""
        return self.get_prompt(domain, PromptType.VALIDATION)

    def get_proposal_prompt(self, domain: Domain) -> str:
        """제안 프롬프트 로드"""
        return self.get_prompt(domain, PromptType.PROPOSAL)

    def auto_detect_domain(self, text: str) -> Optional[Domain]:
        """
        텍스트 내용으로 도메인 자동 감지

        Args:
            text: 분석할 텍스트

        Returns:
            감지된 도메인 또는 None
        """
        text_lower = text.lower()

        # 키워드 점수 계산
        domain_scores = {domain: 0 for domain in Domain}

        for domain in Domain:
            # 도메인 이름 자체 점수
            if domain.value in text_lower:
                domain_scores[domain] += 10

            # 해시태그 점수
            if f"#{domain.value}" in text_lower:
                domain_scores[domain] += 15

        # 최고 점수 도메인 반환
        max_score = max(domain_scores.values())
        if max_score > 0:
            return max(domain_scores, key=domain_scores.get)

        return None

    def list_available_prompts(self) -> Dict[str, List[str]]:
        """
        사용 가능한 프롬프트 목록

        Returns:
            {prompt_type: [domains]}
        """
        available = {
            "validation": [],
            "proposals": []
        }

        for prompt_type in PromptType:
            type_path = self.base_path / prompt_type.value
            if type_path.exists():
                for prompt_file in type_path.glob("*.txt"):
                    domain_name = prompt_file.stem
                    available[prompt_type.value].append(domain_name)

        return available


# CLI 인터페이스
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ITPE Prompt Manager")
    parser.add_argument("--list", action="store_true", help="사용 가능한 프롬프트 목록")
    parser.add_argument("--domain", type=str, help="도메인 (ai_tech, security, network, etc.)")
    parser.add_argument("--type", type=str, choices=["validation", "proposal"],
                       help="프롬프트 유형")
    parser.add_argument("--detect", type=str, help="도메인 자동 감지 (텍스트 입력)")

    args = parser.parse_args()
    manager = PromptManager()

    if args.list:
        available = manager.list_available_prompts()
        print("=== 사용 가능한 프롬프트 ===")
        for prompt_type, domains in available.items():
            print(f"\n[{prompt_type}]")
            for domain in sorted(domains):
                print(f"  - {domain}")

    elif args.detect:
        detected = manager.auto_detect_domain(args.detect)
        if detected:
            print(f"감지된 도메인: {detected.value}")
        else:
            print("도메인을 감지할 수 없습니다")

    elif args.domain and args.type:
        try:
            domain = Domain(args.domain)
            prompt_type = PromptType(args.type + "s")  # proposals 폴더
            prompt = manager.get_prompt(domain, prompt_type)
            print(f"=== {args.domain} - {args.type} prompt ===")
            print(prompt[:500] + "..." if len(prompt) > 500 else prompt)
        except (ValueError, FileNotFoundError) as e:
            print(f"오류: {e}")

    else:
        parser.print_help()
