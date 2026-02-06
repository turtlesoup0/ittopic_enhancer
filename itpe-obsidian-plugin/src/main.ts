/**
 * ITPE Topic Enhancement Plugin
 *
 * Obsidian plugin for ITPE Topic Enhancement System integration.
 * Validates topics and provides enhancement proposals.
 */
import { Plugin, Notice, TFile } from "obsidian";
import { ITPEApiClient } from "./api/client";
import {
	ITPEPluginSettings,
	DEFAULT_SETTINGS,
	Topic,
	ValidationResult,
	EnhancementProposal,
} from "./api/types";
import { Logger } from "./utils/logger";
import { CacheManager } from "./utils/cache";
import { TopicParser } from "./parsers/topic-parser";
import { DataviewIntegration } from "./parsers/dataview";
import { StatusBarManager } from "./ui/status-bar";
import { ValidationResultModal } from "./ui/result-modal";
import { ProposalModal } from "./ui/proposal-modal";
import { ITPEPluginSettings as PluginSettings } from "./settings";
import { ITPEPluginSettingTab } from "./ui/settings-tab";
import { StateSyncManager } from "./sync/state-sync";
import { registerAllCommands } from "./commands";

/**
 * Main Plugin Class
 */
export default class ITPEPlugin extends Plugin {
	settings: PluginSettings;
	logger: Logger;
	apiClient: ITPEApiClient;
	topicParser: TopicParser;
	dataviewIntegration: DataviewIntegration;
	stateSync: StateSyncManager;
	statusBar: StatusBarManager;
	cache: CacheManager<any>;
	autoSyncIntervalId: number | null;

	/**
	 * Plugin onload
	 */
	async onload(): Promise<void> {
		this.logger = new Logger(false);
		this.logger.info("Loading ITPE Topic Enhancement Plugin...");

		// Load settings
		await this.loadSettings();

		// Update logger based on settings
		this.logger = new Logger(this.settings.debugMode);

		// Initialize API client
		this.apiClient = new ITPEApiClient(
			{
				baseUrl: this.settings.backendUrl,
				apiKey: this.settings.apiKey,
			},
			this.logger
		);

		// Initialize core modules
		this.topicParser = new TopicParser(this.app.vault, this.logger);
		this.dataviewIntegration = new DataviewIntegration(this.app, this.logger, this.topicParser);
		this.stateSync = new StateSyncManager(this.app, this.apiClient, this.logger);
		this.cache = new CacheManager();

		// Initialize UI
		if (this.settings.showStatusBar) {
			this.statusBar = new StatusBarManager(this);
			this.statusBar.initialize();
		}

		// Register ribbon icon
		this.addRibbonIcon("sync", "ITPE Sync", () => {
			this.syncAllTopics();
		});

		// Register commands
		registerAllCommands(this);

		// Register context menu
		this.registerContextMenu();

		// Register settings tab
		this.addSettingTab(new ITPEPluginSettingTab(this.app, this));

		// Start auto sync if enabled
		if (this.settings.autoSync) {
			this.startAutoSync();
		}

		this.logger.info("ITPE Topic Enhancement Plugin loaded successfully!");
	}

	/**
	 * Plugin onunload
	 */
	onunload(): void {
		this.stopAutoSync();

		if (this.statusBar) {
			this.statusBar.remove();
		}

		if (this.stateSync) {
			this.stateSync.destroy();
		}

		this.logger.info("ITPE Topic Enhancement Plugin unloaded");
	}

	/**
	 * Export topics as JSON
	 */
	async exportTopics(): Promise<void> {
		try {
			this.notice("Exporting topics...", "info");

			const topics = await this.dataviewIntegration.queryTopics();

			if (topics.length === 0) {
				this.notice("No topics found", "warning");
				return;
			}

			// Copy to clipboard
			const jsonString = JSON.stringify({ topics }, null, 2);
			await navigator.clipboard.writeText(jsonString);

			// Save to file
			const filePath = `itpe-topics-${Date.now()}.json`;
			await this.app.vault.create(filePath, jsonString);

			this.notice(`Exported ${topics.length} topics to ${filePath}`, "success");
		} catch (error) {
			this.logger.error("Failed to export topics", error);
			this.notice("Export failed", "error");
		}
	}

