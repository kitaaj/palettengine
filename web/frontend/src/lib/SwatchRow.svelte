<script module lang="ts">
  export interface Swatch {
    hex: string;
    locked: boolean;
  }
</script>

<script lang="ts">
  let {
    swatches,
    display,
    onToggleLock,
    onEdit,
  }: {
    swatches: Swatch[];
    /** Hexes to actually paint (may be CVD-simulated versions). */
    display: string[];
    onToggleLock: (i: number) => void;
    onEdit: (i: number, hex: string) => void;
  } = $props();

  function textColorOn(hex: string): string {
    // Quick relative-luminance estimate for label legibility.
    const n = parseInt(hex.slice(1), 16);
    const r = (n >> 16) & 255,
      g = (n >> 8) & 255,
      b = n & 255;
    const lum = 0.2126 * r + 0.7152 * g + 0.0722 * b;
    return lum > 140 ? "#111" : "#fff";
  }

  async function copyHex(hex: string) {
    try {
      await navigator.clipboard.writeText(hex);
    } catch {
      /* clipboard unavailable; ignore */
    }
  }
</script>

<div class="row">
  {#each swatches as sw, i (i)}
    <div class="swatch" style="background:{display[i] ?? sw.hex}; color:{textColorOn(display[i] ?? sw.hex)}">
      <button
        class="lock"
        title={sw.locked ? "unlock" : "lock"}
        aria-label={sw.locked ? "unlock color" : "lock color"}
        onclick={() => onToggleLock(i)}
      >
        {sw.locked ? "🔒" : "🔓"}
      </button>
      <button class="hex" title="copy hex" onclick={() => copyHex(sw.hex)}>{sw.hex}</button>
      <label class="edit" title="edit color">
        ✎
        <input
          type="color"
          value={sw.hex}
          oninput={(e) => onEdit(i, (e.target as HTMLInputElement).value)}
        />
      </label>
    </div>
  {/each}
</div>

<style>
  .row {
    display: flex;
    min-height: 240px;
    border-radius: 14px;
    overflow: hidden;
  }
  .swatch {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: flex-end;
    gap: 0.4rem;
    padding: 1rem 0.4rem;
    position: relative;
  }
  .swatch button,
  .swatch .edit {
    background: none;
    border: none;
    color: inherit;
    opacity: 0.85;
  }
  .lock {
    position: absolute;
    top: 0.6rem;
    right: 0.6rem;
    font-size: 1rem;
  }
  .hex {
    font-family: ui-monospace, Consolas, monospace;
    font-size: 0.95rem;
    letter-spacing: 0.02em;
  }
  .edit {
    cursor: pointer;
    font-size: 0.9rem;
  }
  .edit input {
    width: 0;
    height: 0;
    opacity: 0;
    position: absolute;
  }
</style>
