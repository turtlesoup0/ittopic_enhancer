/**
 * Status Bar Component for ITPE Plugin
 *
 * Shows validation status in Obsidian's status bar with Korean text support.
 */
import { App, Notice } from "obsidian";
import { Logger } from "../utils/logger";
import type { ValidationResult } from "../api/types";
import type ITPEPlugin from "../main";

/**
 * Status Bar Manager
 */
export class StatusBarManager {
	private plugin: ITPEPlugin;
	private logger: Logger;
	private statusBarItem: HTMLElement | null;
	private currentScore: number;
	private proposalCount: number;
	private lastValidation: Date | null;
	private currentTaskId: string | null;
	private totalTopics: number;
	private processedTopics: number;

	constructor(plugin: ITPEPlugin) {
		this.plugin = plugin;
		this.logger = plugin.logger;
		this.statusBarItem = null;
		this.currentScore = 0;
		this.proposalCount = 0;
		this.lastValidation = null;
		this.currentTaskId = null;
		this.totalTopics = 0;
		this.processedTopics = 0;
	}

	/**
	 * Initialize status bar
	 */
	initialize(): void {
		this.statusBarItem = this.plugin.addStatusBarItem();
		this.statusBarItem.addClass("itpe-status-bar");
		this.render();

		// Add click handler
		this.statusBarItem.addEventListener("click", () => {
			this.handleClick();
		});
	}

	/**
	 * Update validation score
	 */
	updateScore(score: number): void {
		this.currentScore = Math.round(score * 100);
		this.updateDisplay();
	}

	/**
	 * Update proposal count
	 */
	updateProposalCount(count: number): void {
		this.proposalCount = count;
		this.updateDisplay();
	}

	/**
	 * Update last validation time
	 */
	updateLastValidation(time: Date): void {
		this.lastValidation = time;
		this.updateDisplay();
	}

	/**
	 * Update all status
	 */
	updateStatus(score: number, proposalCount: number, lastValidation: Date): void {
		this.currentScore = Math.round(score * 100);
		this.proposalCount = proposalCount;
		this.lastValidation = lastValidation;
		this.updateDisplay();
	}

	/**
	 * Set validation status for progress tracking
	 */
	setValidationStatus(taskId: string, totalCount: number): void {
		this.currentTaskId = taskId;
		this.totalTopics = totalCount;
		this.processedTopics = 0;
		this.updateDisplay();
	}

	/**
	 * Update progress during validation
	 */
	updateProgress(current: number, total: number): void {
		this.processedTopics = current;
		this.totalTopics = total;
		this.updateDisplay();
	}

	/**
	 * Set validation complete with results
	 */
	setValidationComplete(result: ValidationResult): void {
		this.currentScore = Math.round(result.overall_score * 100);
		this.proposalCount = result.gaps.length;
		this.lastValidation = new Date();
		this.currentTaskId = null;
		this.updateDisplay();
	}

	/**
	 * Clear validation status
	 */
	clearValidationStatus(): void {
		this.currentTaskId = null;
		this.render();
	}

	/**
	 * Render initial state
	 */
	private render(): void {
		if (!this.statusBarItem) {
			return;
		}
		this.statusBarItem.setText("[ITPE] 준비 완료");
	}

	/**
	 * Update status bar display
	 */
	private updateDisplay(): void {
		if (!this.statusBarItem) {
			return;
		}

		// Show progress if validation is in progress
		if (this.currentTaskId) {
			this.statusBarItem.setText(
				`[ITPE] 검증 중... (${this.processedTopics}/${this.totalTopics})`
			);
			return;
		}

		// Show validation result if available
		if (this.lastValidation || this.currentScore > 0) {
			const timeAgo = this.lastValidation
				? this.formatTimeAgo(this.lastValidation)
				: "방금 전";

			this.statusBarItem.setText(
				`[ITPE] 점수: ${this.currentScore}/100 | 제안: ${this.proposalCount}개 | 마지막 검증: ${timeAgo}`
			);
			return;
		}

		// Default state
		this.render();
	}

	/**
	 * Format time ago in Korean
	 */
	private formatTimeAgo(date: Date): string {
		const now = new Date();
		const diffMs = now.getTime() - date.getTime();
		const diffSecs = Math.floor(diffMs / 1000);
		const diffMins = Math.floor(diffSecs / 60);
		const diffHours = Math.floor(diffMins / 60);
		const diffDays = Math.floor(diffHours / 24);

		if (diffSecs < 60) {
			return "방금 전";
		} else if (diffMins < 60) {
			return `${diffMins}분 전`;
		} else if (diffHours < 24) {
			return `${diffHours}시간 전`;
		} else {
			return `${diffDays}일 전`;
		}
	}

	/**
	 * Handle status bar click
	 */
	private handleClick(): void {
		this.logger.info("Status bar clicked");

		// If validation is in progress, show progress info
		if (this.currentTaskId) {
			new Notice(`검증 진행 중: ${this.processedTopics}/${this.totalTopics}`);
			return;
		}

		// If we have validation results, show quick status
		if (this.lastValidation || this.currentScore > 0) {
			const scoreText = this.getScoreText(this.currentScore);
			new Notice(`점수: ${this.currentScore}/100 (${scoreText})\n제안: ${this.proposalCount}개`);
			return;
		}

		// Default: show ready message
		new Notice("ITPE 검증 플러그인이 준비되었습니다.");
	}

	/**
	 * Get score text description
	 */
	private getScoreText(score: number): string {
		if (score >= 85) {
			return "우수";
		} else if (score >= 70) {
			return "보통";
		} else {
			return "개선 필요";
		}
	}

	/**
	 * Hide status bar
	 */
	hide(): void {
		if (this.statusBarItem) {
			this.statusBarItem.hide();
		}
	}

	/**
	 * Show status bar
	 */
	show(): void {
		if (this.statusBarItem) {
			this.statusBarItem.show();
		}
	}

	/**
	 * Remove status bar
	 */
	remove(): void {
		if (this.statusBarItem) {
			this.statusBarItem.remove();
			this.statusBarItem = null;
		}
	}
}
