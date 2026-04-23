# Data Center Investments Agent — Data Model Specification

**Version:** 1.0.0
**Author:** Platform Engineering
**Status:** Draft

---

## 1. Core Type Definitions

### 1.1 DataCenterOperator
```typescript
interface DataCenterOperator {
  id: string;                // UUID v4
  name: string;              // Legal entity name
  ticker: string | null;     // NYSE/NASDAQ ticker, null if private
  moodys_rating: string;     // e.g. "A3", "Baa2", "WR"
  sector: string;            // Moody's sector classification
  hq: string;                // HQ country code (ISO 3166-1)
  market_cap: number | null; // USD millions, null if private
}
```

### 1.2 CreditRating
```typescript
interface CreditRating {
  operator_id: string;
  rating: string;                              // Moody's long-term issuer rating
  outlook: "POS" | "NEG" | "STA" | "DEV";
  watch_status: "UPG" | "DNG" | "UNC" | null;
  rating_date: string;                         // ISO 8601
  previous_rating: string | null;
  analyst: string;
}
```

### 1.3 FinancialMetrics
```typescript
interface FinancialMetrics {
  operator_id: string;
  period: string;            // "2024-Q1" format
  revenue: number;           // USD millions
  ebitda: number;            // USD millions
  ffo: number;               // Funds from operations, USD millions
  debt_to_ebitda: number;    // Leverage ratio
  interest_coverage: number; // EBITDA / interest expense
  occupancy_rate: number;    // 0.0–1.0
  capex: number;             // USD millions
  liquidity: number;         // USD millions (cash + revolver)
}
```

### 1.4 MarketData
```typescript
interface MarketData {
  market_id: string;
  region: "NA" | "EMEA" | "APAC" | "LATAM";
  market_name: string;
  total_capacity_mw: number;
  absorption_rate: number;        // MW absorbed trailing 12 months
  vacancy_rate: number;           // 0.0–1.0
  avg_price_per_kw: number;       // USD per kW/month
  construction_pipeline_mw: number;
  yoy_growth: number;             // YoY capacity growth, 0.0–1.0
}
```

### 1.5 ESGProfile
```typescript
interface ESGProfile {
  operator_id: string;
  pue: number;                    // Power Usage Effectiveness, 1.0–3.0
  carbon_intensity: number;       // kg CO₂e per MWh
  renewable_pct: number;          // 0.0–1.0
  water_usage: number;            // Liters per kWh
  climate_risk_score: number;     // Moody's ESG score 0–100
  green_bond_outstanding: number; // USD millions
}
```

### 1.6 InvestmentRecommendation
```typescript
interface InvestmentRecommendation {
  operator_id: string;
  action: "BUY" | "HOLD" | "SELL" | "MONITOR";
  confidence: number;             // 0.0–1.0
  rationale: string;
  risk_factors: string[];
  target_price: number | null;    // USD, null if private
  time_horizon: "3M" | "6M" | "12M" | "24M";
}
```

### 1.7 ConversationSession
```typescript
interface ConversationSession {
  session_id: string;
  user_id: string;
  agent_id: string;
  messages: { role: "user" | "assistant" | "system"; content: string; ts: string }[];
  created_at: string; // ISO 8601
  metadata: Record<string, string>;
}
```

### 1.8 AgentTrace
```typescript
interface AgentTrace {
  trace_id: string;
  session_id: string;
  agent_name: string;
  action: string;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  latency_ms: number;
  token_count: number;
  cost_usd: number;
}
```

---

## 2. Mock Data

