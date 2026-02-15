// ========================================
// アプリ - メイン（初期化・共通関数）
// ========================================

// グローバル変数
const chatWindow = document.getElementById("chat-window");
const controlArea = document.getElementById("control-area");
const showMenuBtn = document.getElementById("show-menu-btn");

let currentTempleName = "";
let favorites = [];
let currentTab = "all";
let allTemples = [];

// ========================================
// 初期化
// ========================================

window.onload = async function () {
  await loadFavorites();
  await loadUnreadCount();

  try {
    // 寺院名一覧を取得
    const tRes = await fetch("/api/v1/temples/names");
    const tData = await tRes.json();
    
    if (tData.success) {
      allTemples = tData.data.names || [];
    } else {
      console.error("寺院名取得エラー:", tData.error.message);
      allTemples = [];
    }

    updateTempleSelect();

    // 宗派一覧を取得
    const sRes = await fetch("/api/v1/sects");
    const sData = await sRes.json();
    const sSelect = document.getElementById("sect-select");

    if (sData.success) {
      const sects = sData.data.sects || [];
      sects.forEach((sect) => {
        const opt = document.createElement("option");
        opt.value = sect;
        opt.text = sect;
        sSelect.appendChild(opt);
      });
    } else {
      console.error("宗派取得エラー:", sData.error.message);
    }
  } catch (e) {
    console.error("初期化エラー:", e);
    alert("データの読み込みに失敗しました");
  }
};

// ========================================
// タブ切り替え
// ========================================

function switchTab(tab) {
  currentTab = tab;
  document.querySelectorAll(".fav-tab").forEach((btn) => {
    btn.classList.toggle(
      "active",
      btn.textContent.includes(tab === "all" ? "すべて" : "お気に入り"),
    );
  });
  updateTempleSelect();
}

// 寺院セレクトボックスを更新
function updateTempleSelect() {
  const tSelect = document.getElementById("temple-select");
  tSelect.innerHTML = '<option value="">寺院を選択...</option>';

  const displayTemples =
    currentTab === "favorites"
      ? allTemples.filter((n) => favorites.includes(n))
      : allTemples;

  displayTemples.forEach((name) => {
    const opt = document.createElement("option");
    opt.value = name;
    opt.text = favorites.includes(name) ? `⭐ ${name}` : name;
    tSelect.appendChild(opt);
  });
}

// ========================================
// メニュー表示制御
// ========================================

function hideMenu() {
  controlArea.classList.add("minimized");
  showMenuBtn.classList.add("visible");
  document.body.style.paddingBottom = "80px";
}

function showMenu() {
  controlArea.classList.remove("minimized");
  showMenuBtn.classList.remove("visible");
  document.body.style.paddingBottom = "400px";
}

// ========================================
// メッセージ追加
// ========================================

function addMessage(text, sender, isLoading = false) {
  const div = document.createElement("div");
  div.className = `message ${sender}-message`;
  div.id = `msg-${Date.now()}-${Math.random()}`;

  // HTMLタグが含まれている場合はそのまま、そうでない場合は改行を<br>に変換
  if (
    text.includes("<div") ||
    text.includes("<button") ||
    text.includes("<a")
  ) {
    div.innerHTML = text;
  } else {
    div.innerHTML = text.replace(/\n/g, "<br>");
  }

  chatWindow.appendChild(div);

  // お気に入りボタンの状態を更新
  if (sender === "ai") {
    setTimeout(() => {
      const detailButtons = div.querySelectorAll(".favorite-btn-detail");
      detailButtons.forEach((btn) => {
        const templeName = btn.dataset.temple;
        if (favorites.includes(templeName)) {
          btn.textContent = "⭐";
          btn.style.borderColor = "#ffc107";
        }
      });
    }, 100);
  }

  setTimeout(() => {
    window.scrollTo(0, document.body.scrollHeight);
  }, 100);

  return div.id;
}

// ========================================
// ユーティリティ関数
// ========================================

