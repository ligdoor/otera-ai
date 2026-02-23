# Docker開発環境 使い方

## 初回セットアップ

```bash
# プロジェクトフォルダで実行
docker-compose up --build
```

## 2回目以降の起動

```bash
docker-compose up
```

## 停止

```bash
docker-compose down
```

## アクセス

ブラウザで http://localhost:8080 を開く

## よくある操作

### コンテナの中に入る（デバッグ用）
```bash
docker-compose exec web bash
```

### ログを見る
```bash
docker-compose logs -f
```

## 注意点

- `.env` ファイルは必ずプロジェクトのルートに置いてください
- コードを変更すると自動でリロードされます（Flask debug mode）
- Supabaseはクラウド側なのでDocker内から普通につながります
