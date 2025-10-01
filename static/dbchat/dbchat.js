// 리버스 프록시(Nginx)로 /api → FastAPI 라우팅할 때:
const API_BASE = "http://127.0.0.1:8080/api";
// 프록시 없이 FastAPI가 8001 포트에서 따로 돌면:
// const API_BASE = "http://localhost:8001/api";

// ===== 스트리밍 속도 설정 =====
const STREAM_CPS = 18;   // 초당 글자 수(낮을수록 더 느리게)
const TICK_MS    = 50;   // 화면 갱신 주기(ms)

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
    return div;
  }

  // 로딩 말풍선(점 3개 애니메이션 포함)
  function addStreamingMessageShell(){
    const div = document.createElement("div");
    div.className = "bubble ai-msg loading";
    div.innerHTML = `
      <span class="typing-dots" aria-label="생성 중" role="status">
        <span></span><span></span><span></span>
      </span>
    `;
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
    return div;
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

      const menu = document.createElement("div");
      menu.className = "ctx";

      const renameBtn = document.createElement("button");
      renameBtn.type = "button";
      renameBtn.textContent = "제목 변경";

      const delBtn = document.createElement("button");
      delBtn.type = "button";
      delBtn.textContent = "삭제";

      menu.appendChild(renameBtn);
      menu.appendChild(delBtn);

      row.appendChild(titleEl);
      row.appendChild(timeEl);
      row.appendChild(more);
      row.appendChild(menu);

      row.onclick = () => { currentThreadId = t.id; loadMessages(); highlightThread(); };

      more.onclick = (e) => {
        e.stopPropagation();
        document.querySelectorAll(".ctx").forEach(el => { if (el !== menu) el.style.display = "none"; });
        menu.style.display = (menu.style.display === "block" ? "none" : "block");
      };

      renameBtn.onclick = async (e) => {
        e.stopPropagation();
        menu.style.display = "none";
        const currentTitle = (t.title && t.title.trim()) ? t.title : "";
        const newTitle = prompt("새 제목을 입력하세요.", currentTitle);
        if (newTitle === null) return;
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
        await loadThreads();
        highlightThread();
      };

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

  function highlightThread(){
    Array.from(threadsBox.children).forEach(el => {
      el.classList.toggle("active", el.dataset.threadId === currentThreadId);
    });
  }

  async function loadMessages(){
    if (!currentThreadId) return;
    const res  = await fetch(`/dbchat/threads/${currentThreadId}/messages`);
    const data = await res.json();
    chatBox.innerHTML = "";
    (data.messages || []).forEach(m => addMessage(m.role, m.content));
    chatBox.scrollTop = chatBox.scrollHeight;
  }

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


  function createPacedWriter(aiBubble) {
    let displayBuffer = "";
    let timer = null;
    let doneReading = false;

    const charsPerTick = Math.max(1, Math.floor((STREAM_CPS * TICK_MS) / 1000));

    function start() {
      if (timer) return;
      timer = setInterval(() => {
        if (displayBuffer.length > 0) {
          const take = displayBuffer.slice(0, charsPerTick);
          displayBuffer = displayBuffer.slice(charsPerTick);
          aiBubble.textContent += take;
          chatBox.scrollTop = chatBox.scrollHeight;
        } else if (doneReading) {
          stop();
        }
      }, TICK_MS);
    }

    function stop() {
      if (timer) {
        clearInterval(timer);
        timer = null;
      }
    }

    return {
      push(chunk) {
        displayBuffer += chunk;
        start();
      },
      finish() {
        doneReading = true;
        start(); 
      },
      cancel() { stop(); }
    };
  }

  /* ---- 질문 전송 → 스트리밍으로 받기 ---- */
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const q = input.value.trim();
    if (!q) return;

    addMessage("user", q);
    input.value = "";
    input.focus();

    const aiBubble = addStreamingMessageShell();

    const writer = createPacedWriter(aiBubble);
    let started = false;

    try {
      const res = await fetch(`${API_BASE}/ask_stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q })
      });

      if (!res.ok) {
        const errTxt = await res.text().catch(() => "");
        aiBubble.classList.remove("loading");
        aiBubble.textContent = `오류: ${res.status} ${errTxt || res.statusText}`;
        return;
      }

      if (!res.body) {
        aiBubble.classList.remove("loading");
        aiBubble.textContent = "스트림 본문이 없습니다.";
        return;
      }

      const reader  = res.body.getReader();
      const decoder = new TextDecoder("utf-8");

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        if (value) {
          let chunk = decoder.decode(value, { stream: true });

          if (!started) {
            chunk = chunk.replace(/^(생성 중\.\.\.|[\s\u200B\uFEFF\r\n]+)/, "");
            if (chunk.length === 0) continue;

            // 로딩 점 제거하고 본문으로 전환
            aiBubble.classList.remove("loading");
            aiBubble.innerHTML = "";
            started = true;
          }

          writer.push(chunk); // 속도 제한 출력
        }
      }

      writer.finish(); // 남은 버퍼 비우고 종료

      if (!started) {
        // 어떤 이유로든 본문이 전혀 오지 않은 경우
        aiBubble.classList.remove("loading");
        aiBubble.textContent = "응답을 불러오지 못했습니다.";
      }
    } catch (err) {
      console.error(err);
      aiBubble.classList.remove("loading");
      aiBubble.textContent = "네트워크 오류가 발생했습니다.";
      writer.cancel();
    }
  });

  /* ---- 초기 로드 ---- */
  loadThreads();
});
