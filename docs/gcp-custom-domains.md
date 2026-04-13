# GCP custom domains (frontend + API)

## Recommended setup

1. **One canonical frontend URL**  
   Use a single hostname for the SPA (e.g. `https://app.example.com`). Put this in OAuth redirect URIs, `VITE_*` / backend CORS, email links, and documentation.

2. **Apex (`example.com`) → canonical app**  
   Point the apex **A** record at the same global load balancer IP as `app`, but **301-redirect** apex traffic to `https://app.example.com` at the load balancer.

3. **`www` → apex**  
   Point **`www`** **A** at the same IP. By default, **`www.example.com` 301-redirects to `example.com`**, and the apex rule then sends users to `app`. TLS must include `www.example.com` on the managed certificate (handled by Terraform when `redirect_www_to_apex` is true).

4. **API on its own host**  
   Keep the API on `api.example.com` (Cloud Run domain mapping + **CNAME** to `ghs.googlehosted.com`).

5. **TLS**  
   The managed certificate should list every hostname the LB accepts on HTTPS: `app`, apex, and `www` (when using the www→apex redirect).

## Terraform variables (`infra/gcp`)

| Variable | Purpose |
|----------|---------|
| `app_domain` | Canonical frontend hostname (e.g. `app.landgrantiq.com`). |
| `apex_domain` | Root domain for marketing on **Cloud Run** (e.g. `landgrantiq.com`); DNS is Cloud Run anycast A records, not `frontend_ip`. |
| `redirect_apex_to_app` | Default `true`: apex requests get a **301** to `app_domain`. Set `false` only for exceptional cases (both hosts serve the same app — not recommended for production). |
| `redirect_www_to_apex` | Default `true` (when `apex_domain` is set): **`www.<apex>`** gets a **301** to the apex host. |

After changing domains or redirect behavior, run `terraform apply` with the appropriate `-var-file`.

## DNS (typical)

- **`app`** — **A** → frontend static IP (from `terraform output frontend_ip`).
- **`@`** — **A** → same IP (if using apex redirect).
- **`www`** — **A** → same IP (if using www→apex redirect; required for valid HTTPS for `www`).
- **`api`** — **CNAME** → `ghs.googlehosted.com.`

Propagation and managed certificate issuance often take **15–60 minutes** after DNS is correct.

## LandGrant (marketing apex on Cloud Run)

In this repo, **`apex_domain` (e.g. `landgrantiq.com`) is not on the global load balancer.** Marketing uses [Cloud Run domain mapping](https://cloud.google.com/run/docs/mapping-custom-domains) (`landright-marketing`) with its own Google-managed certificate. DNS for **`@`** must follow `terraform output dns_instructions` (typically **four A records** to `216.239.32.21`, `216.239.34.21`, `216.239.36.21`, `216.239.38.21`), **not** `frontend_ip`. **`app`** and **`www`** still use the LB static IP; the LB managed cert covers `app` + `www` only.

**TLS / “Not secure” checks**

1. `dig +short landgrantiq.com A` — should be the **216.239.*** Cloud Run anycast set, **not** the same IP as `app.landgrantiq.com`. If apex matches the LB IP, the browser gets a cert for `app`/`www`, not the apex (name mismatch).
2. `gcloud beta run domain-mappings describe --domain=YOUR_APEX --region=us-central1 --project=YOUR_PROJECT` — confirm `Ready` and compare `resourceRecords` to live DNS.
3. If DNS is correct but the browser still warns, confirm you are not on a **TLS-inspecting proxy** (corporate Zscaler, etc.) without the vendor root CA trusted, or try from another network / device.
