# a01_f08_subagent

Claude Code のサブエージェント機能を使い、サブスク内で F-08 マルチエージェントパイプラインを
手動オーケストレーションする architecture。**本実装 (`a02_langgraph_pipeline`) 完成までの
プロトタイプ**として位置づけ、有効なプロンプト・フローを本実装に逆輸入する二段ロケット戦略の前段。

## 思想

- **コード追加最小**: プロンプトと I/O スキーマは `src/agents/*.py` を単一の正とし、ここでは
  「あの SYSTEM_PROMPT を読んで Agent ツールで起動せよ」と参照するだけ
- **対話駆動**: Claude (チャット内) が手順書を読んで人力 LangGraph として実行する
- **再現性は git で**: 入力 (`fixtures/`) と出力 (`runs/`) を git で追跡し、プロンプト改修の効果を
  diff で観察可能にする

## 特徴

| 項目 | 値 |
|---|---|
| 課金 | Claude Code サブスク（API key 不要）|
| 並列性 | あり（1 メッセージに複数 Agent tool_use で実現）|
| 自動化 | ❌ Claude セッションが必要 |
| 議論ラウンド | scenario で可変（baseline = 1）|
| 移植難度 | 高（プロンプトは src/agents/*.py 経由で本実装に共有可能）|

## 実装

- `playbook.md`: 手順書（Claude が読んで実行する）
- `scenarios/sNN_*.json`: knob 違いの宣言（baseline / 議論ラウンド / プロンプト差替など）
- `prompts/<agent>/<variant>.md`: scenario が参照するプロンプト差分（現状未使用、必要時追加）

## 既知の制約

- サブエージェントのモデルが `src/agents/*.py` のデフォルト (`claude-sonnet-4-6`) と
  一致するとは限らない（Claude Code セッションのモデル設定に依存）
- Bull/Bear のマルチターン議論は手動オーケストレーション（scenario で `debate_rounds` 指定）
- ニュース・指標の取得は WebSearch / WebFetch / yfinance に依存 → ソース・network 制約に従う

## 実行

ユーザがチャットで指示する例:

```
Claude、architectures/a01_f08_subagent/playbook.md で scenario=s01_baseline、
fixture=fixtures/2026-05-19_macro_heavy/ を走らせて
```

Claude は `playbook.md` を読み、`scenarios/s01_baseline.json` の params に従い、
`fixtures/<id>/` の入力で Agent ツールを起動、`runs/<date>_<horizon>/a01_f08_subagent/s01_baseline/`
に成果物を保存する。

## ログ

- 初回試走: `runs/2026-05-19_next_open/a01_f08_subagent/s01_baseline/`
  （Technical 取得失敗で News-only。最終 direction=bearish, P(bear)=0.60, confidence=62）
