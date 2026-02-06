/**
 * Dataview Integration for ITPE Plugin
 *
 * Obsidian Dataview 플러그인과의 통합을 제공합니다.
 * Dataview가 설치되지 않은 경우 수동 파싱으로 대체합니다.
 */
import { App, TFile, TFolder, Vault } from "obsidian";
import type { ParsedTopic } from "./topic-parser";
import { TopicParser } from "./topic-parser";
import { Logger } from "../utils/logger";

// ============================================================================
// Dataview Integration Types
// ============================================================================

/**
 * Dataview 페이지 정보 (내부 타입)
 */
interface DataviewPage {
	file: {
		path: string;
		name: string;
		ctime: number;
		mtime: number;
		tags: string[];
	};
	domain?: string;
	status?: string;
	[key: string]: unknown;
}

/**
 * Dataview API 인터페이스 (타입 정의)
 */
interface DataviewApi {
	pages(query?: string): DataviewPage[];
	page(path: string): DataviewPage | null;
}

// ============================================================================
// Dataview Integration Class
// ============================================================================

/**
 * Dataview Integration
 *
 * Dataview 플러그인을 통한 토픽 조회 및 메타데이터 추출 기능을 제공합니다.
 * Dataview가 설치되지 않은 경우 수동 파싱으로 대체합니다.
 */
export class DataviewIntegration {
	private app: App;
	private logger: Logger;
	private topicParser: TopicParser;
	private _enabled: boolean;

	constructor(app: App, logger: Logger, topicParser: TopicParser) {
		this.app = app;
		this.logger = logger;
		this.topicParser = topicParser;
		this._enabled = this.checkDataviewAvailable();
	}

	/**
	 * Dataview 플러그인 사용 가능 여부
	 */
	get enabled(): boolean {
		return this._enabled;
	}

	/**
	 * Dataview 플러그인 설치 및 활성화 확인
	 *
	 * @private
	 * @returns Dataview 사용 가능 여부
	 */
	private checkDataviewAvailable(): boolean {
		try {
			// @ts-expect-error - Dataview는 Obsidian의 선택적 플러그인
			const dataview = this.app.plugins.plugins.dataview;
			return !!dataview && typeof dataview.pages === "function";
		} catch {
			return false;
		}
	}

	/**
	 * Dataview를 통한 토픽 조회
	 *
	 * @param domain - 필터링할 도메인 (선택)
	 * @returns 조회된 토픽 배열
	 */
	async queryTopics(domain?: string): Promise<ParsedTopic[]> {
		if (!this._enabled) {
			this.logger.warn("Dataview plugin not available, using manual parsing");
			return this.manualTopicScan();
		}

		try {
			const dataview = this.getDataviewApi();

			// Dataview 쿼리 생성
			const query = domain ? `#ITPE and "${domain}"` : "#ITPE";

			const pages = dataview.pages(query);

			const topics: ParsedTopic[] = [];

			for (const page of pages) {
				const file = this.app.vault.getAbstractFileByPath(page.file.path);
				if (file instanceof TFile) {
					const topic = await this.topicParser.parseFile(file);
					if (topic) {
						topics.push(topic);
					}
				}
			}

			this.logger.info(`Dataview query found ${topics.length} topics`);
			return topics;
		} catch (error) {
			this.logger.error("Dataview query failed, falling back to manual scan", error);
			return this.manualTopicScan();
		}
	}

	/**
	 * 토픽 메타데이터 조회 (Dataview 사용)
	 *
	 * @param filePath - 파일 경로
	 * @returns 토픽 메타데이터 또는 null
	 */
	async getTopicMetadata(filePath: string): Promise<Record<string, unknown> | null> {
		if (!this._enabled) {
			return null;
		}

		try {
			const dataview = this.getDataviewApi();
			const page = dataview.page(filePath);

			if (!page) {
				return null;
			}

			return {
				domain: page.domain,
				status: page.status,
				tags: page.file.tags,
				created: page.file.ctime,
				modified: page.file.mtime,
			};
		} catch (error) {
			this.logger.error(`Failed to get metadata for ${filePath}:`, error);
			return null;
		}
	}

