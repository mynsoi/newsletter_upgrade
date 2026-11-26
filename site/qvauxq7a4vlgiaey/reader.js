/* 발행 사이트의 조회수·좋아요·챗봇 (scripts/publish.py가 글 폴더와 목록 폴더에 복사한다).
   글 페이지: <div class="reader-bar" data-article="<글>" hidden> 에 좋아요 버튼을, 머리줄 발행일 옆(.site-header-meta)에 조회수를 넣는다.  목록 페이지: .card[data-article] 마다 수치를 붙인다.
   로그인이 없어 '같은 브라우저' 기준이다 — 브라우저에 무작위 방문자 값을 두고(iw:visitor), 조회는 글마다 하루 한 번만 센다.
   챗봇(2026-11-26): 글 페이지 오른쪽 아래의 '이 글에 대해 물어보기' — /api/chat/(api/chat.py)이 그 글과 참고 원문을 근거로 답한다.
     작업실에서 켠 글에만 버튼이 보인다(시험 방식이면 주소에 ?chat=1을 붙인 사람에게만). 대화는 이 창이 열려 있는 동안만 브라우저가 들고 있다.
   모양(CSS)도 여기서 넣는다 — 이미 발행한 글의 style.css를 건드리지 않고 붙일 수 있게.
   수치를 못 받으면(API 없음·끊김) 아무것도 보이지 않는다. 작업실 미리보기에서는 모양만 보인다. */
