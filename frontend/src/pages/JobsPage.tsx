import { memo, useMemo, useState } from "react";
import type { Job } from "../types";
import { Panel } from "../components/Panel";
import { JobTable } from "../components/JobTable";
import { InlineAudioPlayer } from "../components/InlineAudioPlayer";
import { LiveEventList } from "../components/LiveEventList";
import { useI18n } from "../i18n";

const STATUS_TABS = ["all", "queued", "running", "succeeded", "failed"] as const;

export const JobsPage = memo(function JobsPage({
  jobs,
  selectedJob,
  onSelectJob,
  onCancelJob,
  onRetryJob,
}: {
  jobs: Job[];
  selectedJob: Job | null;
  onSelectJob: (job: Job) => void;
  onCancelJob?: (jobId: string) => void;
  onRetryJob?: (jobId: string) => void;
}) {
  const { t } = useI18n();
  const [statusFilter, setStatusFilter] = useState<(typeof STATUS_TABS)[number]>("all");

  const visibleJobs = useMemo(() => {
    if (statusFilter === "all") return jobs;
    return jobs.filter((job) => job.status === statusFilter);
  }, [jobs, statusFilter]);

  const statusLabelMap: Record<(typeof STATUS_TABS)[number], string> = {
    all: t("jobsPage.all"),
    queued: t("jobsPage.queued"),
    running: t("jobsPage.running"),
    succeeded: t("jobsPage.succeeded"),
    failed: t("jobsPage.failed"),
  };

  return (
    <div className="page-grid two-up wide-right">
      <Panel
        title={t("jobsPage.title")}
        description={t("jobsPage.description")}
        actions={
          <div className="tab-row">
            {STATUS_TABS.map((tab) => (
              <button
                key={tab}
                type="button"
                className={`tab-pill ${statusFilter === tab ? "tab-pill-active" : ""}`}
                onClick={() => setStatusFilter(tab)}
              >
                {statusLabelMap[tab]}
              </button>
            ))}
          </div>
        }
      >
        <JobTable jobs={visibleJobs} onSelect={onSelectJob} onCancel={onCancelJob} onRetry={onRetryJob} />
      </Panel>

      <Panel title={t("jobsPage.detailTitle")} description={t("jobsPage.detailDescription")}>
        {selectedJob ? (
          <div className="job-detail-stack">
            <div className="detail-pills">
              <span>{selectedJob.project_name ?? selectedJob.project_key}</span>
              <span>{selectedJob.provider_key}</span>
              <span>{selectedJob.provider_voice_id}</span>
              <span>{selectedJob.output_format}</span>
            </div>
            <p className="muted-copy">{selectedJob.source_text}</p>
            {selectedJob.artifact ? (
              <InlineAudioPlayer
                downloadUrl={selectedJob.artifact.download_url}
                mimeType={selectedJob.artifact.mime_type}
              />
            ) : null}
            <pre className="code-block">{JSON.stringify(selectedJob.normalized_params, null, 2)}</pre>
            <LiveEventList events={selectedJob.events} compact />
          </div>
        ) : (
          <p className="muted-copy">{t("jobsPage.selectJob")}</p>
        )}
      </Panel>
    </div>
  );
});
