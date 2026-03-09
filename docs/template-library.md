# Template Library

## Documents Covered
- Initial Offer Letter (IOL)
- Final Offer Letter (FOL)
- Easement agreements
- Offers + notices (per 50-state survey)
- Affidavits of service
- Early possession / Department of Transportation packets
- Commissioner filings
- Engagement letters

## Structure
- Each template is stored as Markdown (`.md`) and optionally DOCX for mail merges.
- Metadata lives in adjacent JSON describing:
  - `id`, `version`, `jurisdiction`, `locale`
  - Variables + validation rules
  - Redaction flags
  - `privilege`: `privileged | non_privileged`
  - `classifications`: `[binder, communication, filing]`

Example `templates/library/fol/meta.json`:
```json
{
  "id": "fol",
  "version": "1.0.0",
  "locale": "en-US",
  "jurisdiction": "TX",
  "variables": {
    "owner_name": {"type": "string", "required": true},
    "parcel_id": {"type": "string", "required": true},
    "offer_amount": {"type": "number", "required": true, "currency": "USD"}
  },
  "redactions": ["owner_contact"],
  "privilege": "non_privileged"
}
```

## Approval Flow
1. Draft created by agent or AI suggestion.
2. In-house counsel reviews redlines, attaches citations, and marks `approved`.
3. Backend renders PDF (WeasyPrint) + DOCX, computes SHA-256, stores in `Document` table + Cloud Storage.
4. Immutable version is referenced by cases, rules engine entries, and binder exports.

## Localization
- Strings live in `templates/i18n/*.json` keyed by `en-US`, `es-US` etc.
- Markdown supports conditional blocks via Liquid-style tags (e.g., `{% if jurisdiction == 'TX' %}`).
