"""
寺院データ移行パッチ

Google Sheets の otera_data シートから Supabase の temples テーブルへ移行
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from services.spreadsheet import get_spreadsheet_client
from supabase import create_client, Client


def get_supabase_client() -> Client:
    """Supabaseクライアントを取得"""
    if not Config.SUPABASE_URL or not Config.SUPABASE_SERVICE_KEY:
        raise ValueError("Supabase接続情報が設定されていません")
    
    return create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_KEY)


def migrate_temples():
    """
    寺院データを移行
    
    Google Sheets列: name, sect, address, nokanshiyo, kakimono, flow, caution, transport
    Supabase列: name, sect, address, nokanshiyo, kakimono, flow, caution, transport
    ※完全一致
    """
    print("\n" + "="*60)
    print("🏯 寺院データの移行")
    print("="*60)
    
    try:
        # Google Sheetsから寺院データ取得
        print("\n📥 Google Sheetsから寺院データを取得中...")
        sheets_client = get_spreadsheet_client()
        sheet = sheets_client.open(Config.DATA_SPREADSHEET_NAME).worksheet('otera_data')
        
        all_values = sheet.get_all_values()
        if len(all_values) < 2:
            print("⚠️ 寺院データが存在しません")
            return False
        
        headers = all_values[0]
        print(f"✅ Google Sheets列: {headers}")
        print(f"✅ データ数: {len(all_values) - 1}件")
        
        # Supabaseクライアント取得
        supabase = get_supabase_client()
        
        # 既存寺院を取得（重複チェック用）
        print("\n🔍 Supabaseの既存寺院を確認中...")
        existing_response = supabase.table('temples').select('name').execute()
        existing_names = {t['name'] for t in existing_response.data}
        print(f"✅ 既存寺院: {len(existing_names)}件")
        
        if existing_names:
            print("\n⚠️ 既存の寺院データの扱い:")
            print("1. スキップ（既存データを保持）")
            print("2. 上書き（既存データを更新）")
            print("3. 削除して再作成（全て削除してから追加）")
            choice = input("\n選択してください (1/2/3): ")
            
            if choice == "3":
                print("\n🗑️ 既存データを削除中...")
                for name in existing_names:
                    supabase.table('temples').delete().eq('name', name).execute()
                print(f"✅ {len(existing_names)}件削除完了")
                existing_names.clear()
            elif choice == "2":
                print("\n📝 上書きモードで実行します")
            else:
                print("\n⏭️ スキップモードで実行します")
        
        # 移行カウンター
        success = 0
        skip = 0
        update = 0
        errors = 0
        
        print("\n🔄 寺院データ移行中...")
        for i, row in enumerate(all_values[1:], start=2):
            if not row or len(row) == 0:
                continue
            
            # 行データを辞書に変換
            temple_data = {}
            for j, header in enumerate(headers):
                if j < len(row):
                    temple_data[header] = row[j].strip()
                else:
                    temple_data[header] = ''
            
            temple_name = temple_data.get('name', '')
            if not temple_name:
                print(f"  ⏭️  行{i}: 寺院名が空のためスキップ")
                skip += 1
                continue
            
            try:
                # Google Sheetsの列名をそのまま使用
                insert_data = {
                    'name': temple_data.get('name'),
                    'sect': temple_data.get('sect', ''),
                    'address': temple_data.get('address', ''),
                    'nokanshiyo': temple_data.get('nokanshiyo', ''),
                    'kakimono': temple_data.get('kakimono', ''),
                    'flow': temple_data.get('flow', ''),
                    'caution': temple_data.get('caution', ''),
                    'transport': temple_data.get('transport', '')
                }
                
                # 既存チェック
                if temple_name in existing_names:
                    if choice == "2":  # 上書き
                        supabase.table('temples').update(insert_data).eq('name', temple_name).execute()
                        update += 1
                        print(f"  🔄 行{i}: {temple_name} - 更新")
                    else:  # スキップ
                        skip += 1
                        print(f"  ⏭️  行{i}: {temple_name} - スキップ（既存）")
                else:
                    # 新規追加
                    supabase.table('temples').insert(insert_data).execute()
                    success += 1
                    print(f"  ✅ 行{i}: {temple_name} ({insert_data['sect']})")
                    
            except Exception as e:
                errors += 1
                print(f"  ❌ 行{i}: {temple_name} - エラー: {e}")
        
        # 結果サマリー
        print("\n" + "="*60)
        print("📊 移行結果")
        print("="*60)
        print(f"✅ 新規追加: {success}件")
        print(f"🔄 更新: {update}件")
        print(f"⏭️  スキップ: {skip}件")
        print(f"❌ エラー: {errors}件")
        print(f"📝 合計: {success + update + skip + errors}件")
        
        return errors == 0
        
    except Exception as e:
        print(f"\n❌ 移行エラー: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_temples():
    """移行後のデータを検証"""
    print("\n" + "="*60)
    print("🔍 寺院データの検証")
    print("="*60)
    
    try:
        supabase = get_supabase_client()
        
        # 全寺院を取得
        response = supabase.table('temples').select('name, sect, address').execute()
        temples = response.data
        
        print(f"\n✅ Supabaseに保存された寺院数: {len(temples)}件")
        
        if temples:
            print("\n【最初の5件】")
            for temple in temples[:5]:
                print(f"  - {temple['name']} ({temple['sect']}) - {temple['address']}")
        
        # Google Sheetsと件数比較
        print("\n📊 件数確認:")
        sheets_client = get_spreadsheet_client()
        sheet = sheets_client.open(Config.DATA_SPREADSHEET_NAME).worksheet('otera_data')
        all_values = sheet.get_all_values()
        sheets_count = len(all_values) - 1  # ヘッダー除く
        
        print(f"  Google Sheets: {sheets_count}件")
        print(f"  Supabase: {len(temples)}件")
        
        if sheets_count == len(temples):
            print("\n✅ 件数が一致しています")
        else:
            print(f"\n⚠️ 件数が一致しません（差分: {abs(sheets_count - len(temples))}件）")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 検証エラー: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """メイン処理"""
    print("\n" + "="*60)
    print("🚀 寺院データ移行パッチ")
    print("="*60)
    
    # 環境変数の確認
    print("\n【環境変数】")
    print(f"DATA_SPREADSHEET: {Config.DATA_SPREADSHEET_NAME}")
    print(f"SUPABASE_URL: {Config.SUPABASE_URL}")
    print(f"SUPABASE_KEY: {'設定済み' if Config.SUPABASE_SERVICE_KEY else '❌未設定'}")
    
    if not Config.SUPABASE_URL or not Config.SUPABASE_SERVICE_KEY:
        print("\n❌ Supabase接続情報が未設定です")
        print("\n【.envファイルに以下を設定してください】")
        print("SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co")
        print("SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")
        return
    
    # 移行確認
    print("\n" + "-"*60)
    response = input("\n寺院データの移行を開始しますか？ (y/n): ")
    if response.lower() != 'y':
        print("⏭️ キャンセルしました")
        return
    
    # 移行実行
    success = migrate_temples()
    
    if success:
        # 検証実行
        verify_temples()
        
        print("\n" + "="*60)
        print("🎉 寺院データ移行完了！")
        print("="*60)
        print("\n【次のステップ】")
        print("1. Supabaseダッシュボードで temples テーブルを確認")
        print("2. アプリを再起動して動作確認")
    else:
        print("\n" + "="*60)
        print("⚠️ 寺院データ移行が失敗しました")
        print("="*60)
        print("\n【対処方法】")
        print("1. エラーメッセージを確認")
        print("2. Supabase接続情報を確認")
        print("3. Google Sheetsのデータ形式を確認")


if __name__ == "__main__":
    main()