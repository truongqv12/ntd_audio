import { memo, useEffect, useState } from "react";
import { fetchMonitorLogs, fetchMonitorLogSources, fetchMonitorStatus } from "../api";
import type { LogSource, LogTail, MonitorStatus } from "../types";
import { Panel } from "../components/Panel";
import { StatusBadge } from "../components/StatusBadge";
import { useI18n } from "../i18n";
import { capabilityBadges } from "../lib/voice";

export const MonitorPage = memo(function MonitorPage() {
  const { t } = useI18n();
  const [status, setStatus] = useState<MonitorStatus | null>(null);
  const [sources, setSources] = useState<LogSource[]>([]);
  const [selectedSource, setSelectedSource] = useState("api");
  const [logs, setLogs] = useState<LogTail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let ignore = false;
    const load = async () => {
      try {
        const [statusData, sourceData] = await Promise.all([fetchMonitorStatus(), fetchMonitorLogSources()]);
        if (ignore) return;
        setStatus(statusData);
        setSources(sourceData);
        setError(null);
      } catch (nextError) {
        if (!ignore) setError(nextError instanceof Error ? nextError.message : "Unable to load monitor data");
      }
    };
    load();
    const timer = window.setInterval(load, 10000);
    return () => {
      ignore = true;
      window.clearInterval(timer);
    };
  }, []);

  useEffect(() => {
    let ignore = false;
    const loadLogs = async () => {
      try {
        const logData = await fetchMonitorLogs(selectedSource, 220);
        if (!ignore) setLogs(logData);
      } catch (nextError) {
        if (!ignore) setError(nextError instanceof Error ? nextError.message : "Unable to load logs");
      }
    };
    loadLogs();
    const timer = window.setInterval(loadLogs, 5000);
    return () => {
      ignore = true;
      window.clearInterval(timer);
    };
  }, [selectedSource]);

  return (
    <div className="page-grid monitor-grid">
      <Panel title={t("monitorPage.title")} description={t("monitorPage.description")}>
        {error ? <div className="alert-banner">{error}</div> : null}
        <div className="stat-grid">
          <div className="stat-card"><span>{t("monitorPage.totalJobs")}</span><strong>{status?.queue.total_jobs ?? 0}</strong></div>
          <div className="stat-card"><span>{t("monitorPage.queuedJobs")}</span><strong>{status?.queue.queued_jobs ?? 0}</strong></div>
          <div className="stat-card"><span>{t("monitorPage.runningJobs")}</span><strong>{status?.queue.running_jobs ?? 0}</strong></div>
          <div className="stat-card"><span>{t("monitorPage.failedJobs")}</span><strong>{status?.queue.failed_jobs ?? 0}</strong></div>
          <div className="stat-card"><span>{t("monitorPage.uptime")}</span><strong>{Math.round(status?.uptime_seconds ?? 0)}s</strong></div>
        </div>
        <div className="section-divider" />
        <div className="provider-stack-grid provider-stack-grid-wide">
          {status?.providers.map((provider) => (
            <div key={provider.key} className="provider-stack-card">
              <div className="provider-stack-head">
                <div>
                  <strong>{provider.label}</strong>
                  <p>{provider.service_target ?? provider.key}</p>
                </div>
                <StatusBadge value={provider.reachable ? "online" : "offline"} />
              </div>
              <div className="mini-metrics">
                <span>{provider.voice_count} voices</span>
                <span>{provider.active_jobs} active</span>
                <span>{provider.latency_ms ?? 0} ms</span>
              </div>
              <p className="muted-copy compact-copy">{provider.reason}</p>
              <div className="chip-row">
                {capabilityBadges(provider.capabilities).map((item) => <span className="chip" key={item}>{t(`common.${item}`)}</span>)}
              </div>
            </div>
          ))}
        </div>
      </Panel>

      <Panel title={t("monitorPage.logsTitle")} description={t("monitorPage.logsDescription")}>
        <div className="monitor-toolbar">
          <div className="log-source-pills">
            {sources.map((source) => (
              <button
                key={source.key}
                type="button"
                className={`tab-pill ${selectedSource === source.key ? "tab-pill-active" : ""}`}
                onClick={() => setSelectedSource(source.key)}
                disabled={!source.available}
                title={source.description}
              >
                {source.label}
              </button>
            ))}
          </div>
          <span className="muted-copy">{logs?.source_label ?? selectedSource}</span>
        </div>
        <div className="code-block log-viewer">
          {logs?.lines.length ? logs.lines.map((line, index) => <div key={`${index}-${line.slice(0, 20)}`}>{line}</div>) : <div>{t("monitorPage.noLogs")}</div>}
        </div>
      </Panel>

      <Panel title={t("monitorPage.guidanceTitle")} description={t("monitorPage.guidanceDescription")}>
        <ul className="guidance-list">
          {status?.guidance.map((item, index) => <li key={index}>{item}</li>)}
        </ul>
      </Panel>
    </div>
  );
});
