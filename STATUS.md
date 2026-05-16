# プロジェクトステータス

最終更新: 2026-05-16 (Portfolio Manager 追加 — F-08 エージェント群完成)
ブランチ: `claude/plan-next-tasks-G05pb`

このファイルはプロジェクトの **現状と次にやること** を一覧化する。コミットを打つたびに併せて更新する。

---

## 現状

### 完了済み

- **`src/` ツリーと依存の初期セットアップ**
  - `pyproject.toml`（uv + hatchling、Python 3.12）
  - 主要依存: `langgraph`, `anthropic`, `yfinance`, `pandas`, `pydantic`, `python-dotenv`, `fastapi`, `httpx`
  - dev 依存: `pytest`, `pytest-asyncio`, `ruff`, `mypy`
  - ディレクトリ: `src/{llm,agents,data,features,graph,eval,api}` + `tests/`
  - 各サブモジュールに責務メモ付きの `__init__.py`
  - `.python-version`, `.gitignore`, `.env.example`
  - 初回セットアップは `uv sync` で実行

- **`src/llm/client.py` LLM クライアント抽象（Phase 0/1 切替点）**
  - SPEC §14.1 のとおり LLM 呼び出しを 1 ファイルに集約
  - `LLMClient` Protocol + `AnthropicClient`（Stage 1+）+ `StubClient`（Stage 0/テスト用）
  - Pydantic で `Message` / `CompletionRequest` / `CompletionResult` を定義
  - `get_client()` ファクトリが `ANTHROPIC_API_KEY` の有無で実装を切替
  - `parse_json_response()` で ```json``` フェンス・前後の説明文を剥がして JSON 抽出
  - デフォルトモデル: `claude-sonnet-4-6`

- **`src/agents/news_analyst.py` News Analyst エージェント（F-08 最小エージェント 1 つ目）**
  - F-09 のニュース + センチメント（`NewsItem`）を入力に方向性メモ（`DirectionalMemo`）を返す
  - 6 ホライゾン対応（寄付 / 引け / 後場寄り / ナイト寄り・引け / 翌日寄り）
  - SYSTEM_PROMPT で売買推奨禁止・ハルシネーション抑制・JSON 出力を指示
  - 入力に存在する見出しからのみ key_drivers を選ぶよう制約

- **`src/agents/technical_analyst.py` Technical Analyst エージェント（F-08 2 つ目）**
  - SPEC §F-08 (a)(b)(k) のテクニカル指標スナップショット (`TechnicalIndicators`) を入力に方向性メモを返す
  - 主要指標: SMA(5/25/75/200)、RSI(14)、MACD、Bollinger Width、ATR(14)、一目均衡表雲との位置、オーバーナイトリターン
  - 任意で直近足 (`FuturesBar`) をコンテキストとして渡せる
  - 欠損 (None) 指標はプロンプト上で明示し、判断材料に使わせない
  - ホライゾン別の重み付け方針をプロンプトに明記（寄付前はオーバーナイト系、引け予測は日中モメンタム系を重視）

- **`src/agents/sentiment_aggregator.py` Sentiment Aggregator エージェント（F-08 3 つ目）**
  - 複数の `DirectionalMemo`（カテゴリ別 / ソース別 News Analyst 出力など）を `LabeledMemo` 経由で受け取り 1 つに集約
  - 集約は LLM ベース。confidence と label（"central_bank" / "official" / "exchange" 等は重み高め）で加重判断
  - 方向が割れる場合は乖離をそのまま summary に記述（無理に統合しない）
  - 出力は同じ `DirectionalMemo`。Portfolio Manager から見ると個別 Analyst と同列のシグナル源

