# 日経先物情報サイト リサーチ・設計ログ

最終更新: 2026-05-08
関連: [SPEC.md](./SPEC.md)

このドキュメントは、サイト構想から実装方針決定までの議論・調査結果をまとめたもの。仕様書 (`SPEC.md`) と対で読む想定。

---

## 1. プロジェクト概要

**目的**: 日経平均先物（OSE 大証 / CME）の値動き・板・ニュース・経済指標・**当日 AI 予測**を一元的に提供する Web 情報サイトを構築する。

**主要機能**（仕様書の機能 ID）:
- F-01〜F-07: 価格・チャート・板・アラート・サマリー・検索などの基本機能
- **F-08 当日株価予測**: 機械学習で当日の方向性・レンジ・寄与要因を提示
- **F-09 ニュース・情報収集**: 国内外通信社・中銀・取引所開示・SNS を集約、要約・センチメント分析

**画面 ID** で追加した主要なもの:
- P-13 当日予測画面
- P-14 情報収集ハブ
- P-15 速報フィード

詳細は `SPEC.md` 参照。

---

## 2. リサーチ: LLM オーケストレーション系のリポジトリ

「マルチエージェント LLM で株価予測・取引判断」をしている OSS を 8 件調査した。**日経先物特化のものは存在しない**。米株中心。

### 2.1 比較サマリ

