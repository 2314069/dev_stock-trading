"""データ取得レイヤー。

ソースごとにアダプタ (JPX / CME / FX / News) を分け、各モジュールは:
- 公開する共通スキーマ (Pydantic)
- `Protocol` で型付けされたクライアント IF
- Stage 0 / テスト用のスタブ実装
- 環境に応じてスタブ / 実装を切替える `get_client()` または `get_fetcher()` ファクトリ
を提供する。エージェント (`src/agents/`) およびグラフ (`src/graph/`) はこの IF のみに依存する。
"""
