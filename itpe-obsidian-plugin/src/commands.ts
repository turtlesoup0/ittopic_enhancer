/**
 * Commands Module for ITPE Obsidian Plugin
 *
 * P3-INT-001: Command registration and handlers for ITPE plugin
 *
 * Features:
 * - Export all topics to backend API
 * - Validate currently open file
 * - Bulk validate all topics
 * - Show validation result modal
 * - Show enhancement proposals modal
 * - Open web dashboard in browser
 */

import { Notice, TFile } from "obsidian";
import type ITPEPlugin from "./main";
import { TopicParser } from "./parsers/topic-parser";
import { ValidationResultModal } from "./ui/result-modal";
import { ProposalModal } from "./ui/proposal-modal";
import type { ValidationResult, EnhancementProposal } from "./api/types";
import { TaskStatus, type TaskStatusResponse } from "./api/types";

// ============================================================================
// Command Registration
// ============================================================================

/**
 * Register all plugin commands
 *
 * @param plugin - ITPE plugin instance
 */
export function registerAllCommands(plugin: ITPEPlugin): void {
	// 1. Export all topics to backend API
	plugin.addCommand({
		id: "itpe-export",
		name: "ITPE: 모든 토픽 내보내기",
		callback: () => handleExportTopics(plugin),
	});

	// 2. Validate currently open file
	plugin.addCommand({
		id: "itpe-validate-current",
		name: "ITPE: 현재 파일 검증",
		checkCallback: (checking: boolean) => {
			const activeFile = plugin.app.workspace.getActiveFile();
			if (activeFile) {
				if (!checking) {
					handleValidateCurrent(plugin);
				}
				return true;
			}
			return false;
		},
	});

	// 3. Bulk validate all topics
	plugin.addCommand({
		id: "itpe-validate-all",
		name: "ITPE: 전체 토픽 검증",
		callback: () => handleValidateAll(plugin),
	});

	// 4. Show validation result modal
	plugin.addCommand({
		id: "itpe-show-result",
		name: "ITPE: 검증 결과 보기",
		checkCallback: (checking: boolean) => {
			const activeFile = plugin.app.workspace.getActiveFile();
			if (activeFile) {
				if (!checking) {
					handleShowResult(plugin);
				}
				return true;
			}
			return false;
		},
	});

	// 5. Show enhancement proposals modal
	plugin.addCommand({
		id: "itpe-show-proposals",
		name: "ITPE: 개선 제안 보기",
		checkCallback: (checking: boolean) => {
			const activeFile = plugin.app.workspace.getActiveFile();
			if (activeFile) {
				if (!checking) {
					handleShowProposals(plugin);
				}
				return true;
			}
			return false;
		},
	});

	// 6. Open web dashboard in browser
	plugin.addCommand({
		id: "itpe-open-dashboard",
		name: "ITPE: 대시보드 열기",
		callback: () => handleOpenDashboard(plugin),
	});
}

// ============================================================================
// Command Handlers
// ============================================================================

/**
 * Handle export topics command
 *
 * Exports all topics from the vault to the backend API.
 *
 * @param plugin - ITPE plugin instance
 */
async function handleExportTopics(plugin: ITPEPlugin): Promise<void> {
	try {
		plugin.logger.info("Exporting all topics to backend API...");
		new Notice("ITPE: 모든 토픽 내보내기 시작...");

		// Parse all topics using the topic parser
		const parser = new TopicParser(plugin.app.vault, plugin.logger);
		const parsedTopics = await parser.parseAllTopics();

		if (parsedTopics.length === 0) {
			new Notice("ITPE: 내보낼 토픽이 없습니다.");
			plugin.logger.warn("No topics found to export");
			return;
		}

		// Convert to API format
		const topics = parsedTopics.map((t) => parser.toApiTopic(t));

		// Upload to backend API
		const response = await plugin.apiClient.uploadTopics({ topics });

		new Notice(`ITPE: ${response.uploaded}개 토픽이 성공적으로 내보내졌습니다.`);
		plugin.logger.info(`Exported ${response.uploaded} topics successfully`);
	} catch (error) {
		plugin.logger.error("Failed to export topics", error);
		new Notice(`ITPE: 토픽 내보내기 실패 - ${error instanceof Error ? error.message : "알 수 없는 오류"}`);
	}
}

/**
 * Handle validate current file command
 *
 * Validates the currently open topic file.
 *
 * @param plugin - ITPE plugin instance
 */
