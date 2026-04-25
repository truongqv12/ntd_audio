import { memo } from "react";
import type { VoiceCatalogEntry } from "../types";
import { useI18n } from "../i18n";
import { capabilityBadges } from "../lib/voice";
import { VoiceAvatar } from "./VoiceAvatar";

export const VoiceCard = memo(function VoiceCard({
  voice,
  active,
  onSelect,
}: {
  voice: VoiceCatalogEntry;
  active: boolean;
  onSelect: (voice: VoiceCatalogEntry) => void;
}) {
  const { t } = useI18n();
  return (
    <button
      type="button"
      className={`voice-option-card ${active ? "voice-option-card-active" : ""}`}
      onClick={() => onSelect(voice)}
    >
      <div className="voice-card-stack">
        <VoiceAvatar voice={voice} size="sm" />
        <div className="voice-card-content">
          <div className="voice-card-head">
            <div>
              <strong>{voice.display_name}</strong>
              <p>{voice.provider_label}</p>
            </div>
            <span className={`tiny-badge tiny-badge-${voice.provider_category}`}>
              {voice.provider_category}
            </span>
          </div>
          <div className="voice-card-meta">
            <span>{voice.language ?? t("common.unknown")}</span>
            <span>{voice.locale ?? "—"}</span>
          </div>
          <div className="chip-row">
            {capabilityBadges(voice.capabilities)
              .slice(0, 4)
              .map((item) => (
                <span className="chip" key={item}>
                  {t(`common.${item}`)}
                </span>
              ))}
          </div>
        </div>
      </div>
    </button>
  );
});
