/**
 * Proposal Modal for ITPE Plugin
 *
 * 제안 모달 - 보강 제안 목록을 표시하고 적용하는 모달 컴포넌트
 */
import { App, Modal, Notice } from "obsidian";
import { EnhancementProposal, ProposalPriority } from "../api/types";
import { Logger } from "../utils/logger";

/**
 * Proposal Apply Callback
 */
interface ProposalApplyCallback {
	(proposal: EnhancementProposal): Promise<void> | void;
}

/**
 * Proposal Modal Callbacks
 */
interface ProposalModalCallbacks {
	onApply?: ProposalApplyCallback;
	onDismiss?: () => void;
}

/**
 * Priority 정의에 따른 정렬 순서
 */
const PRIORITY_ORDER: Record<ProposalPriority, number> = {
	[ProposalPriority.CRITICAL]: 0,
	[ProposalPriority.HIGH]: 1,
	[ProposalPriority.MEDIUM]: 2,
	[ProposalPriority.LOW]: 3,
};

/**
 * Priority 라벨 (한국어)
 */
const PRIORITY_LABELS: Record<ProposalPriority, string> = {
	[ProposalPriority.CRITICAL]: "[긴급]",
	[ProposalPriority.HIGH]: "[높음]",
	[ProposalPriority.MEDIUM]: "[중간]",
	[ProposalPriority.LOW]: "[낮음]",
};

/**
 * Proposal Modal Class
 *
 * 보강 제안 목록을 표시하고 제안을 적용하는 모달
 */
export class ProposalModal extends Modal {
	private proposals: EnhancementProposal[];
	private logger: Logger;
	private callbacks: ProposalModalCallbacks;
	private activeFileContent: string = "";
	private activeFilePath: string = "";

	constructor(
		app: App,
		proposals: EnhancementProposal[],
		logger: Logger,
		callbacks?: ProposalModalCallbacks
	) {
		super(app);
		this.proposals = proposals;
		this.logger = logger;
		this.callbacks = callbacks || {};

		// 현재 활성 파일 정보 저장 (나중에 사용을 위해)
		const activeFile = this.app.workspace.getActiveFile();
		if (activeFile) {
			this.activeFilePath = activeFile.path;
		}
	}

	/**
	 * 모달이 열릴 때 호출되는 메서드
	 */
	async onOpen(): Promise<void> {
		const { contentEl } = this;
		contentEl.empty();
		contentEl.addClass("itpe-proposal-modal");

		// 활성 파일 콘텐츠 읽기
		const activeFile = this.app.workspace.getActiveFile();
		if (activeFile) {
			this.activeFileContent = await this.app.vault.read(activeFile);
			this.activeFilePath = activeFile.path;
		}

		// 헤더
		const header = contentEl.createEl("h2", {
			text: `보강 제안 (${this.proposals.length}개)`,
		});

		if (this.proposals.length === 0) {
			contentEl.createEl("p", { text: "표시할 제안이 없습니다." });
			return;
		}

		// 제안 목록 컨테이너
		const listContainer = contentEl.createDiv("itpe-proposal-list");

		// 우선순위별 정렬
		const sortedProposals = this.sortByPriority(this.proposals);

		// 제안 렌더링
		for (const proposal of sortedProposals) {
			this.renderProposal(listContainer, proposal);
		}

		// 푸터 버튼
		this.renderFooter(contentEl);
	}

	/**
	 * 모달이 닫힐 때 호출되는 메서드
	 */
	onClose(): void {
		const { contentEl } = this;
		contentEl.empty();

		if (this.callbacks.onDismiss) {
			this.callbacks.onDismiss();
		}
	}