(function () {
  "use strict";
  var API = "/api/reader/";  // 끝 슬래시 — vercel.json trailingSlash가 없는 주소를 308으로 돌린다
  var PREVIEW = /^\/publish\//.test(location.pathname) || location.protocol === "file:";

  var mem = {};
  function get(k) { try { return localStorage.getItem(k); } catch (e) { return mem[k] || null; } }
  function set(k, v) { try { localStorage.setItem(k, v); } catch (e) { mem[k] = v; } }

  function visitor() {
    var v = get("iw:visitor");
    if (!v || !/^[A-Za-z0-9-]{8,64}$/.test(v)) {
      v = (window.crypto && crypto.randomUUID) ? crypto.randomUUID()
        : "v-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 12) + Math.random().toString(36).slice(2, 12);
      set("iw:visitor", v);
    }
    return v;
  }

  function today() {  // 한국 날짜 — 서버가 세는 날짜와 같게
    return new Date(Date.now() + 9 * 3600 * 1000).toISOString().slice(0, 10);
  }

  function post(body) {
    return fetch(API, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body), keepalive: true })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); });
  }

  function num(n) { return Number(n || 0).toLocaleString("ko-KR"); }

  function style() {
    if (document.getElementById("reader-style")) return;
    var s = document.createElement("style");
    s.id = "reader-style";
    s.textContent =
      ".reader-bar{display:flex;align-items:center;justify-content:center;gap:16px;margin:8px 0 40px;font-size:14px;color:var(--ink-muted,#6E7278)}" +
      ".reader-bar[hidden]{display:none}" +
      ".reader-like{display:inline-flex;align-items:center;gap:8px;min-height:44px;padding:0 20px;border:1px solid var(--line,#DFE1E5);border-radius:999px;" +
      "background:var(--surface,#fff);color:var(--ink-secondary,#3D4148);font:inherit;font-weight:600;cursor:pointer;transition:border-color .15s,color .15s,background .15s}" +
      ".reader-like:hover{border-color:var(--accent,#0B6E4F);color:var(--accent,#0B6E4F)}" +
      ".reader-like:focus-visible{outline:2px solid var(--accent,#0B6E4F);outline-offset:2px}" +
      ".reader-like svg{width:18px;height:18px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linejoin:round}" +
      ".reader-like[aria-pressed=true]{border-color:var(--accent,#0B6E4F);background:var(--accent-soft,#DCEFE7);color:var(--accent,#0B6E4F)}" +
      ".reader-like[aria-pressed=true] svg{fill:currentColor}" +
      ".reader-like-count,.reader-views{font-variant-numeric:tabular-nums}" +
      ".site-header-meta.has-views{display:inline-flex;align-items:center;gap:14px}" +
      ".reader-views{display:inline-flex;align-items:center;gap:5px}" +
      ".reader-views[hidden]{display:none}" +
      ".reader-views svg{width:15px;height:15px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}" +
      ".card-stats{margin-top:12px;font-size:13px;color:var(--muted,#6E7278);font-variant-numeric:tabular-nums}" +
      // 챗봇
      ".rq-open{position:fixed;right:20px;bottom:20px;z-index:200;display:inline-flex;align-items:center;gap:8px;min-height:48px;padding:0 20px;border:0;border-radius:999px;" +
      "background:var(--accent,#0B6E4F);color:#fff;font:inherit;font-size:14.5px;font-weight:600;cursor:pointer;box-shadow:0 6px 20px rgba(16,17,20,.18);transition:transform .15s,box-shadow .15s}" +
      ".rq-open:hover{transform:translateY(-1px);box-shadow:0 10px 26px rgba(16,17,20,.22)}" +
      ".rq-open svg,.rq-send svg,.rq-close svg{width:18px;height:18px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}" +
      ".rq-open:focus-visible,.rq-send:focus-visible,.rq-close:focus-visible{outline:2px solid var(--accent,#0B6E4F);outline-offset:2px}" +
      ".rq-panel{position:fixed;right:20px;bottom:20px;z-index:201;display:flex;flex-direction:column;width:380px;max-width:calc(100vw - 32px);height:560px;max-height:calc(100vh - 40px);" +
      "background:var(--surface,#fff);border:1px solid var(--line,#DFE1E5);border-radius:20px;box-shadow:0 18px 50px rgba(16,17,20,.22);overflow:hidden;font-size:14.5px;color:var(--ink,#101114)}" +
      ".rq-panel[hidden],.rq-open[hidden]{display:none}" +
      ".rq-head{display:flex;align-items:center;gap:8px;padding:14px 12px 14px 18px;border-bottom:1px solid var(--line,#DFE1E5);font-weight:700}" +
      ".rq-head span{flex:1}" +
      ".rq-close{display:inline-flex;align-items:center;justify-content:center;width:36px;height:36px;border:0;border-radius:999px;background:none;color:var(--ink-muted,#6E7278);cursor:pointer}" +
      ".rq-close:hover{background:var(--canvas,#F7F8FA);color:var(--ink,#101114)}" +
      ".rq-log{flex:1;overflow-y:auto;padding:16px 16px 8px;display:flex;flex-direction:column;gap:10px;overscroll-behavior:contain}" +
      ".rq-intro{font-size:12.5px;line-height:1.6;color:var(--ink-muted,#6E7278);margin:0 0 4px}" +
      ".rq-msg{max-width:88%;padding:10px 14px;border-radius:16px;line-height:1.65;white-space:pre-wrap;word-break:keep-all;overflow-wrap:anywhere}" +
      ".rq-msg.me{align-self:flex-end;background:var(--accent,#0B6E4F);color:#fff;border-bottom-right-radius:6px}" +
      ".rq-msg.bot{align-self:flex-start;background:var(--canvas,#F7F8FA);color:var(--ink-secondary,#3D4148);border-bottom-left-radius:6px}" +
      ".rq-msg.err{align-self:flex-start;background:#FEF3F2;color:#B42318;border-bottom-left-radius:6px}" +
      ".rq-wait{display:inline-flex;gap:4px;padding:4px 0}" +
      ".rq-wait i{width:6px;height:6px;border-radius:50%;background:var(--ink-muted,#6E7278);animation:rq-blink 1.2s infinite both}" +
      ".rq-wait i:nth-child(2){animation-delay:.2s}.rq-wait i:nth-child(3){animation-delay:.4s}" +
      "@keyframes rq-blink{0%,80%,100%{opacity:.25}40%{opacity:1}}" +
      ".rq-refs{align-self:flex-start;max-width:88%;margin:-4px 0 2px;font-size:12px;line-height:1.6;color:var(--ink-muted,#6E7278)}" +
      ".rq-refs a{color:inherit;text-decoration:underline;text-underline-offset:2px}" +
      ".rq-refs a:hover{color:var(--accent,#0B6E4F)}" +
      ".rq-form{display:flex;align-items:flex-end;gap:8px;padding:10px 12px 12px;border-top:1px solid var(--line,#DFE1E5)}" +
      ".rq-form textarea{flex:1;box-sizing:border-box;min-height:44px;max-height:120px;resize:none;border:1px solid var(--line,#DFE1E5);border-radius:14px;background:var(--surface,#fff);" +
      "color:var(--ink,#101114);font:inherit;font-size:15px;line-height:1.5;padding:10px 12px;outline:none;overflow-y:hidden}" +
      ".rq-form textarea:focus{border-color:var(--accent,#0B6E4F)}" +
      ".rq-form textarea::placeholder{color:var(--ink-muted,#6E7278)}" +
      ".rq-send{display:inline-flex;align-items:center;justify-content:center;flex:none;width:44px;height:44px;border:0;border-radius:999px;background:var(--accent,#0B6E4F);color:#fff;cursor:pointer}" +
      ".rq-send:disabled{opacity:.4;cursor:default}" +
      "@media (max-width:640px){.rq-open{right:14px;bottom:14px}.rq-panel{right:0;bottom:0;width:100vw;max-width:none;height:82vh;max-height:none;border-radius:20px 20px 0 0;border-bottom:0}" +
      ".rq-form textarea{font-size:16px}}" +
      "@media (prefers-reduced-motion:reduce){.reader-like,.rq-open{transition:none}.rq-wait i{animation:none}}";
    document.head.appendChild(s);
  }

  function article(bar) {
    var id = bar.getAttribute("data-article"), who = visitor();
    var state = { views: 0, likes: 0, liked: false }, busy = false;
    bar.innerHTML =
      '<button type="button" class="reader-like" aria-pressed="false">' +
      '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 20.5s-7.5-4.6-7.5-10.2A4.3 4.3 0 0 1 12 7.6a4.3 4.3 0 0 1 7.5 2.7c0 5.6-7.5 10.2-7.5 10.2z"/></svg>' +
      '<span>좋아요</span><span class="reader-like-count"></span></button>';
    // 조회수는 머리줄의 발행일 옆에 눈 아이콘 + 숫자로(2026-11-20) — 머리줄이 없는 페이지면 좋아요 옆에
    var views = document.createElement("span");
    views.className = "reader-views";
    views.hidden = true;
    views.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z"/><circle cx="12" cy="12" r="2.8"/></svg><span></span>';
    var meta = document.querySelector(".site-header-meta");
    if (meta) meta.classList.add("has-views");
    (meta || bar).appendChild(views);
    var btn = bar.querySelector(".reader-like"), likeN = bar.querySelector(".reader-like-count"), viewN = views.lastChild;

    function paint() {
      btn.setAttribute("aria-pressed", state.liked ? "true" : "false");
      likeN.textContent = num(state.likes);
      viewN.textContent = num(state.views);
      views.setAttribute("aria-label", "조회 " + num(state.views));
    }
    function take(x) { state = { views: x.views, likes: x.likes, liked: !!x.liked }; paint(); }

    btn.addEventListener("click", function () {
      if (busy || PREVIEW) return;
      busy = true;
      var before = state, on = !state.liked;
      state = { views: before.views, likes: Math.max(0, before.likes + (on ? 1 : -1)), liked: on };  // 먼저 바꿔 보이고, 응답으로 맞춘다
      paint();
      post({ article: id, visitor: who, like: on }).then(take, function () { state = before; paint(); })
        .then(function () { busy = false; });
    });

    var key = "iw:v:" + id, first = get(key) !== today();
    post({ article: id, visitor: who, view: first }).then(function (x) {
      if (first) set(key, today());
      take(x);
      bar.hidden = views.hidden = false;
      if (x.chat === "on" || (x.chat === "test" && /[?&]chat=1(&|$)/.test(location.search))) chat(id, who);
    }, function () {
      if (PREVIEW) { paint(); bar.hidden = views.hidden = false; }  // 작업실 미리보기 — 모양만
    });
  }

  /* 챗봇 — 오른쪽 아래 버튼을 누르면 대화창이 열린다. 답변은 문장 단위로 흘러온다(한 줄에 JSON 하나).
     앞선 대화(history)는 이 창이 들고 있다가 질문과 함께 보낸다. 글자는 textContent로만 넣는다. */
  function chat(id, who) {
    function node(tag, cls, text) { var x = document.createElement(tag); if (cls) x.className = cls; if (text != null) x.textContent = text; return x; }
    var ICON_ASK = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4.5 6.5a2 2 0 0 1 2-2h11a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H11l-4.5 3.5v-3.5a2 2 0 0 1-2-2z"/></svg>';
    var open = node("button", "rq-open");
    open.type = "button";
    open.innerHTML = ICON_ASK + "<span>이 글에 대해 물어보기</span>";
    var panel = node("section", "rq-panel");
    panel.hidden = true;
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-label", "이 글에 대해 물어보기");
    var head = node("div", "rq-head"), close = node("button", "rq-close");
    close.type = "button"; close.setAttribute("aria-label", "닫기");
    close.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>';
    head.appendChild(node("span", "", "이 글에 대해 물어보기")); head.appendChild(close);
    var log = node("div", "rq-log");
    log.setAttribute("aria-live", "polite");
    log.appendChild(node("p", "rq-intro", "이 글과 참고자료를 바탕으로 AI가 답합니다. 틀릴 수 있으니 중요한 내용은 원문에서 확인해 주세요. 질문과 답변은 서비스 개선을 위해 기록됩니다."));
    var form = node("form", "rq-form"), input = node("textarea"), send = node("button", "rq-send");
    input.rows = 1; input.maxLength = 300; input.placeholder = "궁금한 점을 물어보세요"; input.setAttribute("aria-label", "질문");
    send.type = "submit"; send.disabled = true; send.setAttribute("aria-label", "보내기");
    send.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 19V5M5.5 11.5L12 5l6.5 6.5"/></svg>';
    form.appendChild(input); form.appendChild(send);
    panel.appendChild(head); panel.appendChild(log); panel.appendChild(form);
    document.body.appendChild(open); document.body.appendChild(panel);

    var history = [], busy = false, cited = false;  // 참고자료 링크는 첫 답변 아래에 한 번만
    function bottom() { log.scrollTop = log.scrollHeight; }
    function check() { send.disabled = busy || !input.value.trim(); }
    function grow() { input.style.height = "auto"; input.style.height = Math.min(input.scrollHeight + 2, 120) + "px"; input.style.overflowY = input.scrollHeight + 2 > 120 ? "auto" : "hidden"; }
    function show(on) {
      panel.hidden = !on; open.hidden = on;
      if (on) { input.focus(); bottom(); } else { open.focus(); }
    }
    open.addEventListener("click", function () { show(true); });
    close.addEventListener("click", function () { show(false); });
    panel.addEventListener("keydown", function (e) { if (e.key === "Escape") show(false); });
    input.addEventListener("input", function () { grow(); check(); });
    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); if (!send.disabled) ask(); }
    });
    form.addEventListener("submit", function (e) { e.preventDefault(); if (!send.disabled) ask(); });

    function refs(list) {
      var withUrl = (list || []).filter(function (r) { return r.url; });
      if (cited || !withUrl.length) return;
      cited = true;
      var box = node("div", "rq-refs", "참고자료: ");
      withUrl.forEach(function (r, i) {
        if (i) box.appendChild(document.createTextNode(" · "));
        var a = node("a", "", r.label || r.url);
        a.href = r.url; a.target = "_blank"; a.rel = "noopener";
        box.appendChild(a);
      });
      log.appendChild(box);
    }

    function ask() {
      var q = input.value.trim();
      busy = true; input.value = ""; grow(); check();
      log.appendChild(node("div", "rq-msg me", q));
      var bot = node("div", "rq-msg bot"), wait = node("span", "rq-wait");
      wait.innerHTML = "<i></i><i></i><i></i>";
      bot.appendChild(wait);
      log.appendChild(bot); bottom();
      var text = "", failed = false;
      function fail(msg) {
        failed = true;
        if (text) { log.appendChild(node("div", "rq-msg err", msg)); } else { bot.className = "rq-msg err"; bot.textContent = msg; }
      }
      function take(line) {
        var m;
        try { m = JSON.parse(line); } catch (e) { return; }
        if (m.t === "text") { if (!text) bot.textContent = ""; text += m.v; bot.textContent = text; }
        else if (m.t === "error") fail(m.v);
        else if (m.t === "done") refs(m.sources);
        bottom();
      }
      fetch("/api/chat/", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ article: id, visitor: who, question: q, history: history.slice(-6) }) })
        .then(function (r) {
          if (!r.ok) return r.json().catch(function () { return {}; }).then(function (j) { fail(j.error || "지금은 답변을 드릴 수 없습니다. 잠시 뒤에 다시 물어봐 주세요."); });
          if (!r.body || !r.body.getReader) return r.text().then(function (t) { t.split("\n").forEach(function (l) { if (l) take(l); }); });
          var reader = r.body.getReader(), dec = new TextDecoder(), buf = "";
          function pump() {
            return reader.read().then(function (x) {
              buf += dec.decode(x.value || new Uint8Array(), { stream: !x.done });
              var lines = buf.split("\n");
              buf = lines.pop();
              lines.forEach(function (l) { if (l) take(l); });
              if (x.done) { if (buf) take(buf); return; }
              return pump();
            });
          }
          return pump();
        })
        .catch(function () { fail("연결이 끊겼습니다. 잠시 뒤에 다시 물어봐 주세요."); })
        .then(function () {
          if (!text && !failed) fail("지금은 답변을 드릴 수 없습니다. 잠시 뒤에 다시 물어봐 주세요.");
          if (text && !failed) history.push({ role: "user", content: q }, { role: "assistant", content: text });
          busy = false; check(); bottom(); input.focus();
        });
    }
  }

  function index(cards) {
    fetch(API).then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); }).then(function (all) {
      cards.forEach(function (c) {
        var x = all[c.getAttribute("data-article")], body = c.querySelector(".card-body");
        if (!x || !body) return;
        var el = document.createElement("div");
        el.className = "card-stats";
        el.textContent = "조회 " + num(x.views) + " · 좋아요 " + num(x.likes);
        body.appendChild(el);
      });
    }, function () {});
  }

  function start() {
    var bar = document.querySelector(".reader-bar[data-article]");
    var cards = Array.prototype.slice.call(document.querySelectorAll(".card[data-article]"));
    if (!bar && !cards.length) return;
    style();
    if (bar) article(bar);
    if (cards.length) index(cards);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();
})();
