/**
 * Plugin Settings Management
 *
 * 플러그인 설정 관리 모듈
 */

import { Notice } from "obsidian";
import { ITPEPluginSettings as IPluginSettings, DEFAULT_SETTINGS } from "./api/types";

/**
 * Plugin Settings Class
 *
 * 플러그인 설정 클래스. 기본값과 함께 설정을 관리합니다.
 */
export class ITPEPluginSettings implements IPluginSettings {
	backendUrl: string;
	apiKey: string;
	autoSync: boolean;
	syncInterval: number;
	showStatusBar: boolean;
	debugMode: boolean;
	domainFolders: string[];

	constructor(settings?: Partial<IPluginSettings>) {
		this.backendUrl = settings?.backendUrl ?? DEFAULT_SETTINGS.backendUrl;
		this.apiKey = settings?.apiKey ?? DEFAULT_SETTINGS.apiKey;
		this.autoSync = settings?.autoSync ?? DEFAULT_SETTINGS.autoSync;
		this.syncInterval = settings?.syncInterval ?? DEFAULT_SETTINGS.syncInterval;
		this.showStatusBar = settings?.showStatusBar ?? DEFAULT_SETTINGS.showStatusBar;
		this.debugMode = settings?.debugMode ?? DEFAULT_SETTINGS.debugMode;
		this.domainFolders = settings?.domainFolders ?? [...DEFAULT_SETTINGS.domainFolders];
	}
}

/**
 * 설정 유효성 검증
 *
 * @param settings - 검증할 설정 객체
 * @returns 유효성 여부
 */
export function validateSettings(settings: ITPEPluginSettings): boolean {
	if (!settings.backendUrl) {
		new Notice("백엔드 URL이 필요합니다.");
		return false;
	}

	try {
		new URL(settings.backendUrl);
	} catch {
		new Notice("유효하지 않은 백엔드 URL입니다.");
		return false;
	}

	if (settings.syncInterval < 1 || settings.syncInterval > 60) {
		new Notice("동기화 간격은 1-60분 사이여야 합니다.");
		return false;
	}

	return true;
}

/**
 * 설정 내보내기 (백업용)
 *
 * @param settings - 내보낼 설정 객체
 * @returns JSON 문자열
 */
export function exportSettings(settings: ITPEPluginSettings): string {
	return JSON.stringify(settings, null, 2);
}

/**
 * 설정 가져오기 (복구용)
 *
 * @param json - JSON 문자열
 * @returns 설정 객체 또는 null
 */
export function importSettings(json: string): ITPEPluginSettings | null {
	try {
		const parsed = JSON.parse(json);
		return new ITPEPluginSettings(parsed);
	} catch {
		return null;
	}
}

// Re-export types for convenience
export { DEFAULT_SETTINGS } from "./api/types";
