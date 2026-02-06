/**
 * Topic File Parser for ITPE Plugin
 *
 * Parses markdown files with ITPE topic format and extracts structured data.
 */
import { TFile, Vault } from "obsidian";
import { nanoid } from "nanoid";
import {
	DomainEnum,
	type Topic,
	type TopicMetadata,
	type TopicContent,
	type TopicCompletionStatus,
} from "../api/types";
import { Logger } from "../utils/logger";

// ============================================================================
// Parser Types
// ============================================================================

/**
 * 파싱된 토픽 데이터 (내부 사용)
 */
export interface ParsedTopic {
	id: string;
	metadata: TopicMetadata;
	content: TopicContent;
	completion: TopicCompletionStatus;
}

/**
 * YAML Frontmatter 파싱 결과
 */
interface FrontmatterData {
	tags?: string[];
	domain?: DomainEnum;
	status?: string;
	[key: string]: unknown;
}

// ============================================================================
// Topic Parser Class
// ============================================================================

/**
 * Topic File Parser
 *
 * ITPE 형식의 마크다운 파일에서 토픽 데이터를 추출합니다.
 */
export class TopicParser {
	private vault: Vault;
	private logger: Logger;

	/**
	 * 유효한 도메인 목록
	 */
	private static readonly VALID_DOMAINS = [
		DomainEnum.SW,
		DomainEnum.정보보안,
		DomainEnum.신기술,
		DomainEnum.네트워크,
		DomainEnum.데이터베이스,
	];

	constructor(vault: Vault, logger: Logger) {
		this.vault = vault;
		this.logger = logger;
	}

	/**
	 * 단일 토픽 파일 파싱
	 *
	 * @param file - Obsidian TFile 객체
	 * @returns 파싱된 토픽 데이터 또는 null (ITPE 태그가 없는 경우)
	 */
	async parseFile(file: TFile): Promise<ParsedTopic | null> {
		try {
			const content = await this.vault.read(file);

			// ITPE 태그가 없는 파일은 건너뜀
			if (!this.isTopicFile(content)) {
				return null;
			}

			// YAML frontmatter 파싱
			const frontmatter = this.parseFrontmatter(content);

			// 도메인 추출 (frontmatter 또는 폴더에서)
			const domain = this.extractDomain(file, frontmatter);

			// 섹션 파싱
			const sections = this.parseSections(content);

			const parsedTopic: ParsedTopic = {
				id: nanoid(),
				metadata: {
					file_path: file.path,
					file_name: file.name,
					folder: file.parent?.path || "",
					domain: domain,
				},
				content: {
					리드문: sections.리드문 || "",
					정의: sections.정의 || "",
					키워드: sections.키워드 || [],
					해시태그: sections.해시태그 || "",
					암기: sections.암기 || "",
				},
				completion: {
					리드문: !!sections.리드문?.length,
					정의: !!sections.정의?.length,
					키워드: Array.isArray(sections.키워드) && sections.키워드.length > 0,
					해시태그: !!sections.해시태그?.length,
					암기: !!sections.암기?.length,
				},
			};

			this.logger.debug(`Parsed topic: ${parsedTopic.id} from ${file.path}`);
			return parsedTopic;
		} catch (error) {
			this.logger.error(`Failed to parse file ${file.path}:`, error);
			return null;
		}
	}

	/**
	 * 전체 토픽 파일 파싱
	 *
	 * @param domainFolders - 특정 도메인 폴더만 파싱할 경우 지정
	 * @returns 파싱된 토픽 배열
	 */
	async parseAllTopics(domainFolders?: string[]): Promise<ParsedTopic[]> {
		const files = this.vault.getMarkdownFiles();
		const topics: ParsedTopic[] = [];

		for (const file of files) {
			// 도메인 폴더 필터링
			if (domainFolders && domainFolders.length > 0) {
				const folder = file.parent?.path || "";
				if (!domainFolders.includes(folder)) {
					continue;
				}
			}

			const topic = await this.parseFile(file);
			if (topic) {
				topics.push(topic);
			}
		}

		this.logger.info(`Parsed ${topics.length} topics from ${files.length} markdown files`);
		return topics;
	}

	/**
	 * ParsedTopic을 API Topic 형식으로 변환
	 *
	 * @param parsed - 파싱된 토픽 데이터
	 * @returns API 형식의 토픽 데이터
	 */
	toApiTopic(parsed: ParsedTopic): Topic {
		return {
			id: parsed.id,
			metadata: parsed.metadata,
			content: parsed.content,
			completion: parsed.completion,
		};
	}

	/**
	 * 파일이 토픽 파일인지 확인
	 *
	 * @param content - 파일 내용
	 * @returns 토픽 파일 여부
	 */
	isTopicFile(content: string): boolean {
		// ITPE 태그 확인
		if (!content.includes("ITPE")) {
			return false;
		}

		// 토픽 지표 확인
		const hasTopicIndicators =
			content.includes("## 리드문") ||
			content.includes("## 정의") ||
			content.includes("## 키워드") ||
			content.includes("#ITPE");

		return hasTopicIndicators;
	}

	// ============================================================================
	// Private Methods
	// ============================================================================

