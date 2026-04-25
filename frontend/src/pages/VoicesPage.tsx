import { memo, useMemo, useState } from "react";
import type { ProviderSummary, VoiceCatalogEntry } from "../types";
import { Panel } from "../components/Panel";
import { VoiceAvatar } from "../components/VoiceAvatar";
import { VoicePickerDialog } from "../components/VoicePickerDialog";
import { useI18n } from "../i18n";
import { capabilityBadges, formatLocaleLabel } from "../lib/voice";

export const VoicesPage = memo(function VoicesPage({
  voices,
  providers,
  selectedVoice,
  onSelectVoice,
}: {
  voices: VoiceCatalogEntry[];
  providers: ProviderSummary[];
  selectedVoice: VoiceCatalogEntry | null;
  onSelectVoice: (voice: VoiceCatalogEntry) => void;
}) {
  const { locale, t } = useI18n();
  const [isPickerOpen, setIsPickerOpen] = useState(false);

  const providerGroups = useMemo(
    () => providers.map((provider) => ({ provider, count: voices.filter((voice) => voice.provider_key === provider.key).length })),
    [providers, voices],
  );

  return (
    <>
      <div className="page-grid two-up">
        <Panel
          title={t("voicesPage.title")}
          description={t("voicesPage.description")}
          actions={<button type="button" className="ghost-button compact-button" onClick={() => setIsPickerOpen(true)}>{t("voicesPage.openPicker")}</button>}
        >
          <div className="provider-stack-grid provider-stack-grid-wide">
            {providerGroups.map(({ provider, count }) => (
              <button key={provider.key} type="button" className="provider-stack-card provider-stack-card-button" onClick={() => setIsPickerOpen(true)}>
                <div className="provider-stack-head">
                  <div>
                    <strong>{provider.label}</strong>
                    <p>{provider.key}</p>
                  </div>
                  <span className={`tiny-badge tiny-badge-${provider.category}`}>{count}</span>
                </div>
                <div className="chip-row">
                  {capabilityBadges(provider.capabilities).slice(0, 4).map((item) => (
                    <span className="chip" key={item}>{t(`common.${item}`)}</span>
                  ))}
                </div>
              </button>
            ))}
          </div>
        </Panel>

        <Panel title={t("voicesPage.detailTitle")} description={t("voicesPage.detailDescription")}>
          {selectedVoice ? (
            <div className="job-detail-stack">
              <div className="selected-voice-head selected-voice-head-with-avatar">
                <div className="selected-voice-identity">
                  <VoiceAvatar voice={selectedVoice} size="lg" />
                  <div>
                    <h3>{selectedVoice.display_name}</h3>
                    <p>{selectedVoice.provider_label} · {selectedVoice.language ?? t("common.unknown")} · {selectedVoice.locale ?? "—"}</p>
                  </div>
                </div>
                <span className={`tiny-badge tiny-badge-${selectedVoice.provider_category}`}>{selectedVoice.provider_category}</span>
              </div>
              <p className="muted-copy">{selectedVoice.description ?? t("common.noDescription")}</p>
              <div className="detail-pills">
                <span>{selectedVoice.voice_type ?? t("common.unknown")}</span>
                <span>{selectedVoice.gender ?? t("common.unknown")}</span>
                <span>{formatLocaleLabel(selectedVoice.locale ?? selectedVoice.language, locale)}</span>
              </div>
              <div className="chip-row">
                {capabilityBadges(selectedVoice.capabilities).map((item) => <span className="chip" key={item}>{t(`common.${item}`)}</span>)}
                {selectedVoice.styles.map((style) => <span className="chip" key={style}>{style}</span>)}
              </div>
              {selectedVoice.preview_url ? <audio className="audio-preview" controls src={selectedVoice.preview_url} /> : <p className="muted-copy">{t("voicePicker.noPreviewSupport")}</p>}
              <pre className="code-block">{JSON.stringify(selectedVoice.provider_metadata, null, 2)}</pre>
            </div>
          ) : (
            <p className="muted-copy">{t("voicesPage.noVoice")}</p>
          )}
        </Panel>
      </div>

      <VoicePickerDialog
        open={isPickerOpen}
        providers={providers}
        voices={voices}
        selectedVoice={selectedVoice}
        onClose={() => setIsPickerOpen(false)}
        onSelectVoice={onSelectVoice}
      />
    </>
  );
});
