function getCookie(name){
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
  }
  const csrftoken = getCookie('csrftoken');
  
  document.addEventListener("DOMContentLoaded", () => {
    const threadsBox = document.getElementById("threads");
    const chatBox    = document.getElementById("chat-messages");
    const form       = document.getElementById("chat-form");
    const input      = document.getElementById("question");
    const newBtn     = document.getElementById("new-thread-btn");
  
    let currentThreadId = null;
    let currentThreads  = [];
  
    /* ---- 말풍선 렌더러 ---- */
    function addMessage(role, text){
      const div = document.createElement("div");
      div.className = "bubble " + (role === "user" ? "user-msg" : "ai-msg");
      div.textContent = text;
      chatBox.appendChild(div);
      chatBox.scrollTop = chatBox.scrollHeight;
    }
  
    /* ---- 히스토리 로드 ---- */
    async function loadThreads(){
      const res  = await fetch("/dbchat/threads");
      const data = await res.json();
      currentThreads = data.threads || [];
      threadsBox.innerHTML = "";
  
      currentThreads.forEach(t => {
        const row  = document.createElement("div");
        row.className = "list-item";
        row.dataset.threadId = t.id;
  
        const safeTitle = (t.title && t.title.trim()) ? t.title : "새 대화";
  
        const titleEl = document.createElement("div");
        titleEl.className = "title";
        titleEl.textContent = safeTitle;
  
        const timeEl = document.createElement("div");
        timeEl.className = "muted";
        timeEl.textContent = t.updated_at;
  
        const more = document.createElement("span");
        more.className = "more-btn";
        more.textContent = "⋯";
  
        // 컨텍스트 메뉴
        const menu = document.createElement("div");
        menu.className = "ctx";
  
        // — 제목 변경
        const renameBtn = document.createElement("button");
        renameBtn.type = "button";
        renameBtn.textContent = "제목 변경";
  
        // — 삭제
        const delBtn = document.createElement("button");
        delBtn.type = "button";
        delBtn.textContent = "삭제";
  
        menu.appendChild(renameBtn);
        menu.appendChild(delBtn);
  
        row.appendChild(titleEl);
        row.appendChild(timeEl);
        row.appendChild(more);
        row.appendChild(menu);
  
        // 항목 클릭 = 스레드 열기
        row.onclick = () => { currentThreadId = t.id; loadMessages(); highlightThread(); };
  
        // ... 클릭 = 메뉴 토글
        more.onclick = (e) => {
          e.stopPropagation();
          document.querySelectorAll(".ctx").forEach(el => { if (el !== menu) el.style.display = "none"; });
          menu.style.display = (menu.style.display === "block" ? "none" : "block");
        };
  
        // === 제목 변경 ===
        renameBtn.onclick = async (e) => {
          e.stopPropagation();
          menu.style.display = "none";
          const currentTitle = (t.title && t.title.trim()) ? t.title : "";
          const newTitle = prompt("새 제목을 입력하세요.", currentTitle);
          if (newTitle === null) return; // 취소
          const title = newTitle.trim();
          if (!title) return alert("제목이 비어 있습니다.");
  
          const res = await fetch(`/dbchat/threads/${t.id}/rename`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-CSRFToken": csrftoken
            },
            body: JSON.stringify({ title })
          });
          if (!res.ok) {
            alert("제목 변경에 실패했습니다.");
            return;
          }
          // 목록 재로드 후 선택 유지
          await loadThreads();
          highlightThread();
        };
  
        // === 삭제 ===
        delBtn.onclick = async (e) => {
          e.stopPropagation();
          menu.style.display = "none";
          if (!confirm("이 대화를 삭제하시겠습니까?")) return;
  
          await fetch(`/dbchat/threads/${t.id}/delete`, {
            method: "DELETE",
            headers: { "X-CSRFToken": csrftoken }
          });
  
          if (currentThreadId === t.id) {
            currentThreadId = null;
            chatBox.innerHTML = "";
          }
          await loadThreads();
        };
  
        threadsBox.appendChild(row);
      });
  
      if (!currentThreadId && currentThreads.length){
        currentThreadId = currentThreads[0].id;
        await loadMessages();
      }
      highlightThread();
    }
  
    // 바깥 클릭 시 열린 메뉴 닫기
    document.addEventListener("click", (e) => {
      if (!e.target.classList.contains("more-btn")) {
        document.querySelectorAll(".ctx").forEach(el => el.style.display = "none");
      }
    });
  
    /* ---- 선택 하이라이트 ---- */
    function highlightThread(){
      Array.from(threadsBox.children).forEach(el => {
        el.classList.toggle("active", el.dataset.threadId === currentThreadId);
      });
    }
  
    /* ---- 메시지 로드 ---- */
    async function loadMessages(){
      if (!currentThreadId) return;
      const res  = await fetch(`/dbchat/threads/${currentThreadId}/messages`);
      const data = await res.json();
      chatBox.innerHTML = "";
      (data.messages || []).forEach(m => addMessage(m.role, m.content));
      chatBox.scrollTop = chatBox.scrollHeight;
    }
  
    /* ---- 새 대화 ---- */
    newBtn.addEventListener("click", async () => {
      const res  = await fetch("/dbchat/threads/new", {
        method: "POST",
        headers: { "X-CSRFToken": csrftoken }
      });
      const data = await res.json();
      currentThreadId = data.thread_id;
      chatBox.innerHTML = "";
      await loadThreads();
    });
  
    /* ---- 질문 전송 ---- */
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const q = input.value.trim();
      if (!q) return;
  
      addMessage("user", q);
      input.value = "";
      input.focus();
  
      const res  = await fetch("/dbchat/ask", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrftoken
        },
        body: JSON.stringify({
          thread_id: currentThreadId,
          question: q,
          options: { stream: false, lang: "ko" },
          ui_context: { page: "dbchat" }
        })
      });
  
      const data = await res.json();
      if (data.thread_id) currentThreadId = data.thread_id;
  
      addMessage("ai", data.message?.content || "응답을 불러오지 못했습니다.");
  
      await loadThreads();
      await loadMessages();
    });
  
    /* ---- 초기 로드 ---- */
    loadThreads();
  });
  