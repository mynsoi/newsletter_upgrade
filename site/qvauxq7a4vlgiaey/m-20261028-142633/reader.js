/* 발행 사이트의 조회수·좋아요·댓글 (scripts/publish.py가 글 폴더와 목록 폴더에 복사한다).
   글 페이지: <div class="reader-bar" data-article="<글>" hidden> 에 좋아요 버튼을, 머리줄 발행일 옆(.site-header-meta)에 조회수·댓글 수를,
             본문 맨 아래(참고자료 다음)에 댓글을 넣는다.  목록 페이지: .card[data-article] 마다 수치를 붙인다.
   로그인이 없어 '같은 브라우저' 기준이다 — 브라우저에 무작위 방문자 값을 두고(iw:visitor), 조회는 글마다 하루 한 번만 센다.
   댓글의 이름은 자유 입력(비우면 익명, iw:name에 기억), '내 댓글'도 방문자 값으로만 가린다. 댓글 글자는 textContent로만 넣는다(태그로 읽히지 않게).
   모양(CSS)도 여기서 넣는다 — 이미 발행한 글의 style.css를 건드리지 않고 붙일 수 있게.
   수치를 못 받으면(API 없음·끊김) 아무것도 보이지 않는다. 작업실 미리보기에서는 모양만 보인다. */
