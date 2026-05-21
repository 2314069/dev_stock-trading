# src/agents/variants/

各 agent の **プロンプトバリアント置き場**。canonical (`src/agents/<agent>.py` の
`SYSTEM_PROMPT`) からの差分プロンプトを実験するための層。

## 構造（将来）

```
src/agents/variants/
  news_analyst/
    root_cause.md       # 結果記事を抑制、原因記事を優先するバリアント
    central_bank.md     # 中銀発言を最重視
  researchers/
    bull_aggressive.md  # Bull の confidence 上限を緩める
    bear_conservative.md
  portfolio_manager/
    high_uncertainty.md # データ欠損時の確率分布をより neutral 寄せ
```

## 参照方法

`architectures/<arch>/scenarios/<scenario>.yaml` の `prompts.<agent>` で
ファイルパスを指定:

```yaml
prompts:
  news_analyst: src/agents/variants/news_analyst/root_cause.md
  researcher_bull: src/agents/variants/researchers/bull_aggressive.md
```

`null` の場合は canonical を使う。

## なぜ arch ローカルではなく src/ 配下に置くか

- 同じプロンプト改修を複数 arch (a01 / a02 / a03) で試したいことが多い
- canonical との対比を見たいので、すぐ隣のディレクトリにある方が改修時に便利
- 「プロンプトの単一の正は src/agents/」という原則と整合