- **`src/agents/researchers.py` Researcher Bull / Bear エージェント（F-08 4 つ目・5 つ目）**
  - `analyze_bull()` と `analyze_bear()` を同居。共通の `ResearcherRequest`（memos + 任意の `opposing_memo`）を受ける
  - Bull は強気側のシナリオを担当し direction は bullish / neutral のみ。Bear は鏡像で bearish / neutral のみ
  - データが反対側を強く支持する場合は無理に自陣営を主張せず、neutral + 低 confidence で正直に返すよう制約
  - `opposing_memo` があれば相手側の前回主張に**直接反論**するプロンプトに切替（マルチターン議論の素材）
  - マルチターン議論のオーケストレーション自体は `src/graph/` の責務として後回し（各 analyze 関数は純粋シングルショット）

- **`src/agents/portfolio_manager.py` Portfolio Manager エージェント（F-08 最終ノード）**
  - 入力 `PortfolioRequest`: 上流 `LabeledMemo` 群 + `bull_memo` / `bear_memo`（議論結果を別フィールドで明示）
  - 出力 `PortfolioPlan`: direction（3 値）/ `DirectionProbabilities`（和 ~1.0 を Pydantic で検証）/ confidence / top_drivers（最大 5）/ scenario / bull_case / bear_case
  - SPEC §F-08 の最終出力のうち **LLM で生成可能な部分** を担当。予測レンジ・ポイント・類似日は ML モデル側として分離
  - `horizon` は req から直接埋め、LLM に echo させない設計
  - プロンプトで「direction は最大確率と整合」「分布の和は 1.0 ±0.01」「入力に無い観点は採用しない」を制約

- **`src/agents/types.py` 共通型**
  - `Horizon` / `DirectionalMemo` / `LabeledMemo` / `DirectionProbabilities` / `PortfolioPlan` を集約
  - News / Technical / Sentiment Aggregator / Researcher は `DirectionalMemo`、Portfolio Manager のみ `PortfolioPlan` を返す
  - `news_analyst.py` / `sentiment_aggregator.py` は後方互換のため再エクスポート

- **テスト**
  - `tests/test_llm_client.py`: StubClient エコー・カスタム responder・get_client 切替・JSON パース 5 ケース
  - `tests/test_news_analyst.py`: スタブ経由のメモ生成・JSON フェンス対応・プロンプト内容検証・スキーマ検証エラー
  - `tests/test_technical_analyst.py`: スタブ経由のメモ生成・JSON フェンス対応・プロンプト要素検証（指標 / シンボル / 直近足）・欠損指標の None 表記・RSI 値域バリデーション
  - `tests/test_sentiment_aggregator.py`: スタブ経由の集約・プロンプトに各 LabeledMemo が並ぶこと・空入力時の挙動・不正 JSON
  - `tests/test_researchers.py`: Bull / Bear の独立スタブ出力・SYSTEM_PROMPT の使い分け（bearish 禁止 / bullish 禁止表現の確認）・opposing_memo のプロンプト埋め込み・初回ターンでの「反論対象なし」表記・各 LabeledMemo の整形・不正 JSON
  - `tests/test_portfolio_manager.py`: スタブ経由のプラン生成・`horizon` が req 由来で LLM 出力を上書きすること・プロンプトの memos / Bull / Bear 整形・Bull/Bear 未入力時の表記・確率分布の和バリデーション・top_drivers 上限 5・不正 JSON
  - `tests/test_data_news.py` / `test_data_jpx.py` / `test_data_cme.py` / `test_data_fx.py`: 各データ層スタブの IF / フィルタ / デフォルト動作
  - `pyproject.toml` に `pythonpath = ["src"]` を追加（`uv sync` 後に `uv run pytest` で動作する）

