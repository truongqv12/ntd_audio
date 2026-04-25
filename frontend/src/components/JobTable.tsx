import { memo } from "react";
import type { Job } from "../types";
import { artifactUrl } from "../api";
import { useI18n } from "../i18n";
import { formatDateTime, formatJobDuration } from "../lib/format";
import { StatusBadge } from "./StatusBadge";

const CANCELABLE = new Set(["queued", "running"]);
const RETRYABLE = new Set(["failed", "canceled"]);

export const JobTable = memo(function JobTable({
  jobs,
  onSelect,
  onCancel,
  onRetry,
}: {
  jobs: Job[];
  onSelect: (job: Job) => void;
  onCancel?: (jobId: string) => void;
  onRetry?: (jobId: string) => void;
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
              <td>
                <StatusBadge value={job.status} />
              </td>
              <td>{formatDateTime(job.created_at)}</td>
              <td>{formatJobDuration(job.duration_seconds)}</td>
              <td>
                <div className="actions-row" onClick={(event) => event.stopPropagation()}>
                  {job.artifact ? (
                    <a
                      className="icon-button"
                      href={artifactUrl(job.artifact.download_url)}
                      target="_blank"
                      rel="noreferrer"
                      title={t("tables.play")}
                    >
                      ▶
                    </a>
                  ) : (
                    <span className="icon-button icon-button-disabled" title={t("tables.play")}>
                      ▶
                    </span>
                  )}
                  {job.artifact ? (
                    <a
                      className="icon-button"
                      href={artifactUrl(job.artifact.download_url)}
                      download
                      title={t("tables.download")}
                    >
                      ↓
                    </a>
                  ) : (
                    <span className="icon-button icon-button-disabled" title={t("tables.download")}>
                      ↓
                    </span>
                  )}
                  {onCancel && CANCELABLE.has(job.status) ? (
                    <button
                      type="button"
                      className="icon-button"
                      onClick={() => onCancel(job.id)}
                      title={t("tables.cancel")}
                    >
                      ✕
                    </button>
                  ) : null}
                  {onRetry && RETRYABLE.has(job.status) ? (
                    <button
                      type="button"
                      className="icon-button"
                      onClick={() => onRetry(job.id)}
                      title={t("tables.retry")}
                    >
                      ↻
                    </button>
                  ) : null}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
});
