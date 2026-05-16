# プロジェクトステータス

最終更新: 2026-05-10
ブランチ: `claude/nikkei-futures-spec-n8Gi6`

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

- **テスト**
  - `tests/test_llm_client.py`: StubClient エコー・カスタム responder・get_client 切替・JSON パース 5 ケース
  - `tests/test_news_analyst.py`: スタブ経由のメモ生成・JSON フェンス対応・プロンプト内容検証・スキーマ検証エラー
  - `pyproject.toml` に `pythonpath = ["src"]` を追加（`uv sync` 後に `uv run pytest` で動作する）

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
  - Technical Analyst（テクニカル指標から方向性メモ）
  - Sentiment Aggregator（複数 News Analyst 出力を集約）
  - Researcher Bull / Bear（議論型）
  - Portfolio Manager（最終シナリオ統合）

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
| 2026-05-08 | `537cbc6` | STATUS.md コミットハッシュのバックフィル |
| 2026-05-08 | `4baad00` | `src/` ツリーと依存（uv + hatchling）の初期セットアップ |
| 2026-05-10 | `3440480` | `src/llm/client.py` LLM 抽象 + News Analyst + tests |

---

## 参考リンク

- [SPEC.md](./SPEC.md) — 仕様書
- [RESEARCH.md](./RESEARCH.md) — 設計・調査ログ
