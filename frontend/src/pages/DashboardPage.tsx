import { memo } from "react";
import type { JobEvent, Project } from "../types";
import { Panel } from "../components/Panel";
import { LiveEventList } from "../components/LiveEventList";
import { StatusBadge } from "../components/StatusBadge";
import { useI18n } from "../i18n";

export const DashboardPage = memo(function DashboardPage({
  metrics,
  projects,
  liveEvents,
  onOpenProjects,
  onOpenNotifications,
}: {
  metrics: {
    totalJobs: number;
    activeJobs: number;
    succeededJobs: number;
    failedJobs: number;
    voiceCount: number;
    projectCount: number;
    healthyProviders: number;
    storedResults: number;
  };
  projects: Project[];
  liveEvents: JobEvent[];
  onOpenProjects: () => void;
  onOpenNotifications: () => void;
}) {
  const { t } = useI18n();
  return (
    <div className="page-grid two-up">
      <Panel title={t("dashboard.title")} description={t("dashboard.description")}>
        <div className="stat-grid">
          <div className="stat-card"><span>{t("dashboard.totalJobs")}</span><strong>{metrics.totalJobs}</strong></div>
          <div className="stat-card"><span>{t("dashboard.activeJobs")}</span><strong>{metrics.activeJobs}</strong></div>
          <div className="stat-card"><span>{t("dashboard.storedResults")}</span><strong>{metrics.storedResults}</strong></div>
          <div className="stat-card"><span>{t("dashboard.voices")}</span><strong>{metrics.voiceCount}</strong></div>
          <div className="stat-card"><span>{t("dashboard.projects")}</span><strong>{metrics.projectCount}</strong></div>
          <div className="stat-card"><span>{t("dashboard.failedJobs")}</span><strong>{metrics.failedJobs}</strong></div>
        </div>

        <div className="section-divider" />
        <div className="panel-subheader-row">
          <h3 className="section-title">{t("dashboard.projectBoard")}</h3>
          <button type="button" className="ghost-button compact-button" onClick={onOpenProjects}>{t("dashboard.manageProjects")}</button>
        </div>

        <div className="project-mini-grid">
          {projects.slice(0, 6).map((project) => (
            <button type="button" key={project.project_key} className="project-mini-card" onClick={onOpenProjects}>
              <div className="project-mini-head">
                <strong>{project.name}</strong>
                <StatusBadge value={project.status} />
              </div>
              <p>{project.project_key}</p>
              <div className="mini-metrics">
                <span>{project.stats.total_jobs} {t("projectsPage.jobs")}</span>
                <span>{project.stats.succeeded_jobs} {t("dashboard.ok")}</span>
                <span>{project.stats.failed_jobs} {t("dashboard.fail")}</span>
              </div>
            </button>
          ))}
        </div>
      </Panel>

      <Panel
        title={t("dashboard.liveNotifications")}
        description={t("dashboard.liveDescription")}
        actions={<button type="button" className="ghost-button compact-button" onClick={onOpenNotifications}>{t("dashboard.openNotifications")}</button>}
      >
        <LiveEventList events={liveEvents.slice(-12).reverse()} />
      </Panel>
    </div>
  );
});
