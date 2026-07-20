<script module lang="ts">
  export interface Swatch {
    hex: string;
    locked: boolean;
  }
</script>

<script lang="ts">
  import Icon from "./Icon.svelte";

  let {
    swatches,
    display,
    textOn = [],
    onToggleLock,
    onOpenEditor,
    onReorder,
  }: {
    swatches: Swatch[];
    /** Hexes to actually paint (may be CVD-simulated versions). */
    display: string[];
    /** Server-computed WCAG overlay colors; null entries fall back to the local estimate. */
    textOn?: (string | null)[];
    onToggleLock: (i: number) => void;
    onOpenEditor: (i: number) => void;
    onReorder: (from: number, to: number) => void;
  } = $props();

  let copiedIndex = $state(-1);
  let dragFrom = $state(-1);
  let dragOver = $state(-1);

  /** Local fallback when no server value applies (e.g. mid-edit or CVD preview). */
  function estimateTextOn(hex: string): string {
    const n = parseInt(hex.slice(1), 16);
    const lum = 0.2126 * ((n >> 16) & 255) + 0.7152 * ((n >> 8) & 255) + 0.0722 * (n & 255);
    return lum > 140 ? "rgb(0 0 0 / 0.82)" : "rgb(255 255 255 / 0.92)";
  }

  function overlayColor(i: number): string {
    return textOn[i] ?? estimateTextOn(display[i] ?? swatches[i].hex);
  }

  async function copyHex(i: number) {
    try {
      await navigator.clipboard.writeText(swatches[i].hex);
      copiedIndex = i;
      setTimeout(() => (copiedIndex = -1), 1100);
    } catch {
      /* clipboard unavailable */
    }
  }

  function drop(i: number) {
    if (dragFrom >= 0 && dragFrom !== i) onReorder(dragFrom, i);
    dragFrom = -1;
    dragOver = -1;
  }
</script>

<div class="row" role="list">
  {#each swatches as sw, i (i)}
    <div
      class="swatch"
      class:locked={sw.locked}
      class:drag-over={dragOver === i && dragFrom !== i}
      role="listitem"
      draggable="true"
      ondragstart={(e) => {
        dragFrom = i;
        e.dataTransfer?.setData("text/plain", String(i));
        if (e.dataTransfer) e.dataTransfer.effectAllowed = "move";
      }}
      ondragover={(e) => {
        e.preventDefault();
        dragOver = i;
      }}
      ondragleave={() => {
        if (dragOver === i) dragOver = -1;
      }}
      ondrop={(e) => {
        e.preventDefault();
        drop(i);
      }}
      ondragend={() => {
        dragFrom = -1;
        dragOver = -1;
      }}
      style="background:{display[i] ?? sw.hex}; color:{overlayColor(i)}"
    >
      <div class="actions">
        <button
          class="action lock"
          title={sw.locked ? "Unlock color" : "Lock color"}
          aria-label={sw.locked ? "Unlock color" : "Lock color"}
          onclick={() => onToggleLock(i)}
        >
          <Icon name={sw.locked ? "lock" : "unlock"} />
        </button>
        <button
          class="action"
          title="Copy hex"
          aria-label="Copy hex value"
          onclick={() => copyHex(i)}
        >
          <Icon name={copiedIndex === i ? "check" : "copy"} />
        </button>
        <button
          class="action"
          title="Edit in OKLCH"
          aria-label="Edit color"
          onclick={() => onOpenEditor(i)}
        >
          <Icon name="sliders" />
        </button>
      </div>
      <span class="hex">{sw.hex}</span>
    </div>
  {/each}
</div>

<style>
  .row {
    display: flex;
    min-height: 260px;
    border-radius: var(--radius);
    overflow: hidden;
    box-shadow: var(--shadow-md);
  }
  @media (max-width: 640px) {
    .row {
      flex-direction: column;
    }
    .swatch {
      flex-direction: row;
      justify-content: space-between;
      padding: 0.7rem 1rem;
      min-height: 3.4rem;
    }
    .actions {
      flex-direction: row;
      opacity: 1;
      transform: none;
    }
  }
  .swatch {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: flex-end;
    gap: 0.55rem;
    padding: 1rem 0.4rem 1.1rem;
    cursor: grab;
    transition: filter 140ms ease;
  }
  .swatch:active {
    cursor: grabbing;
  }
  .swatch.drag-over {
    filter: brightness(1.12);
    outline: 2px dashed rgb(127 127 127 / 0.6);
    outline-offset: -6px;
  }
  .actions {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
    opacity: 0;
    transform: translateY(4px);
    transition:
      opacity 140ms ease,
      transform 140ms ease;
  }
  .swatch:hover .actions,
  .swatch:focus-within .actions {
    opacity: 1;
    transform: none;
  }
  /* A locked swatch always shows its lock state, even without hover. */
  .swatch.locked .actions {
    opacity: 1;
    transform: none;
  }
  .action {
    background: transparent;
    border: none;
    box-shadow: none;
    color: inherit;
    padding: 0.42rem;
    border-radius: var(--radius-sm);
    display: inline-flex;
    cursor: pointer;
  }
  .action:hover {
    background: rgb(127 127 127 / 0.22);
    border: none;
  }
  .hex {
    font-family: ui-monospace, "Cascadia Code", Consolas, monospace;
    font-size: 0.86rem;
    letter-spacing: 0.03em;
    user-select: all;
  }
</style>
