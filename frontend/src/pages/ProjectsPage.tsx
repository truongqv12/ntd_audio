import { memo, useState } from "react";
import type { Project, ProviderSummary } from "../types";
import { Panel } from "../components/Panel";
import { StatusBadge } from "../components/StatusBadge";
import { useI18n } from "../i18n";

export const ProjectsPage = memo(function ProjectsPage({
  projects,
  providers,
  selectedProjectKey,
  onSelectProject,
  onCreateProject,
  onToggleArchive,
}: {
  projects: Project[];
  providers: ProviderSummary[];
  selectedProjectKey: string;
  onSelectProject: (projectKey: string) => void;
  onCreateProject: (payload: {
    project_key: string;
    name: string;
    description?: string;
    default_provider_key?: string;
    default_output_format?: string;
    tags?: string[];
  }) => Promise<Project | null>;
  onToggleArchive: (project: Project) => Promise<Project | null>;
}) {
  const { t } = useI18n();
  const [form, setForm] = useState({
    project_key: "",
    name: "",
    description: "",
    default_provider_key: "",
    default_output_format: "mp3",
    tags: "",
  });

  return (
    <div className="page-grid two-up">
      <Panel title={t("projectsPage.title")} description={t("projectsPage.description")}>
        <div className="project-grid">
          {projects.map((project) => (
            <div className={`project-card ${selectedProjectKey === project.project_key ? "project-card-active" : ""}`} key={project.project_key}>
              <div className="project-mini-head">
                <div>
                  <strong>{project.name}</strong>
                  <p>{project.project_key}</p>
                </div>
                <StatusBadge value={project.status} />
              </div>
              <p className="muted-copy">{project.description ?? t("projectsPage.noDescription")}</p>
              <div className="mini-metrics">
                <span>{project.stats.total_jobs} {t("projectsPage.jobs")}</span>
                <span>{project.stats.succeeded_jobs} {t("projectsPage.ok")}</span>
                <span>{project.stats.failed_jobs} {t("projectsPage.fail")}</span>
              </div>
              <div className="detail-pills">
                <span>{project.default_provider_key ?? t("projectsPage.noDefaultProvider")}</span>
                <span>{project.default_output_format}</span>
                {project.tags.map((tag) => <span key={tag}>{tag}</span>)}
              </div>
              <div className="actions-row">
                <button type="button" className="ghost-button compact-button" onClick={() => onSelectProject(project.project_key)}>{t("projectsPage.use")}</button>
                <button type="button" className="ghost-button compact-button" onClick={() => void onToggleArchive(project)}>
                  {project.status === "archived" ? t("projectsPage.activate") : t("projectsPage.archive")}
                </button>
              </div>
            </div>
          ))}
        </div>
      </Panel>

      <Panel title={t("projectsPage.createTitle")} description={t("projectsPage.createDescription")}>
        <div className="form-field"><label>{t("projectsPage.projectKey")}</label><input value={form.project_key} onChange={(e) => setForm((current) => ({ ...current, project_key: e.target.value }))} placeholder={t("projectsPage.placeholderKey")} /></div>
        <div className="form-field"><label>{t("projectsPage.name")}</label><input value={form.name} onChange={(e) => setForm((current) => ({ ...current, name: e.target.value }))} placeholder={t("projectsPage.placeholderName")} /></div>
        <div className="form-field"><label>{t("projectsPage.descriptionLabel")}</label><textarea rows={4} value={form.description} onChange={(e) => setForm((current) => ({ ...current, description: e.target.value }))} /></div>
        <div className="filter-inline-grid">
          <div className="form-field compact">
            <label>{t("projectsPage.defaultProvider")}</label>
            <select value={form.default_provider_key} onChange={(e) => setForm((current) => ({ ...current, default_provider_key: e.target.value }))}>
              <option value="">{t("common.none")}</option>
              {providers.map((provider) => (
                <option key={provider.key} value={provider.key}>{provider.label}</option>
              ))}
            </select>
          </div>
          <div className="form-field compact">
            <label>{t("projectsPage.defaultFormat")}</label>
            <select value={form.default_output_format} onChange={(e) => setForm((current) => ({ ...current, default_output_format: e.target.value }))}>
              <option value="mp3">mp3</option>
              <option value="wav">wav</option>
            </select>
          </div>
        </div>
        <div className="form-field"><label>{t("projectsPage.tags")}</label><input value={form.tags} onChange={(e) => setForm((current) => ({ ...current, tags: e.target.value }))} placeholder={t("projectsPage.placeholderTags")} /></div>
        <button
          type="button"
          className="primary-button"
          disabled={!form.project_key || !form.name}
          onClick={() => void onCreateProject({
            project_key: form.project_key,
            name: form.name,
            description: form.description,
            default_provider_key: form.default_provider_key || undefined,
            default_output_format: form.default_output_format,
            tags: form.tags.split(",").map((item) => item.trim()).filter(Boolean),
          }).then((created) => {
            if (created) {
              setForm({ project_key: "", name: "", description: "", default_provider_key: "", default_output_format: "mp3", tags: "" });
            }
          })}
        >
          {t("projectsPage.createProject")}
        </button>
      </Panel>
    </div>
  );
});
