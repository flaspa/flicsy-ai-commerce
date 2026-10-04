/* Flicsy Phase 1: a clickable, mock-data customer journey. No backend calls. */
import { AGENTS, STAGES, PRODUCTS, LOOKS, PRESS, CLIPS, NIGEL_NOTES, buildScript } from "./data.js";

const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const money = (n) => `$${n.toLocaleString("en-US")}`;
let P = PRODUCTS, L = LOOKS;  // live run data replaces these when the live desk succeeds
const lookTotal = (items) => items.reduce((t, k) => t + P[k].price, 0);
function useData() {
  const ev = state.run?.live && state.run.data?.evidence;
  if (ev && ev.final?.length) {
    P = Object.fromEntries(Object.entries(ev.products).map(([k, p]) => [k, { ...p, color: p.color || "", stock: p.stock || "Listed on everlane.com" }]));
    const notes = ev.notes || [];
    L = ev.final.map((l, i) => ({ id: ["I", "II", "III"][i], title: l.name, items: l.items, alt: l.alt, rationale: l.rationale || l.why,
      hero: (P[l.items.find((k) => (P[k].source || "").startsWith("Moss"))] || P[l.items[0]]).img,
      nigel: (notes[notes.length - 1] || "").replace(/^@\w+\s*/, "").slice(0, 160) }));
  } else { P = PRODUCTS; L = LOOKS; }
}

const DEMO_REQUEST = "I’m going to a gala dinner in San Francisco next month. I love skiing, I wear a lot of blue, and I’d like something elegant but not conventional.";
const DEFAULT_BRIEF = { occasion: "Gala dinner", city: "San Francisco", when: "Next month", palette: "Blue, always",
  style: "Elegant, not conventional", loves: "Skiing", dressCode: "Black tie", budget: "Up to $600",
  silhouette: "Open to either", dislikes: "No stilettos", photo: null };

const state = {
  brief: {}, step: 0, briefReady: false,
  run: null,   // { start, timers, stages: {id: {state, line}}, room: [], reveals: Set, bag: 'draft'|'revised', done }
  cart: {},    // lookId -> [productKeys]
};

/* ====================== Router ====================== */
const VIEWS = ["stylist", "desk", "curtain", "looks"];
function route() {
  const h = location.hash;
  const view = h.startsWith("#/") ? h.slice(2) : "";
  const inApp = VIEWS.includes(view);
  closeBag();  // never leave the bag's scrim covering a newly opened view
  $("#view-intro").hidden = inApp;
  $("#app-shell").hidden = !inApp;
  if (!inApp) { if (h === "#/" || h === "") window.scrollTo({ top: 0, behavior: "instant" }); return; }
  for (const v of VIEWS) $(`#view-${v}`).hidden = v !== view;
  $$(".app-nav a").forEach((a) => a.classList.toggle("on", a.dataset.nav === view));
  if (view === "curtain") renderRoom();
  if (view === "looks") renderLooks();
  window.scrollTo({ top: 0, behavior: "instant" });
}
window.addEventListener("hashchange", route);

/* ====================== Intro ====================== */
function renderIntro() {
  $("#today").textContent = new Date().toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long", year: "numeric" });
  $$(".year").forEach((y) => (y.textContent = new Date().getFullYear()));
  $("#intro-roles").innerHTML = ["miranda", "andy", "emily", "serena", "nigel"].map((k) => {
    const a = AGENTS[k];
    return `<div class="mp-role"><img src="${a.img}" alt="${a.name}"><b>${a.name}${k === "serena" ? '<span class="new">NEW</span>' : ""}</b>
      <small>${a.role}</small><p>${esc(a.line)}</p></div>`;
  }).join("");
}

/* ====================== Your Stylist ====================== */
const QUESTIONS = [
  { key: "dressCode", q: "Black tie, or cocktail?", chips: ["Black tie", "Black tie optional", "Cocktail"] },
  { key: "budget", q: "What's the budget for the complete look — shoes and accessories included?", chips: ["Under $400", "Up to $600", "Up to $800"] },
  { key: "silhouette", q: "Dress, suit, or open to either?", chips: ["Dress", "Suit", "Open to either"] },
  { key: "dislikes", q: "Anything you won't wear? And are heels okay?", chips: ["No stilettos", "Low heels are fine", "No sequins", "Nothing too tight"], multi: true },
];
const BRIEF_FIELDS = [
  ["occasion", "Occasion"], ["city", "Where"], ["when", "When"], ["dressCode", "Dress code"], ["budget", "Budget"],
  ["silhouette", "Silhouette"], ["palette", "Palette"], ["style", "Style"], ["loves", "Loves"], ["dislikes", "Avoid"], ["photo", "Photo"],
];

