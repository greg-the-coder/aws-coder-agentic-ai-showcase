import { ThumbsUp, ThumbsDown } from 'lucide-react';
import type { FeedbackType } from '../../types';

interface FeedbackButtonsProps {
  current: FeedbackType | null | undefined;
  onFeedback: (type: FeedbackType) => void;
}

export default function FeedbackButtons({ current, onFeedback }: FeedbackButtonsProps) {
  return (
    <div className="flex items-center gap-1">
      <button
        onClick={() => onFeedback('up')}
        className={`p-1.5 rounded-md transition-colors ${
          current === 'up'
            ? 'bg-green-500/15 text-green-400'
            : 'text-slate-600 hover:text-slate-400 hover:bg-terminal-hover'
        }`}
        title="Helpful response"
      >
        <ThumbsUp className="w-3.5 h-3.5" />
      </button>
      <button
        onClick={() => onFeedback('down')}
        className={`p-1.5 rounded-md transition-colors ${
          current === 'down'
            ? 'bg-red-500/15 text-red-400'
            : 'text-slate-600 hover:text-slate-400 hover:bg-terminal-hover'
        }`}
        title="Not helpful"
      >
        <ThumbsDown className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}
