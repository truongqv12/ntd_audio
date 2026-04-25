import { createContext, memo, type ReactNode, useContext, useEffect, useMemo, useState } from "react";

import enMessages from "./i18n/en.json";
import viMessages from "./i18n/vi.json";

export type Locale = "en" | "vi";

type TranslationValue = string | TranslationTree;
interface TranslationTree {
  [key: string]: TranslationValue;
}

type I18nContextValue = {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: string, vars?: Record<string, string | number>) => string;
};

const STORAGE_KEY = "voiceforge.locale";

const messages: Record<Locale, TranslationTree> = {
  en: enMessages as TranslationTree,
  vi: viMessages as TranslationTree,
};

const I18nContext = createContext<I18nContextValue | null>(null);

function resolveMessage(locale: Locale, key: string): string {
  const parts = key.split(".");
  let current: TranslationValue | undefined = messages[locale];
  for (const part of parts) {
    if (!current || typeof current === "string") return key;
    current = current[part];
  }
  return typeof current === "string" ? current : key;
}

function interpolate(template: string, vars?: Record<string, string | number>) {
  if (!vars) return template;
  return template.replace(/\{(\w+)\}/g, (_, token: string) => String(vars[token] ?? `{${token}}`));
}

export const I18nProvider = memo(function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(() => {
    const stored = typeof window !== "undefined" ? window.localStorage.getItem(STORAGE_KEY) : null;
    return stored === "en" || stored === "vi" ? stored : "vi";
  });

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, locale);
    document.documentElement.lang = locale;
  }, [locale]);

  const value = useMemo<I18nContextValue>(
    () => ({
      locale,
      setLocale: setLocaleState,
      t: (key, vars) => interpolate(resolveMessage(locale, key), vars),
    }),
    [locale],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
});

export function useI18n() {
  const context = useContext(I18nContext);
  if (!context) throw new Error("useI18n must be used inside I18nProvider");
  return context;
}
