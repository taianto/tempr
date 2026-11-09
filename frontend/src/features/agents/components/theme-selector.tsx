import { Check, ChevronDown, Monitor, Moon, Sun } from "lucide-react";
import type { KeyboardEvent } from "react";
import { useEffect, useRef, useState } from "react";
import { useTheme } from "../theme";

const preferences = ["system", "light", "dark"] as const;
const labels = { system: "System", light: "Light", dark: "Dark" } as const;
const icons = { system: Monitor, light: Sun, dark: Moon } as const;

export function ThemeSelector() {
  const { preference, setPreference } = useTheme();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const optionRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const Icon = icons[preference];

  useEffect(() => {
    if (!open) return;
    const closeOutside = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", closeOutside);
    return () => document.removeEventListener("pointerdown", closeOutside);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const selectedIndex = preferences.indexOf(preference);
    optionRefs.current[selectedIndex]?.focus();
  }, [open, preference]);

  function closeAndRestoreFocus() {
    setOpen(false);
    triggerRef.current?.focus();
  }

  function handleOptionsKeyDown(event: KeyboardEvent<HTMLFieldSetElement>) {
    if (event.key === "Escape") {
      event.preventDefault();
      closeAndRestoreFocus();
      return;
    }

    const currentIndex = optionRefs.current.indexOf(document.activeElement as HTMLButtonElement);
    let nextIndex: number | undefined;
    if (event.key === "ArrowDown" || event.key === "ArrowRight")
      nextIndex = (currentIndex + 1) % preferences.length;
    if (event.key === "ArrowUp" || event.key === "ArrowLeft")
      nextIndex = (currentIndex - 1 + preferences.length) % preferences.length;
    if (event.key === "Home") nextIndex = 0;
    if (event.key === "End") nextIndex = preferences.length - 1;
    if (nextIndex !== undefined) {
      event.preventDefault();
      optionRefs.current[nextIndex]?.focus();
    }
  }

  return (
    <div ref={rootRef} className="relative shrink-0">
      <button
        ref={triggerRef}
        type="button"
        aria-label={`Theme: ${labels[preference]}`}
        aria-expanded={open}
        aria-controls="theme-options"
        onClick={() => setOpen((current) => !current)}
        onKeyDown={(event) => {
          if (event.key === "ArrowDown" && !open) {
            event.preventDefault();
            setOpen(true);
          }
        }}
        className="inline-flex h-9 items-center gap-2 rounded-lg border border-slate-200 bg-background px-3 text-xs font-medium text-slate-700 shadow-sm transition hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <Icon size={14} aria-hidden="true" />
        <span>{labels[preference]}</span>
        <ChevronDown
          size={14}
          aria-hidden="true"
          className={`transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>
      {open && (
        <fieldset
          id="theme-options"
          onKeyDown={handleOptionsKeyDown}
          className="absolute right-0 top-full z-30 m-0 mt-2 w-36 min-w-0 rounded-xl border border-slate-200 bg-card p-1.5 shadow-card"
        >
          <legend className="sr-only">Theme options</legend>
          {preferences.map((option, index) => {
            const OptionIcon = icons[option];
            return (
              <button
                key={option}
                ref={(element) => {
                  optionRefs.current[index] = element;
                }}
                type="button"
                aria-pressed={preference === option}
                onClick={() => {
                  setPreference(option);
                  closeAndRestoreFocus();
                }}
                className="flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left text-sm text-slate-600 transition hover:bg-slate-50 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <OptionIcon size={15} aria-hidden="true" />
                <span>{labels[option]}</span>
                {preference === option && (
                  <Check size={14} aria-hidden="true" className="ml-auto text-indigo-600" />
                )}
              </button>
            );
          })}
        </fieldset>
      )}
    </div>
  );
}