function renderBrief(fresh) {
  $("#brief-list").innerHTML = BRIEF_FIELDS.map(([k, label]) => {
    const v = k === "photo" ? (state.brief.photo ? "Added — styling context only" : "") : state.brief[k];
    return `<dt>${label}</dt><dd class="${v ? "" : "empty"} ${fresh === k ? "fresh" : ""}">${v ? esc(v) : "—"}</dd>`;
  }).join("");
  const st = $("#brief-state");
  st.textContent = state.briefReady ? "Ready for the desk" : "Drafting";
  st.classList.toggle("ready", state.briefReady);
  $("#consult-btn").disabled = !state.briefReady;
}

function addMsg(who, html, img) {
  const el = document.createElement("div");
  if (who === "miranda") {
    el.className = "msg miranda";
    el.innerHTML = `<img src="${AGENTS.miranda.img}" alt=""><div><div class="who">Miranda</div><div class="bubble">${html}</div></div>`;
  } else {
    el.className = "msg client";
    el.innerHTML = `<div class="who">You</div>${html}${img ? `<img src="${img}" alt="Your photo">` : ""}`;
  }
  $("#thread").append(el);
  $("#thread").scrollTop = $("#thread").scrollHeight;
}

function mirandaSays(html, then, delay = 900) {
  const t = document.createElement("div");
  t.className = "msg miranda";
  t.innerHTML = `<img src="${AGENTS.miranda.img}" alt=""><div class="typing"><i></i><i></i><i></i></div>`;
  $("#thread").append(t);
  $("#thread").scrollTop = $("#thread").scrollHeight;
  setTimeout(() => { t.remove(); addMsg("miranda", html); then && then(); }, delay);
}

function setChips(list, onPick, multi) {
  const box = $("#chips");
  const picked = new Set();
  box.innerHTML = list.map((c) => `<button type="button" class="chip">${esc(c)}</button>`).join("") +
    (multi ? `<button type="button" class="chip done">That's all →</button>` : "");
  $$(".chip", box).forEach((b) => b.addEventListener("click", () => {
    if (b.classList.contains("done")) return onPick([...picked].join(", ") || "Nothing in particular");
    if (!multi) return onPick(b.textContent);
    b.classList.toggle("on");
    b.classList.contains("on") ? picked.add(b.textContent) : picked.delete(b.textContent);
  }));
}

function askNext() {
  const q = QUESTIONS[state.step];
  if (!q) return finishBrief();
  mirandaSays(esc(q.q), () => setChips(q.chips, answer, q.multi));
}

function answer(text) {
  const q = QUESTIONS[state.step];
  $("#chips").innerHTML = "";
  addMsg("client", esc(text));
  state.brief[q.key] = text;
  renderBrief(q.key);
  state.step += 1;
  askNext();
}

function finishBrief() {
  state.briefReady = true;
  renderBrief();
  mirandaSays("That's everything I need. Add a recent photo if you'd like me to consider it — otherwise, <em>let me consult the fashion desk.</em>", () => {
    $("#chips").innerHTML = `<button type="button" class="chip done" id="chip-consult">Consult the Fashion Desk →</button>`;
    $("#chip-consult").addEventListener("click", consult);
  }, 1100);
}

function parseRequest(text) {
  const t = text.toLowerCase();
  const b = state.brief;
  b.occasion = /gala/.test(t) ? "Gala dinner" : /wedding/.test(t) ? "Wedding" : /dinner/.test(t) ? "Dinner" : "Evening event";
  const city = text.match(/\bin ([A-Z][a-zA-Z]+(?: [A-Z][a-zA-Z]+)*)/);
  b.city = city ? city[1] : "—";
  b.when = /next month/.test(t) ? "Next month" : /next week/.test(t) ? "Next week" : "Soon";
  if (/blue/.test(t)) b.palette = "Blue, always";
  if (/elegant/.test(t) || /conventional/.test(t)) b.style = "Elegant, not conventional";
  if (/ski/.test(t)) b.loves = "Skiing";
}

function onSend(e) {
  e && e.preventDefault();
  const box = $("#compose");
  const text = box.value.trim();
  if (!text) return;
  box.value = "";
  if (state.step === 0 && !state.brief.occasion) {
    addMsg("client", esc(text));
    parseRequest(text);
    renderBrief("occasion");
    mirandaSays(`A ${esc(state.brief.occasion.toLowerCase())} in ${esc(state.brief.city)}, for someone who skis and lives in blue. <em>Elegant but not conventional</em> — good. That's the only interesting brief. Four quick questions.`,
      askNext, 1300);
  } else if (QUESTIONS[state.step]) {
    answer(text);
  } else {
    addMsg("client", esc(text));
    state.brief.notes = text;
    mirandaSays("Noted — I'll pass that to the desk.");
  }
}

