/**
 * Logging utility for ITPE Plugin
 */
export class Logger {
	private _debugMode: boolean;

	constructor(debugMode: boolean = false) {
		this._debugMode = debugMode;
	}

	/**
	 * Get debug mode state
	 */
	get debugMode(): boolean {
		return this._debugMode;
	}

	/**
	 * Set debug mode state
	 */
	set debugMode(value: boolean) {
		this._debugMode = value;
	}

	/**
	 * Log debug message
	 */
	debug(message: string, ...args: unknown[]): void {
		if (this._debugMode) {
			console.log(`[ITPE Debug] ${message}`, ...args);
		}
	}

	/**
	 * Log info message
	 */
	info(message: string, ...args: unknown[]): void {
		console.log(`[ITPE] ${message}`, ...args);
	}

	/**
	 * Log warning message
	 */
	warn(message: string, ...args: unknown[]): void {
		console.warn(`[ITPE Warning] ${message}`, ...args);
	}

	/**
	 * Log error message
	 */
	error(message: string, error?: unknown): void {
		console.error(`[ITPE Error] ${message}`, error);
	}

	/**
	 * Log API call
	 */
	api(method: string, url: string, data?: unknown): void {
		if (this._debugMode) {
			console.log(`[ITPE API] ${method} ${url}`, data || "");
		}
	}
}
