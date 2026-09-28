import { CoreError } from "./errors.js";
import { assertFrame, assertFrameRate, type Frame, type FrameRate } from "./types.js";

export type FrameRounding = "floor" | "ceil" | "nearest";

export function frameToSeconds(frame: Frame, frameRate: FrameRate): number {
  assertFrame(frame, "frame");
  assertFrameRate(frameRate);
  return (frame * frameRate.denominator) / frameRate.numerator;
}

export function secondsToFrame(
  seconds: number,
  frameRate: FrameRate,
  rounding: FrameRounding,
): Frame {
  assertFrameRate(frameRate);
  if (!Number.isFinite(seconds)) {
    throw new CoreError("INVALID_FRAME", "seconds must be finite");
  }

  const rawFrame = (seconds * frameRate.numerator) / frameRate.denominator;
  const rounded = rounding === "floor"
    ? Math.floor(rawFrame)
    : rounding === "ceil"
      ? Math.ceil(rawFrame)
      : Math.round(rawFrame);

  assertFrame(rounded, "converted frame");
  return rounded;
}

export function rangesOverlap(
  firstInFrame: Frame,
  firstOutFrame: Frame,
  secondInFrame: Frame,
  secondOutFrame: Frame,
): boolean {
  assertFrame(firstInFrame, "firstInFrame");
  assertFrame(firstOutFrame, "firstOutFrame");
  assertFrame(secondInFrame, "secondInFrame");
  assertFrame(secondOutFrame, "secondOutFrame");
  return firstInFrame < secondOutFrame && secondInFrame < firstOutFrame;
}
