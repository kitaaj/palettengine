<script lang="ts">
  import { exportPalette } from "./api";
  import Icon from "./Icon.svelte";

  let { hexes, formats }: { hexes: string[]; formats: string[] } = $props();

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
      preview = "Binary format — use Download.";
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
    setTimeout(() => (copied = false), 1100);
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
      <span class="label">Format</span>
      <select bind:value={format}>
        {#each formats as f (f)}
          <option value={f}>{f}</option>
        {/each}
      </select>
    </label>
    <label>
      <span class="label">Roles</span>
      <select bind:value={rolesTheme}>
        <option value="none">none</option>
        <option value="light">light</option>
        <option value="dark">dark</option>
      </select>
    </label>
    <div class="spacer"></div>
    <button onclick={copy} disabled={BINARY.has(format)} title="Copy to clipboard">
      <Icon name={copied ? "check" : "copy"} />
      {copied ? "Copied" : "Copy"}
    </button>
    <button onclick={download} title="Download file">
      <Icon name="download" />
      Download
    </button>
  </div>
  <pre>{preview}</pre>
</div>

<style>
  .panel {
    display: flex;
    flex-direction: column;
    gap: 0.7rem;
  }
  .controls {
    display: flex;
    gap: 0.7rem;
    align-items: end;
    flex-wrap: wrap;
  }
  .spacer {
    flex: 1;
  }
  label {
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
  }
  pre {
    background: var(--surface-2);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 0.85rem 1rem;
    max-height: 300px;
    overflow: auto;
    font-size: 0.78rem;
    line-height: 1.55;
    margin: 0;
  }
</style>
