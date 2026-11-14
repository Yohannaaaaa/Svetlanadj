/* SVETLANA AI DJ STUDIO – interface (JavaScript natif, sans dépendance) */
(() => {
  "use strict";
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const S = { state: null, project: null, pollTimer: null, saveTimer: null };

  // ------------------------------------------------------------- API helpers
  async function api(method, url, body) {
    const opts = { method, headers: { "X-Studio": "1" } };
    if (body instanceof FormData) opts.body = body;
    else if (body !== undefined) { opts.body = JSON.stringify(body); opts.headers["Content-Type"] = "application/json"; }
    const r = await fetch(url, opts);
    if (r.status === 401) { location.href = "/login"; throw new Error("auth"); }
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(data.error || `Erreur ${r.status}`);
    return data;
  }
  function toast(msg, ms = 3500) {
    const t = $("#toast"); t.textContent = msg; t.classList.add("show");
    clearTimeout(t._h); t._h = setTimeout(() => t.classList.remove("show"), ms);
  }
  const fail = (e) => { if (e.message !== "auth") toast("⚠ " + e.message, 7000); };
  const money = (v) => `${(v || 0).toFixed(2)} $`;
  const el = (tag, attrs = {}, text) => { const e = document.createElement(tag); Object.assign(e, attrs); if (text !== undefined) e.textContent = text; return e; };
  function fillSelect(sel, entries, value) {
    sel.innerHTML = "";
    for (const [k, label] of entries) sel.append(el("option", { value: k }, label));
    if (value !== undefined && value !== null) sel.value = value;
  }

  // -------------------------------------------------------------- navigation
  function show(view) {
    $$(".view").forEach((v) => v.classList.toggle("active", v.id === "view-" + view));
    $$(".tab").forEach((t) => t.classList.toggle("active", t.dataset.view === view || (view === "editor" && t.dataset.view === "projects")));
    if (view !== "editor") stopPolling();
    window.scrollTo({ top: 0 });
  }
  $$(".tab").forEach((t) => t.addEventListener("click", () => { show(t.dataset.view); if (t.dataset.view === "projects") loadState(); }));

  // ------------------------------------------------------------ global state
  async function loadState() {
    S.state = await api("GET", "/api/state");
    renderWarnings(); renderIdentity(); renderProjects(); renderSettings();
  }
  function renderWarnings() {
    const w = $("#warnings"); w.innerHTML = "";
    for (const msg of S.state.warnings) w.append(el("div", { className: "warning" }, "⚠ " + msg));
  }

  // ---------------------------------------------------------------- identity
  function renderIdentity() {
    const id = S.state.identity;
    $("#id-name").value = id.name || "";
    $("#id-desc").value = id.description || "";
    const drop = $("#ref-drop");
    if (id.reference_image) { $("#ref-preview").src = "/media/identity/" + id.reference_image; drop.classList.add("has"); }
    const list = $("#extra-list"); list.innerHTML = "";
    for (const n of id.extra_references || []) {
      const d = el("div", { className: "thumb" });
      d.append(el("img", { src: "/media/identity/" + n }));
      const b = el("button", { title: "Retirer" }, "✕");
      b.onclick = () => postIdentity({ remove_extra: n });
      d.append(b); list.append(d);
    }
    $("#logo-preview").src = "/media/identity/" + (id.logo || "logo_default.png") + "?t=" + Date.now();
  }
  async function postIdentity(fields, files = {}) {
    const fd = new FormData();
    for (const [k, v] of Object.entries(fields)) fd.append(k, v);
    for (const [k, v] of Object.entries(files)) [].concat(v).forEach((f) => fd.append(k, f));
    try { const r = await api("POST", "/api/identity", fd); S.state.identity = r.identity; renderIdentity(); toast("Identité enregistrée"); }
    catch (e) { fail(e); }
  }
  $("#ref-input").onchange = (e) => e.target.files[0] && postIdentity({}, { reference: e.target.files[0] });
  $("#extra-input").onchange = (e) => e.target.files.length && postIdentity({}, { extra: [...e.target.files] });
  $("#logo-input").onchange = (e) => e.target.files[0] && postIdentity({}, { logo: e.target.files[0] });
  $("#logo-reset").onclick = () => postIdentity({ reset_logo: "1" });
  $("#id-save").onclick = () => postIdentity({ name: $("#id-name").value, description: $("#id-desc").value });
  const drop = $("#ref-drop");
  drop.addEventListener("dragover", (e) => { e.preventDefault(); drop.classList.add("over"); });
  drop.addEventListener("dragleave", () => drop.classList.remove("over"));
  drop.addEventListener("drop", (e) => { e.preventDefault(); drop.classList.remove("over"); const f = e.dataTransfer.files[0]; if (f) postIdentity({}, { reference: f }); });

  // ---------------------------------------------------------------- projects
  function renderProjects() {
    const c = S.state.catalog;
    fillSelect($("#np-template"), Object.entries(c.templates), $("#np-template").value || "awakening");
    fillSelect($("#np-env"), [["", "(selon le scénario)"], ...Object.entries(c.environments)], $("#np-env").value);
    fillSelect($("#np-provider"), Object.entries(S.state.providers).map(([k, v]) => [k, v.label]), $("#np-provider").value || S.state.default_provider);
    const list = $("#project-list"); list.innerHTML = "";
    if (!S.state.projects.length) list.append(el("div", { className: "empty" }, "Aucun projet. Créez « SVETLANA — THE AWAKENING » →"));
    for (const p of S.state.projects) {
      const d = el("div", { className: "project" });
      d.append(el("b", {}, p.title || "Sans titre"));
      d.append(el("small", {}, `${new Date(p.created_at * 1000).toLocaleString("fr-FR")} · ${money(p.spent)}${p.render === "done" ? " · ✔ exporté" : ""}`));
      d.onclick = () => openProject(p.id);
      list.append(d);
    }
  }
  $("#np-create").onclick = async () => {
    try {
      const r = await api("POST", "/api/projects", {
        template: $("#np-template").value, title: $("#np-title").value, environment: $("#np-env").value || null,
        aspect: $("#np-aspect").value, provider: $("#np-provider").value,
      });
      $("#np-title").value = "";
      openProject(r.project.id);
    } catch (e) { fail(e); }
  };

  // ------------------------------------------------------------------ editor
  async function openProject(id) {
    try {
      if (!S.state) await loadState();
      S.project = (await api("GET", "/api/projects/" + id)).project;
      show("editor"); renderEditor(); ensurePolling();
    } catch (e) { fail(e); }
  }
  const P = () => S.project;

  function providerInfo() { return S.state.providers[P().provider] || S.state.providers.demo; }

  function renderEditor() {
    const p = P(), c = S.state.catalog;
    $("#ed-title").value = p.title || "";
    fillSelect($("#ed-provider"), Object.entries(S.state.providers).map(([k, v]) => [k, v.label]), p.provider);
    const pi = providerInfo();
    fillSelect($("#ed-video-model"), Object.entries(pi.video_models).map(([k, v]) => [k, `${v.label} – ${v.price_per_second ? "≈" + v.price_per_second + " $/s" : "gratuit"}`]), p.video_model);
    fillSelect($("#ed-image-model"), Object.entries(pi.image_models).map(([k, v]) => [k, `${v.label} – ${v.price_per_image ? "≈" + v.price_per_image + " $/img" : "gratuit"}`]), p.image_model);
    fillSelect($("#ed-env"), Object.entries(c.environments), p.environment);
    $("#ed-aspect").value = p.aspect; $("#ed-fit").value = p.fit || "cover";
    $("#ed-duration").value = p.duration; $("#ed-dropat").value = p.drop_at;
    $("#ed-astart").value = p.audio_start || 0;
    $("#ed-logo-mode").value = (p.logo || {}).mode || "drop";
    $("#ed-logo-at").value = (p.logo || {}).at ?? p.drop_at;
    $("#view-editor").classList.toggle("landscape", p.aspect === "16:9");
    renderAudio(); renderShots(); renderTimeline(); renderRender(); renderCost();
  }

  function renderCost() {
    const p = P(), pi = providerInfo();
    const vm = pi.video_models[p.video_model] || {}, im = pi.image_models[p.image_model] || {};
    let est = 0;
    for (const s of p.shots) {
      if (!s.keyframe && s.use_keyframe) est += im.price_per_image || 0;
      if (!s.clip) est += (vm.price_per_second || 0) * clipSeconds(s, vm);
    }
    $("#ed-spent").textContent = money(p.spent);
    $("#ed-estimate").textContent = money(est);
  }
  function clipSeconds(s, vm) {
    const need = Math.max(4, Math.ceil(s.end - s.start + 0.5));
    const ds = (vm && vm.durations) || [need];
    const ok = ds.filter((d) => d >= need);
    return ok.length ? Math.min(...ok) : Math.max(...ds);
  }

  // Sauvegarde différée des champs du projet
  function patch(fields, rerender = false) {
    Object.assign(S.project, fields);
    clearTimeout(S.saveTimer);
    S.saveTimer = setTimeout(async () => {
      try {
        const r = await api("PATCH", "/api/projects/" + P().id, fields.shots ? fields : { ...fields });
        mergeProject(r.project, rerender);
      } catch (e) { fail(e); }
    }, 350);
    renderTimeline(); renderCost();
  }
  function saveShots(rerender = false) { patch({ shots: P().shots }, rerender); }
  function mergeProject(fresh, full = false) {
    S.project = fresh;
    if (full) renderEditor(); else { updateShotsLive(); renderTimeline(); renderRender(); renderCost(); }
  }

  const bindPatch = (sel, key, conv = (v) => v, rerender = false) => {
    $(sel).addEventListener("change", (e) => patch({ [key]: conv(e.target.value) }, rerender));
  };
  bindPatch("#ed-title", "title");
  bindPatch("#ed-env", "environment");
  bindPatch("#ed-aspect", "aspect", String, true);
  bindPatch("#ed-fit", "fit");
  bindPatch("#ed-duration", "duration", Number, true);
  bindPatch("#ed-dropat", "drop_at", Number);
  bindPatch("#ed-astart", "audio_start", Number);
  bindPatch("#ed-image-model", "image_model");
  bindPatch("#ed-video-model", "video_model");
  $("#ed-provider").onchange = (e) => {
    const prov = e.target.value, pi = S.state.providers[prov];
    patch({ provider: prov, video_model: Object.keys(pi.video_models)[0], image_model: Object.keys(pi.image_models)[0] }, true);
    if (prov !== "demo" && !S.state.secrets.fal.configured) toast("Ajoutez votre clé fal.ai dans Réglages avant de générer.", 6000);
  };
  $("#ed-logo-mode").onchange = () => patch({ logo: { mode: $("#ed-logo-mode").value, at: Number($("#ed-logo-at").value) } });
  $("#ed-logo-at").onchange = $("#ed-logo-mode").onchange;
  $("#ed-back").onclick = () => { show("projects"); loadState(); };
  $("#ed-delete").onclick = async () => {
    if (!confirm("Supprimer définitivement ce projet et ses vidéos ?")) return;
    try { await api("DELETE", "/api/projects/" + P().id); show("projects"); loadState(); } catch (e) { fail(e); }
  };
  $("#ed-rebuild").onclick = async () => {
    if (!confirm("Remplacer tous les prompts par la version automatique ?")) return;
    try { mergeProject((await api("POST", `/api/projects/${P().id}/rebuild_prompts`, {})).project, true); toast("Prompts reconstruits"); } catch (e) { fail(e); }
  };

  // ------------------------------------------------------------------- audio
  $("#audio-input").onchange = async (e) => {
    const f = e.target.files[0]; if (!f) return;
    const fd = new FormData(); fd.append("audio", f);
    $("#audio-info").textContent = "Import et analyse en cours…";
    try { mergeProject((await api("POST", `/api/projects/${P().id}/audio`, fd)).project, true); toast("Musique analysée"); }
    catch (err) { fail(err); renderAudio(); }
    e.target.value = "";
  };
  $("#audio-auto").onclick = () => {
    const a = P().analysis; if (!a) return toast("Importez d'abord une musique");
    const drops = a.drops || [];
    if (!drops.length) return toast("Aucun drop détecté : placez l'extrait à la main.");
    const main = drops.reduce((m, d) => (d.strength > m.strength ? d : m));
    const start = Math.max(0, Math.min(main.time - P().drop_at, a.duration - P().duration));
    $("#ed-astart").value = start.toFixed(3); patch({ audio_start: +start.toFixed(3) }); renderAudio();
  };
  $("#audio-play").onclick = () => {
    const pl = $("#player"); if (!P().audio) return toast("Aucune musique");
    if (!pl.paused) { pl.pause(); return; }
    pl.currentTime = P().audio_start || 0; pl.play();
    const end = (P().audio_start || 0) + P().duration;
    const tick = () => { if (pl.currentTime >= end) pl.pause(); else if (!pl.paused) requestAnimationFrame(tick); drawWave(); };
    requestAnimationFrame(tick);
  };
  $("#wave").onclick = (e) => {
    const a = P().analysis; if (!a) return;
    const rect = e.target.getBoundingClientRect();
    let t = ((e.clientX - rect.left) / rect.width) * a.duration;
    // aligne sur le premier temps de mesure le plus proche
    const db = a.downbeats || [];
    if (db.length) t = db.reduce((b, x) => (Math.abs(x - t) < Math.abs(b - t) ? x : b), db[0]);
    t = Math.max(0, Math.min(t, a.duration - P().duration));
    $("#ed-astart").value = t.toFixed(3); patch({ audio_start: +t.toFixed(3) }); drawWave();
  };
  function renderAudio() {
    const p = P(), a = p.analysis;
    const info = $("#audio-info"); info.innerHTML = "";
    if (a) {
      info.append(el("span", {}, `${p.track_title || "Piste"} · `), el("b", {}, `${a.bpm} BPM`),
        el("span", {}, ` · ${a.duration.toFixed(1)} s · ${a.drops.length} drop(s) détecté(s)` +
          (a.drops.length ? " à " + a.drops.map((d) => d.time.toFixed(1) + " s").join(", ") : "")));
      $("#player").src = `/media/p/${p.id}/audio/${p.audio}`;
    } else info.textContent = "Aucune musique – importez votre production Suno (MP3 / WAV).";
    drawWave();
  }
  function drawWave() {
    const cv = $("#wave"), ctx = cv.getContext("2d");
    const w = (cv.width = cv.clientWidth * devicePixelRatio), h = (cv.height = 110 * devicePixelRatio);
    ctx.clearRect(0, 0, w, h);
    const a = P() && P().analysis; if (!a) return;
    const env = a.envelope, dur = a.duration, X = (t) => (t / dur) * w;
    const st = P().audio_start || 0;
    ctx.fillStyle = "rgba(225,11,47,.16)"; ctx.fillRect(X(st), 0, X(P().duration), h);
    ctx.fillStyle = "#9aa0aa";
    const bw = w / env.length;
    env.forEach((v, i) => { const bh = v * h * 0.9; ctx.fillRect(i * bw, (h - bh) / 2, Math.max(1, bw - 0.5), bh); });
    ctx.fillStyle = "rgba(255,255,255,.12)";
    (a.downbeats || []).forEach((t, i) => { if (i % 4 === 0) ctx.fillRect(X(t), 0, 1, h); });
    ctx.fillStyle = "#ff2a4d";
    a.drops.forEach((d) => ctx.fillRect(X(d.time) - 1, 0, 3, h));
    ctx.strokeStyle = "#fff"; ctx.lineWidth = 2 * devicePixelRatio;
    ctx.strokeRect(X(st), 1, X(P().duration), h - 2);
    ctx.fillStyle = "#fff"; ctx.fillRect(X(st + P().drop_at) - 1, 0, 2, h);
    const pl = $("#player");
    if (!pl.paused) { ctx.fillStyle = "#3ddc97"; ctx.fillRect(X(pl.currentTime), 0, 2, h); }
  }
  window.addEventListener("resize", () => P() && drawWave());

  // ---------------------------------------------------------------- timeline
  function renderTimeline() {
    const p = P(), tl = $("#timeline"); if (!p) return;
    tl.innerHTML = "";
    const D = p.duration, pct = (t) => `${(t / D) * 100}%`;
    const a = p.analysis;
    const period = a ? a.beat_period : 60 / 150;
    const beats = a ? a.beats.map((b) => b - (p.audio_start || 0)).filter((b) => b >= 0 && b <= D) : [];
    const downs = new Set(a ? a.downbeats.map((b) => (b - (p.audio_start || 0)).toFixed(3)) : []);
    (beats.length ? beats : Array.from({ length: Math.floor(D / period) }, (_, i) => i * period)).forEach((b) => {
      tl.append(el("div", { className: "tl-beat" + (downs.has(b.toFixed(3)) ? " bar" : "") , style: `left:${pct(b)}` }));
    });
    p.shots.forEach((s, i) => {
      const busy = ["generating", "keyframe_running"].includes(s.status);
      const d = el("div", { className: "tl-shot" + (s.clip ? " ready" : "") + (busy ? " busy" : "") }, `${i + 1}. ${s.label || ""}`);
      d.style.left = pct(s.start); d.style.width = `calc(${pct(Math.min(D, s.end) - s.start)} - 2px)`;
      d.onclick = () => $$(".shot")[i].scrollIntoView({ behavior: "smooth", block: "center" });
      tl.append(d);
    });
    if (p.drop_at) tl.append(el("div", { className: "tl-drop", style: `left:${pct(p.drop_at)}` }));
  }

  // ------------------------------------------------------------------- shots
  function renderShots() {
    const box = $("#shots"); box.innerHTML = "";
    const c = S.state.catalog;
    P().shots.forEach((s, i) => {
      const n = $("#shot-tpl").content.firstElementChild.cloneNode(true);
      n.dataset.id = s.id;
      $(".shot-num", n).textContent = String(i + 1).padStart(2, "0");
      $(".s-label", n).value = s.label || "";
      $(".s-start", n).value = s.start; $(".s-end", n).value = s.end;
      fillSelect($(".s-action", n), Object.entries(c.actions), s.action);
      fillSelect($(".s-camera", n), Object.entries(c.cameras), s.camera);
      fillSelect($(".s-env", n), [["", "(environnement du projet)"], ...Object.entries(c.environments)], s.environment || "");
      fillSelect($(".s-trans", n), Object.entries(c.transitions), s.transition_in || "cut");
      $(".s-prompt", n).value = s.prompt || "";
      $(".s-kf-prompt", n).value = s.keyframe_prompt || "";
      $(".s-neg", n).value = s.negative_prompt || "";
      $(".s-use-kf", n).checked = s.use_keyframe !== false;
      const fx = $(".effects", n);
      for (const [k, label] of Object.entries(c.effects)) {
        const l = el("label", { className: "check" });
        const cb = el("input", { type: "checkbox", value: k, checked: (s.effects || []).includes(k) });
        l.append(cb, document.createTextNode(label)); fx.append(l);
        cb.onchange = () => { s.effects = $$(".effects input:checked", n).map((x) => x.value); saveShots(); };
      }
      const field = (sel, key, conv = (v) => v) => $(sel, n).addEventListener("change", (e) => { s[key] = conv(e.target.value); saveShots(); });
      field(".s-label", "label"); field(".s-start", "start", Number); field(".s-end", "end", Number);
      field(".s-prompt", "prompt"); field(".s-kf-prompt", "keyframe_prompt"); field(".s-neg", "negative_prompt");
      field(".s-trans", "transition_in"); field(".s-env", "environment");
      const rebuildOn = (sel, key) => $(sel, n).addEventListener("change", async (e) => {
        s[key] = e.target.value; await flushSave();
        try { mergeProject((await api("POST", `/api/projects/${P().id}/rebuild_prompts`, { shot: s.id })).project, true); } catch (err) { fail(err); }
      });
      rebuildOn(".s-action", "action"); rebuildOn(".s-camera", "camera");
      $(".s-rebuild", n).onclick = async (e) => {
        e.preventDefault(); await flushSave();
        try { mergeProject((await api("POST", `/api/projects/${P().id}/rebuild_prompts`, { shot: s.id })).project, true); } catch (err) { fail(err); }
      };
      $(".s-use-kf", n).onchange = (e) => { s.use_keyframe = e.target.checked; saveShots(); };
      $(".s-remove", n).onclick = () => { if (confirm("Supprimer ce plan ?")) { P().shots.splice(i, 1); saveShots(true); } };
      $(".s-gen-kf", n).onclick = () => runShot(s, "keyframe");
      $(".s-gen-clip", n).onclick = () => runShot(s, "clip");
      $(".s-promote", n).onclick = async () => {
        try {
          const r = await api("POST", `/api/projects/${P().id}/shots/${s.id}/promote`);
          S.state.identity = r.identity; renderIdentity(); toast("Ajoutée aux références d'identité");
        } catch (e) { fail(e); }
      };
      $(".s-up-kf", n).onchange = (e) => uploadShot(s, e.target.files[0], "keyframe");
      $(".s-up-clip", n).onchange = (e) => uploadShot(s, e.target.files[0], "clip");
      $(".s-takes", n).onchange = (e) => { s.clip = e.target.value; saveShots(); updateShotsLive(); };
      box.append(n);
    });
    updateShotsLive();
  }

  const STATUS = { draft: "brouillon", keyframe_running: "keyframe…", keyframe_ready: "keyframe ok", generating: "génération…", ready: "clip prêt", error: "erreur" };
  function updateShotsLive() {
    const p = P();
    const vm = providerInfo().video_models[p.video_model] || {};
    p.shots.forEach((s) => {
      const n = $(`.shot[data-id="${s.id}"]`); if (!n) return;
      const st = $(".status", n); st.className = "status " + s.status;
      st.textContent = (STATUS[s.status] || s.status) + (s.progress ? " · " + s.progress : "");
      $(".error", n).textContent = s.error || "";
      const busy = ["generating", "keyframe_running"].includes(s.status);
      $(".s-gen-kf", n).disabled = busy; $(".s-gen-clip", n).disabled = busy;
      $(".s-promote", n).hidden = !s.keyframe;
      const price = (vm.price_per_second || 0) * clipSeconds(s, vm);
      $(".s-gen-clip", n).textContent = (s.clip ? "Regénérer" : "Générer clip") + (price ? ` (≈${price.toFixed(2)} $)` : "");
      const kb = $(".media-box.keyframe", n), img = $("img", kb);
      if (s.keyframe) { const src = `/media/p/${p.id}/keyframes/${s.keyframe}`; if (!img.src.endsWith(src)) img.src = src; kb.classList.add("has"); }
      else kb.classList.remove("has");
      const cb = $(".media-box.clip", n), v = $("video", cb);
      if (s.clip) { const src = `/media/p/${p.id}/clips/${s.clip}`; if (!v.src.endsWith(src)) { v.src = src; v.play().catch(() => {}); } cb.classList.add("has"); }
      else cb.classList.remove("has");
      const takes = $(".s-takes", n);
      fillSelect(takes, (s.takes || []).map((t, i) => [t, `Prise ${i + 1}${t.includes("upload") ? " (importée)" : ""}`]), s.clip);
      takes.hidden = !(s.takes || []).length;
    });
  }
  async function flushSave() {
    clearTimeout(S.saveTimer);
    try { const r = await api("PATCH", "/api/projects/" + P().id, { shots: P().shots }); S.project = r.project; } catch (e) { fail(e); }
  }
  async function runShot(s, kind) {
    await flushSave();
    const vm = providerInfo().video_models[P().video_model] || {};
    if (kind === "clip" && vm.price_per_second) {
      const cost = vm.price_per_second * clipSeconds(s, vm);
      if (!confirm(`Générer ce clip avec ${vm.label} ?\nCoût estimé : ≈ ${cost.toFixed(2)} $`)) return;
    }
    try { mergeProject((await api("POST", `/api/projects/${P().id}/shots/${s.id}/${kind}`)).project); ensurePolling(); }
    catch (e) { fail(e); }
  }
  async function uploadShot(s, file, kind) {
    if (!file) return;
    const fd = new FormData(); fd.append("file", file); fd.append("kind", kind);
    try { mergeProject((await api("POST", `/api/projects/${P().id}/shots/${s.id}/upload`, fd)).project); toast("Fichier importé"); }
    catch (e) { fail(e); }
  }
  $("#add-shot").onclick = () => {
    const last = P().shots[P().shots.length - 1];
    const start = last ? last.end : 0;
    P().shots.push({ label: "Nouveau plan", start, end: Math.min(P().duration, start + 3) || start + 3, action: "mixing",
      camera: "orbit", transition_in: "cut", effects: [], prompt: "", keyframe_prompt: "" });
    flushSave().then(async () => {
      const id = P().shots[P().shots.length - 1].id;
      try { mergeProject((await api("POST", `/api/projects/${P().id}/rebuild_prompts`, { shot: id })).project, true); } catch (e) { fail(e); }
    });
  };
  async function generateAll(what) {
    await flushSave();
    const p = P(), pi = providerInfo();
    if (p.provider !== "demo") {
      const vm = pi.video_models[p.video_model] || {}, im = pi.image_models[p.image_model] || {};
      const cost = what === "clips"
        ? p.shots.filter((s) => !s.clip).reduce((a, s) => a + (vm.price_per_second || 0) * clipSeconds(s, vm), 0)
        : p.shots.length * (im.price_per_image || 0);
      if (!confirm(`Lancer la génération (${what === "clips" ? "clips manquants" : "toutes les keyframes"}) ?\nCoût estimé : ≈ ${cost.toFixed(2)} $`)) return;
    }
    try { mergeProject((await api("POST", `/api/projects/${p.id}/generate_all`, { what })).project); ensurePolling(); toast("Génération lancée"); }
    catch (e) { fail(e); }
  }
  $("#gen-keyframes").onclick = () => generateAll("keyframes");
  $("#gen-clips").onclick = () => generateAll("clips");

  // ------------------------------------------------------------------ render
  $("#render").onclick = async () => {
    await flushSave();
    const formats = $$(".fmt:checked").map((c) => c.value);
    if (!formats.length) return toast("Choisissez au moins un format");
    const missing = P().shots.filter((s) => !s.clip).length;
    if (missing && !confirm(`${missing} plan(s) sans clip : la keyframe ou la photo officielle sera utilisée à la place. Continuer ?`)) return;
    try { mergeProject((await api("POST", `/api/projects/${P().id}/render`, { formats })).project); ensurePolling(); }
    catch (e) { fail(e); }
  };
  function renderRender() {
    const r = P().render, pr = $("#render-progress"), out = $("#outputs");
    $("#render").disabled = r && r.status === "running";
    if (!r) { pr.hidden = true; out.innerHTML = ""; return; }
    pr.hidden = r.status === "done" && !!r.outputs;
    $("div", pr).style.width = `${Math.round((r.progress || 0) * 100)}%`;
    $("span", pr).textContent = r.status === "error" ? "⚠ " + r.message : `${Math.round((r.progress || 0) * 100)} % · ${r.message || ""}`;
    if (r.status !== "done" || !r.outputs) { if (r.status !== "running") out.innerHTML = ""; return; }
    if (out.dataset.stamp === String(r.finished_at)) return;
    out.dataset.stamp = String(r.finished_at); out.innerHTML = "";
    const base = `/media/p/${P().id}/exports/`;
    for (const o of r.outputs) {
      const d = el("div", { className: "output" });
      d.append(el("h3", {}, o.label));
      d.append(el("video", { src: base + o.video + "?t=" + r.finished_at, controls: true, poster: base + o.thumbnail + "?t=" + r.finished_at, playsInline: true }));
      const row = el("div", { className: "row" });
      row.append(el("a", { className: "btn small", href: base + o.video + "?dl=1" }, "Télécharger MP4"));
      row.append(el("a", { className: "btn ghost small", href: base + o.thumbnail + "?dl=1" }, "Miniature"));
      d.append(row); out.append(d);
    }
    if (r.captions) {
      const d = el("div", { className: "output" });
      d.append(el("h3", {}, "Textes & hashtags"));
      const ta = el("textarea", { rows: 14, readOnly: true });
      fetch(base + r.captions).then((x) => x.text()).then((t) => (ta.value = t));
      d.append(ta); out.append(d);
    }
  }

  // ----------------------------------------------------------------- polling
  function busy() {
    const p = P(); if (!p) return false;
    return (p.render && p.render.status === "running") || p.shots.some((s) => ["generating", "keyframe_running"].includes(s.status));
  }
  function ensurePolling() {
    if (S.pollTimer) return;
    S.pollTimer = setInterval(async () => {
      if (!P()) return stopPolling();
      try {
        const fresh = (await api("GET", "/api/projects/" + P().id)).project;
        const keep = S.project.shots; // conserve les modifications locales non sauvegardées
        fresh.shots.forEach((f) => { const l = keep.find((k) => k.id === f.id); if (l && S.saveTimer) { f.prompt = l.prompt; } });
        mergeProject(fresh);
        if (!busy()) stopPolling();
      } catch (e) { /* réseau : on réessaie */ }
    }, 2500);
  }
  function stopPolling() { clearInterval(S.pollTimer); S.pollTimer = null; }

  // ---------------------------------------------------------------- settings
  function renderSettings() {
    const box = $("#secrets"); box.innerHTML = "";
    for (const [name, st] of Object.entries(S.state.secrets)) {
      const d = el("div", { className: "secret" });
      d.append(el("b", {}, name === "fal" ? "fal.ai (Kling, Veo, Seedance, Nano Banana…)" : name));
      d.append(el("div", { className: st.configured ? "ok" : "missing" },
        st.configured ? `✔ Configurée (${st.masked}) – source : ${st.source === "env" ? "variable " + st.env_var : "stockage chiffré"}` : "✕ Non configurée"));
      if (st.source !== "env") {
        const inp = el("input", { type: "password", placeholder: "Coller la clé ici", autocomplete: "off" });
        const row = el("div", { className: "row" });
        const save = el("button", { className: "btn small" }, "Enregistrer");
        const del = el("button", { className: "btn ghost small" }, "Effacer");
        save.onclick = async () => {
          try { S.state.secrets = (await api("POST", "/api/secrets", { name, value: inp.value })).secrets; renderSettings(); toast("Clé enregistrée (chiffrée)"); }
          catch (e) { fail(e); }
        };
        del.onclick = async () => { try { S.state.secrets = (await api("POST", "/api/secrets", { name, value: "" })).secrets; renderSettings(); } catch (e) { fail(e); } };
        row.append(inp, save, del); d.append(row);
        if (!S.state.can_store_secrets) d.append(el("p", { className: "hint" }, "Stockage chiffré indisponible : définissez APP_SECRET_KEY, ou utilisez la variable " + st.env_var + "."));
      }
      d.append(el("p", { className: "hint" }, "Obtenir une clé : fal.ai → Dashboard → Keys. Ajoutez du crédit avant de générer."));
      box.append(d);
    }
    const t = $("#models-table"); t.innerHTML = "";
    const table = el("table"); const head = el("tr");
    ["Modèle", "Type", "Tarif indicatif"].forEach((h) => head.append(el("th", {}, h))); table.append(head);
    const fal = S.state.providers.fal;
    for (const v of Object.values(fal.video_models)) {
      const tr = el("tr"); tr.append(el("td", {}, v.label), el("td", {}, "vidéo"), el("td", {}, `≈ ${v.price_per_second} $/s`)); table.append(tr);
    }
    for (const v of Object.values(fal.image_models)) {
      const tr = el("tr"); tr.append(el("td", {}, v.label), el("td", {}, "keyframe"), el("td", {}, `≈ ${v.price_per_image} $/image`)); table.append(tr);
    }
    t.append(table);
  }

  loadState().catch(fail);
})();