### 2.1 Operators
```json
[
  { "id": "op-001", "name": "Equinix Inc.",        "ticker": "EQIX", "moodys_rating": "A3",   "sector": "Data Center REIT", "hq": "US", "market_cap": 74200 },
  { "id": "op-002", "name": "Digital Realty Trust", "ticker": "DLR",  "moodys_rating": "Baa2", "sector": "Data Center REIT", "hq": "US", "market_cap": 38500 },
  { "id": "op-003", "name": "QTS Realty Trust",     "ticker": null,   "moodys_rating": "Ba2",  "sector": "Data Center",      "hq": "US", "market_cap": null  },
  { "id": "op-004", "name": "CyrusOne LLC",         "ticker": null,   "moodys_rating": "Ba3",  "sector": "Data Center",      "hq": "US", "market_cap": null  },
  { "id": "op-005", "name": "CoreSite Realty",      "ticker": "COR",  "moodys_rating": "Baa3", "sector": "Data Center REIT", "hq": "US", "market_cap": 8400  },
  { "id": "op-006", "name": "Switch Inc.",          "ticker": "SWCH", "moodys_rating": "B1",   "sector": "Data Center",      "hq": "US", "market_cap": 7900  }
]
```

### 2.2 Markets
```json
[
  { "market_id": "mkt-nova", "region": "NA",   "market_name": "Northern Virginia", "total_capacity_mw": 2850, "absorption_rate": 410, "vacancy_rate": 0.03, "avg_price_per_kw": 120, "construction_pipeline_mw": 680, "yoy_growth": 0.18 },
  { "market_id": "mkt-dfw",  "region": "NA",   "market_name": "Dallas / Ft Worth", "total_capacity_mw": 980,  "absorption_rate": 175, "vacancy_rate": 0.07, "avg_price_per_kw": 95,  "construction_pipeline_mw": 320, "yoy_growth": 0.22 },
  { "market_id": "mkt-phx",  "region": "NA",   "market_name": "Phoenix",           "total_capacity_mw": 620,  "absorption_rate": 130, "vacancy_rate": 0.05, "avg_price_per_kw": 88,  "construction_pipeline_mw": 275, "yoy_growth": 0.29 },
  { "market_id": "mkt-sin",  "region": "APAC", "market_name": "Singapore",         "total_capacity_mw": 410,  "absorption_rate": 55,  "vacancy_rate": 0.02, "avg_price_per_kw": 165, "construction_pipeline_mw": 80,  "yoy_growth": 0.08 },
  { "market_id": "mkt-fra",  "region": "EMEA", "market_name": "Frankfurt",         "total_capacity_mw": 730,  "absorption_rate": 95,  "vacancy_rate": 0.04, "avg_price_per_kw": 140, "construction_pipeline_mw": 210, "yoy_growth": 0.14 }
]
```

### 2.3 Financial Metrics (Q1 & Q2 2024 per operator)
```typescript
const metrics: FinancialMetrics[] = [
  { operator_id:"op-001", period:"2024-Q1", revenue:2012, ebitda:952, ffo:820, debt_to_ebitda:3.8, interest_coverage:5.1, occupancy_rate:0.92, capex:710, liquidity:4500 },
  { operator_id:"op-001", period:"2024-Q2", revenue:2085, ebitda:991, ffo:855, debt_to_ebitda:3.7, interest_coverage:5.3, occupancy_rate:0.93, capex:740, liquidity:4650 },
  { operator_id:"op-002", period:"2024-Q1", revenue:1350, ebitda:685, ffo:570, debt_to_ebitda:5.9, interest_coverage:3.4, occupancy_rate:0.85, capex:520, liquidity:2800 },
  { operator_id:"op-002", period:"2024-Q2", revenue:1385, ebitda:710, ffo:592, debt_to_ebitda:5.7, interest_coverage:3.5, occupancy_rate:0.86, capex:545, liquidity:2950 },
  { operator_id:"op-003", period:"2024-Q1", revenue:420,  ebitda:195, ffo:160, debt_to_ebitda:6.8, interest_coverage:2.6, occupancy_rate:0.88, capex:310, liquidity:900  },
  { operator_id:"op-003", period:"2024-Q2", revenue:445,  ebitda:210, ffo:172, debt_to_ebitda:6.5, interest_coverage:2.7, occupancy_rate:0.89, capex:325, liquidity:950  },
  { operator_id:"op-004", period:"2024-Q1", revenue:380,  ebitda:175, ffo:140, debt_to_ebitda:7.1, interest_coverage:2.3, occupancy_rate:0.82, capex:280, liquidity:650  },
  { operator_id:"op-004", period:"2024-Q2", revenue:395,  ebitda:184, ffo:148, debt_to_ebitda:6.9, interest_coverage:2.4, occupancy_rate:0.83, capex:295, liquidity:700  },
  { operator_id:"op-005", period:"2024-Q1", revenue:185,  ebitda:102, ffo:88,  debt_to_ebitda:4.2, interest_coverage:4.0, occupancy_rate:0.94, capex:95,  liquidity:520  },
  { operator_id:"op-005", period:"2024-Q2", revenue:192,  ebitda:107, ffo:92,  debt_to_ebitda:4.1, interest_coverage:4.1, occupancy_rate:0.95, capex:100, liquidity:545  },
  { operator_id:"op-006", period:"2024-Q1", revenue:165,  ebitda:78,  ffo:62,  debt_to_ebitda:5.5, interest_coverage:2.9, occupancy_rate:0.80, capex:220, liquidity:380  },
  { operator_id:"op-006", period:"2024-Q2", revenue:175,  ebitda:84,  ffo:67,  debt_to_ebitda:5.3, interest_coverage:3.0, occupancy_rate:0.81, capex:235, liquidity:410  },
];
```