async function handleValidateCurrent(plugin: ITPEPlugin): Promise<void> {
	try {
		const activeFile = plugin.app.workspace.getActiveFile();
		if (!activeFile) {
			new Notice("ITPE: 활성 파일이 없습니다.");
			return;
		}

		plugin.logger.info(`Validating current file: ${activeFile.path}`);
		new Notice("ITPE: 현재 파일 검증 중...");

		// Parse the current file
		const parser = new TopicParser(plugin.app.vault, plugin.logger);
		const content = await plugin.app.vault.read(activeFile);
		const parsedTopic = await parser.parseFile(activeFile);

		if (!parsedTopic) {
			new Notice("ITPE: 현재 파일에서 토픽을 파싱할 수 없습니다.");
			plugin.logger.warn(`Could not parse topic from file: ${activeFile.path}`);
			return;
		}

		// Convert to API format
		const topic = parser.toApiTopic(parsedTopic);

		// Upload to backend
		await plugin.apiClient.uploadTopics({ topics: [topic] });

		// Create validation task
		const validationResponse = await plugin.apiClient.createValidation({
			topic_ids: [topic.id],
		});

		plugin.logger.info(`Validation task created: ${validationResponse.task_id}`);

		// Poll for result
		new Notice("ITPE: 검증 완료 대기 중...");
		const result = await pollForResult(
			plugin,
			validationResponse.task_id,
			(status) => {
				plugin.logger.debug(`Validation status: ${status.status}`);
			}
		);

		if (result) {
			// Cache the result
			plugin.cache.set(`validation-${topic.id}`, result);

			// Show result modal
			new ValidationResultModal(plugin.app, result, plugin.logger).open();
			new Notice("ITPE: 검증 완료!");
			plugin.logger.info("Validation completed successfully");
		} else {
			new Notice("ITPE: 검증 시간 초과 또는 실패");
			plugin.logger.warn("Validation polling timed out or failed");
		}
	} catch (error) {
		plugin.logger.error("Failed to validate current file", error);
		new Notice(`ITPE: 검증 실패 - ${error instanceof Error ? error.message : "알 수 없는 오류"}`);
	}
}

/**
 * Handle validate all topics command
 *
 * Validates all topics in the vault.
 *
 * @param plugin - ITPE plugin instance
 */
async function handleValidateAll(plugin: ITPEPlugin): Promise<void> {
	try {
		plugin.logger.info("Validating all topics...");
		new Notice("ITPE: 전체 토픽 검증 시작...");

		// Parse all topics
		const parser = new TopicParser(plugin.app.vault, plugin.logger);
		const parsedTopics = await parser.parseAllTopics();

		if (parsedTopics.length === 0) {
			new Notice("ITPE: 검증할 토픽이 없습니다.");
			plugin.logger.warn("No topics found to validate");
			return;
		}

		// Convert to API format
		const topics = parsedTopics.map((t) => parser.toApiTopic(t));

		// Upload to backend
		await plugin.apiClient.uploadTopics({ topics });

		// Create validation task
		const topicIds = topics.map((t) => t.id);
		const validationResponse = await plugin.apiClient.createValidation({
			topic_ids: topicIds,
		});

		plugin.logger.info(`Validation task created: ${validationResponse.task_id}`);
		new Notice(`ITPE: ${topics.length}개 토픽 검증 시작 (Task ID: ${validationResponse.task_id})`);

		// Poll for result (optional - can be disabled for bulk validation)
		new Notice("ITPE: 백그라운드에서 검증이 진행됩니다. 나중에 결과를 확인하세요.");
	} catch (error) {
		plugin.logger.error("Failed to validate all topics", error);
		new Notice(`ITPE: 전체 검증 실패 - ${error instanceof Error ? error.message : "알 수 없는 오류"}`);
	}
}

/**
 * Handle show validation result command
 *
 * Shows the validation result for the current file.
 *
 * @param plugin - ITPE plugin instance
 */
async function handleShowResult(plugin: ITPEPlugin): Promise<void> {
	try {
		const activeFile = plugin.app.workspace.getActiveFile();
		if (!activeFile) {
			new Notice("ITPE: 활성 파일이 없습니다.");
			return;
		}

		plugin.logger.info(`Showing validation result for: ${activeFile.path}`);

		// Parse the current file to get topic ID
		const parser = new TopicParser(plugin.app.vault, plugin.logger);
		const content = await plugin.app.vault.read(activeFile);
		const parsedTopic = await parser.parseFile(activeFile);

		if (!parsedTopic) {
			new Notice("ITPE: 현재 파일에서 토픽을 파싱할 수 없습니다.");
			return;
		}

		const topic = parser.toApiTopic(parsedTopic);

		// Check cache first
		const cacheKey = `validation-${topic.id}`;
		const cachedResult = plugin.cache.get(cacheKey) as ValidationResult | null;

		if (cachedResult) {
			new ValidationResultModal(plugin.app, cachedResult, plugin.logger).open();
			plugin.logger.info("Showing cached validation result");
			return;
		}

		// If not in cache, try to fetch from API
		// Note: This would require a task ID, which we don't have here
		// For now, just show a message
		new Notice("ITPE: 캐시된 검증 결과가 없습니다. 먼저 검증을 실행하세요.");
		plugin.logger.warn(`No cached validation result for topic: ${topic.id}`);
	} catch (error) {
		plugin.logger.error("Failed to show validation result", error);
		new Notice(`ITPE: 결과 표시 실패 - ${error instanceof Error ? error.message : "알 수 없는 오류"}`);
	}
}

/**
 * Handle show proposals command
 *
 * Shows enhancement proposals for the current file.
 *
 * @param plugin - ITPE plugin instance
 */
