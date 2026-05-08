# プロジェクトステータス

最終更新: 2026-05-08
ブランチ: `claude/nikkei-futures-spec-n8Gi6`

このファイルはプロジェクトの **現状と次にやること** を一覧化する。コミットを打つたびに併せて更新する。

---

## 現状

### 完了済み

- **SPEC.md v0.3** — 日経先物情報サイトの仕様ドラフト
  - 機能 F-01〜F-09（基本機能 + AI 予測 + ニュース・情報収集）
  - 画面 P-01〜P-15
  - F-08 当日予測: マルチホライゾン化 + 日経特化の入力特徴量 13 カテゴリ + モデル戦略
  - F-09 ニュース収集: 国内外通信社・中銀・取引所開示・SNS 集約 + NLP パイプライン
  - §14.1 LLM 実行・課金の段階移行（Stage 0/1/2）
  - データソース表に日経特化ソース追加（投資主体別売買・裁定残・日経VI・配当予定・指数構成・TDnet/EDINET 等）

- **RESEARCH.md** — 設計・調査ログ
  - LLM オーケストレーション系 OSS 8 件の比較（TradingAgents / FinRobot / PrimoAgent / FinMem 等）
  - GPU 不要、Claude Agent SDK のサブスク未対応の確認
  - 開発フェーズ方針（Phase 0/1/2）
  - 移行コスト最小化のための `src/` ツリー構成案

### 進行中

- なし

---

## 次にやること（優先順位順）

### High（直近）

- [ ] **`src/` ツリーの初期セットアップ**
  - Python パッケージ初期化（`pyproject.toml`、`.python-version`）
  - 依存追加: `langgraph`, `anthropic`, `yfinance`, `pandas`, `pydantic`
  - ディレクトリ作成: `src/llm`, `src/agents`, `src/data`, `src/features`, `src/graph`, `src/eval`, `src/api`
  - `.gitignore`, `.env.example`

- [ ] **`src/llm/client.py` の抽象実装**（Phase 0 仕様）
  - Claude Code 経由で動かす前提の最小実装
  - Phase 1 で `anthropic.Anthropic()` 直叩きに差し替え可能な I/F 設計

- [ ] **F-08 最小エージェント 1 つの実装**
  - 候補: News Analyst（F-09 のセンチメント特徴量を読んで方向性メモを返す）
  - Claude Code 内で動作確認

### Medium（短期）

- [ ] **データ層スタブ**
  - `src/data/jpx.py`（日経先物期近、出来高、OI）
  - `src/data/cme.py`（CME 日経夜間、円建/ドル建）
  - `src/data/fx.py`（USD/JPY、リスクリバーサル）
  - `src/data/news.py`（F-09 のニュース取得 IF）

- [ ] **PrimoAgent fork → 日経 ETF (1321) で動作確認**
  - yfinance を JPX データに差替
  - F-08 MVP の叩き台に

- [ ] **TradingAgents の LangGraph グラフを精読**
  - F-08 のエージェント構成と差分を整理

### Low（後回し）

- [ ] 連続契約 (continuous contract) の ratio 調整実装
- [ ] 配当落ちバックアウト処理
- [ ] レジーム検知（HMM / Change Point Detection）
- [ ] ウォークフォワード・バックテスト基盤
- [ ] F-09 のクローラ実装（TDnet / EDINET / RSS）
- [ ] フロントエンド（Next.js）の初期セットアップ
- [ ] CI/CD（GitHub Actions）

---

## 未解決事項（仕様書 §17 のサマリ）

法務・契約系:
- AI 予測機能の投資助言業該当性の法務確認
- ニュース提供各社との契約範囲（ヘッドライン / 要約 / 本文 / 再配信）
- リアルタイム配信ライセンスの調達時期
- SNS データ利用の可否

技術系（F-08 関連）:
- 連続契約の調整方式（panama / ratio / 無調整）
- 配当落ちの扱い（バックアウト or ダミー化）
- レジーム検知手法の選定
- モデル分離 vs 統合（SQ 週専用 / CME→OSE 伝播 / 後場寄り の独立化粒度）
- マルチホライゾン: 独立モデル群 / 共有 backbone のどちらをデフォルトに
- イベント時の予測停止ポリシー

その他:
- 翻訳・要約 LLM の選定と月次予算上限
- チャートライブラリの最終選定

---

## コミット履歴（このブランチ）

| 日付 | コミット | 内容 |
|---|---|---|
| 2026-05-07 | `daf84b3` | 初版仕様書 + AI 予測機能 (F-08) を追加 |
| 2026-05-07 | `ba3491f` | ニュース・情報収集機能 (F-09) を追加 |
| 2026-05-08 | `633fe5c` | RESEARCH.md（OSS 調査・設計方針）を追加 |
| 2026-05-08 | `d34e242` | §14.1 LLM 実行・課金フェーズを追加 |
| 2026-05-08 | `fdc6a98` | F-08 を日経特化に拡張（マルチホライゾン・特徴量 13 カテゴリ） |
| 2026-05-08 | `7e028af` | STATUS.md を追加（運用開始） |

---

## 参考リンク

- [SPEC.md](./SPEC.md) — 仕様書
- [RESEARCH.md](./RESEARCH.md) — 設計・調査ログ