	/**
	 * Validate current topic
	 */
	async validateCurrentTopic(): Promise<void> {
		const activeFile = this.app.workspace.getActiveFile();
		if (!activeFile) {
			this.notice("No active file", "warning");
			return;
		}

		try {
			this.notice("Validating current topic...", "info");

			const topic = await this.topicParser.parseFile(activeFile);

			if (!topic) {
				this.notice("Could not parse topic from current file", "warning");
				return;
			}

			// Upload and validate
			await this.stateSync.uploadTopics([topic]);
			const taskId = await this.stateSync.createValidation([topic.id]);

			if (taskId) {
				// Poll for result
				await this.stateSync.pollValidationStatus(
					taskId,
					(processed, total) => {
						this.logger.info(`Validation progress: ${processed}/${total}`);
					},
					(result) => {
						// Show result modal
						new ValidationResultModal(this.app, result, this.logger).open();
						// Update status bar
						if (this.statusBar) {
							this.statusBar.updateScore(result.overall_score);
							this.statusBar.updateLastValidation(new Date());
						}
					},
					(error) => {
						this.notice(`Validation failed: ${error.message}`, "error");
					}
				);
			}
		} catch (error) {
			this.logger.error("Failed to validate current topic", error);
			this.notice("Validation failed", "error");
		}
	}

	/**
	 * Validate all topics
	 */
	async validateAllTopics(): Promise<void> {
		try {
			this.notice("Validating all topics...", "info");

			const topics = await this.dataviewIntegration.queryTopics();

			if (topics.length === 0) {
				this.notice("No topics found", "warning");
				return;
			}

			// Upload topics
			await this.stateSync.uploadTopics(topics);

			// Create validation task
			const topicIds = topics.map((t) => t.id);
			const taskId = await this.stateSync.createValidation(topicIds);

			if (taskId) {
				this.notice(`Started validation for ${topics.length} topics`, "success");
			}
		} catch (error) {
			this.logger.error("Failed to validate all topics", error);
			this.notice("Validation failed", "error");
		}
	}

	/**
	 * Show validation result
	 */
	async showValidationResult(): Promise<void> {
		const activeFile = this.app.workspace.getActiveFile();
		if (!activeFile) {
			this.notice("No active file", "warning");
			return;
		}

		try {
			const topic = await this.topicParser.parseFile(activeFile);

			if (!topic) {
				this.notice("Could not parse topic from current file", "warning");
				return;
			}

			// Get cached result or show message
			const cacheKey = `validation-${topic.id}`;
			const cached = this.cache.get(cacheKey);

			if (cached) {
				new ValidationResultModal(this.app, cached, this.logger).open();
			} else {
				this.notice("No validation result found. Please validate first.", "info");
			}
		} catch (error) {
			this.logger.error("Failed to show validation result", error);
			this.notice("Failed to show result", "error");
		}
	}

	/**
	 * Show proposals
	 */
	async showProposals(): Promise<void> {
		const activeFile = this.app.workspace.getActiveFile();
		if (!activeFile) {
			this.notice("No active file", "warning");
			return;
		}

		try {
			const topic = await this.topicParser.parseFile(activeFile);

			if (!topic) {
				this.notice("Could not parse topic from current file", "warning");
				return;
			}

			const proposals = await this.stateSync.getProposals(topic.id);

			if (proposals.length === 0) {
				this.notice("No proposals found for this topic", "info");
				return;
			}

			// Show proposal modal
			new ProposalModal(this.app, proposals, this.logger, {
				onApply: async (proposal) => {
					const success = await this.stateSync.applyProposal(proposal.id, topic.id);
					if (success) {
						this.notice("Proposal applied successfully", "success");
					} else {
						this.notice("Failed to apply proposal", "error");
					}
				},
			}).open();
		} catch (error) {
			this.logger.error("Failed to show proposals", error);
			this.notice("Failed to show proposals", "error");
		}
	}

