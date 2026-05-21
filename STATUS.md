# プロジェクトステータス

最終更新: 2026-05-21 (構造改善 — runs パス再編 / versioning / ActualOutcome / variants グローバル化 等 13 項目)
ブランチ: `claude/plan-next-tasks-h60S6`

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

- **構造改善（2026-05-21）— 批判的レビューを受けて 13 項目の改善を実装**
  - 出力契約の明示化: 全 arch は `PortfolioPlan` を吐く、Python 互換 arch のみ `Orchestrator` Protocol を実装
  - runs パス再編: `runs/<date>_<horizon>/<arch>/<scenario>/` → `runs/<fixture_id>/<horizon>/<arch>/<scenario>/<run_id>/`。fixture と run の対応が path で明示
  - run versioning: `manifest.json` に `git_sha` / `prompts_hash` / `run_id` 追加。同じ scenario × fixture でも別 prompts_hash で並列保存可能に
  - prompts variant をグローバル化: `src/agents/variants/<agent>/<variant>.md` に統一（arch ローカルでなく arch 横断で再利用可能）
  - 命名統一: `fixtures/<id>/metadata.json` → `fixture.json`、`fixtures/_helpers/` → `fixtures/tools/`
  - scenario を YAML 化: `sNN_*.json` → `sNN_*.yaml` (人手編集向上、`pyyaml` を dev deps に追加)
  - scenario カタログ: `architectures/<arch>/scenarios/README.md` 新設
  - `ActualOutcome` 型追加 (`src/agents/types.py`): fixture/label.json の検証用
  - eval/reports を experiments に統合: 生スコアは `experiments/expNNN_*/scores.json` に
  - experiments/exp001_a01_baseline_observation/ 新設: 既存 baseline run を experiment レポート化
  - `src/graph/orchestrator.py` docstring に「具象実装は architectures/aNN/impl.py に置く」明記
  - architectures/README.md に「src/ への依存」「外部 fork 系は subtree 推奨」セクション
  - `.gitignore` に将来 OHLCV 増殖時の方針コメント

- **architecture-first リストラ（2026-05-19）— 複数アーキテクチャ × scenario × fixture を並列に試せる構造**
  - 旧構成 `playbooks/predict.md` (シングル) → 新構成 `architectures/aNN_*/` (multiple) へ昇格
  - `architectures/a01_f08_subagent/`: 旧 playbook の移行先。シングルエージェント方式は a01 と命名
  - `architectures/README.md`: arch カタログ。a02_langgraph_pipeline / a03_tradingagents_fork / a04_crewai / a05_hierarchical / a06_single_react / a07_blackboard などを planned/idea で予約
  - `architectures/a01_f08_subagent/scenarios/s01_baseline.json`: scenario manifest 形式を確立 (id / playbook / prompts / params / hypothesis)
  - `fixtures/`: 入力スナップショット層。同じ news / technicals を複数 arch / scenario で再利用可能に。`2026-05-19_macro_heavy/` を最初のリアル fixture として整備
  - `fixtures/_helpers/compute_indicators_yfinance.py`: 旧 `runs/.../compute_indicators.py` を汎用化、CLI 引数で fixture 生成可能に
  - `eval/`: 採点ハーネス層を予約 (scorers / reports)。`PortfolioPlan` 出力が揃っているので arch 横断採点が可能
  - `experiments/`: 仮説 × 結論レポート層を予約。eval/reports の生スコアを参照して story を残す
  - 既存 baseline run を `runs/2026-05-19_next_open/a01_f08_subagent/s01_baseline/` へマイグレート。`manifest.json` で arch/scenario/fixture/model/outputs/result_brief を宣言
  - 旧 `playbooks/` ディレクトリは削除（git mv で履歴保持）

- **`playbooks/` サブエージェント実行版（2026-05-18, 後に architecture-first へ移行）— Claude Code サブスクで動かすプロトタイプ**
  - 本実装 (`src/graph/langgraph_impl.py`) 完成までの **二段ロケット戦略の前段**
  - **プロンプトと I/O スキーマは `src/agents/*.py` を単一の正とする**。playbook は「あの SYSTEM_PROMPT を読んで使え」と参照するのみ（二重管理回避）
  - 制約: サブエージェントのモデルが `claude-sonnet-4-6` と一致しない可能性、Bull/Bear マルチターン議論は手動、Web からのニュース取得品質はソース依存
  - 初回試走 (2026-05-19): `runs/2026-05-19_next_open/a01_f08_subagent/s01_baseline/` — Technical 取得失敗で News-only 動作、最終 direction=bearish, P(bear)=0.60, confidence=62

