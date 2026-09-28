import assert from "node:assert/strict";
import test from "node:test";
import { frameToSeconds, rangesOverlap, secondsToFrame } from "../src/core/index.js";

test("converts rational frame rates without using a decimal FPS approximation", () => {
  const frameRate = { numerator: 24000, denominator: 1001 };
  assert.equal(frameToSeconds(24000, frameRate), 1001);
  assert.equal(secondsToFrame(1001, frameRate, "nearest"), 24000);
});

test("supports explicit frame rounding for negative time", () => {
  const frameRate = { numerator: 24, denominator: 1 };
  assert.equal(secondsToFrame(-1.1, frameRate, "floor"), -27);
  assert.equal(secondsToFrame(-1.1, frameRate, "ceil"), -26);
  assert.equal(secondsToFrame(-1.1, frameRate, "nearest"), -26);
});

test("uses half-open ranges so clips touching at a boundary do not overlap", () => {
  assert.equal(rangesOverlap(0, 4, 4, 8), false);
  assert.equal(rangesOverlap(0, 4, 3, 8), true);
});
