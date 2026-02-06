/**
 * Validation Result Modal for ITPE Plugin
 *
 * Modal showing validation results with tabs and Korean text support.
 */
import { App, Modal, Notice } from "obsidian";
import type { ValidationResult, ContentGap, MatchedReference, GapType } from "../api/types";
import type { Logger } from "../utils/logger";

/**
 * Tab state for result modal
 */
type TabType = "gaps" | "references";

/**
 * Validation Result Modal
 */
export class ValidationResultModal extends Modal {
	private result: ValidationResult;
	private logger: Logger;
	private currentTab: TabType = "gaps";

	constructor(app: App, result: ValidationResult, logger: Logger) {
		super(app);
		this.result = result;
		this.logger = logger;
	}

	/**
	 * Open modal on display
	 */
	onOpen(): void {
		const { contentEl } = this;
		contentEl.empty();
		contentEl.addClass("itpe-result-modal");

		// Header
		contentEl.createEl("h2", { text: "검증 결과" });

		// Overall Score
		this.renderScore(contentEl);

		// Tabs
		this.renderTabs(contentEl);

		// Tab content
		const tabContent = contentEl.createDiv({ cls: "itpe-tab-content" });
		this.renderTabContent(tabContent);

		// Close button
		const buttonContainer = contentEl.createDiv({
			cls: "itpe-modal-buttons",
		});
		buttonContainer
			.createEl("button", { text: "닫기" })
			.addEventListener("click", () => this.close());
	}

	/**
	 * Close modal
	 */
	onClose(): void {
		const { contentEl } = this;
		contentEl.empty();
	}

	/**
	 * Render overall score section
	 */
	private renderScore(container: HTMLElement): void {
		const scoreEl = container.createDiv({ cls: "itpe-score-container" });

		const scoreValue = Math.round(this.result.overall_score * 100);
		const color = this.getScoreColor(scoreValue);

		// Main score
		const mainScore = scoreEl.createEl("div", {
			cls: `itpe-score itpe-score-${color}`,
		});
		mainScore.createEl("span", { text: "종합 점수: " });
		mainScore.createEl("strong", { text: `${scoreValue}/100` });

		// Sub-scores
		const subScores = scoreEl.createDiv({ cls: "itpe-sub-scores" });

		subScores.createEl("span", {
			text: `완전성: ${Math.round(this.result.field_completeness_score * 100)}%`,
			cls: "itpe-sub-score",
		});
		subScores.createEl("span", {
			text: `정확성: ${Math.round(this.result.content_accuracy_score * 100)}%`,
			cls: "itpe-sub-score",
		});
		subScores.createEl("span", {
			text: `참조 적합성: ${Math.round(this.result.reference_coverage_score * 100)}%`,
			cls: "itpe-sub-score",
		});
	}

	/**
	 * Render tab buttons
	 */
	private renderTabs(container: HTMLElement): void {
		const tabsContainer = container.createDiv({ cls: "itpe-tabs" });

		const gapsBtn = tabsContainer.createEl("button", {
			text: `검증 격차 (${this.result.gaps.length})`,
			cls: this.currentTab === "gaps" ? "itpe-tab-active" : "",
		});

		const refsBtn = tabsContainer.createEl("button", {
			text: `참조 문서 (${this.result.matched_references.length})`,
			cls: this.currentTab === "references" ? "itpe-tab-active" : "",
		});

		// Tab switching
		gapsBtn.addEventListener("click", () => {
			this.currentTab = "gaps";
			this.refreshContent(container);
		});

		refsBtn.addEventListener("click", () => {
			this.currentTab = "references";
			this.refreshContent(container);
		});
	}

	/**
	 * Refresh modal content when tab changes
	 */
	private refreshContent(container: HTMLElement): void {
		const tabContent = container.querySelector(".itpe-tab-content") as HTMLElement;
		if (tabContent) {
			tabContent.empty();
			this.renderTabContent(tabContent);

			// Update tab button states
			const buttons = container.querySelectorAll(".itpe-tabs button");
			buttons.forEach((btn, index) => {
				if ((index === 0 && this.currentTab === "gaps") ||
					(index === 1 && this.currentTab === "references")) {
					btn.addClass("itpe-tab-active");
				} else {
					btn.removeClass("itpe-tab-active");
				}
			});
		}
	}

	/**
	 * Render tab content based on current tab
	 */
	private renderTabContent(container: HTMLElement): void {
		if (this.currentTab === "gaps") {
			this.renderGaps(container);
		} else {
			this.renderReferences(container);
		}
	}

	/**
	 * Render gaps tab content
	 */
	private renderGaps(container: HTMLElement): void {
		if (this.result.gaps.length === 0) {
			container.createEl("p", {
				text: "발견된 검증 격차가 없습니다. 훌륭합니다!",
				cls: "itpe-no-gaps",
			});
			return;
		}

		// Sort by priority and confidence
		const sortedGaps = [...this.result.gaps].sort((a, b) => {
			const priorityOrder: Record<GapType, number> = {
				incomplete_definition: 0,
				missing_examples: 1,
				insufficient_depth: 2,
				weak_keywords: 3,
			};
			const priorityA = priorityOrder[a.gap_type] ?? 999;
			const priorityB = priorityOrder[b.gap_type] ?? 999;
			return priorityA - priorityB || (b.confidence - a.confidence);
		});

		for (const gap of sortedGaps) {
			this.renderGapItem(container, gap);
		}
	}

