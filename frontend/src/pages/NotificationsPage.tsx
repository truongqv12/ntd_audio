import { memo, useEffect, useMemo, useState } from "react";
import type { JobEvent } from "../types";
import { Panel } from "../components/Panel";
import { LiveEventList } from "../components/LiveEventList";
import { useI18n } from "../i18n";

export const NotificationsPage = memo(function NotificationsPage({
  liveEvents,
  onMarkSeen,
}: {
  liveEvents: JobEvent[];
  onMarkSeen: () => void;
}) {
  const { t } = useI18n();
  const [severityFilter, setSeverityFilter] = useState<"all" | "failed" | "completed" | "started">("all");

  useEffect(() => {
    onMarkSeen();
  }, [onMarkSeen]);

  const visibleEvents = useMemo(() => {
    if (severityFilter === "all") return [...liveEvents].reverse();
    return [...liveEvents].reverse().filter((event) => event.event_type === severityFilter);
  }, [liveEvents, severityFilter]);

  const labels = {
    all: t("notificationsPage.all"),
    failed: t("notificationsPage.failed"),
    completed: t("notificationsPage.completed"),
    started: t("notificationsPage.started"),
  } as const;

  return (
    <Panel title={t("notificationsPage.title")} description={t("notificationsPage.description")}>
      <div className="tab-row">
        {(["all", "failed", "completed", "started"] as const).map((item) => (
          <button
            key={item}
            type="button"
            className={`tab-pill ${severityFilter === item ? "tab-pill-active" : ""}`}
            onClick={() => setSeverityFilter(item)}
          >
            {labels[item]}
          </button>
        ))}
      </div>
      <LiveEventList events={visibleEvents} />
    </Panel>
  );
});
