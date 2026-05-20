# architectures/

予測パイプラインの **設計思想ごとに独立した実装** を並べるディレクトリ。各 architecture は
`src/graph/orchestrator.py` の `Orchestrator` Protocol を満たす
（= 何らかの形で `PredictionRequest` → `PortfolioPlan` を実現する）ことで、出力スキーマが揃い
`eval/` で arch 横断採点が可能になる。

## カタログ

| ID | 思想 | 状態 | 実行モード | 出典・参考 |
|---|---|---|---|---|
| `a01_f08_subagent` | Claude Code サブエージェントで F-08 を手動オーケスト | active | サブスク (Agent ツール) | SPEC §F-08 |
| `a02_langgraph_pipeline` | LangGraph による F-08 自動パイプライン | planned | API 従量 | TradingAgents 系 |
| `a03_tradingagents_fork` | TradingAgents 構成を日経向けに移植 | idea | - | Xiao et al. |
| `a04_crewai` | CrewAI 移植版 | idea | - | CrewAI |
| `a05_hierarchical` | マネージャー+部下の階層型 | idea | - | AutoGen |
| `a06_single_react` | 1 エージェントが多役を ReAct で演じる | idea | - | ReAct (Yao et al.) |
| `a07_blackboard` | 共有スクラッチパッドに各エージェントが書込 | idea | - | Blackboard pattern |

## 共通契約

```python
# src/graph/orchestrator.py（既存）
class Orchestrator(Protocol):
    def predict(self, req: PredictionRequest) -> PortfolioPlan: ...
```

サブエージェント方式は Python から直接呼べないが、`runs/<date>/<arch>/<scenario>/05_plan.json`
として同じ `PortfolioPlan` スキーマで出力すれば eval ハーネスに乗る。

## 新 architecture を追加するとき

1. `aNN_<short_name>/` を切る
2. `README.md`: 思想・特徴・出典・既知の制約
3. **実装**:
   - playbook 系 (人間 + サブエージェント実行) → `playbook.md`
   - コード系 (Python 実装) → `impl.py` + `Orchestrator` 実装クラス
4. `scenarios/s01_baseline.json` を最低 1 つ用意
5. 既存 `fixtures/<id>/` で `runs/<date>/<arch>/s01_baseline/` を 1 回流す
6. 望ましくは `experiments/expNNN_<topic>/` を切って **他 arch との比較レポート** を書く

## 命名規約

- arch ID は `aNN_<snake_case>` 形式（NN は 01 から連番）
- 退役したものは `archive/aNN_xxx/` へ移動（履歴保持）
