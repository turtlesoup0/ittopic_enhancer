/**
 * State Synchronization Manager for ITPE Plugin
 *
 * Manages background polling for validation tasks, cache integration,
 * and automatic refresh of validation results.
 */
import { App, Notice, TFile } from "obsidian";
import { ITPEApiClient } from "../api/client";
import { Topic, ValidationResult, EnhancementProposal, UpdateTopicRequest, TaskStatusResponse, TopicContent } from "../api/types";
import { Logger } from "../utils/logger";
import { CacheManager } from "../utils/cache";
import { TopicParser } from "../parsers/topic-parser";

/**
 * Validation task metadata
 */
interface ValidationTask {
	id: string;
	topicId: string | null;
	totalCount?: number;
	startTime: number;
}

/**
 * State Sync Manager
 *
 * Manages background synchronization of validation tasks with automatic polling,
 * cache integration, and status bar updates.
 */
export class StateSyncManager {
	private app: App;
	private apiClient: ITPEApiClient;
	private logger: Logger;
	private parser: TopicParser;
	private cache: CacheManager<any>;
	private activeTasks: Map<string, ValidationTask>;
	private pollingIntervals: Map<string, number>;
	private pollInterval: number | null;
	private isRunning: boolean;
	private syncIntervalMs: number;

	constructor(app: App, apiClient: ITPEApiClient, logger: Logger, syncIntervalMinutes: number = 5) {
		this.app = app;
		this.apiClient = apiClient;
		this.logger = logger;
		this.parser = new TopicParser(app.vault, logger);
		this.cache = new CacheManager(5 * 60 * 1000); // 5 minutes
		this.activeTasks = new Map();
		this.pollingIntervals = new Map();
		this.pollInterval = null;
		this.isRunning = false;
		this.syncIntervalMs = syncIntervalMinutes * 60 * 1000;
	}

	/**
	 * Start background sync
	 */
	start(): void {
		if (this.isRunning) {
			this.logger.warn("State sync is already running");
			return;
		}

		this.isRunning = true;
		this.pollInterval = window.setInterval(() => {
			this.pollAllTasks();
		}, this.syncIntervalMs);

		this.logger.info(`State sync started (interval: ${this.syncIntervalMs / 1000}s)`);
	}

	/**
	 * Stop background sync
	 */
	async stop(): Promise<void> {
		if (!this.isRunning) {
			return;
		}

		this.isRunning = false;

		// Clear background polling interval
		if (this.pollInterval) {
			clearInterval(this.pollInterval);
			this.pollInterval = null;
		}

		// Clear all task polling intervals
		for (const intervalId of this.pollingIntervals.values()) {
			clearInterval(intervalId);
		}
		this.pollingIntervals.clear();

		this.logger.info("State sync stopped");
	}

	/**
	 * Register a validation task for polling
	 */
	registerTask(taskId: string, topicId: string | null, totalCount?: number): void {
		this.activeTasks.set(taskId, {
			id: taskId,
			topicId,
			totalCount,
			startTime: Date.now(),
		});

		this.logger.debug(`Registered task ${taskId} for polling`);

		// Start polling immediately
		this.pollTask(taskId);
	}

	/**
	 * Upload topics to backend
	 */
	async uploadTopics(topics: Topic[]): Promise<{ uploaded: number; failed: number }> {
		this.logger.info(`Uploading ${topics.length} topics...`);

		try {
			const response = await this.apiClient.uploadTopics({ topics });
			this.logger.info(`Uploaded: ${response.uploaded}, Failed: ${response.failed ?? 0}`);
			return { uploaded: response.uploaded, failed: topics.length - response.uploaded };
		} catch (error) {
			this.logger.error("Failed to upload topics", error);
			return { uploaded: 0, failed: topics.length };
		}
	}

	/**
	 * Create validation task
	 */
	async createValidation(topicIds: string[]): Promise<string | null> {
		this.logger.info(`Creating validation for ${topicIds.length} topics...`);

		try {
			const response = await this.apiClient.createValidation({
				topic_ids: topicIds,
			});

			this.logger.info(`Validation task created: ${response.task_id}`);
			return response.task_id;
		} catch (error) {
			this.logger.error("Failed to create validation", error);
			return null;
		}
	}

	/**
	 * Get validation status (one-time check)
	 */
	async getValidationStatus(taskId: string): Promise<TaskStatusResponse | null> {
		try {
			return await this.apiClient.getTaskStatus(taskId);
		} catch (error) {
			this.logger.error(`Failed to get status for task ${taskId}`, error);
			return null;
		}
	}

