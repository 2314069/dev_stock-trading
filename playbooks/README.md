# playbooks/

Claude Code の **サブエージェント機能** を使い、サブスク内で F-08 マルチエージェント
パイプラインを試走するための手順書集。本実装 (`src/graph/langgraph_impl.py`) が
完成するまでのプロトタイプ用。

## 位置づけ

| レイヤ | 役割 | 課金 | 自動化 |
|---|---|---|---|
| 本実装 (`src/graph/langgraph_impl.py`) | 自動・本番 | Anthropic API 従量 | ✅ バッチ可 |
| **playbooks/** (this) | プロトタイプ・プロンプト検証 | Claude Code サブスク | ❌ 対話必要 |
| `StubOrchestrator` | スキーマ確認・下流開発 | 無料 | ✅ |

## 思想

- **プロンプトと I/O スキーマは `src/agents/*.py` を単一の正とする**。playbook では
  「あの SYSTEM_PROMPT を読んで使え」と参照するだけにして、二重管理を避ける。
- **手順書 + 入力 + 出力ログ**を git で残し、プロンプト改修の効果を diff で見られるようにする。
- 検証で「このプロンプト / フローは有効」と判明したものを `src/agents/` や `src/graph/` に
  逆輸入する流れ。

## 使い方

ユーザがチャットで指示する:

```
Claude、playbooks/predict.md で 2026-05-19 寄付 (^N225) の予測やって
```

Claude はこの手順書を読み、Agent ツールで各役割をサブエージェント起動し、
`runs/<date>_<horizon>/` に成果物を保存して報告する。

## 既知の制約

- サブエージェントのモデルバージョンは `src/agents/*.py` のデフォルト
  (`claude-sonnet-4-6`) と一致するとは限らない（Claude Code セッションのモデル設定に依存）
- Bull/Bear のマルチターン議論は手動オーケストレーション（現状は 1 ラウンドのみ）
- ニュース・指標の取得は WebSearch / WebFetch / yfinance に依存 → ソースの安定性は別途検証

## ファイル

- `predict.md` — F-08 を end-to-end で 1 回回す手順書
- 今後追加候補: `backtest_dryrun.md`, `prompt_ablation.md`, `horizon_sweep.md`
