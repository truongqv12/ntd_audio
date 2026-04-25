import { memo } from "react";
import type { JobEvent } from "../types";
import { useI18n } from "../i18n";
import { formatClockTime } from "../lib/format";

export const LiveEventList = memo(function LiveEventList({
  events,
  compact = false,
}: {
  events: JobEvent[];
  compact?: boolean;
}) {
  const { t } = useI18n();

  return (
    <div className={`event-stream ${compact ? "compact-stream" : ""}`.trim()}>
      {events.length > 0 ? (
        events.map((event, index) => (
          <div className="event-row" key={`${event.created_at}-${index}`}>
            <span className="event-time">{formatClockTime(event.created_at)}</span>
            <span className={`event-type event-type-${event.event_type}`}>{event.event_type}</span>
            <div>
              <p>{event.message}</p>
            </div>
          </div>
        ))
      ) : (
        <p className="muted-copy">{t("notificationsPage.noEvents")}</p>
      )}
    </div>
  );
});
