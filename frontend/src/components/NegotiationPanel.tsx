"use client";

import { useEffect, useState } from "react";
import {
  listOffers,
  createOffer,
  createCounterOffer,
  getPaymentLedger,
  type OfferItem,
  type OfferCreatePayload,
  type CounterOfferPayload,
  type PaymentLedgerResponse,
} from "@/lib/api";

type Props = {
  parcelId: string;
  projectId: string;
};

type OfferStatus = "draft" | "pending" | "accepted" | "rejected" | "countered" | "withdrawn" | "expired";
type OfferType = "initial" | "counter" | "final" | "settlement";

const STATUS_COLORS: Record<OfferStatus, string> = {
  draft: "bg-slate-100 text-slate-700",
  pending: "bg-blue-50 text-blue-700",
  accepted: "bg-emerald-50 text-emerald-700",
  rejected: "bg-rose-50 text-rose-700",
  countered: "bg-purple-50 text-purple-700",
  withdrawn: "bg-amber-50 text-amber-700",
  expired: "bg-slate-50 text-slate-500",
};

const TYPE_LABELS: Record<OfferType, string> = {
  initial: "Initial Offer",
  counter: "Counter Offer",
  final: "Final Offer",
  settlement: "Settlement",
};

export function NegotiationPanel({ parcelId, projectId }: Props) {
  const [offers, setOffers] = useState<OfferItem[] | null>(null);
  const [ledger, setLedger] = useState<PaymentLedgerResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  
  // Create offer form
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [offerType, setOfferType] = useState<OfferType>("initial");
  const [amount, setAmount] = useState("");
  const [terms, setTerms] = useState("");
  
  // Counter offer form
  const [counteringOfferId, setCounteringOfferId] = useState<string | null>(null);
  const [counterAmount, setCounterAmount] = useState("");
  const [counterTerms, setCounterTerms] = useState("");
  const [submittingCounter, setSubmittingCounter] = useState(false);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const [offersRes, ledgerRes] = await Promise.all([
        listOffers(parcelId),
        getPaymentLedger(parcelId).catch(() => null),
      ]);
      // Sort by created_date descending (most recent first for timeline)
      setOffers(offersRes.items.sort((a, b) => 
        new Date(b.created_date || 0).getTime() - new Date(a.created_date || 0).getTime()
      ));
      setLedger(ledgerRes);
    } catch (e) {
      setError(String(e));
      setOffers(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, [parcelId, projectId]);

  async function handleCreateOffer() {
    if (!amount) {
      setError("Please provide an offer amount");
      return;
    }

    setCreating(true);
    setError(null);
    try {
      const payload: OfferCreatePayload = {
        parcel_id: parcelId,
        project_id: projectId,
        offer_type: offerType,
        amount: parseFloat(amount),
        terms: terms ? { description: terms } : undefined,
      };
      await createOffer(payload);
      setShowCreate(false);
      setAmount("");
      setTerms("");
      setOfferType("initial");
      await refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setCreating(false);
    }
  }

  async function handleCounterOffer(offerId: string) {
    if (!counterAmount) {
      setError("Please provide a counter amount");
      return;
    }

    setSubmittingCounter(true);
    setError(null);
    try {
      const payload: CounterOfferPayload = {
        counter_amount: parseFloat(counterAmount),
        counter_terms: counterTerms ? { description: counterTerms } : undefined,
      };
      await createCounterOffer(offerId, payload);
      setCounteringOfferId(null);
      setCounterAmount("");
      setCounterTerms("");
      await refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setSubmittingCounter(false);
    }
  }

  function formatCurrency(value?: number): string {
    if (value === undefined || value === null) return "—";
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  }

  function formatDate(isoDate?: string): string {
    if (!isoDate) return "—";
    return new Date(isoDate).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  }

  function formatTime(isoDate?: string): string {
    if (!isoDate) return "";
    return new Date(isoDate).toLocaleTimeString("en-US", {
      hour: "numeric",
      minute: "2-digit",
    });
  }

  const currentOffer = offers?.find((o) => 
    o.status === "pending" || o.status === "accepted"
  );
  const acceptedOffer = offers?.find((o) => o.status === "accepted");

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold">Negotiation</h3>
          <p className="text-sm text-slate-500">Parcel: {parcelId}</p>
        </div>
        <div className="flex items-center gap-3">
          {acceptedOffer && (
            <span className="text-xs px-2 py-1 rounded-full bg-emerald-50 text-emerald-700">
              Deal: {formatCurrency(acceptedOffer.amount)}
            </span>
          )}
          <button
            onClick={() => setShowCreate(!showCreate)}
            className="text-sm px-3 py-1 rounded-md bg-brand text-white hover:bg-brand-dark transition-colors"
            disabled={!!acceptedOffer}
          >
            {showCreate ? "Cancel" : "+ New Offer"}
          </button>
          <button
            onClick={refresh}
            disabled={loading}
            className="text-sm text-brand hover:underline disabled:opacity-50"
          >
            Refresh
          </button>
        </div>
      </div>

      {/* Payment Ledger Summary */}
      {ledger && (
        <div className="mb-6 p-3 rounded-lg bg-slate-50 border border-slate-200">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-slate-700">Payment Status</span>
            <span className={`text-xs px-2 py-1 rounded-full ${
              ledger.payment_status === "paid" 
                ? "bg-emerald-100 text-emerald-700"
                : ledger.payment_status === "pending"
                ? "bg-blue-100 text-blue-700"
                : "bg-slate-100 text-slate-600"
            }`}>
              {ledger.payment_status || "not set"}
            </span>
          </div>
          {ledger.amount_paid && (
            <p className="text-xs text-slate-500 mt-1">
              Paid: {formatCurrency(ledger.amount_paid)} on {formatDate(ledger.payment_date)}
            </p>
          )}
        </div>
      )}

      {/* Create Offer Form */}
      {showCreate && (
        <div className="mb-6 p-4 rounded-lg bg-slate-50 border border-slate-200">
          <h4 className="font-medium mb-3">Create New Offer</h4>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label className="text-xs text-slate-500 block mb-1">Offer Type</label>
              <select
                value={offerType}
                onChange={(e) => setOfferType(e.target.value as OfferType)}
                className="w-full px-3 py-2 text-sm border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-brand"
              >
                <option value="initial">Initial Offer</option>
                <option value="counter">Counter Offer</option>
                <option value="final">Final Offer</option>
                <option value="settlement">Settlement</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-slate-500 block mb-1">Amount ($)</label>
              <input
                type="number"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                placeholder="0"
                className="w-full px-3 py-2 text-sm border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-brand"
              />
            </div>
          </div>
          <div className="mb-4">
            <label className="text-xs text-slate-500 block mb-1">Terms / Notes</label>
            <textarea
              value={terms}
              onChange={(e) => setTerms(e.target.value)}
              placeholder="Enter any terms or notes..."
              rows={2}
              className="w-full px-3 py-2 text-sm border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-brand"
            />
          </div>
          <button
            onClick={handleCreateOffer}
            disabled={creating}
            className="px-4 py-2 text-sm rounded-md bg-brand text-white hover:bg-brand-dark disabled:opacity-50 transition-colors"
          >
            {creating ? "Creating..." : "Submit Offer"}
          </button>
        </div>
      )}

      {error && <p className="text-sm text-rose-600 mb-3">{error}</p>}
      {loading && <p className="text-sm text-slate-500 mb-3">Loading...</p>}

      {/* Offer Timeline */}
      <div className="relative">
        {/* Timeline line */}
        {(offers?.length ?? 0) > 0 && (
          <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-slate-200" />
        )}

        <ul className="space-y-4">
          {(offers ?? []).map((offer, index) => {
            const status = (offer.status as OfferStatus) || "draft";
            const type = (offer.offer_type as OfferType) || "initial";
            const isLatest = index === 0;
            const isCountering = counteringOfferId === offer.id;

            return (
              <li key={offer.id} className="relative pl-10">
                {/* Timeline dot */}
                <div className={`absolute left-2.5 w-3 h-3 rounded-full border-2 ${
                  status === "accepted"
                    ? "bg-emerald-500 border-emerald-500"
                    : status === "rejected"
                    ? "bg-rose-500 border-rose-500"
                    : status === "pending"
                    ? "bg-blue-500 border-blue-500"
                    : "bg-white border-slate-300"
                }`} style={{ top: "0.5rem" }} />

                <div className={`p-4 rounded-lg border ${
                  isLatest && status === "pending"
                    ? "border-blue-200 bg-blue-50/30"
                    : status === "accepted"
                    ? "border-emerald-200 bg-emerald-50/30"
                    : "border-slate-200 bg-white"
                }`}>
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-semibold text-slate-900">
                          {formatCurrency(offer.amount)}
                        </span>
                        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_COLORS[status]}`}>
                          {status}
                        </span>
                        <span className="text-xs text-slate-500">
                          {TYPE_LABELS[type]}
                        </span>
                      </div>
                      <p className="text-xs text-slate-500">
                        {formatDate(offer.created_at)} at {formatTime(offer.created_at)}
                      </p>
                      {offer.terms && typeof offer.terms === "object" && (offer.terms as { description?: string }).description && (
                        <p className="text-xs text-slate-600 mt-2 italic">
                          "{(offer.terms as { description: string }).description}"
                        </p>
                      )}
                      {offer.counter_amount && (
                        <p className="text-xs text-purple-600 mt-2">
                          Counter: {formatCurrency(offer.counter_amount)} on {formatDate(offer.counter_date)}
                        </p>
                      )}
                    </div>
                    <div className="flex flex-col gap-2 ml-4">
                      {/* Actions for pending offers */}
                      {status === "pending" && !isCountering && (
                        <>
                          <button
                            onClick={() => setCounteringOfferId(offer.id)}
                            className="text-xs px-3 py-1 rounded bg-purple-500 text-white hover:bg-purple-600 transition-colors"
                          >
                            Counter
                          </button>
                        </>
                      )}
                    </div>
                  </div>

                  {/* Counter Offer Form */}
                  {isCountering && (
                    <div className="mt-4 pt-4 border-t border-slate-200">
                      <h5 className="text-sm font-medium mb-3">Submit Counter Offer</h5>
                      <div className="grid grid-cols-2 gap-3 mb-3">
                        <div>
                          <label className="text-xs text-slate-500 block mb-1">Counter Amount ($)</label>
                          <input
                            type="number"
                            value={counterAmount}
                            onChange={(e) => setCounterAmount(e.target.value)}
                            placeholder="0"
                            className="w-full px-2 py-1 text-sm border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-brand"
                          />
                        </div>
                        <div>
                          <label className="text-xs text-slate-500 block mb-1">Counter Terms</label>
                          <input
                            type="text"
                            value={counterTerms}
                            onChange={(e) => setCounterTerms(e.target.value)}
                            placeholder="Optional terms..."
                            className="w-full px-2 py-1 text-sm border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-brand"
                          />
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleCounterOffer(offer.id)}
                          disabled={submittingCounter}
                          className="px-3 py-1 text-sm rounded-md bg-purple-500 text-white hover:bg-purple-600 disabled:opacity-50 transition-colors"
                        >
                          {submittingCounter ? "Submitting..." : "Submit Counter"}
                        </button>
                        <button
                          onClick={() => {
                            setCounteringOfferId(null);
                            setCounterAmount("");
                            setCounterTerms("");
                          }}
                          className="px-3 py-1 text-sm rounded-md border border-slate-300 text-slate-600 hover:bg-slate-50 transition-colors"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </li>
            );
          })}
          {offers?.length === 0 && (
            <li className="py-8 text-center text-slate-500">
              <p>No offers recorded for this parcel.</p>
              <button
                onClick={() => setShowCreate(true)}
                className="mt-2 text-brand hover:underline"
              >
                Create the first offer
              </button>
            </li>
          )}
        </ul>
      </div>

      {/* Summary Stats */}
      {offers && offers.length > 0 && (
        <div className="mt-6 pt-4 border-t border-slate-200">
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <p className="text-2xl font-semibold text-slate-900">{offers.length}</p>
              <p className="text-xs text-slate-500">Total Offers</p>
            </div>
            <div>
              <p className="text-2xl font-semibold text-slate-900">
                {offers.filter((o) => o.offer_type === "counter").length}
              </p>
              <p className="text-xs text-slate-500">Counters</p>
            </div>
            <div>
              <p className="text-2xl font-semibold text-emerald-600">
                {acceptedOffer ? formatCurrency(acceptedOffer.amount) : "—"}
              </p>
              <p className="text-xs text-slate-500">Final Amount</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
