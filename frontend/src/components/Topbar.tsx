import { memo } from "react";
import { ROUTE_TRANSLATION_KEYS, type AppRoute } from "../config/navigation";
import type { Project } from "../types";
import { useI18n } from "../i18n";

export const Topbar = memo(function Topbar({
  route,
  currentProject,
  unreadNotifications,
  totalVoices,
  onNavigate,
}: {
  route: AppRoute;
  currentProject: Project | null;
  unreadNotifications: number;
  totalVoices: number;
  onNavigate: (route: AppRoute) => void;
}) {
  const { locale, setLocale, t } = useI18n();

  return (
    <header className="topbar panel-surface">
      <div>
        <p className="eyebrow">{t("topbar.eyebrow")}</p>
        <h1>{t(ROUTE_TRANSLATION_KEYS[route])}</h1>
      </div>
      <div className="topbar-actions">
        <div className="top-status-pill">
          <span className="status-dot status-good" />
          <span>{t("topbar.currentProject")}</span>
          <strong>{currentProject?.name ?? t("common.none")}</strong>
        </div>
        <div className="top-status-pill">
          <span className="status-dot status-good" />
          <span>{t("topbar.totalVoices")}</span>
          <strong>{totalVoices}</strong>
        </div>
        <button type="button" className="top-status-pill clickable-pill" onClick={() => onNavigate("notifications")}>
          <span className="status-dot status-good" />
          <span>{t("topbar.notifications")}</span>
          <strong>{unreadNotifications}</strong>
        </button>
        <div className="language-switcher" aria-label={t("topbar.language")}> 
          <button type="button" className={`lang-button ${locale === "vi" ? "lang-button-active" : ""}`} onClick={() => setLocale("vi")}>VI</button>
          <button type="button" className={`lang-button ${locale === "en" ? "lang-button-active" : ""}`} onClick={() => setLocale("en")}>EN</button>
        </div>
      </div>
    </header>
  );
});
