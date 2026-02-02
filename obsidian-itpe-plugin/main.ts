import { Plugin, TFile, Notice, Menu } from "obsidian";
import { ITPESettingTab } from "./settings";
import { DataviewExporter } from "./export";
import { SyncManager } from "./sync";
import {
	ITPEPluginSettings,
	DEFAULT_SETTINGS,
	Topic,
	EnhancementProposal,
	DataviewQueryResult,
} from "./types";

/**
 * ITPE Topic Enhancement Plugin
 *
 * Obsidian 플러그인으로 ITPE Topic Enhancement System과 동기화하여
 * 토픽 내용을 검증하고 개선 제안을 받습니다.
 */
export default class ITPEPlugin extends Plugin {
	settings: ITPEPluginSettings;
	exporter: DataviewExporter;
	syncManager: SyncManager;
	autoSyncIntervalId: number | null = null;

	/**
	 * 플러그인 로드
	 */
	async onload() {
		console.log("ITPE Topic Enhancement Plugin 로드 중...");

		// 설정 로드
		await this.loadSettings();

		// 모듈 초기화
		this.exporter = new DataviewExporter(this);
		this.syncManager = new SyncManager(this);

		// 리본 아이콘 추가
		this.addRibbonIcon("sync", "ITPE 동기화", () => {
			this.syncAllTopics();
		});

		// 명령 팔레트 명령 추가
		this.addCommands();

		// 컨텍스트 메뉴 추가
		this.addContextMenu();

		// 설정 탭 등록
		this.addSettingTab(new ITPESettingTab(this.app, this));

		// 자동 동기화 시작 (설정된 경우)
		if (this.settings.autoSync) {
			this.startAutoSync();
		}

		console.log("ITPE Topic Enhancement Plugin 로드 완료!");
	}

	/**
	 * 플러그인 언로드
	 */
	onunload() {
		this.stopAutoSync();
		console.log("ITPE Topic Enhancement Plugin 언로드됨");
	}

	/**
	 * 명령 팔레트 명령 추가
	 */
	private addCommands() {
		// Dataview JSON 내보내기
		this.addCommand({
			id: "export-dataview-json",
			name: "Dataview JSON 내보내기",
			callback: () => {
				this.exportDataviewToJson();
			},
		});

		// 현재 파일 동기화
		this.addCommand({
			id: "sync-current-file",
			name: "현재 파일 동기화",
			callback: () => {
				this.syncCurrentFile();
			},
		});

		// 전체 토픽 동기화
		this.addCommand({
			id: "sync-all-topics",
			name: "전체 토픽 동기화",
			callback: () => {
				this.syncAllTopics();
			},
		});

		// 제안 보기
		this.addCommand({
			id: "view-proposals",
			name: "제안 보기",
			callback: () => {
				this.viewProposals();
			},
		});

		// 제안 적용
		this.addCommand({
			id: "apply-proposals",
			name: "제안 적용",
			callback: () => {
				this.applyProposals();
			},
		});
	}

	/**
	 * 컨텍스트 메뉴 추가
	 */
	private addContextMenu() {
		// 파일 메뉴에 "ITPE로 동기화" 추가
		this.registerEvent(
			this.app.workspace.on("file-menu", (menu: Menu, file: TFile) => {
				menu.addItem((item) => {
					item.setTitle("ITPE로 동기화")
						.setIcon("sync")
						.onClick(() => {
							this.syncFile(file);
						});
				});
			})
		);
	}

	/**
	 * Dataview 쿼리 결과를 JSON으로 내보냅니다.
	 */
	async exportDataviewToJson(): Promise<void> {
		try {
			const result = await this.exporter.exportFromCurrentFile();

			if (!result.성공) {
				new Notice(`내보내기 실패: ${result.에러}`);
				return;
			}

			const topics = result.데이터;

			if (topics.length === 0) {
				new Notice("내보낼 토픽이 없습니다.");
				return;
			}

			// 클립보드에 복사
			await this.exporter.copyToClipboard(topics);
			new Notice(`${topics.length}개 토픽이 클립보드에 복사되었습니다.`);

			// 파일로도 저장
			await this.exporter.saveToFile(topics);
			new Notice(`itpe-topics.json 파일이 생성되었습니다.`);
		} catch (error) {
			new Notice(`내보내기 실패: ${error}`);
			console.error("Dataview 내보내기 실패:", error);
		}
	}