	/**
	 * YAML frontmatter 파싱
	 *
	 * @param content - 마크다운 내용
	 * @returns 파싱된 frontmatter 데이터
	 */
	private parseFrontmatter(content: string): FrontmatterData {
		const frontmatterRegex = /^---\n([\s\S]*?)\n---/;
		const match = content.match(frontmatterRegex);

		if (!match) {
			return {};
		}

		const frontmatter: FrontmatterData = {};
		const lines = match[1].split("\n");

		for (const line of lines) {
			const colonIndex = line.indexOf(":");
			if (colonIndex === -1) continue;

			const key = line.slice(0, colonIndex).trim();
			let value: unknown = line.slice(colonIndex + 1).trim();

			// 배열 값 파싱 (예: [ITPE, SW, 토픽])
			if (typeof value === "string" && value.startsWith("[") && value.endsWith("]")) {
				value = value
					.slice(1, -1)
					.split(",")
					.map((s) => s.trim())
					.filter((s) => s.length > 0);
			}

			// 문자열 값의 따옴표 제거
			if (typeof value === "string" && value.startsWith('"') && value.endsWith('"')) {
				value = value.slice(1, -1);
			}

			frontmatter[key] = value;
		}

		return frontmatter;
	}

	/**
	 * 도메인 추출 (frontmatter 또는 폴더에서)
	 *
	 * @param file - 파일 객체
	 * @param frontmatter - frontmatter 데이터
	 * @returns 도메인 값
	 */
	private extractDomain(file: TFile, frontmatter: FrontmatterData): DomainEnum {
		// 1. frontmatter에서 domain 확인
		const domainFromFrontmatter = frontmatter.domain as DomainEnum;
		if (domainFromFrontmatter && TopicParser.VALID_DOMAINS.includes(domainFromFrontmatter)) {
			return domainFromFrontmatter;
		}

		// 2. 폴더 경로에서 도메인 추출
		const folder = file.parent?.path || "";
		for (const domain of TopicParser.VALID_DOMAINS) {
			if (folder.includes(domain)) {
				return domain;
			}
		}

		// 3. 기본값: SW
		return DomainEnum.SW;
	}

	/**
	 * 콘텐츠 섹션 파싱 (리드문, 정의, 키워드, 해시태그, 암기)
	 *
	 * @param content - 마크다운 내용
	 * @returns 파싱된 섹션 데이터
	 */
	private parseSections(content: string): Partial<TopicContent> {
		const sections: Partial<TopicContent> = {};

		// frontmatter 제거
		content = content.replace(/^---\n[\s\S]*?\n---\n*/, "");

		// 섹션 패턴 정의
		const sectionPatterns: Record<string, RegExp> = {
			리드문: /##\s*리드문\s*\n([\s\S]*?)(?=\n##|$)/i,
			정의: /##\s*정의\s*\n([\s\S]*?)(?=\n##|$)/i,
			키워드: /##\s*키워드\s*\n([\s\S]*?)(?=\n##|$)/i,
			해시태그: /##\s*해시태그\s*\n([\s\S]*?)(?=\n##|$)/i,
			암기: /##\s*암기(?:\s*포인트)?\s*\n([\s\S]*?)(?=\n##|$)/i,
		};

		// 텍스트 섹션 파싱 (리드문, 정의, 암기)
		for (const key of ["리드문", "정의", "암기"] as const) {
			const match = content.match(sectionPatterns[key]);
			if (match) {
				sections[key] = this.cleanText(match[1]);
			}
		}

		// 키워드 리스트 파싱
		const keywordMatch = content.match(sectionPatterns.키워드);
		if (keywordMatch) {
			sections.키워드 = this.extractListItems(keywordMatch[1]);
		}

		// 해시태그 파싱
		const hashtagMatch = content.match(sectionPatterns.해시태그);
		if (hashtagMatch) {
			sections.해시태그 = this.cleanText(hashtagMatch[1]);
		}

		return sections;
	}

	/**
	 * 리스트 아이템 추출
	 *
	 * @param text - 텍스트 내용
	 * @returns 추출된 리스트 아이템 배열
	 */
	private extractListItems(text: string): string[] {
		const keywords: string[] = [];
		const lines = text.split("\n");

		for (const line of lines) {
			const cleaned = line.replace(/^[-*]\s*/, "").trim();
			if (cleaned) {
				keywords.push(cleaned);
			}
		}

		return keywords;
	}

	/**
	 * 텍스트 정리
	 *
	 * @param text - 원본 텍스트
	 * @returns 정리된 텍스트
	 */
	private cleanText(text: string): string {
		return text.trim().replace(/\s+/g, " ");
	}
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * 토픽 ID 생성 (파일 경로 기반)
 *
 * @param filePath - 파일 경로
 * @returns 토픽 ID
 */
export function generateTopicId(filePath: string): string {
	const normalized = filePath.toLowerCase().replace(/\s+/g, "-");
	const hash = simpleHash(normalized);
	return `topic-${hash}`;
}

/**
 * 간단한 해시 함수
 *
 * @param str - 입력 문자열
 * @returns 해시 값
 */
function simpleHash(str: string): string {
	let hash = 0;
	for (let i = 0; i < str.length; i++) {
		const charCode = str.charCodeAt(i);
		hash = ((hash << 5) - hash) + charCode;
		hash = hash & hash; // 32비트 정수로 변환
	}
	return Math.abs(hash).toString(16);
}
