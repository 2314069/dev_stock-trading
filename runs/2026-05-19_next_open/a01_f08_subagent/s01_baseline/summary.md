# 予測サマリ: 2026-05-19 next_open (^N225)

**playbook**: `playbooks/predict.md`
**実行**: Claude Code (web) サブエージェント版プロトタイプ
**as_of**: 2026-05-18T15:15:00+09:00

---

## 入力

| 項目 | 値 |
|---|---|
| ニュース件数 | 25 |
| 期間 | 2026-04-20 〜 2026-05-18 |
| テクニカル指標 | **取得失敗**（network policy で全 finance ソース 403） |

### 主要トピック（ニュース由来）
- **マクロ（米）**: 4月CPI +3.8% に加速、10年債4.59%、ウォーシュ次期 FRB 議長承認、S&P -1.14%/NASDAQ -1.62%
- **マクロ（日）**: 日銀 6月利上げ観測 55%、真壁委員「早期利上げを」、JGB 10年 2.7%（10年ぶり高水準）、PPI +4.9%
- **地政学・コモディティ**: イラン戦争長期化、ブレント原油一時 111 ドル
- **企業**: SBG 純利益 5 兆円超（史上最高益）、アドバンテスト +25.7% 強気予想、フジクラ -19% ストップ安、トヨタ 27/3 期営業益 -20.3% 予想
- **市場**: 日経 5/15 -1244円(2.0%)、5/18 -593円(0.97%)、3 日続落、SGX 先物 400 円安
- **FX**: USD/JPY 158.90（6 営業日続伸）
- **イベント控え**: 5/19 朝 日本 1Q GDP 速報、5/20 Nvidia 決算

---

## 各エージェント出力

| Agent | direction | confidence | summary |
|---|---|---|---|
| **News Analyst** | bearish | 72 | 米金利上昇・原油高・日銀タカ派の三重苦で 3 日続落。SGX 400 円安、米株安と中東情勢悪化が翌寄付に重し |
| **Technical Analyst** | — | — | **スキップ**（OHLC データ取得不能） |
| **Bull Researcher** | bullish | 58 | 3 日続落と SGX 400 円安で短期過熱解消、円安・SBG 最高益・GDP 速報プラス成長見込みで自律反発余地 |
| **Bear Researcher** | bearish | 78 | 三重苦 + SGX 400 円安 + 米株大幅安 + AI 関連失望売り + Nvidia 決算前様子見で買い手不在 |

---

## 最終 PortfolioPlan

| 項目 | 値 |
|---|---|
| **direction** | **bearish** |
| **P(bullish)** | 0.22 |
| **P(neutral)** | 0.18 |
| **P(bearish)** | **0.60** |
| **confidence** | **62** |

### Scenario
> 米金利上昇・原油高・日銀タカ派の三重苦に加え、SGX 先物 400 円安と米株大幅安を引き継ぎ
> next_open は弱気バイアス継続が濃厚。ただし 3 日続落で短期過熱は解消し円安・SBG 最高益が
> 下支え、テクニカル取得不能の不確実性も残るため下値は限定的となる可能性。

### Bull Case (要旨)
3 日続落と SGX 400 円安で短期過熱が解消し、円安加速と SBG 史上最高益・アドバンテスト強気
見通し、GDP 速報プラス成長確認で自律反発余地が広がる。

### Bear Case (要旨)
米金利上昇・原油高・日銀タカ派の三重苦に SGX 400 円安と米株大幅安が重なり、AI 関連失望売り
と決算前様子見で買い手不在のまま next_open は弱気継続が濃厚。

---

## 観察 / 気付き（プロトタイプ検証の本題）

### 1. サブエージェント並列実行は機能した
- Bull/Bear を 1 メッセージ内 2 つの Agent tool_use で並列起動 → 別々の独立 context で実行され
  別々の通知で返ってきた。本実装 (LangGraph) の並列ノードのモックとして十分機能する
- 各サブエージェントが JSON のみ厳格に返してくれた（プロンプトで強調した効果あり）

### 2. データ層の network 制約が致命的
- yfinance / Stooq / FRED CSV / Yahoo Finance / Google Finance / Investing 全て **403 (Host not in allowlist)**
- WebSearch は通るが AI 要約で **複数クエリ間で価格が不整合**（5/15 vs 5/18 で 600 円差など）→
  Technical Analyst の入力として信頼できない
- 結論: **Technical Analyst を回すには allowlist 拡張 or 外部実行が必要**

### 3. プロンプト設計の課題
- News Analyst が key_drivers に「市場サマリー記事」（5/15・5/18 の日経終値の記事）を選びがち。
  これは記事自体が下げ要因の **説明であって原因ではない** ので、純粋な原因記事（CPI・金利・原油・
  日銀発言）を上位に選ぶプロンプト改善余地あり
- Portfolio Manager の `horizon` は LLM が echo してくれなかった → playbook の規定通り
  手動補完。本実装 (`runner.py` の `post_process`) では既に補完済みなのでこの問題は出ない
- Bull/Bear の confidence が 58 vs 78 で偏った（Bear 優位は妥当だが、Bull はもう少し低くても）→
  「opposing_memo なし」だと相手側論点への反論機会が無いので、**2 ラウンド議論** にすると
  両者 confidence が現実に近づきそう

### 4. 整合性チェック
- direction_probabilities: 0.22 + 0.18 + 0.60 = 1.00 ✅
- direction (`bearish`) と最大確率 (`bearish`=0.60) は整合 ✅
- top_drivers は全て入力メモから採用 ✅
- 制約「テクニカル不在のため confidence を低めに」を反映: 62（Bear 単体の 78 より下げ） ✅

### 5. 本実装移植への示唆
- **News のカテゴリ別分割**を入れると Sentiment Aggregator が活きる。今回は 25 件を一括投入したが、
  「central_bank」「earnings」「geopolitics」等カテゴリ別に News Analyst を並列起動 → Sentiment
  Aggregator で集約、の方が個別シグナルがブレない
- **Bull/Bear 議論ラウンド** を 2-3 周回す価値が高い。1 周だと Bear が単純な root cause 列挙に
  寄りすぎる
- **Technical 抜きでも一応動く** ことが分かったので、本実装でも Technical を optional に
  できる設計が良い（休場日・データ欠損日に強い）

---

## 免責

この予測は **プロトタイプの検証ログ** であり、投資助言ではありません。

- 入力ニュースは WebSearch / WebFetch 経由で取得しており、一部に **未検証情報・要約レベルの
  誤差・架空の事象** が含まれる可能性があります（特に 2026 年付近の事象は AI の知識ベース外）
- テクニカル指標は **取得できておらず**、本来の F-08 設計の半分しか動作していません
- モデルは Claude Code セッションのデフォルト（`src/agents/*.py` の指定 `claude-sonnet-4-6` と
  一致するとは限らない）

実取引には**使用しないでください**。
