"""アプリ全体の設定値を集約する。

技術要素の差替（LLM プロバイダ・モデル・データソース・予算上限など）はここを起点に行う。
設定値は環境変数からも上書き可能で、テストでは `set_settings()` で直接注入する。

依存方針:
- 本パッケージは他の src/ 配下のモジュールに依存しない（最下層レイヤ）。
- `python-dotenv` は依存に含まれるため `.env` の自動読み込みも行う。
"""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()  # .env を一度だけ読む（既存環境変数は上書きしない）


class LLMSettings(BaseModel):
    """LLM 呼び出しの既定値。エージェント側で個別 override 可能。"""

    default_model: str = "claude-sonnet-4-6"
    default_max_tokens: int = 2048
    default_temperature: float = 0.0


class Settings(BaseModel):
    """アプリ全体の設定。"""

    llm: LLMSettings = Field(default_factory=LLMSettings)

    @classmethod
    def from_env(cls, **overrides: Any) -> Settings:
        """環境変数から設定を読み出す。未指定キーは BaseModel のデフォルトを使う。

        対応する環境変数:
        - LLM_DEFAULT_MODEL
        - LLM_DEFAULT_MAX_TOKENS
        - LLM_DEFAULT_TEMPERATURE
        """
        llm_values: dict[str, Any] = {}
        if (v := os.environ.get("LLM_DEFAULT_MODEL")) is not None:
            llm_values["default_model"] = v
        if (v := os.environ.get("LLM_DEFAULT_MAX_TOKENS")) is not None:
            llm_values["default_max_tokens"] = int(v)
        if (v := os.environ.get("LLM_DEFAULT_TEMPERATURE")) is not None:
            llm_values["default_temperature"] = float(v)
        llm = LLMSettings(**llm_values)
        defaults: dict[str, Any] = {"llm": llm}
        defaults.update(overrides)
        return cls(**defaults)


_settings: Settings | None = None


def get_settings() -> Settings:
    """シングルトンの Settings を返す。初回呼出時に env から読む。"""
    global _settings
    if _settings is None:
        _settings = Settings.from_env()
    return _settings


def set_settings(settings: Settings) -> None:
    """主にテスト / DI 用。次回 `get_settings()` から渡した値を返すようにする。"""
    global _settings
    _settings = settings


def reset_settings() -> None:
    """主にテスト用。シングルトンを破棄し次回 `get_settings()` で env から再読込。"""
    global _settings
    _settings = None


__all__ = [
    "LLMSettings",
    "Settings",
    "get_settings",
    "reset_settings",
    "set_settings",
]
