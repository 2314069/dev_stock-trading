# experiments/

複数 run を横断する **仮説 × 結論レポート** の置き場。`eval/reports/` の生スコアを参照して
「何を試して何が分かったか」を物語形式でまとめる。

## ディレクトリ命名

`exp<NNN>_<short_topic>/` （連番）

例:
- `exp001_arch_shootout/` — a01 vs a02 vs a03 を同 fixture で比較
- `exp002_debate_rounds_ablation/` — a01 内で議論ラウンド数を 1/2/3
- `exp003_prompt_root_cause/` — News Analyst プロンプトを root_cause 寄りに改修
- `exp004_news_split_by_category/` — News を分割して Sentiment Aggregator を活かす

## 中身

| ファイル | 内容 |
|---|---|
| `README.md` | 仮説・対照群・実験設計・期待される観察 |
| `matrix.md` | 結果表（run へのリンク） |
| `conclusion.md` | 結論・採用 / 却下判断・次アクション |

## experiments と runs / eval の関係

```
fixtures/<id>/                  ← 入力 (1 個)
runs/<date>/<arch>/<scenario>/  ← 実行結果 (N 個)
eval/reports/<date>_xxx.md      ← 生スコア表
experiments/expNNN_xxx/         ← 仮説 + 結論 (story 形式)
```

`experiments/` は人間（や将来の私）が読んで意思決定するためのもの。「なぜこのプロンプト改修を
採用したか」「なぜこの arch を archive 行きにしたか」の根拠を残す層。

## 現状

未実装。a01 の baseline 1 件しか走っていないため、まず比較対象を作るところから。
