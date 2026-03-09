"use client";

import { useState, useEffect, useCallback } from "react";
import { listTitleInstruments, type TitleInstrumentItem } from "@/lib/api";

// ============================================================================
// Types
// ============================================================================

type Props = {
  parcelId: string;
  onEntitiesUpdate?: (documentId: string, entities: ExtractedEntity[]) => void;
};

type ExtractedEntity = {
  id: string;
  type: EntityType;
  value: string;
  confidence: number;
  originalValue?: string;
  verified: boolean;
  boundingBox?: { x: number; y: number; width: number; height: number };
};

type EntityType = 
  | "grantor"
  | "grantee"
  | "legal_description"
  | "recording_date"
  | "book_page"
  | "consideration"
  | "notary"
  | "parcel_number"
  | "address"
  | "acreage"
  | "date"
  | "amount"
  | "name"
  | "other";

type SelectedDocument = TitleInstrumentItem & {
  entities: ExtractedEntity[];
};

// ============================================================================
// Constants
// ============================================================================

const ENTITY_TYPE_CONFIG: Record<EntityType, { label: string; icon: string; color: string }> = {
  grantor: { label: "Grantor", icon: "M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z", color: "bg-blue-100 text-blue-700 border-blue-300" },
  grantee: { label: "Grantee", icon: "M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z", color: "bg-purple-100 text-purple-700 border-purple-300" },
  legal_description: { label: "Legal Description", icon: "M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2", color: "bg-emerald-100 text-emerald-700 border-emerald-300" },
  recording_date: { label: "Recording Date", icon: "M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z", color: "bg-amber-100 text-amber-700 border-amber-300" },
  book_page: { label: "Book/Page", icon: "M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253", color: "bg-slate-100 text-slate-700 border-slate-300" },
  consideration: { label: "Consideration", icon: "M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z", color: "bg-green-100 text-green-700 border-green-300" },
  notary: { label: "Notary", icon: "M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z", color: "bg-indigo-100 text-indigo-700 border-indigo-300" },
  parcel_number: { label: "Parcel Number", icon: "M7 20l4-16m2 16l4-16M6 9h14M4 15h14", color: "bg-rose-100 text-rose-700 border-rose-300" },
  address: { label: "Address", icon: "M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z M15 11a3 3 0 11-6 0 3 3 0 016 0z", color: "bg-cyan-100 text-cyan-700 border-cyan-300" },
  acreage: { label: "Acreage", icon: "M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064", color: "bg-lime-100 text-lime-700 border-lime-300" },
  date: { label: "Date", icon: "M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z", color: "bg-orange-100 text-orange-700 border-orange-300" },
  amount: { label: "Amount", icon: "M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z", color: "bg-teal-100 text-teal-700 border-teal-300" },
  name: { label: "Name", icon: "M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z", color: "bg-violet-100 text-violet-700 border-violet-300" },
  other: { label: "Other", icon: "M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z", color: "bg-gray-100 text-gray-700 border-gray-300" },
};

// ============================================================================
// Helper Functions
// ============================================================================

function parseOCREntities(ocr_payload: Record<string, unknown> | undefined): ExtractedEntity[] {
  if (!ocr_payload) return [];
  
  const entities: ExtractedEntity[] = [];
  const confidence = typeof ocr_payload.confidence === "number" ? ocr_payload.confidence : 0.8;
  
  // Parse entities array if present
  if (Array.isArray(ocr_payload.entities)) {
    ocr_payload.entities.forEach((entity, idx) => {
      if (typeof entity === "string") {
        entities.push({
          id: `entity-${idx}`,
          type: detectEntityType(entity),
          value: entity,
          confidence,
          verified: false,
        });
      } else if (typeof entity === "object" && entity !== null) {
        const e = entity as Record<string, unknown>;
        entities.push({
          id: `entity-${idx}`,
          type: (e.type as EntityType) || detectEntityType(String(e.value || e.text || "")),
          value: String(e.value || e.text || ""),
          confidence: typeof e.confidence === "number" ? e.confidence : confidence,
          verified: false,
        });
      }
    });
  }
  
  // Parse extracted_data if present
  if (typeof ocr_payload.extracted_data === "object" && ocr_payload.extracted_data !== null) {
    const data = ocr_payload.extracted_data as Record<string, unknown>;
    Object.entries(data).forEach(([key, value], idx) => {
      if (value && typeof value === "string") {
        entities.push({
          id: `data-${idx}`,
          type: mapKeyToEntityType(key),
          value,
          confidence,
          verified: false,
        });
      }
    });
  }
  
  return entities;
}

