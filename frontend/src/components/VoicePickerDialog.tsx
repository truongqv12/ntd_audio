import { memo, useDeferredValue, useEffect, useMemo, useState } from "react";
import { fetchVoiceSearch } from "../api";
import type { ProviderSummary, VoiceCatalogEntry } from "../types";
import { useI18n } from "../i18n";
import { capabilityBadges, formatLocaleLabel, getVoiceLocalesForProvider } from "../lib/voice";
import { VoiceAvatar } from "./VoiceAvatar";

type VoicePickerDialogProps = {
  open: boolean;
  providers: ProviderSummary[];
  voices: VoiceCatalogEntry[];
  selectedVoice: VoiceCatalogEntry | null;
  onClose: () => void;
  onSelectVoice: (voice: VoiceCatalogEntry) => void;
};

export const VoicePickerDialog = memo(function VoicePickerDialog({
  open,
  providers,
  voices,
  selectedVoice,
  onClose,
  onSelectVoice,
}: VoicePickerDialogProps) {
  const { locale, t } = useI18n();
  const [providerKey, setProviderKey] = useState<string>(selectedVoice?.provider_key ?? providers[0]?.key ?? "");
  const [localeFilter, setLocaleFilter] = useState<string>(selectedVoice?.locale ?? "all");
  const [search, setSearch] = useState("");
  const [remoteVoices, setRemoteVoices] = useState<VoiceCatalogEntry[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const deferredSearch = useDeferredValue(search);

  useEffect(() => {
    if (!open) return;
    setProviderKey(selectedVoice?.provider_key ?? providers[0]?.key ?? "");
    setLocaleFilter(selectedVoice?.locale ?? "all");
    setSearch("");
  }, [open, providers, selectedVoice]);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  const localeOptions = useMemo(() => getVoiceLocalesForProvider(voices, providerKey), [providerKey, voices]);

  useEffect(() => {
    if (!open || !providerKey) return;
    let ignore = false;
    const run = async () => {
      try {
        setIsSearching(true);
        const response = await fetchVoiceSearch({
          q: deferredSearch.trim() || undefined,
          provider_key: providerKey,
          locale: localeFilter !== "all" ? localeFilter : undefined,
          limit: 80,
        });
        if (!ignore) setRemoteVoices(response.items);
      } catch {
        if (!ignore) {
          const fallback = voices.filter((voice) => {
            const matchesProvider = voice.provider_key === providerKey;
            const matchesLocale = localeFilter === "all" || (voice.locale ?? voice.language ?? "unknown") === localeFilter;
            const query = deferredSearch.trim().toLowerCase();
            const haystack = [
              voice.display_name,
              voice.provider_label,
              voice.language ?? "",
              voice.locale ?? "",
              voice.description ?? "",
              ...voice.tags,
              ...voice.styles,
            ]
              .join(" ")
              .toLowerCase();
            const matchesSearch = !query || haystack.includes(query);
            return matchesProvider && matchesLocale && matchesSearch;
          });
          setRemoteVoices(fallback);
        }
      } finally {
        if (!ignore) setIsSearching(false);
      }
    };
    run();
    return () => {
      ignore = true;
    };
  }, [deferredSearch, localeFilter, open, providerKey, voices]);

  const filteredVoices = remoteVoices;

  const previewVoice = useMemo(() => {
    if (!selectedVoice || selectedVoice.provider_key !== providerKey) return filteredVoices[0] ?? null;
    return selectedVoice;
  }, [filteredVoices, providerKey, selectedVoice]);

  if (!open) return null;

  return (
    <div className="voice-dialog-overlay" role="dialog" aria-modal="true" aria-label={t("voicePicker.title")}>
      <div className="voice-dialog-shell panel-surface">
        <div className="voice-dialog-header">
          <div>
            <p className="eyebrow">{t("common.chooseVoice")}</p>
            <h2>{t("voicePicker.title")}</h2>
            <p>{t("voicePicker.description")}</p>
          </div>
          <button type="button" className="ghost-button compact-button" onClick={onClose}>
            {t("voicePicker.close")}
          </button>
        </div>

        <div className="voice-dialog-grid">
          <aside className="voice-engine-column">
            <h3>{t("voicePicker.engineList")}</h3>
            <div className="voice-engine-list">
              {providers.map((provider) => (
                <button
                  key={provider.key}
                  type="button"
                  className={`voice-engine-card ${provider.key === providerKey ? "voice-engine-card-active" : ""}`}
                  onClick={() => {
                    setProviderKey(provider.key);
                    setLocaleFilter("all");
                  }}
                >
                  <div>
                    <strong>{provider.label}</strong>
                    <p>{provider.key}</p>
                  </div>
                  <div className="chip-row">
                    {capabilityBadges(provider.capabilities).slice(0, 3).map((item) => (
                      <span className="chip" key={item}>{t(`common.${item}`)}</span>
                    ))}
                  </div>
                </button>
              ))}
            </div>
          </aside>

          <section className="voice-browser-column">
            <div className="voice-browser-toolbar">
              <div>
                <h3>{t("voicePicker.localeList")}</h3>
                <p className="muted-copy">{t("common.countryFilterHint")}</p>
              </div>
              <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder={t("common.search")} />
            </div>
            <div className="locale-chip-row">
              <button
                type="button"
                className={`locale-chip ${localeFilter === "all" ? "locale-chip-active" : ""}`}
                onClick={() => setLocaleFilter("all")}
              >
                {t("voicePicker.localeAll")}
              </button>
              {localeOptions.map((item) => (
                <button
                  key={item}
                  type="button"
                  className={`locale-chip ${localeFilter === item ? "locale-chip-active" : ""}`}
                  onClick={() => setLocaleFilter(item)}
                >
                  {formatLocaleLabel(item, locale)}
                </button>
              ))}
            </div>

            <div className="voice-dialog-list">
              {isSearching ? <p className="muted-copy">Searching voices…</p> : null}
              {!isSearching && filteredVoices.length > 0 ? (
                filteredVoices.map((voice) => {
                  const active = selectedVoice?.provider_key === voice.provider_key && selectedVoice?.provider_voice_id === voice.provider_voice_id;
                  return (
                    <button
                      key={`${voice.provider_key}:${voice.provider_voice_id}`}
                      type="button"
                      className={`voice-dialog-card ${active ? "voice-dialog-card-active" : ""}`}
                      onClick={() => onSelectVoice(voice)}
                    >
                      <VoiceAvatar voice={voice} size="md" />
                      <div className="voice-dialog-card-body">
                        <div className="voice-dialog-card-head">
                          <div>
                            <strong>{voice.display_name}</strong>
                            <p>{voice.language ?? t("common.unknown")} · {voice.locale ?? "—"}</p>
                          </div>
                          <span className={`tiny-badge tiny-badge-${voice.provider_category}`}>{voice.provider_category}</span>
                        </div>
                        <p className="muted-copy line-clamp-2">{voice.description ?? t("common.noDescription")}</p>
                        <div className="chip-row">
                          {capabilityBadges(voice.capabilities).slice(0, 4).map((item) => (
                            <span className="chip" key={item}>{t(`common.${item}`)}</span>
                          ))}
                        </div>
                      </div>
                    </button>
                  );
                })
              ) : null}
              {!isSearching && filteredVoices.length === 0 ? <p className="muted-copy">{t("voicePicker.noVoices")}</p> : null}
            </div>
          </section>

          <aside className="voice-preview-column">
            <h3>{t("voicePicker.selectedVoice")}</h3>
            {previewVoice ? (
              <div className="voice-preview-card">
                <div className="voice-preview-head">
                  <VoiceAvatar voice={previewVoice} size="lg" />
                  <div>
                    <strong>{previewVoice.display_name}</strong>
                    <p>{previewVoice.provider_label}</p>
                    <p className="muted-copy">{formatLocaleLabel(previewVoice.locale ?? previewVoice.language, locale)}</p>
                  </div>
                </div>
                <div className="detail-pills">
                  <span>{previewVoice.voice_type ?? t("common.unknown")}</span>
                  <span>{previewVoice.gender ?? t("common.unknown")}</span>
                </div>
                <div className="chip-row">
                  {previewVoice.styles.map((style) => (
                    <span className="chip" key={style}>{style}</span>
                  ))}
                  {previewVoice.tags.map((tag) => (
                    <span className="chip" key={tag}>{tag}</span>
                  ))}
                </div>
                {previewVoice.preview_url ? (
                  <div className="voice-preview-player">
                    <span className="muted-copy">{t("voicePicker.previewAvailable")}</span>
                    <audio controls src={previewVoice.preview_url} />
                  </div>
                ) : (
                  <div className="voice-preview-player voice-preview-player-empty">
                    <span className="muted-copy">{t("voicePicker.previewUnavailable")}</span>
                    <p className="muted-copy">{t("voicePicker.noPreviewSupport")}</p>
                  </div>
                )}
                <button type="button" className="primary-button" onClick={onClose}>
                  {t("voicePicker.applyVoice")}
                </button>
              </div>
            ) : (
              <p className="muted-copy">{t("common.noVoicesFound")}</p>
            )}
          </aside>
        </div>
      </div>
    </div>
  );
});
