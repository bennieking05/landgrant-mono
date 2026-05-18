import type { ConversationListItem } from "@/lib/api";

type Props = {
  conversations: ConversationListItem[];
  loading: boolean;
  onSelect: (conversationId: string) => void;
  onNewConversation: () => void;
  onClose: () => void;
};

export function CopilotConversationHistory({
  conversations,
  loading,
  onSelect,
  onNewConversation,
  onClose,
}: Props) {
  return (
    <div className="absolute inset-0 top-[60px] bg-white z-20 flex flex-col">
      <div className="p-4 border-b border-slate-200 flex items-center justify-between">
        <h4 className="font-medium text-slate-900">Recent Conversations</h4>
        <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-4">
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <div className="flex gap-1">
              <span className="w-2 h-2 bg-brand rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
              <span className="w-2 h-2 bg-brand rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
              <span className="w-2 h-2 bg-brand rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
            </div>
          </div>
        ) : conversations.length === 0 ? (
          <div className="text-center py-8 text-slate-500">
            <svg className="w-12 h-12 mx-auto mb-3 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
            <p className="text-sm">No previous conversations</p>
            <p className="text-xs mt-1">Start a new conversation to see it here</p>
          </div>
        ) : (
          <div className="space-y-2">
            {conversations.map((conv) => (
              <button
                key={conv.conversation_id}
                onClick={() => onSelect(conv.conversation_id)}
                className="w-full text-left p-3 rounded-lg border border-slate-200 hover:border-brand hover:bg-brand/5 transition-colors"
              >
                <p className="text-sm text-slate-900 truncate">{conv.preview || "Empty conversation"}</p>
                <div className="flex items-center gap-2 mt-1 text-xs text-slate-500">
                  <span>{conv.message_count} messages</span>
                  <span>&bull;</span>
                  <span>{new Date(conv.last_updated).toLocaleDateString()}</span>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
      <div className="p-4 border-t border-slate-200">
        <button
          onClick={onNewConversation}
          className="w-full px-4 py-2 text-sm bg-brand text-white rounded-lg hover:bg-brand-dark transition-colors"
        >
          Start New Conversation
        </button>
      </div>
    </div>
  );
}
