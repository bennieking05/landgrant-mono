"use client";

import { useEffect, useState } from "react";
import {
  listTemplates,
  renderTemplate,
  deriveDeadlines,
  type TemplateMetadata,
  type TemplateRenderResponse,
} from "@/lib/api";

export function TemplateViewer() {
  const [templates, setTemplates] = useState<TemplateMetadata[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Selected template and preview
  const [selected, setSelected] = useState<TemplateMetadata | null>(null);
  const [variables, setVariables] = useState<Record<string, string>>({});
  const [renderResult, setRenderResult] = useState<TemplateRenderResponse | null>(null);
  const [rendering, setRendering] = useState(false);
  const [derivingDeadlines, setDerivingDeadlines] = useState(false);
  const [deadlinesGenerated, setDeadlinesGenerated] = useState(false);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const res = await listTemplates();
      setTemplates(res);
    } catch (e) {
      setError(String(e));
      setTemplates(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  function selectTemplate(tpl: TemplateMetadata) {
    setSelected(tpl);
    setRenderResult(null);
    setDeadlinesGenerated(false);
    // Initialize variables from schema
    const vars: Record<string, string> = {};
    if (tpl.variables && typeof tpl.variables === "object") {
      for (const key of Object.keys(tpl.variables)) {
        vars[key] = "";
      }
    }
    setVariables(vars);
  }

  async function handleRender() {
    if (!selected) return;

    setRendering(true);
    setError(null);
    setDeadlinesGenerated(false);
    try {
      // Convert string values to appropriate types based on schema
      const typedVars: Record<string, unknown> = {};
      for (const [key, val] of Object.entries(variables)) {
        const schema = selected.variables[key] as { type?: string } | undefined;
        if (schema?.type === "number" || schema?.type === "integer") {
          typedVars[key] = val ? Number(val) : 0;
        } else if (schema?.type === "array") {
          typedVars[key] = val ? val.split(",").map((s) => s.trim()) : [];
        } else {
          typedVars[key] = val;
        }
      }

      const res = await renderTemplate({
        template_id: selected.id,
        locale: selected.locale,
        variables: typedVars,
      });
      setRenderResult(res);
    } catch (e) {
      setError(String(e));
    } finally {
      setRendering(false);
    }
  }

  async function handleDeriveDeadlines() {
    if (!renderResult?.deadline_anchors || !selected?.jurisdiction) return;

    setDerivingDeadlines(true);
    setError(null);
    try {
      await deriveDeadlines({
        project_id: "PRJ-001", // Default project
        jurisdiction: selected.jurisdiction,
        anchor_events: renderResult.deadline_anchors,
        persist: true,
        timezone: selected.jurisdiction === "IN" ? "America/Indiana/Indianapolis" : "America/Chicago",
      });
      setDeadlinesGenerated(true);
    } catch (e) {
      setError(String(e));
    } finally {
      setDerivingDeadlines(false);
    }
  }

  function getVariableType(schema: unknown): string {
    if (schema && typeof schema === "object" && "type" in schema) {
      return String((schema as { type: string }).type);
    }
    return "string";
  }

  function isRequired(schema: unknown): boolean {
    if (schema && typeof schema === "object" && "required" in schema) {
      return Boolean((schema as { required: boolean }).required);
    }
    return false;
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold">Template Library</h3>
          <p className="text-sm text-slate-500">Browse and preview document templates</p>
        </div>
        <button
          onClick={refresh}
          disabled={loading}
          className="text-sm text-brand hover:underline disabled:opacity-50"
        >
          Refresh
        </button>
      </div>

      {error && <p className="text-sm text-rose-600 mb-3">{error}</p>}
      {loading && <p className="text-sm text-slate-500 mb-3">Loading templates...</p>}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Template list */}
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-slate-700">Available Templates</h4>
          <ul className="space-y-2 max-h-64 overflow-y-auto">
            {(templates ?? []).map((tpl) => (
              <li
                key={tpl.id}
                onClick={() => selectTemplate(tpl)}
                className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                  selected?.id === tpl.id
                    ? "border-brand bg-brand/5"
                    : "border-slate-200 hover:border-slate-300"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium text-slate-900">{tpl.id.toUpperCase()}</span>
                  <span className="text-xs text-slate-500">v{tpl.version}</span>
                </div>
                <div className="flex gap-2 mt-1">
                  {tpl.jurisdiction && (
                    <span className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded">
                      {tpl.jurisdiction}
                    </span>
                  )}
                  <span className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded">
                    {tpl.locale}
                  </span>
                  <span className={`text-xs px-2 py-0.5 rounded ${
                    tpl.privilege === "privileged" ? "bg-amber-100 text-amber-700" : "bg-emerald-100 text-emerald-700"
                  }`}>
                    {tpl.privilege}
                  </span>
                </div>
              </li>
            ))}
            {templates?.length === 0 && (
              <li className="py-4 text-center text-slate-500">No templates found</li>
            )}
          </ul>
        </div>

        {/* Variable form + Preview */}
        <div className="space-y-4">
          {selected ? (
            <>
              <div>
                <h4 className="text-sm font-medium text-slate-700 mb-2">
                  Variables for {selected.id.toUpperCase()}
                </h4>
                <div className="space-y-3 max-h-48 overflow-y-auto">
                  {Object.entries(selected.variables).map(([key, schema]) => (
                    <div key={key}>
                      <label className="block text-xs text-slate-600 mb-1">
                        {key}
                        {isRequired(schema) && <span className="text-rose-500 ml-1">*</span>}
                        <span className="text-slate-400 ml-2">({getVariableType(schema)})</span>
                      </label>
                      <input
                        type={getVariableType(schema) === "number" || getVariableType(schema) === "integer" ? "number" : "text"}
                        value={variables[key] ?? ""}
                        onChange={(e) => setVariables({ ...variables, [key]: e.target.value })}
                        placeholder={getVariableType(schema) === "array" ? "comma,separated,values" : `Enter ${key}`}
                        className="w-full rounded-md border border-slate-300 px-3 py-1.5 text-sm"
                      />
                    </div>
                  ))}
                </div>
                <button
                  onClick={handleRender}
                  disabled={rendering}
                  className="mt-3 w-full rounded-md bg-brand px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
                >
                  {rendering ? "Rendering..." : "Preview Template"}
                </button>
              </div>

              {renderResult && (
                <div className="space-y-4">
                  <div>
                    <h4 className="text-sm font-medium text-slate-700 mb-2">Rendered Preview</h4>
                    <div className="bg-slate-50 rounded-lg p-4 text-sm text-slate-700 whitespace-pre-wrap max-h-48 overflow-y-auto font-mono">
                      {renderResult.rendered}
                    </div>
                  </div>

                  {/* Deadline Anchors */}
                  {renderResult.deadline_anchors && Object.keys(renderResult.deadline_anchors).length > 0 && (
                    <div className="border-t border-slate-200 pt-3">
                      <h4 className="text-sm font-medium text-slate-700 mb-2">
                        Deadline Anchors Detected
                      </h4>
                      <div className="bg-indigo-50 rounded-lg p-3 space-y-1">
                        {Object.entries(renderResult.deadline_anchors).map(([event, date]) => (
                          <div key={event} className="flex justify-between text-xs">
                            <span className="text-indigo-700 font-medium">{event.replace(/_/g, " ")}</span>
                            <span className="text-indigo-600">{date}</span>
                          </div>
                        ))}
                      </div>
                      {selected?.jurisdiction && (
                        <button
                          onClick={handleDeriveDeadlines}
                          disabled={derivingDeadlines || deadlinesGenerated}
                          className={`mt-3 w-full rounded-md px-4 py-2 text-sm font-medium ${
                            deadlinesGenerated
                              ? "bg-emerald-100 text-emerald-700"
                              : "bg-indigo-600 text-white disabled:opacity-50"
                          }`}
                        >
                          {deadlinesGenerated
                            ? "Statutory Deadlines Generated"
                            : derivingDeadlines
                            ? "Generating..."
                            : `Generate ${selected.jurisdiction} Statutory Deadlines`}
                        </button>
                      )}
                    </div>
                  )}

                  {renderResult.document_id && (
                    <p className="text-xs text-slate-500">
                      Document ID: {renderResult.document_id}
                    </p>
                  )}
                </div>
              )}
            </>
          ) : (
            <div className="flex items-center justify-center h-48 text-slate-400 text-sm">
              Select a template to view details
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

