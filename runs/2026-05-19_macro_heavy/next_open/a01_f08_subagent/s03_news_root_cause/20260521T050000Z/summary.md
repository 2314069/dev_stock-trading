# 予測サマリ: s03_news_root_cause (2026-05-19 next_open, ^N225)

**arch**: a01_f08_subagent
**scenario**: s03_news_root_cause (News Analyst プロンプト改修 — 原因記事優先)
**fixture**: 2026-05-19_macro_heavy
**run_id**: 20260521T050000Z

---

## 仮説

s01_baseline 走行時、News Analyst の key_drivers に「日経平均 593 円安で 3 日続落」「米国株 5/15
大幅下落」など **市場サマリ記事 (= 価格動向そのものを伝える結果記事)** が並んでいた。
これらは下落の **結果の説明であって原因ではない** ため、根本要因 (CPI・金利・中銀発言・
地政学イベント) を優先する制約を追加する。

期待:
- key_drivers から結果記事が消える
- 代わりに原因記事が並ぶ
- direction / confidence は s01 から大きく変わらないはず（情報量同等）
- 大きく変わるなら、結果記事に判断が引きずられていた証拠

## 各エージェント出力

| Agent | s01 結果 | s03 結果 | 変化 |
|---|---|---|---|
| News Analyst | bearish, 72 (結果記事多め) | bearish, **72** (原因記事のみ) | direction/confidence 同、**質改善** |
| Bull Researcher | bullish, 58 | bullish, **58** | 同 |
| Bear Researcher | bearish, 78 | bearish, **78** | 同 |

## key_drivers の質的変化 (本検証の主目的)

### s01_baseline (結果記事 3/5)
1. 日経平均5月18日終値593円安、3日続落 ❌ 結果
2. 米国株5月15日大幅下落、S&P500 -1.14% ❌ 結果
3. 米10年債利回り 4.59% へ上昇 ⚠ やや結果寄り
4. イラン戦争・ホルムズ海峡封鎖 ✅ 原因
5. 日本10年JGB 2.7% ⚠ やや結果寄り

### s03_news_root_cause (原因記事 5/5)
1. 米4月CPI +3.8% に加速 ✅ 経済指標
2. 日銀MASU委員「早期利上げを」 ✅ 要人発言
3. イラン戦争・ホルムズ海峡封鎖 ✅ 地政学
4. フジクラ -19% ストップ安 ✅ 個別決算
5. ウォーシュ氏 FRB 議長承認 ✅ 要人人事

**仮説完全に確認**: 結果記事が消え、純粋な原因記事 5/5 に置き換わった。

## 最終 PortfolioPlan (s01 との比較)

| 項目 | s01_baseline | s03_news_root_cause | 差分 |
|---|---|---|---|
| direction | bearish | bearish | 同 |
| P(bullish) | 0.22 | 0.20 | -0.02 |
| P(neutral) | 0.18 | 0.20 | +0.02 |
| P(bearish) | 0.60 | 0.60 | 同 |
| **confidence** | 62 | **70** | **+8** ★ |

**重要な発見**:
- 分布はほぼ同じ (P(bear) = 0.60 で不変)
- **confidence が 8 ポイント上昇** (62 → 70)
- key_drivers の質が向上したことで、PM が「**確かな理由がある下落**」と判断し
  確信度を上げた

## s01 / s02 / s03 の効果まとめ

3 つの scenario の効果が **直交している** ことが判明:

| scenario | direction | P(bear) | confidence | 効果 |
|---|---|---|---|---|
| s01_baseline | bearish | 0.60 | 62 | (基準) |
| s02_2round_debate | bearish | **0.52** ↓ | 62 | **分布**を neutral 寄りに (Bear 過信抑制) |
| s03_news_root_cause | bearish | 0.60 | **70** ↑ | **確信度**を上昇 (key_drivers 質向上) |

- **s02** は議論ラウンド数で「分布」を動かす
- **s03** はプロンプト改修で「確信度」を動かす
- **s04 (案)**: s02 + s03 を組み合わせれば、両方の効果が独立に効くか検証できる

## 観察 / 気付き

### プロンプト改修の効果は確信度に出る
key_drivers から結果記事を排除しただけで confidence が +8。これは PM が「市場サマリ記事は
信号として弱い」と暗黙に評価していた可能性を示唆。プロンプト改修の **検出力テスト** としても
有用な scenario。

### direction が変わらなかった意義
情報総量が同じなら direction も同じになる、というのは想定通りだが、これは **このフィクスチャ
特有の現象** かもしれない (材料が明らかに弱気優勢)。中立的な fixture では direction も
動く可能性。複数 fixture での再検証が望まれる。

### s01 と s03 の Researcher 出力が全く同じ
Bull/Bear には News Analyst の出力に加えて「補足材料」を渡しているので、key_drivers が
変わっても判断は変わらなかった。これは **Researcher は News の生材料を見ている** ことを
示唆し、News Analyst の出力フォーマット改修が Researcher に伝播しないという観察。

### 整合性チェック
- 確率和: 0.20 + 0.20 + 0.60 = 1.00 ✅
- direction (`bearish`) と最大確率 (`bearish=0.60`) は整合 ✅
- top_drivers は全て入力メモから採用 ✅
- top_drivers が News の原因記事と一致 → variant プロンプトが下流まで伝播 ✅

## 次のアクション

- **s04 (案)**: s02 + s03 を組み合わせ「議論 2 ラウンド × News プロンプト改修」を試す。
  確信度と分布の両方が動くか確認
- **別 fixture (2026-05-19_calm 等) で s03 を再走**: direction が変わるケースがあるか
- canonical (src/agents/news_analyst.py) に root_cause variant の制約を **逆輸入** する判断:
  - 結果記事を排除する制約は本実装でも価値が高い
  - 検証 1 回で採用を決めるのは早計、3-5 fixture で再現を確認してから

## 免責

これはプロトタイプ検証ログであり投資助言ではありません。