	/**
	 * Poll all active tasks
	 */
	private async pollAllTasks(): Promise<void> {
		if (this.activeTasks.size === 0) {
			return;
		}

		this.logger.debug(`Polling ${this.activeTasks.size} active tasks`);

		const taskIds = Array.from(this.activeTasks.keys());
		for (const taskId of taskIds) {
			await this.pollTask(taskId);
		}
	}

	/**
	 * Poll a specific task
	 */
	private async pollTask(taskId: string): Promise<void> {
		const task = this.activeTasks.get(taskId);
		if (!task) {
			return;
		}

		try {
			const status = await this.apiClient.getTaskStatus(taskId);

			if (status.status === "completed") {
				await this.handleTaskComplete(task);
			} else if (status.status === "failed") {
				this.handleTaskFailed(task);
			}
			// Still processing, continue polling
		} catch (error) {
			this.logger.error(`Polling failed for task ${taskId}:`, error);
		}
	}

	/**
	 * Handle task completion
	 */
	private async handleTaskComplete(task: ValidationTask): Promise<void> {
		this.logger.info(`Task ${task.id} completed`);

		try {
			// Get validation result
			const result = await this.apiClient.getValidationResult(task.id);

			// Cache the result
			this.cache.set(`validation:${task.topicId || task.id}`, result);

			// Show notification
			new Notice("검증이 완료되었습니다!");

			// Remove from active tasks
			this.activeTasks.delete(task.id);
		} catch (error) {
			this.logger.error("Failed to handle task completion:", error);
		}
	}

	/**
	 * Handle task failure
	 */
	private handleTaskFailed(task: ValidationTask): void {
		this.logger.warn(`Task ${task.id} failed`);
		new Notice("검증이 실패했습니다.");

		// Remove from active tasks
		this.activeTasks.delete(task.id);
	}

	/**
	 * Poll validation status (with callbacks for UI updates)
	 *
	 * @deprecated Use registerTask() for automatic polling instead
	 */
	async pollValidationStatus(
		taskId: string,
		onProgress?: (processed: number, total: number) => void,
		onComplete?: (result: ValidationResult) => void,
		onError?: (error: Error) => void
	): Promise<void> {
		// Register the task
		this.registerTask(taskId, null);

		const poll = async () => {
			try {
				const status = await this.apiClient.getTaskStatus(taskId);

				if (status.status === "completed") {
					// Get result and trigger callback
					const result = await this.apiClient.getValidationResult(taskId);

					// Cache result
					if (result.topic_id) {
						this.cache.set(`validation:${result.topic_id}`, result);
					}

					// Remove from polling
					this.activeTasks.delete(taskId);

					// Clear interval
					const intervalId = this.pollingIntervals.get(taskId);
					if (intervalId) {
						clearInterval(intervalId);
						this.pollingIntervals.delete(taskId);
					}

					if (onComplete) {
						onComplete(result);
					}
				} else if (status.status === "failed") {
					this.activeTasks.delete(taskId);

					// Clear interval
					const intervalId = this.pollingIntervals.get(taskId);
					if (intervalId) {
						clearInterval(intervalId);
						this.pollingIntervals.delete(taskId);
					}

					if (onError) {
						onError(new Error("Validation failed"));
					}
				}
			} catch (error) {
				this.activeTasks.delete(taskId);

				// Clear interval
				const intervalId = this.pollingIntervals.get(taskId);
				if (intervalId) {
					clearInterval(intervalId);
					this.pollingIntervals.delete(taskId);
				}

				if (onError) {
					onError(error as Error);
				}
			}
		};

		// Initial check
		await poll();

		// Start polling interval for this task
		const intervalId = window.setInterval(poll, 2000);
		this.pollingIntervals.set(taskId, intervalId);
	}

	/**
	 * Get proposals for topic
	 */
	async getProposals(topicId: string): Promise<EnhancementProposal[]> {
		// Check cache first
		const cacheKey = `proposals-${topicId}`;
		const cached = this.cache.get(cacheKey) as EnhancementProposal[] | null;
		if (cached) {
			return cached;
		}

		try {
			const response = await this.apiClient.getProposals({ topic_id: topicId });
			this.cache.set(cacheKey, response.proposals);
			return response.proposals;
		} catch (error) {
			this.logger.error(`Failed to get proposals for ${topicId}`, error);
			return [];
		}
	}

	/**
	 * Get active task count
	 */
	getActiveTaskCount(): number {
		return this.activeTasks.size;
	}

