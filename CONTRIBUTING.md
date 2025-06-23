# コントリビューションガイドライン

このプロジェクトへの貢献に興味を持っていただき、ありがとうございます。以下のガイドラインに従って貢献をお願いします。

## 開発環境のセットアップ

1. リポジトリをクローン
```bash
git clone https://github.com/yourusername/image_mosaic5.git
cd image_mosaic5
```

2. 仮想環境の作成と有効化
```bash
python -m venv venv
source venv/bin/activate  # Linuxの場合
venv\Scripts\activate     # Windowsの場合
```

3. 依存パッケージのインストール
```bash
pip install -r requirements.txt
```

## 開発の流れ

1. 新しい機能やバグ修正のためのブランチを作成
```bash
git checkout -b feature/your-feature-name
```

2. 変更を加える
3. 変更をコミット
```bash
git commit -m "Add: 新機能の説明"
```

4. ブランチをプッシュ
```bash
git push origin feature/your-feature-name
```

5. プルリクエストを作成

## コーディング規約

- PEP 8に準拠したPythonコード
- 適切なドキュメンテーション（docstring）の追加
- ユニットテストの作成（可能な場合）
- 日本語のコメントは適切に使用

## プルリクエストのガイドライン

1. プルリクエストの説明を明確に記述
2. 関連するIssue番号を参照（存在する場合）
3. 変更内容の詳細な説明を追加
4. スクリーンショットやGIFを添付（UIの変更の場合）

## バグ報告

バグを発見した場合は、以下の情報を含めてIssueを作成してください：

1. バグの詳細な説明
2. 再現手順
3. 期待される動作
4. 実際の動作
5. スクリーンショット（該当する場合）
6. 環境情報（OS、Pythonバージョンなど）

## 機能リクエスト

新機能のリクエストは以下の情報を含めてIssueを作成してください：

1. 機能の詳細な説明
2. 使用例
3. 実装の提案（可能な場合）

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。コントリビューションを行うことで、あなたのコードも同じライセンスの下で公開されることに同意したことになります。 