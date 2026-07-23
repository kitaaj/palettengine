import { describe, expect, it } from "vitest";
import { contrastRatio, ensureContrast, readableOn, relLuminance } from "./contrast";

describe("relLuminance / contrastRatio", () => {
  it("black on white is the maximum 21:1", () => {
    expect(contrastRatio("#000000", "#ffffff")).toBeCloseTo(21, 5);
  });

  it("is symmetric and 1:1 for identical colors", () => {
    expect(contrastRatio("#3b82f6", "#3b82f6")).toBeCloseTo(1, 5);
    expect(contrastRatio("#123456", "#abcdef")).toBeCloseTo(
      contrastRatio("#abcdef", "#123456"),
      10,
    );
  });

  it("orders luminance sensibly", () => {
    expect(relLuminance("#ffffff")).toBeGreaterThan(relLuminance("#808080"));
    expect(relLuminance("#808080")).toBeGreaterThan(relLuminance("#000000"));
  });
});

describe("readableOn", () => {
  it("picks white on dark, black on light", () => {
    expect(readableOn("#0b132b")).toBe("#ffffff");
    expect(readableOn("#f1faee")).toBe("#000000");
  });
});

describe("ensureContrast", () => {
  it("keeps a foreground that already passes", () => {
    // Pure white already clears 4.5:1 on a deep navy.
    expect(ensureContrast("#ffffff", "#0b132b", 4.5)).toBe("#ffffff");
  });

  // Adversarial pairs, including the user's reference combos, where the raw
  // pairing clashes and must be corrected.
  const pairs: [string, string][] = [
    ["#667085", "#ffffff"], // muted grey on white
    ["#ffff00", "#ffffff"], // yellow on white (a classic low-contrast trap)
    ["#0057ff", "#0057ff"], // color on itself
    ["#f8f7f4", "#f8f7f4"], // porcelain on porcelain
    ["#b6ff2e", "#b6ff2e"], // lime on lime
    ["#3a0ca3", "#fff275"], // royal iris text on butter yellow
    ["#e46cff", "#2e0f35"], // electric orchid on deep plum
    ["#cfff74", "#2f3a1d"], // warm lime on olive ink
    ["#25272c", "#b8f7e4"], // graphite on sky mint
  ];

  for (const [fg, bg] of pairs) {
    it(`guarantees >= 4.5:1 for ${fg} on ${bg}`, () => {
      const fixed = ensureContrast(fg, bg, 4.5);
      expect(fixed).toMatch(/^#[0-9a-f]{6}$/);
      expect(contrastRatio(fixed, bg)).toBeGreaterThanOrEqual(4.5);
    });
  }

  it("honours a lower target for muted text", () => {
    const fixed = ensureContrast("#8a93a2", "#16191e", 3);
    expect(contrastRatio(fixed, "#16191e")).toBeGreaterThanOrEqual(3);
  });
});
