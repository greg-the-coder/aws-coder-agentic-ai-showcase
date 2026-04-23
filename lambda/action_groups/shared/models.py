"""Data classes for Data Center Investments Agent.

Uses stdlib ``dataclasses`` (no Pydantic dependency).  Every model provides
``to_dict()`` and ``from_dict()`` helpers for DynamoDB round-tripping.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _convert_decimals(obj: Any) -> Any:
    """Recursively convert ``Decimal`` values to int/float for JSON safety."""
    from decimal import Decimal

    if isinstance(obj, Decimal):
        return int(obj) if obj == int(obj) else float(obj)
    if isinstance(obj, dict):
        return {k: _convert_decimals(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_convert_decimals(i) for i in obj]
    return obj


# ---------------------------------------------------------------------------
# 1.1 DataCenterOperator
# ---------------------------------------------------------------------------

@dataclass
class DataCenterOperator:
    id: str
    name: str
    ticker: Optional[str]
    moodys_rating: str
    sector: str
    hq: str
    market_cap: Optional[float]

    def to_dict(self) -> Dict[str, Any]:
        return _convert_decimals(asdict(self))

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DataCenterOperator:
        return cls(
            id=data["id"],
            name=data["name"],
            ticker=data.get("ticker"),
            moodys_rating=data["moodys_rating"],
            sector=data["sector"],
            hq=data["hq"],
            market_cap=float(data["market_cap"]) if data.get("market_cap") is not None else None,
        )


# ---------------------------------------------------------------------------
# 1.2 CreditRating
# ---------------------------------------------------------------------------

@dataclass
class CreditRating:
    operator_id: str
    rating: str
    outlook: str  # POS | NEG | STA | DEV
    watch_status: Optional[str]  # UPG | DNG | UNC | None
    rating_date: str  # ISO 8601
    previous_rating: Optional[str]
    analyst: str

    def to_dict(self) -> Dict[str, Any]:
        return _convert_decimals(asdict(self))

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CreditRating:
        return cls(
            operator_id=data["operator_id"],
            rating=data["rating"],
            outlook=data["outlook"],
            watch_status=data.get("watch_status"),
            rating_date=data["rating_date"],
            previous_rating=data.get("previous_rating"),
            analyst=data["analyst"],
        )


# ---------------------------------------------------------------------------
# 1.3 FinancialMetrics
# ---------------------------------------------------------------------------

@dataclass
class FinancialMetrics:
    operator_id: str
    period: str  # "2024-Q1" format
    revenue: float  # USD millions
    ebitda: float
    ffo: float
    debt_to_ebitda: float
    interest_coverage: float
    occupancy_rate: float  # 0.0–1.0
    capex: float
    liquidity: float

    def to_dict(self) -> Dict[str, Any]:
        return _convert_decimals(asdict(self))

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> FinancialMetrics:
        return cls(
            operator_id=data["operator_id"],
            period=data["period"],
            revenue=float(data["revenue"]),
            ebitda=float(data["ebitda"]),
            ffo=float(data["ffo"]),
            debt_to_ebitda=float(data["debt_to_ebitda"]),
            interest_coverage=float(data["interest_coverage"]),
            occupancy_rate=float(data["occupancy_rate"]),
            capex=float(data["capex"]),
            liquidity=float(data["liquidity"]),
        )


# ---------------------------------------------------------------------------
# 1.4 MarketData
# ---------------------------------------------------------------------------

@dataclass
class MarketData:
    market_id: str
    region: str  # NA | EMEA | APAC | LATAM
    market_name: str
    total_capacity_mw: float
    absorption_rate: float
    vacancy_rate: float  # 0.0–1.0
    avg_price_per_kw: float
    construction_pipeline_mw: float
    yoy_growth: float  # 0.0–1.0

    def to_dict(self) -> Dict[str, Any]:
        return _convert_decimals(asdict(self))

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MarketData:
        return cls(
            market_id=data["market_id"],
            region=data["region"],
            market_name=data["market_name"],
            total_capacity_mw=float(data["total_capacity_mw"]),
            absorption_rate=float(data["absorption_rate"]),
            vacancy_rate=float(data["vacancy_rate"]),
            avg_price_per_kw=float(data["avg_price_per_kw"]),
            construction_pipeline_mw=float(data["construction_pipeline_mw"]),
            yoy_growth=float(data["yoy_growth"]),
        )


# ---------------------------------------------------------------------------
# 1.5 ESGProfile
# ---------------------------------------------------------------------------

@dataclass
class ESGProfile:
    operator_id: str
    pue: float  # 1.0–3.0
    carbon_intensity: float  # kg CO₂e per MWh
    renewable_pct: float  # 0.0–1.0
    water_usage: float  # Liters per kWh
    climate_risk_score: float  # 0–100
    green_bond_outstanding: float  # USD millions

    def to_dict(self) -> Dict[str, Any]:
        return _convert_decimals(asdict(self))

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ESGProfile:
        return cls(
            operator_id=data["operator_id"],
            pue=float(data["pue"]),
            carbon_intensity=float(data["carbon_intensity"]),
            renewable_pct=float(data["renewable_pct"]),
            water_usage=float(data["water_usage"]),
            climate_risk_score=float(data["climate_risk_score"]),
            green_bond_outstanding=float(data["green_bond_outstanding"]),
        )


# ---------------------------------------------------------------------------
# 1.6 InvestmentRecommendation
# ---------------------------------------------------------------------------

@dataclass
class InvestmentRecommendation:
    operator_id: str
    action: str  # BUY | HOLD | SELL | MONITOR
    confidence: float  # 0.0–1.0
    rationale: str
    risk_factors: List[str] = field(default_factory=list)
    target_price: Optional[float] = None
    time_horizon: str = "12M"  # 3M | 6M | 12M | 24M

    def to_dict(self) -> Dict[str, Any]:
        return _convert_decimals(asdict(self))

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> InvestmentRecommendation:
        return cls(
            operator_id=data["operator_id"],
            action=data["action"],
            confidence=float(data["confidence"]),
            rationale=data["rationale"],
            risk_factors=data.get("risk_factors", []),
            target_price=float(data["target_price"]) if data.get("target_price") is not None else None,
            time_horizon=data.get("time_horizon", "12M"),
        )


# ---------------------------------------------------------------------------
# 1.7 ConversationSession
# ---------------------------------------------------------------------------

@dataclass
class MessageEntry:
    role: str  # user | assistant | system
    content: str
    ts: str  # ISO 8601

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MessageEntry:
        return cls(role=data["role"], content=data["content"], ts=data["ts"])


@dataclass
class ConversationSession:
    session_id: str
    user_id: str
    agent_id: str
    messages: List[MessageEntry] = field(default_factory=list)
    created_at: str = ""
    metadata: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["messages"] = [m.to_dict() if isinstance(m, MessageEntry) else m for m in self.messages]
        return _convert_decimals(d)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ConversationSession:
        return cls(
            session_id=data["session_id"],
            user_id=data.get("user_id", ""),
            agent_id=data.get("agent_id", ""),
            messages=[MessageEntry.from_dict(m) for m in data.get("messages", [])],
            created_at=data.get("created_at", ""),
            metadata=data.get("metadata", {}),
        )


# ---------------------------------------------------------------------------
# 1.8 AgentTrace
# ---------------------------------------------------------------------------

@dataclass
class AgentTrace:
    trace_id: str
    session_id: str
    agent_name: str
    action: str
    input: Dict[str, Any] = field(default_factory=dict)
    output: Dict[str, Any] = field(default_factory=dict)
    latency_ms: float = 0.0
    token_count: int = 0
    cost_usd: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # Store nested dicts as JSON strings for DynamoDB compatibility
        d["input"] = json.dumps(d["input"]) if isinstance(d["input"], dict) else str(d["input"])
        d["output"] = json.dumps(d["output"]) if isinstance(d["output"], dict) else str(d["output"])
        d["cost_usd"] = str(d["cost_usd"])
        return _convert_decimals(d)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AgentTrace:
        raw_input = data.get("input", {})
        raw_output = data.get("output", {})
        return cls(
            trace_id=data["trace_id"],
            session_id=data.get("session_id", ""),
            agent_name=data["agent_name"],
            action=data["action"],
            input=json.loads(raw_input) if isinstance(raw_input, str) else raw_input,
            output=json.loads(raw_output) if isinstance(raw_output, str) else raw_output,
            latency_ms=float(data.get("latency_ms", 0)),
            token_count=int(data.get("token_count", 0)),
            cost_usd=float(data.get("cost_usd", 0)),
        )
