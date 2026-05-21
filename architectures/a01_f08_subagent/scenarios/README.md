# scenarios カタログ (a01_f08_subagent)

a01 内で試す scenario の一覧。各 `sNN_*.yaml` の概要と現状をここに集約する。

## 状態の意味

- `active`: 現在試行中、または採用済み
- `archived`: 試したが採用しなかった（履歴として残す）
- `planned`: 着想だけ、未実装

## 一覧

| ID | タイトル | 状態 | 仮説 | 結論 |
|---|---|---|---|---|
| `s01_baseline` | F-08 baseline (5 agents, 1-round) | active | F-08 を最小構成で 1 回流す | 走ったが Technical 不在で半分動作 (`runs/2026-05-19_macro_heavy/next_open/a01_f08_subagent/s01_baseline/baseline_run/` 参照) |
| `s02_2round_debate` | Bull/Bear 議論を 2 ラウンド | active | 反論機会で Bear の過信 (78) を抑制できる | **部分確認**: Bear 78→74、Bull 58→58、P(bear) 0.60→0.52、confidence 62 維持。詳細は `runs/.../s02_2round_debate/20260521T030000Z/summary.md` |
| `s03_news_root_cause` | News Analyst プロンプト改修 (原因記事優先) | active | key_drivers から結果記事を排除し原因記事を選ばせる | (試行中) |
| `s04_news_by_category` | News をカテゴリ別に分割 → Sentiment Aggregator 活性化 | planned | カテゴリ別 News Analyst の独立判断で signal がブレない | - |
| `s05_no_technical` | Technical 抜きで PM | planned | データ欠損日でも動くか確認 | - |

## 新 scenario を追加するとき

1. `sNN_<slug>.yaml` を切る（連番）
2. `based_on` で派生元 scenario を指定（baseline = null）
3. `prompts` で variant 差替を指定（`src/agents/variants/<agent>/<variant>.md`）
4. `params` で arch 内の knob を変更
5. `hypothesis` に「何を検証したいか」を 1-3 行で
6. 走らせて `runs/<fixture_id>/<horizon>/a01_f08_subagent/<scenario_id>/<run_id>/` に出力
7. このカタログの表に行追加
8. 結果が固まったら `archived` か canonical 採用かを判断

## archive 運用

採用しないと決めた scenario も削除せず、`status: archived` にして yaml に
`archived_at` と `archive_reason` を追加して残す。履歴として diff で追えるようにする。
