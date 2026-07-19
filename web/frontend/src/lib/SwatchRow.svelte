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
    onEdit,
  }: {
    swatches: Swatch[];
    /** Hexes to actually paint (may be CVD-simulated versions). */
    display: string[];
    /** Server-computed WCAG overlay colors; null entries fall back to the local estimate. */
    textOn?: (string | null)[];
    onToggleLock: (i: number) => void;
    onEdit: (i: number, hex: string) => void;
  } = $props();

  let copiedIndex = $state(-1);

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
</script>

<div class="row" role="list">
  {#each swatches as sw, i (i)}
    <div
      class="swatch"
      class:locked={sw.locked}
      role="listitem"
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
        <label class="action" title="Edit color" aria-label="Edit color">
          <Icon name="droplet" />
          <input
            type="color"
            value={sw.hex}
            oninput={(e) => onEdit(i, (e.target as HTMLInputElement).value)}
          />
        </label>
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
    .row :global(.swatch),
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
    transition: flex-grow 160ms ease;
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
  .action input {
    position: absolute;
    width: 0;
    height: 0;
    opacity: 0;
  }
  .hex {
    font-family: ui-monospace, "Cascadia Code", Consolas, monospace;
    font-size: 0.86rem;
    letter-spacing: 0.03em;
    user-select: all;
  }
</style>
