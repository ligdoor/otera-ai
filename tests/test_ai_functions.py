"""
AI機能のテスト (ai_functions.py)
Gemini APIを使用したQ&A機能を検証
"""

import pytest
from unittest.mock import patch, MagicMock
from modules import ai_functions


class TestGeminiAPI:
    """Gemini API呼び出しのテスト"""
    
    @patch('modules.ai_functions.genai')
    def test_AIに質問して回答を取得(self, mock_genai):
        """Gemini APIに質問して回答を取得できる"""
        # モックレスポンス
        mock_response = MagicMock()
        mock_response.text = "これはテスト回答です。"
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        question = "仏教とは何ですか？"
        answer = ai_functions.ask_gemini(question)
        
        assert answer is not None
        assert len(answer) > 0
        assert answer == "これはテスト回答です。"
    
    @patch('modules.ai_functions.genai')
    def test_空の質問は拒否(self, mock_genai):
        """空の質問は処理されない"""
        answer = ai_functions.ask_gemini('')
        
        assert answer is None or answer == ''
    
    @patch('modules.ai_functions.genai')
    def test_長すぎる質問は制限(self, mock_genai):
        """極端に長い質問は制限される"""
        long_question = 'あ' * 10000
        
        # 長すぎる質問は切り詰められる
        result = ai_functions.ask_gemini(long_question)
        
        # エラーにならずに処理される
        assert result is not None


class TestTempleQA:
    """寺院Q&A機能のテスト"""
    
    @patch('modules.ai_functions.genai')
    @patch('modules.ai_functions.supabase')
    def test_寺院に関する質問(self, mock_supabase, mock_genai):
        """寺院に関する質問に答えられる"""
        # 寺院データのモック
        mock_response = MagicMock()
        mock_response.data = [{
            'id': 1,
            'name': '浅草寺',
            'description': '東京都台東区にある寺院'
        }]
        mock_supabase.table().select().eq().execute.return_value = mock_response
        
        # AIレスポンスのモック
        mock_ai_response = MagicMock()
        mock_ai_response.text = "浅草寺は東京都台東区にある歴史的な寺院です。"
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_ai_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        temple_id = 1
        question = "この寺院について教えてください"
        answer = ai_functions.ask_about_temple(temple_id, question)
        
        assert answer is not None
        assert '浅草寺' in answer
    
    @patch('modules.ai_functions.genai')
    def test_仏教用語の説明(self, mock_genai):
        """仏教用語について説明できる"""
        mock_response = MagicMock()
        mock_response.text = "涅槃とは、煩悩から解放された悟りの境地です。"
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        question = "涅槃とは何ですか？"
        answer = ai_functions.ask_gemini(question)
        
        assert '涅槃' in answer


class TestButsugoQA:
    """仏具Q&A機能のテスト"""
    
    @patch('modules.ai_functions.genai')
    @patch('modules.ai_functions.supabase')
    def test_仏具に関する質問(self, mock_supabase, mock_genai):
        """仏具に関する質問に答えられる"""
        # 仏具データのモック
        mock_response = MagicMock()
        mock_response.data = [{
            'id': 1,
            'name': '数珠',
            'description': '念仏を唱える際に使用する仏具'
        }]
        mock_supabase.table().select().eq().execute.return_value = mock_response
        
        # AIレスポンスのモック
        mock_ai_response = MagicMock()
        mock_ai_response.text = "数珠は念仏を数えるために使用される仏具です。"
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_ai_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        butsugo_id = 1
        question = "この仏具の使い方を教えてください"
        answer = ai_functions.ask_about_butsugo(butsugo_id, question)
        
        assert answer is not None
        assert '数珠' in answer


class TestContextAwareQA:
    """文脈を考慮したQ&Aのテスト"""
    
    @patch('modules.ai_functions.genai')
    def test_前の質問を考慮した回答(self, mock_genai):
        """前の質問を考慮して回答できる"""
        mock_response1 = MagicMock()
        mock_response1.text = "浅草寺は東京都台東区にあります。"
        
        mock_response2 = MagicMock()
        mock_response2.text = "浅草寺の創建は628年です。"
        
        mock_model = MagicMock()
        mock_model.generate_content.side_effect = [mock_response1, mock_response2]
        mock_genai.GenerativeModel.return_value = mock_model
        
        # 1回目の質問
        answer1 = ai_functions.ask_with_context("浅草寺はどこにありますか？", context=[])
        
        # 2回目の質問（前の質問を考慮）
        context = [
            {'role': 'user', 'content': "浅草寺はどこにありますか？"},
            {'role': 'assistant', 'content': answer1}
        ]
        answer2 = ai_functions.ask_with_context("その寺院はいつ建てられましたか？", context=context)
        
        assert '628年' in answer2


