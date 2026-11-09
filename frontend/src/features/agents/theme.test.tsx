import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ThemeSelector } from "./components/theme-selector";
import { ThemeProvider, useTheme } from "./theme";

function ThemeControl() {
  const { resolvedTheme } = useTheme();
  return (
    <>
      <ThemeSelector />
      <output data-testid="resolved-theme">{resolvedTheme}</output>
    </>
  );
}

function renderTheme() {
  return render(
    <ThemeProvider>
      <ThemeControl />
    </ThemeProvider>,
  );
}

afterEach(() => {
  cleanup();
  window.localStorage.clear();
  document.documentElement.classList.remove("dark");
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("theme preference", () => {
  it("loads and applies a saved preference", () => {
    window.localStorage.setItem("tempr-theme", "dark");
    renderTheme();
    expect(screen.getByRole("button", { name: "Theme: Dark" })).toBeInTheDocument();
    expect(screen.getByTestId("resolved-theme")).toHaveTextContent("dark");
    expect(document.documentElement).toHaveClass("dark");
  });

  it("follows system changes until the user chooses a theme", () => {
    let change: ((event: MediaQueryListEvent) => void) | undefined;
    vi.stubGlobal(
      "matchMedia",
      vi.fn(() => ({
        matches: false,
        addEventListener: (_name: string, callback: (event: MediaQueryListEvent) => void) => {
          change = callback;
        },
        removeEventListener: vi.fn(),
      })),
    );
    renderTheme();
    expect(screen.getByTestId("resolved-theme")).toHaveTextContent("light");
    act(() => change?.({ matches: true } as MediaQueryListEvent));
    expect(screen.getByTestId("resolved-theme")).toHaveTextContent("dark");
    fireEvent.click(screen.getByRole("button", { name: "Theme: System" }));
    fireEvent.click(screen.getByRole("button", { name: "Light" }));
    act(() => change?.({ matches: true } as MediaQueryListEvent));
    expect(screen.getByTestId("resolved-theme")).toHaveTextContent("light");
  });

  it("keeps the selection active if local storage cannot be written", async () => {
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("Storage blocked");
    });
    const user = userEvent.setup();
    renderTheme();
    await user.click(screen.getByRole("button", { name: "Theme: System" }));
    await user.click(screen.getByRole("button", { name: "Dark" }));
    expect(screen.getByTestId("resolved-theme")).toHaveTextContent("dark");
    expect(document.documentElement).toHaveClass("dark");
  });

  it("opens and changes the theme with the keyboard", async () => {
    const user = userEvent.setup();
    renderTheme();
    await user.tab();
    const trigger = screen.getByRole("button", { name: "Theme: System" });
    expect(trigger).toHaveFocus();
    await user.keyboard("{ARROWDOWN}{ARROWDOWN}{ENTER}");
    expect(screen.getByRole("button", { name: "Theme: Light" })).toBeInTheDocument();
  });
});