	/**
	 * Open dashboard
	 */
	async openDashboard(): Promise<void> {
		const dashboardUrl = `${this.settings.backendUrl}/dashboard`;
		window.open(dashboardUrl, "_blank");
		this.notice("Opening dashboard...", "info");
	}

	/**
	 * Sync all topics
	 */
	async syncAllTopics(): Promise<void> {
		try {
			this.logger.info("Starting sync for all topics...");

			const topics = await this.dataviewIntegration.queryTopics();

			if (topics.length === 0) {
				this.logger.info("No topics found to sync");
				this.notice("No topics found", "warning");
				return;
			}

			this.logger.info(`Found ${topics.length} topics to sync`);

			// Upload topics
			const uploadResult = await this.stateSync.uploadTopics(topics);
			this.logger.info(`Uploaded ${uploadResult.uploaded} topics, ${uploadResult.failed} failed`);

			// Create validation task
			const topicIds = topics.map((t) => t.id);
			const taskId = await this.stateSync.createValidation(topicIds);

			if (taskId) {
				this.notice(`Sync started for ${topics.length} topics`, "success");
				this.logger.info(`Validation task created: ${taskId}`);
			} else {
				this.notice("Failed to create validation task", "error");
			}
		} catch (error) {
			this.logger.error("Failed to sync all topics", error);
			this.notice("Sync failed", "error");
		}
	}

	/**
	 * Register context menu
	 */
	private registerContextMenu(): void {
		this.registerEvent(
			this.app.workspace.on("file-menu", (menu, file: TFile) => {
				menu.addItem((item) => {
					item
						.setTitle("ITPE: Sync Topic")
						.setIcon("sync")
						.onClick(() => {
							this.stateSync.syncCurrentFile();
						});
				});
			})
		);
	}

	/**
	 * Start auto sync
	 */
	private startAutoSync(): void {
		this.stopAutoSync();

		const intervalMs = this.settings.syncInterval * 60 * 1000;

		this.autoSyncIntervalId = window.setInterval(async () => {
			if (this.settings.autoSync) {
				await this.syncAllTopics();
			}
		}, intervalMs);

		this.logger.info(`Auto sync started: ${this.settings.syncInterval} minutes`);
	}

	/**
	 * Stop auto sync
	 */
	stopAutoSync(): void {
		if (this.autoSyncIntervalId !== null) {
			clearInterval(this.autoSyncIntervalId);
			this.autoSyncIntervalId = null;
			this.logger.info("Auto sync stopped");
		}
	}

	/**
	 * Restart auto sync
	 */
	restartAutoSync(): void {
		if (this.settings.autoSync) {
			this.startAutoSync();
		}
	}

	/**
	 * Load settings
	 */
	async loadSettings(): Promise<void> {
		const saved = await this.loadData();
		this.settings = new PluginSettings(saved || {});
	}

	/**
	 * Save settings
	 */
	async saveSettings(): Promise<void> {
		await this.saveData(this.settings);

		// Update logger
		this.logger.debugMode = this.settings.debugMode;

		// Update API client
		this.apiClient = new ITPEApiClient(
			{
				baseUrl: this.settings.backendUrl,
				apiKey: this.settings.apiKey,
			},
			this.logger
		);

		// Update state sync
		this.stateSync = new StateSyncManager(this.app, this.apiClient, this.logger);
	}

	/**
	 * Show notice helper
	 */
	private notice(message: string, type: "info" | "success" | "warning" | "error" = "info"): void {
		new Notice(`[ITPE] ${message}`, 5000);
		this.logger.info(message);
	}
}
