/**
 * Cache management for ITPE Plugin
 */
export class CacheManager<T> {
	private cache: Map<string, { data: T; timestamp: number; ttl: number }>;
	private defaultTTL: number;

	constructor(defaultTTL: number = 5 * 60 * 1000) {
		// Default TTL: 5 minutes
		this.cache = new Map();
		this.defaultTTL = defaultTTL;
	}

	/**
	 * Set cache value
	 */
	set(key: string, data: T, ttl?: number): void {
		this.cache.set(key, {
			data,
			timestamp: Date.now(),
			ttl: ttl || this.defaultTTL,
		});
	}

	/**
	 * Get cache value
	 */
	get(key: string): T | null {
		const entry = this.cache.get(key);
		if (!entry) {
			return null;
		}

		const now = Date.now();
		if (now - entry.timestamp > entry.ttl) {
			this.cache.delete(key);
			return null;
		}

		return entry.data;
	}

	/**
	 * Check if cache exists and is valid
	 */
	has(key: string): boolean {
		return this.get(key) !== null;
	}

	/**
	 * Clear specific cache entry
	 */
	clear(key: string): void {
		this.cache.delete(key);
	}

	/**
	 * Clear all cache entries
	 */
	clearAll(): void {
		this.cache.clear();
	}

	/**
	 * Clean up expired entries
	 */
	cleanup(): number {
		const now = Date.now();
		let removed = 0;
		for (const [key, entry] of this.cache.entries()) {
			if (now - entry.timestamp > entry.ttl) {
				this.cache.delete(key);
				removed++;
			}
		}
		return removed;
	}
}
