"use client";

import { useState, useCallback, useEffect } from "react";
import { getCase, getAppraisal, listOffers, type CaseDetails, type AppraisalResponse, type OffersResponse } from "@/lib/api";

type Props = {
  parcelId?: string;
  projectId?: string;
  jurisdiction?: string;
  assessedValue?: number;
  onPredictionComplete?: (prediction: SettlementPrediction) => void;
  autoFill?: boolean; // Enable auto-fill from case data
};

type SettlementRange = {
  low: number;
  expected: number;
  high: number;
};

type Timeline = {
  expected_days: number;
  min_days: number;
  max_days: number;
};

type Risk = {
  litigation_probability: number;
  dispute_level: string;
  risk_factors: string[];
};

type Recommendations = {
  initial_offer: number;
  ceiling: number;
  strategy: string;
};

type SettlementPrediction = {
  settlement_range: SettlementRange;
  confidence: number;
  timeline: Timeline;
  risk: Risk;
  recommendations: Recommendations;
  factors: string[];
  model_version: string;
  generated_at: string;
};

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8050";

export function SettlementPredictor({
  parcelId,
  projectId,
  jurisdiction = "TX",
  assessedValue = 0,
  onPredictionComplete,
  autoFill = true,
}: Props) {
  const [prediction, setPrediction] = useState<SettlementPrediction | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [autoFillStatus, setAutoFillStatus] = useState<string | null>(null);

  // Form state
  const [formData, setFormData] = useState({
    jurisdiction: jurisdiction,
    assessed_value: assessedValue || 350000,
    property_type: "residential_single",
    project_type: "utility",
    owner_occupied: false,
    principal_residence: false,
    family_ownership_years: 0,
    partial_taking: false,
    severance_impact: 0,
    access_impact: false,
    business_on_property: false,
    owner_has_attorney: false,
    previous_counter_offer: false,
    counter_offer_amount: 0,
    owner_contested_appraisal: false,
  });

  // Auto-fill from case/parcel data
  useEffect(() => {
    if (!autoFill || !parcelId) return;

    const loadCaseData = async () => {
      setAutoFillStatus("Loading case data...");
      const updates: Partial<typeof formData> = {};
      let fieldsUpdated = 0;

      try {
        // Load case details
        const caseData = await getCase(parcelId);
        if (caseData) {
          // Auto-detect risk level from case data
          if (caseData.risk_score !== undefined) {
            if (caseData.risk_score >= 70) {
              updates.owner_has_attorney = true;
              fieldsUpdated++;
            }
          }
        }
      } catch (e) {
        console.log("Could not load case data:", e);
      }

      try {
        // Load appraisal data for assessed value
        const appraisal = await getAppraisal(parcelId);
        if (appraisal.appraisal?.value) {
          updates.assessed_value = appraisal.appraisal.value;
          fieldsUpdated++;
        }
      } catch (e) {
        console.log("Could not load appraisal data:", e);
      }

      try {
        // Load offers to check for counter-offers
        const offersData = await listOffers(parcelId);
        if (offersData.items && offersData.items.length > 0) {
          const counterOffers = offersData.items.filter(o => o.offer_type === "counter" || o.source === "landowner");
          if (counterOffers.length > 0) {
            updates.previous_counter_offer = true;
            const latestCounter = counterOffers.sort((a, b) => 
              new Date(b.created_date || 0).getTime() - new Date(a.created_date || 0).getTime()
            )[0];
            if (latestCounter.amount) {
              updates.counter_offer_amount = latestCounter.amount;
            }
            fieldsUpdated += 2;
          }
        }
      } catch (e) {
        console.log("Could not load offers data:", e);
      }

      // Apply updates
      if (Object.keys(updates).length > 0) {
        setFormData(prev => ({ ...prev, ...updates }));
        setAutoFillStatus(`Auto-filled ${fieldsUpdated} field(s) from case data`);
        // Show advanced options if counter-offer was detected
        if (updates.previous_counter_offer) {
          setShowAdvanced(true);
        }
      } else {
        setAutoFillStatus(null);
      }
    };

    loadCaseData();
  }, [parcelId, autoFill]);

  // Update jurisdiction when prop changes
  useEffect(() => {
    if (jurisdiction && jurisdiction !== formData.jurisdiction) {
      setFormData(prev => ({ ...prev, jurisdiction }));
    }
  }, [jurisdiction]);

  const handleSubmit = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE}/analytics/predict-settlement`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Persona": "in_house_counsel",
        },
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        // Try to parse server error message
        let errorMessage = `Prediction failed: ${response.status}`;
        try {
          const errorData = await response.json();
          errorMessage = errorData.detail || errorData.message || errorData.error || errorMessage;
        } catch {
          // Response wasn't JSON, use default message
        }
        throw new Error(errorMessage);
      }

      const data: SettlementPrediction = await response.json();
      setPrediction(data);
      onPredictionComplete?.(data);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }, [formData, onPredictionComplete]);

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const formatPercent = (value: number) => {
    return `${(value * 100).toFixed(0)}%`;
  };

  const getDisputeColor = (level: string) => {
    switch (level) {
      case "low":
        return "text-emerald-600 bg-emerald-50";
      case "medium":
        return "text-amber-600 bg-amber-50";
      case "high":
        return "text-orange-600 bg-orange-50";
      case "very_high":
        return "text-rose-600 bg-rose-50";
      default:
        return "text-slate-600 bg-slate-50";
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.7) return "text-emerald-600";
    if (confidence >= 0.5) return "text-amber-600";
    return "text-rose-600";
  };

  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
      {/* Header */}
      <div className="px-6 py-4 border-b border-slate-200 bg-gradient-to-r from-purple-50 to-indigo-50">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center">
            <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
          <div>
            <h3 className="text-lg font-semibold text-slate-900">Settlement Predictor</h3>
            <p className="text-sm text-slate-500">AI-powered settlement analysis</p>
          </div>
        </div>
      </div>

      {/* Form */}
      <div className="p-6">
        {/* Auto-fill status */}
        {autoFillStatus && (
          <div className="mb-4 px-3 py-2 bg-emerald-50 border border-emerald-200 rounded-lg flex items-center gap-2">
            <svg className="w-4 h-4 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            <span className="text-sm text-emerald-700">{autoFillStatus}</span>
            <button
              onClick={() => setAutoFillStatus(null)}
              className="ml-auto text-emerald-600 hover:text-emerald-800"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        )}

        <div className="grid grid-cols-2 gap-4 mb-4">
          {/* Jurisdiction */}
          <div>
            <label className="text-xs text-slate-500 block mb-1">Jurisdiction</label>
            <select
              value={formData.jurisdiction}
              onChange={(e) => setFormData({ ...formData, jurisdiction: e.target.value })}
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
            >
              <option value="TX">Texas</option>
              <option value="CA">California</option>
              <option value="FL">Florida</option>
              <option value="IN">Indiana</option>
              <option value="MI">Michigan</option>
              <option value="MO">Missouri</option>
            </select>
          </div>

          {/* Assessed Value */}
          <div>
            <label className="text-xs text-slate-500 block mb-1">Assessed Value ($)</label>
            <input
              type="number"
              value={formData.assessed_value}
              onChange={(e) => setFormData({ ...formData, assessed_value: Number(e.target.value) })}
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
            />
          </div>

          {/* Property Type */}
          <div>
            <label className="text-xs text-slate-500 block mb-1">Property Type</label>
            <select
              value={formData.property_type}
              onChange={(e) => setFormData({ ...formData, property_type: e.target.value })}
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
            >
              <option value="residential_single">Residential (Single)</option>
              <option value="residential_multi">Residential (Multi)</option>
              <option value="commercial">Commercial</option>
              <option value="industrial">Industrial</option>
              <option value="agricultural">Agricultural</option>
              <option value="vacant_land">Vacant Land</option>
            </select>
          </div>

          {/* Project Type */}
          <div>
            <label className="text-xs text-slate-500 block mb-1">Project Type</label>
            <select
              value={formData.project_type}
              onChange={(e) => setFormData({ ...formData, project_type: e.target.value })}
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
            >
              <option value="highway">Highway</option>
              <option value="utility">Utility</option>
              <option value="transit">Transit</option>
              <option value="pipeline">Pipeline</option>
              <option value="flood_control">Flood Control</option>
            </select>
          </div>
        </div>

        {/* Quick toggles */}
        <div className="flex flex-wrap gap-3 mb-4">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={formData.owner_occupied}
              onChange={(e) => setFormData({ ...formData, owner_occupied: e.target.checked })}
              className="rounded text-purple-600 focus:ring-purple-500"
            />
            Owner Occupied
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={formData.owner_has_attorney}
              onChange={(e) => setFormData({ ...formData, owner_has_attorney: e.target.checked })}
              className="rounded text-purple-600 focus:ring-purple-500"
            />
            Has Attorney
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={formData.partial_taking}
              onChange={(e) => setFormData({ ...formData, partial_taking: e.target.checked })}
              className="rounded text-purple-600 focus:ring-purple-500"
            />
            Partial Taking
          </label>
        </div>

        {/* Advanced options toggle */}
        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="text-sm text-purple-600 hover:text-purple-700 mb-4"
        >
          {showAdvanced ? "Hide" : "Show"} advanced options
        </button>

        {/* Advanced options */}
        {showAdvanced && (
          <div className="p-4 bg-slate-50 rounded-lg mb-4 space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={formData.business_on_property}
                  onChange={(e) => setFormData({ ...formData, business_on_property: e.target.checked })}
                  className="rounded text-purple-600 focus:ring-purple-500"
                />
                Business on Property
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={formData.access_impact}
                  onChange={(e) => setFormData({ ...formData, access_impact: e.target.checked })}
                  className="rounded text-purple-600 focus:ring-purple-500"
                />
                Access Impact
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={formData.owner_contested_appraisal}
                  onChange={(e) => setFormData({ ...formData, owner_contested_appraisal: e.target.checked })}
                  className="rounded text-purple-600 focus:ring-purple-500"
                />
                Contested Appraisal
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={formData.previous_counter_offer}
                  onChange={(e) => setFormData({ ...formData, previous_counter_offer: e.target.checked })}
                  className="rounded text-purple-600 focus:ring-purple-500"
                />
                Has Counter Offer
              </label>
            </div>
            {formData.previous_counter_offer && (
              <div>
                <label className="text-xs text-slate-500 block mb-1">Counter Offer Amount ($)</label>
                <input
                  type="number"
                  value={formData.counter_offer_amount}
                  onChange={(e) => setFormData({ ...formData, counter_offer_amount: Number(e.target.value) })}
                  className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
              </div>
            )}
            
            {/* Additional factors */}
            <div className="pt-3 border-t border-slate-200 space-y-3">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={formData.principal_residence}
                  onChange={(e) => setFormData({ ...formData, principal_residence: e.target.checked })}
                  className="rounded text-purple-600 focus:ring-purple-500"
                />
                Principal Residence
              </label>
              
              <div>
                <label className="text-xs text-slate-500 block mb-1">Family Ownership (years)</label>
                <input
                  type="number"
                  min="0"
                  value={formData.family_ownership_years}
                  onChange={(e) => setFormData({ ...formData, family_ownership_years: Number(e.target.value) })}
                  className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                  placeholder="0"
                />
              </div>
              
              {formData.partial_taking && (
                <div>
                  <label className="text-xs text-slate-500 block mb-1">Severance Impact (%)</label>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    value={formData.severance_impact}
                    onChange={(e) => setFormData({ ...formData, severance_impact: Number(e.target.value) })}
                    className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                    placeholder="0"
                  />
                  <p className="text-xs text-slate-400 mt-1">Impact on remaining property value</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Predict button */}
        <button
          onClick={handleSubmit}
          disabled={loading || formData.assessed_value <= 0}
          className="w-full py-3 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-lg font-medium hover:from-purple-700 hover:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              Analyzing...
            </span>
          ) : (
            "Generate Prediction"
          )}
        </button>

        {error && (
          <p className="mt-3 text-sm text-rose-600 text-center">{error}</p>
        )}
      </div>

      {/* Results */}
      {prediction && (
        <div className="border-t border-slate-200">
          {/* Settlement Range */}
          <div className="p-6 bg-gradient-to-r from-emerald-50 to-teal-50">
            <h4 className="text-sm font-medium text-slate-700 mb-3">Predicted Settlement Range</h4>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-slate-500">Low</span>
              <span className="text-sm text-slate-500">Expected</span>
              <span className="text-sm text-slate-500">High</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-lg font-medium text-slate-600">
                {formatCurrency(prediction.settlement_range.low)}
              </span>
              <span className="text-2xl font-bold text-emerald-600">
                {formatCurrency(prediction.settlement_range.expected)}
              </span>
              <span className="text-lg font-medium text-slate-600">
                {formatCurrency(prediction.settlement_range.high)}
              </span>
            </div>
            <div className="mt-3 h-2 bg-slate-200 rounded-full overflow-hidden relative">
              {/* Range bar visualization */}
              {prediction.settlement_range.high > 0 && (
                <div
                  className="h-full bg-gradient-to-r from-emerald-400 to-teal-500 absolute"
                  style={{
                    left: `${Math.max(0, (prediction.settlement_range.low / prediction.settlement_range.high) * 100)}%`,
                    width: `${Math.min(100, 100 - (prediction.settlement_range.low / prediction.settlement_range.high) * 100)}%`,
                  }}
                />
              )}
              {/* Expected value marker */}
              {prediction.settlement_range.high > 0 && (
                <div
                  className="absolute w-1 h-4 -top-1 bg-emerald-600 rounded"
                  style={{
                    left: `${Math.min(100, Math.max(0, (prediction.settlement_range.expected / prediction.settlement_range.high) * 100))}%`,
                  }}
                />
              )}
            </div>
            <p className={`mt-2 text-sm ${getConfidenceColor(prediction.confidence)}`}>
              {formatPercent(prediction.confidence)} confidence
            </p>
          </div>

          {/* Timeline & Risk */}
          <div className="grid grid-cols-2 divide-x divide-slate-200">
            <div className="p-6">
              <h4 className="text-sm font-medium text-slate-700 mb-3">Timeline</h4>
              <p className="text-3xl font-bold text-slate-900">
                {prediction.timeline.expected_days}
                <span className="text-base font-normal text-slate-500 ml-1">days</span>
              </p>
              <p className="text-sm text-slate-500 mt-1">
                Range: {prediction.timeline.min_days} - {prediction.timeline.max_days} days
              </p>
            </div>
            <div className="p-6">
              <h4 className="text-sm font-medium text-slate-700 mb-3">Litigation Risk</h4>
              <p className="text-3xl font-bold text-slate-900">
                {formatPercent(prediction.risk.litigation_probability)}
              </p>
              <span className={`inline-block mt-2 px-2 py-1 rounded-full text-xs font-medium ${getDisputeColor(prediction.risk.dispute_level)}`}>
                {prediction.risk.dispute_level.replace("_", " ")} dispute
              </span>
            </div>
          </div>

          {/* Recommendations */}
          <div className="p-6 border-t border-slate-200">
            <h4 className="text-sm font-medium text-slate-700 mb-3">Recommended Offer Strategy</h4>
            <div className="grid grid-cols-2 gap-4 mb-4">
              <div className="p-3 bg-blue-50 rounded-lg">
                <p className="text-xs text-blue-600 mb-1">Initial Offer</p>
                <p className="text-lg font-semibold text-blue-900">
                  {formatCurrency(prediction.recommendations.initial_offer)}
                </p>
              </div>
              <div className="p-3 bg-purple-50 rounded-lg">
                <p className="text-xs text-purple-600 mb-1">Ceiling</p>
                <p className="text-lg font-semibold text-purple-900">
                  {formatCurrency(prediction.recommendations.ceiling)}
                </p>
              </div>
            </div>
            <p className="text-sm text-slate-600">{prediction.recommendations.strategy}</p>
          </div>

          {/* Risk Factors */}
          {prediction.risk.risk_factors.length > 0 && (
            <div className="p-6 border-t border-slate-200 bg-rose-50/30">
              <h4 className="text-sm font-medium text-rose-700 mb-2">Risk Factors</h4>
              <ul className="space-y-1">
                {prediction.risk.risk_factors.map((factor, i) => (
                  <li key={i} className="text-sm text-rose-600 flex items-start gap-2">
                    <span className="text-rose-400 mt-0.5">!</span>
                    {factor}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Positive Factors */}
          {prediction.factors.length > 0 && (
            <div className="p-6 border-t border-slate-200">
              <h4 className="text-sm font-medium text-slate-700 mb-2">Positive Factors</h4>
              <ul className="space-y-1">
                {prediction.factors.map((factor, i) => (
                  <li key={i} className="text-sm text-slate-600 flex items-start gap-2">
                    <span className="text-emerald-500 mt-0.5">✓</span>
                    {factor}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Footer */}
          <div className="px-6 py-3 bg-slate-50 text-center">
            <p className="text-xs text-slate-400">
              Model: {prediction.model_version} • Generated: {new Date(prediction.generated_at).toLocaleString()}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
