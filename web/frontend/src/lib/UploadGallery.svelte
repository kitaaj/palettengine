<script lang="ts">
  import { extractPalette } from "./api";
  import { readableOn } from "./contrast";
  import Icon from "./Icon.svelte";

  let {
    size = 5,
    onSend,
  }: {
    /** Number of swatches to pull from each image. */
    size?: number;
    /** Load a card's colors into the main editor. */
    onSend?: (hexes: string[]) => void;
  } = $props();

  interface Card {
    id: number;
    name: string;
    thumb: string;
    colors: string[];
    busy: boolean;
    error: string;
  }

  let cards = $state<Card[]>([]);
  let dragActive = $state(false);
  let copiedId = $state(-1);
  let nextId = 0;

  async function addFile(file: File) {
    if (!file.type.startsWith("image/")) return;
    const card: Card = {
      id: nextId++,
      name: file.name,
      thumb: URL.createObjectURL(file),
      colors: [],
      busy: true,
      error: "",
    };
    // Newest first, matching the reference board.
    cards = [card, ...cards];
    try {
      const doc = await extractPalette(file, { size });
      update(card.id, { colors: doc.colors.map((c) => c.hex), busy: false });
    } catch (e) {
      update(card.id, { busy: false, error: e instanceof Error ? e.message : String(e) });
    }
  }

  function update(id: number, patch: Partial<Card>) {
    cards = cards.map((c) => (c.id === id ? { ...c, ...patch } : c));
  }

  function onPick(files: FileList | null) {
    if (!files) return;
    for (const f of Array.from(files)) addFile(f);
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    dragActive = false;
    onPick(e.dataTransfer?.files ?? null);
  }

  function remove(id: number) {
    const card = cards.find((c) => c.id === id);
    if (card) URL.revokeObjectURL(card.thumb);
    cards = cards.filter((c) => c.id !== id);
  }

  async function copyAll(card: Card) {
    if (!card.colors.length) return;
    try {
      await navigator.clipboard.writeText(card.colors.join(", "));
      copiedId = card.id;
      setTimeout(() => (copiedId = -1), 1100);
    } catch {
      /* clipboard unavailable */
    }
  }

  async function copyHex(hex: string) {
    try {
      await navigator.clipboard.writeText(hex);
    } catch {
      /* clipboard unavailable */
    }
  }

  function baseName(name: string): string {
    return name.replace(/\.[^.]+$/, "") || "palette";
  }

  // Hard ceiling on the exported width (8K). We never upscale past the source
  // image's own resolution, so a small photo exports small; this only caps
  // genuinely huge originals.
  const MAX_WIDTH = 7680;
  // WebP at this quality is visually lossless for photos at a fraction of PNG's size.
  const QUALITY = 0.92;

  /** Encode the canvas, preferring WebP, then JPEG, then PNG (whatever the browser supports). */
  async function encode(canvas: HTMLCanvasElement): Promise<{ blob: Blob; ext: string } | null> {
    for (const [type, ext] of [
      ["image/webp", "webp"],
      ["image/jpeg", "jpg"],
      ["image/png", "png"],
    ] as const) {
      const blob = await new Promise<Blob | null>((res) => canvas.toBlob(res, type, QUALITY));
      // A browser that can't produce `type` silently falls back to PNG; the
      // type check confirms we actually got the format we asked for.
      if (blob && blob.type === type) return { blob, ext };
    }
    return null;
  }

  /** Render the card (image above, palette strip below) and download it as a compressed image. */
  async function downloadCard(card: Card) {
    if (!card.colors.length) return;
    const img = new Image();
    img.src = card.thumb;
    try {
      await img.decode();
    } catch {
      /* draw whatever decoded; a broken image just yields the strip */
    }

    // Match the source resolution (no upscaling), capped at 8K.
    const w = Math.min(MAX_WIDTH, img.naturalWidth || 2000);
    const aspect = img.naturalWidth ? img.naturalHeight / img.naturalWidth : 0.625;
    const imgH = img.naturalWidth ? Math.round(w * aspect) : 0;
    const stripH = Math.round(w * 0.12);

    const canvas = document.createElement("canvas");
    canvas.width = w;
    canvas.height = imgH + stripH;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = "high";

    if (imgH) ctx.drawImage(img, 0, 0, w, imgH);

    const n = card.colors.length;
    const bw = w / n;
    card.colors.forEach((hex, i) => {
      ctx.fillStyle = hex;
      // +1 avoids hairline seams from fractional block widths.
      ctx.fillRect(Math.floor(i * bw), imgH, Math.ceil(bw) + 1, stripH);
    });

    const out = await encode(canvas);
    if (!out) return;
    const a = document.createElement("a");
    a.href = URL.createObjectURL(out.blob);
    a.download = `${baseName(card.name)}-palette.${out.ext}`;
    a.click();
    URL.revokeObjectURL(a.href);
  }
</script>

