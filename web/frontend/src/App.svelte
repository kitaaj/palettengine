<script lang="ts">
  import { onMount } from "svelte";
  import {
    extractPalette,
    fetchMeta,
    generatePalette,
    simulatePalette,
    type Meta,
    type PalettePayload,
  } from "./lib/api";
  import ContrastGrid from "./lib/ContrastGrid.svelte";
  import ExportPanel from "./lib/ExportPanel.svelte";
  import Icon from "./lib/Icon.svelte";
  import SwatchEditor from "./lib/SwatchEditor.svelte";
  import SwatchRow, { type Swatch } from "./lib/SwatchRow.svelte";
  import ThemePreview from "./lib/ThemePreview.svelte";

  let meta = $state<Meta | null>(null);
  let swatches = $state<Swatch[]>([]);
  let payload = $state<PalettePayload | null>(null);

  let scheme = $state("auto");
  let size = $state(5);
  let mode = $state("general");
  let seedText = $state("");

  let cvd = $state("none");
  let simulated = $state<string[]>([]);
  let busy = $state(false);
  let error = $state("");
  let linkCopied = $state(false);
  let editorIndex = $state(-1);

  // Extraction source (kept so the palette can be re-rolled from the same image).
  let sourceFile = $state<File | null>(null);
  let sourceThumb = $state("");
  let faithful = $state(false);

  // Undo/redo: snapshots of the visible palette state.
  interface Snapshot {
    swatches: Swatch[];
    payload: PalettePayload | null;
  }
  let past = $state<Snapshot[]>([]);
  let future = $state<Snapshot[]>([]);
  const canUndo = $derived(past.length > 0);
  const canRedo = $derived(future.length > 0);

  type ThemeMode = "light" | "dark" | "system";
  let theme = $state<ThemeMode>((localStorage.getItem("theme") as ThemeMode) ?? "system");

  const hexes = $derived(swatches.map((s) => s.hex));
  const display = $derived(cvd === "none" ? hexes : simulated);
  // Server-computed WCAG overlay colors; only valid while the swatch still matches
  // the payload (a local edit or CVD preview falls back to the client estimate).
  const textOn = $derived(
    swatches.map((s, i) =>
      cvd === "none" && payload?.colors[i]?.hex === s.hex
        ? (payload.colors[i].text_on ?? null)
        : null,
    ),
  );

  function setTheme(t: ThemeMode) {
    theme = t;
    localStorage.setItem("theme", t);
    if (t === "system") delete document.documentElement.dataset.theme;
    else document.documentElement.dataset.theme = t;
  }

  function syncUrl() {
    const p = new URLSearchParams();
    p.set("c", hexes.map((h) => h.slice(1)).join("-"));
    const locked = swatches.flatMap((s, i) => (s.locked ? [i] : []));
    if (locked.length) p.set("l", locked.join("."));
    p.set("scheme", scheme);
    p.set("mode", mode);
    if (seedText.trim()) p.set("seed", seedText.trim());
    history.replaceState(null, "", `#${p.toString()}`);
  }

  function applyPayload(doc: PalettePayload, keepLocks: boolean) {
    payload = doc;
    swatches = doc.colors.map((c, i) => ({
      hex: c.hex,
      locked: keepLocks && (swatches[i]?.locked ?? false),
    }));
    refreshSim();
    syncUrl();
  }

  /** Restore a palette from the URL hash; true if one was restored. */
  async function restoreFromUrl(): Promise<boolean> {
    const p = new URLSearchParams(location.hash.slice(1));
    const c = p.get("c");
    if (!c) return false;
    const hx = c.split("-").map((h) => `#${h}`);
    if (!hx.length || hx.some((h) => !/^#[0-9a-f]{6}$/i.test(h))) return false;
    scheme = p.get("scheme") ?? scheme;
    mode = p.get("mode") ?? mode;
    seedText = p.get("seed") ?? "";
    size = hx.length;
    // Lock every slot to the URL's colors: the engine returns them exactly,
    // along with the full score/contrast/roles payload.
    const locks: Record<number, string> = Object.fromEntries(hx.map((h, i) => [i, h]));
    const doc = await generatePalette({ scheme, size, mode, locks, seed: 0 });
    applyPayload(doc, false);
    const lockedSet = new Set((p.get("l") ?? "").split(".").filter(Boolean).map(Number));
    swatches = swatches.map((s, i) => ({ ...s, locked: lockedSet.has(i) }));
    return true;
  }

  async function copyLink() {
    await navigator.clipboard.writeText(location.href);
    linkCopied = true;
    setTimeout(() => (linkCopied = false), 1100);
  }

  // ---- history ----------------------------------------------------------
  function pushHistory() {
    if (!swatches.length) return;
    past = [
      ...past.slice(-49),
      { swatches: $state.snapshot(swatches), payload: $state.snapshot(payload) },
    ];
    future = [];
  }

  function restoreSnapshot(s: Snapshot) {
    swatches = s.swatches.map((x) => ({ ...x }));
    payload = s.payload;
    refreshSim();
    syncUrl();
  }

  function undo() {
    if (!canUndo) return;
    future = [...future, { swatches: $state.snapshot(swatches), payload: $state.snapshot(payload) }];
    const s = past[past.length - 1];
    past = past.slice(0, -1);
    restoreSnapshot(s);
  }

  function redo() {
    if (!canRedo) return;
    past = [...past, { swatches: $state.snapshot(swatches), payload: $state.snapshot(payload) }];
    const s = future[future.length - 1];
    future = future.slice(0, -1);
    restoreSnapshot(s);
  }

  /**
   * Refresh score/contrast/roles after a local change (edit, reorder) without
   * altering the colors: an all-locked generate returns them exactly.
   */
  async function refreshPanels() {
    const locks: Record<number, string> = Object.fromEntries(hexes.map((h, i) => [i, h]));
    try {
      payload = await generatePalette({ scheme, size: hexes.length, mode, locks, seed: 0 });
    } catch {
      /* panels go stale rather than erroring the whole app */
    }
    refreshSim();
    syncUrl();
  }

  async function refreshSim() {
    if (cvd === "none" || swatches.length === 0) return;
    try {
      simulated = await simulatePalette(hexes, cvd);
    } catch {
      simulated = hexes;
    }
  }

  async function doGenerate() {
    busy = true;
    error = "";
    pushHistory();
    try {
      const locks: Record<number, string> = {};
      swatches.forEach((s, i) => {
        if (s.locked && i < size) locks[i] = s.hex;
      });
      const seed = seedText.trim() === "" ? null : Number(seedText);
      applyPayload(await generatePalette({ scheme, size, mode, locks, seed }), true);
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    } finally {
      busy = false;
    }
  }

  async function runExtract(file: File, seed?: number) {
    busy = true;
    error = "";
    pushHistory();
    try {
      applyPayload(await extractPalette(file, { size, faithful, seed }), false);
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    } finally {
      busy = false;
    }
  }

  function onUpload(files: FileList | null) {
    if (!files?.length) return;
    const file = files[0];
    sourceFile = file;
    if (sourceThumb) URL.revokeObjectURL(sourceThumb);
    sourceThumb = file.type.startsWith("image/") ? URL.createObjectURL(file) : "";
    runExtract(file);
  }

  function reroll() {
    if (sourceFile) runExtract(sourceFile, Math.floor(Math.random() * 1_000_000));
  }

  function clearSource() {
    sourceFile = null;
    if (sourceThumb) URL.revokeObjectURL(sourceThumb);
    sourceThumb = "";
  }

  function toggleLock(i: number) {
    swatches[i].locked = !swatches[i].locked;
    syncUrl();
  }

  function applyEdit(hex: string) {
    if (editorIndex < 0) return;
    pushHistory();
    swatches[editorIndex].hex = hex;
    swatches[editorIndex].locked = true; // editing implies intent to keep
    editorIndex = -1;
    refreshPanels();
  }

  function reorder(from: number, to: number) {
    pushHistory();
    const arr = swatches.map((s) => ({ ...s }));
    const [moved] = arr.splice(from, 1);
    arr.splice(to, 0, moved);
    swatches = arr;
    refreshPanels();
  }

  function setCvd(kind: string) {
    cvd = kind;
    refreshSim();
  }

  function onKey(e: KeyboardEvent) {
    if (editorIndex >= 0) return; // modal handles its own keys
    const mod = e.ctrlKey || e.metaKey;
    if (mod && e.key.toLowerCase() === "z" && !e.shiftKey) {
      e.preventDefault();
      undo();
    } else if ((mod && e.key.toLowerCase() === "y") || (mod && e.shiftKey && e.key.toLowerCase() === "z")) {
      e.preventDefault();
      redo();
    } else if (e.code === "Space" && !(e.target instanceof HTMLInputElement)) {
      e.preventDefault();
      doGenerate();
    }
  }

  // One-time init. NOT an $effect: doGenerate() reads `swatches` synchronously and
  // writes it on completion, so a tracking effect would re-trigger itself forever
  // (an infinite request loop against /api/generate).
  onMount(() => {
    setTheme(theme);
    fetchMeta()
      .then((m) => (meta = m))
      .catch(() => (error = "API unreachable — is `palette serve` running?"));
    restoreFromUrl()
      .then((restored) => {
        if (!restored) doGenerate();
      })
      .catch(() => doGenerate());
  });
</script>

<svelte:window onkeydown={onKey} />

<main>
  <header>
    <div class="brand">
      <svg width="26" height="26" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <circle cx="9" cy="9" r="6.5" fill="var(--accent)" opacity="0.9" />
        <circle cx="15" cy="15" r="6.5" fill="var(--ok)" opacity="0.75" />
      </svg>
      <h1>Palette<span>Generator</span></h1>
    </div>
    <div class="meta-links">
      <span class="hint"><kbd>Space</kbd> to generate</span>
      <button
        class="ghost"
        onclick={undo}
        disabled={!canUndo}
        title="Undo (Ctrl+Z)"
        aria-label="Undo"
      >
        <Icon name="undo" size={13} />
      </button>
      <button
        class="ghost"
        onclick={redo}
        disabled={!canRedo}
        title="Redo (Ctrl+Y)"
        aria-label="Redo"
      >
        <Icon name="redo" size={13} />
      </button>
      <button class="ghost" onclick={copyLink} title="Copy shareable link">
        <Icon name={linkCopied ? "check" : "link"} size={13} />
        {linkCopied ? "Copied" : "Share"}
      </button>
      <div class="segmented" role="group" aria-label="Theme">
        <button
          class:active={theme === "light"}
          onclick={() => setTheme("light")}
          title="Light theme"
          aria-label="Light theme"
        >
          <Icon name="sun" size={13} />
        </button>
        <button
          class:active={theme === "system"}
          onclick={() => setTheme("system")}
          title="Follow system theme"
          aria-label="System theme"
        >
          <Icon name="monitor" size={13} />
        </button>
        <button
          class:active={theme === "dark"}
          onclick={() => setTheme("dark")}
          title="Dark theme"
          aria-label="Dark theme"
        >
          <Icon name="moon" size={13} />
        </button>
      </div>
      <a href="/docs" target="_blank" rel="noreferrer">
        API
        <Icon name="external-link" size={12} />
      </a>
    </div>
  </header>

  <section class="toolbar">
    <label>
      <span class="label">Scheme</span>
      <select bind:value={scheme}>
        {#each meta?.schemes ?? ["auto"] as s (s)}
          <option value={s}>{s.replaceAll("_", " ")}</option>
        {/each}
      </select>
    </label>
    <label>
      <span class="label">Colors</span>
      <input type="number" min="1" max="12" bind:value={size} onchange={doGenerate} />
    </label>
    <div class="field">
      <span class="label">Mode</span>
      <div class="segmented" role="group" aria-label="Generation mode">
        {#each meta?.modes ?? ["general", "ui"] as m (m)}
          <button
            class:active={mode === m}
            onclick={() => {
              mode = m;
              doGenerate();
            }}
          >
            {m}
          </button>
        {/each}
      </div>
    </div>
    <label>
      <span class="label">Seed</span>
      <input type="text" placeholder="random" bind:value={seedText} />
    </label>
    <div class="spacer"></div>
    <label class="upload">
      <input
        type="file"
        accept="image/*,video/*"
        onchange={(e) => onUpload((e.target as HTMLInputElement).files)}
      />
      <span class="upload-btn"><Icon name="image" /> Extract from image</span>
    </label>
    <button class="primary" onclick={doGenerate} disabled={busy}>
      <Icon name="refresh" />
      Generate
    </button>
  </section>

  {#if error}
    <p class="error" role="alert">{error}</p>
  {/if}

  {#if sourceFile}
    <section class="source-chip">
      {#if sourceThumb}
        <img src={sourceThumb} alt="Extraction source" />
      {/if}
      <div class="source-meta">
        <span class="source-name">{sourceFile.name}</span>
        <span class="source-hint">palette extracted from this {sourceThumb ? "image" : "file"}</span>
      </div>
      <label class="faithful">
        <input type="checkbox" bind:checked={faithful} />
        faithful
      </label>
      <button onclick={reroll} disabled={busy} title="Extract a different palette from the same source">
        <Icon name="refresh" size={13} />
        Re-roll
      </button>
      <button class="ghost" onclick={clearSource} title="Dismiss source" aria-label="Dismiss source">
        <Icon name="x" size={13} />
      </button>
    </section>
  {/if}

  {#if swatches.length}
    <SwatchRow
      {swatches}
      {display}
      {textOn}
      onToggleLock={toggleLock}
      onOpenEditor={(i) => (editorIndex = i)}
      onReorder={reorder}
    />

    <section class="cvd">
      <span class="cvd-label"><Icon name="eye" size={14} /> Vision</span>
      <div class="segmented" role="group" aria-label="Color vision simulation">
        {#each ["none", ...(meta?.cvd_kinds ?? [])] as kind (kind)}
          <button class:active={cvd === kind} onclick={() => setCvd(kind)}>{kind}</button>
        {/each}
      </div>
    </section>

    {#if payload}
      <div class="grid2">
        <section class="card">
          <h2>Quality <small>score {payload.score.toFixed(2)}</small></h2>
          {#each Object.entries(payload.breakdown) as [term, v] (term)}
            <div class="bar">
              <span>{term.replaceAll("_", " ")}</span>
              <div class="track"><div class="fill" style="width:{v * 100}%"></div></div>
              <b>{v.toFixed(2)}</b>
            </div>
          {/each}
        </section>

        <section class="card">
          <h2>Contrast</h2>
          <ContrastGrid {hexes} matrix={payload.contrast} />
        </section>

        <section class="card">
          <h2>Themes</h2>
          <div class="themes">
            <ThemePreview roles={payload.roles.light} theme="light" />
            <ThemePreview roles={payload.roles.dark} theme="dark" />
          </div>
        </section>

        <section class="card">
          <h2>Export</h2>
          <ExportPanel {hexes} formats={meta?.formats ?? []} />
        </section>
      </div>
    {/if}
  {/if}

  {#if editorIndex >= 0 && swatches[editorIndex]}
    <SwatchEditor
      hex={swatches[editorIndex].hex}
      onApply={applyEdit}
      onClose={() => (editorIndex = -1)}
    />
  {/if}
</main>

<style>
  main {
    max-width: 1100px;
    margin: 0 auto;
    padding: 1.4rem 1.5rem 3rem;
    display: flex;
    flex-direction: column;
    gap: 1.15rem;
  }

  /* ---- header ---- */
  header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .brand {
    display: flex;
    align-items: center;
    gap: 0.6rem;
  }
  h1 {
    margin: 0;
    font-size: 1.25rem;
    font-weight: 700;
    letter-spacing: -0.01em;
  }
  h1 span {
    color: var(--muted);
    font-weight: 400;
  }
  .meta-links {
    display: flex;
    align-items: center;
    gap: 1rem;
    font-size: 0.8rem;
  }
  .hint {
    color: var(--muted);
  }
  kbd {
    border: 1px solid var(--border);
    border-bottom-width: 2px;
    border-radius: 5px;
    padding: 0.05rem 0.4rem;
    font-size: 0.72rem;
    font-family: inherit;
    background: var(--surface);
  }
  .meta-links a {
    color: var(--muted);
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
  }
  .meta-links a:hover {
    color: var(--accent);
  }
  .meta-links .segmented button {
    padding: 0.32rem 0.5rem;
  }
  .meta-links .ghost {
    font-size: 0.8rem;
    color: var(--muted);
  }
  .meta-links .ghost:hover {
    color: var(--accent);
  }

  /* ---- toolbar ---- */
  .toolbar {
    display: flex;
    gap: 0.9rem;
    align-items: end;
    flex-wrap: wrap;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 0.9rem 1rem;
    box-shadow: var(--shadow-sm);
  }
  .toolbar label,
  .toolbar .field {
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
  }
  .toolbar input[type="number"] {
    width: 4.6rem;
  }
  .toolbar input[type="text"] {
    width: 6.5rem;
  }
  .spacer {
    flex: 1;
  }
  .upload input {
    display: none;
  }
  .upload-btn {
    border: 1px dashed var(--border);
    border-radius: var(--radius-sm);
    padding: 0.45rem 0.85rem;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    color: var(--muted);
    transition: 130ms ease;
  }
  .upload-btn:hover {
    border-color: var(--accent);
    color: var(--accent);
  }

  /* ---- segmented control ---- */
  .segmented {
    display: inline-flex;
    background: var(--surface-2);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 2px;
    gap: 2px;
  }
  .segmented button {
    border: none;
    background: transparent;
    box-shadow: none;
    border-radius: calc(var(--radius-sm) - 2px);
    padding: 0.3rem 0.75rem;
    font-size: 0.82rem;
    color: var(--muted);
  }
  .segmented button:hover {
    color: var(--text);
  }
  .segmented button.active {
    background: var(--surface);
    color: var(--text);
    font-weight: 600;
    box-shadow: var(--shadow-sm);
  }

  .error {
    color: var(--danger);
    margin: 0;
  }

  /* ---- extraction source chip ---- */
  .source-chip {
    display: flex;
    align-items: center;
    gap: 0.8rem;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 0.55rem 0.8rem;
    box-shadow: var(--shadow-sm);
  }
  .source-chip img {
    width: 44px;
    height: 44px;
    object-fit: cover;
    border-radius: var(--radius-sm);
    border: 1px solid var(--border);
  }
  .source-meta {
    display: flex;
    flex-direction: column;
    min-width: 0;
    flex: 1;
  }
  .source-name {
    font-size: 0.84rem;
    font-weight: 600;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .source-hint {
    font-size: 0.74rem;
    color: var(--muted);
  }
  .faithful {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    font-size: 0.8rem;
    color: var(--muted);
    cursor: pointer;
  }

  /* ---- cvd row ---- */
  .cvd {
    display: flex;
    gap: 0.7rem;
    align-items: center;
  }
  .cvd-label {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.8rem;
    color: var(--muted);
  }

  /* ---- cards ---- */
  .grid2 {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
    gap: 1.15rem;
  }
  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1.05rem 1.2rem 1.2rem;
    box-shadow: var(--shadow-sm);
  }
  .card h2 {
    margin: 0 0 0.9rem;
    font-size: 0.95rem;
    font-weight: 650;
  }
  .card h2 small {
    color: var(--muted);
    font-weight: 400;
    font-size: 0.8rem;
  }
  .bar {
    display: grid;
    grid-template-columns: 9rem 1fr 2.6rem;
    gap: 0.6rem;
    align-items: center;
    font-size: 0.84rem;
    margin-bottom: 0.5rem;
  }
  .bar b {
    font-variant-numeric: tabular-nums;
    font-weight: 600;
    text-align: right;
  }
  .track {
    height: 7px;
    background: var(--surface-2);
    border-radius: 999px;
    overflow: hidden;
  }
  .fill {
    height: 100%;
    background: var(--accent);
    border-radius: 999px;
    transition: width 220ms ease;
  }
  .themes {
    display: flex;
    flex-direction: column;
    gap: 0.85rem;
  }
</style>