function detectEntityType(value: string): EntityType {
  const v = value.toLowerCase();
  
  // Date patterns
  if (/^\d{1,2}\/\d{1,2}\/\d{2,4}$/.test(value) || /^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return "date";
  }
  
  // Amount patterns
  if (/^\$[\d,]+(\.\d{2})?$/.test(value) || /^\d+\.\d{2}$/.test(value)) {
    return "amount";
  }
  
  // Book/Page patterns
  if (/^(book|vol|volume)\s*\d+/i.test(value) || /^page\s*\d+/i.test(value)) {
    return "book_page";
  }
  
  // Acreage patterns
  if (/\d+(\.\d+)?\s*(acres?|ac)/i.test(value)) {
    return "acreage";
  }
  
  // Legal description indicators
  if (v.includes("lot") || v.includes("block") || v.includes("section") || v.includes("metes") || v.includes("bounds")) {
    return "legal_description";
  }
  
  // Address indicators
  if (/^\d+\s+\w+\s+(st|street|ave|avenue|rd|road|ln|lane|dr|drive|blvd|boulevard)/i.test(value)) {
    return "address";
  }
  
  return "other";
}

function mapKeyToEntityType(key: string): EntityType {
  const k = key.toLowerCase();
  if (k.includes("grantor")) return "grantor";
  if (k.includes("grantee")) return "grantee";
  if (k.includes("legal") || k.includes("description")) return "legal_description";
  if (k.includes("record") && k.includes("date")) return "recording_date";
  if (k.includes("book") || k.includes("page")) return "book_page";
  if (k.includes("consider") || k.includes("amount") || k.includes("price")) return "consideration";
  if (k.includes("notary")) return "notary";
  if (k.includes("parcel") || k.includes("apn")) return "parcel_number";
  if (k.includes("address")) return "address";
  if (k.includes("acre")) return "acreage";
  if (k.includes("date")) return "date";
  if (k.includes("name")) return "name";
  return "other";
}

// ============================================================================
// Component
// ============================================================================

