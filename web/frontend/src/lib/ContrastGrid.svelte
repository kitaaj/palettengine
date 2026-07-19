<script lang="ts">
  let { hexes, matrix }: { hexes: string[]; matrix: number[][] } = $props();

  function grade(ratio: number): { label: string; cls: string } {
    if (ratio >= 7) return { label: "AAA", cls: "aaa" };
    if (ratio >= 4.5) return { label: "AA", cls: "aa" };
    if (ratio >= 3) return { label: "LG", cls: "large" }; // large text only
    return { label: "—", cls: "fail" };
  }
</script>

<div class="wrap">
  <table>
    <thead>
      <tr>
        <th></th>
        {#each hexes as h, i (i)}
          <th><span class="dot" style="background:{h}" title={h}></span></th>
        {/each}
      </tr>
    </thead>
    <tbody>
      {#each matrix as row, i (i)}
        <tr>
          <th><span class="dot" style="background:{hexes[i]}" title={hexes[i]}></span></th>
          {#each row as ratio, j (j)}
            {#if i === j}
              <td class="self"></td>
            {:else}
              {@const g = grade(ratio)}
              <td title="{ratio.toFixed(2)}:1">
                <span class="ratio">{ratio.toFixed(1)}</span>
                <span class="badge {g.cls}">{g.label}</span>
              </td>
            {/if}
          {/each}
        </tr>
      {/each}
    </tbody>
  </table>
  <p class="legend">
    <span class="badge aaa">AAA</span> ≥ 7 &nbsp;·&nbsp;
    <span class="badge aa">AA</span> ≥ 4.5 &nbsp;·&nbsp;
    <span class="badge large">LG</span> large text ≥ 3 &nbsp;·&nbsp;
    <span class="badge fail">—</span> fails
  </p>
</div>

<style>
  .wrap {
    overflow-x: auto;
  }
  table {
    border-collapse: collapse;
  }
  th,
  td {
    padding: 0.4rem 0.5rem;
    text-align: center;
    border: 1px solid var(--border);
    font-size: 0.82rem;
  }
  .ratio {
    display: block;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
  }
  .dot {
    display: inline-block;
    width: 1.05rem;
    height: 1.05rem;
    border-radius: 50%;
    border: 1px solid var(--border);
  }
  .self {
    background: var(--surface-2);
  }
  .badge {
    display: inline-block;
    font-size: 0.62rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    border-radius: 999px;
    padding: 0.06rem 0.42rem;
    margin-top: 0.15rem;
  }
  .badge.aaa {
    color: var(--ok);
    background: color-mix(in srgb, var(--ok) 14%, transparent);
  }
  .badge.aa {
    color: var(--info);
    background: color-mix(in srgb, var(--info) 14%, transparent);
  }
  .badge.large {
    color: var(--warn);
    background: color-mix(in srgb, var(--warn) 14%, transparent);
  }
  .badge.fail {
    color: var(--danger);
    background: color-mix(in srgb, var(--danger) 12%, transparent);
  }
  .legend {
    color: var(--muted);
    font-size: 0.78rem;
    margin: 0.7rem 0 0;
  }
</style>
