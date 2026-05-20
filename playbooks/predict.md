# 予測実行 playbook (F-08 end-to-end, サブエージェント版)

Claude Code の Agent ツールでサブエージェントを並列起動し、F-08 マルチエージェント
パイプライン (News / Technical / Sentiment / Bull / Bear / Portfolio Manager) を
1 回回す手順書。本実装 (`src/graph/langgraph_impl.py`) の代替プロトタイプ。

---

## トリガ例

ユーザ:
> Claude、`playbooks/predict.md` で 2026-05-19 寄付 (`^N225`) の予測やって

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

`runs/<date>_<horizon>/` 以下に成果物を保存:

```
runs/2026-05-19_open_today/
  inputs.json           # PredictionRequest 相当 + 取得した NewsItem / TechnicalIndicators
  01_news.json          # News Analyst → DirectionalMemo
  02_technical.json     # Technical Analyst → DirectionalMemo
  03_sentiment.json     # (任意) Sentiment Aggregator → DirectionalMemo
  04_bull.json          # Bull Researcher → DirectionalMemo
  04_bear.json          # Bear Researcher → DirectionalMemo
  05_plan.json          # Portfolio Manager → PortfolioPlan
  summary.md            # Claude による解説と免責
```

各 JSON は対応する Pydantic スキーマ (`src/agents/types.py`) に従う。

---

## 実行ステップ

### Step 0: 準備

1. `mkdir -p runs/<date>_<horizon>/`
2. 必要なソースを Read し、SYSTEM_PROMPT と入力フォーマッタを確認:
   - `src/agents/types.py`（`DirectionalMemo` / `LabeledMemo` / `PortfolioPlan`）
   - `src/agents/news_analyst.py`（`SYSTEM_PROMPT`, `_build_user_message`）
   - `src/agents/technical_analyst.py`
   - `src/agents/sentiment_aggregator.py`
   - `src/agents/researchers.py`（`BULL_SYSTEM_PROMPT` / `BEAR_SYSTEM_PROMPT`）
   - `src/agents/portfolio_manager.py`
3. 既存の `runs/<date>_<horizon>/` がある場合は上書きの可否をユーザに確認。

### Step 1: データ取得（並列で 2 つ実行）

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

結果を `runs/<date>_<horizon>/inputs.json` の `news` フィールドに保存。

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

結果を `runs/<date>_<horizon>/inputs.json` の `indicators` フィールドに保存。

**注意**: `^N225` は現物指数なので厳密には先物 (`NK=F`) と乖離する。検証段階では妥協し、
本実装で JPX 公式データに差替予定。symbol 選択はユーザ指定に従う。

### Step 2: News Analyst（サブエージェント）

`Agent(subagent_type=general-purpose)` を 1 つ起動:

- **system**: `src/agents/news_analyst.py` の `SYSTEM_PROMPT` をそのまま渡す
- **user**: `NewsAnalysisRequest`(`horizon`, `as_of`, `news`) を
  `_build_user_message()` と同じフォーマットで構築
- **期待出力**: `DirectionalMemo` の JSON 1 つ
- サブエージェントには「JSON のみ出力。前後に説明を付けない」と再強調
- 結果を `runs/<date>_<horizon>/01_news.json` に保存（Pydantic で検証可能な形）

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

### Step 5: Researcher Bull + Bear（並列起動）

`Agent` を **2 つ並列**で起動（1 メッセージ内に 2 つの tool_use ブロックを置く）:

#### Bull
- **system**: `src/agents/researchers.py` の `BULL_SYSTEM_PROMPT`
- **user**: `ResearcherRequest`(`horizon`, `as_of`, `memos=[news, technical]`, `opposing_memo=None`)
- 結果を `04_bull.json` に保存

#### Bear
- **system**: `BEAR_SYSTEM_PROMPT`
- **user**: 同上
- 結果を `04_bear.json` に保存

`memos` は `LabeledMemo` 配列:
```json
[
  {"label": "news", "memo": <01_news.json の中身>},
  {"label": "technical", "memo": <02_technical.json の中身>}
]
```

将来の議論ラウンド拡張: Bull/Bear をもう 1 ラウンド回す場合、各々の前回出力を
`opposing_memo` に入れて再起動。最大 N ラウンド。

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

`runs/<date>_<horizon>/summary.md` に以下をまとめる:

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

ユーザ向けには `05_plan.json` の要約と「`runs/<date>_<horizon>/` に保存しました」を返す。

---

## 反復のヒント

| やりたいこと | 操作 |
|---|---|
| プロンプトを変える | `src/agents/<name>.py` の `SYSTEM_PROMPT` を編集（本実装と共通） |
| 入力データの形を変える | `src/agents/<name>.py` の Pydantic スキーマと `_build_user_message` を編集 |
| 別ホライゾンで試す | このコマンドを `horizon` 違いで再実行 |
| プロンプト変更の効果を見る | `git diff runs/` で過去 run と比較 |
| 議論ラウンドを増やす | Step 5 を `opposing_memo` 付きでもう 1 周実行 |

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
