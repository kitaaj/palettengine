import { describe, expect, it } from "vitest";
import { clampToGamut, hexToOklch, hexToRgb, inGamut, oklchToHex, rgbToHex } from "./oklch";

describe("hex <-> rgb", () => {
  it("parses 6- and 3-digit hex", () => {
    expect(hexToRgb("#ffffff")).toEqual([1, 1, 1]);
    expect(hexToRgb("#000000")).toEqual([0, 0, 0]);
    expect(hexToRgb("fff")).toEqual([1, 1, 1]);
  });

  it("formats and clamps", () => {
    expect(rgbToHex([1, 0, 0.5019607843137255])).toBe("#ff0080");
    expect(rgbToHex([1.4, -0.2, 0])).toBe("#ff0000");
  });
});

describe("oklch conversions (Ottosson reference vectors)", () => {
  it("matches the published sRGB primaries", () => {
    const red = hexToOklch("#ff0000");
    expect(red.l).toBeCloseTo(0.6279, 3);
    expect(red.c).toBeCloseTo(0.2577, 3);
    expect(red.h).toBeCloseTo(29.23, 1);

    const white = hexToOklch("#ffffff");
    expect(white.l).toBeCloseTo(1.0, 3);
    expect(white.c).toBeCloseTo(0.0, 3);
  });

  it("round-trips hex -> oklch -> hex exactly at 8-bit", () => {
    for (const hex of ["#3b82f6", "#e63946", "#f1faee", "#0b132b", "#5bc0be", "#123456"]) {
      expect(oklchToHex(hexToOklch(hex))).toBe(hex);
    }
  });

  it("matches the Python core for a known color", () => {
    // #3b82f6 per palettengine: oklch(0.6231, 0.1880, 259.81)
    const c = hexToOklch("#3b82f6");
    expect(c.l).toBeCloseTo(0.6231, 3);
    expect(c.c).toBeCloseTo(0.188, 3);
    expect(c.h).toBeCloseTo(259.8, 1);
  });
});

describe("gamut clamping", () => {
  it("keeps in-gamut colors untouched", () => {
    const c = hexToOklch("#5bc0be");
    expect(clampToGamut(c)).toEqual(c);
  });

  it("reduces chroma for impossible colors, preserving l and h", () => {
    const wild = { l: 0.5, c: 0.9, h: 30 };
    const clamped = clampToGamut(wild);
    expect(clamped.c).toBeLessThan(0.9);
    expect(clamped.l).toBe(0.5);
    expect(clamped.h).toBe(30);
    expect(oklchToHex(wild)).toMatch(/^#[0-9a-f]{6}$/);
  });

  it("inGamut flags out-of-range channels", () => {
    expect(inGamut([0.5, 0.5, 0.5])).toBe(true);
    expect(inGamut([1.2, 0, 0])).toBe(false);
  });
});
