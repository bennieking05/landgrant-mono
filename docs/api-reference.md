# LandRight API Reference

## Authentication

All API requests require an `X-Persona` header indicating the user's role:

- `landowner` - Landowner portal access
- `land_agent` - Land acquisition agent
- `in_house_counsel` - In-house legal counsel
- `outside_counsel` - External legal counsel
- `admin` - System administrator

## Base URL

- Development: `http://localhost:8050`
- Production: `https://api.landright.com`

---

## ROE (Right-of-Entry) Management

### Create ROE

```http
POST /roe
```

**Request:**
```json
{
  "parcel_id": "PARCEL-001",
  "project_id": "PRJ-001",
  "effective_date": "2026-01-01T00:00:00Z",
  "expiry_date": "2026-12-31T00:00:00Z",
  "conditions": "Survey activities only",
  "permitted_activities": ["survey", "environmental"],
  "access_windows": {"weekdays": "8am-5pm"}
}
```

**Response:**
```json
{
  "roe_id": "ROE-abc123",
  "status": "draft",
  "created_at": "2026-01-01T00:00:00Z"
}
```

### List ROEs

```http
GET /roe?parcel_id={parcel_id}
```

### Get ROE Details

```http
GET /roe/{roe_id}
```

### Update ROE

```http
PUT /roe/{roe_id}
```

### Record Field Event

```http
POST /roe/{roe_id}/field-events
```

**Request:**
```json
{
  "event_type": "check_in",
  "personnel_name": "John Agent",
  "latitude": 30.2672,
  "longitude": -97.7431,
  "notes": "Arrived at site"
}
```

### List Expiring ROEs

```http
GET /roe/expiring?project_id={project_id}&days_threshold=30
```

---

## Offers & Payment Ledger

### Create Offer

```http
POST /offers
```

**Request:**
```json
{
  "parcel_id": "PARCEL-001",
  "project_id": "PRJ-001",
  "offer_type": "initial",
  "amount": 150000,
  "terms": {"description": "Standard acquisition terms"}
}
```

### List Offers

```http
GET /offers?parcel_id={parcel_id}
```

### Submit Counteroffer

```http
POST /offers/{offer_id}/counter
```

**Request:**
```json
{
  "counter_amount": 175000,
  "counter_terms": {"description": "Landowner counter"}
}
```

### Get Payment Ledger

```http
GET /payment-ledger/{parcel_id}
```

### Update Payment Ledger

```http
PUT /payment-ledger/{parcel_id}
```

---

## Litigation Cases

### Create Case

```http
POST /litigation
```

**Request:**
```json
{
  "parcel_id": "PARCEL-001",
  "project_id": "PRJ-001",
  "court": "District Court of Travis County",
  "court_county": "Travis",
  "cause_number": "2026-CV-12345",
  "is_quick_take": false
}
```

### List Cases

```http
GET /litigation?project_id={project_id}&status={status}
```

### Update Case

```http
PUT /litigation/{case_id}
```

### Get Status History

```http
GET /litigation/{case_id}/history
```

### Get Analytics

```http
GET /litigation/analytics/summary?project_id={project_id}
```

---

## E-Sign Integration

### Initiate Signing

```http
POST /esign/initiate
```

**Request:**
```json
{
  "document_id": "DOC-001",
  "parcel_id": "PARCEL-001",
  "project_id": "PRJ-001",
  "signers": [
    {"email": "owner@example.com", "name": "John Owner", "role": "signer"}
  ],
  "subject": "Document Ready for Signature",
  "return_url": "https://portal.landright.com/signed"
}
```

### Get Envelope Status

```http
GET /esign/status/{envelope_id}
```

### Webhook Handler

```http
POST /esign/webhook
```

### Void Envelope

```http
POST /esign/void/{envelope_id}
```

### List Envelopes

```http
GET /esign/list?project_id={project_id}
```

---

## Communications

### Send Single Message

```http
POST /communications/send
```

### Send Batch

```http
POST /communications/batch
```

**Request:**
```json
{
  "project_id": "PRJ-001",
  "template_id": "offer_letter",
  "channel": "email",
  "recipients": [
    {"parcel_id": "PARCEL-001", "email": "owner1@example.com"},
    {"parcel_id": "PARCEL-002", "email": "owner2@example.com"}
  ],
  "variables": {"agent_name": "John Agent"}
}
```

### Get Batch Status

```http
GET /communications/batch/{batch_id}
```

---

## Portal (Landowner)

### Send Invite

```http
POST /portal/invites
```

### Verify Magic Link

```http
POST /portal/verify
```

**Request:**
```json
{
  "token": "abc123..."
}
```

**Response:**
```json
{
  "status": "verified",
  "invite_id": "INV-001",
  "session_expires_at": "2026-01-02T00:00:00Z",
  "parcel_id": "PARCEL-001"
}
```

### Get Session Info

```http
GET /portal/session
```

### Submit Decision

```http
POST /portal/decision
```

---

## Chat/Messaging

### Create Thread

```http
POST /chat/threads
```

### List Threads

```http
GET /chat/threads?parcel_id={parcel_id}
```

### Send Message

```http
POST /chat/threads/{thread_id}/messages
```

### Mark Read

```http
POST /chat/threads/{thread_id}/read-all
```

---

## Title & Curative

### Upload Title Instrument

```http
POST /title (multipart/form-data)
```

### List Curative Items

```http
GET /title/curative?parcel_id={parcel_id}
```

### Create Curative Item

```http
POST /title/curative
```

### Update Curative Item

```http
PUT /title/curative/{item_id}
```

---

## Health Checks

```http
GET /health/live
GET /health/invite
GET /health/esign
```

---

## Error Codes

| Code | Description |
|------|-------------|
| 400 | Bad Request - Invalid input |
| 401 | Unauthorized - Invalid/missing authentication |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource doesn't exist |
| 410 | Gone - Resource expired |
| 413 | Payload Too Large - File too big |
| 429 | Too Many Requests - Rate limited |
| 500 | Internal Server Error |

## Rate Limits

- Portal verify: 5 attempts per invite per 10 minutes
- Batch communications: 1000 recipients per request
- API requests: 1000 requests per minute per IP
