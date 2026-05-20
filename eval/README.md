# eval/

予測 (`PortfolioPlan`) を採点するハーネス。`fixtures/<id>/label.json`（実際の翌寄付値）と
`runs/<date>/<arch>/<scenario>/05_plan.json` を突合して各種スコアを計算する。

## なぜ共有層なのか

すべての architecture が同じ `PortfolioPlan` を出力するため、スコアラーは arch を意識せず採点
可能。これにより:

- **arch 横断比較**: a01 vs a02 vs a03 を同じ fixture で採点
- **scenario アブレーション**: 同じ arch 内で knob を振った効果を定量化
- **キャリブレーション**: 確率出力 (`direction_probabilities`) の信頼性を Brier score で

## スコア種類（実装予定）

| ファイル | 種類 | 用途 |
|---|---|---|
| `scorers/directional_accuracy.py` | 方向当たり率 | direction (bullish/neutral/bearish) と実際の方向の一致 |
| `scorers/brier_score.py` | Brier score | direction_probabilities のキャリブレーション |
| `scorers/log_loss.py` | 対数損失 | 同上、確率分布全体の質 |
| `scorers/confidence_correlation.py` | confidence と的中率の相関 | confidence が「自信過剰」「自信なさすぎ」を検出 |

## 使い方（将来）

```bash
# 単発採点
uv run python -m eval.score \
  --fixture 2026-05-19_macro_heavy \
  --arch a01_f08_subagent \
  --scenario s01_baseline

# arch 横断
uv run python -m eval.shootout --fixture 2026-05-19_macro_heavy
```

## レポート

`reports/<date>_<topic>.md` に採点結果を蓄積。`experiments/` と違い、こちらは **生スコア表** に
近い性質。`experiments/` の結論レポートは reports を参照して書く。

## 現状

未実装。優先順:

1. `fixtures/<id>/label.json` を 1 件埋める（2026-05-19 の実際の値）
2. `scorers/directional_accuracy.py` を最小実装
3. 第 2 arch (a02) が出来てから shootout を整備
