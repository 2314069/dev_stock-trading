"""エージェント共通の LLM 呼び出しヘルパ。

各エージェントから重複していたボイラープレート（`CompletionRequest` 構築 → `client.complete()` 呼出
→ JSON パース → Pydantic 検証）を 1 ファイルに集約する。リトライ・レイテンシ計測・トークン課金
記録・プロンプトキャッシュなどの横断的関心事は、本ファイルに後付けで差し込むことを想定している。

エージェント側は `run_json_agent(system=..., user=..., schema=...)` を呼ぶだけになり、
LLM I/F の変更は本ファイル + `client.py` の修正で完結する。
"""

from __future__ import annotations

from collections.abc import Callable

from pydantic import BaseModel

from config import get_settings
from llm.client import (
    CompletionRequest,
    LLMClient,
    Message,
    get_client,
    parse_json_response,
)

Postprocess = Callable[[dict[str, object]], dict[str, object]]


def run_json_agent[T: BaseModel](
    *,
    system: str,
    user: str,
    schema: type[T],
    client: LLMClient | None = None,
    model: str | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
    post_process: Postprocess | None = None,
) -> T:
    """システム + ユーザメッセージ → JSON 応答 → Pydantic 検証まで一気通貫。

    Args:
        system: SYSTEM_PROMPT。
        user: ユーザメッセージ本文。
        schema: 検証先 Pydantic モデル。
        client: 任意の LLMClient（テストでは StubClient を渡す）。
            None の場合は `get_client()` を使う。
        model: モデル名の override。None なら settings のデフォルト。
        max_tokens: トークン上限の override。None なら settings のデフォルト。
        temperature: 温度の override。None なら settings のデフォルト。
        post_process: JSON パース後・Pydantic 検証前にペイロードを書き換えるフック
            (例: 呼出側既知の値を注入する、フィールド名を正規化する など)。
    """
    settings = get_settings()
    client = client or get_client()

    kwargs: dict[str, object] = {
        "system": system,
        "messages": [Message(role="user", content=user)],
        "max_tokens": max_tokens if max_tokens is not None else settings.llm.default_max_tokens,
        "temperature": (
            temperature if temperature is not None else settings.llm.default_temperature
        ),
    }
    if model is not None:
        kwargs["model"] = model

    result = client.complete(CompletionRequest(**kwargs))  # type: ignore[arg-type]
    payload = parse_json_response(result.content)
    if post_process is not None:
        payload = post_process(payload)
    return schema.model_validate(payload)


__all__ = ["Postprocess", "run_json_agent"]