function initStylist() {
  addMsg("miranda", "Good evening. Where are you going — and how do you want to feel when you walk in?");
  $("#compose").value = DEMO_REQUEST;
  $("#compose-form").addEventListener("submit", onSend);
  $("#compose").addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) onSend(e); });
  $("#consult-btn").addEventListener("click", consult);
  $("#photo-input").addEventListener("change", (e) => {
    const f = e.target.files[0];
    if (!f) return;
    const r = new FileReader();
    r.onload = () => {
      state.brief.photo = r.result;
      $("#photo-preview").style.backgroundImage = `url(${r.result})`;
      $("#photo-preview").textContent = " ";
      addMsg("client", "Here's a recent photo.", r.result);
      renderBrief("photo");
      mirandaSays("Thank you. I'll keep your colouring and proportions in mind — it stays between us.");
    };
    r.readAsDataURL(f);
  });
  renderBrief();
}

function consult() {
  startLive({ ...DEFAULT_BRIEF, ...state.brief });
  location.hash = "#/desk";
}

/* ====================== Live run: real ZooWork agents coordinating in a real Band room ====================== */
const LIVE_TIMEOUT_MS = 150000;
async function startLive(brief) {
  if (state.run) { state.run.timers.forEach(clearTimeout); clearInterval(state.run.poll); }
  const { photo, ...briefNoPhoto } = brief;
  const run = { brief, start: Date.now(), timers: [], stages: {}, room: [], reveals: new Set(), bag: null, done: false, live: { id: null, room: null } };
  STAGES.forEach((s) => (run.stages[s.id] = { state: "waiting", line: "Waiting" }));
  state.run = run;
  $("#skip-btn").hidden = false;
  $("#play-btn").textContent = "Replay run";
  refresh();
  const fallback = (why) => {
    console.error("Live desk unavailable, switching to rehearsal run:", why);
    clearInterval(run.poll);
    if (state.run !== run) return;
    toast("Live desk unavailable — showing the rehearsal run.");
    startRun(brief);
  };
  try {
    const r = await fetch("/api/live/runs", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(briefNoPhoto) });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    run.live.id = (await r.json()).run_id;
  } catch (e) { return fallback(e); }
  let misses = 0;
  run.poll = setInterval(async () => {
    if (state.run !== run) return clearInterval(run.poll);
    if (Date.now() - run.start > LIVE_TIMEOUT_MS) return fallback("timeout");
    try {
      const r = await fetch(`/api/live/runs/${run.live.id}`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      applyLive(run, await r.json());
      misses = 0;
    } catch (e) { if (e.fatal || ++misses >= 3) fallback(e); }
  }, 1000);
}

function applyLive(run, d) {
  if (d.status === "error") throw Object.assign(new Error(d.error), { fatal: true });
  run.live.room = d.room_id;
  for (const s of STAGES) {
    const st = d.stages[s.id];
    if (st) run.stages[s.id] = { state: st, line: d.lines[s.id] || run.stages[s.id].line };
  }
  const done = (id) => d.stages[id] === "done";
  const before = new Set(run.reveals);
  if (done("andy")) run.reveals.add("press");
  if (done("emily")) run.reveals.add("clips");
  if (d.events.some((e) => e.from === "serena")) run.bag = "draft";
  if (d.events.some((e) => e.kind === "revision")) run.bag = "revised";
  if (done("nigel")) run.reveals.add("notes");
  if (done("final")) run.reveals.add("verdict");
  run.data = d;
  const tools = (d.tools || []).map((t) => ({ kind: "tool", from: t.from, tool: t.tool, args: t.args, result: t.result, ts: t.at }));
  run.room = [...tools, ...d.events.map((e) => {
    const to = (e.text.match(/^@(\w+)/) || [])[1];
    const kind = { reject: "reject", approve: "approve", revision: "revision" }[e.kind] || "";
    return { from: e.from, text: e.text, kind, ts: e.at, mentions: to ? [to] : [], handoff: !!to && !kind && e.from !== "client" };
  })].sort((a, b) => new Date(a.ts) - new Date(b.ts));
  if (d.status === "done") { run.done = true; clearInterval(run.poll); $("#skip-btn").hidden = true; }
  refresh([...run.reveals].find((x) => !before.has(x)));
}

function refresh(fresh) {
  renderDesk(fresh);
  if (!$("#view-curtain").hidden) renderRoom();
}

