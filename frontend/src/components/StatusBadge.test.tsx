import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { I18nProvider } from "../i18n";
import { StatusBadge } from "./StatusBadge";

function renderBadge(value: string) {
  return render(
    <I18nProvider>
      <StatusBadge value={value} />
    </I18nProvider>,
  );
}

describe("StatusBadge", () => {
  it("uses the succeeded style for succeeded jobs", () => {
    renderBadge("succeeded");
    const node = screen.getByText(/succeeded|thành công/i);
    expect(node).toHaveClass("status-tag-succeeded");
  });

  it("uses the failed style for failed jobs", () => {
    renderBadge("failed");
    const node = screen.getByText(/^(failed|lỗi)$/i);
    expect(node).toHaveClass("status-tag-failed");
  });

  it("falls back to queued style for unknown values and shows the raw label", () => {
    renderBadge("mystery");
    const node = screen.getByText("mystery");
    expect(node).toHaveClass("status-tag-queued");
  });
});
