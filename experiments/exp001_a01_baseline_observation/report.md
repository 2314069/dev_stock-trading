# exp001 レポート: a01 baseline 試走

## 入力

| 項目 | 値 |
|---|---|
| Architecture | `a01_f08_subagent` (Claude Code サブエージェント版) |
| Scenario | `s01_baseline` (F-08 5 agents, 1-round debate) |
| Fixture | `2026-05-19_macro_heavy` (米金利上昇・原油高・日銀タカ派の重い日) |
| Symbol | `^N225` |
| Horizon | `next_open` (2026-05-19 寄付) |
| As-of | 2026-05-18T15:15:00+09:00 |

## 各エージェント出力

| Agent | direction | confidence |
|---|---|---|
| News Analyst | bearish | 72 |
| Technical Analyst | — (SKIPPED) | — |
| Bull Researcher | bullish | 58 |
| Bear Researcher | bearish | 78 |
| Portfolio Manager | **bearish** | **62** |

## 最終出力 (PortfolioPlan)

| 項目 | 値 |
|---|---|
| direction | bearish |
| P(bullish) | 0.22 |
| P(neutral) | 0.18 |
| P(bearish) | **0.60** |
| confidence | 62 |

Top drivers:
1. 米長期金利上昇 (10年債4.59%, 年内5%観測) + 米株大幅安 (S&P -1.14%, NASDAQ -1.62%)
2. SGX 日経先物 400 円安で寄り付き
3. 中東情勢悪化 (イラン戦争長期化・ホルムズ海峡封鎖懸念) による原油高
4. 日銀タカ派観測 (6月利上げ 55%, JGB 10年 2.7%)
5. 円安加速 + SBG 史上最高益 + アドバンテスト強気見通し (下支え)

## 観察

### 機能した点
- **並列実行**: Bull/Bear を 1 メッセージ内 2 つの Agent tool_use で並列起動 → 別 context で完了 (8 秒・8 秒)
- **JSON 厳格出力**: プロンプト末尾の「厳密な JSON のみ」強調が効いた。全エージェントから直接 `json.loads()` できる形で返答
- **スキーマ整合**: 確率和 = 1.00、direction と最大確率が整合、top_drivers は全て入力メモから採用
- **制約反映**: Technical 不在を考慮して confidence を 62 に下げた (Bear 単体 78 から)

### 判明した制約・改善点
1. **Technical Analyst スキップ**: yfinance / Stooq / FRED など全 finance ソースが network policy で 403。WebSearch も AI 要約で価格不整合 → allowlist 拡張 or 外部実行が必要
2. **`horizon` を LLM が echo しない**: 手動補完が必要。本実装の `runner.post_process` は既対応
3. **News の key_drivers が結果記事に寄る**: 「市場サマリ記事」を選びがち、原因記事を優先する指示が要る (→ s03_news_root_cause)
4. **Bull/Bear 1 ラウンドだと反論機会なし**: confidence が 58 vs 78 で偏った (→ s02_2round_debate)
5. ニュースカテゴリ別分割 + Sentiment Aggregator 活用で個別シグナルがブレなくなる可能性 (→ s04_news_by_category)

## 採点 (pending)

`fixtures/2026-05-19_macro_heavy/label.json` が無いため未採点。実際の翌寄付値が判明次第、
`eval/scorers/directional_accuracy.py` で採点予定。

## 免責

これはプロトタイプ検証ログであり投資助言ではありません。2026 年の市況情報は AI の知識ベース外で、
WebSearch / WebFetch 経由のため未検証情報を含みます。実取引には使用しないでください。