/* ====================== Run engine (drives Desk + Curtain) ====================== */
function startRun(brief) {
  if (state.run) { state.run.timers.forEach(clearTimeout); clearInterval(state.run.poll); }
  const run = { brief, start: Date.now(), timers: [], stages: {}, room: [], reveals: new Set(), bag: null, done: false };
  STAGES.forEach((s) => (run.stages[s.id] = { state: "waiting", line: "Waiting" }));
  state.run = run;
  const script = buildScript(brief);
  run.script = script;
  script.forEach((ev, i) => run.timers.push(setTimeout(() => apply(ev, i), ev.at)));
  renderDesk();
  renderRoom();
  $("#skip-btn").hidden = false;
  $("#play-btn").textContent = "Replay run";
}

function apply(ev, i) {
  const run = state.run;
  if (!run || run.applied?.has(i)) return;
  (run.applied ||= new Set()).add(i);
  if (ev.stage) {
    const s = run.stages[ev.stage];
    if (ev.state) s.state = ev.state;
    if (ev.line) s.line = ev.line;
  }
  if (ev.room) run.room.push({ ...ev.room, at: ev.at });
  if (ev.bag) run.bag = ev.bag;
  if (ev.reveal) run.reveals.add(ev.reveal);
  if (ev.end) { run.done = true; $("#skip-btn").hidden = true; }
  renderDesk(ev.reveal);
  if (!$("#view-curtain").hidden) renderRoom();
}

function skipRun() {
  if (state.run?.live) startRun(state.run.brief);  // leave the live room; jump to the rehearsal result
  const run = state.run;
  if (!run) return;
  run.timers.forEach(clearTimeout);
  run.script.forEach((ev, i) => apply(ev, i));
}

/* ====================== The Fashion Desk ====================== */
function renderDesk(fresh) {
  const run = state.run;
  const b = run?.brief;
  $("#run-brief").innerHTML = b
    ? `<b>${esc(b.occasion)} · ${esc(b.city)}</b> · ${esc(b.dressCode)} · ${esc(b.budget)} · ${esc(b.silhouette)} · ${esc(b.palette)} · ${esc(b.dislikes)}`
    : `No brief yet — start with <a class="link" href="#/stylist">Your Stylist</a>, or play the demo run.`;

  $("#stages").innerHTML = STAGES.map((s) => {
    const a = AGENTS[s.agent];
    const st = run ? run.stages[s.id] : { state: "waiting", line: "Waiting" };
    const pill = { waiting: "Waiting", working: "Working", done: "Complete", blocked: "Change requested" }[st.state];
    const q = s.id === "final" ? "Which looks do we present?" : a.question;
    return `<div class="stage ${st.state}">
      <div class="portrait"><img src="${a.img}" alt="${a.name}"></div>
      <div class="card"><h3>${s.title}</h3><div class="role">${s.sub}</div><p class="q">“${esc(q)}”</p>
        <div class="status"><span class="pill">${pill}</span><span class="line">${esc(st.line)}</span></div></div></div>`;
  }).join("");

  const open = new Set($$("#drawers details[open]").map((d) => d.dataset.id));
  const R = run ? run.reveals : new Set();
  const drawer = (id, title, meta, ready, body, waitingFor) =>
    `<details class="drawer ${ready ? "ready" : ""} ${fresh === id ? "fresh" : ""}" data-id="${id}" ${open.has(id) || fresh === id ? "open" : ""}>
      <summary><span class="d-title">${title}</span><span class="d-meta">${meta}</span><span class="d-state">${ready ? "Ready" : "Waiting for " + waitingFor}</span></summary>
      <div class="d-body">${ready ? body : `<p class="locked">${waitingFor} hasn't reported yet.</p>`}</div></details>`;

  const bagReady = run && run.bag;
  const ev = run?.live && run.data?.evidence;
  $("#drawers").innerHTML =
    drawer("press", "Andy's Press Desk", ev?.press ? `${ev.press.sources.length} real sources · Tavily · ${ev.press.status}` : "5 publications · dynamically selected per brief", R.has("press"), ev?.press ? livePress(ev.press) : pressBody(), "Andy") +
    drawer("clips", "Emily's Clipping Book", ev?.clips ? `${ev.clips.matched} of ${ev.clips.searched} real TikTok clips · Bright Data · ${ev.clips.status}` : CLIPS.stats, R.has("clips"), ev?.clips ? liveClips(ev.clips) : clipsBody(), "Emily") +
    drawer("bag", "Serena's Shopping Bag", ev?.looks?.length ? `Real products · Moss ${ev.moss?.[0]?.status || ""} + Everlane catalog` : "Everlane catalog · 1,500 products indexed", bagReady, ev?.looks?.length ? liveBag(ev) : bagReady ? bagBody(run.bag) : "", "Serena") +
    drawer("notes", "Nigel's Notes", "Occasion · budget · fit · evidence", R.has("notes"), ev?.notes?.length ? liveNotes(ev) : notesBody(), "Nigel") +
    (R.has("verdict") ? verdictCard() : "");
}

