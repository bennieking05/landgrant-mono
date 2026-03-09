"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { createCase } from "@/lib/api";
import { useNavigate } from "react-router-dom";

// Common Texas county FIPS codes for smart suggestions
const TEXAS_COUNTIES: Record<string, string> = {
  "48439": "Tarrant County",
  "48113": "Dallas County",
  "48201": "Harris County",
  "48029": "Bexar County",
  "48453": "Travis County",
  "48141": "El Paso County",
  "48085": "Collin County",
  "48121": "Denton County",
  "48215": "Hidalgo County",
  "48157": "Fort Bend County",
};

// State FIPS prefixes for jurisdiction detection
const STATE_PREFIXES: Record<string, string> = {
  "48": "TX",
  "06": "CA",
  "12": "FL",
  "18": "IN",
  "26": "MI",
  "29": "MO",
};

type Props = {
  initialProjectId: string;
  onPartyAdd?: (party: { name: string; role: string; email?: string }) => void;
};

export function IntakeForm({ initialProjectId, onPartyAdd }: Props) {
  const navigate = useNavigate();
  const [projectId, setProjectId] = useState(initialProjectId);
  const [countyFips, setCountyFips] = useState("48439");
  const [jurisdiction, setJurisdiction] = useState("TX");
  const [status, setStatus] = useState<string | null>(null);
  const [showSuggestions, setShowSuggestions] = useState(false);
  
  // Enhanced form fields
  const [ownerName, setOwnerName] = useState("");
  const [ownerEmail, setOwnerEmail] = useState("");
  const [propertyAddress, setPropertyAddress] = useState("");
  const [estimatedValue, setEstimatedValue] = useState<number | "">("");
  const [riskLevel, setRiskLevel] = useState<"low" | "medium" | "high">("medium");

  // Auto-detect jurisdiction from FIPS code
  useEffect(() => {
    const prefix = countyFips.slice(0, 2);
    const detectedJurisdiction = STATE_PREFIXES[prefix];
    if (detectedJurisdiction && detectedJurisdiction !== jurisdiction) {
      setJurisdiction(detectedJurisdiction);
    }
  }, [countyFips, jurisdiction]);

  // Get county name from FIPS
  const countyName = useMemo(() => {
    return TEXAS_COUNTIES[countyFips] || null;
  }, [countyFips]);

  // Filter suggestions based on input
  const fipsSuggestions = useMemo(() => {
    if (!countyFips || countyFips.length < 2) return [];
    return Object.entries(TEXAS_COUNTIES)
      .filter(([fips, name]) => 
        fips.startsWith(countyFips) || 
        name.toLowerCase().includes(countyFips.toLowerCase())
      )
      .slice(0, 5);
  }, [countyFips]);

  // Calculate risk score from risk level
  const getRiskScore = useCallback((level: "low" | "medium" | "high") => {
    switch (level) {
      case "low": return 25;
      case "medium": return 50;
      case "high": return 75;
    }
  }, []);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setStatus("Submitting...");
    
    // Build parties array
    const parties = [];
    if (ownerName) {
      parties.push({
        name: ownerName,
        role: "landowner",
        email: ownerEmail || undefined,
      });
    }

    try {
      const response = await createCase({
        project_id: projectId,
        jurisdiction_code: jurisdiction,
        parcels: [
          {
            county_fips: countyFips,
            stage: "intake",
            risk_score: getRiskScore(riskLevel),
            parties,
          },
        ],
      });
      const parcelId = response.parcel_ids?.[0];
      setStatus(`Created parcels: ${response.parcel_ids?.join(", ") ?? "none"}`);
      if (parcelId) {
        navigate(`/workbench?projectId=${encodeURIComponent(projectId)}&parcelId=${encodeURIComponent(parcelId)}`);
      }
    } catch (error) {
      setStatus(`Create case failed: ${String(error)}`);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="px-6 py-4 border-b border-slate-200 bg-gradient-to-r from-brand/5 to-purple-50">
        <h3 className="text-lg font-semibold text-slate-900">Intake Form</h3>
        <p className="text-sm text-slate-600">Create a new parcel case with smart field detection</p>
      </div>
      
      <div className="p-6 space-y-4">
        {/* Project & Location */}
        <div className="grid grid-cols-2 gap-4">
          <label className="block text-sm">
            <span className="text-slate-600 font-medium">Project ID</span>
            <input
              value={projectId}
              onChange={(e) => setProjectId(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent"
              required
            />
          </label>
          
          <label className="block text-sm relative">
            <span className="text-slate-600 font-medium">County FIPS</span>
            <input
              value={countyFips}
              onChange={(e) => {
                setCountyFips(e.target.value);
                setShowSuggestions(true);
              }}
              onFocus={() => setShowSuggestions(true)}
              onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent"
              placeholder="e.g., 48439"
              required
            />
            {countyName && (
              <span className="absolute right-3 top-9 text-xs text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded">
                {countyName}
              </span>
            )}
            
            {/* FIPS Suggestions Dropdown */}
            {showSuggestions && fipsSuggestions.length > 0 && (
              <div className="absolute z-10 mt-1 w-full bg-white border border-slate-200 rounded-lg shadow-lg max-h-48 overflow-auto">
                {fipsSuggestions.map(([fips, name]) => (
                  <button
                    key={fips}
                    type="button"
                    onClick={() => {
                      setCountyFips(fips);
                      setShowSuggestions(false);
                    }}
                    className="w-full text-left px-3 py-2 hover:bg-slate-50 text-sm flex justify-between items-center"
                  >
                    <span className="font-medium">{fips}</span>
                    <span className="text-slate-500">{name}</span>
                  </button>
                ))}
              </div>
            )}
          </label>
        </div>

        {/* Jurisdiction (auto-detected) */}
        <div className="flex items-center gap-2 px-3 py-2 bg-blue-50 rounded-lg">
          <svg className="w-4 h-4 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
          <span className="text-sm text-blue-700">
            Jurisdiction auto-detected: <strong>{jurisdiction}</strong>
          </span>
          <select
            value={jurisdiction}
            onChange={(e) => setJurisdiction(e.target.value)}
            className="ml-auto text-sm bg-white border border-blue-200 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="TX">Texas</option>
            <option value="CA">California</option>
            <option value="FL">Florida</option>
            <option value="IN">Indiana</option>
            <option value="MI">Michigan</option>
            <option value="MO">Missouri</option>
          </select>
        </div>

        {/* Landowner Info */}
        <div className="pt-4 border-t border-slate-200">
          <h4 className="text-sm font-medium text-slate-700 mb-3">Landowner Information (Optional)</h4>
          <div className="grid grid-cols-2 gap-4">
            <label className="block text-sm">
              <span className="text-slate-600">Owner Name</span>
              <input
                value={ownerName}
                onChange={(e) => setOwnerName(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent"
                placeholder="John Smith"
              />
            </label>
            <label className="block text-sm">
              <span className="text-slate-600">Owner Email</span>
              <input
                type="email"
                value={ownerEmail}
                onChange={(e) => setOwnerEmail(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent"
                placeholder="owner@email.com"
              />
            </label>
          </div>
        </div>

        {/* Property & Risk */}
        <div className="pt-4 border-t border-slate-200">
          <h4 className="text-sm font-medium text-slate-700 mb-3">Property Details</h4>
          <div className="space-y-4">
            <label className="block text-sm">
              <span className="text-slate-600">Property Address (Optional)</span>
              <input
                value={propertyAddress}
                onChange={(e) => setPropertyAddress(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent"
                placeholder="123 Main St, City, State"
              />
            </label>
            
            <div className="grid grid-cols-2 gap-4">
              <label className="block text-sm">
                <span className="text-slate-600">Estimated Value ($)</span>
                <input
                  type="number"
                  value={estimatedValue}
                  onChange={(e) => setEstimatedValue(e.target.value ? Number(e.target.value) : "")}
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent"
                  placeholder="350000"
                />
              </label>
              
              <label className="block text-sm">
                <span className="text-slate-600">Initial Risk Assessment</span>
                <select
                  value={riskLevel}
                  onChange={(e) => setRiskLevel(e.target.value as "low" | "medium" | "high")}
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent"
                >
                  <option value="low">Low Risk</option>
                  <option value="medium">Medium Risk</option>
                  <option value="high">High Risk</option>
                </select>
              </label>
            </div>
          </div>
        </div>
      </div>
      
      <div className="px-6 py-4 bg-slate-50 border-t border-slate-200 flex items-center justify-between">
        <button 
          type="submit" 
          className="rounded-lg bg-brand px-6 py-2 text-sm font-medium text-white hover:bg-brand-dark transition-colors"
        >
          Create Parcel Case
        </button>
        {status && (
          <p className={`text-sm ${status.includes("failed") ? "text-rose-600" : "text-slate-500"}`}>
            {status}
          </p>
        )}
      </div>
    </form>
  );
}