	/**
	 * Check if sync is running
	 */
	isActive(): boolean {
		return this.isRunning;
	}

	/**
	 * Apply proposal to topic
	 */
	async applyProposal(proposalId: string, topicId: string): Promise<boolean> {
		this.logger.info(`Applying proposal ${proposalId} to topic ${topicId}`);

		try {
			// Get proposal details
			const proposals = await this.getProposals(topicId);
			const proposal = proposals.find((p) => p.id === proposalId);

			if (!proposal) {
				this.logger.error(`Proposal ${proposalId} not found`);
				return false;
			}

			// Map target_field to TopicContent field
			const contentUpdate: Partial<TopicContent> = {};
			const fieldMap: Record<string, keyof TopicContent> = {
				"리드문": "리드문",
				"정의": "정의",
				"키워드": "키워드",
				"해시태그": "해시태그",
				"암기": "암기",
			};

			// Use title as fallback if target_field is not set
			const targetField = proposal.target_field || proposal.title;
			const contentField = fieldMap[targetField];
			if (contentField) {
				// Handle array fields differently
				if (contentField === "키워드") {
					(contentUpdate as Partial<TopicContent>)[contentField] = proposal.suggested_content.split(",").map(k => k.trim());
				} else {
					(contentUpdate as Partial<TopicContent>)[contentField] = proposal.suggested_content;
				}
			}

			// Apply to backend
			const request: UpdateTopicRequest = {
				content: contentUpdate,
			};

			await this.apiClient.updateTopic(topicId, request);

			// Apply to local file
			await this.applyProposalToFile(proposal, topicId);

			// Clear cache
			this.cache.clear(`proposals-${topicId}`);

			return true;
		} catch (error) {
			this.logger.error(`Failed to apply proposal ${proposalId}`, error);
			return false;
		}
	}

	/**
	 * Apply proposal to local file
	 */
	private async applyProposalToFile(proposal: EnhancementProposal, topicId: string): Promise<void> {
		// Find file by topic ID
		const file = this.findFileByTopicId(topicId);
		if (!file) {
			this.logger.error(`File not found for topic ${topicId}`);
			return;
		}

		// Read file content
		const content = await this.app.vault.read(file);

		// Find and replace the target field
		const fieldPattern = new RegExp(`##\\s*${proposal.target_field}\\s*\\n+([\\s\\S]+?)(?=\\n##|\\n\\n\\n|$)`);
		const newContent = content.replace(
			fieldPattern,
			`## ${proposal.target_field}\n${proposal.suggested_content}\n`
		);

		// Write updated content
		await this.app.vault.modify(file, newContent);

		this.logger.info(`Applied proposal to file ${file.path}`);
	}

	/**
	 * Find file by topic ID
	 * Note: This uses the cache to find the topic, then gets the file from the vault
	 */
	private findFileByTopicId(topicId: string): TFile | null {
		// Try to get the cached topic to find its file path
		const cachedTopic = this.cache.get(`topic:${topicId}`) as Topic | null;
		if (cachedTopic?.metadata.file_path) {
			const file = this.app.vault.getAbstractFileByPath(cachedTopic.metadata.file_path);
			if (file instanceof TFile) {
				return file;
			}
		}

		// Fallback: return null if not found in cache
		this.logger.warn(`Could not find file for topic ID: ${topicId}`);
		return null;
	}

	/**
	 * Sync current file
	 */
	async syncCurrentFile(): Promise<void> {
		const activeFile = this.app.workspace.getActiveFile();
		if (!activeFile) {
			new Notice("No active file");
			return;
		}

		try {
			const topic = await this.parser.parseFile(activeFile);

			if (!topic) {
				new Notice("Could not parse topic from current file");
				return;
			}

			// Upload and validate
			await this.uploadTopics([topic]);
			const taskId = await this.createValidation([topic.id]);

			if (taskId) {
				new Notice("Validation started");
				// Poll for result
				await this.pollValidationStatus(
					taskId,
					(processed, total) => {
						this.logger.info(`Validation progress: ${processed}/${total}`);
					},
					(result) => {
						new Notice(`Validation complete: Score ${result.overall_score}/100`);
					},
					(error) => {
						new Notice(`Validation failed: ${error.message}`);
					}
				);
			}
		} catch (error) {
			this.logger.error("Failed to sync current file", error);
			new Notice("Sync failed");
		}
	}

	/**
	 * Clean up resources
	 */
	destroy(): void {
		// Stop background sync
		this.stop();

		// Clear all tasks
		this.activeTasks.clear();

		// Clear cache
		this.cache.clearAll();
	}
}
