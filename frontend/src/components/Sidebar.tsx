import { memo } from "react";
import { NAV_ITEMS, NAV_TRANSLATION_KEYS, type AppRoute } from "../config/navigation";
import { useI18n } from "../i18n";

export const Sidebar = memo(function Sidebar({
  route,
  onNavigate,
  projectCount,
  healthyProviders,
  activeJobs,
}: {
  route: AppRoute;
  onNavigate: (route: AppRoute) => void;
  projectCount: number;
  healthyProviders: number;
  activeJobs: number;
}) {
  const { t } = useI18n();

  return (
    <aside className="sidebar">
      <div className="brand-block">
        <div className="brand-logo">⋮⋮</div>
        <div>
          <div className="brand-title-row">
            <strong>{t("brand.title")}</strong>
            <span className="brand-badge">{t("brand.badge")}</span>
          </div>
          <p className="brand-subtitle">{t("brand.subtitle")}</p>
        </div>
      </div>

      <nav className="nav-list">
        {NAV_ITEMS.map((item) => (
          <button
            key={item.key}
            type="button"
            className={`nav-item ${route === item.key ? "nav-item-active" : ""}`}
            onClick={() => onNavigate(item.key)}
          >
            <span className="nav-icon">{item.icon}</span>
            <span>{t(NAV_TRANSLATION_KEYS[item.key])}</span>
          </button>
        ))}
      </nav>

      <div className="sidebar-status panel-surface">
        <h3>{t("sidebar.workspace")}</h3>
        <div className="metric-line"><span>{t("sidebar.providers")}</span><strong>{healthyProviders}</strong></div>
        <div className="metric-line"><span>{t("sidebar.activeJobs")}</span><strong>{activeJobs}</strong></div>
        <div className="metric-line"><span>{t("sidebar.projects")}</span><strong>{projectCount}</strong></div>
      </div>

      <div className="sidebar-footer panel-surface">
        <p>{t("brand.footerTitle")}</p>
        <span>{t("brand.footerSubtitle")}</span>
      </div>
    </aside>
  );
});