function livePress(p) {
  return `<p class="d-note">${p.status === "LIVE" ? "Live Tavily search" : "FALLBACK — Tavily unavailable"} · query: “${esc(p.query)}”</p><div class="press-grid"><div>${p.sources.map((s) =>
    `<div class="src"><b>${esc(s.publication)}</b><span><a class="link" href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.title)}</a>${s.insight ? `<br><small style="color:var(--muted);letter-spacing:0;text-transform:none;font-weight:400">${esc(s.insight)}</small>` : ""}</span><small>Read</small></div>`).join("")}</div>
    <div><span class="label">Andy's direction</span><div class="signal"><i>Editorial</i>${esc(p.direction || "")}</div></div></div>`;
}

function liveClips(c) {
  if (!c.clips.length) return `<p class="d-note">No relevant clips in the clipping book (${c.status}).</p>`;
  return `<p class="d-note">${c.status === "CLIPBOOK" ? "Real TikTok posts collected by Mira Picks via Bright Data" : "FALLBACK"} · matched on: ${esc((c.terms || []).join(", "))}</p>
    <div class="tags">${[...new Set(c.clips.map((x) => x.trend).filter(Boolean))].map((t) => `<span class="tag">${esc(t)}</span>`).join("")}</div>
    <div class="clip-grid">${c.clips.slice(0, 4).map((x, i) => `<a class="clip" href="${esc(x.url)}" target="_blank" rel="noopener" style="background:linear-gradient(160deg, ${["#2a3550", "#8fb3ff", "#2f5cc4", "#1b1f2a"][i]}, #111)">
      <p>${esc(x.text)}</p><small>@${esc(x.creator || "")} · ${esc(x.date)} · ${x.tags.map((t) => "#" + esc(t)).join(" ")}</small><b>▶ ${(x.plays || 0).toLocaleString("en-US")} plays</b></a>`).join("")}</div>
    <p class="d-note">${esc(c.say || "")}</p>`;
}

function liveBag(ev) {
  const P2 = ev.products;
  return `<div class="bag-looks">${ev.looks.map((l, i) => {
    const draft = ev.draft[i] || l;
    const removed = draft.items.filter((k) => !l.items.includes(k));
    const rows = [...removed.map((k) => [k, "struck"]), ...l.items.map((k) => [k, draft.items.includes(k) ? "" : "swapped"])];
    return `<div class="bag-look"><h4>${esc(l.name)}<span>${money(l.total)}</span></h4>${rows.map(([k, cls]) => {
      const p = P2[k];
      return `<div class="mini ${cls}"><img src="${esc(p.img)}" alt=""><div><a href="${esc(p.url)}" target="_blank" rel="noopener">${esc(p.name)}</a><small>${esc(p.source || p.retailer)}${p.color ? " · " + esc(p.color) : ""}</small></div><b>${money(p.price)}</b></div>`;
    }).join("")}</div>`;
  }).join("")}</div>`;
}

function liveNotes(ev) {
  return `<div class="notes-grid"><div><span class="label">Nigel, live</span>${ev.notes.map((n, i) =>
    `<div class="nigel-q ${i === 0 ? "reject" : ""}"><i>${i === 0 ? "First review · change requested" : "After Serena's revision"}</i>“${esc(n.replace(/@\[\[[^\]]+\]\]\s*/g, ""))}”</div>`).join("")}</div>
    <div><span class="label">Revision</span>${ev.revision ? `<div class="nigel-q"><i>${esc(ev.revision.replaces)}</i>${esc(ev.revision.changed)}</div>` : `<p class="locked">No revision.</p>`}</div></div>`;
}

function pressBody() {
  return `<p class="d-note">${PRESS.note} · query: “${esc(PRESS.query)}”</p><div class="press-grid"><div>${PRESS.sources.map((s) =>
    `<div class="src ${s.status}"><b>${s.name}</b><span>${esc(s.headline)}</span><small>${s.status === "read" ? "Read" : "Paywalled"}</small></div>`).join("")}</div>
    <div><span class="label">Press signals</span>${PRESS.signals.map((s) => `<div class="signal"><i>${s.strength}</i>${esc(s.signal)}</div>`).join("")}</div></div>`;
}

