type DraftResponseType = "counter_offer" | "acceptance" | "rejection";

type DraftModalProps = {
  draftType: DraftResponseType;
  draftNotes: string;
  onDraftTypeChange: (t: DraftResponseType) => void;
  onNotesChange: (n: string) => void;
  onSubmit: () => void;
  onCancel: () => void;
};

export function DraftResponseModal({
  draftType,
  draftNotes,
  onDraftTypeChange,
  onNotesChange,
  onSubmit,
  onCancel,
}: DraftModalProps) {
  return (
    <div className="absolute inset-0 bg-black/20 flex items-center justify-center p-4 z-10">
      <div className="bg-white rounded-lg shadow-xl p-4 w-full max-w-sm">
        <h4 className="font-semibold text-slate-900 mb-3">Draft Response</h4>
        <div className="space-y-3">
          <div>
            <label className="text-xs font-medium text-slate-600 block mb-1">Response Type</label>
            <select
              value={draftType}
              onChange={(e) => onDraftTypeChange(e.target.value as DraftResponseType)}
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand"
            >
              <option value="counter_offer">Counter Offer</option>
              <option value="acceptance">Acceptance</option>
              <option value="rejection">Rejection</option>
            </select>
          </div>
          <div>
            <label className="text-xs font-medium text-slate-600 block mb-1">Notes (optional)</label>
            <textarea
              value={draftNotes}
              onChange={(e) => onNotesChange(e.target.value)}
              placeholder="Any specific points to include..."
              rows={2}
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-brand"
            />
          </div>
          <div className="flex gap-2 justify-end">
            <button onClick={onCancel} className="px-3 py-1.5 text-sm text-slate-600 hover:text-slate-800">
              Cancel
            </button>
            <button onClick={onSubmit} className="px-3 py-1.5 text-sm bg-brand text-white rounded-lg hover:bg-brand-dark">
              Generate Draft
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

type ExplainModalProps = {
  requirement: string;
  jurisdiction?: string;
  onRequirementChange: (r: string) => void;
  onSubmit: () => void;
  onCancel: () => void;
};

export function ExplainRequirementModal({
  requirement,
  jurisdiction,
  onRequirementChange,
  onSubmit,
  onCancel,
}: ExplainModalProps) {
  return (
    <div className="absolute inset-0 bg-black/20 flex items-center justify-center p-4 z-10">
      <div className="bg-white rounded-lg shadow-xl p-4 w-full max-w-sm">
        <h4 className="font-semibold text-slate-900 mb-3">Explain Requirement</h4>
        <div className="space-y-3">
          <div>
            <label className="text-xs font-medium text-slate-600 block mb-1">Requirement</label>
            <textarea
              value={requirement}
              onChange={(e) => onRequirementChange(e.target.value)}
              placeholder="e.g., 'Good faith negotiation', 'Appraisal requirements', 'Notice periods'..."
              rows={3}
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-brand"
            />
          </div>
          <p className="text-xs text-slate-500">
            Jurisdiction: <span className="font-medium">{jurisdiction || "Not set"}</span>
          </p>
          <div className="flex gap-2 justify-end">
            <button onClick={onCancel} className="px-3 py-1.5 text-sm text-slate-600 hover:text-slate-800">
              Cancel
            </button>
            <button
              onClick={onSubmit}
              disabled={!requirement.trim()}
              className="px-3 py-1.5 text-sm bg-brand text-white rounded-lg hover:bg-brand-dark disabled:opacity-50"
            >
              Explain
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
