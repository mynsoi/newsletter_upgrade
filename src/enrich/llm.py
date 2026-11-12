"""enrich 단계 공통 — 모델 호출 결과(ModelReply)·비용 집계(CostState)·모델 단가.

관련성 판별(relevance.py)과 문서 카드(doc_cards.py·backfill_cards.py)가 같은 CostState에 비용을
쌓는다. 2026-11-10 claim 추출을 없애면서 extract_claims.py에 있던 것을 여기로 옮겼다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# $ / 1M 토큰 (input, output) — Anthropic 공식 요금표 기준(claude-api 스킬 캐시 2026-06-24).
# 여기 없는 모델로 --cost-cap을 걸면 상한을 신뢰할 수 없으므로 relevance.main()이 즉시 중단한다.
MODEL_PRICING: dict[str, tuple[float, float]] = {
    "claude-opus-5": (5.00, 25.00),
    "claude-sonnet-5-5": (2.00, 10.00),   # 문서 카드(card_model, doc_cards.py)
    "claude-sonnet-5": (2.00, 10.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-haiku-4-5": (1.00, 5.00),
}
_DATED_SUFFIX_RE = re.compile(r"-\d{8}$")


def _price_for(model: str) -> tuple[float, float] | None:
    """모델 ID(날짜 접미사 포함 가능)로 (입력가, 출력가)를 찾는다. 모르면 None."""
    if model in MODEL_PRICING:
        return MODEL_PRICING[model]
    return MODEL_PRICING.get(_DATED_SUFFIX_RE.sub("", model))


@dataclass
class ModelReply:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    truncated: bool = False   # stop_reason='max_tokens' — 응답이 상한에서 잘렸다


@dataclass
class CostState:
    """판별+카드 호출을 누적 집계 — 실측 비용을 --cost-cap과 비교하는 근거."""
    cap: float | None = None
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost: float = 0.0
    cap_hit: bool = False
    tier_counts: dict[str, int] = field(default_factory=dict)

    def record(self, model: str, reply: ModelReply) -> None:
        self.calls += 1
        self.input_tokens += reply.input_tokens
        self.output_tokens += reply.output_tokens
        price = _price_for(model)
        if price:
            self.cost += reply.input_tokens / 1_000_000 * price[0]
            self.cost += reply.output_tokens / 1_000_000 * price[1]

    def cap_reached(self) -> bool:
        return self.cap is not None and self.cost >= self.cap


def call_model(prompt: str, model: str, max_tokens: int) -> ModelReply:
    from ssl_compat import repair_truststore_injection
    repair_truststore_injection()  # 개발 PC의 SSL 주입 충돌(src/ssl_compat.py)
    import anthropic  # 지연 임포트 — dry-run 시 SDK 불필요
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    usage = getattr(msg, "usage", None)
    return ModelReply(text, getattr(usage, "input_tokens", 0) or 0,
                      getattr(usage, "output_tokens", 0) or 0,
                      getattr(msg, "stop_reason", None) == "max_tokens")
