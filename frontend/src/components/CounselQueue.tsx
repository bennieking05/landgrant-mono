"use client";

import { useEffect, useState, useCallback } from "react";
import { apiGet } from "@/lib/api";
import { LoadingSpinner, ErrorMessage, EmptyState } from "@/components/ui";
import { ClipboardCheck } from "lucide-react";

type Approval = { case_id: string; action: string; due: string };

export function CounselQueue() {
  const [items, setItems] = useState<Approval[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(() => {
    setLoading(true);
    setError(null);
    apiGet<{ items: Approval[] }>("/workflows/approvals", "in_house_counsel")
      .then((d) => setItems(d.items))
      .catch((e) => {
        setItems(null);
        setError(String(e));
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <h3 className="text-lg font-semibold">Counsel approvals</h3>

      {loading && (
        <div className="mt-4">
          <LoadingSpinner text="Loading approvals..." />
        </div>
      )}

      {error && (
        <div className="mt-4">
          <ErrorMessage message="Failed to load approvals" onRetry={fetchData} />
        </div>
      )}

      {!loading && !error && items?.length === 0 && (
        <EmptyState
          icon={ClipboardCheck}
          message="No pending approvals"
          className="mt-4"
        />
      )}

      {!loading && !error && items && items.length > 0 && (
        <table className="mt-3 w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wide text-slate-500">
              <th>Case</th>
              <th>Action</th>
              <th>Due</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.case_id} className="border-t text-slate-700">
                <td className="py-2">{item.case_id}</td>
                <td>{item.action}</td>
                <td>{item.due}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}