class TestResponseFormatting:
    """回答フォーマットのテスト"""
    
    @patch('modules.ai_functions.genai')
    def test_マークダウン形式の回答(self, mock_genai):
        """マークダウン形式で回答が返される"""
        mock_response = MagicMock()
        mock_response.text = "# 仏教とは\n\n仏教は紀元前5世紀頃にインドで始まった宗教です。"
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        answer = ai_functions.ask_gemini("仏教とは？")
        
        assert '#' in answer  # マークダウンの見出し
    
    @patch('modules.ai_functions.genai')
    def test_HTMLタグを除去(self, mock_genai):
        """回答からHTMLタグが除去される"""
        mock_response = MagicMock()
        mock_response.text = "<script>alert('test')</script>普通のテキスト"
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        answer = ai_functions.ask_gemini_safe("質問")
        
        assert '<script>' not in answer
        assert '普通のテキスト' in answer


class TestErrorHandling:
    """エラーハンドリングのテスト"""
    
    @patch('modules.ai_functions.genai')
    def test_APIエラー時の処理(self, mock_genai):
        """Gemini APIがエラーを返した時の処理"""
        mock_model = MagicMock()
        mock_model.generate_content.side_effect = Exception("API Error")
        mock_genai.GenerativeModel.return_value = mock_model
        
        answer = ai_functions.ask_gemini("質問")
        
        # エラーメッセージが返される
        assert answer is not None
        assert 'エラー' in answer or answer == ''
    
    @patch('modules.ai_functions.genai')
    def test_タイムアウト時の処理(self, mock_genai):
        """タイムアウト時の処理"""
        import time
        
        mock_model = MagicMock()
        
        def slow_response(*args, **kwargs):
            time.sleep(10)  # 10秒待機
            return MagicMock(text="遅い回答")
        
        mock_model.generate_content.side_effect = slow_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        # タイムアウト設定（5秒）
        answer = ai_functions.ask_gemini_with_timeout("質問", timeout=5)
        
        # タイムアウトエラーが処理される
        assert answer is not None


class TestContentFiltering:
    """コンテンツフィルタリングのテスト"""
    
    @patch('modules.ai_functions.genai')
    def test_不適切な質問をフィルタ(self, mock_genai):
        """不適切な質問がフィルタリングされる"""
        inappropriate_questions = [
            "違法な方法を教えて",
            "暴力的な内容",
        ]
        
        for question in inappropriate_questions:
            result = ai_functions.is_appropriate_question(question)
            assert result is False
    
    @patch('modules.ai_functions.genai')
    def test_適切な質問は通過(self, mock_genai):
        """適切な質問は通過する"""
        appropriate_questions = [
            "仏教について教えてください",
            "浅草寺の歴史は？",
            "数珠の使い方を知りたいです"
        ]
        
        for question in appropriate_questions:
            result = ai_functions.is_appropriate_question(question)
            assert result is True


class TestQuestionHistory:
    """質問履歴のテスト"""
    
    @patch('modules.ai_functions.supabase')
    def test_質問履歴を保存(self, mock_supabase):
        """ユーザーの質問履歴が保存される"""
        user_id = 1
        question = "仏教とは？"
        answer = "仏教は..."
        
        ai_functions.save_question_history(user_id, question, answer)
        
        # データベースに保存されたことを確認
        mock_supabase.table().insert().execute.assert_called_once()
    
    @patch('modules.ai_functions.supabase')
    def test_質問履歴を取得(self, mock_supabase):
        """ユーザーの質問履歴を取得できる"""
        mock_response = MagicMock()
        mock_response.data = [
            {'question': '質問1', 'answer': '回答1'},
            {'question': '質問2', 'answer': '回答2'}
        ]
        mock_supabase.table().select().eq().order().execute.return_value = mock_response
        
        user_id = 1
        history = ai_functions.get_question_history(user_id)
        
        assert len(history) == 2


class TestResponseQuality:
    """回答品質のテスト"""
    
    @patch('modules.ai_functions.genai')
    def test_回答が十分な長さ(self, mock_genai):
        """回答が十分な長さを持つ"""
        mock_response = MagicMock()
        mock_response.text = "これは詳細な回答です。" * 10
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        answer = ai_functions.ask_gemini("詳しく教えて")
        
        # 最低100文字以上
        assert len(answer) >= 100
    
    @patch('modules.ai_functions.genai')
    def test_回答に質問内容が含まれる(self, mock_genai):
        """回答に質問のキーワードが含まれる"""
        mock_response = MagicMock()
        mock_response.text = "浅草寺は東京都台東区にある寺院です。"
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        question = "浅草寺について"
        answer = ai_functions.ask_gemini(question)
        
        assert '浅草寺' in answer


# テスト実行時の設定
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