function clipsBody() {
  return `<p class="d-note">${CLIPS.note}</p><div class="tags">${CLIPS.aesthetics.map((a) => `<span class="tag">${a}</span>`).join("")}</div>
    <div class="clip-grid">${CLIPS.clips.map((c) => `<div class="clip" style="background:linear-gradient(160deg, ${c.tone}, #111)">
      <p>${esc(c.text)}</p><small>${c.tags.map((t) => "#" + t).join(" ")}</small><b>▶ ${c.plays} plays</b></div>`).join("")}</div>`;
}

function bagBody(version) {
  return `<div class="bag-looks">${LOOKS.map((l) => {
    let rows = l.items.map((k) => [k, ""]);
    let total = lookTotal(l.items);
    if (l.revised) {
      if (version === "draft") { rows = rows.map(([k]) => [k === l.revised.to ? l.revised.from : k, ""]); total = total - PRODUCTS[l.revised.to].price + PRODUCTS[l.revised.from].price; }
      else rows = rows.flatMap(([k]) => (k === l.revised.to ? [[l.revised.from, "struck"], [k, "swapped"]] : [[k, ""]]));
    }
    return `<div class="bag-look"><h4>Look ${l.id}<span class="${total > 600 ? "over" : ""}">${money(total)}</span></h4>${rows.map(([k, cls]) => {
      const p = PRODUCTS[k];
      return `<div class="mini ${cls}"><img src="${p.img}" alt=""><div>${esc(p.name)}<small>${p.retailer} · ${esc(p.color)}</small></div><b>${money(p.price)}</b></div>`;
    }).join("")}</div>`;
  }).join("")}</div>`;
}

function notesBody() {
  return `<div class="notes-grid"><div><span class="label">Checks</span>${NIGEL_NOTES.checks.map(([k, v, s]) =>
    `<div class="check"><b>${k}</b><span>${esc(v)}</span><span class="${s}">${s === "ok" ? "✓" : "!"}</span></div>`).join("")}</div>
    <div><span class="label">On each look</span>
      <div class="nigel-q reject"><i>Rejected · Look II</i>“${esc(NIGEL_NOTES.rejection.reason)}”</div>
      ${LOOKS.map((l) => `<div class="nigel-q"><i>Look ${l.id} · ${esc(l.title)}</i>“${esc(l.nigel)}”</div>`).join("")}</div></div>`;
}

function verdictCard() {
  return `<div class="verdict-card"><img src="${AGENTS.miranda.img}" alt="Miranda"><div><span class="label">Miranda — Final edit</span>
    <blockquote>“Present I and II as the edit, III as the alternative direction.”</blockquote></div>
    <a class="cta" href="#/looks">See your looks →</a></div>`;
}

/* ====================== Behind the Curtain ====================== */
function renderRoom() {
  const run = state.run;
  const seatState = (k) => {
    if (!run) return "";
    const ids = STAGES.filter((s) => s.agent === k).map((s) => run.stages[s.id].state);
    return ids.find((x) => x === "working" || x === "blocked") || (ids.every((x) => x === "done") ? "done" : ids.includes("done") ? "done" : "");
  };
  $("#seats").innerHTML = Object.entries(AGENTS).map(([k, a]) =>
    `<li class="seat"><img src="${a.img}" alt=""><div><code>${a.handle}</code><small>${a.role}${a.tool ? " · " + a.tool : ""}</small></div><span class="st ${seatState(k)}"></span></li>`).join("");
  const live = $("#room-live");
  live.textContent = !run ? "idle" : run.live ? (run.done ? "LIVE · BAND · complete" : "LIVE · BAND") : run.done ? "rehearsal · complete" : "rehearsal";
  live.classList.toggle("on", !!run && !run.done);
  if (!run) return;
  const b = run.brief;
  $("#room-name").textContent = run.live?.room ? `Room: ${run.live.room}`
    : `#flicsy-${b.occasion.toLowerCase().replace(/\W+/g, "-")}-${b.city.toLowerCase().replace(/\W+/g, "-")}`.replace(/-+/g, "-");
  $(".room-meta").innerHTML = run.live ? "Real Band room · 5 ZooWork agents<br>Every handoff is a Band @mention" : "Rehearsal room · scripted fallback";
  const fmtAt = (at) => new Date(run.start + at).toLocaleTimeString("en-GB");
  const fmt = (at, ts) => (ts ? new Date(ts).toLocaleTimeString("en-GB") : fmtAt(at));
  const mention = (t) => esc(t).replace(/@(\w+)/g, '<span class="m">@$1</span>');
  $("#feed").innerHTML = run.room.map((m) => {
    if (m.kind === "system") return `<li class="ev system"><time>${fmt(m.at, m.ts)}</time><div class="txt">— ${esc(m.text)} —</div></li>`;
    const a = AGENTS[m.from] || { name: "Client brief", img: "", handle: "@client" };
    const avatar = a.img ? `<img src="${a.img}" alt="">` : `<span></span>`;
    let body;
    if (m.kind === "tool") body = `<div class="toolcall"><b>${esc(m.tool)}</b>(${esc(m.args)})<span class="res">→ ${esc(m.result)}</span></div>`;
    else if (m.kind === "reject") body = `<div class="txt"><div class="tagx">REQUEST CHANGE</div>${mention(m.text)}</div>`;
    else if (m.kind === "approve") body = `<div class="txt"><div class="tagx">FINAL APPROVAL</div>${mention(m.text)}</div>`;
    else if (m.kind === "revision") body = `<div class="txt"><div class="tagx">REVISION</div>${mention(m.text)}</div><span class="handoff">↳ handoff → @nigel</span>`;
    else body = `<div class="txt">${mention(m.text)}</div>${m.handoff ? `<span class="handoff">↳ handoff → @${esc(m.mentions[0])}</span>` : ""}`;
    return `<li class="ev ${m.kind || ""}"><time>${fmt(m.at, m.ts)}</time>${avatar}<div><div class="who">${a.name}<code>${a.handle}</code></div>${body}</div></li>`;
  }).join("");
  const feed = $("#feed");
  feed.scrollTop = feed.scrollHeight;
}

