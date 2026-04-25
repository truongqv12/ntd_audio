import { memo } from "react";
import { useI18n } from "../i18n";

export const StatusBadge = memo(function StatusBadge({ value }: { value: string }) {
  const { t } = useI18n();
  const className =
    value === "succeeded" || value === "active" || value === "online"
      ? "status-tag-succeeded"
      : value === "failed" || value === "archived" || value === "offline"
        ? "status-tag-failed"
        : "status-tag-queued";

  const labelMap: Record<string, string> = {
    active: t("common.active"),
    archived: t("common.archived"),
    online: t("common.online"),
    offline: t("common.offline"),
    queued: t("jobsPage.queued"),
    running: t("jobsPage.running"),
    succeeded: t("jobsPage.succeeded"),
    failed: t("jobsPage.failed"),
  };

  return <span className={`status-tag ${className}`}>{labelMap[value] ?? value}</span>;
});
