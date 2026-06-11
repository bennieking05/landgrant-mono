import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import en from "./locales/en.json";
import es from "./locales/es.json";

const STORAGE_KEY = "landgrant.locale";

export function getStoredLocale(): string {
  try {
    return window.localStorage.getItem(STORAGE_KEY) || "en";
  } catch {
    return "en";
  }
}

export function setStoredLocale(lng: string) {
  try {
    window.localStorage.setItem(STORAGE_KEY, lng);
  } catch {
    /* ignore */
  }
}

void i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    es: { translation: es },
  },
  lng: typeof window !== "undefined" ? getStoredLocale() : "en",
  fallbackLng: "en",
  interpolation: { escapeValue: false },
});

export default i18n;
