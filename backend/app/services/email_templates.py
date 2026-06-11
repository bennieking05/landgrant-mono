"""Branded HTML email templates (UX-10).

Inline-styled, table-based HTML for broad email-client support. These wrap the
existing plain-text notification bodies so we always send a multipart email
(text/plain + text/html). Kept dependency-free (no Jinja) on purpose.
"""

from __future__ import annotations

from html import escape
from typing import Any

NAVY = "#14294A"
COPPER = "#B26A2C"
INK = "#0F172A"
MUTED = "#64748B"
BORDER = "#E2E8F0"

DISCLAIMER = (
    "This message is part of an eminent-domain negotiation record. It is not "
    "legal advice. You have the right to consult your own attorney at any time."
)


def _button(href: str, label: str) -> str:
    return (
        f'<table role="presentation" cellpadding="0" cellspacing="0" '
        f'style="margin:24px 0;"><tr><td '
        f'style="border-radius:6px;background:{COPPER};">'
        f'<a href="{escape(href, quote=True)}" '
        f'style="display:inline-block;padding:12px 24px;font-family:Arial,Helvetica,sans-serif;'
        f'font-size:15px;font-weight:600;color:#ffffff;text-decoration:none;border-radius:6px;">'
        f"{escape(label)}</a></td></tr></table>"
    )


def _layout(title: str, inner_html: str) -> str:
    """Wrap content in the branded LandGrantIQ shell."""
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{escape(title)}</title>
</head>
<body style="margin:0;padding:0;background:#F1F5F9;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#F1F5F9;padding:24px 0;">
    <tr><td align="center">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
             style="max-width:560px;background:#ffffff;border:1px solid {BORDER};border-radius:12px;overflow:hidden;">
        <tr>
          <td style="background:{NAVY};padding:20px 28px;">
            <span style="font-family:Arial,Helvetica,sans-serif;font-size:20px;font-weight:700;color:#ffffff;letter-spacing:-0.3px;">
              LandGrant<span style="color:{COPPER};">IQ</span>
            </span>
          </td>
        </tr>
        <tr>
          <td style="padding:28px;font-family:Arial,Helvetica,sans-serif;font-size:15px;line-height:1.55;color:{INK};">
            {inner_html}
          </td>
        </tr>
        <tr>
          <td style="padding:18px 28px;border-top:1px solid {BORDER};font-family:Arial,Helvetica,sans-serif;font-size:12px;line-height:1.5;color:{MUTED};">
            <p style="margin:0 0 8px;">{escape(DISCLAIMER)}</p>
            <p style="margin:0;">&copy; LandGrantIQ &middot;
              <a href="https://landgrantiq.com/terms" style="color:{MUTED};">Terms</a> &middot;
              <a href="https://landgrantiq.com/privacy" style="color:{MUTED};">Privacy</a> &middot;
              <a href="mailto:help@landgrantiq.com" style="color:{MUTED};">Support</a>
            </p>
            <p style="margin:12px 0 0;font-size:11px;line-height:1.45;color:#94a3b8;">
              LandRight AI, Inc. &middot; 1234 Commerce Drive, Austin, TX 78701 USA.
              <a href="mailto:privacy@landgrantiq.com?subject=Unsubscribe" style="color:#94a3b8;">Unsubscribe</a>
              from marketing and non-transactional reminders (CAN-SPAM).
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def render_email_html(
    template_id: str,
    variables: dict[str, Any],
    subject: str | None,
    text_body: str,
) -> str:
    """Return a branded HTML body for the given notification template."""
    title = subject or "LandGrantIQ"

    if template_id == "portal_invite":
        invite_link = str(variables.get("invite_link", ""))
        project_id = escape(str(variables.get("project_id", "")))
        parcel_id = escape(str(variables.get("parcel_id", "")))
        inner = (
            f'<h1 style="margin:0 0 12px;font-size:20px;color:{NAVY};">You\'re invited to review your property</h1>'
            f'<p style="margin:0 0 12px;">A company wants to use part of your land for a public '
            f"project. Use the secure link below to review the details and respond. Take your time "
            f"&mdash; nothing happens until you decide.</p>"
            f'<p style="margin:0;color:{MUTED};font-size:13px;">Project {project_id}'
            + (f" &middot; Parcel {parcel_id}" if parcel_id else "")
            + "</p>"
        )
        if invite_link:
            inner += _button(invite_link, "Review my property")
        return _layout(title, inner)

    if template_id == "decision_confirmation":
        selection = escape(str(variables.get("selection", "")))
        parcel_id = escape(str(variables.get("parcel_id", "")))
        inner = (
            f'<h1 style="margin:0 0 12px;font-size:20px;color:{NAVY};">We received your response</h1>'
            f'<p style="margin:0 0 12px;">Thank you. We recorded your decision '
            f"<strong>{selection}</strong>"
            + (f" for parcel {parcel_id}" if parcel_id else "")
            + ".</p>"
            '<p style="margin:0;">Your response goes to your agent and attorney for review. We will '
            "contact you with the next steps.</p>"
        )
        return _layout(title, inner)

    if template_id == "deadline_reminder":
        title_line = escape(str(variables.get("title", "Upcoming deadline")))
        due = escape(str(variables.get("due_at", "")))
        project = escape(str(variables.get("project_id", "")))
        inner = (
            f'<h1 style="margin:0 0 12px;font-size:20px;color:{NAVY};">Deadline reminder</h1>'
            f'<p style="margin:0 0 12px;"><strong>{title_line}</strong></p>'
            f'<p style="margin:0 0 12px;color:{MUTED};font-size:14px;">Due: {due}</p>'
        )
        if project:
            inner += f'<p style="margin:0;color:{MUTED};font-size:13px;">Project {project}</p>'
        return _layout(title, inner)

    # Generic fallback: render the plain-text body as paragraphs.
    paragraphs = (
        "".join(
            f'<p style="margin:0 0 12px;">{escape(line)}</p>'
            for line in text_body.splitlines()
            if line.strip()
        )
        or f'<p style="margin:0;">{escape(text_body)}</p>'
    )
    return _layout(title, paragraphs)
