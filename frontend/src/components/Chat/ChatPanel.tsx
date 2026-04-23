import { useState, useRef, useEffect, useCallback } from 'react';
import { Send, Sparkles } from 'lucide-react';
import MessageBubble from './MessageBubble';
import type { ChatMessage, FeedbackType } from '../../types';
import { submitQuery, submitFeedback } from '../../services/api';

// ─── Demo Conversations ──────────────────────────────────────────────────────

const DEMO_RESPONSES: Record<string, { content: string; sources: string[]; suggestions: string[] }> = {
  'compare leverage for eqix and dlr': {
    content: `Here is the leverage comparison (Debt/EBITDA) for Equinix and Digital Realty over the last 4 quarters:

| Issuer | Q1-2024 | Q2-2024 | Q3-2024 | Q4-2024 | Trend |
|--------|---------|---------|---------|---------|-------|
| **EQIX** | 5.4x | 5.3x | 5.2x | 5.1x | ↓ Improving |
| **DLR** | 6.1x | 6.3x | 6.2x | 6.0x | → Stable |

**Key Observations:**
- **Equinix** has been consistently deleveraging, reducing Debt/EBITDA by 0.3x over the past year. Current leverage of 5.1x is well within the A3 rating category threshold.
- **Digital Realty** remains range-bound at ~6.0–6.3x, consistent with Baa2 positioning. The slight improvement in Q4 reflects proceeds from JV asset sales.
- The spread between the two has widened from 0.7x to 0.9x, reflecting Equinix's superior free cash flow generation.`,
    sources: ["Source: Moody's CreditView, as of 2025-01-15"],
    suggestions: ['Add CoreWeave and show FFO/Debt too', 'Show this as a chart', 'What drives the difference in leverage?'],
  },
  'show esg profile for switch': {
    content: `## ESG Profile — Switch Inc. (SWCH)

| Metric | Value | Sector Avg | Rating |
|--------|-------|-----------|--------|
| **PUE** | 1.18 | 1.35 | ⭐ Best-in-class |
| **Renewable Energy** | 100% | 62% | ⭐ Best-in-class |
| **Carbon Intensity** | 105 kg CO₂e/MWh | 285 | ⭐ Best-in-class |
| **Water Usage** | 0.9 L/kWh | 1.3 | ⭐ Above average |
| **Climate Risk Score** | 88/100 | 68 | ⭐ Strong |
| **Green Bonds Outstanding** | $1.2B | $1.4B | Moderate |

**Analysis:**
Switch operates the most energy-efficient data center fleet in our coverage universe, achieving a PUE of 1.18 through its proprietary cooling technology. The company runs on **100% renewable energy** via long-term PPAs in Nevada.

Despite its **B1 speculative-grade rating**, Switch's ESG profile is investment-grade quality, creating a potential catalyst for rating upgrade if financial metrics improve.

> *"Switch's ESG commitment is a structural competitive advantage in an industry increasingly scrutinized for energy consumption."* — Moody's ESG Credit Impact Assessment`,
    sources: ["Source: Moody's ESG Solutions, as of 2024-H2", "Source: Switch Inc. 2024 Sustainability Report"],
    suggestions: ['Compare Switch ESG to Equinix', 'How does PUE affect credit rating?', 'Show all operators by climate risk score'],
  },
  'what is the market outlook for northern virginia': {
    content: `## Market Outlook — Northern Virginia (N. Virginia / Ashburn)

### Key Metrics

| Metric | Current | YoY Change |
|--------|---------|------------|
| **Total Capacity** | 2,850 MW | +18% |
| **Vacancy Rate** | 3.0% | -1.2 pp |
| **Absorption (TTM)** | 410 MW | +24% |
| **Avg Price** | $120/kW/mo | +8% |
| **Construction Pipeline** | 680 MW | +35% |

### Market Dynamics

**Demand:** Northern Virginia remains the **world's largest and most active** data center market. Hyperscaler demand from AWS, Microsoft Azure, and Google Cloud continues to drive record absorption. AI/ML workloads are accelerating demand for high-density deployments (40+ kW/rack).

**Supply:** The 680 MW construction pipeline represents the highest ever recorded, but **power availability is the binding constraint**. Dominion Energy has flagged 2-3 year lead times for new substation capacity in Loudoun County.

**Pricing:** Rental rates have increased ~8% YoY to $120/kW/month, reversing a decade-long decline. Power scarcity is shifting landlord-tenant dynamics in favor of operators with existing utility commitments.

**Risk Factors:**
- ⚠️ Power grid constraints may limit near-term supply additions
- ⚠️ Regulatory scrutiny on land use and noise in residential-adjacent areas
- ✅ Strong demand fundamentals with multi-year visibility
- ✅ Institutional capital deepening the market (Blackstone, KKR, Brookfield)`,
    sources: ["Source: Moody's CreditView Market Analytics, as of 2025-01", "Source: CBRE North America Data Center Report H2-2024"],
    suggestions: ['Compare N. Virginia to Dallas/Ft Worth', 'Which operators have the most capacity in N.VA?', 'Show supply/demand chart for top 5 markets'],
  },
};

