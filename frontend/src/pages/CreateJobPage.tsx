import { memo, useState } from "react";
import type { Project, ProviderParamField, ProviderSummary, VoiceCatalogEntry } from "../types";
import { Panel } from "../components/Panel";
import { VoicePickerDialog } from "../components/VoicePickerDialog";
import { VoiceAvatar } from "../components/VoiceAvatar";
import { VoiceParameterPanel } from "../components/VoiceParameterPanel";
import { useI18n } from "../i18n";
import { capabilityBadges } from "../lib/voice";

export const CreateJobPage = memo(function CreateJobPage({
  projects,
  selectedProject,
  selectedProjectKey,
  onSelectProject,
  providers,
  voices,
  selectedVoice,
  onSelectVoice,
  sourceText,
  onSourceTextChange,
  outputFormat,
  onOutputFormatChange,
  voiceParams,
  voiceParameterSchemas,
  onVoiceParamChange,
  onCreateJob,
  isSubmitting,
  errorMessage,
}: {
  projects: Project[];
  selectedProject: Project | null;
  selectedProjectKey: string;
  onSelectProject: (projectKey: string) => void;
  providers: ProviderSummary[];
  voices: VoiceCatalogEntry[];
  selectedVoice: VoiceCatalogEntry | null;
  onSelectVoice: (voice: VoiceCatalogEntry) => void;
  sourceText: string;
  onSourceTextChange: (value: string) => void;
  outputFormat: string;
  onOutputFormatChange: (value: string) => void;
  voiceParams: Record<string, string | number | boolean>;
  voiceParameterSchemas: Record<string, ProviderParamField[]>;
  onVoiceParamChange: (key: string, value: string | number | boolean) => void;
  onCreateJob: () => void;
  isSubmitting: boolean;
  errorMessage: string | null;
}) {
  const { t } = useI18n();
  const [isPickerOpen, setIsPickerOpen] = useState(false);

  return (
    <>
      <div className="page-grid create-page-grid">
        <Panel title={t("createJob.title")} description={t("createJob.description")}>
          <div className="filter-inline-grid">
            <div className="form-field compact">
              <label>{t("common.project")}</label>
              <select value={selectedProjectKey} onChange={(event) => onSelectProject(event.target.value)}>
                {projects.map((project) => (
                  <option key={project.project_key} value={project.project_key}>
                    {project.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="form-field compact">
              <label>{t("common.output")}</label>
              <select value={outputFormat} onChange={(event) => onOutputFormatChange(event.target.value)}>
                <option value="mp3">mp3</option>
                <option value="wav">wav</option>
              </select>
            </div>
            <div className="form-field compact">
              <label>{t("createJob.defaultProvider")}</label>
              <input value={selectedProject?.default_provider_key ?? t("common.none")} readOnly />
            </div>
          </div>

          <div className="project-context-card">
            <div>
              <strong>{selectedProject?.name ?? t("common.none")}</strong>
              <p>{selectedProject?.description ?? t("createJob.projectContextFallback")}</p>
            </div>
            <div className="detail-pills">
              <span>{selectedProject?.default_provider_key ?? t("projectsPage.noDefaultProvider")}</span>
              <span>{selectedProject?.default_output_format ?? outputFormat}</span>
              <span>
                {selectedProject?.stats.total_jobs ?? 0} {t("createJob.jobsCount")}
              </span>
            </div>
          </div>

          <div className="form-field">
            <label>{t("createJob.scriptLabel")}</label>
            <textarea
              rows={10}
              value={sourceText}
              onChange={(event) => onSourceTextChange(event.target.value)}
            />
            <div className="helper-row">
              <span>
                {sourceText.length} {t("createJob.chars")}
              </span>
              <span>{t("createJob.scriptHint")}</span>
            </div>
          </div>

          <div className="panel-subheader-row">
            <h3 className="section-title">{t("createJob.advancedTitle")}</h3>
            <span className="muted-copy">{t("createJob.advancedDescription")}</span>
          </div>
          <VoiceParameterPanel
            providerKey={selectedVoice?.provider_key}
            schemas={voiceParameterSchemas}
            values={voiceParams}
            onChange={onVoiceParamChange}
          />

          {errorMessage ? <div className="inline-alert">{errorMessage}</div> : null}
          <button
            type="button"
            className="primary-button"
            disabled={!selectedVoice || !sourceText.trim() || isSubmitting}
            onClick={onCreateJob}
          >
            {isSubmitting ? t("createJob.queueing") : t("createJob.queueButton")}
          </button>
        </Panel>

        <Panel
          title={t("createJob.selectedVoiceTitle")}
          description={t("createJob.selectedVoiceDescription")}
        >
          <div className="voice-selection-actions">
            <button type="button" className="ghost-button" onClick={() => setIsPickerOpen(true)}>
              {selectedVoice ? t("common.changeVoice") : t("createJob.pickerButton")}
            </button>
          </div>

          {selectedVoice ? (
            <div className="selected-voice-card selected-voice-card-large">
              <div className="selected-voice-head selected-voice-head-with-avatar">
                <div className="selected-voice-identity">
                  <VoiceAvatar voice={selectedVoice} size="lg" />
                  <div>
                    <h3>{selectedVoice.display_name}</h3>
                    <p>
                      {selectedVoice.provider_label} · {selectedVoice.language ?? t("common.unknown")} ·{" "}
                      {selectedVoice.locale ?? "—"}
                    </p>
                  </div>
                </div>
                <span className={`tiny-badge tiny-badge-${selectedVoice.provider_category}`}>
                  {selectedVoice.provider_category}
                </span>
              </div>
              <p className="muted-copy">{selectedVoice.description ?? t("common.noDescription")}</p>
              <div className="detail-pills">
                <span>{selectedVoice.voice_type ?? t("common.unknown")}</span>
                <span>{selectedVoice.gender ?? t("common.unknown")}</span>
                <span>{selectedVoice.provider_voice_id}</span>
              </div>
              <div className="chip-row">
                {capabilityBadges(selectedVoice.capabilities).map((item) => (
                  <span className="chip" key={item}>
                    {t(`common.${item}`)}
                  </span>
                ))}
                {selectedVoice.styles.map((style) => (
                  <span className="chip" key={style}>
                    {style}
                  </span>
                ))}
              </div>
              {selectedVoice.preview_url ? (
                <audio className="audio-preview" controls src={selectedVoice.preview_url} />
              ) : (
                <p className="muted-copy">{t("voicePicker.noPreviewSupport")}</p>
              )}
            </div>
          ) : (
            <div className="empty-state-box">
              <p className="muted-copy">{t("createJob.voiceRequired")}</p>
            </div>
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
