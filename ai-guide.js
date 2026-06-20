/**
 * AI 大屏讲解员 - 前端注入脚本
 *
 * 注入悬浮按钮，点击后 POST timestamp + 页面名到讲解员 API。
 * 服务端自动 CDP 截图 → 识别 → 返回讲解词。
 *
 * 用法：
 *   <script src="http://localhost:8000/ai-guide.js"></script>
 */

(function () {
  const API_URL = "http://localhost:8000/api/v1/describe";
  const MENU_NAME = document.title || "驾驶舱大屏";

  const makeStyle = (parts) => parts.join("; ");

  const btn = document.createElement("button");
  btn.textContent = "🤖 AI 介绍";
  btn.style.cssText = makeStyle([
    "position: fixed",
    "bottom: 32px",
    "right: 32px",
    "z-index: 99999",
    "padding: 12px 24px",
    "font-size: 16px",
    "font-weight: 600",
    "color: #fff",
    "background: linear-gradient(135deg, #4f46e5, #7c3aed)",
    "border: none",
    "border-radius: 12px",
    "cursor: pointer",
    "box-shadow: 0 4px 20px rgba(79, 70, 229, 0.4)",
    "transition: transform 0.15s, box-shadow 0.15s",
    "font-family: system-ui, -apple-system, sans-serif",
  ]);

  const panel = document.createElement("div");
  panel.style.cssText = makeStyle([
    "position: fixed",
    "bottom: 96px",
    "right: 32px",
    "z-index: 99998",
    "width: 440px",
    "max-height: 400px",
    "background: rgba(15, 23, 42, 0.93)",
    "backdrop-filter: blur(12px)",
    "border: 1px solid rgba(255, 255, 255, 0.12)",
    "border-radius: 16px",
    "padding: 20px 24px",
    "color: #e2e8f0",
    "font-family: system-ui, -apple-system, sans-serif",
    "font-size: 15px",
    "line-height: 1.7",
    "overflow-y: auto",
    "box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5)",
    "transform: translateY(12px)",
    "opacity: 0",
    "transition: transform 0.25s ease, opacity 0.25s ease",
    "pointer-events: none",
  ]);

  const closeBtn = document.createElement("button");
  closeBtn.textContent = "✕";
  closeBtn.style.cssText = makeStyle([
    "position: absolute",
    "top: 10px",
    "right: 14px",
    "background: none",
    "border: none",
    "color: #94a3b8",
    "font-size: 20px",
    "cursor: pointer",
    "padding: 4px 6px",
    "line-height: 1",
  ]);
  closeBtn.onclick = (e) => { e.stopPropagation(); hidePanel(); };

  const content = document.createElement("div");
  content.style.paddingRight = "20px";

  panel.appendChild(closeBtn);
  panel.appendChild(content);
  document.body.appendChild(btn);
  document.body.appendChild(panel);

  function showPanel(html) {
    content.innerHTML = html;
    panel.style.transform = "translateY(0)";
    panel.style.opacity = "1";
    panel.style.pointerEvents = "auto";
  }

  function hidePanel() {
    panel.style.transform = "translateY(12px)";
    panel.style.opacity = "0";
    panel.style.pointerEvents = "none";
  }

  // ─── 按钮点击：发 timestamp + 页面名 → 服务端截图 → 返回讲解词 ──
  btn.addEventListener("click", async () => {
    if (btn.disabled) return;

    btn.disabled = true;
    btn.textContent = "⏳ 识别中...";
    btn.style.opacity = "0.6";
    btn.style.cursor = "not-allowed";
    btn.style.transform = "none";

    showPanel(
      '<span style="color: #a5b4fc; font-style: italic;">⏳ 正在通过服务端截图识别，请稍候...</span>'
    );

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
      if (!desc) throw new Error("返回数据为空");

      const html = desc
        .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
        .replace(/\n/g, "<br>")
        .replace(/> (.+)/g, "&gt; $1");
      showPanel(html);
    } catch (err) {
      showPanel(
        '<span style="color: #fca5a5;">❌ 识别失败：' +
          err.message +
          "</span>"
      );
    } finally {
      btn.disabled = false;
      btn.textContent = "🤖 AI 介绍";
      btn.style.opacity = "1";
      btn.style.cursor = "pointer";
    }
  });
})();