function findDemoResponse(input: string): { content: string; sources: string[]; suggestions: string[] } | null {
  const lower = input.toLowerCase().trim();
  for (const [key, val] of Object.entries(DEMO_RESPONSES)) {
    if (lower.includes(key) || key.includes(lower)) return val;
  }
  // Partial matches
  if (lower.includes('leverage') && (lower.includes('eqix') || lower.includes('dlr') || lower.includes('equinix') || lower.includes('digital realty'))) {
    return DEMO_RESPONSES['compare leverage for eqix and dlr'];
  }
  if (lower.includes('esg') && lower.includes('switch')) {
    return DEMO_RESPONSES['show esg profile for switch'];
  }
  if (lower.includes('northern virginia') || lower.includes('n. virginia') || lower.includes('nova') || (lower.includes('market') && lower.includes('virginia'))) {
    return DEMO_RESPONSES['what is the market outlook for northern virginia'];
  }
  return null;
}

const WELCOME_MESSAGE: ChatMessage = {
  id: 'welcome',
  role: 'assistant',
  content: `Welcome to the **Data Center Investments Agent**. I can help you analyze credit ratings, financial metrics, market dynamics, and ESG profiles across the data center sector.

Here are some things you can ask me:`,
  timestamp: new Date().toISOString(),
  suggestions: [
    'Compare leverage for EQIX and DLR',
    'Show ESG profile for Switch',
    'What is the market outlook for Northern Virginia?',
  ],
};

const FALLBACK_RESPONSE = {
  content: `I understand your question. Let me search across our data sources for the most relevant information.

> **Note:** This is a demo environment. In production, this query would be routed through the multi-agent system — the Supervisor Agent would delegate to the appropriate specialist sub-agent (Credit, Financial, Market, or ESG) which would access Moody's CreditView data via Workato pipelines.

For the best demo experience, try one of these queries:
- "Compare leverage for EQIX and DLR"
- "Show ESG profile for Switch"
- "What is the market outlook for Northern Virginia?"`,
  sources: ['Source: Demo Environment — Mock Data'],
  suggestions: [
    'Compare leverage for EQIX and DLR',
    'Show ESG profile for Switch',
    'What is the market outlook for Northern Virginia?',
  ],
};

// ─── Component ───────────────────────────────────────────────────────────────

