/**
 * Logger Tests
 */
import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { Logger } from "../../utils/logger";

describe("Logger", () => {
	let logger: Logger;
	let consoleLogSpy: ReturnType<typeof vi.spyOn>;
	let consoleWarnSpy: ReturnType<typeof vi.spyOn>;
	let consoleErrorSpy: ReturnType<typeof vi.spyOn>;

	beforeEach(() => {
		logger = new Logger(false);
		consoleLogSpy = vi.spyOn(console, "log").mockImplementation(() => {});
		consoleWarnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
		consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
	});

	afterEach(() => {
		vi.restoreAllMocks();
	});

	describe("debug mode", () => {
		it("should have debug mode off by default", () => {
			const defaultLogger = new Logger();
			expect(defaultLogger.debugMode).toBe(false);
		});

		it("should set debug mode via constructor", () => {
			const debugLogger = new Logger(true);
			expect(debugLogger.debugMode).toBe(true);
		});

		it("should allow changing debug mode", () => {
			expect(logger.debugMode).toBe(false);
			logger.debugMode = true;
			expect(logger.debugMode).toBe(true);
		});
	});

	describe("debug logging", () => {
		it("should not log debug messages when debug mode is off", () => {
			logger.debug("test message");
			expect(consoleLogSpy).not.toHaveBeenCalled();
		});

		it("should log debug messages when debug mode is on", () => {
			logger.debugMode = true;
			logger.debug("test message");
			expect(consoleLogSpy).toHaveBeenCalledWith("[ITPE Debug] test message");
		});

		it("should log debug messages with additional arguments", () => {
			logger.debugMode = true;
			logger.debug("test message", { foo: "bar" });
			expect(consoleLogSpy).toHaveBeenCalledWith("[ITPE Debug] test message", { foo: "bar" });
		});
	});

	describe("API logging with data", () => {
		it("should log API calls with data as empty string when undefined", () => {
			logger.debugMode = true;
			logger.api("GET", "/api/test", undefined);
			expect(consoleLogSpy).toHaveBeenCalledWith("[ITPE API] GET /api/test", "");
		});
	});

	describe("info logging", () => {
		it("should always log info messages", () => {
			logger.info("test message");
			expect(consoleLogSpy).toHaveBeenCalledWith("[ITPE] test message");
		});

		it("should log info messages with additional arguments", () => {
			logger.info("test message", 123, true);
			expect(consoleLogSpy).toHaveBeenCalledWith("[ITPE] test message", 123, true);
		});
	});

	describe("warn logging", () => {
		it("should always log warn messages", () => {
			logger.warn("test warning");
			expect(consoleWarnSpy).toHaveBeenCalledWith("[ITPE Warning] test warning");
		});

		it("should log warn messages with additional arguments", () => {
			logger.warn("test warning", { code: 500 });
			expect(consoleWarnSpy).toHaveBeenCalledWith("[ITPE Warning] test warning", { code: 500 });
		});
	});

	describe("error logging", () => {
		it("should always log error messages", () => {
			logger.error("test error");
			expect(consoleErrorSpy).toHaveBeenCalledWith("[ITPE Error] test error", undefined);
		});

		it("should log error messages with error object", () => {
			const error = new Error("test error details");
			logger.error("test error", error);
			expect(consoleErrorSpy).toHaveBeenCalledWith("[ITPE Error] test error", error);
		});

		it("should log error messages with custom error data", () => {
			logger.error("test error", { code: "ERR_001", message: "Custom error" });
			expect(consoleErrorSpy).toHaveBeenCalledWith("[ITPE Error] test error", { code: "ERR_001", message: "Custom error" });
		});
	});

	describe("API logging", () => {
		it("should not log API calls when debug mode is off", () => {
			logger.api("GET", "/api/test");
			expect(consoleLogSpy).not.toHaveBeenCalled();
		});

		it("should log API calls when debug mode is on", () => {
			logger.debugMode = true;
			logger.api("GET", "/api/test");
			expect(consoleLogSpy).toHaveBeenCalledWith("[ITPE API] GET /api/test", "");
		});

		it("should log API calls with data", () => {
			logger.debugMode = true;
			logger.api("POST", "/api/test", { foo: "bar" });
			expect(consoleLogSpy).toHaveBeenCalledWith("[ITPE API] POST /api/test", { foo: "bar" });
		});
	});

	describe("message formatting", () => {
		it("should prefix debug messages correctly", () => {
			logger.debugMode = true;
			logger.debug("test");
			expect(consoleLogSpy).toHaveBeenCalledWith("[ITPE Debug] test");
		});

		it("should prefix info messages correctly", () => {
			logger.info("test");
			expect(consoleLogSpy).toHaveBeenCalledWith("[ITPE] test");
		});

		it("should prefix warning messages correctly", () => {
			logger.warn("test");
			expect(consoleWarnSpy).toHaveBeenCalledWith("[ITPE Warning] test");
		});

		it("should prefix error messages correctly", () => {
			logger.error("test");
			expect(consoleErrorSpy).toHaveBeenCalledWith("[ITPE Error] test", undefined);
		});

		it("should prefix API messages correctly", () => {
			logger.debugMode = true;
			logger.api("GET", "/test");
			expect(consoleLogSpy).toHaveBeenCalledWith("[ITPE API] GET /test", "");
		});
	});
});
