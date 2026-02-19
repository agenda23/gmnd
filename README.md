# Discord Bot "gmnd"

`gmnd` は、Go言語製の高速な Gemini CLI ツールである `gmn` をバックエンドとして活用し、Discord上での高度な対話、文脈維持、およびシステム管理を可能にする Bot です。

## 主な機能

- **高度な対話**: 指定した常駐チャンネル、またはメンションによる対話。
- **文脈維持**: ギルド・チャンネルごとの履歴管理。
- **マルチモーダル対応**: 画像やPDFなどの添付ファイルを `gmn` に渡して処理。
- **自動要約 (AM 03:00)**: 毎日の会話履歴を自動で要約し、アーカイブ化。
- **Slash Commands**:
    - `/status`: 稼働状況の確認。
    - `/config`: 常駐チャンネルの設定。
    - `/set_system`: システムプロンプト（人格）の設定。
    - `/clear_context`: 履歴の消去（確認ボタン付き）。
    - `/model`: Gemini モデルの切り替え。
- **運用機能**: `system.log` へのログ出力、Graceful Shutdown 対応。

## 必要条件

- Python 3.10+
- Go 1.20+ (`gmn` バイナリのビルド・実行用)
- [`gmn` CLI](https://github.com/tomohiro-owada/gmn) (パスが通っていること)
- `gemini-cli (Node.js版)` でのログイン済み (`~/.gemini/` に認証情報があること)

## インストールと実行

1. リポジトリをクローンまたはダウンロードします。
2. 依存関係をインストールし、環境をセットアップします（`uv` がインストールされている必要があります）:
   ```bash
   uv sync
   ```
3. `.env` ファイルを作成し、Discord Bot のトークンを設定します:
   ```env
   DISCORD_BOT_TOKEN=your_discord_bot_token_here
   ```
4. Bot を起動します:
   ```bash
   uv run main.py
   ```

## 使い方（クイックマニュアル）

### 対話する
- **常駐チャンネル**: 設定されたチャンネルでは、そのまま発言するだけで AI が応答します。
- **メンション**: その他のチャンネルでは、Bot にメンション（@Bot名）を付けて話しかけてください。

### ファイルを読み込ませる
- 画像や PDF を添付してメッセージを送信すると、AI がその内容を理解して回答します。

### コマンド
- `/help`: コマンド一覧を表示します。
- `/status`: 稼働状況を確認します。

> [!TIP]
> **詳細な操作マニュアルは [こちら(docs/instructions.md)](docs/instructions.md) をご覧ください。**

## ディレクトリ構造

- `main.py`: Bot のメインロジック。
- `core.py`: CLI 連携とコンテキスト管理のユーティリティ。
- `config.json`: 動作設定。
- `data/`: 文脈履歴保存ディレクトリ。
- `docs/`: ドキュメント類。
    - [`instructions.md`](docs/instructions.md): **操作マニュアル（詳細はこちら）**
    - `Discord Bot "gmnd" 仕様書.md`: プロジェクト仕様書。
- `system.log`: システムエラーおよびイベントログ。
- `LICENSE`: MIT ライセンス。
- `CHANGELOG.md`: 更新履歴。

## 開発とテスト

- `tests/`: ユニットテスト（開発中）。
- `pyproject.toml` / `uv.lock`: `uv` による依存関係管理。

## Thanks

- **Google Gemini CLI Team**: 素晴らしい AI インターフェースの基盤を提供していただき感謝します。
- **[tomohiro-owada](https://github.com/tomohiro-owada)**: 高速な Go 製 Gemini CLI ツール `gmn` の開発に心より感謝いたします。

