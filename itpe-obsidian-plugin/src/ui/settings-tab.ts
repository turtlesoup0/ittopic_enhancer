/**
 * Settings Tab for ITPE Plugin
 *
 * 플러그인 설정 UI 탭 구현
 */
import { App, Notice, PluginSettingTab, Setting } from "obsidian";
import ITPEPlugin from "../main";

/**
 * ITPE 플러그인 설정 탭
 */
export class ITPEPluginSettingTab extends PluginSettingTab {
	plugin: ITPEPlugin;

	constructor(app: App, plugin: ITPEPlugin) {
		super(app, plugin);
		this.plugin = plugin;
	}

	display(): void {
		const { containerEl } = this;
		containerEl.empty();

		// Header
		containerEl.createEl("h2", { text: "ITPE Topic Enhancement Plugin 설정" });

		// Backend URL
		new Setting(containerEl)
			.setName("백엔드 API URL")
			.setDesc("백엔드 API 서버 주소")
			.addText((text) =>
				text
					.setPlaceholder("http://localhost:8000")
					.setValue(this.plugin.settings.backendUrl)
					.onChange(async (value) => {
						this.plugin.settings.backendUrl = value;
						await this.plugin.saveSettings();
					})
			);

		// API Key
		new Setting(containerEl)
			.setName("API 키")
			.setDesc("백엔드 API 인증 키")
			.addText((text) =>
				text
					.setPlaceholder("API 키 입력...")
					.setValue(this.plugin.settings.apiKey)
					.onChange(async (value) => {
						this.plugin.settings.apiKey = value;
						await this.plugin.saveSettings();
					})
			);

		// Auto Sync
		new Setting(containerEl)
			.setName("자동 동기화")
			.setDesc("검증 결과 자동 동기화")
			.addToggle((toggle) =>
				toggle
					.setValue(this.plugin.settings.autoSync)
					.onChange(async (value) => {
						this.plugin.settings.autoSync = value;
						await this.plugin.saveSettings();

						if (value) {
							this.plugin.restartAutoSync();
						} else {
							this.plugin.stopAutoSync();
						}
					})
			);

		// Sync Interval
		new Setting(containerEl)
			.setName("동기화 간격")
			.setDesc("자동 동기화 간격 (분)")
			.addSlider((slider) =>
				slider
					.setLimits(1, 60, 1)
					.setValue(this.plugin.settings.syncInterval)
					.setDynamicTooltip()
					.onChange(async (value) => {
						this.plugin.settings.syncInterval = value;
						await this.plugin.saveSettings();

						if (this.plugin.settings.autoSync) {
							this.plugin.restartAutoSync();
						}
					})
			);

		// Show Status Bar
		new Setting(containerEl)
			.setName("상태 표시줄 표시")
			.setDesc("상태 표시줄 표시 여부")
			.addToggle((toggle) =>
				toggle
					.setValue(this.plugin.settings.showStatusBar)
					.onChange(async (value) => {
						this.plugin.settings.showStatusBar = value;
						await this.plugin.saveSettings();
					})
			);

		// Debug Mode
		new Setting(containerEl)
			.setName("디버그 모드")
			.setDesc("상세 로그 출력")
			.addToggle((toggle) =>
				toggle
					.setValue(this.plugin.settings.debugMode)
					.onChange(async (value) => {
						this.plugin.settings.debugMode = value;
						await this.plugin.saveSettings();
					})
			);

		// Domain Folders
		new Setting(containerEl)
			.setName("도메인 폴더")
			.setDesc("토픽을 검색할 도메인 폴더 목록 (쉼표로 구분)")
			.addText((text) =>
				text
					.setPlaceholder("SW, 정보보안, 신기술")
					.setValue(this.plugin.settings.domainFolders.join(", "))
					.onChange(async (value) => {
						this.plugin.settings.domainFolders = value
							.split(",")
							.map((s) => s.trim())
							.filter((s) => s.length > 0);
						await this.plugin.saveSettings();
					})
			);

		// Test Connection Button
		new Setting(containerEl)
			.setName("연결 테스트")
			.setDesc("백엔드 API 연결 상태 확인")
			.addButton((button) =>
				button
					.setButtonText("테스트")
					.onClick(async () => {
						const originalText = button.buttonEl.innerText;
						button.buttonEl.innerText = "테스트 중...";
						button.buttonEl.disabled = true;

						try {
							const success = await this.plugin.apiClient.testConnection();
							if (success) {
								new Notice("연결 성공!", 3000);
							} else {
								new Notice("연결 실패. 설정을 확인해주세요.", 5000);
							}
						} catch (error) {
							new Notice("연결 오류가 발생했습니다.", 5000);
						} finally {
							button.buttonEl.innerText = originalText;
							button.buttonEl.disabled = false;
						}
					})
			);
	}
}