### 2.4 ESG Profiles

```json
[
  { "operator_id": "op-001", "pue": 1.25, "carbon_intensity": 210, "renewable_pct": 0.96, "water_usage": 1.1, "climate_risk_score": 82, "green_bond_outstanding": 3750 },
  { "operator_id": "op-002", "pue": 1.35, "carbon_intensity": 290, "renewable_pct": 0.68, "water_usage": 1.4, "climate_risk_score": 71, "green_bond_outstanding": 2100 },
  { "operator_id": "op-003", "pue": 1.40, "carbon_intensity": 340, "renewable_pct": 0.52, "water_usage": 1.6, "climate_risk_score": 63, "green_bond_outstanding": 500  },
  { "operator_id": "op-004", "pue": 1.38, "carbon_intensity": 310, "renewable_pct": 0.45, "water_usage": 1.5, "climate_risk_score": 58, "green_bond_outstanding": 0    },
  { "operator_id": "op-005", "pue": 1.30, "carbon_intensity": 250, "renewable_pct": 0.72, "water_usage": 1.2, "climate_risk_score": 75, "green_bond_outstanding": 800  },
  { "operator_id": "op-006", "pue": 1.18, "carbon_intensity": 105, "renewable_pct": 1.00, "water_usage": 0.9, "climate_risk_score": 88, "green_bond_outstanding": 1200 }
]
```

---

## 3. Data Scenarios

| Operator | Rating | Scenario | Key Demonstration |
|---|---|---|---|
| Equinix | A3 | Investment-grade leader | Global diversification across 70+ markets; best-in-class PUE of 1.25; stable outlook with strong FFO |
| Digital Realty | Baa2 | Moderate leverage | Joint venture exposure via partnerships; elevated debt-to-EBITDA ~5.9x; deleveraging trajectory |
| QTS Realty | Ba2 | Acquisition scenario | Blackstone take-private; ticker set to `null`; high capex reflecting post-acquisition expansion |
| CyrusOne | Ba3 | Private equity transition | KKR/GIP ownership; highest leverage in dataset at 7.1x; occupancy recovery story |
| CoreSite | Baa3 | REIT with hyperscaler concentration | Top-3 tenant concentration >60% revenue; highest occupancy at 94-95%; limited geographic footprint |
| Switch | B1 | High renewable commitment | 100% renewable energy; lowest PUE (1.18); speculative-grade but strong ESG narrative |

---

## 4. Moody's CreditView API Field Mapping