(function () {
  "use strict";
  var API = "/api/reader/";  // 끝 슬래시 — vercel.json trailingSlash가 없는 주소를 308으로 돌린다
  var PREVIEW = /^\/publish\//.test(location.pathname) || location.protocol === "file:";
  var MAX = 500;

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

  // 응답이 실패면 서버가 준 말(error)을 담아 거절한다 — 댓글 화면이 그대로 보여 준다
  function done(r) {
    return r.json().catch(function () { return {}; }).then(function (j) {
      if (!r.ok) { var e = new Error(j.error || String(r.status)); e.code = j.code; throw e; }
      return j;
    });
  }
  function post(body) {
    return fetch(API, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body), keepalive: true }).then(done);
  }

  function num(n) { return Number(n || 0).toLocaleString("ko-KR"); }
  function el(tag, cls, text) {
    var x = document.createElement(tag);
    if (cls) x.className = cls;
    if (text != null) x.textContent = text;
    return x;
  }

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
      // 댓글
      ".reader-comments{border-top:1px solid var(--line,#DFE1E5);padding-top:32px;margin-bottom:48px;scroll-margin-top:72px}" +
      ".reader-comments[hidden],.reader-comments [hidden]{display:none}" +
      ".reader-comments h3{font-size:14px;font-weight:700;color:var(--ink-muted,#6E7278);margin:0 0 16px}" +
      ".reader-comments h3 b{color:var(--ink,#101114);font-variant-numeric:tabular-nums;margin-left:4px}" +
      ".rc-form{display:grid;gap:8px;margin-bottom:8px}" +
      ".rc-form input,.rc-form textarea{width:100%;box-sizing:border-box;border:1px solid var(--line,#DFE1E5);border-radius:12px;background:var(--surface,#fff);" +
      "color:var(--ink,#101114);font:inherit;font-size:15px;line-height:1.6;padding:10px 14px;outline:none;transition:border-color .15s}" +
      ".rc-form input{max-width:220px}" +
      ".rc-form textarea{min-height:92px;resize:vertical}" +
      ".rc-form input:focus,.rc-form textarea:focus{border-color:var(--accent,#0B6E4F)}" +
      ".rc-form input::placeholder,.rc-form textarea::placeholder{color:var(--ink-muted,#6E7278)}" +
      ".rc-row{display:flex;align-items:center;gap:12px;flex-wrap:wrap}" +
      ".rc-note{flex:1;min-width:160px;font-size:12.5px;line-height:1.5;color:var(--ink-muted,#6E7278)}" +
      ".rc-count{font-size:12.5px;color:var(--ink-muted,#6E7278);font-variant-numeric:tabular-nums}" +
      ".rc-count.over{color:#B42318;font-weight:600}" +
      ".rc-submit{min-height:40px;padding:0 20px;border:0;border-radius:999px;background:var(--accent,#0B6E4F);color:#fff;font:inherit;font-size:14px;font-weight:600;cursor:pointer;transition:opacity .15s}" +
      ".rc-submit:hover{opacity:.9}" +
      ".rc-submit:disabled{opacity:.4;cursor:default}" +
      ".rc-submit:focus-visible,.rc-del:focus-visible,.rc-more:focus-visible{outline:2px solid var(--accent,#0B6E4F);outline-offset:2px}" +
      ".rc-msg{min-height:20px;margin:4px 0 8px;font-size:13px;line-height:1.5;color:#B42318}" +
      ".rc-msg.ok{color:var(--accent,#0B6E4F)}" +
      ".rc-closed,.rc-empty{font-size:14px;line-height:1.7;color:var(--ink-muted,#6E7278);margin:0 0 8px}" +
      ".rc-list{list-style:none;margin:0;padding:0}" +
      ".rc-item{padding:16px 0;border-bottom:1px solid var(--line,#DFE1E5)}" +
      ".rc-item:last-child{border-bottom:0}" +
      ".rc-head{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap;margin-bottom:4px}" +
      ".rc-name{font-size:14px;font-weight:700;color:var(--ink,#101114);overflow-wrap:anywhere}" +
      ".rc-at{font-size:12.5px;color:var(--ink-muted,#6E7278);font-variant-numeric:tabular-nums}" +
      ".rc-tag{font-size:12px;font-weight:600;color:var(--accent,#0B6E4F);background:var(--accent-soft,#DCEFE7);border-radius:999px;padding:1px 8px}" +
      ".rc-del{margin-left:auto;border:0;background:none;padding:4px 0;font:inherit;font-size:12.5px;color:var(--ink-muted,#6E7278);cursor:pointer}" +
      ".rc-del:hover,.rc-del.arm{color:#B42318}" +
      ".rc-body{margin:0;font-size:15px;line-height:1.7;color:var(--ink-secondary,#3D4148);white-space:pre-wrap;overflow-wrap:anywhere}" +
      ".rc-more{display:block;margin:12px auto 0;min-height:40px;padding:0 20px;border:1px solid var(--line,#DFE1E5);border-radius:999px;background:var(--surface,#fff);" +
      "color:var(--ink-secondary,#3D4148);font:inherit;font-size:14px;font-weight:600;cursor:pointer}" +
      ".rc-more:hover{border-color:var(--accent,#0B6E4F);color:var(--accent,#0B6E4F)}" +
      "@media (max-width:640px){.rc-form input,.rc-form textarea{font-size:16px}.rc-form input{max-width:none}}" +
      "@media (prefers-reduced-motion:reduce){.reader-like,.rc-form input,.rc-form textarea,.rc-submit{transition:none}}";
    document.head.appendChild(s);
  }

  var ICON_EYE = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z"/><circle cx="12" cy="12" r="2.8"/></svg><span></span>';
  var ICON_TALK = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4.5 6.5a2 2 0 0 1 2-2h11a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H11l-4.5 3.5v-3.5a2 2 0 0 1-2-2z"/></svg><span></span>';

  function article(bar) {
    var id = bar.getAttribute("data-article"), who = visitor();
    var state = { views: 0, likes: 0, liked: false }, busy = false;
    bar.innerHTML =
      '<button type="button" class="reader-like" aria-pressed="false">' +
      '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 20.5s-7.5-4.6-7.5-10.2A4.3 4.3 0 0 1 12 7.6a4.3 4.3 0 0 1 7.5 2.7c0 5.6-7.5 10.2-7.5 10.2z"/></svg>' +
      '<span>좋아요</span><span class="reader-like-count"></span></button>';
    // 조회수·댓글 수는 머리줄의 발행일 옆에 아이콘 + 숫자로(2026-11-20) — 머리줄이 없는 페이지면 좋아요 옆에
    var meta = document.querySelector(".site-header-meta");
    if (meta) meta.classList.add("has-views");
    function badge(icon) {
      var x = el("span", "reader-views");
      x.hidden = true;
      x.innerHTML = icon;
      (meta || bar).appendChild(x);
      return x;
    }
    var views = badge(ICON_EYE), talks = badge(ICON_TALK);
    var btn = bar.querySelector(".reader-like"), likeN = bar.querySelector(".reader-like-count");

    function paint() {
      btn.setAttribute("aria-pressed", state.liked ? "true" : "false");
      likeN.textContent = num(state.likes);
      views.lastChild.textContent = num(state.views);
      views.setAttribute("aria-label", "조회 " + num(state.views));
    }
    function take(x) { state = { views: x.views, likes: x.likes, liked: !!x.liked }; paint(); }
    function talkCount(n) {  // 댓글 수 — 댓글을 받을 수 있을 때만 보인다
      talks.lastChild.textContent = num(n);
      talks.setAttribute("aria-label", "댓글 " + num(n));
      talks.hidden = false;
    }

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

    comments(id, who, talkCount);
  }

  /* 댓글 — 본문 맨 아래(참고자료 다음). 새 것부터 20개, '더 보기'로 이어서.
     쓰기 방식(mode): open 바로 공개 · moderated 승인 뒤 공개(쓴 사람에게만 '승인 대기'로 보임) · closed 새 댓글 받지 않음. */
  function comments(id, who, onCount) {
    var host = document.querySelector("main.article-page") || document.querySelector("main");
    if (!host) return;
    var box = el("section", "reader-comments");
    box.hidden = true;
    box.id = "comments";
    var title = el("h3", "", "댓글"), totalEl = el("b");
    title.appendChild(totalEl);

    var form = el("form", "rc-form"), name = el("input"), body = el("textarea");
    name.type = "text"; name.maxLength = 20; name.placeholder = "이름 (비우면 익명)"; name.autocomplete = "nickname";
    name.setAttribute("aria-label", "이름"); name.value = get("iw:name") || "";
    body.placeholder = "글을 읽고 든 생각을 남겨 주세요"; body.setAttribute("aria-label", "댓글 내용");
    var row = el("div", "rc-row"), note = el("span", "rc-note", "댓글은 이 글을 보는 모든 독자에게 공개됩니다."),
      count = el("span", "rc-count", "0/" + MAX), submit = el("button", "rc-submit", "등록");
    submit.type = "submit"; submit.disabled = true;
    row.appendChild(note); row.appendChild(count); row.appendChild(submit);
    form.appendChild(name); form.appendChild(body); form.appendChild(row);
    var msg = el("div", "rc-msg"); msg.setAttribute("role", "status");
    var closed = el("p", "rc-closed", "지금은 새 댓글을 받지 않습니다."); closed.hidden = true;
    var empty = el("p", "rc-empty", "첫 댓글을 남겨 보세요."); empty.hidden = true;
    var list = el("ul", "rc-list"), more = el("button", "rc-more", "댓글 더 보기");
    more.type = "button"; more.hidden = true;
    [title, form, closed, msg, empty, list, more].forEach(function (x) { box.appendChild(x); });
    host.appendChild(box);

    var total = 0, mode = "open", sending = false, lastId = null;

    function say(text, ok) { msg.textContent = text || ""; msg.className = "rc-msg" + (ok ? " ok" : ""); }
    function setTotal(n) {
      total = n;
      totalEl.textContent = n ? num(n) : "";
      empty.hidden = !!list.children.length || mode === "closed";
      if (mode !== "closed" || n) onCount(n);
    }
    function when(at) {
      try {
        return new Date(at).toLocaleString("ko-KR", { timeZone: "Asia/Seoul", year: "numeric", month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" });
      } catch (e) { return ""; }
    }
    function item(c) {
      var li = el("li", "rc-item"), head = el("div", "rc-head");
      head.appendChild(el("span", "rc-name", c.name));
      head.appendChild(el("span", "rc-at", when(c.at)));
      if (c.pending) head.appendChild(el("span", "rc-tag", "승인 대기"));
      if (c.mine) {
        var del = el("button", "rc-del", "삭제"), timer;
        del.type = "button";
        del.addEventListener("click", function () {
          if (!del.classList.contains("arm")) {  // 한 번 더 눌러야 지운다
            del.classList.add("arm"); del.textContent = "한 번 더 누르면 삭제";
            timer = setTimeout(function () { del.classList.remove("arm"); del.textContent = "삭제"; }, 3000);
            return;
          }
          clearTimeout(timer);
          del.disabled = true;
          post({ article: id, visitor: who, uncomment: c.id }).then(function (x) {
            li.remove();
            setTotal(x.total);
          }, function () { del.disabled = false; del.classList.remove("arm"); del.textContent = "삭제"; say("지우지 못했습니다. 잠시 뒤에 다시 해 주세요."); });
        });
        head.appendChild(del);
      }
      li.appendChild(head);
      li.appendChild(el("p", "rc-body", c.body));
      return li;
    }
    function fill(x, append) {
      mode = x.mode;
      form.hidden = mode === "closed";
      closed.hidden = mode !== "closed";
      note.textContent = mode === "moderated" ? "댓글은 확인을 거친 뒤 모든 독자에게 공개됩니다." : "댓글은 이 글을 보는 모든 독자에게 공개됩니다.";
      if (!append) list.textContent = "";
      x.comments.forEach(function (c) { list.appendChild(item(c)); lastId = c.id; });
      more.hidden = !x.more;
      setTotal(x.total);
    }
    function load(before) {
      var u = API + "?article=" + encodeURIComponent(id) + "&visitor=" + encodeURIComponent(who) + (before ? "&before=" + before : "");
      return fetch(u).then(done).then(function (x) { fill(x, !!before); box.hidden = false; });
    }
    function check() {
      var n = body.value.trim().length;
      count.textContent = n + "/" + MAX;
      count.className = "rc-count" + (n > MAX ? " over" : "");
      submit.disabled = sending || !n || n > MAX || PREVIEW;
    }

    body.addEventListener("input", function () { say(""); check(); });
    more.addEventListener("click", function () {
      more.disabled = true;
      load(lastId).then(function () { more.disabled = false; }, function () { more.disabled = false; say("더 불러오지 못했습니다."); });
    });
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      if (submit.disabled) return;
      sending = true; check(); say("");
      set("iw:name", name.value.trim());
      post({ article: id, visitor: who, comment: { name: name.value, body: body.value } }).then(function (x) {
        list.insertBefore(item(x.comment), list.firstChild);
        body.value = "";
        setTotal(x.total);
        say(x.comment.pending ? "등록했습니다. 확인을 거친 뒤 공개됩니다." : "등록했습니다.", true);
      }, function (err) {
        if (err.code === "closed") { mode = "closed"; form.hidden = true; closed.hidden = false; }
        say(err.code ? err.message : "등록하지 못했습니다. 잠시 뒤에 다시 해 주세요.");
      }).then(function () { sending = false; check(); });
    });

    load().then(null, function () {
      if (PREVIEW) { empty.hidden = false; box.hidden = false; onCount(0); }  // 작업실 미리보기 — 모양만(등록 버튼은 눌리지 않는다)
    });
  }

  function index(cards) {
    fetch(API).then(done).then(function (all) {
      cards.forEach(function (c) {
        var x = all[c.getAttribute("data-article")], body = c.querySelector(".card-body");
        if (!x || !body) return;
        body.appendChild(el("div", "card-stats", "조회 " + num(x.views) + " · 좋아요 " + num(x.likes) + (x.comments ? " · 댓글 " + num(x.comments) : "")));
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
