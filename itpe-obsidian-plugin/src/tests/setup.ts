/**
 * Test Setup for ITPE Plugin
 *
 * Common test fixtures, mocks, and utilities.
 */

import { vi } from "vitest";
import type { App } from "obsidian";
import { DomainEnum, ProposalPriority, TaskStatus, GapType, ReferenceSourceType } from "../api/types";

/**
 * Mock App instance
 */
export const mockApp = {
	vault: {
		read: vi.fn(),
		write: vi.fn(),
		modify: vi.fn(),
		create: vi.fn(),
		delete: vi.fn(),
		exists: vi.fn(),
		list: vi.fn(),
		getMarkdownFiles: vi.fn(() => []),
		getAbstractFileByPath: vi.fn(),
	},
	workspace: {
		getActiveFile: vi.fn(),
		openLinkText: vi.fn(),
	},
	metadataCache: {},
} as unknown as App;

/**
 * Mock Logger instance
 */
export const mockLogger = {
	debug: vi.fn(),
	info: vi.fn(),
	warn: vi.fn(),
	error: vi.fn(),
	api: vi.fn(),
	_debugMode: false,
	get debugMode(): boolean {
		return this._debugMode;
	},
	set debugMode(value: boolean) {
		this._debugMode = value;
	},
};

/**
 * Mock API Client
 */
export const mockApiClient = {
	uploadTopics: vi.fn(),
	createValidation: vi.fn(),
	getTaskStatus: vi.fn(),
	getValidationResult: vi.fn(),
	getProposals: vi.fn(),
	updateTopic: vi.fn(),
	testConnection: vi.fn(),
};

/**
 * Mock StateSyncManager dependencies
 */
export const mockStateSyncDeps = {
	app: mockApp,
	apiClient: mockApiClient,
	logger: mockLogger,
};

/**
 * Create a mock topic
 */
export function createMockTopic(overrides = {}) {
	return {
		id: "test-topic-id",
		metadata: {
			file_path: "/test/path.md",
			file_name: "test.md",
			folder: "test",
			domain: DomainEnum.SW,
		},
		content: {
			리드문: "Test lead sentence",
			정의: "Test definition",
			키워드: ["test", "keyword"],
			해시태그: "#test",
			암기: "Test memory aid",
		},
		completion: {
			리드문: true,
			정의: true,
			키워드: true,
			해시태그: true,
			암기: true,
		},
		...overrides,
	};
}

/**
 * Create a mock validation result
 */
export function createMockValidationResult(overrides = {}) {
	return {
		id: "validation-1",
		topic_id: "test-topic-id",
		overall_score: 0.85,
		field_completeness_score: 0.9,
		content_accuracy_score: 0.8,
		reference_coverage_score: 0.85,
		gaps: [],
		matched_references: [],
		validation_timestamp: new Date().toISOString(),
		...overrides,
	};
}

/**
 * Create a mock task status response
 */
export function createMockTaskStatus(overrides = {}) {
	return {
		id: "task-1",
		status: TaskStatus.PENDING,
		created_at: new Date().toISOString(),
		...overrides,
	};
}

/**
 * Create a mock enhancement proposal
 */
export function createMockProposal(overrides = {}) {
	return {
		id: "proposal-1",
		topic_id: "test-topic-id",
		priority: ProposalPriority.HIGH,
		title: "Test Proposal",
		description: "Test proposal description",
		current_content: "Old content",
		suggested_content: "New content",
		target_field: "정의",
		reasoning: "Test reasoning",
		reference_sources: [],
		estimated_effort: 30,
		confidence: 0.9,
		created_at: new Date().toISOString(),
		...overrides,
	};
}

/**
 * Wait for async operations
 */
export function flushPromises(): Promise<void> {
	return new Promise((resolve) => setTimeout(resolve, 0));
}

/**
 * Advance timers by a specified amount
 */
export function advanceTimersByTime(ms: number): void {
	vi.advanceTimersByTime(ms);
}

/**
 * Clear all mocks
 */
export function clearAllMocks(): void {
	vi.clearAllMocks();
}