export default function ChatPanel() {
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME_MESSAGE]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [sessionId] = useState(() => `sess-${Date.now()}`);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping, scrollToBottom]);

  const handleSend = useCallback(
    async (text?: string) => {
      const query = (text ?? input).trim();
      if (!query || isTyping) return;

      const userMsg: ChatMessage = {
        id: `msg-${Date.now()}`,
        role: 'user',
        content: query,
        timestamp: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, userMsg]);
      setInput('');
      setIsTyping(true);

      // Try real API first, fall back to demo data
      let responseData: { content: string; sources: string[]; suggestions: string[] };
      let traceId = `tr-${Date.now()}`;

      try {
        const apiRes = await submitQuery(sessionId, query);
        const text = apiRes.message || apiRes.response || '';
        if (!text) throw new Error('Empty response');
        responseData = {
          content: text,
          sources: apiRes.sources ?? (apiRes.source ? [`Source: ${apiRes.source}`] : []),
          suggestions: apiRes.suggestions ?? [
            'Compare leverage for EQIX and DLR',
            'Show ESG profile for Switch',
            'What is the market outlook for Northern Virginia?',
          ],
        };
        traceId = apiRes.trace_id ?? `tr-${Date.now()}`;
      } catch {
        // API unavailable — use demo data
        await new Promise((r) => setTimeout(r, 800 + Math.random() * 1200));
        responseData = findDemoResponse(query) ?? FALLBACK_RESPONSE;
      }

      const assistantMsg: ChatMessage = {
        id: `msg-${Date.now()}-resp`,
        role: 'assistant',
        content: responseData.content,
        timestamp: new Date().toISOString(),
        sources: responseData.sources,
        suggestions: responseData.suggestions,
        feedback: null,
        traceId,
      };

      setMessages((prev) => [...prev, assistantMsg]);
      setIsTyping(false);
    },
    [input, isTyping, sessionId]
  );

  const handleFeedback = useCallback(
    (msgId: string, type: FeedbackType) => {
      setMessages((prev) =>
        prev.map((m) => (m.id === msgId ? { ...m, feedback: type } : m))
      );
      const msg = messages.find((m) => m.id === msgId);
      if (msg?.traceId) {
        submitFeedback(msg.traceId, type).catch(() => {});
      }
    },
    [messages]
  );

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <header className="h-14 flex items-center justify-between px-6 border-b border-terminal-border bg-terminal-surface/50 backdrop-blur-sm flex-shrink-0">
        <div className="flex items-center gap-3">
          <Sparkles className="w-5 h-5 text-blue-400" />
          <h1 className="text-sm font-semibold text-slate-200">DC Investments Agent</h1>
          <span className="text-xs text-slate-600 hidden sm:inline">|</span>
          <span className="text-xs text-slate-500 hidden sm:inline">Powered by AWS Bedrock Agents</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-600 font-mono">{sessionId}</span>
        </div>
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-6 space-y-6">
        {messages.map((msg) => (
          <MessageBubble
            key={msg.id}
            message={msg}
            onFeedback={msg.role === 'assistant' ? (type) => handleFeedback(msg.id, type) : undefined}
            onSuggestionClick={(s) => handleSend(s)}
          />
        ))}

        {/* Typing Indicator */}
        {isTyping && (
          <div className="flex gap-3 animate-fade-in">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/15 flex items-center justify-center flex-shrink-0">
              <div className="flex gap-1">
                <span className="typing-dot w-1.5 h-1.5 bg-emerald-400 rounded-full" />
                <span className="typing-dot w-1.5 h-1.5 bg-emerald-400 rounded-full" />
                <span className="typing-dot w-1.5 h-1.5 bg-emerald-400 rounded-full" />
              </div>
            </div>
            <div className="bg-terminal-surface border border-terminal-border rounded-xl px-4 py-3">
              <p className="text-sm text-slate-500">Analyzing across Moody's data sources...</p>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="flex-shrink-0 border-t border-terminal-border bg-terminal-surface/50 backdrop-blur-sm p-4">
        <div className="max-w-4xl mx-auto flex gap-3">
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about credit ratings, leverage, ESG, or market outlook..."
              rows={1}
              className="w-full bg-terminal-card border border-terminal-border rounded-xl px-4 py-3 pr-12 text-sm text-slate-200 placeholder-slate-600 resize-none focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/25 transition-colors"
            />
          </div>
          <button
            onClick={() => handleSend()}
            disabled={!input.trim() || isTyping}
            className="h-[46px] w-[46px] flex items-center justify-center bg-blue-500 hover:bg-blue-600 disabled:bg-slate-700 disabled:text-slate-500 text-white rounded-xl transition-colors flex-shrink-0"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
        <p className="text-center text-[10px] text-slate-600 mt-2">
          Responses cite Moody's data sources. Always verify critical investment decisions with primary sources.
        </p>
      </div>
    </div>
  );
}
