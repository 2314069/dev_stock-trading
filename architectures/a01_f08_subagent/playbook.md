# a01_f08_subagent: F-08 end-to-end playbook

Claude Code の Agent ツールでサブエージェントを並列起動し、F-08 マルチエージェント
パイプライン (News / Technical / Sentiment / Bull / Bear / Portfolio Manager) を
1 回回す手順書。本実装 (`src/graph/langgraph_impl.py` = `a02_langgraph_pipeline`) 完成までの
プロトタイプ architecture。

---

## トリガ例

ユーザ:
> Claude、`architectures/a01_f08_subagent/playbook.md` で
> scenario=`s01_baseline`、fixture=`fixtures/2026-05-19_macro_heavy/` を走らせて

シナリオ指定がない場合は `s01_baseline` を既定。fixture 指定がない場合は Step 1 で新規収集。

---

## 入力パラメータ

| 項目 | 型 | 例 | 既定 |
|---|---|---|---|
| `date` | str (YYYY-MM-DD) | `2026-05-19` | 必須 |
| `horizon` | `agents.types.Horizon` | `open_today` | 必須 |
| `symbol` | str | `^N225` / `NK=F` / `1321.T` | `^N225` |
| `as_of` | ISO8601 datetime | `2026-05-18T15:00:00+09:00` | 直近の取引終了時刻 |

`horizon` 候補（`src/agents/types.py`）:
- `open_today` / `close_today` / `afternoon_open`
- `night_open` / `night_close` / `next_open`

---

## 出力

`runs/<fixture_id>/<horizon>/a01_f08_subagent/<scenario_id>/<run_id>/` 以下に成果物を保存:

```
runs/2026-05-19_macro_heavy/next_open/a01_f08_subagent/s01_baseline/<run_id>/
  manifest.json         # 何を使ったか宣言 (arch / scenario / fixture / git_sha / prompts_hash / run_id)
  01_news.json          # News Analyst → DirectionalMemo
  02_technical.json     # Technical Analyst → DirectionalMemo
  03_sentiment.json     # (任意) Sentiment Aggregator → DirectionalMemo
  04_bull.json          # Bull Researcher → DirectionalMemo
  04_bear.json          # Bear Researcher → DirectionalMemo
  05_plan.json          # Portfolio Manager → PortfolioPlan
  summary.md            # Claude による解説と免責
```

`<run_id>` はタイムスタンプベース (`YYYYMMDDTHHMMSSZ`) か、特別な run には slug
(`baseline_run` 等)。同じ scenario × fixture を別 prompts_hash で再実行できるようにする。

各 JSON は対応する Pydantic スキーマ (`src/agents/types.py`) に従う。

入力 (NewsItem / TechnicalIndicators) は `fixtures/<id>/` に置く（複数 arch / scenario で
再利用するため、run 配下には置かない）。

---

## 実行ステップ

### Step 0: 準備

1. `<run_id>` を決定（既定は `date +%Y%m%dT%H%M%SZ` の UTC タイムスタンプ）
2. `mkdir -p runs/<fixture_id>/<horizon>/a01_f08_subagent/<scenario_id>/<run_id>/`
3. `architectures/a01_f08_subagent/scenarios/<scenario_id>.yaml` を Read し
   - `params` (debate_rounds / news_split_by_category / skip_* 等) を確認
   - `prompts` で差替指定があれば該当 `src/agents/variants/<agent>/<variant>.md` を Read
4. 必要なソースを Read し、SYSTEM_PROMPT と入力フォーマッタを確認:
   - `src/agents/types.py`（`DirectionalMemo` / `LabeledMemo` / `PortfolioPlan` / `ActualOutcome`）
   - `src/agents/news_analyst.py`（`SYSTEM_PROMPT`, `_build_user_message`）
   - `src/agents/technical_analyst.py`
   - `src/agents/sentiment_aggregator.py`
   - `src/agents/researchers.py`（`BULL_SYSTEM_PROMPT` / `BEAR_SYSTEM_PROMPT`）
   - `src/agents/portfolio_manager.py`
5. `prompts_hash` を計算（`src/agents/*.py` を SHA256 連結、先頭 16 桁）と `git_sha`
   (`git rev-parse --short HEAD`) を取得し、manifest 用に控える

### Step 1: データ取得（並列で 2 つ実行、または fixture 読込）

**fixture モード**: `fixtures/<id>/` 指定があれば `news.json` / `technicals.json` を読み、
1A/1B はスキップして Step 2 へ。`technicals_failed.json` があれば Technical Analyst をスキップ
（scenario の `params.skip_technical_if_unavailable=true` のとき）。

**fresh モード** (fixture 未指定): 1A/1B を実行し、結果を新規 `fixtures/<date>_<auto_label>/` に
保存（再利用可能化）。

#### 1A. ニュース収集（WebSearch / WebFetch サブエージェント）

