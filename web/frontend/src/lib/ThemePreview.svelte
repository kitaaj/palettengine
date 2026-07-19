<script lang="ts">
  let {
    roles,
    theme,
  }: { roles: Record<string, string>; theme: string } = $props();
</script>

<div
  class="card"
  style="background:{roles.background}; color:{roles.text}; border-color:{roles.muted}"
>
  <div class="chip" style="background:{roles.surface}">
    <h4 style="color:{roles.text}">{theme} theme</h4>
    <p style="color:{roles.text}">Roles assigned from the palette — text is WCAG-corrected.</p>
    <div class="buttons">
      <span class="btn" style="background:{roles.primary}; color:{roles.background}">primary</span>
      <span class="btn" style="background:{roles.secondary}; color:{roles.background}"
        >secondary</span
      >
      <span class="btn outline" style="border-color:{roles.accent}; color:{roles.accent}"
        >accent</span
      >
    </div>
  </div>
</div>

<style>
  .card {
    border-radius: 12px;
    border: 1px solid;
    padding: 1rem;
  }
  .chip {
    border-radius: 10px;
    padding: 0.9rem 1rem;
  }
  h4 {
    margin: 0 0 0.3rem;
    text-transform: capitalize;
  }
  p {
    margin: 0 0 0.8rem;
    font-size: 0.85rem;
    opacity: 0.85;
  }
  .buttons {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
  }
  .btn {
    border-radius: 999px;
    padding: 0.3rem 0.9rem;
    font-size: 0.8rem;
    font-weight: 600;
  }
  .btn.outline {
    background: transparent;
    border: 1.5px solid;
  }
</style>