	/**
	 * Render single gap item
	 */
	private renderGapItem(container: HTMLElement, gap: ContentGap): void {
		const gapEl = container.createDiv({
			cls: `itpe-gap itpe-gap-${gap.gap_type}`,
		});

		// Header with type label and confidence
		const header = gapEl.createDiv({ cls: "itpe-gap-header" });
		header.createEl("span", {
			text: this.getGapTypeLabel(gap.gap_type),
			cls: "itpe-gap-type",
		});
		header.createEl("span", {
			text: `신뢰도: ${Math.round(gap.confidence * 100)}%`,
			cls: "itpe-gap-confidence",
		});

		// Field name
		gapEl.createEl("h4", {
			text: gap.field_name,
			cls: "itpe-gap-field",
		});

		// Current value
		const currentEl = gapEl.createDiv({ cls: "itpe-gap-current" });
		currentEl.createEl("strong", { text: "현재: " });
		currentEl.createEl("span", {
			text: gap.current_value || "(비어있음)",
			cls: "itpe-gap-value",
		});

		// Suggested value
		const suggestedEl = gapEl.createDiv({ cls: "itpe-gap-suggested" });
		suggestedEl.createEl("strong", { text: "제안: " });
		suggestedEl.createEl("span", {
			text: gap.suggested_value,
			cls: "itpe-gap-value",
		});

		// Reasoning
		if (gap.reasoning) {
			const reasoningEl = gapEl.createDiv({ cls: "itpe-gap-reasoning" });
			reasoningEl.createEl("em", {
				text: gap.reasoning,
				cls: "itpe-gap-reasoning-text",
			});
		}

		// Apply suggestion button (shows notice for now)
		const applyBtn = gapEl.createEl("button", {
			text: "제안 적용",
			cls: "itpe-apply-btn",
		});
		applyBtn.addEventListener("click", () => {
			this.handleApplySuggestion(gap);
		});
	}

	/**
	 * Render references tab content
	 */
	private renderReferences(container: HTMLElement): void {
		if (this.result.matched_references.length === 0) {
			container.createEl("p", {
				text: "일치하는 참조 문서가 없습니다.",
				cls: "itpe-no-refs",
			});
			return;
		}

		// Sort by trust score
		const sortedRefs = [...this.result.matched_references].sort(
			(a, b) => b.trust_score - a.trust_score
		);

		for (const ref of sortedRefs) {
			this.renderReferenceItem(container, ref);
		}
	}

	/**
	 * Render single reference item
	 */
	private renderReferenceItem(container: HTMLElement, ref: MatchedReference): void {
		const refEl = container.createDiv({ cls: "itpe-reference" });

		// Header with title and source type
		const header = refEl.createDiv({ cls: "itpe-ref-header" });
		header.createEl("strong", {
			text: ref.title,
			cls: "itpe-ref-title",
		});
		header.createEl("span", {
			text: this.getSourceTypeLabel(ref.source_type),
			cls: "itpe-ref-type",
		});

		// Details (similarity, trust, domain)
		const details = refEl.createDiv({ cls: "itpe-ref-details" });
		details.createEl("span", {
			text: `유사도: ${Math.round(ref.similarity_score * 100)}%`,
		});
		details.createEl("span", {
			text: `신뢰도: ${Math.round(ref.trust_score * 100)}%`,
		});
		details.createEl("span", {
			text: ref.domain,
			cls: "itpe-ref-domain",
		});

		// Relevant snippet
		if (ref.relevant_snippet) {
			const snippetEl = refEl.createDiv({ cls: "itpe-ref-snippet" });
			snippetEl.createEl("strong", { text: "관련 내용: " });
			snippetEl.createEl("span", {
				text: ref.relevant_snippet,
				cls: "itpe-ref-snippet-text",
			});
		}
	}

	/**
	 * Get score color class
	 */
	private getScoreColor(score: number): string {
		if (score >= 85) {
			return "green";
		} else if (score >= 70) {
			return "yellow";
		} else {
			return "red";
		}
	}

	/**
	 * Get Korean label for gap type
	 */
	private getGapTypeLabel(type: GapType): string {
		const labels: Record<GapType, string> = {
			incomplete_definition: "[중요] 정의 불충분",
			missing_examples: "[중간] 예제 부족",
			weak_keywords: "[낮음] 키워드 약함",
			insufficient_depth: "[중간] 내용 깊이 부족",
		};
		return labels[type] || type;
	}

	/**
	 * Get emoji icon for source type
	 */
	private getSourceTypeLabel(type: string): string {
		const labels: Record<string, string> = {
			pdf_book: "📖 도서",
			web_article: "🌐 웹",
			technical_doc: "📄 기술 문서",
		};
		return labels[type] || type;
	}

	/**
	 * Handle apply suggestion click
	 */
	private handleApplySuggestion(gap: ContentGap): void {
		new Notice("제안 적용 기능은 제안 모달에서 사용 가능합니다.");
		this.logger.info(`Apply suggestion requested for field: ${gap.field_name}`);
	}
}