<div class="gallery">
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <label
    class="dropzone"
    class:active={dragActive}
    ondragover={(e) => {
      e.preventDefault();
      dragActive = true;
    }}
    ondragleave={() => (dragActive = false)}
    ondrop={onDrop}
  >
    <input
      type="file"
      accept="image/*"
      multiple
      onchange={(e) => {
        onPick((e.target as HTMLInputElement).files);
        (e.target as HTMLInputElement).value = "";
      }}
    />
    <span class="dz-icon"><Icon name="image" size={20} /></span>
    <span class="dz-title">Drop images here, or click to browse</span>
    <span class="dz-hint">Each image becomes a card with its extracted palette attached below.</span>
  </label>

  {#if cards.length}
    <div class="grid">
      {#each cards as card (card.id)}
        <figure class="card">
          <div class="thumb-wrap">
            <img class="thumb" src={card.thumb} alt={card.name} />
            <button
              class="remove"
              title="Remove"
              aria-label="Remove image"
              onclick={() => remove(card.id)}
            >
              <Icon name="x" size={13} />
            </button>
            {#if card.busy}
              <span class="overlay">Extracting palette…</span>
            {/if}
          </div>

          {#if card.error}
            <p class="card-error" role="alert">{card.error}</p>
          {:else}
            <div class="strip" class:pending={card.busy}>
              {#each card.colors as hex (hex)}
                <button
                  class="chip"
                  style="background:{hex}; color:{readableOn(hex)}"
                  title="Copy {hex}"
                  onclick={() => copyHex(hex)}
                >
                  <span class="chip-hex">{hex}</span>
                </button>
              {/each}
            </div>
          {/if}

          <figcaption class="foot">
            <span class="name" title={card.name}>{card.name}</span>
            <span class="foot-actions">
              <button
                class="ghost"
                disabled={!card.colors.length}
                title="Copy all hex values"
                aria-label="Copy all hex values"
                onclick={() => copyAll(card)}
              >
                <Icon name={copiedId === card.id ? "check" : "copy"} size={13} />
              </button>
              <button
                class="ghost"
                disabled={!card.colors.length}
                title="Download card as an image"
                aria-label="Download card as image"
                onclick={() => downloadCard(card)}
              >
                <Icon name="download" size={13} />
              </button>
              {#if onSend}
                <button
                  class="ghost"
                  disabled={!card.colors.length}
                  title="Load into the editor above"
                  onclick={() => onSend?.(card.colors)}
                >
                  <Icon name="sliders" size={13} /> Edit
                </button>
              {/if}
            </span>
          </figcaption>
        </figure>
      {/each}
    </div>
  {/if}
</div>

<style>
  .gallery {
    display: flex;
    flex-direction: column;
    gap: 1.1rem;
  }
  .dropzone {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.35rem;
    text-align: center;
    padding: 1.6rem 1rem;
    border: 1.5px dashed var(--border);
    border-radius: var(--radius);
    background: var(--surface);
    cursor: pointer;
    transition:
      border-color 130ms ease,
      background 130ms ease;
  }
  .dropzone:hover,
  .dropzone.active {
    border-color: var(--accent);
    background: color-mix(in srgb, var(--accent) 5%, var(--surface));
  }
  .dropzone input {
    display: none;
  }
  .dz-icon {
    color: var(--accent);
    display: inline-flex;
  }
  .dz-title {
    font-weight: 600;
    font-size: 0.9rem;
  }
  .dz-hint {
    font-size: 0.78rem;
    color: var(--muted);
    max-width: 30rem;
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(min(260px, 100%), 1fr));
    gap: 1.1rem;
  }
  .card {
    margin: 0;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    overflow: hidden;
    box-shadow: var(--shadow-sm);
    display: flex;
    flex-direction: column;
  }
  .thumb-wrap {
    position: relative;
    aspect-ratio: 16 / 10;
    background: var(--surface-2);
  }
  .thumb {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }
  .remove {
    position: absolute;
    top: 0.5rem;
    right: 0.5rem;
    width: 1.7rem;
    height: 1.7rem;
    padding: 0;
    border-radius: 50%;
    background: rgb(0 0 0 / 0.55);
    border: none;
    color: #fff;
    display: grid;
    place-items: center;
    box-shadow: none;
    opacity: 0;
    transition: opacity 130ms ease;
  }
  .card:hover .remove,
  .remove:focus-visible {
    opacity: 1;
  }
  .remove:hover {
    background: rgb(0 0 0 / 0.72);
  }
  .overlay {
    position: absolute;
    inset: 0;
    display: grid;
    place-items: center;
    background: rgb(0 0 0 / 0.45);
    color: #fff;
    font-size: 0.78rem;
    font-weight: 600;
  }
  .strip {
    display: flex;
    height: 46px;
  }
  .strip.pending {
    min-height: 46px;
    background: var(--surface-2);
  }
  .chip {
    flex: 1;
    border: none;
    border-radius: 0;
    box-shadow: none;
    padding: 0;
    display: flex;
    align-items: flex-end;
    justify-content: center;
    cursor: pointer;
  }
  .chip-hex {
    font-family: ui-monospace, "Cascadia Code", Consolas, monospace;
    font-size: 0.6rem;
    letter-spacing: 0.02em;
    padding-bottom: 0.32rem;
    opacity: 0;
    transition: opacity 120ms ease;
  }
  .chip:hover .chip-hex,
  .chip:focus-visible .chip-hex {
    opacity: 1;
  }
  .card-error {
    margin: 0;
    padding: 0.7rem 0.85rem;
    color: var(--danger);
    font-size: 0.78rem;
  }
  .foot {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.55rem 0.7rem 0.6rem;
  }
  .name {
    flex: 1;
    min-width: 0;
    font-size: 0.78rem;
    font-weight: 550;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .foot-actions {
    display: inline-flex;
    gap: 0.3rem;
    flex-shrink: 0;
  }
  .foot-actions .ghost {
    font-size: 0.74rem;
    color: var(--muted);
    padding: 0.3rem 0.45rem;
  }
  .foot-actions .ghost:hover:not(:disabled) {
    color: var(--accent);
  }
</style>