- **差替容易性リファクタ（2026-05-16）— 技術要素のスイッチを 1 ファイル変更で済むように**
  - `src/config/` 設定層を新設。`Settings` / `LLMSettings` を pydantic で定義し、環境変数（`LLM_DEFAULT_MODEL` / `LLM_DEFAULT_MAX_TOKENS` / `LLM_DEFAULT_TEMPERATURE`）から上書き可能。`get_settings()` / `set_settings()` / `reset_settings()` でシングルトン管理。`.env` も自動ロード
  - `src/llm/runner.py` を新設。各エージェントに 5 箇所重複していた LLM 呼出ボイラープレート（CompletionRequest 構築 → complete → JSON パース → Pydantic 検証）を `run_json_agent()` に集約。リトライ・レイテンシ計測・課金記録・プロンプトキャッシュなど横断的関心事を後付けする場所として一元化
  - `src/llm/client.py` の `DEFAULT_MODEL` 直書きを廃止。`CompletionRequest` の model / max_tokens / temperature は `Field(default_factory=...)` で config から取得し、テストでは `set_settings()` で差替できるようにした
  - 5 エージェント（News / Technical / Sentiment Aggregator / Researchers / Portfolio Manager）を runner 経由に書き換え。各 `analyze()` は 4 行に短縮。既存テストは無修正で全件パス
  - `src/graph/orchestrator.py` を新設。`PredictionRequest` + `Orchestrator` Protocol + `StubOrchestrator` + `get_orchestrator()`。LangGraph 実装着手前に IF を確定させ、LangGraph → CrewAI → 自作 への乗換コストを最小化する設計
  - `pyproject.toml` の wheel packages に `src/config` を追加

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
  - `tests/test_config.py`: デフォルト値・シングルトン・set/reset・env 上書き
  - `tests/test_llm_runner.py`: ランナーの検証 / post_process / 不正 JSON / スキーマ違反 / settings デフォルト・明示 override / system & user の引き渡し
  - `tests/test_orchestrator.py`: `StubOrchestrator` の既定プラン・canned プランの horizon 上書き・`get_orchestrator()` の戻り型
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

- [x] **`a01_f08_subagent/playbook.md` を 1 回走らせる（サブエージェント実行版の動作確認）**
  - 初回試走 完了 (2026-05-19): direction=bearish, P(bear)=0.60, confidence=62, Technical 抜きで News-only
  - 観察: 並列実行は機能、サブエージェント JSON 厳格出力 OK、network 制約で Technical 取得不能、`horizon` は手動補完
  - 詳細: `runs/2026-05-19_next_open/a01_f08_subagent/s01_baseline/summary.md`

- [ ] **次に試したい scenario / architecture を切る**
  - **s02_2round_debate**: Bull/Bear 議論を 2 ラウンドに増やす（同 fixture で baseline と比較）
  - **s03_news_root_cause**: News Analyst のプロンプトを「結果記事より原因記事優先」に改修
  - **s04_news_by_category**: News をカテゴリ別に分割 → Sentiment Aggregator を活用
  - **a02_langgraph_pipeline**: LangGraph 本実装。`Orchestrator` Protocol 準拠で同 fixture で a01 と比較

- [ ] **eval ハーネスの最小実装**
  - `fixtures/2026-05-19_macro_heavy/label.json` に実際の翌寄付値を埋める（後日判明）
  - `eval/scorers/directional_accuracy.py` を最小実装
  - 多 run 揃ったら `experiments/exp001_*/matrix.md` で横断比較

- [ ] **オーケストレーション (src/graph/) の LangGraph 実装 = a02_langgraph_pipeline**
  - a01 で有効と判明したフロー・プロンプトを本実装に昇格させる
  - IF は `graph/orchestrator.py` の `Orchestrator` Protocol で固定済み
  - 具象実装 (`graph/langgraph_impl.py` など) を追加し、`get_orchestrator()` で差替
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
| 2026-05-16 | `4fb2dc3` | Portfolio Manager + `PortfolioPlan` / `DirectionProbabilities` 型追加 |
| 2026-05-16 | `89e1090` | 差替容易性リファクタ: `src/config/` + `llm/runner.py` + `graph/orchestrator.py` Protocol |
| 2026-05-18 | `08f5b25` | `playbooks/predict.md` + `runs/` — サブエージェント実行版プロトタイプ |
| 2026-05-19 | `914f46f` | `runs/2026-05-19_next_open/` 初回試走 (direction=bearish, P=0.60, conf=62) |
| 2026-05-19 | `8f52609` | architecture-first リストラ: `architectures/` + `fixtures/` + `eval/` + `experiments/` 層導入、a01 マイグレート |
| 2026-05-21 | (pending) | 構造改善 13 項目: runs パス再編 / versioning (git_sha + prompts_hash + run_id) / variants グローバル化 / YAML 化 / ActualOutcome / 命名統一 等 |

---

## 参考リンク

- [SPEC.md](./SPEC.md) — 仕様書
- [RESEARCH.md](./RESEARCH.md) — 設計・調査ログ
