export type AppRoute =
  | "dashboard"
  | "create"
  | "jobs"
  | "script"
  | "projects"
  | "voices"
  | "library"
  | "notifications"
  | "providers"
  | "monitor"
  | "voice-lab"
  | "settings";

export type NavItem = {
  key: AppRoute;
  icon: string;
  group: "core" | "admin";
};

export const NAV_ITEMS: NavItem[] = [
  { key: "dashboard", icon: "◫", group: "core" },
  { key: "create", icon: "+", group: "core" },
  { key: "jobs", icon: "≡", group: "core" },
  { key: "script", icon: "▤", group: "core" },
  { key: "library", icon: "♫", group: "core" },
  { key: "notifications", icon: "◉", group: "core" },
  { key: "projects", icon: "⌂", group: "admin" },
  { key: "voices", icon: "◎", group: "admin" },
  { key: "providers", icon: "◌", group: "admin" },
  { key: "monitor", icon: "▣", group: "admin" },
  { key: "voice-lab", icon: "✦", group: "admin" },
  { key: "settings", icon: "⚙", group: "admin" },
];

export const ROUTE_TRANSLATION_KEYS: Record<AppRoute, string> = {
  dashboard: "routes.dashboard",
  create: "routes.create",
  jobs: "routes.jobs",
  script: "routes.script",
  projects: "routes.projects",
  voices: "routes.voices",
  library: "routes.library",
  notifications: "routes.notifications",
  providers: "routes.providers",
  monitor: "routes.monitor",
  "voice-lab": "routes.voiceLab",
  settings: "routes.settings",
};

export const NAV_TRANSLATION_KEYS: Record<AppRoute, string> = {
  dashboard: "nav.dashboard",
  create: "nav.create",
  jobs: "nav.jobs",
  script: "nav.script",
  projects: "nav.projects",
  voices: "nav.voices",
  library: "nav.library",
  notifications: "nav.notifications",
  providers: "nav.providers",
  monitor: "nav.monitor",
  "voice-lab": "nav.voiceLab",
  settings: "nav.settings",
};
