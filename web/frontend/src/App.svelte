<script lang="ts">
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

  $effect(() => {
    fetchMeta()
      .then((m) => (meta = m))
      .catch(() => (error = "API unreachable — is `palette serve` running?"));
    doGenerate();
  });
</script>

<svelte:window onkeydown={onKey} />

<main>
  <header>
    <h1>palette<span>-generator</span></h1>
    <p class="tag">
      perceptual palettes in OKLCH · hard locks · WCAG-aware · <kbd>space</kbd> to generate
    </p>
  </header>

  <section class="controls">
    <label>
      scheme
      <select bind:value={scheme}>
        {#each meta?.schemes ?? ["auto"] as s (s)}
          <option value={s}>{s.replaceAll("_", " ")}</option>
        {/each}
      </select>
    </label>
    <label>
      colors
      <input type="number" min="1" max="12" bind:value={size} onchange={doGenerate} />
    </label>
    <label>
      mode
      <select bind:value={mode} onchange={doGenerate}>
        <option value="general">general</option>
        <option value="ui">ui</option>
      </select>
    </label>
    <label>
      seed
      <input type="text" placeholder="random" bind:value={seedText} />
    </label>
    <button class="primary" onclick={doGenerate} disabled={busy}>
      {busy ? "…" : "generate"}
    </button>
    <label class="upload">
      <input
        type="file"
        accept="image/*,video/*"
        onchange={(e) => onUpload((e.target as HTMLInputElement).files)}
      />
      <span>extract from image…</span>
    </label>
  </section>

  {#if error}
    <p class="error">{error}</p>
  {/if}

  {#if swatches.length}
    <SwatchRow {swatches} {display} onToggleLock={toggleLock} onEdit={editColor} />

    <section class="cvd">
      <span>vision:</span>
      {#each ["none", ...(meta?.cvd_kinds ?? [])] as kind (kind)}
        <button class:active={cvd === kind} onclick={() => setCvd(kind)}>{kind}</button>
      {/each}
    </section>

    {#if payload}
      <div class="grid2">
        <section class="card">
          <h2>quality <small>score {payload.score.toFixed(2)}</small></h2>
          {#each Object.entries(payload.breakdown) as [term, v] (term)}
            <div class="bar">
              <span>{term.replaceAll("_", " ")}</span>
              <div class="track"><div class="fill" style="width:{v * 100}%"></div></div>
              <b>{v.toFixed(2)}</b>
            </div>
          {/each}
        </section>

        <section class="card">
          <h2>contrast</h2>
          <ContrastGrid {hexes} matrix={payload.contrast} />
        </section>

        <section class="card">
          <h2>themes</h2>
          <div class="themes">
            <ThemePreview roles={payload.roles.light} theme="light" />
            <ThemePreview roles={payload.roles.dark} theme="dark" />
          </div>
        </section>

        <section class="card">
          <h2>export</h2>
          <ExportPanel {hexes} formats={meta?.formats ?? []} />
        </section>
      </div>
    {/if}
  {/if}
</main>

<style>
  main {
    max-width: 1080px;
    margin: 0 auto;
    padding: 1.2rem 1.4rem 3rem;
    display: flex;
    flex-direction: column;
    gap: 1.1rem;
  }
  header h1 {
    margin: 0;
    font-size: 1.6rem;
  }
  header h1 span {
    color: var(--muted);
    font-weight: 400;
  }
  .tag {
    margin: 0.2rem 0 0;
    color: var(--muted);
    font-size: 0.85rem;
  }
  kbd {
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 0 0.3rem;
    font-size: 0.75rem;
  }
  .controls {
    display: flex;
    gap: 0.8rem;
    align-items: end;
    flex-wrap: wrap;
  }
  .controls label {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    font-size: 0.8rem;
    color: var(--muted);
  }
  .controls input[type="number"] {
    width: 4.5rem;
  }
  .controls input[type="text"] {
    width: 6.5rem;
  }
  .upload input {
    display: none;
  }
  .upload span {
    border: 1px dashed var(--border);
    border-radius: 8px;
    padding: 0.45rem 0.9rem;
    cursor: pointer;
    display: inline-block;
  }
  .upload span:hover {
    border-color: var(--accent);
  }
  .error {
    color: #dc2626;
    margin: 0;
  }
  .cvd {
    display: flex;
    gap: 0.4rem;
    align-items: center;
    font-size: 0.85rem;
    color: var(--muted);
  }
  .cvd button {
    padding: 0.25rem 0.7rem;
    font-size: 0.8rem;
    border-radius: 999px;
  }
  .cvd button.active {
    background: var(--accent);
    border-color: var(--accent);
    color: #fff;
  }
  .grid2 {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
    gap: 1.1rem;
  }
  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 1rem 1.2rem;
  }
  .card h2 {
    margin: 0 0 0.8rem;
    font-size: 1.05rem;
  }
  .card h2 small {
    color: var(--muted);
    font-weight: 400;
  }
  .bar {
    display: grid;
    grid-template-columns: 9rem 1fr 2.5rem;
    gap: 0.6rem;
    align-items: center;
    font-size: 0.85rem;
    margin-bottom: 0.45rem;
  }
  .track {
    height: 8px;
    background: var(--border);
    border-radius: 999px;
    overflow: hidden;
  }
  .fill {
    height: 100%;
    background: var(--accent);
    border-radius: 999px;
  }
  .themes {
    display: flex;
    flex-direction: column;
    gap: 0.8rem;
  }
</style>
