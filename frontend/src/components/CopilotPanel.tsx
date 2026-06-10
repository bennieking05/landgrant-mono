import { useState, useRef, useEffect, useCallback } from "react";
import {
  askCopilot,
  copilotSummarizeCase,
  copilotDraftResponse,
  copilotExplainRequirement,
  listCopilotConversations,
  getCopilotConversation,
  getApiAuth,
  type CopilotMessage,
  type ConversationListItem,
} from "@/lib/api";
import { CopilotMessageBubble } from "./copilot/CopilotMessageBubble";
import { CopilotConversationHistory } from "./copilot/CopilotConversationHistory";
import { DraftResponseModal, ExplainRequirementModal } from "./copilot/CopilotQuickActionModals";
import { readSSEStream } from "@/lib/sse";

type Props = {
  caseId?: string;
  parcelId?: string;
  jurisdiction?: string;
  isOpen?: boolean;
  onClose?: () => void;
};

type QuickActionType = "summarize" | "draft" | "explain" | null;
type DraftResponseType = "counter_offer" | "acceptance" | "rejection";

type StreamMessage = {
  type: "conversation_id" | "citations" | "chunk" | "done" | "error";
  conversation_id?: string;
  citations?: string[];
  content?: string;
  error?: string;
};

export function CopilotPanel({
  caseId,
  parcelId,
  jurisdiction,
  isOpen = true,
  onClose,
}: Props) {
  const [messages, setMessages] = useState<CopilotMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [currentCitations, setCurrentCitations] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  
  // Quick action state
  const [activeQuickAction, setActiveQuickAction] = useState<QuickActionType>(null);
  const [draftType, setDraftType] = useState<DraftResponseType>("counter_offer");
  const [draftNotes, setDraftNotes] = useState("");
  const [explainRequirement, setExplainRequirement] = useState("");
  
  // Conversation history state
  const [showHistory, setShowHistory] = useState(false);
  const [conversationHistory, setConversationHistory] = useState<ConversationListItem[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent]);

  // Focus input when panel opens
  useEffect(() => {
    if (isOpen) {
      inputRef.current?.focus();
    }
  }, [isOpen]);

  const handleStreamingAsk = useCallback(async (question: string) => {
    setLoading(true);
    setError(null);
    setIsStreaming(true);
    setStreamingContent("");
    setCurrentCitations([]);

    // Add user message
    const userMessage: CopilotMessage = {
      role: "user",
      content: question,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);

    const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8050";
    
    try {
      abortControllerRef.current = new AbortController();
      
      const { token } = getApiAuth();
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }
      const response = await fetch(`${API_BASE}/copilot/ask`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          question,
          case_id: caseId,
          parcel_id: parcelId,
          jurisdiction,
          conversation_id: conversationId,
          conversation_history: messages.map((m) => ({
            role: m.role,
            content: m.content,
          })),
          stream: true,
        }),
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) {
        // Try to parse server error message
        let errorMessage = `Request failed: ${response.status}`;
        try {
          const errorData = await response.json();
          errorMessage = errorData.detail || errorData.message || errorData.error || errorMessage;
        } catch {
          // Response wasn't JSON, use default message
        }
        throw new Error(errorMessage);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error("No response body");
      }

      let fullContent = "";
      let citations: string[] = [];

      for await (const event of readSSEStream(reader)) {
        let data: StreamMessage;
        try {
          data = JSON.parse(event.data) as StreamMessage;
        } catch {
          // Skip non-JSON comments / keepalives.
          continue;
        }

        switch (data.type) {
          case "conversation_id":
            if (data.conversation_id) {
              setConversationId(data.conversation_id);
            }
            break;
          case "citations":
            if (data.citations) {
              citations = data.citations;
              setCurrentCitations(data.citations);
            }
            break;
          case "chunk":
            if (data.content) {
              fullContent += data.content;
              setStreamingContent(fullContent);
            }
            break;
          case "done": {
            const assistantMessage: CopilotMessage = {
              role: "assistant",
              content: fullContent,
              timestamp: new Date().toISOString(),
              citations,
            };
            setMessages((prev) => [...prev, assistantMessage]);
            setStreamingContent("");
            break;
          }
          case "error":
            setError(data.error || "Unknown error");
            break;
        }
      }
    } catch (err) {
      if ((err as Error).name === "AbortError") {
        // User cancelled
      } else {
        setError(String(err));
      }
    } finally {
      setLoading(false);
      setIsStreaming(false);
      abortControllerRef.current = null;
    }
  }, [caseId, parcelId, jurisdiction, conversationId, messages]);

  const handleNonStreamingAsk = useCallback(async (question: string) => {
    setLoading(true);
    setError(null);

    // Add user message
    const userMessage: CopilotMessage = {
      role: "user",
      content: question,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);

    try {
      const response = await askCopilot({
        question,
        case_id: caseId,
        parcel_id: parcelId,
        jurisdiction,
        conversation_id: conversationId || undefined,
        conversation_history: messages.map((m) => ({
          role: m.role,
          content: m.content,
        })),
        stream: false,
      });

      setConversationId(response.conversation_id);
      
      const assistantMessage: CopilotMessage = {
        role: "assistant",
        content: response.answer,
        timestamp: new Date().toISOString(),
        citations: response.citations,
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }, [caseId, parcelId, jurisdiction, conversationId, messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const question = input.trim();
    if (!question || loading) return;

    setInput("");
    // Use streaming by default
    handleStreamingAsk(question);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleClearConversation = () => {
    setMessages([]);
    setConversationId(null);
    setCurrentCitations([]);
    setError(null);
  };

  const handleCancel = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
  };

  // Quick action handlers using dedicated API endpoints
  const handleSummarizeCase = useCallback(async () => {
    setLoading(true);
    setError(null);
    setActiveQuickAction(null);

    // Add user message
    const userMessage: CopilotMessage = {
      role: "user",
      content: "Summarize this case and provide next steps",
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);

    try {
      const response = await copilotSummarizeCase(caseId, parcelId, jurisdiction);
      setConversationId(response.conversation_id);
      
      const assistantMessage: CopilotMessage = {
        role: "assistant",
        content: response.answer,
        timestamp: new Date().toISOString(),
        citations: response.citations,
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }, [caseId, parcelId, jurisdiction]);

  const handleDraftResponse = useCallback(async () => {
    if (!parcelId) {
      setError("Parcel ID is required for drafting responses");
      return;
    }
    
    setLoading(true);
    setError(null);
    setActiveQuickAction(null);

    const typeLabel = draftType.replace("_", " ");
    const userMessage: CopilotMessage = {
      role: "user",
      content: `Draft a ${typeLabel} response${draftNotes ? `: ${draftNotes}` : ""}`,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);

    try {
      const response = await copilotDraftResponse(parcelId, draftType, jurisdiction, draftNotes || undefined);
      setConversationId(response.conversation_id);
      
      const assistantMessage: CopilotMessage = {
        role: "assistant",
        content: response.answer,
        timestamp: new Date().toISOString(),
        citations: response.citations,
      };
      setMessages((prev) => [...prev, assistantMessage]);
      setDraftNotes("");
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }, [parcelId, jurisdiction, draftType, draftNotes]);

  const handleExplainRequirement = useCallback(async () => {
    if (!explainRequirement.trim()) {
      setError("Please enter a requirement to explain");
      return;
    }
    if (!jurisdiction) {
      setError("Jurisdiction is required to explain requirements");
      return;
    }
    
    setLoading(true);
    setError(null);
    setActiveQuickAction(null);

    const userMessage: CopilotMessage = {
      role: "user",
      content: `Explain this requirement for ${jurisdiction}: ${explainRequirement}`,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);

    try {
      const response = await copilotExplainRequirement(explainRequirement, jurisdiction);
      setConversationId(response.conversation_id);
      
      const assistantMessage: CopilotMessage = {
        role: "assistant",
        content: response.answer,
        timestamp: new Date().toISOString(),
        citations: response.citations,
      };
      setMessages((prev) => [...prev, assistantMessage]);
      setExplainRequirement("");
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }, [explainRequirement, jurisdiction]);

  // Legacy quick actions (using streaming ask)
  const legacyQuickActions = [
    { label: "Check Deadlines", prompt: "What are the upcoming deadlines for this case and their statutory basis?" },
    { label: "Risk Analysis", prompt: "What are the potential risks or issues with this case that need attention?" },
  ];

  // Load conversation history
  const loadConversationHistory = useCallback(async () => {
    setLoadingHistory(true);
    try {
      const response = await listCopilotConversations(10);
      setConversationHistory(response.conversations);
    } catch (err) {
      console.error("Failed to load conversations:", err);
    } finally {
      setLoadingHistory(false);
    }
  }, []);

  // Load a specific conversation
  const loadConversation = useCallback(async (convId: string) => {
    setLoading(true);
    try {
      const response = await getCopilotConversation(convId);
      setMessages(response.messages);
      setConversationId(convId);
      setShowHistory(false);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }, []);

  // Toggle history view
  const handleToggleHistory = useCallback(() => {
    if (!showHistory) {
      loadConversationHistory();
    }
    setShowHistory(!showHistory);
  }, [showHistory, loadConversationHistory]);

  if (!isOpen) return null;

  return (
    <div className="flex flex-col h-full bg-white border-l border-slate-200 relative">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 bg-gradient-to-r from-brand/5 to-purple-50">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-brand to-purple-600 flex items-center justify-center">
            <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
          </div>
          <div>
            <h3 className="font-semibold text-slate-900">AI Copilot</h3>
            <p className="text-xs text-slate-500">Legal research assistant</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleToggleHistory}
            className={`text-xs px-2 py-1 rounded flex items-center gap-1 transition-colors ${
              showHistory 
                ? "bg-brand/10 text-brand" 
                : "text-slate-500 hover:text-slate-700 hover:bg-slate-100"
            }`}
            title="Conversation history"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            History
          </button>
          {messages.length > 0 && (
            <button
              onClick={handleClearConversation}
              className="text-xs text-slate-500 hover:text-slate-700 px-2 py-1 rounded hover:bg-slate-100"
            >
              Clear
            </button>
          )}
          {onClose && (
            <button
              onClick={onClose}
              className="text-slate-400 hover:text-slate-600 p-1 rounded hover:bg-slate-100"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>
      </div>

      {/* Context indicator */}
      {(caseId || parcelId || jurisdiction) && (
        <div className="px-4 py-2 bg-slate-50 border-b border-slate-200 flex flex-wrap gap-2 text-xs">
          {jurisdiction && (
            <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full">
              {jurisdiction}
            </span>
          )}
          {parcelId && (
            <span className="px-2 py-0.5 bg-emerald-100 text-emerald-700 rounded-full">
              Parcel: {parcelId}
            </span>
          )}
          {caseId && (
            <span className="px-2 py-0.5 bg-purple-100 text-purple-700 rounded-full">
              Case: {caseId}
            </span>
          )}
        </div>
      )}

      {/* Quick Actions Bar (visible when messages exist) */}
      {messages.length > 0 && (
        <div className="px-4 py-2 bg-gradient-to-r from-slate-50 to-slate-100 border-b border-slate-200 flex gap-2 overflow-x-auto">
          <button
            onClick={handleSummarizeCase}
            disabled={loading}
            className="text-xs px-2.5 py-1 rounded-full bg-white border border-slate-200 text-slate-600 hover:border-brand hover:text-brand transition-colors whitespace-nowrap flex items-center gap-1 disabled:opacity-50"
          >
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            Summarize
          </button>
          <button
            onClick={() => setActiveQuickAction("draft")}
            disabled={loading || !parcelId}
            className="text-xs px-2.5 py-1 rounded-full bg-white border border-slate-200 text-slate-600 hover:border-emerald-500 hover:text-emerald-700 transition-colors whitespace-nowrap flex items-center gap-1 disabled:opacity-50"
          >
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
            Draft
          </button>
          <button
            onClick={() => setActiveQuickAction("explain")}
            disabled={loading || !jurisdiction}
            className="text-xs px-2.5 py-1 rounded-full bg-white border border-slate-200 text-slate-600 hover:border-purple-500 hover:text-purple-700 transition-colors whitespace-nowrap flex items-center gap-1 disabled:opacity-50"
          >
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Explain
          </button>
        </div>
      )}

      {showHistory && (
        <CopilotConversationHistory
          conversations={conversationHistory}
          loading={loadingHistory}
          onSelect={loadConversation}
          onNewConversation={() => { handleClearConversation(); setShowHistory(false); }}
          onClose={() => setShowHistory(false)}
        />
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && !isStreaming && !showHistory && (
          <div className="text-center py-8">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-br from-brand/10 to-purple-100 flex items-center justify-center">
              <svg className="w-8 h-8 text-brand" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
            </div>
            <h4 className="font-medium text-slate-900 mb-1">How can I help?</h4>
            <p className="text-sm text-slate-500 mb-4">
              Ask me about eminent domain law, case procedures, or deadlines.
            </p>
            
            {/* AI-Powered Quick Actions */}
            <div className="space-y-3">
              <p className="text-xs font-medium text-slate-400 uppercase tracking-wide">AI Quick Actions</p>
              <div className="flex flex-wrap justify-center gap-2">
                <button
                  onClick={handleSummarizeCase}
                  disabled={loading}
                  className="text-xs px-3 py-1.5 rounded-full bg-brand/10 border border-brand/30 text-brand hover:bg-brand/20 transition-colors flex items-center gap-1.5"
                >
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  Summarize Case
                </button>
                <button
                  onClick={() => setActiveQuickAction("draft")}
                  disabled={loading || !parcelId}
                  className="text-xs px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-700 hover:bg-emerald-500/20 transition-colors disabled:opacity-50 flex items-center gap-1.5"
                >
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                  Draft Response
                </button>
                <button
                  onClick={() => setActiveQuickAction("explain")}
                  disabled={loading || !jurisdiction}
                  className="text-xs px-3 py-1.5 rounded-full bg-purple-500/10 border border-purple-500/30 text-purple-700 hover:bg-purple-500/20 transition-colors disabled:opacity-50 flex items-center gap-1.5"
                >
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Explain Requirement
                </button>
              </div>

              {/* Additional quick prompts */}
              <div className="pt-2">
                <p className="text-xs font-medium text-slate-400 uppercase tracking-wide mb-2">Quick Questions</p>
                <div className="flex flex-wrap justify-center gap-2">
                  {legacyQuickActions.map((action, i) => (
                    <button
                      key={i}
                      onClick={() => handleStreamingAsk(action.prompt)}
                      className="text-xs px-3 py-1.5 rounded-full border border-slate-200 text-slate-600 hover:bg-slate-50 hover:border-brand hover:text-brand transition-colors"
                    >
                      {action.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {activeQuickAction === "draft" && (
          <DraftResponseModal
            draftType={draftType}
            draftNotes={draftNotes}
            onDraftTypeChange={setDraftType}
            onNotesChange={setDraftNotes}
            onSubmit={handleDraftResponse}
            onCancel={() => setActiveQuickAction(null)}
          />
        )}

        {activeQuickAction === "explain" && (
          <ExplainRequirementModal
            requirement={explainRequirement}
            jurisdiction={jurisdiction}
            onRequirementChange={setExplainRequirement}
            onSubmit={handleExplainRequirement}
            onCancel={() => setActiveQuickAction(null)}
          />
        )}

        {messages.map((msg, i) => (
          <CopilotMessageBubble key={i} message={msg} />
        ))}

        {/* Streaming content */}
        {isStreaming && streamingContent && (
          <div className="flex justify-start">
            <div className="max-w-[85%] rounded-lg px-4 py-2.5 bg-slate-100 text-slate-900">
              <p className="text-sm whitespace-pre-wrap">{streamingContent}</p>
              <span className="inline-block w-2 h-4 ml-1 bg-brand animate-pulse" />
            </div>
          </div>
        )}

        {/* Loading indicator */}
        {loading && !streamingContent && (
          <div className="flex justify-start">
            <div className="rounded-lg px-4 py-2.5 bg-slate-100">
              <div className="flex items-center gap-2">
                <div className="flex gap-1">
                  <span className="w-2 h-2 bg-brand rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                  <span className="w-2 h-2 bg-brand rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                  <span className="w-2 h-2 bg-brand rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                </div>
                <span className="text-xs text-slate-500">Thinking...</span>
                <button
                  onClick={handleCancel}
                  className="text-xs text-rose-500 hover:text-rose-700 ml-2"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="flex justify-center">
            <div className="text-sm text-rose-600 bg-rose-50 px-4 py-2 rounded-lg">
              {error}
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Current citations */}
      {currentCitations.length > 0 && isStreaming && (
        <div className="px-4 py-2 bg-amber-50 border-t border-amber-100">
          <p className="text-xs font-medium text-amber-700 mb-1">Referencing:</p>
          <div className="flex flex-wrap gap-1">
            {currentCitations.map((citation, i) => (
              <span key={i} className="text-xs px-2 py-0.5 bg-amber-100 rounded text-amber-800">
                {citation}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-4 border-t border-slate-200 bg-slate-50">
        <div className="flex gap-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question..."
            rows={1}
            className="flex-1 px-3 py-2 text-sm border border-slate-200 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="px-4 py-2 bg-brand text-white rounded-lg hover:bg-brand-dark disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>
        </div>
        <p className="text-xs text-slate-400 mt-2 text-center">
          AI responses require attorney review. Not legal advice.
        </p>
      </form>
    </div>
  );
}
