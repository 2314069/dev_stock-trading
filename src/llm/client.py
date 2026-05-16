"""LLM クライアント抽象。

SPEC §14.1 の方針に従い、Stage 0 (Claude Code / プロトタイピング) → Stage 1 (Anthropic API キー)
→ Stage 2 (マルチプロバイダ + Batch) の切替をこのファイル 1 点で吸収する。エージェント本体・データ層・
グラフ層はこの I/F のみに依存する。
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Callable
from typing import Literal, Protocol

from pydantic import BaseModel

DEFAULT_MODEL = "claude-sonnet-4-6"


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class CompletionRequest(BaseModel):
    messages: list[Message]
    system: str | None = None
    model: str = DEFAULT_MODEL
    max_tokens: int = 2048
    temperature: float = 0.0


class CompletionResult(BaseModel):
    content: str
    stop_reason: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0


class LLMClient(Protocol):
    def complete(self, request: CompletionRequest) -> CompletionResult: ...


class AnthropicClient:
    """Stage 1+: anthropic SDK 直叩き。`ANTHROPIC_API_KEY` を使う。"""

    def __init__(self, api_key: str | None = None) -> None:
        from anthropic import Anthropic

        self._client = Anthropic(api_key=api_key) if api_key else Anthropic()

    def complete(self, request: CompletionRequest) -> CompletionResult:
        kwargs: dict[str, object] = {
            "model": request.model,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "messages": [m.model_dump() for m in request.messages],
        }
        if request.system is not None:
            kwargs["system"] = request.system
        resp = self._client.messages.create(**kwargs)  # type: ignore[arg-type]
        text = "".join(block.text for block in resp.content if block.type == "text")
        return CompletionResult(
            content=text,
            stop_reason=resp.stop_reason or "end_turn",
            model=resp.model,
            input_tokens=resp.usage.input_tokens,
            output_tokens=resp.usage.output_tokens,
        )


Responder = Callable[[CompletionRequest], str]


class StubClient:
    """Stage 0: API キー無しでエージェント開発・ユニットテストを回すためのスタブ。

    `responder` を渡せば任意の応答を生成できる（テストではここに正規の JSON を返す関数を渡す）。
    省略時は最後のユーザメッセージの先頭 80 文字をエコーバックする。
    """

    def __init__(self, responder: Responder | None = None) -> None:
        self._responder = responder or _default_responder

    def complete(self, request: CompletionRequest) -> CompletionResult:
        content = self._responder(request)
        return CompletionResult(
            content=content,
            stop_reason="end_turn",
            model="stub",
            input_tokens=0,
            output_tokens=len(content),
        )


def _default_responder(request: CompletionRequest) -> str:
    last_user = next((m.content for m in reversed(request.messages) if m.role == "user"), "")
    return f"[stub] {last_user[:80]}"


def get_client() -> LLMClient:
    """環境に応じて実装を返す。`ANTHROPIC_API_KEY` があれば Anthropic、無ければ Stub。"""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return AnthropicClient()
    return StubClient()


_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL)


def parse_json_response(content: str) -> dict[str, object]:
    """LLM が返す JSON を頑健にパースする。```json``` フェンスを剥がし、最初の JSON オブジェクトを抽出する。"""
    m = _FENCE_RE.match(content)
    if m:
        content = m.group(1)
    start = content.find("{")
    end = content.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"no JSON object found in response: {content!r}")
    return json.loads(content[start : end + 1])


__all__ = [
    "DEFAULT_MODEL",
    "AnthropicClient",
    "CompletionRequest",
    "CompletionResult",
    "LLMClient",
    "Message",
    "StubClient",
    "get_client",
    "parse_json_response",
]
