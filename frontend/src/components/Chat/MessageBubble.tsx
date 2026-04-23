import ReactMarkdown from 'react-markdown';
import { Bot, User } from 'lucide-react';
import FeedbackButtons from './FeedbackButtons';
import type { ChatMessage, FeedbackType } from '../../types';

interface MessageBubbleProps {
  message: ChatMessage;
  onFeedback?: (type: FeedbackType) => void;
  onSuggestionClick?: (suggestion: string) => void;
}

export default function MessageBubble({ message, onFeedback, onSuggestionClick }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';

  if (isSystem) {
    return (
      <div className="flex justify-center my-2 animate-fade-in">
        <span className="text-xs text-slate-600 bg-terminal-surface px-3 py-1 rounded-full">
          {message.content}
        </span>
      </div>
    );
  }

  return (
    <div className={`flex gap-3 animate-fade-in ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <div
        className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
          isUser ? 'bg-blue-500/20' : 'bg-emerald-500/15'
        }`}
      >
        {isUser ? (
          <User className="w-4 h-4 text-blue-400" />
        ) : (
          <Bot className="w-4 h-4 text-emerald-400" />
        )}
      </div>

      {/* Content */}
      <div className={`flex-1 max-w-[85%] ${isUser ? 'flex flex-col items-end' : ''}`}>
        <div
          className={`rounded-xl px-4 py-3 ${
            isUser
              ? 'bg-blue-500/15 border border-blue-500/20 text-slate-200'
              : 'bg-terminal-surface border border-terminal-border text-slate-200'
          }`}
        >
          {isUser ? (
            <p className="text-sm">{message.content}</p>
          ) : (
            <div className="markdown-body">
              <ReactMarkdown>{message.content}</ReactMarkdown>
            </div>
          )}
        </div>

        {/* Source Attribution */}
        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="mt-1.5 px-1">
            {message.sources.map((src, i) => (
              <p key={i} className="text-xs text-slate-500 italic">
                {src}
              </p>
            ))}
          </div>
        )}

        {/* Feedback + Timestamp */}
        {!isUser && (
          <div className="flex items-center gap-3 mt-1.5 px-1">
            {onFeedback && (
              <FeedbackButtons current={message.feedback ?? null} onFeedback={onFeedback} />
            )}
            <span className="text-[10px] text-slate-600">
              {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
          </div>
        )}

        {/* Follow-up Suggestions */}
        {!isUser && message.suggestions && message.suggestions.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-3 px-1">
            {message.suggestions.map((s, i) => (
              <button
                key={i}
                onClick={() => onSuggestionClick?.(s)}
                className="text-xs text-blue-400 bg-blue-500/10 border border-blue-500/20 rounded-lg px-3 py-1.5 hover:bg-blue-500/20 transition-colors"
              >
                {s}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
