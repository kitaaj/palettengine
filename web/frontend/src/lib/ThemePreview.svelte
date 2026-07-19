<script lang="ts">
  let { roles, theme }: { roles: Record<string, string>; theme: string } = $props();
</script>

<div class="card" style="background:{roles.background}; color:{roles.text}">
  <div class="head">
    <span class="title">{theme} theme</span>
    <span class="pill" style="background:{roles.accent}; color:{roles.background}">accent</span>
  </div>
  <div class="chip" style="background:{roles.surface}">
    <p style="color:{roles.text}">
      Semantic roles assigned from the palette. Text is contrast-corrected to WCAG AA.
    </p>
    <div class="buttons">
      <span class="btn" style="background:{roles.primary}; color:{roles.background}">Primary</span>
      <span class="btn" style="background:{roles.secondary}; color:{roles.background}">
        Secondary
      </span>
      <span class="btn outline" style="border-color:{roles.accent}; color:{roles.accent}">
        Outline
      </span>
    </div>
  </div>
</div>

<style>
  .card {
    border-radius: var(--radius);
    border: 1px solid var(--border);
    padding: 0.9rem 1rem 1rem;
    box-shadow: var(--shadow-sm);
  }
  .head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.7rem;
  }
  .title {
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.05em;
    text-transform: capitalize;
  }
  .pill {
    font-size: 0.66rem;
    font-weight: 700;
    border-radius: 999px;
    padding: 0.12rem 0.55rem;
  }
  .chip {
    border-radius: var(--radius-sm);
    padding: 0.8rem 0.95rem;
  }
  p {
    margin: 0 0 0.75rem;
    font-size: 0.8rem;
    opacity: 0.85;
  }
  .buttons {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
  }
  .btn {
    border-radius: var(--radius-sm);
    padding: 0.28rem 0.8rem;
    font-size: 0.76rem;
    font-weight: 600;
  }
  .btn.outline {
    background: transparent;
    border: 1.5px solid;
  }
</style>
