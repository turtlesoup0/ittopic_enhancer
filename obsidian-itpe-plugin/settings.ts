import { App, PluginSettingTab, Setting } from "obsidian";
import ITPEPlugin from "./main";
import { DomainEnum, ITPEPluginSettings, DEFAULT_SETTINGS } from "./types";

/**
 * ITPE Plugin 설정 탭
 * API 엔드포인트, API 키, 도메인 매핑 등을 설정합니다.
 */
export class ITPESettingTab extends PluginSettingTab {
	plugin: ITPEPlugin;

	constructor(app: App, plugin: ITPEPlugin) {
		super(app, plugin);
		this.plugin = plugin;
	}

	display(): void {
		const { containerEl } = this;
		containerEl.empty();

		// 헤더
		containerEl.createEl("h2", { text: "ITPE Topic Enhancement 설정" });

		// API 설정 섹션
		this.addApiSettings(containerEl);

		// 동기화 설정 섹션
		this.addSyncSettings(containerEl);

		// 도메인 매핑 섹션
		this.addDomainMappingSettings(containerEl);

		// 알림 설정 섹션
		this.addNotificationSettings(containerEl);
	}

	private addApiSettings(containerEl: HTMLElement): void {
		containerEl.createEl("h3", { text: "API 설정" });

		new Setting(containerEl)
			.setName("API 엔드포인트")
			.setDesc("ITPE Topic Enhancement 백엔드 API 주소")
			.addText((text) =>
				text
					.setPlaceholder("http://localhost:8000/api/v1")
					.setValue(this.plugin.settings.apiEndpoint)
					.onChange(async (value) => {
						this.plugin.settings.apiEndpoint = value;
						await this.plugin.saveSettings();
					})
			);

		new Setting(containerEl)
			.setName("API 키")
			.setDesc("인증을 위한 API 키 (선택 사항)")
			.addText((text) =>
				text
					.setPlaceholder("선택 사항")
					.setValue(this.plugin.settings.apiKey)
					.onChange(async (value) => {
						this.plugin.settings.apiKey = value;
						await this.plugin.saveSettings();
					})
			);

		// 연결 테스트 버튼
		new Setting(containerEl)
			.setName("연결 테스트")
			.setDesc("API 서버와의 연결을 테스트합니다")
			.addButton((button) =>
				button
					.setButtonText("테스트")
					.onClick(async () => {
						button.setButtonText("테스트 중...");
						button.setDisabled(true);

						const success = await this.plugin.testApiConnection();

						if (success) {
							button.setButtonText("성공!");
							button.setCta();
							setTimeout(() => {
								button.setButtonText("테스트");
								button.setDisabled(false);
								button.removeCta();
							}, 2000);
						} else {
							button.setButtonText("실패");
							setTimeout(() => {
								button.setButtonText("테스트");
								button.setDisabled(false);
							}, 2000);
						}
					})
			);
	}

	private addSyncSettings(containerEl: HTMLElement): void {
		containerEl.createEl("h3", { text: "동기화 설정" });

		new Setting(containerEl)
			.setName("자동 동기화")
			.setDesc("주기적으로 토픽을 자동으로 동기화합니다")
			.addToggle((toggle) =>
				toggle
					.setValue(this.plugin.settings.autoSync)
					.onChange(async (value) => {
						this.plugin.settings.autoSync = value;
						await this.plugin.saveSettings();

						if (value) {
							this.plugin.startAutoSync();
						} else {
							this.plugin.stopAutoSync();
						}
					})
			);

		new Setting(containerEl)
			.setName("동기화 주기")
			.setDesc("자동 동기화 간격 (분)")
			.addSlider((slider) =>
				slider
					.setLimits(5, 1440, 5)
					.setValue(this.plugin.settings.syncInterval)
					.setDynamicTooltip()
					.onChange(async (value) => {
						this.plugin.settings.syncInterval = value;
						await this.plugin.saveSettings();

						// 자동 동기화가 켜져 있으면 재시작
						if (this.plugin.settings.autoSync) {
							this.plugin.restartAutoSync();
						}
					})
			);

		new Setting(containerEl)
			.setName("지금 동기화")
			.setDesc("모든 토픽을 백엔드로 업로드하고 검증을 요청합니다")
			.addButton((button) =>
				button
					.setButtonText("동기화 시작")
					.setCta()
					.onClick(async () => {
						button.setButtonText("동기화 중...");
						button.setDisabled(true);

						try {
							const result = await this.plugin.syncAllTopics();
							button.setButtonText(`${result.count}개 완료`);

							setTimeout(() => {
								button.setButtonText("동기화 시작");
								button.setDisabled(false);
								button.setCta();
							}, 3000);
						} catch (error) {
							button.setButtonText("실패");
							setTimeout(() => {
								button.setButtonText("동기화 시작");
								button.setDisabled(false);
								button.setCta();
							}, 2000);
						}
					})
			);
	}

	private addDomainMappingSettings(containerEl: HTMLElement): void {
		containerEl.createEl("h3", { text: "도메인 매핑" });
		containerEl.createEl("p", {
			text: "폴더 이름을 도메인에 매핑합니다. Dataview 쿼리 경로에 맞게 설정하세요."
		});

		const domains = Object.values(DomainEnum);
		const currentMapping = this.plugin.settings.domainMapping;

		domains.forEach((domain) => {
			new Setting(containerEl)
				.setName(domain)
				.setDesc(`${domain} 도메인에 해당하는 폴더 이름`)
				.addText((text) =>
					text
						.setPlaceholder("폴더 이름")
						.setValue(currentMapping[domain] || "")
						.onChange(async (value) => {
							if (value) {
								this.plugin.settings.domainMapping[value] = domain as DomainEnum;
								await this.plugin.saveSettings();
							}
						})
				);
		});
	}

	private addNotificationSettings(containerEl: HTMLElement): void {
		containerEl.createEl("h3", { text: "알림 설정" });

		new Setting(containerEl)
			.setName("알림 표시")
			.setDesc("동기화 및 검증 완료 시 알림을 표시합니다")
			.addToggle((toggle) =>
				toggle
					.setValue(this.plugin.settings.notificationsEnabled)
					.onChange(async (value) => {
						this.plugin.settings.notificationsEnabled = value;
						await this.plugin.saveSettings();
					})
			);
	}
}