	/**
	 * 제안 렌더링
	 */
	private renderProposal(container: HTMLElement, proposal: EnhancementProposal): void {
		const proposalEl = container.createDiv("itpe-proposal");
		proposalEl.addClass(`itpe-proposal-${proposal.priority}`);

		// 우선순위 배지와 제목 컨테이너
		const headerEl = proposalEl.createDiv("itpe-proposal-header");

		// 우선순위 배지
		const badge = headerEl.createEl("span", {
			text: PRIORITY_LABELS[proposal.priority],
			cls: `itpe-badge itpe-badge-${proposal.priority}`,
		});

		// 제목
		const title = headerEl.createEl("h3", { text: proposal.title });

		// 설명
		const desc = proposalEl.createDiv("itpe-proposal-desc");
		desc.createEl("p", { text: proposal.description });

		// 현재 콘텐츠
		const currentEl = proposalEl.createDiv("itpe-proposal-current");
		currentEl.createEl("strong", { text: "현재: " });
		currentEl.createEl("pre", {
			text: proposal.current_content || "(비어있음)",
			cls: "itpe-content-current",
		});

		// 제안된 콘텐츠
		const suggestedEl = proposalEl.createDiv("itpe-proposal-suggested");
		suggestedEl.createEl("strong", { text: "제안: " });
		suggestedEl.createEl("pre", {
			text: proposal.suggested_content,
			cls: "itpe-content-suggested",
		});

		// 근거 (Reasoning)
		const reasoningEl = proposalEl.createDiv("itpe-proposal-reasoning");
		reasoningEl.createEl("label", { text: "근거: " });
		reasoningEl.createEl("p", { text: proposal.reasoning });

		// 메타데이터
		const metaEl = proposalEl.createDiv("itpe-proposal-meta");

		const effortEl = metaEl.createEl("span", {
			cls: "itpe-meta-effort",
		});
		effortEl.createEl("small", { text: `예상 시간: ${proposal.estimated_effort}분` });

		const confidenceEl = metaEl.createEl("span", {
			cls: "itpe-meta-confidence",
		});
		confidenceEl.createEl("small", {
			text: `신뢰도: ${Math.round(proposal.confidence * 100)}%`,
		});

		// 참고소스 (있는 경우)
		if (proposal.reference_sources && proposal.reference_sources.length > 0) {
			const sourcesEl = proposalEl.createDiv("itpe-proposal-sources");
			sourcesEl.createEl("label", { text: "참고소스: " });
			const sourcesList = sourcesEl.createEl("ul");
			for (const source of proposal.reference_sources) {
				sourcesList.createEl("li", { text: source });
			}
		}

		// 적용 버튼
		const applyBtn = proposalEl.createEl("button", {
			text: "적용",
			cls: "itpe-apply-btn mod-cta",
		});
		applyBtn.onclick = () => this.handleApply(proposal, applyBtn);
	}

	/**
	 * 푸터 렌더링
	 */
	private renderFooter(container: HTMLElement): void {
		const footer = container.createDiv("itpe-modal-footer");

		const applyAllBtn = footer.createEl("button", {
			text: "모두 적용",
			cls: "itpe-apply-all-btn",
		});
		applyAllBtn.onclick = () => this.handleApplyAll();

		const closeBtn = footer.createEl("button", {
			text: "닫기",
			cls: "itpe-close-btn",
		});
		closeBtn.onclick = () => this.close();
	}

	/**
	 * 단일 제안 적용 처리
	 */
	private async handleApply(
		proposal: EnhancementProposal,
		button: HTMLButtonElement
	): Promise<void> {
		// 처리 중 버튼 비활성화
		button.disabled = true;
		button.textContent = "적용 중...";

		try {
			// 콜백이 있으면 실행
			if (this.callbacks.onApply) {
				await this.callbacks.onApply(proposal);
			}

			new Notice(`제안이 적용되었습니다: ${proposal.title}`);
			this.logger.info(`Applied proposal: ${proposal.id}`);

			// 적용된 제안 목록에서 제거
			this.proposals = this.proposals.filter((p) => p.id !== proposal.id);

			// 모든 제안이 적용되면 모달 닫기
			if (this.proposals.length === 0) {
				this.close();
			} else {
				// 모달 새로고침
				await this.onOpen();
			}
		} catch (error) {
			new Notice(
				`제안 적용 실패: ${error instanceof Error ? error.message : "Unknown error"}`
			);
			this.logger.error(`Failed to apply proposal ${proposal.id}`, error);
			button.disabled = false;
			button.textContent = "적용";
		}
	}

	/**
	 * 모든 제안 적용 처리
	 */
	private async handleApplyAll(): Promise<void> {
		const sortedProposals = this.sortByPriority([...this.proposals]);

		const successCount = { value: 0 };
		const failCount = { value: 0 };

		for (const proposal of sortedProposals) {
			try {
				if (this.callbacks.onApply) {
					await this.callbacks.onApply(proposal);
				}
				new Notice(`적용 완료: ${proposal.title}`);
				this.logger.info(`Applied proposal: ${proposal.id}`);
				successCount.value++;
			} catch (error) {
				new Notice(`적용 실패: ${proposal.title}`);
				this.logger.error(`Failed to apply proposal ${proposal.id}`, error);
				failCount.value++;
			}
		}

		// 결과 요약
		if (failCount.value === 0) {
			new Notice(`모든 제안이 성공적으로 적용되었습니다 (${successCount.value}개)`);
		} else {
			new Notice(
				`적용 완료: ${successCount.value}개, 실패: ${failCount.value}개`
			);
		}

		this.close();
	}

	/**
	 * 우선순위별 정렬
	 */
	private sortByPriority(proposals: EnhancementProposal[]): EnhancementProposal[] {
		return [...proposals].sort((a, b) => {
			const priorityA = PRIORITY_ORDER[a.priority];
			const priorityB = PRIORITY_ORDER[b.priority];

			// 우선순위가 다르면 우선순위 기준 정렬
			if (priorityA !== priorityB) {
				return priorityA - priorityB;
			}

			// 같은 우선순위면 신뢰도 기준 정렬 (높은 것 먼저)
			return b.confidence - a.confidence;
		});
	}
}
