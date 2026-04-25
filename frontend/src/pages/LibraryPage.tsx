import { memo, useDeferredValue, useMemo, useState } from "react";
import type { Job, Project } from "../types";
import { Panel } from "../components/Panel";
import { artifactUrl } from "../api";
import { useI18n } from "../i18n";
import { formatDateTime, formatJobDuration } from "../lib/format";

export const LibraryPage = memo(function LibraryPage({
  jobs,
  projects,
}: {
  jobs: Job[];
  projects: Project[];
}) {
  const { t } = useI18n();
  const [projectFilter, setProjectFilter] = useState("all");
  const [search, setSearch] = useState("");
  const deferredSearch = useDeferredValue(search);

  const storedResults = useMemo(() => {
    const query = deferredSearch.trim().toLowerCase();
    return jobs.filter((job) => {
      if (!job.artifact) return false;
      const matchesProject = projectFilter === "all" || job.project_key === projectFilter;
      const matchesSearch =
        !query ||
        [job.project_name ?? job.project_key, job.provider_key, job.provider_voice_id, job.source_text]
          .join(" ")
          .toLowerCase()
          .includes(query);
      return matchesProject && matchesSearch;
    });
  }, [deferredSearch, jobs, projectFilter]);

  return (
    <Panel title={t("library.title")} description={t("library.description")}>
      <div className="filter-inline-grid">
        <div className="form-field compact">
          <label>{t("library.searchResult")}</label>
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder={t("library.placeholder")}
          />
        </div>
        <div className="form-field compact">
          <label>{t("library.project")}</label>
          <select value={projectFilter} onChange={(event) => setProjectFilter(event.target.value)}>
            <option value="all">{t("common.all")}</option>
            {projects.map((project) => (
              <option key={project.project_key} value={project.project_key}>
                {project.name}
              </option>
            ))}
          </select>
        </div>
      </div>
      <div className="library-grid">
        {storedResults.map((job) => (
          <article key={job.id} className="library-card">
            <div className="project-mini-head">
              <div>
                <strong>{job.project_name ?? job.project_key}</strong>
                <p>
                  {job.provider_key} · {job.provider_voice_id}
                </p>
              </div>
              <span className="tiny-badge tiny-badge-cloud">{job.output_format}</span>
            </div>
            <p className="muted-copy line-clamp-3">{job.source_text}</p>
            <div className="mini-metrics">
              <span>{formatDateTime(job.finished_at ?? job.created_at)}</span>
              <span>{formatJobDuration(job.duration_seconds)}</span>
            </div>
            <div className="actions-row">
              <a
                className="ghost-button compact-button"
                href={artifactUrl(job.artifact!.download_url)}
                target="_blank"
                rel="noreferrer"
              >
                {t("common.open")}
              </a>
              <a className="primary-link" href={artifactUrl(job.artifact!.download_url)} download>
                {t("common.download")}
              </a>
            </div>
          </article>
        ))}
        {storedResults.length === 0 ? <p className="muted-copy">{t("library.noArtifacts")}</p> : null}
      </div>
    </Panel>
  );
});
