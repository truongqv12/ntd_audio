import { memo } from "react";
import type { ProviderSummary } from "../types";
import { Panel } from "../components/Panel";
import { capabilityBadges } from "../lib/voice";
import { StatusBadge } from "../components/StatusBadge";
import { useI18n } from "../i18n";

export const ProvidersPage = memo(function ProvidersPage({ providers }: { providers: ProviderSummary[] }) {
  const { t } = useI18n();
  return (
    <Panel title={t("providersPage.title")} description={t("providersPage.description")}>
      <div className="provider-stack-grid provider-stack-grid-wide">
        {providers.map((provider) => (
          <div key={provider.key} className="provider-stack-card">
            <div className="provider-stack-head">
              <div>
                <strong>{provider.label}</strong>
                <p>{provider.key}</p>
              </div>
              <StatusBadge value={provider.reachable ? "online" : "offline"} />
            </div>
            <p className="muted-copy compact-copy">{provider.reason}</p>
            <div className="chip-row">
              {capabilityBadges(provider.capabilities).map((item) => <span className="chip" key={item}>{t(`common.${item}`)}</span>)}
            </div>
          </div>
        ))}
      </div>
    </Panel>
  );
});
