FROM python:3.11-slim

WORKDIR /app

# 依存関係をインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションファイルをコピー
COPY . .

# ポート8080で起動
EXPOSE 8080

# Flaskアプリを起動
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "main:app"]