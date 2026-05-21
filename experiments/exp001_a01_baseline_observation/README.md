# exp001_a01_baseline_observation

## 仮説

a01_f08_subagent (Claude Code サブエージェントで F-08 を手動オーケスト) が、
Claude Code セッションのサブスク内で end-to-end に動作し、`PortfolioPlan` 形式の
最終出力を生成できることを確認する。

特に以下を観察:
- サブエージェントの並列起動が機能するか (Bull/Bear)
- JSON 厳格出力が実現できるか (プロンプトでの強調の効果)
- ネットワーク制約環境でのデータ取得制限がどう影響するか
- 各エージェントの出力が `src/agents/types.py` のスキーマで検証可能か

## 設計

- **対象 arch**: a01_f08_subagent only (比較対象なし、起動確認が主目的)
- **scenario**: s01_baseline のみ
- **fixture**: 2026-05-19_macro_heavy (米金利・原油・日銀の重い日)
- **run 数**: 1 (baseline_run)

## 結果サマリ

| 観点 | 結果 |
|---|---|
| 動作 | 完走 ✅ |
| 出力 direction | bearish |
| P(bearish) | 0.60 |
| confidence | 62 |
| 並列実行 | 機能した (Bull/Bear) |
| JSON 出力 | 厳格 ✅ |
| Technical Analyst | スキップ (fixture technicals_failed) |
| label.json | pending (実際の翌寄付値、後日埋め) |

詳細は `report.md` と
`runs/2026-05-19_macro_heavy/next_open/a01_f08_subagent/s01_baseline/baseline_run/summary.md`

## 結論

- a01 は **動作する** ことを確認。Technical 抜きでも F-08 の他 5 役は機能した
- ただし F-08 設計の半分しか動作していない (Technical 取得には allowlist 拡張 or 外部実行が必要)
- プロンプトの観察: News Analyst が key_drivers に「市場サマリー記事」を選びがち
  → s03_news_root_cause で改善検証する価値あり
- Bull/Bear 1 ラウンド議論だと反論機会が無い → s02_2round_debate で確認価値あり

## 次のアクション

1. s02_2round_debate を実装して同 fixture で再走、Bear の confidence 変化を確認
2. label.json (実際の 5/19 寄付値) が判明したら scores.json を埋め、eval/scorers で採点
3. a02_langgraph_pipeline 実装後、同 fixture で並列比較 (exp002 として独立)
