import { memo } from "react";
import type { Job } from "../types";
import { artifactUrl } from "../api";
import { useI18n } from "../i18n";
import { formatDateTime, formatJobDuration } from "../lib/format";
import { StatusBadge } from "./StatusBadge";

export const JobTable = memo(function JobTable({
  jobs,
  onSelect,
}: {
  jobs: Job[];
  onSelect: (job: Job) => void;
}) {
  const { t } = useI18n();
  return (
    <div className="jobs-table-wrap">
      <table className="jobs-table">
        <thead>
          <tr>
            <th>{t("tables.id")}</th>
            <th>{t("tables.project")}</th>
            <th>{t("tables.provider")}</th>
            <th>{t("tables.status")}</th>
            <th>{t("tables.created")}</th>
            <th>{t("tables.duration")}</th>
            <th>{t("tables.actions")}</th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((job) => (
            <tr key={job.id} onClick={() => onSelect(job)}>
              <td>
                <div className="job-id-cell">
                  <strong>{job.id.slice(0, 12)}...</strong>
                  <span>{job.provider_voice_id}</span>
                </div>
              </td>
              <td>{job.project_name ?? job.project_key}</td>
              <td>{job.provider_key}</td>
              <td><StatusBadge value={job.status} /></td>
              <td>{formatDateTime(job.created_at)}</td>
              <td>{formatJobDuration(job.duration_seconds)}</td>
              <td>
                <div className="actions-row" onClick={(event) => event.stopPropagation()}>
                  {job.artifact ? (
                    <a className="icon-button" href={artifactUrl(job.artifact.download_url)} target="_blank" rel="noreferrer">▶</a>
                  ) : (
                    <span className="icon-button icon-button-disabled">▶</span>
                  )}
                  {job.artifact ? (
                    <a className="icon-button" href={artifactUrl(job.artifact.download_url)} download>↓</a>
                  ) : (
                    <span className="icon-button icon-button-disabled">↓</span>
                  )}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
});
