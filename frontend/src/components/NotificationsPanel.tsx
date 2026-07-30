import { useState } from "react";
import { previewNotification, type NotificationPreviewResponse } from "@/lib/api";
import { Button, Field, Input, Select, Alert, Badge, useToast } from "@/components/ui";

type Props = {
  projectId: string;
  parcelId: string;
};

const TEMPLATE_OPTIONS = [
  { id: "portal_invite", label: "Portal invite" },
  { id: "decision_confirmation", label: "Decision confirmation" },
  { id: "offer_letter", label: "Offer letter" },
  { id: "deadline_reminder", label: "Deadline reminder" },
];

const CHANNEL_OPTIONS = [
  { id: "email", label: "Email" },
  { id: "sms", label: "SMS" },
];

export function NotificationsPanel({ projectId, parcelId }: Props) {
  const toast = useToast();
  const [templateId, setTemplateId] = useState("portal_invite");
  const [channel, setChannel] = useState("email");
  const [recipient, setRecipient] = useState("");
  const [recipientError, setRecipientError] = useState<string | null>(null);
  const [preview, setPreview] = useState<NotificationPreviewResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handlePreview() {
    if (!recipient) {
      setRecipientError("Please enter a recipient");
      return;
    }
    setRecipientError(null);
    setLoading(true);
    setError(null);
    try {
      const res = await previewNotification({
        template_id: templateId,
        channel,
        to: recipient,
        project_id: projectId,
        parcel_id: parcelId,
        variables: {},
      });
      setPreview(res);
      if (res.mode === "live") {
        toast.success("Notification sent", `Sent to ${res.to}`);
      } else {
        toast.success("Preview generated");
      }
    } catch (e) {
      const message = e instanceof Error ? e.message : String(e);
      setError(message);
      setPreview(null);
      toast.error("Couldn't generate preview", message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-card border border-slate-200 bg-white p-6 shadow-card">
      <div className="mb-4">
        <h3 className="text-h3 font-semibold">Notifications</h3>
        <p className="text-small text-slate-500">
          Preview and send communications to landowners
        </p>
      </div>

      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <Field label="Template">
            {(field) => (
              <Select
                {...field}
                value={templateId}
                onChange={(e) => setTemplateId(e.target.value)}
              >
                {TEMPLATE_OPTIONS.map((opt) => (
                  <option key={opt.id} value={opt.id}>
                    {opt.label}
                  </option>
                ))}
              </Select>
            )}
          </Field>
          <Field label="Channel">
            {(field) => (
              <Select
                {...field}
                value={channel}
                onChange={(e) => setChannel(e.target.value)}
              >
                {CHANNEL_OPTIONS.map((opt) => (
                  <option key={opt.id} value={opt.id}>
                    {opt.label}
                  </option>
                ))}
              </Select>
            )}
          </Field>
        </div>

        <Field
          label={`Recipient ${channel === "email" ? "(email)" : "(phone)"}`}
          required
          error={recipientError}
        >
          {(field) => (
            <Input
              {...field}
              type={channel === "email" ? "email" : "tel"}
              value={recipient}
              onChange={(e) => {
                setRecipient(e.target.value);
                if (recipientError) setRecipientError(null);
              }}
              placeholder={channel === "email" ? "owner@example.com" : "+1 555-123-4567"}
            />
          )}
        </Field>

        <div className="flex gap-2 text-caption text-slate-500">
          <span>
            Project <span className="font-id">{projectId}</span>
          </span>
          <span>·</span>
          <span>
            Parcel <span className="font-id">{parcelId}</span>
          </span>
        </div>

        <Button className="w-full" onClick={handlePreview} loading={loading}>
          {loading ? "Generating preview..." : "Preview notification"}
        </Button>

        {error && (
          <Alert variant="danger" title="Couldn't generate preview">
            {error}
          </Alert>
        )}

        {preview && (
          <div className="border-t border-slate-200 pt-4 space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-small font-medium text-slate-700">Preview</h4>
              <Badge variant={preview.mode === "live" ? "success" : "warning"}>
                {preview.mode === "live" ? "Live" : "Preview"}
              </Badge>
            </div>

            {preview.subject && (
              <div>
                <p className="text-caption text-slate-500">Subject</p>
                <p className="text-small text-slate-900">{preview.subject}</p>
              </div>
            )}

            <div>
              <p className="text-caption text-slate-500">Body</p>
              <div className="bg-slate-50 rounded-card p-3 text-small text-slate-700 whitespace-pre-wrap max-h-48 overflow-y-auto">
                {preview.body}
              </div>
            </div>

            <div className="flex flex-wrap gap-4 text-caption text-slate-500">
              <span>To: {preview.to}</span>
              <span>Channel: {preview.channel}</span>
              {preview.notification_id && (
                <span>
                  ID: <span className="font-id">{preview.notification_id}</span>
                </span>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
