"""
APIルート
その他のAPIエンドポイント
"""
from flask import Blueprint

api_bp = Blueprint('api', __name__)

# 現在は空ですが、将来的にAPI専用のエンドポイントを追加できます
# 例: 外部システム連携用のAPIなど