async function handleShowProposals(plugin: ITPEPlugin): Promise<void> {
	try {
		const activeFile = plugin.app.workspace.getActiveFile();
		if (!activeFile) {
			new Notice("ITPE: 활성 파일이 없습니다.");
			return;
		}

		plugin.logger.info(`Showing proposals for: ${activeFile.path}`);
		new Notice("ITPE: 개선 제안 불러오는 중...");

		// Parse the current file to get topic ID
		const parser = new TopicParser(plugin.app.vault, plugin.logger);
		const content = await plugin.app.vault.read(activeFile);
		const parsedTopic = await parser.parseFile(activeFile);

		if (!parsedTopic) {
			new Notice("ITPE: 현재 파일에서 토픽을 파싱할 수 없습니다.");
			return;
		}

		const topic = parser.toApiTopic(parsedTopic);

		// Fetch proposals from API
		const response = await plugin.apiClient.getProposals({
			topic_id: topic.id,
		});

		if (response.proposals.length === 0) {
			new Notice("ITPE: 이 토픽에 대한 개선 제안이 없습니다.");
			plugin.logger.info(`No proposals found for topic: ${topic.id}`);
			return;
		}

		// Show proposal modal
		new ProposalModal(
			plugin.app,
			response.proposals,
			plugin.logger,
			{
				onApply: async (proposal: EnhancementProposal) => {
					try {
						// Apply the proposal - use title as the target field
						await plugin.apiClient.updateTopic(topic.id, {
							content: {
								[proposal.title]: proposal.suggested_content,
							},
						});

						// Update the file
						const updatedContent = content.replace(
							proposal.current_content,
							proposal.suggested_content
						);
						await plugin.app.vault.modify(activeFile, updatedContent);

						new Notice("ITPE: 제안이 성공적으로 적용되었습니다.");
						plugin.logger.info(`Applied proposal: ${proposal.id}`);
					} catch (error) {
						plugin.logger.error("Failed to apply proposal", error);
						new Notice("ITPE: 제안 적용 실패");
					}
				},
			}
		).open();

		plugin.logger.info(`Showing ${response.proposals.length} proposals`);
	} catch (error) {
		plugin.logger.error("Failed to show proposals", error);
		new Notice(`ITPE: 제안 표시 실패 - ${error instanceof Error ? error.message : "알 수 없는 오류"}`);
	}
}

/**
 * Handle open dashboard command
 *
 * Opens the web dashboard in the default browser.
 *
 * @param plugin - ITPE plugin instance
 */
function handleOpenDashboard(plugin: ITPEPlugin): void {
	try {
		const dashboardUrl = `${plugin.settings.backendUrl}/dashboard`;
		plugin.logger.info(`Opening dashboard: ${dashboardUrl}`);
		window.open(dashboardUrl, "_blank");
		new Notice("ITPE: 대시보드 열기");
	} catch (error) {
		plugin.logger.error("Failed to open dashboard", error);
		new Notice("ITPE: 대시보드 열기 실패");
	}
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Poll for validation result
 *
 * Polls the backend API for validation results at 2-second intervals
 * with a maximum of 60 attempts (2 minutes total).
 *
 * @param plugin - ITPE plugin instance
 * @param taskId - Validation task ID
 * @param onStatusUpdate - Callback for status updates
 * @returns Validation result or null if timeout/failed
 */
async function pollForResult(
	plugin: ITPEPlugin,
	taskId: string,
	onStatusUpdate?: (status: TaskStatusResponse) => void
): Promise<ValidationResult | null> {
	const MAX_ATTEMPTS = 60;
	const POLL_INTERVAL_MS = 2000;

	for (let attempt = 0; attempt < MAX_ATTEMPTS; attempt++) {
		try {
			// Get task status
			const status = await plugin.apiClient.getTaskStatus(taskId);

			if (onStatusUpdate) {
				onStatusUpdate(status);
			}

			// Check if completed
			if (status.status === TaskStatus.COMPLETED) {
				plugin.logger.info(`Validation completed after ${attempt + 1} attempts`);

				// Get the result
				const result = await plugin.apiClient.getValidationResult(taskId);
				return result;
			}

			// Check if failed
			if (status.status === TaskStatus.FAILED) {
				plugin.logger.error(`Validation failed: ${taskId}`);
				return null;
			}

			// Wait before next poll
			await sleep(POLL_INTERVAL_MS);
		} catch (error) {
			plugin.logger.error(`Error polling for result (attempt ${attempt + 1})`, error);
			await sleep(POLL_INTERVAL_MS);
		}
	}

	plugin.logger.warn(`Validation polling timed out after ${MAX_ATTEMPTS} attempts`);
	return null;
}

/**
 * Sleep for specified milliseconds
 *
 * @param ms - Milliseconds to sleep
 * @returns Promise that resolves after the specified time
 */
function sleep(ms: number): Promise<void> {
	return new Promise((resolve) => setTimeout(resolve, ms));
}

// ============================================================================
// Types
// ============================================================================

// Note: TaskStatusResponse is now imported from api/types.ts