/* ====================== Your Looks + bag ====================== */
function renderLooks() {
  const b = state.run?.brief || { ...DEFAULT_BRIEF, ...state.brief };
  $("#looks-title").textContent = `For your ${b.occasion === "Gala dinner" ? "gala" : (b.occasion || "evening").toLowerCase()}, Miranda selected these looks.`;
  useData();
  $("#looks").innerHTML = L.map((l) => {
    const added = !!state.cart[l.id];
    return `<article class="look" data-look="${l.id}">
      <div class="look-img"><img src="${l.hero}" alt="${esc(l.title)}"><span class="num">${l.id}</span>${l.alt ? '<span class="alt">Alternative direction</span>' : ""}</div>
      <div class="look-copy">
        <div class="kicker"><span class="dot"></span>Look ${l.id}${l.alt ? " · The bold one" : ""}</div>
        <h2>${esc(l.title)}</h2>
        <p class="rationale">“${esc(l.rationale)}”</p>
        <div class="rationale-by"><img src="${AGENTS.miranda.img}" alt="">Miranda, Lead Stylist</div>
        <div class="items">${l.items.map((k) => {
          const p = P[k];
          return `<div class="item"><img src="${p.img}" alt="${esc(p.name)}"><div><div class="ret">${p.retailer}</div>
            <div class="nm"><a href="${p.url}" target="_blank" rel="noopener">${esc(p.name)}</a></div>
            <div class="av ${p.low ? "low" : ""}">${esc(p.color)} · ${esc(p.stock)}</div></div>
            <div class="pr">${money(p.price)}${p.was ? `<s>${money(p.was)}</s>` : ""}</div></div>`;
        }).join("")}</div>
        <div class="total"><span>Complete look</span><b>${money(lookTotal(l.items))}</b></div>
        <div class="nigel-line"><img src="${AGENTS.nigel.img}" alt="">Nigel: “${esc(l.nigel)}”</div>
        <div class="look-actions">
          <button class="cta add ${added ? "added" : ""}" type="button">${added ? "Added to bag ✓" : "Add Look to Cart"}</button>
          <button class="btn-line refine-btn" type="button">Refine This Look</button>
        </div>
        <div class="refine-slot"></div>
      </div></article>`;
  }).join("");
  $$(".look").forEach((el) => {
    const id = el.dataset.look;
    $(".add", el).addEventListener("click", () => addLook(id));
    $(".refine-btn", el).addEventListener("click", () => openRefine(el, id));
  });
}

function openRefine(el, id) {
  const slot = $(".refine-slot", el);
  if (slot.innerHTML) { slot.innerHTML = ""; return; }
  slot.innerHTML = `<div class="refine"><p>What should Miranda change about Look ${id}?</p>
    <div class="chips">${["Swap the shoes", "Warmer for the evening", "Less blue", "Lower the budget"].map((c) => `<button type="button" class="chip">${c}</button>`).join("")}</div>
    <form class="compose-row"><input placeholder="Or tell her in your own words…"><button class="btn-ink" type="submit">Send to Miranda</button></form></div>`;
  const send = (text) => {
    if (!text) return;
    slot.innerHTML = "";
    if (state.run) { state.run.room.push({ from: "client", text: `@miranda Look ${id}: ${text}`, at: Date.now() - state.run.start }); }
    toast(`Miranda has your note on Look ${id}: “${text}”. Live refinement connects in Phase 2.`);
  };
  $$(".chip", slot).forEach((c) => c.addEventListener("click", () => send(c.textContent)));
  $("form", slot).addEventListener("submit", (e) => { e.preventDefault(); send($("input", slot).value.trim()); });
}