	/**
	 * 특정 폴더의 토픽 조회
	 *
	 * @param folderPath - 폴더 경로
	 * @returns 조회된 토픽 배열
	 */
	async getTopicsFromFolder(folderPath: string): Promise<ParsedTopic[]> {
		const topics: ParsedTopic[] = [];

		try {
			if (this._enabled) {
				// Dataview 사용
				const dataview = this.getDataviewApi();
				const pages = dataview.pages(`"${folderPath}"`);

				for (const page of pages) {
					const file = this.app.vault.getAbstractFileByPath(page.file.path);
					if (file instanceof TFile) {
						const topic = await this.topicParser.parseFile(file);
						if (topic) {
							topics.push(topic);
						}
					}
				}
			} else {
				// 수동 폴더 스캔
				const folder = this.app.vault.getAbstractFileByPath(folderPath);
				if (folder instanceof TFolder) {
					const files = this.getMarkdownFilesInFolder(folder);
					for (const file of files) {
						const topic = await this.topicParser.parseFile(file);
						if (topic) {
							topics.push(topic);
						}
					}
				}
			}
		} catch (error) {
			this.logger.error(`Failed to get topics from folder ${folderPath}:`, error);
		}

		return topics;
	}

	// ============================================================================
	// Private Methods
	// ============================================================================

	/**
	 * Dataview API 가져오기
	 *
	 * @private
	 * @returns Dataview API 인스턴스
	 * @throws Dataview를 사용할 수 없는 경우
	 */
	private getDataviewApi(): DataviewApi {
		// @ts-expect-error - Dataview는 선택적 플러그인
		return this.app.plugins.plugins.dataview as DataviewApi;
	}

	/**
	 * 수동 토픽 스캔 (Dataview 미설치 시)
	 *
	 * @private
	 * @returns 파싱된 토픽 배열
	 */
	private async manualTopicScan(): Promise<ParsedTopic[]> {
		const topics: ParsedTopic[] = [];
		const markdownFiles = this.app.vault.getMarkdownFiles();

		for (const file of markdownFiles) {
			try {
				const topic = await this.topicParser.parseFile(file);
				if (topic) {
					topics.push(topic);
				}
			} catch (error) {
				this.logger.error(`Failed to process file ${file.path}:`, error);
			}
		}

		this.logger.info(`Manual scan found ${topics.length} topics`);
		return topics;
	}

	/**
	 * 폴더 내 모든 마크다운 파일 재귀적으로 가져오기
	 *
	 * @private
	 * @param folder - 폴더 객체
	 * @returns 마크다운 파일 배열
	 */
	private getMarkdownFilesInFolder(folder: TFolder): TFile[] {
		const files: TFile[] = [];

		for (const child of folder.children) {
			if (child instanceof TFile && child.extension === "md") {
				files.push(child);
			} else if (child instanceof TFolder) {
				files.push(...this.getMarkdownFilesInFolder(child));
			}
		}

		return files;
	}
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Dataview 플러그인 사용 가능 여부 확인
 *
 * @param app - Obsidian App 인스턴스
 * @returns Dataview 사용 가능 여부
 */
export function isDataviewAvailable(app: App): boolean {
	try {
		// @ts-expect-error - Dataview는 선택적 플러그인
		const dataview = app.plugins.plugins.dataview;
		return !!dataview && typeof dataview.pages === "function";
	} catch {
		return false;
	}
}

/**
 * Dataview Integration 인스턴스 생성
 *
 * @param app - Obsidian App 인스턴스
 * @param logger - Logger 인스턴스
 * @param topicParser - TopicParser 인스턴스
 * @returns DataviewIntegration 인스턴스
 */
export function createDataviewIntegration(
	app: App,
	logger: Logger,
	topicParser: TopicParser
): DataviewIntegration {
	return new DataviewIntegration(app, logger, topicParser);
}
