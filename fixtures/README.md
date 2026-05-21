# fixtures/

予測パイプラインへの **入力スナップショット**。同じ入力を複数 architecture / scenario で
試せるように切り出した層。「入力品質」と「判断品質」を分離して議論できるようにする。

## ディレクトリ命名

`<date>_<short_label>/`

例:
- `2026-05-19_macro_heavy/` — 米金利上昇・原油高・日銀タカ派観測の重い日
- `2026-05-19_calm/` (将来)
- `2026-09-20_boj_day/` (将来) — 日銀会合当日

## ファイル

| ファイル | 内容 | スキーマ |
|---|---|---|
| `news.json` | ニュース配列 | `data.news.NewsItem` 互換 |
| `technicals.json` | TechnicalIndicators + recent_bars | `agents.technical_analyst.TechnicalIndicators` |
| `technicals_failed.json` | 取得失敗マーカー（technicals.json の代わり） | 自由形式 |
| `fixture.json` | 収集日時・方法・カバー期間・データ品質メモ | 自由形式 |
| `label.json` | 実際の翌寄付値（後日埋め、eval 用） | `agents.types.ActualOutcome` |

`technicals.json` か `technicals_failed.json` のどちらか一方が存在する。

### label.json のスキーマ

`src/agents/types.py` の `ActualOutcome` 型に準拠:

```json
{
  "horizon": "next_open",
  "actual_direction": "bearish",
  "actual_open": 60500.0,
  "actual_close": 60815.0,
  "open_return": -0.0052,
  "note": "Nikkei.co.jp 公式値より"
}
```

`uv run python -c "from agents.types import ActualOutcome; ActualOutcome(**json.load(...))"`
で検証可能。

## なぜ fixture を切るのか

1. **再取得コスト削減**: ニュース収集サブエージェントは 4 分前後かかる。同じ入力で複数 arch /
   scenario を試したいので、1 度取得して再利用
2. **公平比較**: 全 architecture が同じ fixture を読めば、出力差はアーキテクチャ・プロンプト
   起因に絞れる
3. **再現性**: WebSearch 経由のニュース取得は同じクエリでも結果がブレうる。スナップショット化
   すれば再現可能
4. **network 制約環境対応**: yfinance などが弾かれる環境でも、既存 fixture でテストできる

## 新 fixture を作るとき

1. `<date>_<label>/` ディレクトリを切る
2. `news.json` を収集（サブエージェントに WebSearch 渡す or 手動入力）
3. `technicals.json` を計算（`tools/compute_indicators_yfinance.py` か手動）
4. `fixture.json` に収集方法・期間・品質メモを記録
5. 後日、実際の値が判明したら `label.json` を `ActualOutcome` 形式で埋める（eval で参照）

## ヘルパー (`tools/`)

- `tools/compute_indicators_yfinance.py`: yfinance で OHLCV を取って TechnicalIndicators を
  計算。network allowlist で yahoo finance が通る環境で使用

```bash
uv run python fixtures/tools/compute_indicators_yfinance.py \
  --symbol ^N225 --as-of 2026-05-18T15:15:00+09:00 --horizon next_open \
  --out fixtures/2026-05-19_macro_heavy/technicals.json
```