| リポジトリ | Stars | License | オーケストレータ | 直近活動 | 一言 |
|---|---|---|---|---|---|
| [TradingAgents](https://github.com/TauricResearch/TradingAgents) | 70.7k | Apache-2.0 | LangGraph | v0.2.4 (2026/4) | デファクト。多 LLM 対応、checkpoint resume |
| [FinRobot](https://github.com/AI4Finance-Foundation/FinRobot) | 6.9k | Apache-2.0 | 独自 Smart Scheduler | v1.0.0 (2026/3) | プラットフォーム志向、Perception/Brain/Action |
| [PrimoAgent](https://github.com/ivebotunac/PrimoAgent) | 318 | MIT | LangGraph 線形 | 2025/9 | 翌日予測の最小サンプル。バックテスト数値あり |
| [FinMem](https://github.com/pipiku915/FinMem-LLM-StockTrading) | 中 | MIT | 独自 + 階層メモリ | 学術系 (2023) | 「類似日記憶」の設計参考 |
| [ai-agent-comparison](https://github.com/Vigneshmaradiya/ai-agent-comparison) | 小 | MIT | 3 種比較 | リファレンス | フレームワーク選定材料 |
| [AgenticTrading](https://github.com/Open-Finance-Lab/AgenticTrading) | 187 | LICENSE記載 | MCP + A2A | 198 commits | Neo4j メモリ、研究寄り |
| [LLM-Enhanced-Trading](https://github.com/Ronitt272/LLM-Enhanced-Trading) | 小 | MIT | 単発スクリプト | - | FinGPT センチメント連携の例 |
| [StockAgent](https://github.com/MingyuJ666/Stockagent) | 中 | 不明 | 独自シミュレータ | 学術系 (2024) | 評価設計（リーケージ防止）の参考 |

### 2.2 各リポジトリの要点

#### TradingAgents（最有力の参考実装）
- Fundamentals / Sentiment / News / Technical の **Analyst 4 種** → **Bull/Bear Researcher の構造化ディベート** → Trader → Risk / Portfolio Manager
- LangGraph + checkpoint（中断再開、決定ログ永続化）
- マルチプロバイダ（OpenAI / Anthropic / Gemini / DeepSeek / Qwen / GLM / Ollama / Azure）
- データ層が Alpha Vantage 依存。**日経 / 限月 / SQ / OSE ナイトセッションは未対応**

#### FinRobot（プラットフォーム参考）
- Perception → Brain (Financial CoT) → Action の三層
- Market Forecaster / Document Analysis / Trading Strategy + 株式リサーチ用 8 エージェント
- レポート生成（DCF・3 年予測・ピア比較）が強い
- 米株 (NVDA/MSFT 等) 前提、FMP/FINNHUB/SEC

#### PrimoAgent（MVP の叩き台に最適）
- **4 エージェント線形パイプライン**: Data Collection → Technical Analysis → News Intelligence → Portfolio Manager
- 出力は CSV、信頼度・ポジションサイズ付き
- バックテスト公開: META +31.97% / AAPL -6.88% / Sharpe -2.04〜+2.90 とブレ大

#### FinMem（メモリ設計）
- Working / Episodic / Semantic の 3 層メモリ
- **F-08 の `similarDays`** や、F-09 で蓄積したニュース文脈の参照に転用可能

#### ai-agent-comparison（フレームワーク選定）
- 同一ワークフローを CrewAI / LangGraph / AutoGen で実装
- 結論: CrewAI = 線形・低学習コスト、LangGraph = DAG・状態管理、AutoGen = 動的会話
- → **F-08 のような構造化フローは LangGraph、F-09 の編集判断や品質チェックは AutoGen** が見えやすい

### 2.3 仕様への適用方針

```
F-08 当日予測
  ├─ ベース構造: TradingAgents（Analyst→Researcher debate→Trader→Risk）
  ├─ MVP 試作: PrimoAgent（LangGraph 線形パイプライン）
  ├─ 類似日メモリ: FinMem（3 層メモリ）
  ├─ 評価設計: StockAgent（リーケージ防止）+ 自前ウォークフォワード
  └─ センチメント連結: LLM-Enhanced-Trading のフロー

F-09 情報収集
  ├─ 文書解析: FinRobot Document Analysis Agent
  └─ センチメント: FinGPT (LLM-Enhanced-Trading 流用)

オーケストレータ
  └─ LangGraph に決め打ち（ai-agent-comparison より）
```

### 2.4 共通の不足点（自前実装が必要）

1. **日経先物・OSE ナイトセッション・限月・SQ** を扱うリポジトリは皆無
2. **TDnet / EDINET の適時開示**は OSS にほぼなし
3. **大阪取引所のティック / 板気配** もデータ層自作
4. バックテストは米株個別銘柄ベース、**先物の限月交代・ロールオーバー対応** は要追加

---

## 3. リソース・課金の整理

### 3.1 GPU の要否

GPU は **必須ではない**。

| LLM 選択 | GPU | 必要なもの | コスト感 |
|---|---|---|---|
| OpenAI / Anthropic / Gemini API | 不要 | API キー + 課金 | 1 銘柄 1 日分で数十円〜数百円 |
| DeepSeek / Qwen など低価格 API | 不要 | API キー | 上記の 1/5〜1/10 |
| Ollama（ローカル LLM） | 必要 | 24GB+ VRAM 推奨 | 電気代のみ |

マルチエージェントは **1 回の判断で 10〜30 回の LLM 呼び出し** が発生するため、本格バックテストは数十〜数百ドル規模になる。

### 3.2 Claude サブスク vs API（重要）

調査の結果、**Claude Pro/Max サブスクと API は別課金**かつ **Claude Agent SDK はサブスク認証に未対応**（API キー必須）。

| 使い方 | サブスクで動く？ | 用途 |
|---|---|---|
| **Claude Code CLI** | ○ | 対話的に開発・プロトタイピング |
| **Claude Agent SDK** (Python/TS) | × API キー必須 | プログラム化・スケジュール実行 |
| **Anthropic API 直叩き** | × | 同上 |

公式情報:
- [Agent SDK Overview](https://code.claude.com/docs/en/agent-sdk/overview)
- [Use Claude Code with your Pro or Max plan](https://support.claude.com/en/articles/11145838-use-claude-code-with-your-pro-or-max-plan)
- [Issue #559: Max plan billing 対応リクエスト（未承認）](https://github.com/anthropics/claude-agent-sdk-python/issues/559)

サブスクの 5 時間枠（Pro 約 44k tok / Max 5x 約 88k tok / Max 20x 約 176k tok）で収まる用途のみサブスクで完結する。

---

## 4. 開発フェーズ方針（決定）

サブスクを最大活用しつつ、将来は API へ移行する **3 段階** で進める。

### Phase 0: プロトタイピング（サブスクのみで完結）
- **Claude Code (CLI) で開発作業そのものを進める**
- データ取得スクリプト（yfinance / JPX）、特徴量、プロンプト、LangGraph グラフを実装
- 動作確認は Claude Code 内で 1〜2 回、5 時間枠に収まる範囲で
- → サブスク料金のみ、API 課金ゼロ

### Phase 1: 本格稼働（API キー必須に移行）
- バックテスト（過去 1 年 × 数百日 × エージェント 5 種 = 数千〜数万 LLM 呼び出し）
- 毎日のスケジュール推論（cron で 7:30 / 9:00–14:30 30 分毎 / 16:00）
- これらは 5 時間枠を超えるため `ANTHROPIC_API_KEY` を発行し Agent SDK へ
- 安価なモデル (`claude-haiku-4-5`) や DeepSeek を併用してコスト最適化

### Phase 2: サービス化
- ユーザー毎課金、レート制限、Batch API（50% 引き）活用
- マルチプロバイダ抽象化（Claude / DeepSeek / Gemini を切替）

---

## 5. 移行を最小化するプロジェクト構成案

LLM 呼び出しを 1 ファイルに集約しておき、Phase 0 → 1 はそのファイル差替で済むようにする。

```
src/
├── llm/
│   └── client.py        # ← Phase 0/1 で差し替える唯一の場所
├── agents/
│   ├── news_analyst.py        # プロンプト + 処理ロジック
│   ├── technical_analyst.py
│   ├── sentiment_analyst.py
│   ├── researcher_bull.py
│   ├── researcher_bear.py
│   └── portfolio_manager.py
├── data/
│   ├── jpx.py                 # 日経/JPX データ取得
│   ├── cme.py                 # CME 日経夜間
│   ├── fx.py                  # USD/JPY
│   └── news.py                # ニュースフィード
├── features/
│   └── builder.py             # F-08 の特徴量生成
├── graph/
│   └── workflow.py            # LangGraph orchestration
├── eval/
│   ├── backtest.py            # ウォークフォワード
│   └── metrics.py
└── api/
    └── predictions.py         # /predictions/today 等
```

`llm/client.py` の責務:
- Phase 0: Claude Code 内で対話実行する補助関数のみ（プロンプト調整に専念）
- Phase 1+: `anthropic.Anthropic()` クライアントで API 直叩き
- Phase 2: マルチプロバイダ抽象化（Strategy パターン）

---

## 6. 次のアクション

優先度順:

1. **`SPEC.md` の §14 ロードマップに Phase 0 / 1 / 2 を追記**（サブスク → API 移行を明文化）
2. **リポジトリの初期セットアップ**: 上記 `src/` ツリー、Python パッケージ初期化、基本的な依存（langgraph, anthropic, yfinance, pandas, pydantic）
3. **`llm/client.py` の抽象を Phase 0 仕様で実装**（最小、Claude Code 経由で動かす前提）
4. **F-08 の最小エージェント 1 つ**（例: News Analyst）を実装して、Claude Code 内で動作確認
5. **PrimoAgent をクローンして yfinance を JPX データに差し替え**、日経 ETF (1321) で動作確認 → MVP の叩き台
6. **TradingAgents の LangGraph グラフを読み**、F-08 のエージェント構成と差分を整理

### 後回しでよい項目

- TDnet / EDINET の取込（F-09 の Phase 4.6）
- リアルタイム板気配（OSE 配信契約待ち）
- 多言語化、有料プラン

---

## 7. 未解決事項（仕様書 §17 の補足）

- リアルタイム配信ライセンスの調達時期
- ニュース提供各社との契約範囲
- 有料化の課金モデル（v2 検討）
- AI 予測機能の法務確認（投資助言業に該当しないことの確証）
- LLM 月次予算の上限設定とアラート

---

## 参考資料

### 仕様書
- [SPEC.md](./SPEC.md) — 詳細仕様

### LLM オーケストレーション OSS
- [TradingAgents](https://github.com/TauricResearch/TradingAgents) / [論文](https://arxiv.org/abs/2412.20138)
- [FinRobot](https://github.com/AI4Finance-Foundation/FinRobot)
- [PrimoAgent](https://github.com/ivebotunac/PrimoAgent)
- [FinMem-LLM-StockTrading](https://github.com/pipiku915/FinMem-LLM-StockTrading)
- [ai-agent-comparison](https://github.com/Vigneshmaradiya/ai-agent-comparison)
- [AgenticTrading](https://github.com/Open-Finance-Lab/AgenticTrading)
- [LLM-Enhanced-Trading](https://github.com/Ronitt272/LLM-Enhanced-Trading)
- [StockAgent](https://github.com/MingyuJ666/Stockagent)
- [awesome-ai-in-finance](https://github.com/georgezouq/awesome-ai-in-finance) — キュレーションリスト

### Claude SDK / 認証
- [Agent SDK Overview](https://code.claude.com/docs/en/agent-sdk/overview)
- [Agent SDK Quickstart](https://code.claude.com/docs/en/agent-sdk/quickstart)
- [Claude API Authentication](https://platform.claude.com/docs/en/manage-claude/authentication.md)
- [Use Claude Code with your Pro or Max plan](https://support.claude.com/en/articles/11145838-use-claude-code-with-your-pro-or-max-plan)
- [Rate limits](https://platform.claude.com/docs/en/api/rate-limits)
