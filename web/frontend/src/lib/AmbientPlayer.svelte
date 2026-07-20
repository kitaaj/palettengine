<script lang="ts">
  import { onDestroy } from "svelte";
  import Icon from "./Icon.svelte";
  import { samplePalette, type Lab } from "./livePalette";

  let {
    file,
    onApply,
    onClose,
  }: { file: File; onApply: (hexes: string[]) => void; onClose: () => void } = $props();

  // Tiny sample buffer (16:9). Big enough for stable colors, small enough to be ~free.
  const SW = 32;
  const SH = 18;
  const MIN_INTERVAL = 90; // ms between samples => ~11 fps of palette work

  let video: HTMLVideoElement;
  let glow: HTMLCanvasElement;
  let hexes = $state<string[]>([]);
  let playing = $state(false);
  const url = URL.createObjectURL(file);

  let ctx: CanvasRenderingContext2D | null = null;
  let prev: Lab[] | null = null;
  let lastTs = 0;
  let rafId = 0;
  let rvfc = 0;

  const hasRVFC =
    typeof HTMLVideoElement !== "undefined" && "requestVideoFrameCallback" in HTMLVideoElement.prototype;

  function processFrame(now: number) {
    if (!ctx || !video || video.readyState < 2) return;
    if (now - lastTs < MIN_INTERVAL) return;
    lastTs = now;
    // One tiny draw feeds both the glow (this canvas, CSS-blurred) and the palette.
    ctx.drawImage(video, 0, 0, SW, SH);
    const data = ctx.getImageData(0, 0, SW, SH).data;
    const { centers, hexes: h } = samplePalette(data, 5, prev ?? undefined);
    prev = centers;
    hexes = h;
  }

  // requestVideoFrameCallback only fires for newly displayed frames — it naturally
  // stops when the video is paused, ended, or the tab is hidden. That's the whole
  // performance story: no work happens unless a fresh frame is actually on screen.
  function scheduleRVFC() {
    rvfc = video.requestVideoFrameCallback((now) => {
      processFrame(now);
      scheduleRVFC();
    });
  }

  // Fallback loop guards on paused/hidden so idle cost is a timestamp compare.
  function loopRAF(now: number) {
    if (!video.paused && !video.ended && !document.hidden) processFrame(now);
    rafId = requestAnimationFrame(loopRAF);
  }

  function start() {
    if (hasRVFC) scheduleRVFC();
    else rafId = requestAnimationFrame(loopRAF);
  }

  function onLoaded() {
    const c = glow.getContext("2d", { willReadFrequently: true });
    ctx = c;
    start();
  }

  function onKeydown(e: KeyboardEvent) {
    if (e.key === "Escape") onClose();
  }

  onDestroy(() => {
    if (rafId) cancelAnimationFrame(rafId);
    if (rvfc && video) video.cancelVideoFrameCallback?.(rvfc);
    URL.revokeObjectURL(url);
  });
</script>

<svelte:window onkeydown={onKeydown} />

<div
  class="backdrop"
  role="presentation"
  onclick={(e) => e.target === e.currentTarget && onClose()}
>
  <div class="ambient" role="dialog" aria-modal="true" aria-label="Ambient mode">
    <div class="head">
      <span class="title"><Icon name="film" size={14} /> Ambient mode <em>live</em></span>
      <button class="ghost" onclick={onClose} aria-label="Close"><Icon name="x" /></button>
    </div>

    <div class="stage">
      <canvas bind:this={glow} class="glow" width={SW} height={SH}></canvas>
      <!-- svelte-ignore a11y_media_has_caption -->
      <video
        bind:this={video}
        src={url}
        class="player"
        controls
        autoplay
        muted
        loop
        playsinline
        onloadeddata={onLoaded}
        onplay={() => (playing = true)}
        onpause={() => (playing = false)}
      ></video>
    </div>

    <div class="strip" aria-label="Live palette">
      {#each hexes as h, i (i)}
        <div class="cell" style="background:{h}">
          <span>{h}</span>
        </div>
      {/each}
      {#if !hexes.length}
        <div class="cell placeholder"><span>sampling…</span></div>
      {/if}
    </div>

    <div class="foot">
      <span class="hint">
        {playing ? "Colors follow playback in real time." : "Press play to begin."}
      </span>
      <button
        class="primary"
        onclick={() => hexes.length && onApply(hexes)}
        disabled={!hexes.length}
        title="Send the current live palette to the editor"
      >
        <Icon name="check" /> Use current palette
      </button>
    </div>
  </div>
</div>

<style>
  .backdrop {
    position: fixed;
    inset: 0;
    background: #05070a;
    display: grid;
    place-items: center;
    z-index: 50;
  }
  .ambient {
    width: min(880px, calc(100vw - 2rem));
    display: flex;
    flex-direction: column;
    gap: 0.9rem;
    padding: 1rem 1.1rem 1.2rem;
  }
  .head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    color: #e8eaee;
  }
  .title {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    font-weight: 600;
  }
  .title em {
    font-style: normal;
    font-size: 0.65rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #ff5470;
    border: 1px solid #ff5470;
    border-radius: 999px;
    padding: 0.05rem 0.45rem;
  }
  .head .ghost {
    background: transparent;
    border-color: transparent;
    color: #e8eaee;
    box-shadow: none;
  }
  .head .ghost:hover {
    background: rgb(255 255 255 / 0.1);
  }

  .stage {
    position: relative;
    display: grid;
    place-items: center;
    padding: 4%;
  }
  /* The tiny sampled frame, scaled up and heavily blurred by the GPU: the ambient glow. */
  .glow {
    position: absolute;
    inset: -2%;
    width: 104%;
    height: 104%;
    filter: blur(58px) saturate(1.5);
    opacity: 0.75;
    z-index: 0;
    border-radius: 24px;
    /* image-rendering hint is irrelevant once blurred, but avoids a sharp first frame */
    image-rendering: auto;
  }
  .player {
    position: relative;
    z-index: 1;
    max-width: 100%;
    max-height: 62vh;
    border-radius: 12px;
    background: #000;
    box-shadow: 0 10px 40px rgb(0 0 0 / 0.5);
  }

  .strip {
    display: flex;
    height: 54px;
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 4px 18px rgb(0 0 0 / 0.4);
  }
  .cell {
    flex: 1;
    display: grid;
    place-items: center;
    transition: background 120ms linear;
  }
  .cell span {
    font-family: ui-monospace, Consolas, monospace;
    font-size: 0.72rem;
    color: rgb(255 255 255 / 0.9);
    mix-blend-mode: difference;
  }
  .cell.placeholder {
    background: #1a1d22;
  }

  .foot {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
  }
  .hint {
    color: #8a93a2;
    font-size: 0.82rem;
  }
</style>