export function DocumentExtraction({ parcelId, onEntitiesUpdate }: Props) {
  const [documents, setDocuments] = useState<TitleInstrumentItem[]>([]);
  const [selectedDoc, setSelectedDoc] = useState<SelectedDocument | null>(null);
  const [editingEntity, setEditingEntity] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load documents
  useEffect(() => {
    loadDocuments();
  }, [parcelId]);

  const loadDocuments = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await listTitleInstruments(parcelId);
      setDocuments(res.items);
      
      // Auto-select first document with OCR data
      const firstWithOCR = res.items.find(d => d.ocr_payload);
      if (firstWithOCR) {
        handleSelectDocument(firstWithOCR);
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  const handleSelectDocument = (doc: TitleInstrumentItem) => {
    const entities = parseOCREntities(doc.ocr_payload);
    setSelectedDoc({ ...doc, entities });
    setEditingEntity(null);
  };

  const handleUpdateEntity = useCallback((entityId: string, updates: Partial<ExtractedEntity>) => {
    if (!selectedDoc) return;
    
    const updatedEntities = selectedDoc.entities.map(e => 
      e.id === entityId ? { ...e, ...updates } : e
    );
    
    setSelectedDoc({ ...selectedDoc, entities: updatedEntities });
    
    if (selectedDoc.document_id) {
      onEntitiesUpdate?.(selectedDoc.document_id, updatedEntities);
    }
  }, [selectedDoc, onEntitiesUpdate]);

  const handleVerifyEntity = (entityId: string) => {
    handleUpdateEntity(entityId, { verified: true });
  };

  const handleRejectEntity = (entityId: string) => {
    if (!selectedDoc) return;
    const updatedEntities = selectedDoc.entities.filter(e => e.id !== entityId);
    setSelectedDoc({ ...selectedDoc, entities: updatedEntities });
  };

  const handleVerifyAll = () => {
    if (!selectedDoc) return;
    const updatedEntities = selectedDoc.entities.map(e => ({ ...e, verified: true }));
    setSelectedDoc({ ...selectedDoc, entities: updatedEntities });
    
    if (selectedDoc.document_id) {
      onEntitiesUpdate?.(selectedDoc.document_id, updatedEntities);
    }
  };

  const handleAddEntity = () => {
    if (!selectedDoc) return;
    
    const newEntity: ExtractedEntity = {
      id: `manual-${Date.now()}`,
      type: "other",
      value: "",
      confidence: 1,
      verified: false,
    };
    
    setSelectedDoc({ ...selectedDoc, entities: [...selectedDoc.entities, newEntity] });
    setEditingEntity(newEntity.id);
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.9) return "text-emerald-600";
    if (confidence >= 0.7) return "text-amber-600";
    return "text-rose-600";
  };

  const getDocumentType = (metadata?: Record<string, unknown>): string => {
    const type = metadata?.instrument_type;
    if (typeof type === "string") {
      return type.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
    }
    return "Document";
  };

  const getOverallConfidence = (): number => {
    if (!selectedDoc?.entities.length) return 0;
    return selectedDoc.entities.reduce((acc, e) => acc + e.confidence, 0) / selectedDoc.entities.length;
  };

  const getVerifiedCount = (): number => {
    return selectedDoc?.entities.filter(e => e.verified).length || 0;
  };

  // ============================================================================
  // Render
  // ============================================================================

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-slate-200 bg-gradient-to-r from-cyan-50 to-blue-50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center">
              <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-slate-900">Document Extraction</h3>
              <p className="text-sm text-slate-500">Review and correct OCR-extracted entities</p>
            </div>
          </div>
          {selectedDoc && (
            <div className="flex items-center gap-4">
              <div className="text-right">
                <p className={`text-lg font-bold ${getConfidenceColor(getOverallConfidence())}`}>
                  {(getOverallConfidence() * 100).toFixed(0)}%
                </p>
                <p className="text-xs text-slate-500">Avg Confidence</p>
              </div>
              <div className="text-right">
                <p className="text-lg font-bold text-emerald-600">
                  {getVerifiedCount()}/{selectedDoc.entities.length}
                </p>
                <p className="text-xs text-slate-500">Verified</p>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="flex min-h-[500px]">
        {/* Document List */}
        <div className="w-1/3 border-r border-slate-200">
          <div className="p-3 border-b border-slate-100 bg-slate-50">
            <h4 className="text-sm font-medium text-slate-700">Documents ({documents.length})</h4>
          </div>
          <div className="overflow-y-auto max-h-[450px]">
            {loading ? (
              <div className="p-6 text-center text-slate-500">Loading...</div>
            ) : documents.length === 0 ? (
              <div className="p-6 text-center text-slate-500">
                <svg className="w-12 h-12 mx-auto mb-3 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <p className="text-sm">No documents found</p>
                <p className="text-xs text-slate-400 mt-1">Upload title instruments to extract entities</p>
              </div>
            ) : (
              documents.map(doc => {
                const hasOCR = !!doc.ocr_payload;
                const confidence = typeof doc.ocr_payload?.confidence === "number" 
                  ? doc.ocr_payload.confidence 
                  : null;
                const entityCount = Array.isArray(doc.ocr_payload?.entities) 
                  ? doc.ocr_payload.entities.length 
                  : 0;
                
                return (
                  <button
                    key={doc.id}
                    onClick={() => handleSelectDocument(doc)}
                    className={`w-full text-left p-4 border-b border-slate-100 hover:bg-slate-50 transition-colors ${
                      selectedDoc?.id === doc.id ? "bg-cyan-50 border-l-4 border-l-cyan-500" : ""
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <div className={`w-8 h-8 rounded flex items-center justify-center flex-shrink-0 ${
                        hasOCR ? "bg-cyan-100" : "bg-slate-100"
                      }`}>
                        <svg className={`w-4 h-4 ${hasOCR ? "text-cyan-600" : "text-slate-400"}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-slate-900 truncate">
                          {getDocumentType(doc.metadata)}
                        </p>
                        <div className="flex items-center gap-2 mt-1">
                          {hasOCR ? (
                            <>
                              {confidence !== null && (
                                <span className={`text-xs ${getConfidenceColor(confidence)}`}>
                                  {(confidence * 100).toFixed(0)}% confidence
                                </span>
                              )}
                              <span className="text-xs text-slate-400">
                                {entityCount} entities
                              </span>
                            </>
                          ) : (
                            <span className="text-xs text-slate-400">No OCR data</span>
                          )}
                        </div>
                      </div>
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </div>

        {/* Entity Editor */}
        <div className="flex-1 bg-slate-50">
          {selectedDoc ? (
            <div className="h-full flex flex-col">
              {/* Entity Header */}
              <div className="p-4 bg-white border-b border-slate-200 flex items-center justify-between">
                <div>
                  <h4 className="font-medium text-slate-900">{getDocumentType(selectedDoc.metadata)}</h4>
                  <p className="text-sm text-slate-500">{selectedDoc.entities.length} extracted entities</p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={handleAddEntity}
                    className="px-3 py-1.5 text-sm bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors"
                  >
                    + Add Entity
                  </button>
                  <button
                    onClick={handleVerifyAll}
                    className="px-3 py-1.5 text-sm bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors"
                  >
                    Verify All
                  </button>
                </div>
              </div>

              {/* Entity List */}
              <div className="flex-1 overflow-y-auto p-4 space-y-3">
                {selectedDoc.entities.length === 0 ? (
                  <div className="text-center py-8 text-slate-500">
                    <svg className="w-12 h-12 mx-auto mb-3 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                    </svg>
                    <p className="text-sm">No entities extracted</p>
                    <button
                      onClick={handleAddEntity}
                      className="mt-2 text-cyan-600 hover:underline text-sm"
                    >
                      Add manually
                    </button>
                  </div>
                ) : (
                  selectedDoc.entities.map(entity => {
                    const config = ENTITY_TYPE_CONFIG[entity.type];
                    const isEditing = editingEntity === entity.id;
                    
                    return (
                      <div
                        key={entity.id}
                        className={`p-4 bg-white rounded-lg border transition-colors ${
                          entity.verified 
                            ? "border-emerald-200 bg-emerald-50/30" 
                            : "border-slate-200 hover:border-slate-300"
                        }`}
                      >
                        <div className="flex items-start gap-3">
                          {/* Entity Type Icon */}
                          <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 border ${config.color}`}>
                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={config.icon} />
                            </svg>
                          </div>

                          {/* Entity Content */}
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              {isEditing ? (
                                <select
                                  value={entity.type}
                                  onChange={(e) => handleUpdateEntity(entity.id, { type: e.target.value as EntityType })}
                                  className="text-sm font-medium border border-slate-200 rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-cyan-500"
                                >
                                  {Object.entries(ENTITY_TYPE_CONFIG).map(([type, cfg]) => (
                                    <option key={type} value={type}>{cfg.label}</option>
                                  ))}
                                </select>
                              ) : (
                                <span className="text-sm font-medium text-slate-700">{config.label}</span>
                              )}
                              <span className={`text-xs ${getConfidenceColor(entity.confidence)}`}>
                                {(entity.confidence * 100).toFixed(0)}%
                              </span>
                              {entity.verified && (
                                <span className="text-xs px-2 py-0.5 bg-emerald-100 text-emerald-700 rounded-full">
                                  Verified
                                </span>
                              )}
                            </div>
                            
                            {isEditing ? (
                              <textarea
                                value={entity.value}
                                onChange={(e) => handleUpdateEntity(entity.id, { value: e.target.value })}
                                className="w-full text-sm border border-slate-200 rounded p-2 focus:outline-none focus:ring-2 focus:ring-cyan-500"
                                rows={entity.value.length > 50 ? 3 : 1}
                              />
                            ) : (
                              <p className="text-sm text-slate-900 break-words">{entity.value || "(empty)"}</p>
                            )}
                            
                            {entity.originalValue && entity.originalValue !== entity.value && (
                              <p className="text-xs text-slate-400 mt-1 line-through">
                                Original: {entity.originalValue}
                              </p>
                            )}
                          </div>

                          {/* Actions */}
                          <div className="flex items-center gap-1 flex-shrink-0">
                            {isEditing ? (
                              <button
                                onClick={() => setEditingEntity(null)}
                                className="px-2 py-1 text-xs bg-cyan-600 text-white rounded hover:bg-cyan-700 transition-colors"
                              >
                                Done
                              </button>
                            ) : (
                              <>
                                <button
                                  onClick={() => setEditingEntity(entity.id)}
                                  className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded transition-colors"
                                  title="Edit"
                                >
                                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                                  </svg>
                                </button>
                                {!entity.verified && (
                                  <button
                                    onClick={() => handleVerifyEntity(entity.id)}
                                    className="p-1.5 text-emerald-500 hover:text-emerald-700 hover:bg-emerald-50 rounded transition-colors"
                                    title="Verify"
                                  >
                                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                    </svg>
                                  </button>
                                )}
                                <button
                                  onClick={() => handleRejectEntity(entity.id)}
                                  className="p-1.5 text-rose-400 hover:text-rose-600 hover:bg-rose-50 rounded transition-colors"
                                  title="Remove"
                                >
                                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                  </svg>
                                </button>
                              </>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          ) : (
            <div className="h-full flex items-center justify-center text-slate-400">
              <div className="text-center">
                <svg className="w-16 h-16 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <p className="text-sm">Select a document to review entities</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {error && (
        <div className="px-6 py-3 bg-rose-50 border-t border-rose-200 text-sm text-rose-600">
          {error}
        </div>
      )}
    </div>
  );
}
