import { useCallback, useEffect, useState } from "react";
import type { AppRoute } from "../config/navigation";

const VALID_ROUTES: AppRoute[] = [
  "dashboard",
  "create",
  "jobs",
  "script",
  "projects",
  "voices",
  "library",
  "notifications",
  "providers",
  "monitor",
  "voice-lab",
  "settings",
];

function getRouteFromHash(): AppRoute {
  const raw = window.location.hash.replace(/^#\/?/, "");
  return VALID_ROUTES.includes(raw as AppRoute) ? (raw as AppRoute) : "dashboard";
}

export function useHashRoute() {
  const [route, setRouteState] = useState<AppRoute>(() => getRouteFromHash());

  useEffect(() => {
    const onHashChange = () => setRouteState(getRouteFromHash());
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  const setRoute = useCallback((nextRoute: AppRoute) => {
    window.location.hash = `/${nextRoute}`;
    setRouteState(nextRoute);
  }, []);

  return { route, setRoute };
}
