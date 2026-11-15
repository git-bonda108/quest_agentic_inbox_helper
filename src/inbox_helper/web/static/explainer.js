/* The explainer timeline.
 *
 * render(t) draws the whole stage for a moment t in seconds, from the data in the
 * page (recorded runs, never typed here). Nothing animates on its own, so play,
 * pause, seek and a frame-by-frame recording all show exactly the same picture.
 */
"use strict";
(function () {
  var D = JSON.parse(document.getElementById("data").textContent);
  var params = new URLSearchParams(location.search);
  var RECORD = params.has("record");
  var W = 1440, H = 810, TOTAL = 86;
  var STEP_AT = [0, 7, 15, 28, 36, 47, 63];
  var END_AT = 80;

  var $ = function (id) { return document.getElementById(id); };
  var stage = $("stage"), viewport = $("viewport");
  if (RECORD) document.documentElement.classList.add("record");

  // ---------------------------------------------------------------- helpers
  function clamp(x, a, b) { return Math.min(b === undefined ? 1 : b, Math.max(a === undefined ? 0 : a, x)); }
  function prog(t, a, b) { return clamp((t - a) / (b - a)); }
  function ease(x) { return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; }
  function lerp(a, b, x) { return a + (b - a) * x; }
  function within(t, a, b) { return t >= a && t < (b === undefined ? Infinity : b); }
  // Opacity of something shown from a until b, with short fades.
  function vis(t, a, b, d) {
    d = d || 0.35;
    var shown = prog(t, a, a + d);
    if (b === undefined || b === Infinity) return shown;
    return Math.min(shown, 1 - prog(t, b, b + d));
  }
  function setOpacity(el, o) {
    var v = o <= 0 ? "0" : o >= 1 ? "1" : o.toFixed(3);
    if (el._o !== v) { el.style.opacity = v; el._o = v; }
  }
  function setText(el, s) { if (el._t !== s) { el.textContent = s; el._t = s; } }
  function setClass(el, name, on) { el.classList.toggle(name, !!on); }
  function setTransform(el, s) { if (el._tr !== s) { el.style.transform = s; el._tr = s; } }
  function dots(t) { return ".".repeat(1 + (Math.floor(t * 3) % 3)); }
  function first(name) { return name.split(" ")[0]; }
  var NUMBER = ["No", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"];

  // Position of an element on the stage, ignoring transforms.
  function box(el) {
    var x = 0, y = 0, e = el;
    while (e && e !== stage) { x += e.offsetLeft; y += e.offsetTop; e = e.offsetParent; }
    return { x: x, y: y, w: el.offsetWidth, h: el.offsetHeight, cx: x + el.offsetWidth / 2, cy: y + el.offsetHeight / 2 };
  }

  // ---------------------------------------------------------------- data
  var rows = D.rows;
  var focus = D.focus;
  var readRows = rows.filter(function (r) { return !r.blocked; });
  var drafted = rows.filter(function (r) { return r.tag === "To the Drafter"; });
  var blockedRow = rows.filter(function (r) { return r.blocked; })[0];
  var injectedRow = rows.filter(function (r) { return r.key === D.injected.key; })[0];
  var draft1 = focus.attempts[0].text;
  // Only said when the recording shows it: every other draft passed on its first attempt.
  function othersSentence() {
    var others = drafted.filter(function (r) { return r.key !== focus.key; });
    var firstTry = others.filter(function (r) { return r.attempts === 1; });
    return others.length && firstTry.length === others.length ? " The other " + NUMBER[others.length].toLowerCase() + " passed on the first attempt." : "";
  }
  var draft2 = focus.final;

  var CAPTIONS = [
    ["Nine candidate messages", " land in the hiring inbox. Every name and message here is synthetic."],
    ["The guardrail", " on the Foundry agent blocks " + first(D.blocked.name) + "'s message, which hides an instruction to announce an offer. No model reads it; a person will."],
    ["The Classifier agent", " answers two questions for each message: what does the person want, and must a person handle it?"],
    ["Routing is code, not a model.", " A reason for a person, or under " + D.floor + " sure: to a person. Not a candidate: set aside. " + NUMBER[drafted.length] + " go to the Drafter."],
    ["The Drafter agent", " writes each reply from the hiring policy only. Code checks every draft: " + D.max_words + " words or fewer, no amounts, no “!”, the right sign-off."],
    ["The Critic agent,", " a different model, sends " + focus.first + "'s draft back: the policy does not promise a follow-up. The Drafter rewrites it, and the Critic accepts." + othersSentence()],
    ["A person decides.", " " + D.reviewer + " reads the draft and chooses Approve and send, or Reject. Only the exact text " + D.reviewer + " approved goes out, once, and every step is in the audit trail."],
  ];

  // ---------------------------------------------------------------- timeline
  var T = {
    rowIn: function (i) { return 0.6 + i * 0.5; },
    mailOut: function (i) { return 7.5 + i * 0.25; },
    blockedAt: 0, // set below
    readIn: function (j) { return 16.0 + j * 1.15; },
    routeIn: function (j) { return 29.0 + j * 0.4; },
    toDrafter: function (k) { return 33.6 + k * 0.18; },
    type1: [37.0, 41.4], ticks1: [41.9, 42.3, 42.7, 43.1], send1: [43.6, 44.4],
    rejected: 47.0, flag: 47.3, bubCritic: 47.6, back: [48.0, 49.2],
    attempt2: 49.6, bubDrafter: 49.8, type2: [50.2, 53.2], ticks2: [53.5, 53.8, 54.1, 54.4], send2: [54.6, 55.4],
    accepted: 56.4, bubAccept: 56.6,
    toDesk: function (k) { return 58.0 + k * 0.3; },
    card: 63.4, cursorIn: 65.6, toReject: [66.0, 67.0], hoverReject: [67.0, 68.6], toApprove: [68.6, 69.4],
    press: 69.8, stamp: 70.1, toGate: [70.6, 71.3], toOut: [71.5, 72.2], audit: function (k) { return 72.8 + k * 0.55; },
  };
  var blockedIndex = rows.indexOf(blockedRow);
  T.blockedAt = T.mailOut(blockedIndex) + 0.7;

  // ---------------------------------------------------------------- elements
  var el = {
    steps: Array.prototype.slice.call(document.querySelectorAll("#steps li")),
    inboxCount: $("inboxCount"),
    guard: $("guard"), guardState: $("guardState"),
    classifier: $("ag-classifier"), drafter: $("ag-drafter"), critic: $("ag-critic"),
    stC: $("st-classifier"), stD: $("st-drafter"), stK: $("st-critic"),
    qC: $("q-classifier"), qD: $("q-drafter"), qK: $("q-critic"),
    link1: $("link-1"), link2: $("link-2"), routing: $("code-routing"), checks: $("code-checks"),
    idle: $("sc-idle"), blocked: $("sc-blocked"), readout: $("sc-readout"), focus: $("sc-focus"),
    note: $("noteInjected"), draftCard: $("draftCard"), draftText: $("draftText"), attempt: $("attempt"),
    verdict: $("critVerdict"), bubCritic: $("bub-critic"), bubDrafter: $("bub-drafter"), bubAccept: $("bub-accept"),
    reviewer: $("reviewer"), reading: $("reading"), rcard: $("rcard"), approve: $("btnApprove"), reject: $("btnReject"),
    tip: $("tipReject"), stamp: $("stamp"), btns: document.querySelector(".rbtns"), gate: $("gateRow"), gateText: $("gateText"), out: $("outRow"), outText: $("outText"),
    capNum: $("capNum"), capText: $("capText"), caption: $("caption"), cursor: $("cursor"), endcard: $("endcard"),
    tokens: $("tokens"), audit: $("audit"),
  };
  var rowEl = {}, tagEl = {}, roEl = {}, rtEl = {};
  rows.forEach(function (r) { rowEl[r.key] = $("row-" + r.key); tagEl[r.key] = $("tag-" + r.key); });
  readRows.forEach(function (r) { roEl[r.key] = $("ro-" + r.key); rtEl[r.key] = $("rt-" + r.key); });
  var checkEls = [0, 1, 2, 3].map(function (i) { return $("ck-" + i); });
  var auditEls = focus.audit.map(function (_, k) { return $("au-" + k); });
  var laneCount = {};
  D.lanes.forEach(function (l) { laneCount[l.key] = $("n-" + l.key); });

  // ---------------------------------------------------------------- tokens
  // A token travels through waypoints [x, y, t]; it shows from the first to the last.
  var tokens = [];
  function token(cls, icon, label, pts, lane) {
    var node = document.createElement("span");
    node.className = "tok " + cls;
    var ic = document.createElement("span");
    ic.className = "ic";
    ic.textContent = icon;
    node.appendChild(ic);
    node.appendChild(document.createTextNode(label));
    el.tokens.appendChild(node);
    tokens.push({ node: node, pts: pts, lane: lane || null });
  }
  function at(b, t, dx, dy) { return [b.cx + (dx || 0), b.cy + (dy || 0), t]; }

  function buildTokens() {
    el.tokens.textContent = "";
    tokens = [];
    var G = box(el.guard), Z = box($("guardZone")), C = box(el.classifier), R = box(el.routing), Dr = box(el.drafter);
    var K = box(el.checks), Cr = box(el.critic), card = box(el.rcard), gate = box(el.gate), out = box(el.out);
    function lane(key) { return box($("lane-" + key)); }

    rows.forEach(function (r, i) {
      var start = box(rowEl[r.key]);
      var t0 = T.mailOut(i), tg = t0 + 0.7;
      var gx = Z.x + 44 + i * ((Z.w - 88) / (rows.length - 1));
      var from = [start.x + start.w - 30, start.cy, t0];
      if (r.blocked) {
        var L = lane("person");
        token("mail", "✉", first(r.name), [from, [gx, Z.cy, tg], [gx, Z.cy, 12.6], [L.cx, L.cy, 13.6]], "person");
      } else {
        token("mail", "✉", first(r.name), [from, [gx, Z.cy, tg], [C.cx, C.cy - 8, tg + 0.55]]);
      }
    });

    var k = 0;
    rows.forEach(function (r) {
      if (r.blocked) return;
      if (r.lane === "person" || r.lane === "aside") {
        var t0 = r.lane === "person" ? 32.4 : 32.8;
        var L = lane(r.lane);
        token(r.lane === "person" ? "person" : "aside", r.lane === "person" ? "!" : "–", first(r.name),
          [at(R, t0), [L.cx, L.cy, t0 + 0.9]], r.lane);
      } else {
        var t1 = T.toDrafter(k);
        token("", "✎", first(r.name), [at(R, t1), at(Dr, t1 + 0.6, 0, -6)]);
        k += 1;
      }
    });

    token("", "✎", "draft 1", [at(Dr, T.send1[0] - 0.4, 0, 22), at(K, T.send1[0], 0, 30), at(Cr, T.send1[1], 0, 22)]);
    token("bad", "✕", "problems", [at(Cr, T.back[0], 0, 22), at(K, T.back[0] + 0.6, 0, 30), at(Dr, T.back[1], 0, 22)]);
    token("", "✎", "draft 2", [at(Dr, T.send2[0] - 0.4, 0, 22), at(K, T.send2[0], 0, 30), at(Cr, T.send2[1], 0, 22)]);

    drafted.forEach(function (r, j) {
      var t0 = T.toDesk(j), L = lane(r.lane);
      token("good", "✓", first(r.name), [at(Cr, t0, 0, 30), [L.cx, L.cy, t0 + 0.9]], r.lane);
    });

    token("good", "✓", "approved text", [at(card, T.toGate[0], 0, 10), [gate.x + 60, gate.y + 15, T.toGate[1]], [out.x + 60, out.y + 15, T.toOut[0]], [out.x + out.w - 40, out.y + 15, T.toOut[1]]]);
  }

  function placeToken(tok, t) {
    var p = tok.pts, n = p.length;
    var t0 = p[0][2], t1 = p[n - 1][2];
    if (t < t0 || t > t1 + 0.05) { setOpacity(tok.node, 0); return; }
    var x = p[0][0], y = p[0][1];
    for (var i = 0; i < n - 1; i++) {
      if (t >= p[i][2] && t <= p[i + 1][2]) {
        var s = p[i + 1][2] === p[i][2] ? 1 : ease(prog(t, p[i][2], p[i + 1][2]));
        x = lerp(p[i][0], p[i + 1][0], s); y = lerp(p[i][1], p[i + 1][1], s);
        break;
      }
      if (t > p[i + 1][2]) { x = p[i + 1][0]; y = p[i + 1][1]; }
    }
    var o = Math.min(prog(t, t0, t0 + 0.15), 1 - prog(t, t1 - 0.12, t1 + 0.05));
    setOpacity(tok.node, o);
    if (!tok.w) { tok.w = tok.node.offsetWidth; tok.h = tok.node.offsetHeight; }
    var w = tok.w, h = tok.h;
    setTransform(tok.node, "translate(" + (x - w / 2).toFixed(1) + "px," + (y - h / 2).toFixed(1) + "px)");
  }

  // ---------------------------------------------------------------- draft text
  function drawDraft(t) {
    var text = "", mark = false, caret = false, attempt = 1;
    if (t < T.type1[0]) text = "";
    else if (t < T.attempt2 + 0.4) {
      var n = Math.floor(draft1.length * prog(t, T.type1[0], T.type1[1]));
      text = draft1.slice(0, n);
      caret = t < T.type1[1] + 0.3;
      mark = t >= T.flag;
    } else {
      attempt = 2;
      var m = Math.floor(draft2.length * prog(t, T.type2[0], T.type2[1]));
      text = draft2.slice(0, m);
      caret = t >= T.type2[0] - 0.2 && t < T.type2[1] + 0.3;
    }
    var blink = Math.floor(t * 2.5) % 2 === 0;
    var key = text.length + "|" + mark + "|" + (caret && blink) + "|" + attempt;
    if (el.draftText._k === key) return;
    el.draftText._k = key;
    el.draftText.textContent = "";
    if (mark) {
      var at0 = text.indexOf(focus.flagged);
      el.draftText.appendChild(document.createTextNode(text.slice(0, at0)));
      var mk = document.createElement("mark");
      mk.textContent = focus.flagged;
      el.draftText.appendChild(mk);
      el.draftText.appendChild(document.createTextNode(text.slice(at0 + focus.flagged.length)));
    } else {
      el.draftText.appendChild(document.createTextNode(text));
    }
    if (caret && blink) {
      var c = document.createElement("span");
      c.className = "caret";
      el.draftText.appendChild(c);
    }
  }

  // ---------------------------------------------------------------- render
  var lastCaption = -1;
  function render(t) {
    var step = 0;
    for (var s = 0; s < STEP_AT.length; s++) if (t >= STEP_AT[s]) step = s;

    el.steps.forEach(function (li, i) {
      setClass(li, "now", i === step && t < END_AT);
      setClass(li, "done", i < step || t >= END_AT);
    });

    // caption
    if (step !== lastCaption) {
      lastCaption = step;
      setText(el.capNum, String(step + 1));
      el.capText.textContent = "";
      var em = document.createElement("em");
      em.textContent = CAPTIONS[step][0];
      el.capText.appendChild(em);
      el.capText.appendChild(document.createTextNode(CAPTIONS[step][1]));
    }
    var capStart = STEP_AT[step];
    setOpacity(el.capText, prog(t, capStart, capStart + 0.4) * 0.999 + 0.001);

    // 1. inbox rows
    var arrived = 0;
    rows.forEach(function (r, i) {
      var a = T.rowIn(i), p = ease(prog(t, a, a + 0.45));
      if (t >= a) arrived += 1;
      setOpacity(rowEl[r.key], p);
      setTransform(rowEl[r.key], "translateX(" + ((1 - p) * -24).toFixed(1) + "px)");
    });
    setText(el.inboxCount, arrived + " new");

    // 2. guard
    var guardBlocked = within(t, T.blockedAt, 14.5);
    setClass(el.guard, "blocked", guardBlocked);
    setClass(el.guard, "checking", within(t, 7.3, T.blockedAt));
    setText(el.guardState, t < 7.3 ? "watching" : t < T.blockedAt ? "checking" + dots(t) : guardBlocked ? "blocked: " + first(D.blocked.name) : "1 blocked · watching");

    // tags on inbox rows
    rows.forEach(function (r, i) {
      var show;
      if (r.blocked) show = T.blockedAt + 0.3;
      else show = T.routeIn(readRows.indexOf(r));
      setOpacity(tagEl[r.key], prog(t, show, show + 0.3));
    });

    // classifier
    var reached = rows.filter(function (r, i) { return !r.blocked && t >= T.mailOut(i) + 1.25; }).length;
    var read = readRows.filter(function (r, j) { return t >= T.readIn(j); }).length;
    var lastRead = T.readIn(readRows.length - 1);
    setClass(el.classifier, "busy", within(t, 8.2, lastRead + 1.2));
    setClass(el.classifier, "good", t >= lastRead + 1.2);
    setText(el.stC, t < 8.2 ? "idle" : t < 15.4 ? "receiving" + dots(t) : t < lastRead + 1.2 ? "reading " + read + " of " + readRows.length : "done · " + readRows.length + " read");
    setText(el.qC, String(Math.max(0, reached - read)));
    setOpacity(el.qC, within(t, 8.2, lastRead + 0.6) && reached - read > 0 ? 1 : 0);

    // routing
    var routing = within(t, 28.3, 35.5);
    setClass(el.routing, "on", routing);
    setClass(el.link1, "on", routing);

    // drafter
    var inDrafter = drafted.filter(function (r, k) { return t >= T.toDrafter(k) + 0.6; }).length;
    setClass(el.drafter, "busy", within(t, 33.8, T.send2[0]));
    setText(el.stD, t < 33.8 ? "idle" : t < 36.3 ? "receiving" + dots(t) : t < T.type1[1] ? "writing " + drafted.length + " replies" + dots(t) : t < T.attempt2 ? "handed over" : t < T.type2[1] ? "rewriting" + dots(t) : "done");
    setText(el.qD, String(inDrafter));
    setOpacity(el.qD, within(t, 33.8, 36.3) && inDrafter > 0 ? 1 : 0);

    // checks chip and second link
    var checking = within(t, T.ticks1[0] - 0.3, T.send1[1]) || within(t, T.ticks2[0] - 0.3, T.send2[1]);
    setClass(el.checks, "on", checking);
    setClass(el.link2, "on", checking);
    setClass(el.link2, "back", within(t, T.back[0], T.back[1]));
    [el.link1, el.link2].forEach(function (lk) {
      var wire = lk.firstElementChild;
      var dir = lk.classList.contains("back") ? -1 : 1;
      var on = lk.classList.contains("on") || lk.classList.contains("back");
      var pos = on ? (dir * t * 42).toFixed(1) + "px 0" : "0 0";
      if (wire._bp !== pos) { wire.style.backgroundPosition = pos; wire._bp = pos; }
    });

    // critic
    var reviewing = within(t, T.send1[1], T.rejected) || within(t, T.send2[1], T.accepted);
    setClass(el.critic, "busy", reviewing);
    setClass(el.critic, "bad", within(t, T.rejected, T.attempt2));
    setClass(el.critic, "good", t >= T.accepted);
    setText(el.stK, t < T.send1[1] ? "idle" : t < T.rejected ? "reviewing" + dots(t) : t < T.attempt2 ? "sent back" : t < T.send2[1] ? "waiting" : t < T.accepted ? "reviewing" + dots(t) : "accepted");

    // work area scenes
    setOpacity(el.idle, vis(t, 0, 9.0));
    setOpacity(el.blocked, vis(t, 9.3, 14.8));
    setOpacity(el.readout, vis(t, 15.2, 36.0));
    setOpacity(el.focus, vis(t, 36.3));
    readRows.forEach(function (r, j) {
      var a = T.readIn(j);
      setOpacity(roEl[r.key], prog(t, a, a + 0.3));
      setOpacity(rtEl[r.key], prog(t, T.routeIn(j), T.routeIn(j) + 0.3));
      setClass(rowEl[r.key], "pulse", within(t, a, a + 0.9));
    });
    var injAt = T.readIn(readRows.indexOf(injectedRow)) + 0.4;
    setOpacity(el.note, prog(t, injAt, injAt + 0.4));

    // draft card
    drawDraft(t);
    setText(el.attempt, "attempt " + (t >= T.attempt2 ? 2 : 1) + " of " + D.max_attempts);
    var ticks = t < T.attempt2 ? T.ticks1 : T.ticks2;
    checkEls.forEach(function (c, i) { setClass(c, "ok", t >= ticks[i]); });
    var verdict = within(t, T.rejected, T.attempt2) ? "bad" : t >= T.accepted ? "good" : "";
    setClass(el.verdict, "bad", verdict === "bad");
    setClass(el.verdict, "good", verdict === "good");
    setText(el.verdict, verdict === "bad" ? "Critic: sent back" : verdict === "good" ? "Critic: accepted" : "");
    setClass(el.draftCard, "bad", verdict === "bad");
    setClass(el.draftCard, "good", verdict === "good");
    setOpacity(el.bubCritic, prog(t, T.bubCritic, T.bubCritic + 0.4));
    setOpacity(el.bubDrafter, prog(t, T.bubDrafter, T.bubDrafter + 0.4));
    setOpacity(el.bubAccept, prog(t, T.bubAccept, T.bubAccept + 0.4));

    // tokens and lane counts
    var counts = {};
    tokens.forEach(function (tok) {
      placeToken(tok, t);
      if (tok.lane) {
        var end = tok.pts[tok.pts.length - 1][2];
        if (t >= end) counts[tok.lane] = (counts[tok.lane] || 0) + 1;
        var laneEl = laneCount[tok.lane] && laneCount[tok.lane].parentNode;
        if (laneEl && within(t, end, end + 0.7)) laneEl._hit = true;
      }
    });
    D.lanes.forEach(function (l) {
      var n = counts[l.key] || 0, lane = laneCount[l.key].parentNode;
      setText(laneCount[l.key], String(n));
      setClass(lane, "zero", n === 0);
      setClass(lane, "hit", !!lane._hit);
      lane._hit = false;
    });

    // 7. review
    setClass(el.reviewer, "on", within(t, T.card, T.press));
    setClass(el.reviewer, "done", t >= T.press);
    setText(el.reading, t < T.card ? "waiting" : t < T.press ? "reading" + dots(t) : "approved");
    var cardIn = ease(prog(t, T.card, T.card + 0.5));
    setOpacity(el.rcard, cardIn);
    setTransform(el.rcard, "translateY(" + ((1 - cardIn) * 12).toFixed(1) + "px)");
    setClass(el.reject, "hover", within(t, T.hoverReject[0], T.hoverReject[1]));
    setClass(el.approve, "hover", within(t, T.toApprove[1], T.press + 0.3));
    setClass(el.approve, "press", within(t, T.press, T.press + 0.25));
    setOpacity(el.tip, vis(t, T.hoverReject[0] + 0.2, T.hoverReject[1] - 0.2, 0.25));
    setOpacity(el.stamp, prog(t, T.stamp, T.stamp + 0.3));
    setOpacity(el.btns, 1 - prog(t, T.stamp, T.stamp + 0.3));
    setClass(el.gate, "on", within(t, T.toGate[0], T.toOut[1]));
    setText(el.gateText, t < T.toGate[1] ? "code · exact approved text only" : "exact match · " + focus.digest);
    setClass(el.out, "sent", t >= T.toOut[1]);
    setText(el.outText, t < T.toOut[1] ? "simulated · nothing sent yet" : "sent once to " + focus.email);
    setOpacity(el.audit, prog(t, T.audit(0) - 0.4, T.audit(0)));
    auditEls.forEach(function (a, k) { setOpacity(a, prog(t, T.audit(k), T.audit(k) + 0.3)); });

    // cursor: in, to Reject, hover, to Approve, press, out
    var cur = cursorAt(t);
    setOpacity(el.cursor, cur.o);
    setTransform(el.cursor, "translate(" + cur.x.toFixed(1) + "px," + cur.y.toFixed(1) + "px) scale(" + cur.s + ")");

    // end card
    var e = ease(prog(t, END_AT, END_AT + 0.8));
    setOpacity(el.endcard, e);
    setTransform(el.endcard, "scale(" + (0.98 + 0.02 * e).toFixed(4) + ")");

    updateControls(t);
  }

  var CUR = null;
  function measureCursor() {
    var a = box(el.approve), r = box(el.reject), c = box(el.rcard);
    CUR = {
      start: [c.x + c.w + 30, c.y + c.h + 120],
      reject: [r.cx - 6, r.cy - 4],
      approve: [a.cx - 6, a.cy - 4],
    };
  }
  function cursorAt(t) {
    var p = CUR.start;
    if (t >= T.toReject[0]) p = mix(CUR.start, CUR.reject, ease(prog(t, T.toReject[0], T.toReject[1])));
    if (t >= T.toApprove[0]) p = mix(CUR.reject, CUR.approve, ease(prog(t, T.toApprove[0], T.toApprove[1])));
    var o = Math.min(prog(t, T.cursorIn, T.cursorIn + 0.3), 1 - prog(t, 73.5, 73.9));
    var s = within(t, T.press, T.press + 0.25) ? 0.88 : 1;
    return { x: p[0], y: p[1], o: o, s: s };
  }
  function mix(a, b, x) { return [lerp(a[0], b[0], x), lerp(a[1], b[1], x)]; }

  // ---------------------------------------------------------------- scale
  function fit() {
    var s;
    if (RECORD) s = Math.min(window.innerWidth / W, window.innerHeight / H);
    else s = viewport.clientWidth / W;
    stage.style.transform = "scale(" + s + ")";
    viewport.style.height = (H * s).toFixed(2) + "px";
    if (RECORD) viewport.style.width = (W * s).toFixed(2) + "px";
  }

  // ---------------------------------------------------------------- playback
  var play = $("play"), restart = $("restart"), bar = $("bar"), progress = $("progress"), time = $("time");
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var t = 0, playing = false, last = null;

  function clock(x) {
    var m = Math.floor(x / 60), s = Math.floor(x % 60);
    return m + ":" + (s < 10 ? "0" : "") + s;
  }
  function updateControls(x) {
    if (!progress) return;
    progress.style.width = (100 * x / TOTAL).toFixed(2) + "%";
    setText(time, clock(x) + " / " + clock(TOTAL));
    var now = String(Math.round(x));
    if (bar._v !== now) { bar.setAttribute("aria-valuenow", now); bar._v = now; }
    setText(play, playing ? "Pause" : x >= TOTAL ? "Replay" : "Play");
  }
  function loop(now) {
    if (playing) {
      if (last !== null) t = Math.min(TOTAL, t + (now - last) / 1000);
      last = now;
      if (t >= TOTAL) playing = false;
      render(t);
    } else {
      last = null;
    }
    requestAnimationFrame(loop);
  }

  function start() {
    fit();
    buildTokens();
    measureCursor();
    if (RECORD) {
      window.__total = TOTAL;
      window.__seek = function (x) { t = x; playing = false; render(t); return true; };
      render(0);
      document.body.dataset.ready = "1";
      return;
    }
    if (reduce) { t = END_AT - 0.5; playing = false; } else { playing = true; }
    render(t);
    requestAnimationFrame(loop);
    play.addEventListener("click", function () {
      if (t >= TOTAL) t = 0;
      playing = !playing;
      render(t);
    });
    restart.addEventListener("click", function () { t = 0; playing = true; render(t); });
    bar.setAttribute("role", "slider");
    bar.setAttribute("tabindex", "0");
    bar.setAttribute("aria-label", "Position in the explainer");
    bar.setAttribute("aria-valuemin", "0");
    bar.setAttribute("aria-valuemax", String(TOTAL));
    bar.addEventListener("click", function (ev) {
      var r = bar.getBoundingClientRect();
      t = clamp((ev.clientX - r.left) / r.width) * TOTAL;
      render(t);
    });
    bar.addEventListener("keydown", function (ev) {
      if (ev.key === "ArrowRight") t = Math.min(TOTAL, t + 5);
      else if (ev.key === "ArrowLeft") t = Math.max(0, t - 5);
      else return;
      ev.preventDefault();
      render(t);
    });
    window.addEventListener("resize", function () { fit(); });
  }

  var fontsReady = document.fonts && document.fonts.ready ? document.fonts.ready : Promise.resolve();
  fontsReady.then(start, start);
})();
