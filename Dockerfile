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
# worker=1 + threads=4 でメモリ使用量を削減（512MB→256MB対応）
# workerを2→1にするだけで約100MB節約、threadsで同時接続は維持
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "4", "--worker-class", "gthread", "--timeout", "60", "main:app"]