| Moody's CreditView Field | Internal Field | Type | Notes |
|---|---|---|---|
| `orgId` | `DataCenterOperator.id` | string | Mapped via lookup table |
| `organizationName` | `DataCenterOperator.name` | string | Direct mapping |
| `ltRating` | `CreditRating.rating` | string | Long-term issuer rating |
| `ratingOutlook` | `CreditRating.outlook` | enum | Normalized to POS/NEG/STA/DEV |
| `watchListStatus` | `CreditRating.watch_status` | enum | null when not on watch |
| `ratingActionDate` | `CreditRating.rating_date` | string | Converted to ISO 8601 |
| `previousRating` | `CreditRating.previous_rating` | string | null for initial ratings |
| `leadAnalyst` | `CreditRating.analyst` | string | Full name |
| `esgCisScore` | `ESGProfile.climate_risk_score` | number | Moody's CIS 0–100 scale |
| `sectorCode` | `DataCenterOperator.sector` | string | Mapped from Moody's taxonomy |

---

## 5. DynamoDB Table Schemas

| Table | Partition Key (HASH) | Sort Key (RANGE) | GSI | TTL |
|---|---|---|---|---|
| `dcai-sessions` | `session_id` | — | `user-index`: `user_id` / `created_at` | `expires_at` |
| `dcai-operators` | `id` | — | `rating-index`: `moodys_rating` / `name` | — |
| `dcai-metrics` | `operator_id` | `period` | `period-index`: `period` / `operator_id` | — |

---

## 6. OpenSearch Index Mappings

```json
{
  "settings": {
    "index": { "knn": true, "knn.algo_param.ef_search": 512 }
  },
  "mappings": {
    "properties": {
      "embedding": {
        "type": "knn_vector",
        "dimension": 1536,
        "method": {
          "name": "hnsw",
          "space_type": "cosinesimil",
          "engine": "nmslib",
          "parameters": { "ef_construction": 512, "m": 16 }
        }
      },
      "text":        { "type": "text",    "analyzer": "standard" },
      "source":      { "type": "keyword" },
      "operator_id": { "type": "keyword" },
      "doc_type":    { "type": "keyword" },
      "created_at":  { "type": "date", "format": "strict_date_optional_time" }
    }
  }
}
```

---

## 7. Data Validation Rules

| Field | Rule | Error Code |
|---|---|---|
| `moodys_rating` | Must match `Aaa\|Aa[1-3]\|A[1-3]\|Baa[1-3]\|Ba[1-3]\|B[1-3]\|Caa[1-3]\|Ca\|C\|WR\|NR` | `INVALID_RATING` |
| `pue` | Must be between 1.0 and 3.0 inclusive | `PUE_OUT_OF_RANGE` |
| `occupancy_rate` | Must be between 0.0 and 1.0 inclusive | `INVALID_OCCUPANCY` |
| `renewable_pct` | Must be between 0.0 and 1.0 inclusive | `INVALID_RENEWABLE_PCT` |
| `debt_to_ebitda` | Must be > 0 and < 20.0 | `LEVERAGE_OUT_OF_RANGE` |
| `period` | Must match format `YYYY-Q[1-4]` | `INVALID_PERIOD` |
| `outlook` | Must be one of POS, NEG, STA, DEV | `INVALID_OUTLOOK` |
| `confidence` | Must be between 0.0 and 1.0 inclusive | `INVALID_CONFIDENCE` |
| `market_cap` | Must be > 0 when not null | `INVALID_MARKET_CAP` |
| `vacancy_rate` | Must be between 0.0 and 1.0 inclusive | `INVALID_VACANCY` |

---

## 8. Data Freshness Requirements

| Data Category | Source | Refresh SLA | Staleness Threshold | Alert Channel |
|---|---|---|---|---|
| Credit Ratings | Moody's CreditView | Real-time (webhook) | 15 minutes | PagerDuty P1 |
| Rating Actions | Moody's CreditView | Real-time (webhook) | 15 minutes | PagerDuty P1 |
| Financial Metrics | SEC EDGAR / Operator IR | Quarterly (T+5 days) | 30 days post-filing | Slack #data-ops |
| Market Data | CBRE / JLL / Cushman | Monthly | 45 days | Slack #data-ops |
| ESG Profiles | Moody's ESG Solutions | Semi-annual | 180 days | Email digest |
| Operator Master Data | Internal + Moody's | On rating action | 24 hours | Slack #data-ops |
| Embeddings Index | Knowledge base rebuild | Weekly | 10 days | CloudWatch alarm |
