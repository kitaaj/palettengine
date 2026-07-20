<script lang="ts">
  let { roles, theme }: { roles: Record<string, string>; theme: string } = $props();

  /** Black or white text for legibility on an arbitrary background color. */
  function readable(hex: string): string {
    const n = parseInt(hex.slice(1), 16);
    const lum = 0.2126 * ((n >> 16) & 255) + 0.7152 * ((n >> 8) & 255) + 0.0722 * (n & 255);
    return lum > 140 ? "#111418" : "#ffffff";
  }

  // Roles shown in the compact legend beneath the mock (label -> key).
  const legend: [string, string][] = [
    ["Bg", "background"],
    ["Surface", "surface"],
    ["Text", "text"],
    ["Primary", "primary"],
    ["Secondary", "secondary"],
    ["Accent", "accent"],
    ["Muted", "muted"],
  ];
</script>

<figure class="wrap">
  <!-- A believable mini-app rendered entirely from the palette's roles. -->
  <div class="app" style="background:{roles.background}; color:{roles.text}">
    <div class="chrome">
      <span class="dots">
        <i style="background:{roles.primary}"></i>
        <i style="background:{roles.secondary}"></i>
        <i style="background:{roles.accent}"></i>
      </span>
      <span class="tab" style="color:{roles.muted}">{theme}</span>
    </div>

    <div class="surface" style="background:{roles.surface}">
      <div class="row between">
        <span class="h" style="color:{roles.text}">Dashboard</span>
        <span class="badge" style="background:{roles.accent}; color:{readable(roles.accent)}">
          Live
        </span>
      </div>
      <p style="color:{roles.text}">Your projects at a glance.</p>
      <p class="muted" style="color:{roles.muted}">3 updates since yesterday</p>

      <div class="actions">
        <span class="btn" style="background:{roles.primary}; color:{readable(roles.primary)}">
          Primary
        </span>
        <span class="btn" style="background:{roles.secondary}; color:{readable(roles.secondary)}">
          Secondary
        </span>
        <span class="btn ghost" style="color:{roles.accent}; border-color:{roles.accent}">
          Ghost
        </span>
        <span class="link" style="color:{roles.accent}">Learn more →</span>
      </div>
    </div>
  </div>

  <figcaption class="legend">
    {#each legend as [label, key] (key)}
      <span class="swatch" title={roles[key]}>
        <i style="background:{roles[key]}"></i>
        {label}
      </span>
    {/each}
  </figcaption>
</figure>

<style>
  .wrap {
    margin: 0;
  }
  .app {
    border-radius: var(--radius);
    border: 1px solid var(--border);
    padding: 0.6rem;
    box-shadow: var(--shadow-sm);
    overflow: hidden;
  }
  .chrome {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.1rem 0.35rem 0.55rem;
  }
  .dots {
    display: inline-flex;
    gap: 0.32rem;
  }
  .dots i {
    width: 0.62rem;
    height: 0.62rem;
    border-radius: 50%;
    display: block;
  }
  .tab {
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: capitalize;
  }
  .surface {
    border-radius: var(--radius-sm);
    padding: 0.85rem 0.95rem 0.95rem;
  }
  .row.between {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .h {
    font-size: 1rem;
    font-weight: 700;
  }
  .badge {
    font-size: 0.62rem;
    font-weight: 700;
    letter-spacing: 0.03em;
    border-radius: 999px;
    padding: 0.1rem 0.5rem;
  }
  p {
    margin: 0.45rem 0 0;
    font-size: 0.82rem;
  }
  p.muted {
    margin-top: 0.15rem;
    font-size: 0.74rem;
  }
  .actions {
    display: flex;
    align-items: center;
    gap: 0.45rem;
    flex-wrap: wrap;
    margin-top: 0.8rem;
  }
  .btn {
    border-radius: var(--radius-sm);
    padding: 0.3rem 0.7rem;
    font-size: 0.75rem;
    font-weight: 600;
  }
  .btn.ghost {
    background: transparent;
    border: 1.5px solid;
  }
  .link {
    font-size: 0.75rem;
    font-weight: 600;
    margin-left: auto;
  }

  /* legend */
  .legend {
    display: flex;
    flex-wrap: wrap;
    gap: 0.3rem 0.7rem;
    margin: 0.6rem 0.2rem 0;
  }
  .swatch {
    display: inline-flex;
    align-items: center;
    gap: 0.32rem;
    font-size: 0.68rem;
    color: var(--muted);
  }
  .swatch i {
    width: 0.72rem;
    height: 0.72rem;
    border-radius: 3px;
    border: 1px solid var(--border);
    display: block;
  }
</style>
