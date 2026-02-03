// ========================================
// アプリ - 音声入力機能
// ========================================

let recognition = null;

function startVoiceInput() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    
    if (!SpeechRecognition) {
        alert('❌ お使いのブラウザは音声入力に対応していません。Chrome、Edge、Safariをお使いください。');
        return;
    }
    
    recognition = new SpeechRecognition();
    recognition.lang = 'ja-JP';
    recognition.continuous = false;
    recognition.interimResults = false;
    
    const freeInput = document.getElementById('free-input');
    
    recognition.onstart = function() {
        freeInput.placeholder = '🎤 音声を認識中...';
        freeInput.style.borderColor = '#f44336';
    };
    
    recognition.onresult = function(event) {
        const transcript = event.results[0][0].transcript;
        freeInput.value = transcript;
        freeInput.placeholder = '例：駐車場の場所は？';
        freeInput.style.borderColor = '#e0e0e0';
    };
    
    recognition.onerror = function(event) {
        console.error('音声認識エラー:', event.error);
        freeInput.placeholder = '例：駐車場の場所は？';
        freeInput.style.borderColor = '#e0e0e0';
        
        if (event.error === 'network') {
            alert('❌ ネットワークエラーが発生しました。インターネット接続を確認してください。');
        } else if (event.error === 'not-allowed') {
            alert('❌ マイクの使用が許可されていません。ブラウザの設定でマイクを許可してください。');
        } else if (event.error === 'no-speech') {
            alert('⚠️ 音声が検出されませんでした。もう一度お試しください。');
        }
    };
    
    recognition.onend = function() {
        freeInput.placeholder = '例：駐車場の場所は？';
        freeInput.style.borderColor = '#e0e0e0';
    };
    
    try {
        recognition.start();
    } catch (e) {
        console.error('音声認識開始エラー:', e);
        alert('❌ 音声認識の開始に失敗しました');
    }
}