/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE?: string;
  readonly VITE_AUTH_TOKEN?: string;
  readonly VITE_SENTRY_DSN?: string;
  readonly VITE_APP_VERSION?: string;
  readonly VITE_BUILD_SHA?: string;
  readonly VITE_MAPBOX_TOKEN?: string;
  readonly VITE_MAP_ENGINE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