`Agent(subagent_type=general-purpose)` を 1 つ起動し、以下を依頼:

- `as_of` までの 24-48 時間に発生した **日経 225 先物に影響しうる** ニュースを収集
- 優先ソース（impact 高い順）:
  - 中央銀行: 日銀 / FOMC / ECB / 中国人民銀
  - 経済指標: 米雇用統計 / CPI / GDP / 日本 CPI / 鉱工業生産
  - 米国市場: NY ダウ / S&P500 / ナスダック前日終値・先物
  - 為替: USD/JPY / EUR/JPY
  - 主要企業: 日経採用銘柄の決算 / TOPIX core30
  - 地政学: 戦争 / 制裁 / 主要国選挙
- 出力フォーマット: `data.news.NewsItem` 互換の JSON 配列
  ```json
  [
    {
      "headline": "...",
      "summary": "...",
      "source": "Reuters" | "Bloomberg" | "日経" | ...,
      "url": "...",
      "timestamp": "2026-05-18T13:30:00+09:00",
      "sentiment": -1.0 から +1.0,
      "impact": "low" | "medium" | "high",
      "categories": ["central_bank", "us_market", ...]
    }
  ]
  ```
- 件数目安: 10-30 件。信頼性低いもの・重複は除外
- 投機的・憶測ベースの記事は impact を下げる

結果を `fixtures/<新 id>/news.json` に保存（fresh モードのみ）。

#### 1B. テクニカル指標取得

`yfinance` で `symbol` の OHLCV を取得し、`TechnicalIndicators`
(`src/agents/technical_analyst.py`) を構築:

- 直近 250 営業日の日足を取得（200SMA 計算のため）
- 必要指標:
  - `last_price` / `prev_close`
  - `sma_5`, `sma_25`, `sma_75`, `sma_200`
  - `rsi_14` (Wilder の RSI)
  - `macd` (EMA12 - EMA26), `macd_signal` (EMA9 of MACD)
  - `bollinger_width` (上限 - 下限 / 中央; 25日 2σ)
  - `atr_14`
  - `ichimoku_cloud_position`: 終値と先行スパン A/B 上限・下限の関係から `above` / `inside` / `below`
  - `overnight_return`: 取得不可なら None
- 計算できない指標は `None` のまま
- 任意: `recent_bars` に直近 5-10 本の足を `FuturesBar` 形式で添える

結果を `fixtures/<新 id>/technicals.json` に保存（fresh モードのみ）。失敗時は
`fixtures/<新 id>/technicals_failed.json` に失敗理由を残す。

**注意**: `^N225` は現物指数なので厳密には先物 (`NK=F`) と乖離する。検証段階では妥協し、
本実装で JPX 公式データに差替予定。symbol 選択はユーザ指定に従う。

### Step 2: News Analyst（サブエージェント）

`Agent(subagent_type=general-purpose)` を 1 つ起動:

- **system**: `src/agents/news_analyst.py` の `SYSTEM_PROMPT` をそのまま渡す
- **user**: `NewsAnalysisRequest`(`horizon`, `as_of`, `news`) を
  `_build_user_message()` と同じフォーマットで構築
- **期待出力**: `DirectionalMemo` の JSON 1 つ
- サブエージェントには「JSON のみ出力。前後に説明を付けない」と再強調
- 結果を `runs/<fixture_id>/<horizon>/a01_f08_subagent/<scenario_id>/<run_id>/01_news.json` に保存（Pydantic で検証可能な形）

ニュースを **カテゴリ別** に複数サブエージェントで走らせる拡張は将来。今は 1 つに統合して投入。

### Step 3: Technical Analyst（Step 2 と並列起動可）

`Agent(subagent_type=general-purpose)`:

- **system**: `src/agents/technical_analyst.py` の `SYSTEM_PROMPT`
- **user**: `TechnicalAnalysisRequest`(`horizon`, `as_of`, `symbol`, `indicators`, `recent_bars`) を
  `_build_user_message()` 形式で構築
- 結果を `02_technical.json` に保存

### Step 4: Sentiment Aggregator（条件付き）

`01_news.json` が 1 つしかない現状ではスキップ可。将来カテゴリ別 News を走らせるように
なったら有効化。スキップ時は News の memo をそのまま下流に渡す。

実行する場合:
- **system**: `src/agents/sentiment_aggregator.py` の `SYSTEM_PROMPT`
- **user**: `SentimentAggregationRequest`(`horizon`, `as_of`, `memos=LabeledMemo[]`)
- 結果を `03_sentiment.json` に保存

### Step 5: Researcher Bull + Bear（並列起動、scenario.params.debate_rounds 回繰返）

`Agent` を **2 つ並列**で起動（1 メッセージ内に 2 つの tool_use ブロックを置く）。
`debate_rounds=N` の場合、以下を N 回繰り返す（2 回目以降は前回の相手出力を `opposing_memo` に渡す）。

