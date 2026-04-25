import { memo, useEffect, useMemo, useState } from "react";
import type {
  HealthResponse,
  Project,
  ProviderCredential,
  ProviderSummary,
  SettingsOverview,
} from "../types";
import { Panel } from "../components/Panel";
import { useI18n } from "../i18n";
import { updateMergeDefaults, updateProviderCredentials } from "../api";

function cloneCredentialFields(credential: ProviderCredential) {
  return Object.fromEntries(
    Object.entries(credential.fields).map(([key, field]) => [key, field.value ?? ""]),
  );
}

export const SettingsPage = memo(function SettingsPage({
  health,
  currentProject,
  projects,
  providers,
  settingsOverview,
  onUpdateProject,
  onRefresh,
}: {
  health: HealthResponse | null;
  currentProject: Project | null;
  projects: Project[];
  providers: ProviderSummary[];
  settingsOverview: SettingsOverview | null;
  onUpdateProject: (projectKey: string, payload: Record<string, unknown>) => Promise<Project | null>;
  onRefresh: (refreshCatalog?: boolean) => Promise<void>;
}) {
  const { t } = useI18n();
  const [credentialDrafts, setCredentialDrafts] = useState<Record<string, Record<string, unknown>>>({});
  const [mergeDraft, setMergeDraft] = useState<Record<string, unknown>>({});
  const [projectDraft, setProjectDraft] = useState<Record<string, unknown>>({});
  const [savingProvider, setSavingProvider] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const credentials = settingsOverview?.provider_credentials ?? [];
  const schemas = settingsOverview?.voice_parameter_schemas ?? {};
  const providerMap = useMemo(
    () => new Map(providers.map((provider) => [provider.key, provider])),
    [providers],
  );

  useEffect(() => {
    const next: Record<string, Record<string, unknown>> = {};
    for (const credential of credentials) next[credential.provider_key] = cloneCredentialFields(credential);
    setCredentialDrafts(next);
  }, [settingsOverview]);

  useEffect(() => {
    setMergeDraft(settingsOverview?.merge_defaults ?? {});
  }, [settingsOverview]);

  useEffect(() => {
    if (!currentProject) return;
    const projectSettings = currentProject.settings ?? {};
    setProjectDraft({
      default_provider_key: currentProject.default_provider_key ?? "",
      default_output_format: currentProject.default_output_format ?? "mp3",
      merge_silence_ms: Number(
        projectSettings.merge_silence_ms ?? settingsOverview?.merge_defaults?.merge_silence_ms ?? 150,
      ),
      merge_output_format: String(
        projectSettings.merge_output_format ?? settingsOverview?.merge_defaults?.merge_output_format ?? "wav",
      ),
    });
  }, [currentProject, settingsOverview]);

  async function saveCredential(providerKey: string) {
    try {
      setSavingProvider(providerKey);
      setError(null);
      await updateProviderCredentials(providerKey, credentialDrafts[providerKey] ?? {});
      setMessage("Provider settings saved. Refreshing catalog and health checks.");
      await onRefresh(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save provider settings");
    } finally {
      setSavingProvider(null);
    }
  }

  async function saveMergeDefaults() {
    try {
      setError(null);
      await updateMergeDefaults(mergeDraft);
      setMessage("Global merge defaults saved.");
      await onRefresh(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save merge defaults");
    }
  }

  async function saveProjectDefaults() {
    if (!currentProject) return;
    try {
      setError(null);
      const settings = {
        ...(currentProject.settings ?? {}),
        merge_silence_ms: Number(projectDraft.merge_silence_ms ?? 150),
        merge_output_format: String(projectDraft.merge_output_format ?? "wav"),
      };
      await onUpdateProject(currentProject.project_key, {
        default_provider_key: projectDraft.default_provider_key || null,
        default_output_format: projectDraft.default_output_format || "mp3",
        settings,
      });
      setMessage("Project defaults saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save project defaults");
    }
  }

  return (
    <div className="settings-page-grid">
      <Panel
        title="Provider credentials"
        description="Set API keys and runtime endpoints used by cloud and self-hosted providers. Environment variables still take precedence when present."
      >
        {message ? <div className="success-banner">{message}</div> : null}
        {error ? <div className="inline-alert">{error}</div> : null}
        <div className="provider-settings-grid">
          {credentials.map((credential) => {
            const draft = credentialDrafts[credential.provider_key] ?? {};
            const provider = providerMap.get(credential.provider_key);
            return (
              <div className="provider-settings-card" key={credential.provider_key}>
                <div className="provider-stack-head">
                  <div>
                    <strong>{credential.label}</strong>
                    <p>
                      {credential.provider_key} · {credential.category}
                    </p>
                  </div>
                  <span
                    className={`status-tag ${credential.configured ? "status-tag-succeeded" : "status-tag-queued"}`}
                  >
                    {credential.configured ? "configured" : "not configured"}
                  </span>
                </div>
                {provider ? <p className="muted-copy compact-copy">{provider.reason}</p> : null}
                <div className="settings-field-grid">
                  {Object.entries(credential.fields).map(([fieldKey, field]) => (
                    <label className="form-field compact" key={fieldKey}>
                      <span>{field.label}</span>
                      <input
                        type={field.secret ? "password" : "text"}
                        value={String(draft[fieldKey] ?? "")}
                        placeholder={field.env_present ? `Using ${field.env}` : field.label}
                        onChange={(event) =>
                          setCredentialDrafts((current) => ({
                            ...current,
                            [credential.provider_key]: {
                              ...(current[credential.provider_key] ?? {}),
                              [fieldKey]: event.target.value,
                            },
                          }))
                        }
                      />
                      {field.env_present ? (
                        <small className="muted-copy">ENV override active: {field.env}</small>
                      ) : null}
                    </label>
                  ))}
                </div>
                <button
                  type="button"
                  className="ghost-button compact-button"
                  onClick={() => void saveCredential(credential.provider_key)}
                  disabled={savingProvider === credential.provider_key}
                >
                  {savingProvider === credential.provider_key ? "Saving..." : "Save provider"}
                </button>
              </div>
            );
          })}
        </div>
      </Panel>

      <Panel
        title="Project defaults"
        description="Defaults applied to Create Job and Script Editor rows unless a row overrides them."
      >
        <div className="filter-inline-grid">
          <div className="form-field compact">
            <label>{t("settingsPage.currentProject")}</label>
            <input value={currentProject?.name ?? t("common.none")} readOnly />
          </div>
          <div className="form-field compact">
            <label>Default provider</label>
            <select
              value={String(projectDraft.default_provider_key ?? "")}
              onChange={(event) =>
                setProjectDraft((current) => ({ ...current, default_provider_key: event.target.value }))
              }
            >
              <option value="">None</option>
              {providers.map((provider) => (
                <option key={provider.key} value={provider.key}>
                  {provider.label}
                </option>
              ))}
            </select>
          </div>
          <div className="form-field compact">
            <label>Default output</label>
            <select
              value={String(projectDraft.default_output_format ?? "mp3")}
              onChange={(event) =>
                setProjectDraft((current) => ({ ...current, default_output_format: event.target.value }))
              }
            >
              <option value="mp3">mp3</option>
              <option value="wav">wav</option>
            </select>
          </div>
        </div>
        <div className="filter-inline-grid">
          <div className="form-field compact">
            <label>Merge silence ms</label>
            <input
              type="number"
              min={0}
              value={Number(projectDraft.merge_silence_ms ?? 150)}
              onChange={(event) =>
                setProjectDraft((current) => ({ ...current, merge_silence_ms: Number(event.target.value) }))
              }
            />
          </div>
          <div className="form-field compact">
            <label>Merge output</label>
            <select
              value={String(projectDraft.merge_output_format ?? "wav")}
              onChange={(event) =>
                setProjectDraft((current) => ({ ...current, merge_output_format: event.target.value }))
              }
            >
              <option value="wav">wav</option>
              <option value="mp3">mp3</option>
            </select>
          </div>
        </div>
        <button
          className="primary-button compact-primary"
          type="button"
          onClick={() => void saveProjectDefaults()}
          disabled={!currentProject}
        >
          Save project defaults
        </button>
      </Panel>

      <Panel
        title="Global merge defaults"
        description="Fallback values used when a project has not customized merge behavior."
      >
        <div className="filter-inline-grid">
          <div className="form-field compact">
            <label>Merge silence ms</label>
            <input
              type="number"
              min={0}
              value={Number(mergeDraft.merge_silence_ms ?? 150)}
              onChange={(event) =>
                setMergeDraft((current) => ({ ...current, merge_silence_ms: Number(event.target.value) }))
              }
            />
          </div>
          <div className="form-field compact">
            <label>Merge output format</label>
            <select
              value={String(mergeDraft.merge_output_format ?? "wav")}
              onChange={(event) =>
                setMergeDraft((current) => ({ ...current, merge_output_format: event.target.value }))
              }
            >
              <option value="wav">wav</option>
              <option value="mp3">mp3</option>
            </select>
          </div>
          <div className="form-field compact">
            <label>Normalize loudness</label>
            <select
              value={String(mergeDraft.normalize_loudness ?? false)}
              onChange={(event) =>
                setMergeDraft((current) => ({
                  ...current,
                  normalize_loudness: event.target.value === "true",
                }))
              }
            >
              <option value="false">Off</option>
              <option value="true">On</option>
            </select>
          </div>
        </div>
        <button
          className="ghost-button compact-button"
          type="button"
          onClick={() => void saveMergeDefaults()}
        >
          Save global merge defaults
        </button>
      </Panel>

      <Panel
        title="Voice parameter schemas"
        description="Parameter forms are generated from provider schemas so every engine can expose different controls without hard-coding UI per voice."
      >
        <div className="schema-list">
          {Object.entries(schemas).map(([providerKey, fields]) => (
            <details key={providerKey} className="schema-details">
              <summary>
                {providerKey} · {fields.length} fields
              </summary>
              <div className="settings-stack">
                {fields.map((field) => (
                  <div className="settings-item" key={field.key}>
                    <span>{field.label}</span>
                    <strong>
                      {field.key} · {field.kind}
                      {field.unit ? ` · ${field.unit}` : ""}
                    </strong>
                  </div>
                ))}
              </div>
            </details>
          ))}
        </div>
      </Panel>

      <Panel title={t("settingsPage.systemTitle")} description={t("settingsPage.systemDescription")}>
        <pre className="code-block">{JSON.stringify({ health, projects: projects.length }, null, 2)}</pre>
      </Panel>
    </div>
  );
});
