/**
 * Mock Obsidian API
 *
 * This file provides mock implementations for Obsidian's API
 * which is only available in the Obsidian Electron environment.
 */

export class Notice {
	constructor(
		public message: string,
		public timeout: number = 5000
	) {}
}

export class TFile {
	constructor(
		public path: string,
		public name: string,
		public basename: string,
		public extension: string
	) {}
}

export class TFolder {
	constructor(
		public path: string,
		public name: string
	) {}
}

export class Menu {
	constructor() {}

	addItem(item: any): this {
		return this;
	}
}

export class MenuItem {
	constructor(public menu: Menu) {}

	setTitle(title: string): this {
		return this;
	}

	setIcon(icon: string): this {
		return this;
	}

	setId(id: string): this {
		return this;
	}

	setIsChecked(isChecked: boolean): this {
		return this;
	}

	setDisabled(disabled: boolean): this {
		return this;
	}

	setDisabledReason(reason: string): this {
		return this;
	}

	onClick(callback: () => void): this {
		return this;
	}
}

export interface App {
	vault: {
		read(file: TFile): Promise<string>;
		write(file: TFile, data: string): Promise<void>;
		modify(file: TFile, data: string): Promise<void>;
		create(path: string, data: string): Promise<TFile>;
		delete(file: TFile): Promise<void>;
		exists(path: string): boolean;
		list(): string[];
		getMarkdownFiles(): TFile[];
		getAbstractFileByPath(path: string): TFile | TFolder | null;
	};
	workspace: {
		getActiveFile(): TFile | null;
		openLinkText(linkText: string, sourcePath: string): void;
	};
	metadataCache: {
		getCache(file: TFile): any;
	};
}

export const Plugin = class {
	loaded: boolean = false;
	manifest: any = {};

	addRibbonIcon(icon: string, title: string, callback: () => void): HTMLElement {
		return document.createElement("div");
	}

	addStatusBarItem(): HTMLElement {
		return document.createElement("div");
	}

	addSettingTab(tab: any): void {}

	registerEvent(event: any): void {}

	registerContextMenu(
		location: string,
		callback: (menu: Menu, file: TFile) => void
	): void {}

	async loadData(): Promise<any> {
		return {};
	}

	async saveData(data: any): Promise<void> {}
};

// Default export for compatibility
export default {
	Notice,
	TFile,
	TFolder,
	Menu,
	MenuItem,
	Plugin,
};
