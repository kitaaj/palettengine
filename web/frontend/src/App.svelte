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

  const hexes = $derived(swatches.map((s) => s.hex));
  const display = $derived(cvd === "none" ? hexes : simulated);

  function applyPayload(doc: PalettePayload, keepLocks: boolean) {
    payload = doc;
    swatches = doc.colors.map((c, i) => ({
      hex: c.hex,
      locked: keepLocks && (swatches[i]?.locked ?? false),
    }));
    refreshSim();
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

  async function onUpload(files: FileList | null) {
    if (!files?.length) return;
    busy = true;
    error = "";
    try {
      applyPayload(await extractPalette(files[0], size, false), false);
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    } finally {
      busy = false;
    }
  }

  function toggleLock(i: number) {
    swatches[i].locked = !swatches[i].locked;
  }

  function editColor(i: number, hex: string) {
    swatches[i].hex = hex;
    swatches[i].locked = true; // editing implies intent to keep
    refreshSim();
  }

  function setCvd(kind: string) {
    cvd = kind;
    refreshSim();
  }

  function onKey(e: KeyboardEvent) {
    if (e.code === "Space" && !(e.target instanceof HTMLInputElement)) {
      e.preventDefault();
      doGenerate();
    }
  }

  // One-time init. NOT an $effect: doGenerate() reads `swatches` synchronously and
  // writes it on completion, so a tracking effect would re-trigger itself forever
  // (an infinite request loop against /api/generate).
  onMount(() => {
    fetchMeta()
      .then((m) => (meta = m))
      .catch(() => (error = "API unreachable — is `palette serve` running?"));
    doGenerate();
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

  {#if swatches.length}
    <SwatchRow {swatches} {display} onToggleLock={toggleLock} onEdit={editColor} />

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
