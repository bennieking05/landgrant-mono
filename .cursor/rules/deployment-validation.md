# Deployment & Live Service Validation Rule

## NON-NEGOTIABLE POLICY

After any infrastructure, backend, frontend, or marketing deployment change, you MUST validate live services before marking work complete.

---

## Service Inventory

| Service          | URL                                              | Expected |
|------------------|--------------------------------------------------|----------|
| Frontend SPA     | `https://app.landgrantiq.com`                    | HTTP 200, HTML with `<div id="root">`, JS/CSS assets load |
| API              | `https://api.landgrantiq.com/health/live`        | HTTP 200, `{"status":"ok"}` |
| API invite       | `https://api.landgrantiq.com/health/invite`      | HTTP 200 |
| API e-sign       | `https://api.landgrantiq.com/health/esign`       | HTTP 200 |
| AI health        | `https://api.landgrantiq.com/ai/health`          | HTTP 200, `gemini_enabled: true` |
| Copilot health   | `https://api.landgrantiq.com/copilot/health`     | HTTP 200 |
| Predictions      | `https://api.landgrantiq.com/predictions/health` | HTTP 200 |
| RAG health       | `https://api.landgrantiq.com/rag/health`         | HTTP 200 |
| OpenAPI spec     | `https://api.landgrantiq.com/openapi.json`       | HTTP 200, valid JSON |
| Marketing        | Cloud Run URL for `landgrant-marketing`           | HTTP 200, `<title>LandGrant` |
| Apex domain      | `https://landgrantiq.com`                        | HTTP 200 (requires correct DNS) |

---

## Required Validation Steps

### 1. Health Endpoint Sweep

```bash
for ep in /health/live /health/invite /health/esign /ai/health /copilot/health /predictions/health /rag/health; do
  echo "$ep: $(curl -sS -o /dev/null -w '%{http_code}' https://api.landgrantiq.com$ep)"
done
```

### 2. Frontend Asset Check

```bash
curl -sS https://app.landgrantiq.com | grep -o 'src="[^"]*\.js"'
curl -sS https://app.landgrantiq.com | grep -o 'href="[^"]*\.css"'
# Then verify each asset returns HTTP 200
```

### 3. CORS Verification

```bash
curl -sS -X OPTIONS \
  -H "Origin: https://app.landgrantiq.com" \
  -H "Access-Control-Request-Method: GET" \
  -D - -o /dev/null https://api.landgrantiq.com/health/live
# Must include: access-control-allow-origin header
```

### 4. RBAC Smoke Test

Dev (X-Persona header still honoured):

```bash
# Unauthenticated → 401 (missing header + no JWT)
curl -sS -w '%{http_code}' https://api.landgrantiq.com/parcels
# Invalid persona → 401
curl -sS -w '%{http_code}' -H "X-Persona: bogus" https://api.landgrantiq.com/parcels
# Valid persona → 200
curl -sS -w '%{http_code}' -H "X-Persona: land_agent" https://api.landgrantiq.com/parcels
```

Prod (JWT-derived persona; `X-Persona` is ignored per Phase 3.3):

```bash
TOKEN=$(gcloud secrets versions access latest --secret landgrant-smoke-jwt --project clearpath-490715)
curl -sS -w '%{http_code}' -H "Authorization: Bearer $TOKEN" https://api.landgrantiq.com/parcels
# Missing token → 401
curl -sS -w '%{http_code}' https://api.landgrantiq.com/parcels
```

### 4a. Audit Chain Verification

```bash
curl -sS -H "Authorization: Bearer $TOKEN" \
  https://api.landgrantiq.com/audit/chain/verify
# Expect {"verified": true, ...}; page on-call if verified == false
```

### 4b. AI-First Gates

```bash
# Citation gate rejects outputs without anchors (422).
curl -sS -w '%{http_code}' -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"document_id":"probe","ai_output":{"claims":[{"text":"t","citation":null}]}}' \
  https://api.landgrantiq.com/qa/check
# Approvals require pending state.
curl -sS -w '%{http_code}' -H "Authorization: Bearer $TOKEN" \
  https://api.landgrantiq.com/approvals?status=pending
```

### 4c. Rate Limiter

```bash
# Default limit is 120/min; this loop must eventually return 429.
for i in $(seq 1 200); do
  curl -sS -o /dev/null -w '%{http_code}\n' \
    -H "Authorization: Bearer $TOKEN" \
    https://api.landgrantiq.com/health/live
done | sort | uniq -c
```

### 5. SSL Certificate Check

```bash
echo | openssl s_client -connect app.landgrantiq.com:443 -servername app.landgrantiq.com 2>/dev/null \
  | openssl x509 -noout -subject -ext subjectAltName
```

### 6. DNS Verification

```bash
dig landgrantiq.com A +short
dig app.landgrantiq.com A +short
dig api.landgrantiq.com CNAME +short
```

---

## Expected DNS Configuration

| Record               | Type  | Value                                              |
|----------------------|-------|----------------------------------------------------|
| `app.landgrantiq.com`| A     | `34.102.158.32` (frontend LB static IP)            |
| `api.landgrantiq.com`| CNAME | `ghs.googlehosted.com.` (Cloud Run domain mapping) |
| `landgrantiq.com`    | A     | `216.239.32.21` + `.34.21` + `.36.21` + `.38.21`   |
| `www.landgrantiq.com`| A     | `34.102.158.32` (redirects 301 → apex)             |

---

## Personas for Testing

Valid `X-Persona` header values: `land_agent`, `in_house_counsel`, `outside_counsel`, `landowner`, `firm_admin`, `admin`

---

## Cloud Run Services

List and verify all services are running:

```bash
gcloud run services list --project clearpath-490715 --region us-central1
```

Expected services: `landgrant-api`, `landgrant-marketing`, `landgrant-worker`

---

## If Validation Fails

1. Record the failing endpoint, HTTP status, and response body
2. Check Cloud Run logs: `gcloud run services logs read <service> --project clearpath-490715 --region us-central1`
3. Check Terraform state: `cd infra/gcp && terraform plan -var-file=environments/dev.tfvars`
4. Do NOT mark deployment as complete until all checks pass
