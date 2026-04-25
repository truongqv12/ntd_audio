import { memo, useMemo } from "react";
import type { ProviderSummary } from "../types";
import { Panel } from "../components/Panel";
import { useI18n } from "../i18n";

export const VoiceLabPage = memo(function VoiceLabPage({ providers }: { providers: ProviderSummary[] }) {
  const { t } = useI18n();
  const customVoiceProviders = useMemo(
    () =>
      providers.filter(
        (provider) => provider.capabilities.custom_voice || provider.capabilities.voice_cloning,
      ),
    [providers],
  );

  return (
    <div className="page-grid two-up">
      <Panel title={t("voiceLab.title")} description={t("voiceLab.description")}>
        <div className="voice-lab-flow">
          <div className="lab-step-card">
            <strong>{t("voiceLab.step1Title")}</strong>
            <p>{t("voiceLab.step1Body")}</p>
          </div>
          <div className="lab-step-card">
            <strong>{t("voiceLab.step2Title")}</strong>
            <p>{t("voiceLab.step2Body")}</p>
          </div>
          <div className="lab-step-card">
            <strong>{t("voiceLab.step3Title")}</strong>
            <p>{t("voiceLab.step3Body")}</p>
          </div>
        </div>
        <div className="section-divider" />
        <div className="research-note-card">
          <strong>{t("voiceLab.cloneResearchTitle")}</strong>
          <p>{t("voiceLab.cloneResearchBody")}</p>
        </div>
      </Panel>
      <Panel title={t("voiceLab.eligibleTitle")} description={t("voiceLab.eligibleDescription")}>
        <div className="provider-stack-grid">
          {customVoiceProviders.map((provider) => (
            <div key={provider.key} className="provider-stack-card">
              <div className="provider-stack-head">
                <div>
                  <strong>{provider.label}</strong>
                  <p>{provider.key}</p>
                </div>
                <span className="tiny-badge tiny-badge-cloud">voice-lab</span>
              </div>
              <div className="chip-row">
                {provider.capabilities.custom_voice ? (
                  <span className="chip">{t("voiceLab.customVoice")}</span>
                ) : null}
                {provider.capabilities.voice_cloning ? (
                  <span className="chip">{t("voiceLab.cloning")}</span>
                ) : null}
              </div>
            </div>
          ))}
          {customVoiceProviders.length === 0 ? (
            <p className="muted-copy">{t("voiceLab.noEligible")}</p>
          ) : null}
        </div>
      </Panel>
    </div>
  );
});