- **`src/data/` データ層スタブ（Stage 0 用、4 モジュール）**
  - `src/data/news.py`: `NewsItem` / `NewsQuery` / `NewsFetcher` Protocol / `StubNewsFetcher`（since・until・sources・categories・min_impact・limit でフィルタ）。`NewsItem` / `Impact` は `agents/news_analyst.py` から本モジュールへ移管し、後方互換のため再エクスポート
  - `src/data/jpx.py`: 日経225先物の `FuturesBar` / `FuturesQuote` / `JpxClient` Protocol（quote / bars / OI）/ `StubJpxClient`（決定論的）
  - `src/data/cme.py`: `CmeNikkeiQuote` / `CmeNikkeiBar`（円建/ドル建）/ `CmeClient` Protocol / `StubCmeClient`
  - `src/data/fx.py`: `FxQuote`（change / change_pct プロパティ）/ `RiskReversal`（OTM プット IV − OTM コール IV）/ `FxClient` Protocol / `StubFxClient`
  - 各モジュールに `get_client()` / `get_fetcher()` ファクトリを置き、Stage 1+ で実 API 実装へ差替えるだけにする
  - `pyproject.toml` の wheel packages に登録済みの `src/data` がディレクトリ未作成だった問題を同時に解消

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

- [ ] **uv 環境の初回セットアップ**（未完了）
  - 現環境に uv / Python 3.12 が PATH 上に無い
  - `winget install --id=astral-sh.uv` などでインストール後、`uv sync` を実行
  - その後 `uv run pytest` で `tests/test_llm_client.py` + `tests/test_news_analyst.py` の動作確認
  - `pre-commit` の導入は任意（後回し可）

- [ ] **News Analyst の Claude Code 内動作確認**
  - `ANTHROPIC_API_KEY` を `.env` に設定し、実 LLM での出力品質を確認
  - 出力 JSON の安定性（フェンス有無、温度、prefill 要否）を観察し必要に応じて調整

- [ ] **F-08 残りエージェントの実装**
  - [x] Technical Analyst（2026-05-16 実装）
  - [x] Sentiment Aggregator（2026-05-16 実装）
  - [x] Researcher Bull / Bear（2026-05-16 実装。議論オーケストレーションは graph 層に後回し）
  - [x] Portfolio Manager（2026-05-16 実装。F-08 エージェント群が一通り揃った）

- [ ] **オーケストレーション (src/graph/) の LangGraph 実装**
  - News × N → Sentiment Aggregator → (Technical と並列) → Bull/Bear 議論 (rounds) → Portfolio Manager
  - 状態管理（中間 memo の蓄積）、ホライゾン別グラフの分岐、エラーリトライ

### Medium（短期）

- [x] **データ層スタブ**（2026-05-16 実装。Stage 0 用、`Protocol` IF + `Stub*` 実装 + `get_client()` ファクトリ）
  - `src/data/jpx.py`（日経先物期近、OHLCV、OI）
  - `src/data/cme.py`（CME 日経夜間、円建/ドル建）
  - `src/data/fx.py`（USD/JPY、リスクリバーサル）
  - `src/data/news.py`（F-09 のニュース取得 IF。`NewsItem` を `agents/news_analyst.py` から移管）

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
| 2026-05-08 | `537cbc6` | STATUS.md コミットハッシュのバックフィル |
| 2026-05-08 | `4baad00` | `src/` ツリーと依存（uv + hatchling）の初期セットアップ |
| 2026-05-10 | `3440480` | `src/llm/client.py` LLM 抽象 + News Analyst + tests |
| 2026-05-16 | `0e8aad0` | `src/data/{news,jpx,cme,fx}.py` スタブ + tests（4 モジュール）|
| 2026-05-16 | `677558a` | `uv.lock` を追加（依存バージョン固定）|
| 2026-05-16 | `fd8a2f1` | Technical Analyst + 共通型 `agents/types.py` + tests |
| 2026-05-16 | `6510871` | Sentiment Aggregator + tests |
| 2026-05-16 | `6b0dcbd` | Researcher Bull / Bear + LabeledMemo を types に集約 |
| 2026-05-16 | _未定_ | Portfolio Manager + `PortfolioPlan` / `DirectionProbabilities` 型追加 |

---

## 参考リンク

- [SPEC.md](./SPEC.md) — 仕様書
- [RESEARCH.md](./RESEARCH.md) — 設計・調査ログ