	/**
	 * 현재 파일을 동기화합니다.
	 */
	async syncCurrentFile(): Promise<void> {
		const activeFile = this.app.workspace.getActiveFile();
		if (!activeFile) {
			new Notice("활성 파일이 없습니다.");
			return;
		}

		await this.syncFile(activeFile);
	}

	/**
	 * 특정 파일을 동기화합니다.
	 */
	async syncFile(file: TFile): Promise<void> {
		try {
			// Dataview에서 토픽 추출
			const content = await this.app.vault.read(file);
			const dataviewBlocks = this.exporter["extractDataviewBlocks"](content);

			if (dataviewBlocks.length === 0) {
				new Notice("이 파일에는 Dataview 쿼리가 없습니다.");
				return;
			}

			// 토픽 데이터 추출
			const topics: Topic[] = [];
			for (const block of dataviewBlocks) {
				const blockTopics = await this.exporter["extractTopicsFromDataview"](block);
				topics.push(...blockTopics);
			}

			if (topics.length === 0) {
				new Notice("이 파일에서 토픽을 찾을 수 없습니다.");
				return;
			}

			// 동기화
			new Notice(`${topics.length}개 토픽 동기화 시작...`);
			await this.syncManager.fullSync(topics);
		} catch (error) {
			new Notice(`동기화 실패: ${error}`);
			console.error("파일 동기화 실패:", error);
		}
	}

	/**
	 * 모든 토픽을 동기화합니다.
	 */
	async syncAllTopics(): Promise<{ count: number }> {
		try {
			new Notice("모든 토픽 동기화 시작...");

			// 모든 마크다운 파일 스캔
			const markdownFiles = this.app.vault.getMarkdownFiles();

			// 토픽 추출
			const allTopics: Topic[] = [];

			for (const file of markdownFiles) {
				try {
					const content = await this.app.vault.read(file);
					const dataviewBlocks = this.exporter["extractDataviewBlocks"](content);

					for (const block of dataviewBlocks) {
						const topics = await this.exporter["extractTopicsFromDataview"](block);
						allTopics.push(...topics);
					}
				} catch (error) {
					console.error(`파일 처리 중 오류 (${file.path}):`, error);
				}
			}

			if (allTopics.length === 0) {
				new Notice("동기화할 토픽이 없습니다.");
				return { count: 0 };
			}

			// 동기화 실행
			const result = await this.syncManager.fullSync(allTopics);

			new Notice(`동기화 완료: ${result.count}개 제안 생성됨`);

			return { count: result.count };
		} catch (error) {
			new Notice(`동기화 실패: ${error}`);
			console.error("전체 동기화 실패:", error);
			return { count: 0 };
		}
	}

	/**
	 * 제안을 봅니다.
	 */
	async viewProposals(): Promise<void> {
		const activeFile = this.app.workspace.getActiveFile();
		if (!activeFile) {
			new Notice("활성 파일이 없습니다.");
			return;
		}

		try {
			// 현재 파일에서 토픽 ID 추출
			const topicId = this.exporter["generateTopicId"](activeFile.path);

			// 제안 조회
			const response = await this.syncManager.getProposals(topicId);

			if (response.total === 0) {
				new Notice("이 토픽에 대한 제안이 없습니다.");
				return;
			}

			// 제안 표시 (모달 또는 새 파일)
			this.displayProposals(response.proposals, topicId);
		} catch (error) {
			new Notice(`제안 조회 실패: ${error}`);
			console.error("제안 조회 실패:", error);
		}
	}