#### Bull
- **system**: `src/agents/researchers.py` の `BULL_SYSTEM_PROMPT`（または scenario.prompts.researcher_bull）
- **user**: `ResearcherRequest`(`horizon`, `as_of`, `memos=[news, technical]`, `opposing_memo=<前回の bear 出力 or None>`)
- 結果を `04_bull.json` （単発）または `04_bull_r{N}.json` （議論モード）に保存

#### Bear
- **system**: `BEAR_SYSTEM_PROMPT`（または scenario.prompts.researcher_bear）
- **user**: 同上、`opposing_memo=<前回の bull 出力 or None>`
- 結果を `04_bear.json` または `04_bear_r{N}.json` に保存

`memos` は `LabeledMemo` 配列:
```json
[
  {"label": "news", "memo": <01_news.json の中身>},
  {"label": "technical", "memo": <02_technical.json の中身>}
]
```

議論ラウンド最終出力（=最後の round の memo）を Step 6 に渡す。

### Step 6: Portfolio Manager

`Agent(subagent_type=general-purpose)`:

- **system**: `src/agents/portfolio_manager.py` の `SYSTEM_PROMPT`
- **user**: `PortfolioRequest`(`horizon`, `as_of`, `symbol`, `memos`, `bull_memo`, `bear_memo`)
  - `memos`: news / technical の `LabeledMemo` 群
  - `bull_memo` / `bear_memo`: Step 5 の出力
- 出力: `PortfolioPlan`。ただし `horizon` は req から埋めるので、LLM が echo しなかった
  場合は手動で補完
- 結果を `05_plan.json` に保存

### Step 7: 報告

`runs/<fixture_id>/<horizon>/a01_f08_subagent/<scenario_id>/<run_id>/manifest.json` を書く:

```json
{
  "run_id": "...",
  "executed_at": "ISO8601",
  "git_sha": "<git rev-parse --short HEAD の結果>",
  "prompts_hash": "sha256:<16 桁>",
  "architecture": {"id": "a01_f08_subagent", ...},
  "scenario": {"id": "...", "ref": "architectures/.../scenarios/<id>.yaml"},
  "fixture": {"id": "...", "ref": "fixtures/<id>/"},
  "request": {...}, "models": {...}, "outputs": {...}, "result_brief": {...}, "notes": "..."
}
```

同ディレクトリの `summary.md` に以下をまとめる:

```markdown
# 予測サマリ: <date> <horizon> <symbol>

## 入力
- ニュース件数: N
- 主要トピック: ...
- テクニカル: last=..., RSI=..., MACD=...

## 各エージェント出力
- News Analyst: direction=..., confidence=...
- Technical Analyst: direction=..., confidence=...
- Bull: ...
- Bear: ...

## 最終 PortfolioPlan
- direction: ...
- probabilities: bullish=..., neutral=..., bearish=...
- confidence: ...
- top_drivers: ...
- scenario: ...

## 観察 / 気付き
（プロンプトの効き方、入力品質、矛盾の有無など）

## 免責
このプロンプトはプロトタイプ検証用です。投資助言ではありません。実取引には使用しないでください。
```

ユーザ向けには `05_plan.json` の要約と保存先パスを返す。

---

## 反復のヒント

| やりたいこと | 操作 |
|---|---|
| canonical プロンプト改修 | `src/agents/<name>.py` の `SYSTEM_PROMPT` 編集（本実装と共通）→ 新 scenario で試走 |
| プロンプトのバリアントを試す | `src/agents/variants/<agent>/<variant>.md` を作成（arch 横断で再利用可）→ 新 scenario の `prompts.<agent>` で参照 |
| フロー違いを試す | 新 scenario の `params` で `debate_rounds` / `news_split_by_category` 等を変更 |
| 別 fixture で試す | `fixtures/<別 id>/` を指定して再実行 |
| 別日付・別 horizon | `as_of` / `target_date` / `horizon` を変えて実行 |
| 別 architecture と比較 | `architectures/<別 arch>/` を実装、同 fixture で走らせて `eval/` で採点 |

---

## 既知の落とし穴

- **サブエージェントが JSON 以外を喋る**: 「JSON のみ」を再強調して再起動。または
  サブエージェントの出力から正規表現で JSON 部分だけ抽出。
- **ニュースの impact / sentiment 推定が雑**: WebSearch ベースなので元記事の本文まで
  読まないとブレる。重要な記事は WebFetch で本文取得を指示する。
- **yfinance の `^N225` データが取れない**: 代替 `NK=F` or `1321.T` を試す。
  休場日の `as_of` も注意。
- **モデルバージョン差**: サブエージェントのモデルが `claude-sonnet-4-6` と
  違う場合、`src/agents/*.py` で観察される挙動と乖離する可能性。
