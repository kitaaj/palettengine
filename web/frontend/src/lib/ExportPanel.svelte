<script lang="ts">
  import { exportPalette } from "./api";

  let {
    hexes,
    formats,
  }: { hexes: string[]; formats: string[] } = $props();

  let format = $state("css");
  let rolesTheme = $state("none");
  let preview = $state("");
  let copied = $state(false);

  const BINARY = new Set(["ase"]);

  $effect(() => {
    // Re-render the preview whenever inputs change (skip binary formats).
    const f = format,
      rt = rolesTheme,
      hx = hexes;
    if (BINARY.has(f)) {
      preview = "(binary format — use Download)";
      return;
    }
    let cancelled = false;
    exportPalette(hx, f, rt)
      .then(async (blob) => {
        if (!cancelled) preview = await blob.text();
      })
      .catch((e) => {
        if (!cancelled) preview = `error: ${e.message}`;
      });
    return () => {
      cancelled = true;
    };
  });

  async function copy() {
    await navigator.clipboard.writeText(preview);
    copied = true;
    setTimeout(() => (copied = false), 1200);
  }

  async function download() {
    const blob = await exportPalette(hexes, format, rolesTheme);
    const ext: Record<string, string> = {
      json: "json",
      css: "css",
      scss: "scss",
      tailwind: "js",
      tokens: "tokens.json",
      svg: "svg",
      gpl: "gpl",
      ase: "ase",
    };
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `palette.${ext[format] ?? "txt"}`;
    a.click();
    URL.revokeObjectURL(a.href);
  }
</script>

<div class="panel">
  <div class="controls">
    <label>
      format
      <select bind:value={format}>
        {#each formats as f (f)}
          <option value={f}>{f}</option>
        {/each}
      </select>
    </label>
    <label>
      roles
      <select bind:value={rolesTheme}>
        <option value="none">none</option>
        <option value="light">light</option>
        <option value="dark">dark</option>
      </select>
    </label>
    <button onclick={copy} disabled={BINARY.has(format)}>{copied ? "copied!" : "copy"}</button>
    <button onclick={download}>download</button>
  </div>
  <pre>{preview}</pre>
</div>

<style>
  .panel {
    display: flex;
    flex-direction: column;
    gap: 0.6rem;
  }
  .controls {
    display: flex;
    gap: 0.7rem;
    align-items: end;
    flex-wrap: wrap;
  }
  label {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    font-size: 0.8rem;
    color: var(--muted);
  }
  pre {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 0.9rem;
    max-height: 300px;
    overflow: auto;
    font-size: 0.8rem;
    margin: 0;
  }
</style>