	/**
	 * 제안을 표시합니다.
	 */
	private displayProposals(proposals: EnhancementProposal[], topicId: string): void {
		// 새 노트에 제안 내용 작성
		let content = `# 제안 목록\n\n`;
		content += `토픽 ID: ${topicId}\n`;
		content += `총 ${proposals.length}개의 제안\n\n`;
		content += `---\n\n`;

		for (const proposal of proposals) {
			content += `## ${proposal.title}\n\n`;
			content += `**우선순위:** ${proposal.priority}\n`;
			content += `**대상 필드:** ${proposal.target_field}\n`;
			content += `**신뢰도:** ${(proposal.confidence_score * 100).toFixed(1)}%\n\n`;
			content += `### 설명\n${proposal.description}\n\n`;
			content += `### 기존 내용\n${proposal.original_content}\n\n`;
			content += `### 제안 내용\n${proposal.suggested_content}\n\n`;

			if (proposal.references.length > 0) {
				content += `### 참조\n`;
				proposal.references.forEach((ref) => {
					content += `- ${ref}\n`;
				});
				content += `\n`;
			}

			content += `---\n\n`;
		}

		// 새 파일 생성
		const filename = `제안-${new Date().toISOString().slice(0, 10)}.md`;
		this.app.vault.create(filename, content);

		new Notice(`${proposals.length}개 제안이 ${filename}에 작성되었습니다.`);
	}

	/**
	 * 제안을 적용합니다.
	 */
	async applyProposals(): Promise<void> {
		const activeFile = this.app.workspace.getActiveFile();
		if (!activeFile) {
			new Notice("활성 파일이 없습니다.");
			return;
		}

		try {
			// 현재 파일에서 토픽 ID 추출
			const topicId = this.exporter["generateTopicId"](activeFile.path);

			// 제안 조회
			const response = await this.syncManager.getProposals(topicId);

			if (response.total === 0) {
				new Notice("적용할 제안이 없습니다.");
				return;
			}

			// 첫 번째 제안 적용 (개선 필요: 사용자 선택)
			const proposal = response.proposals[0];

			// 백엔드에 제안 적용 요청
			await this.syncManager.applyProposal(proposal.id, topicId);

			// 로컬 파일에도 적용
			const topic = {
				id: topicId,
				metadata: {
					file_path: activeFile.path,
					file_name: activeFile.name,
					folder: activeFile.parent?.path || "",
					domain: "신기술" as any,
					exam_frequency: "medium" as any,
				},
			} as Topic;

			await this.syncManager["applyProposalToFile"](proposal, topic);
		} catch (error) {
			new Notice(`제안 적용 실패: ${error}`);
			console.error("제안 적용 실패:", error);
		}
	}

	/**
	 * API 연결을 테스트합니다.
	 */
	async testApiConnection(): Promise<boolean> {
		return await this.syncManager.testConnection();
	}

	/**
	 * 자동 동기화를 시작합니다.
	 */
	startAutoSync(): void {
		this.stopAutoSync(); // 기존 인터벌 정리

		const intervalMs = this.settings.syncInterval * 60 * 1000;

		this.autoSyncIntervalId = window.setInterval(async () => {
			if (this.settings.autoSync) {
				await this.syncAllTopics();
			}
		}, intervalMs);

		console.log(`자동 동기화 시작: ${this.settings.syncInterval}분마다`);
	}

	/**
	 * 자동 동기화를 중지합니다.
	 */
	stopAutoSync(): void {
		if (this.autoSyncIntervalId !== null) {
			window.clearInterval(this.autoSyncIntervalId);
			this.autoSyncIntervalId = null;
			console.log("자동 동기화 중지");
		}
	}

	/**
	 * 자동 동기화를 재시작합니다.
	 */
	restartAutoSync(): void {
		if (this.settings.autoSync) {
			this.startAutoSync();
		}
	}

	/**
	 * 설정을 로드합니다.
	 */
	async loadSettings() {
		this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
	}

	/**
	 * 설정을 저장합니다.
	 */
	async saveSettings() {
		await this.saveData(this.settings);
	}
}
