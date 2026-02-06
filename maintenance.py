# maintenance.py
"""
メンテナンスモード管理モジュール
Supabaseのsystem_settingsテーブルでメンテナンス状態を管理
"""

from config import Config

class MaintenanceMode:
    """メンテナンスモード管理クラス"""
    
    @staticmethod
    def is_enabled():
        """
        メンテナンスモードが有効かどうかをチェック
        
        Returns:
            bool: メンテナンスモードが有効ならTrue、無効ならFalse
        """
        try:
            if Config.USE_SUPABASE:
                from services.supabase_db import get_supabase_client
                supabase = get_supabase_client()
                
                result = supabase.table('system_settings')\
                    .select('value')\
                    .eq('key', 'maintenance_mode')\
                    .single()\
                    .execute()
                
                return result.data.get('value') == 'true'
            else:
                # Google Sheetsの場合は常にメンテナンスモードOFF
                return False
                
        except Exception as e:
            print(f"⚠️ メンテナンスモード取得エラー: {e}")
            # エラー時は安全のため通常モード（False）を返す
            return False
    
    @staticmethod
    def get_message():
        """
        メンテナンスメッセージを取得
        
        Returns:
            str: メンテナンスメッセージ（設定されていない場合はデフォルトメッセージ）
        """
        try:
            if Config.USE_SUPABASE:
                from services.supabase_db import get_supabase_client
                supabase = get_supabase_client()
                
                result = supabase.table('system_settings')\
                    .select('description')\
                    .eq('key', 'maintenance_mode')\
                    .single()\
                    .execute()
                
                return result.data.get('description', 'システムメンテナンス中です')
            else:
                return 'システムメンテナンス中です'
                
        except Exception as e:
            print(f"⚠️ メンテナンスメッセージ取得エラー: {e}")
            return 'システムメンテナンス中です'
    
 
    @staticmethod
    def toggle(user_id):
        """メンテナンスモードを切り替え"""
        print(f"🔧 toggle() 開始: user_id={user_id}")
        
        try:
            if not Config.USE_SUPABASE:
                print("❌ Supabaseが無効")
                return {
                    'success': False,
                    'error': 'Google Sheetsモードではメンテナンス機能は利用できません'
                }
            
            from services.supabase_db import get_supabase_client
            supabase = get_supabase_client()
            print("✅ Supabaseクライアント取得成功")
            
            # 現在の状態を取得
            print("📡 現在の状態を取得中...")
            current = supabase.table('system_settings')\
                .select('value')\
                .eq('key', 'maintenance_mode')\
                .single()\
                .execute()
            print(f"📊 現在の値: {current.data}")
            
            # 状態を反転
            new_value = 'false' if current.data['value'] == 'true' else 'true'
            print(f"🔄 新しい値: {new_value}")
            
            # 更新
            print("💾 データベース更新中...")
            supabase.table('system_settings')\
                .update({'value': new_value})\
                .eq('key', 'maintenance_mode')\
                .execute()
            
            print(f"✅ メンテナンスモード切り替え成功: {new_value}")
            
            return {
                'success': True,
                'maintenance_mode': new_value == 'true'
            }
            
        except Exception as e:
            print(f"❌ メンテナンスモード切り替えエラー: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }