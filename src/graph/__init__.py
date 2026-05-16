"""F-08 オーケストレーション層。

`orchestrator.py` で具象実装に依存しない `Orchestrator` Protocol を定義し、
LangGraph / CrewAI / 自作実装などを差替可能にする。

実装ファイル (例: `langgraph_impl.py`) を本パッケージに追加し、`get_orchestrator()` で
切替する。Stage 0 では `StubOrchestrator` で下流（API・評価・表示）の組み立てが進められる。
"""
