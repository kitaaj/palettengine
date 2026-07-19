<script lang="ts">
  let { hexes, matrix }: { hexes: string[]; matrix: number[][] } = $props();

  function grade(ratio: number): { label: string; cls: string } {
    if (ratio >= 7) return { label: "AAA", cls: "aaa" };
    if (ratio >= 4.5) return { label: "AA", cls: "aa" };
    if (ratio >= 3) return { label: "AA+", cls: "large" }; // large text only
    return { label: "✕", cls: "fail" };
  }
</script>

<div class="wrap">
  <table>
    <thead>
      <tr>
        <th></th>
        {#each hexes as h (h)}
          <th><span class="dot" style="background:{h}"></span></th>
        {/each}
      </tr>
    </thead>
    <tbody>
      {#each matrix as row, i (i)}
        <tr>
          <th><span class="dot" style="background:{hexes[i]}"></span></th>
          {#each row as ratio, j (j)}
            {#if i === j}
              <td class="self">—</td>
            {:else}
              {@const g = grade(ratio)}
              <td class={g.cls} title="{ratio.toFixed(2)}:1">
                <b>{ratio.toFixed(1)}</b>
                <small>{g.label}</small>
              </td>
            {/if}
          {/each}
        </tr>
      {/each}
    </tbody>
  </table>
  <p class="legend">
    WCAG contrast: <span class="aaa">AAA ≥ 7</span> · <span class="aa">AA ≥ 4.5</span> ·
    <span class="large">large text ≥ 3</span> · <span class="fail">✕ fails</span>
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
    padding: 0.35rem 0.55rem;
    text-align: center;
    border: 1px solid var(--border);
    font-size: 0.85rem;
  }
  td small {
    display: block;
    font-size: 0.65rem;
    opacity: 0.75;
  }
  .dot {
    display: inline-block;
    width: 1.1rem;
    height: 1.1rem;
    border-radius: 50%;
    border: 1px solid var(--border);
  }
  .self {
    color: var(--muted);
  }
  .aaa {
    color: #16a34a;
  }
  .aa {
    color: #2563eb;
  }
  .large {
    color: #d97706;
  }
  .fail {
    color: #dc2626;
  }
  .legend {
    color: var(--muted);
    font-size: 0.8rem;
  }
  .legend span {
    font-weight: 600;
  }
</style>
