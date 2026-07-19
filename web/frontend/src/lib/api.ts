/** Typed client for the palette-generator JSON API. */

export interface ApiColor {
  hex: string;
  oklch: [number, number, number];
}

export interface PalettePayload {
  colors: ApiColor[];
  score: number;
  breakdown: Record<string, number>;
  contrast: number[][];
  roles: { light: Record<string, string>; dark: Record<string, string> };
}

export interface Meta {
  schemes: string[];
  formats: string[];
  cvd_kinds: string[];
  roles: string[];
  modes: string[];
}

export interface GenerateOptions {
  scheme?: string;
  size?: number;
  locks?: Record<number, string>;
  seed?: number | null;
  mode?: string;
}

async function jsonOrThrow<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const doc = await res.json();
      detail = typeof doc.detail === "string" ? doc.detail : JSON.stringify(doc.detail);
    } catch {
      /* keep statusText */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export async function fetchMeta(): Promise<Meta> {
  return jsonOrThrow(await fetch("/api/meta"));
}

export async function generatePalette(opts: GenerateOptions): Promise<PalettePayload> {
  const body: Record<string, unknown> = {
    scheme: opts.scheme ?? "auto",
    size: opts.size ?? 5,
    locks: opts.locks ?? {},
    mode: opts.mode ?? "general",
  };
  if (opts.seed !== null && opts.seed !== undefined) body.seed = opts.seed;
  return jsonOrThrow(
    await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  );
}

export async function extractPalette(
  file: File,
  size: number,
  faithful: boolean,
): Promise<PalettePayload> {
  const form = new FormData();
  form.append("file", file);
  form.append("size", String(size));
  form.append("faithful", String(faithful));
  return jsonOrThrow(await fetch("/api/extract", { method: "POST", body: form }));
}

export async function simulatePalette(colors: string[], kind: string): Promise<string[]> {
  const doc = await jsonOrThrow<{ colors: string[] }>(
    await fetch("/api/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ colors, kind }),
    }),
  );
  return doc.colors;
}

export async function exportPalette(
  colors: string[],
  format: string,
  rolesTheme: string,
): Promise<Blob> {
  const res = await fetch("/api/export", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ colors, format, roles_theme: rolesTheme }),
  });
  if (!res.ok) throw new Error(res.statusText);
  return res.blob();
}
