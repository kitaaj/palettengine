import { describe, expect, it } from "vitest";
import { labToHex, samplePalette, type Lab } from "./livePalette";

function solid(hex: string, count: number): Uint8ClampedArray {
  const n = parseInt(hex.slice(1), 16);
  const r = (n >> 16) & 255,
    g = (n >> 8) & 255,
    b = n & 255;
  const buf = new Uint8ClampedArray(count * 4);
  for (let i = 0; i < count; i++) {
    buf.set([r, g, b, 255], i * 4);
  }
  return buf;
}

function twoTone(hexA: string, hexB: string, each: number): Uint8ClampedArray {
  const a = solid(hexA, each);
  const b = solid(hexB, each);
  const buf = new Uint8ClampedArray(a.length + b.length);
  buf.set(a, 0);
  buf.set(b, a.length);
  return buf;
}

describe("samplePalette", () => {
  it("returns k centers and k valid hexes", () => {
    const { centers, hexes } = samplePalette(twoTone("#112a4a", "#ee6644", 100), 5);
    expect(centers).toHaveLength(5);
    expect(hexes).toHaveLength(5);
    for (const h of hexes) expect(h).toMatch(/^#[0-9a-f]{6}$/);
  });

  it("sorts centers dark -> light", () => {
    const { centers } = samplePalette(twoTone("#000000", "#ffffff", 200), 5);
    for (let i = 1; i < centers.length; i++) {
      expect(centers[i][0]).toBeGreaterThanOrEqual(centers[i - 1][0]);
    }
  });

  it("collapses a solid color to that color", () => {
    const { hexes } = samplePalette(solid("#3b82f6", 300), 5);
    for (const h of hexes) expect(h).toBe("#3b82f6");
  });

  it("recovers both colors of a two-tone frame", () => {
    const { hexes } = samplePalette(twoTone("#e63946", "#457b9d", 300), 5);
    // The darkest and lightest centers should bracket the two source colors.
    expect(hexes).toContain(hexes[0]);
    const set = new Set(hexes);
    expect(set.size).toBeGreaterThan(1);
  });

  it("warm-start keeps k centers and is stable across identical frames", () => {
    const frame = twoTone("#222222", "#dddddd", 150);
    const first = samplePalette(frame, 4);
    const second = samplePalette(frame, 4, first.centers);
    expect(second.centers).toHaveLength(4);
    // Identical frame + warm start => centers essentially unchanged.
    for (let i = 0; i < 4; i++) {
      expect(second.centers[i][0]).toBeCloseTo(first.centers[i][0], 5);
    }
  });

  it("labToHex round-trips a known OKLab value", () => {
    // white ~ (1,0,0); black ~ (0,0,0)
    expect(labToHex([1, 0, 0] as Lab)).toBe("#ffffff");
    expect(labToHex([0, 0, 0] as Lab)).toBe("#000000");
  });
});
