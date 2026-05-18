import type { CopilotMessage } from "@/lib/api";

type Props = {
  message: CopilotMessage;
};

export function CopilotMessageBubble({ message }: Props) {
  return (
    <div className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-lg px-4 py-2.5 ${
          message.role === "user"
            ? "bg-brand text-white"
            : "bg-slate-100 text-slate-900"
        }`}
      >
        <p className="text-sm whitespace-pre-wrap">{message.content}</p>

        {message.citations && message.citations.length > 0 && (
          <div className="mt-2 pt-2 border-t border-slate-200/50">
            <p className="text-xs font-medium text-slate-500 mb-1">Citations:</p>
            <div className="flex flex-wrap gap-1">
              {message.citations.map((citation, j) => (
                <span
                  key={j}
                  className="text-xs px-2 py-0.5 bg-white/50 rounded text-slate-600"
                >
                  {citation}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
