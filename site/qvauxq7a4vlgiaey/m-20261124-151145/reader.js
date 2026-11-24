/* 발행 사이트의 조회수·좋아요 (scripts/publish.py가 글 폴더와 목록 폴더에 복사한다).
   글 페이지: <div class="reader-bar" data-article="<글>" hidden> 에 좋아요 버튼을, 머리줄 발행일 옆(.site-header-meta)에 조회수를 넣는다.  목록 페이지: .card[data-article] 마다 수치를 붙인다.
   로그인이 없어 '같은 브라우저' 기준이다 — 브라우저에 무작위 방문자 값을 두고(iw:visitor), 조회는 글마다 하루 한 번만 센다.
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
      "@media (prefers-reduced-motion:reduce){.reader-like{transition:none}}";
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
    }, function () {
      if (PREVIEW) { paint(); bar.hidden = views.hidden = false; }  // 작업실 미리보기 — 모양만
    });
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
