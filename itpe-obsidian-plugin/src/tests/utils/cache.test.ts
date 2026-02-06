/**
 * Cache Manager Tests
 */
import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { CacheManager } from "../../utils/cache";

describe("CacheManager", () => {
	let cache: CacheManager<string>;

	beforeEach(() => {
		// Use vitest fake timers
		vi.useFakeTimers();
		cache = new CacheManager(1000); // 1 second TTL for testing
	});

	afterEach(() => {
		vi.restoreAllMocks();
	});

	describe("set and get", () => {
		it("should store and retrieve values", () => {
			cache.set("key1", "value1");
			expect(cache.get("key1")).toBe("value1");
		});

		it("should return null for non-existent keys", () => {
			expect(cache.get("nonexistent")).toBeNull();
		});

		it("should support custom TTL", () => {
			cache.set("key1", "value1", 5000); // 5 seconds
			expect(cache.get("key1")).toBe("value1");
		});
	});

	describe("TTL expiration", () => {
		it("should expire entries after TTL", () => {
			cache.set("key1", "value1");
			expect(cache.get("key1")).toBe("value1");

			// Advance time past TTL
			vi.advanceTimersByTime(1100);
			expect(cache.get("key1")).toBeNull();
		});

		it("should not expire entries before TTL", () => {
			cache.set("key1", "value1");
			vi.advanceTimersByTime(500);
			expect(cache.get("key1")).toBe("value1");
		});

		it("should use custom TTL when provided", () => {
			cache.set("key1", "value1", 2000);
			vi.advanceTimersByTime(1100);
			expect(cache.get("key1")).toBe("value1");

			vi.advanceTimersByTime(1000);
			expect(cache.get("key1")).toBeNull();
		});
	});

	describe("has", () => {
		it("should return true for existing valid entries", () => {
			cache.set("key1", "value1");
			expect(cache.has("key1")).toBe(true);
		});

		it("should return false for non-existent entries", () => {
			expect(cache.has("nonexistent")).toBe(false);
		});

		it("should return false for expired entries", () => {
			cache.set("key1", "value1");
			vi.advanceTimersByTime(1100);
			expect(cache.has("key1")).toBe(false);
		});
	});

	describe("clear", () => {
		it("should remove specific entry", () => {
			cache.set("key1", "value1");
			cache.set("key2", "value2");

			cache.clear("key1");
			expect(cache.get("key1")).toBeNull();
			expect(cache.get("key2")).toBe("value2");
		});

		it("should not error when clearing non-existent key", () => {
			expect(() => cache.clear("nonexistent")).not.toThrow();
		});
	});

	describe("clearAll", () => {
		it("should remove all entries", () => {
			cache.set("key1", "value1");
			cache.set("key2", "value2");
			cache.set("key3", "value3");

			cache.clearAll();
			expect(cache.get("key1")).toBeNull();
			expect(cache.get("key2")).toBeNull();
			expect(cache.get("key3")).toBeNull();
		});
	});

	describe("cleanup", () => {
		it("should remove expired entries", () => {
			cache.set("key1", "value1", 500);
			cache.set("key2", "value2", 2000);
			cache.set("key3", "value3", 500);

			vi.advanceTimersByTime(600);

			const removed = cache.cleanup();
			expect(removed).toBe(2);
			expect(cache.get("key1")).toBeNull();
			expect(cache.get("key2")).toBe("value2");
			expect(cache.get("key3")).toBeNull();
		});

		it("should return 0 when no entries are expired", () => {
			cache.set("key1", "value1");
			const removed = cache.cleanup();
			expect(removed).toBe(0);
		});
	});

	describe("type safety", () => {
		it("should store complex objects", () => {
			const objCache = new CacheManager<{ name: string }>(1000);
			const obj = { name: "test" };
			objCache.set("key1", obj);
			expect(objCache.get("key1")).toEqual(obj);
		});

		it("should store arrays", () => {
			const arrayCache = new CacheManager<number[]>(1000);
			const arr = [1, 2, 3];
			arrayCache.set("key1", arr);
			expect(arrayCache.get("key1")).toEqual(arr);
		});
	});
});