// クリップボードにコピー
function copyToClipboard(text) {
  if (window.event) window.event.stopPropagation();

  if (navigator.clipboard) {
    navigator.clipboard
      .writeText(text)
      .then(() => {
        console.log("コピーしました:", text);
      })
      .catch((err) => {
        console.error("コピー失敗:", err);
      });
  } else {
    // フォールバック
    const textarea = document.createElement("textarea");
    textarea.value = text;
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand("copy");
    document.body.removeChild(textarea);
  }
}

// チャットクリア
function clearAllChat() {
  if (!confirm("会話履歴をクリアしますか？")) return;

  chatWindow.innerHTML =
    '<div class="message ai-message"><p>👋 <strong>ようこそ！</strong><br>寺院名を選択して詳細情報を確認できます。</p></div>';
  currentTempleName = "";

  const quickQaArea = document.getElementById("quick-qa-area");
  quickQaArea.style.display = "none";
}

// ダークモード切り替え
function toggleDarkMode() {
  document.body.classList.toggle("dark-mode");
  const theme = document.body.classList.contains("dark-mode")
    ? "dark"
    : "light";
  localStorage.setItem("theme", theme);
}

// ダークモードの初期化
if (localStorage.getItem("theme") === "dark") {
  document.body.classList.add("dark-mode");
}

// ========================================
// アコーディオン制御
// ========================================

function toggleAccordionFront(headerId, contentId) {
  const header = document.getElementById(headerId);
  const content = document.getElementById(contentId);

  if (!header || !content) {
    // IDが見つからない場合は従来の方法で探す
    const allHeaders = document.querySelectorAll(".accordion-header");
    allHeaders.forEach((h) => {
      if (h.nextElementSibling && h.nextElementSibling.id === contentId) {
        header = h;
        content = h.nextElementSibling;
      }
    });
  }

  if (!header || !content) return;

  const isActive = header.classList.contains("active");

  if (isActive) {
    // 閉じる
    const currentHeight = content.scrollHeight;
    content.style.maxHeight = currentHeight + "px";

    requestAnimationFrame(() => {
      content.style.maxHeight = "0";
      header.classList.remove("active");
      content.classList.remove("active");
    });
  } else {
    // 開く
    header.classList.add("active");
    content.classList.add("active");

    const scrollHeight = content.scrollHeight;
    content.style.maxHeight = scrollHeight + "px";

    setTimeout(() => {
      if (content.classList.contains("active")) {
        content.style.maxHeight = "none";
      }
    }, 400);
  }
}

// ========================================
// お気に入りボタン（詳細画面用）
// ========================================

async function toggleFavoriteDetail(name) {
  try {
    const res = await fetch("/api/v1/favorites/toggle", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ temple_name: name }),
    });

    const data = await res.json();

    if (data.success) {
      // お気に入りリストを更新
      if (data.data.action === "added") {
        favorites.push(name);
      } else {
        const index = favorites.indexOf(name);
        if (index > -1) favorites.splice(index, 1);
      }

      // ボタンの表示を更新
      updateFavoriteButtons(name);
      updateTempleSelect();
    } else {
      alert("お気に入りの更新に失敗しました");
    }
  } catch (e) {
    console.error("お気に入り更新エラー:", e);
    alert("お気に入りの更新に失敗しました");
  }
}

// すべてのお気に入りボタンの表示を更新
function updateFavoriteButtons(templeName) {
  const isFavorite = favorites.includes(templeName);

  // 寺院詳細のボタン
  const detailButtons = document.querySelectorAll(".favorite-btn-detail");
  detailButtons.forEach((btn) => {
    if (btn.dataset.temple === templeName) {
      btn.textContent = isFavorite ? "⭐" : "☆";
      btn.style.borderColor = isFavorite ? "#ffc107" : "#ddd";
    }
  });

  // 宗派別リストのボタン
  const listButtons = document.querySelectorAll(".favorite-btn");
  listButtons.forEach((btn) => {
    const card = btn.closest(".temple-card");
    if (card && card.textContent.includes(templeName)) {
      btn.textContent = isFavorite ? "⭐" : "☆";
    }
  });
}
