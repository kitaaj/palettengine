<script lang="ts">
  import Icon from "./Icon.svelte";
  import { hexToOklch, isClamped, oklchToHex } from "./oklch";

  let {
    hex,
    onApply,
    onClose,
  }: { hex: string; onApply: (hex: string) => void; onClose: () => void } = $props();

  const initial = hexToOklch(hex);
  let l = $state(initial.l);
  let c = $state(initial.c);
  let h = $state(initial.h);
  let hexInput = $state(hex);

  const currentHex = $derived(oklchToHex({ l, c, h }));
  const clamped = $derived(isClamped({ l, c, h }));

  function commitHexInput() {
    const v = hexInput.trim();
    if (/^#?[0-9a-f]{6}$/i.test(v)) {
      const parsed = hexToOklch(v.startsWith("#") ? v : `#${v}`);
      l = parsed.l;
      c = parsed.c;
      h = parsed.h;
    } else {
      hexInput = currentHex;
    }
  }

  function onKeydown(e: KeyboardEvent) {
    if (e.key === "Escape") onClose();
    if (e.key === "Enter" && !(e.target instanceof HTMLInputElement && e.target.type === "text"))
      onApply(currentHex);
  }
</script>

<svelte:window onkeydown={onKeydown} />

<div
  class="backdrop"
  role="presentation"
  onclick={(e) => {
    if (e.target === e.currentTarget) onClose();
  }}
>
  <div class="dialog" role="dialog" aria-modal="true" aria-label="Edit color">
    <div class="head">
      <span class="title"><Icon name="sliders" size={14} /> Edit color</span>
      <button class="ghost" onclick={onClose} aria-label="Close"><Icon name="x" /></button>
    </div>

    <div class="preview-row">
      <div class="preview" style="background:{currentHex}"></div>
      <div class="preview-meta">
        <input
          class="hex-input"
          type="text"
          bind:value={hexInput}
          onblur={commitHexInput}
          onkeydown={(e) => e.key === "Enter" && commitHexInput()}
          spellcheck="false"
          aria-label="Hex value"
        />
        <span class="oklch-readout">
          oklch({l.toFixed(3)} {c.toFixed(3)} {h.toFixed(1)})
        </span>
        {#if clamped}
          <span class="clamp-note">chroma clamped to sRGB gamut</span>
        {/if}
      </div>
    </div>

    <label>
      <span class="label">Lightness <b>{l.toFixed(3)}</b></span>
      <input
        type="range"
        min="0.02"
        max="0.98"
        step="0.001"
        bind:value={l}
        oninput={() => (hexInput = currentHex)}
        style="background: linear-gradient(to right, {oklchToHex(
          { l: 0.05, c, h },
        )}, {oklchToHex({ l: 0.5, c, h })}, {oklchToHex({ l: 0.95, c, h })})"
      />
    </label>
    <label>
      <span class="label">Chroma <b>{c.toFixed(3)}</b></span>
      <input
        type="range"
        min="0"
        max="0.35"
        step="0.001"
        bind:value={c}
        oninput={() => (hexInput = currentHex)}
        style="background: linear-gradient(to right, {oklchToHex(
          { l, c: 0, h },
        )}, {oklchToHex({ l, c: 0.35, h })})"
      />
    </label>
    <label>
      <span class="label">Hue <b>{h.toFixed(1)}°</b></span>
      <input
        type="range"
        min="0"
        max="360"
        step="0.5"
        bind:value={h}
        oninput={() => (hexInput = currentHex)}
        style="background: linear-gradient(to right, {[0, 60, 120, 180, 240, 300, 360]
          .map((deg) => oklchToHex({ l, c, h: deg }))
          .join(', ')})"
      />
    </label>

    <div class="actions">
      <button onclick={onClose}>Cancel</button>
      <button class="primary" onclick={() => onApply(currentHex)}>
        <Icon name="check" /> Apply
      </button>
    </div>
  </div>
</div>

<style>
  .backdrop {
    position: fixed;
    inset: 0;
    background: rgb(0 0 0 / 0.45);
    display: grid;
    place-items: center;
    z-index: 40;
  }
  .dialog {
    width: min(420px, calc(100vw - 2rem));
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    box-shadow: var(--shadow-md);
    padding: 1rem 1.1rem 1.1rem;
    display: flex;
    flex-direction: column;
    gap: 0.85rem;
  }
  .head {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .title {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    font-weight: 600;
    font-size: 0.9rem;
  }
  .preview-row {
    display: flex;
    gap: 0.9rem;
    align-items: center;
  }
  .preview {
    width: 74px;
    height: 74px;
    border-radius: var(--radius-sm);
    border: 1px solid var(--border);
    flex-shrink: 0;
  }
  .preview-meta {
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
    min-width: 0;
  }
  .hex-input {
    font-family: ui-monospace, Consolas, monospace;
    width: 8.5rem;
  }
  .oklch-readout {
    font-family: ui-monospace, Consolas, monospace;
    font-size: 0.74rem;
    color: var(--muted);
  }
  .clamp-note {
    font-size: 0.72rem;
    color: var(--warn);
  }
  label {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
  }
  label .label b {
    color: var(--text);
    font-variant-numeric: tabular-nums;
    margin-left: 0.3rem;
  }
  input[type="range"] {
    -webkit-appearance: none;
    appearance: none;
    height: 14px;
    border-radius: 999px;
    border: 1px solid var(--border);
    outline-offset: 3px;
  }
  input[type="range"]::-webkit-slider-thumb {
    -webkit-appearance: none;
    appearance: none;
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: #fff;
    border: 2px solid rgb(0 0 0 / 0.35);
    box-shadow: var(--shadow-sm);
    cursor: pointer;
  }
  input[type="range"]::-moz-range-thumb {
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: #fff;
    border: 2px solid rgb(0 0 0 / 0.35);
    cursor: pointer;
  }
  .actions {
    display: flex;
    justify-content: end;
    gap: 0.6rem;
    margin-top: 0.2rem;
  }
</style>
