/**
 * AI 大屏讲解员 - 前端注入脚本
 *
 * 注入悬浮按钮，点击后触发服务端 CDP 截图 + LLM 识别。
 * 讲解词返回后打印到控制台（面板已隐藏，待 TTS 集成）。
 *
 * 用法：
 *   <script src="http://localhost:8000/ai-guide.js"></script>
 */

(function () {
  const API_URL = "http://localhost:8000/api/v1/describe";
  const MENU_NAME = document.title || "驾驶舱大屏";

  const btn = document.createElement("button");
  btn.textContent = "🤖 AI 介绍";
  Object.assign(btn.style, {
    position: "fixed",
    bottom: "32px",
    right: "32px",
    zIndex: "99999",
    padding: "12px 24px",
    fontSize: "16px",
    fontWeight: "600",
    color: "#fff",
    background: "linear-gradient(135deg, #4f46e5, #7c3aed)",
    border: "none",
    borderRadius: "12px",
    cursor: "pointer",
    boxShadow: "0 4px 20px rgba(79, 70, 229, 0.4)",
    fontFamily: "system-ui, -apple-system, sans-serif",
  });

  document.body.appendChild(btn);

  btn.addEventListener("click", async () => {
    if (btn.disabled) return;

    btn.disabled = true;
    btn.textContent = "⏳ 识别中...";
    btn.style.opacity = "0.6";
    btn.style.cursor = "not-allowed";

    try {
      const ts = Date.now().toString();
      const resp = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ timestamp: ts, menu_name: MENU_NAME }),
      });
      const body = await resp.json();
      if (!resp.ok) throw new Error(body.detail || `HTTP ${resp.status}`);

      const desc = body?.data?.description;
      if (desc) {
        console.log("🤖 AI 讲解词:", desc);
      }
    } catch (err) {
      console.error("❌ AI 识别失败:", err.message);
    } finally {
      btn.disabled = false;
      btn.textContent = "🤖 AI 介绍";
      btn.style.opacity = "1";
      btn.style.cursor = "pointer";
    }
  });
})();