function addLook(id) {
  const look = L.find((l) => l.id === id);
  if (state.cart[id]) { openBag(); return; }
  state.cart[id] = { title: look.title, items: look.items.map((k) => P[k]) };
  renderBag();
  renderLooks();
  const btn = $("#bag-btn");
  btn.classList.remove("bump"); void btn.offsetWidth; btn.classList.add("bump");
  toast(`Look ${id} · ${look.title} added to your bag — ${money(lookTotal(look.items))}`);
}

function renderBag() {
  const ids = Object.keys(state.cart);
  const count = ids.reduce((n, id) => n + state.cart[id].items.length, 0);
  $("#bag-count").textContent = count;
  let total = 0;
  $("#bag-items").innerHTML = ids.length ? ids.map((id) => {
    const look = state.cart[id];
    const sub = look.items.reduce((t, p) => t + p.price, 0);
    total += sub;
    return `<li class="grp"><span>Look ${id} · ${esc(look.title)}</span><button class="link" data-remove="${id}" type="button">Remove</button></li>` +
      state.cart[id].items.map((p) => { return `<li class="mini"><img src="${p.img}" alt=""><div>${esc(p.name)}<small>${p.retailer}${p.color ? " · " + esc(p.color) : ""}</small></div><b>${money(p.price)}</b></li>`; }).join("");
  }).join("") : `<li class="empty">Your bag is empty. Miranda's looks are waiting.</li>`;
  $("#bag-total").textContent = money(total);
  $$("[data-remove]").forEach((b) => b.addEventListener("click", () => { delete state.cart[b.dataset.remove]; renderBag(); if (!$("#view-looks").hidden) renderLooks(); }));
}

const openBag = () => { $("#bag").hidden = false; $("#scrim").hidden = false; };
const closeBag = () => { $("#bag").hidden = true; $("#scrim").hidden = true; };

let toastTimer;
function toast(text) {
  const t = $("#toast");
  t.textContent = text;
  t.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (t.hidden = true), 3800);
}

/* ====================== Boot ====================== */
renderIntro();
initStylist();
renderDesk();
renderBag();
$("#play-btn").addEventListener("click", () => startRun({ ...DEFAULT_BRIEF, ...state.brief }));
$("#skip-btn").addEventListener("click", skipRun);
$("#curtain-play").addEventListener("click", () => startRun({ ...DEFAULT_BRIEF, ...state.brief }));
$("#bag-btn").addEventListener("click", openBag);
$("#bag-close").addEventListener("click", closeBag);
$("#scrim").addEventListener("click", closeBag);
$("#checkout-btn").addEventListener("click", async () => {
  if (!Object.keys(state.cart).length) return toast("Add a look first.");
  const btn = $("#checkout-btn");
  const items = Object.values(state.cart).flatMap((l) => l.items.map((p) => ({ url: p.url, name: p.name })));
  btn.disabled = true;
  try {
    const r = await fetch("/api/checkout", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ items }) });
    const d = await r.json();
    if (!r.ok || !d.url) throw new Error(d.detail || `HTTP ${r.status}`);
    sessionStorage.setItem("flicsy-cart", JSON.stringify(state.cart));  // restore the bag if the customer cancels
    location.href = d.url;  // Stripe-hosted test checkout
  } catch (e) {
    console.error("Checkout failed:", e);
    toast(`Checkout unavailable: ${e.message}. Your bag is saved — nothing was charged.`);
    btn.disabled = false;
  }
});

/* Returning from Stripe test checkout */
(() => {
  const q = new URLSearchParams(location.search).get("checkout");
  if (!q) return;
  const saved = sessionStorage.getItem("flicsy-cart");
  history.replaceState(null, "", "/#/looks");
  route();
  if (q === "success") {
    sessionStorage.removeItem("flicsy-cart");
    $("#bag-items").innerHTML = `<li class="empty" style="font-style:normal"><span class="label" style="color:var(--done)">Payment complete · Stripe test mode</span><br><br>This was a test transaction. No retailer order was placed.</li>`;
    $("#bag-total").textContent = "$0";
    setTimeout(openBag, 0);  // after the boot route() below, which closes the bag
  } else if (saved) {
    state.cart = JSON.parse(saved);
    renderBag();
    setTimeout(openBag, 0);
    toast("Checkout cancelled — your bag is just as you left it.");
  }
})();
route();
