# architectures/

予測パイプラインの **設計思想ごとに独立した実装** を並べるディレクトリ。各 architecture は
**共通の出力スキーマ (`PortfolioPlan`)** を生成することで、`eval/` が arch を意識せず採点できる。
Python から呼べる arch は加えて `src/graph/orchestrator.py` の `Orchestrator` Protocol も実装する。

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

### 出力契約（全 arch 必須）

```python
# src/agents/types.py
class PortfolioPlan(BaseModel):
    horizon: Horizon
    direction: Literal["bullish", "neutral", "bearish"]
    direction_probabilities: DirectionProbabilities
    confidence: int
    ...
```

すべての arch は最終出力として `PortfolioPlan` を吐く。
保存先: `runs/<fixture_id>/<horizon>/<arch>/<scenario>/<run_id>/05_plan.json`。
これにより `eval/scorers/` が arch を意識せず採点できる。

### Python 契約（コード系 arch のみ）

```python
# src/graph/orchestrator.py
class Orchestrator(Protocol):
    def predict(self, req: PredictionRequest) -> PortfolioPlan: ...
```

Python から呼べる arch (`a02` 以降の本実装系) は加えてこの Protocol を実装する。
a01 のような playbook 系 (人間 + サブエージェント) は Python 関数として呼べないため
Protocol を厳密には満たさない。出力スキーマだけ揃える緩い契約。

## src/ への依存

各 arch は `src/` の以下を共有部品として利用:

| モジュール | 役割 |
|---|---|
| `src/agents/<agent>.py` | プロンプト (`SYSTEM_PROMPT`) と I/O 型定義の **単一の正** |
| `src/agents/types.py` | `DirectionalMemo` / `PortfolioPlan` / `ActualOutcome` |
| `src/agents/variants/<agent>/<variant>.md` | プロンプト改修バリアント (arch 横断で再利用) |
| `src/graph/orchestrator.py` | `Orchestrator` Protocol、`PredictionRequest` |
| `src/data/` | データ層 (`NewsFetcher` / `JpxClient` 等) Protocol + スタブ |
| `src/llm/` | LLM クライアント抽象 + runner |
| `src/config/` | 設定管理 |

arch 固有の実装は arch 配下に閉じ込め、`src/` には共有部品しか置かない。

## 新 architecture を追加するとき

1. `aNN_<short_name>/` を切る
2. `README.md`: 思想・特徴・出典・既知の制約・依存する src/ モジュール
3. **実装**:
   - playbook 系 (人間 + サブエージェント実行) → `playbook.md`
   - コード系 (Python 実装) → `impl.py` に `Orchestrator` 実装クラスを置く
   - 具象実装を `src/graph/<arch>_impl.py` には **置かない** (arch 配下に閉じる)
4. `scenarios/s01_baseline.yaml` を最低 1 つ用意
5. `scenarios/README.md` に scenario カタログを置く
6. 既存 `fixtures/<id>/` で `runs/<fixture>/<horizon>/<arch>/s01_baseline/<run_id>/` を 1 回流す
7. 望ましくは `experiments/expNNN_<topic>/` を切って **他 arch との比較レポート** を書く

## 外部 fork 系 arch の取り込み

a03_tradingagents_fork のような外部リポジトリの取り込みは **git subtree が無難** (submodule
だと依存先の認証や clone 順序で詰まりやすい)。`architectures/aNN_*/external/` に subtree で
入れて、その上に薄いラッパーを書くのが推奨。

## 命名規約

- arch ID は `aNN_<snake_case>` 形式（NN は 01 から連番）
- 退役したものは `archive/aNN_xxx/` へ移動（履歴保持）
