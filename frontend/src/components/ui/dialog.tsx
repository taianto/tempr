import * as DialogPrimitive from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";

// biome-ignore lint/style/useComponentExportOnlyModules: Radix exports compound primitives for dialog composition.
export const Dialog = DialogPrimitive.Root;
// biome-ignore lint/style/useComponentExportOnlyModules: Radix exports compound primitives for dialog composition.
export const DialogTrigger = DialogPrimitive.Trigger;
// biome-ignore lint/style/useComponentExportOnlyModules: Radix exports compound primitives for dialog composition.
export const DialogTitle = DialogPrimitive.Title;
// biome-ignore lint/style/useComponentExportOnlyModules: Radix exports compound primitives for dialog composition.
export const DialogDescription = DialogPrimitive.Description;

export function DialogContent({
  className,
  layout = "drawer",
  children,
  ...props
}: ComponentProps<typeof DialogPrimitive.Content> & { layout?: "drawer" | "centered" }) {
  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className="fixed inset-0 z-40 bg-slate-950/35 backdrop-blur-[2px] data-[state=open]:animate-in" />
      <DialogPrimitive.Content
        className={cn(
          layout === "centered"
            ? "fixed left-1/2 top-1/2 z-50 max-h-[min(92vh,900px)] w-[calc(100%-1rem)] max-w-5xl -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-2xl border bg-background p-4 shadow-card focus:outline-none sm:w-[calc(100%-3rem)] sm:p-7"
            : "fixed inset-y-0 right-0 z-50 w-full max-w-xl overflow-y-auto border-l bg-background p-6 shadow-card focus:outline-none sm:p-8",
          className,
        )}
        {...props}
      >
        {children}
        <DialogPrimitive.Close
          aria-label="Close details"
          className={`absolute right-5 top-5 rounded-md p-2 text-muted-foreground transition hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${layout === "centered" ? "right-3 top-3 sm:right-5 sm:top-5" : ""}`}
        >
          <X size={18} />
        </DialogPrimitive.Close>
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  );
}
