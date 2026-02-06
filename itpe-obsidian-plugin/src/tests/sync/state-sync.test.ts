/**
 * State Sync Manager Tests
 */
import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { StateSyncManager } from "../../sync/state-sync";
import { ITPEApiClient } from "../../api/client";
import { Logger } from "../../utils/logger";
import { TopicParser } from "../../parsers/topic-parser";
import { ValidationResult } from "../../api/types";
import { createMockTopic, createMockValidationResult, createMockTaskStatus, createMockProposal, mockApp, mockLogger, mockApiClient } from "../setup";

describe("StateSyncManager", () => {
	let stateSync: StateSyncManager;
	let apiClient: ITPEApiClient;
	let logger: Logger;
	let parser: TopicParser;

	beforeEach(() => {
		vi.useFakeTimers();

		logger = new Logger(true);
		apiClient = new ITPEApiClient({ baseUrl: "http://localhost:8000", apiKey: "test" }, logger);
		parser = new TopicParser(mockApp.vault, logger);

		// Mock the API client methods
		apiClient["request"] = vi.fn().mockResolvedValue({});

		stateSync = new StateSyncManager(mockApp, apiClient as any, logger, 1);
	});

	afterEach(() => {
		vi.restoreAllMocks();
		stateSync.destroy();
	});

	describe("initialization", () => {
		it("should initialize with default values", () => {
			expect(stateSync.isActive()).toBe(false);
			expect(stateSync.getActiveTaskCount()).toBe(0);
		});

		it("should initialize with custom sync interval", () => {
			const customSync = new StateSyncManager(mockApp, apiClient as any, logger, 10);
			expect(customSync).toBeDefined();
			customSync.destroy();
		});
	});

	describe("start and stop", () => {
		it("should start background sync", () => {
			stateSync.start();
			expect(stateSync.isActive()).toBe(true);
		});

		it("should not start if already running", () => {
			stateSync.start();
			const warnSpy = vi.spyOn(logger, "warn");
			stateSync.start();
			expect(warnSpy).toHaveBeenCalledWith("State sync is already running");
		});

		it("should stop background sync", async () => {
			stateSync.start();
			await stateSync.stop();
			expect(stateSync.isActive()).toBe(false);
		});

		it("should handle stop when not running", async () => {
			await expect(stateSync.stop()).resolves.not.toThrow();
		});
	});

	describe("task registration", () => {
		it("should register a task for polling", () => {
			stateSync.registerTask("task-1", "topic-1", 10);
			expect(stateSync.getActiveTaskCount()).toBe(1);
		});

		it("should register multiple tasks", () => {
			stateSync.registerTask("task-1", "topic-1", 10);
			stateSync.registerTask("task-2", "topic-2", 5);
			expect(stateSync.getActiveTaskCount()).toBe(2);
		});

		it("should allow topicId to be null", () => {
			stateSync.registerTask("task-1", null, 10);
			expect(stateSync.getActiveTaskCount()).toBe(1);
		});
	});

	describe("upload topics", () => {
		it("should upload topics successfully", async () => {
			const mockTopics = [createMockTopic()];
			const mockResponse = { uploaded: 1, topic_ids: ["topic-1"] };

			apiClient["request"] = vi.fn().mockResolvedValue(mockResponse);

			const result = await stateSync.uploadTopics(mockTopics);
			expect(result.uploaded).toBe(1);
			expect(result.failed).toBe(0);
		});

		it("should handle upload failures", async () => {
			const mockTopics = [createMockTopic()];
			apiClient["request"] = vi.fn().mockRejectedValue(new Error("Upload failed"));

			const result = await stateSync.uploadTopics(mockTopics);
			expect(result.uploaded).toBe(0);
			expect(result.failed).toBe(1);
		});

		it("should handle partial upload success", async () => {
			const mockTopics = [createMockTopic(), createMockTopic({ id: "topic-2" })];
			const mockResponse = { uploaded: 1, topic_ids: ["topic-1"] };

			apiClient["request"] = vi.fn().mockResolvedValue(mockResponse);

			const result = await stateSync.uploadTopics(mockTopics);
			expect(result.uploaded).toBe(1);
			expect(result.failed).toBe(1);
		});
	});

	describe("create validation", () => {
		it("should create validation task successfully", async () => {
			const mockResponse = { task_id: "task-1", status: "pending" };
			apiClient["request"] = vi.fn().mockResolvedValue(mockResponse);

			const taskId = await stateSync.createValidation(["topic-1"]);
			expect(taskId).toBe("task-1");
		});

		it("should return null on failure", async () => {
			apiClient["request"] = vi.fn().mockRejectedValue(new Error("Failed"));

			const taskId = await stateSync.createValidation(["topic-1"]);
			expect(taskId).toBeNull();
		});
	});

	describe("get validation status", () => {
		it("should return task status", async () => {
			const mockStatus = createMockTaskStatus();
			apiClient["request"] = vi.fn().mockResolvedValue(mockStatus);

			const status = await stateSync.getValidationStatus("task-1");
			expect(status).toEqual(mockStatus);
		});

		it("should return null on error", async () => {
			apiClient["request"] = vi.fn().mockRejectedValue(new Error("Failed"));

			const status = await stateSync.getValidationStatus("task-1");
			expect(status).toBeNull();
		});
	});

	describe("get proposals", () => {
		it("should return cached proposals", async () => {
			const mockProposals = [createMockProposal()];
			const cacheSpy = vi.spyOn(stateSync["cache"], "get").mockReturnValueOnce(mockProposals);

			const proposals = await stateSync.getProposals("topic-1");
			expect(proposals).toEqual(mockProposals);
			expect(cacheSpy).toHaveBeenCalledWith("proposals-topic-1");
		});

		it("should fetch and cache proposals", async () => {
			const mockProposals = [createMockProposal()];
			const mockResponse = { proposals: mockProposals, total: 1 };

			apiClient["request"] = vi.fn().mockResolvedValue(mockResponse);
			const cacheSpy = vi.spyOn(stateSync["cache"], "get").mockReturnValueOnce(null);

			const proposals = await stateSync.getProposals("topic-1");
			expect(proposals).toEqual(mockProposals);
		});

		it("should return empty array on error", async () => {
			apiClient["request"] = vi.fn().mockRejectedValue(new Error("Failed"));
			const cacheSpy = vi.spyOn(stateSync["cache"], "get").mockReturnValueOnce(null);

			const proposals = await stateSync.getProposals("topic-1");
			expect(proposals).toEqual([]);
		});
	});

	describe("poll validation status", () => {
		it("should poll and call onComplete when task completes", async () => {
			const mockResult = createMockValidationResult();
			const mockStatus = createMockTaskStatus({ status: "completed" });

			let completed = false;
			let result: ValidationResult | null = null;

			// Mock the specific API methods
			apiClient.getTaskStatus = vi.fn().mockResolvedValue(mockStatus);
			apiClient.getValidationResult = vi.fn().mockResolvedValue(mockResult);

			await stateSync.pollValidationStatus("task-1", undefined, (r) => {
				completed = true;
				result = r;
			});

			expect(completed).toBe(true);
			expect(result).toEqual(mockResult);
		});

		it("should call onError when task fails", async () => {
			const mockStatus = createMockTaskStatus({ status: "failed" });

			let failed = false;
			let error: Error | null = null;

			apiClient.getTaskStatus = vi.fn().mockResolvedValue(mockStatus);

			await stateSync.pollValidationStatus("task-1", undefined, undefined, (e) => {
				failed = true;
				error = e;
			});

			expect(failed).toBe(true);
			expect((error as Error | null)?.message).toBe("Validation failed");
		});
	});

	describe("destroy", () => {
		it("should clean up all resources", () => {
			stateSync.registerTask("task-1", "topic-1");
			stateSync.start();

			stateSync.destroy();

			expect(stateSync.isActive()).toBe(false);
			expect(stateSync.getActiveTaskCount()).toBe(0);
		});
	});
});
