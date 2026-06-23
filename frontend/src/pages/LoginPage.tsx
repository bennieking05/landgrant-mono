import { useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/context/AuthContext";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { Alert, Button, Card, CardBody, Field, Input, Logo } from "@/components/ui";

export function LoginPage() {
  const { t } = useTranslation();
  useDocumentTitle("Sign in");
  const { isAuthenticated, login } = useAuth();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (isAuthenticated) {
    const dest = (location.state as { from?: string } | null)?.from ?? "/";
    return <Navigate to={dest} replace />;
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await login(email.trim(), password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-4 py-12">
      <div className="mb-6 flex flex-col items-center gap-3 text-center">
        <Logo size={32} />
        <div>
          <h1 className="text-h1 text-slate-900">{t("pages.login.title")}</h1>
          <p className="mt-1 text-small text-slate-600">{t("pages.login.subtitle")}</p>
        </div>
      </div>

      <Card>
        <CardBody>
          <form onSubmit={onSubmit} className="space-y-4" noValidate>
            {error ? (
              <Alert variant="danger" title={t("pages.login.errorTitle")}>
                {error}
              </Alert>
            ) : null}
            <Field label={t("pages.login.email")}>
              {(props) => (
                <Input
                  {...props}
                  type="email"
                  autoComplete="username"
                  autoFocus
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              )}
            </Field>
            <Field label={t("pages.login.password")}>
              {(props) => (
                <Input
                  {...props}
                  type="password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              )}
            </Field>
            <Button type="submit" loading={busy} disabled={busy} className="w-full">
              {busy ? t("pages.login.signingIn") : t("pages.login.signIn")}
            </Button>
          </form>
        </CardBody>
      </Card>

      <p className="mt-4 text-center text-caption text-slate-500">
        {t("pages.login.demo")} <code className="rounded bg-slate-100 px-1">agent@example.com</code> /{" "}
        <code className="rounded bg-slate-100 px-1">devpass123</code>
      </p>
    </div>
  );
}
