import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import * as Sentry from "@sentry/react";
import { I18nextProvider } from "react-i18next";

import { App } from "@/App";
import "@/index.css";
import i18n from "@/i18n";
import { ToastProvider, TooltipProvider } from "@/components/ui";
import { ErrorBoundary } from "@/components/ErrorBoundary";

if (import.meta.env.VITE_SENTRY_DSN) {
  Sentry.init({
    dsn: import.meta.env.VITE_SENTRY_DSN,
    environment: import.meta.env.MODE,
    tracesSampleRate: 0.1,
  });
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <I18nextProvider i18n={i18n}>
        <ToastProvider>
          <TooltipProvider>
            <BrowserRouter>
              <App />
            </BrowserRouter>
          </TooltipProvider>
        </ToastProvider>
      </I18nextProvider>
    </ErrorBoundary>
  </React.StrictMode>,
);
