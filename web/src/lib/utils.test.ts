import { describe, expect, it } from "vitest"

import { cn, formatDuration, titleCase } from "./utils"

describe("formatting helpers", () => {
  it("formats work durations", () => {
    expect(formatDuration(0)).toBe("0m")
    expect(formatDuration(1800)).toBe("30m")
    expect(formatDuration(27000)).toBe("7h 30m")
  })

  it("humanizes enum-like values", () => {
    expect(titleCase("verified_face")).toBe("Verified Face")
    expect(titleCase(null)).toBe("—")
  })

  it("merges tailwind classes", () => {
    expect(cn("px-2", "px-4")).toBe("px-4")
  })
})
