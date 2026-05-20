# runs/

`playbooks/` の実行結果（入力スナップショット + 各エージェント出力 + 最終プラン）の保存先。

## ディレクトリ命名

```
runs/<date>_<horizon>/
```

例: `runs/2026-05-19_open_today/`

複数 symbol を同時に扱うようになったら `runs/<date>_<horizon>_<symbol>/` に拡張する。

## 中身

`playbooks/predict.md` 実行時:

| ファイル | 内容 | スキーマ |
|---|---|---|
| `inputs.json` | 取得した news / indicators / params | `PredictionRequest` 相当 + 追加 |
| `01_news.json` | News Analyst 出力 | `DirectionalMemo` |
| `02_technical.json` | Technical Analyst 出力 | `DirectionalMemo` |
| `03_sentiment.json` | Sentiment Aggregator 出力（任意） | `DirectionalMemo` |
| `04_bull.json` | Bull Researcher 出力 | `DirectionalMemo` |
| `04_bear.json` | Bear Researcher 出力 | `DirectionalMemo` |
| `05_plan.json` | 最終シナリオ | `PortfolioPlan` |
| `summary.md` | Claude の解説と免責 | - |

## git で追跡する理由

- プロンプトを `src/agents/*.py` で改修した時、出力がどう変わるかを diff で見られる
- 「このプロンプトはこういう入力に強い / 弱い」のレグレッションを観察できる
- 検証ログとして残し、本実装移植時の「期待値」として参照できる

大量に溜まったら古いものを別ブランチ or アーカイブに退避する運用で良い。

## 注意

- 個人情報・取引履歴・実際のポジションサイズなどは絶対に置かない（公開リポジトリ前提）
- 投資判断には**使わない**。あくまでプロンプト・フロー検証のログ
