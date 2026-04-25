import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { useHashRoute } from "./useHashRoute";

describe("useHashRoute", () => {
  beforeEach(() => {
    window.location.hash = "";
  });

  afterEach(() => {
    window.location.hash = "";
  });

  it("falls back to dashboard for empty hash", () => {
    const { result } = renderHook(() => useHashRoute());
    expect(result.current.route).toBe("dashboard");
  });

  it("parses a valid route from the hash", () => {
    window.location.hash = "#/jobs";
    const { result } = renderHook(() => useHashRoute());
    expect(result.current.route).toBe("jobs");
  });

  it("ignores unknown routes and falls back to dashboard", () => {
    window.location.hash = "#/not-a-real-route";
    const { result } = renderHook(() => useHashRoute());
    expect(result.current.route).toBe("dashboard");
  });

  it("updates the hash when setRoute is called", () => {
    const { result } = renderHook(() => useHashRoute());
    act(() => result.current.setRoute("voices"));
    expect(window.location.hash).toBe("#/voices");
    expect(result.current.route).toBe("voices");
  });

  it("reacts to hashchange events", () => {
    const { result } = renderHook(() => useHashRoute());
    act(() => {
      window.location.hash = "#/library";
      window.dispatchEvent(new HashChangeEvent("hashchange"));
    });
    expect(result.current.route).toBe("library");
  });
});
