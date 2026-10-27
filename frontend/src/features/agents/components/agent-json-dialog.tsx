import { Braces, Check, ClipboardPaste, LoaderCircle, WandSparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { ApiError } from "../types";

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  submitLabel: string;
  fieldLabel: string;
  endpoint: string;
  example: Record<string, unknown>;
  initialValue: Record<string, unknown>;
  onSubmit: (value: Record<string, unknown>) => Promise<void>;
};

export function AgentJsonDialog({
  open,
  onOpenChange,
  title,
  description,
  submitLabel,
  fieldLabel,
  endpoint,
  example,
  initialValue,
  onSubmit,
}: Props) {
  const initialJson = JSON.stringify(initialValue, null, 2);
  const [json, setJson] = useState(initialJson);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<{ path: string; message: string }[]>([]);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (open) {
      setJson(initialJson);
      setError(null);
      setFieldErrors([]);
    }
  }, [open, initialJson]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setFieldErrors([]);

    let value: unknown;
    try {
      value = JSON.parse(json);
    } catch (cause) {
      setError(
        cause instanceof Error
          ? `Invalid JSON: ${cause.message}`
          : "Invalid JSON. Check the syntax and try again.",
      );
      return;
    }
    if (!value || typeof value !== "object" || Array.isArray(value)) {
      setError("The agent must be a JSON object.");
      return;
    }

    setSubmitting(true);
    try {
      await onSubmit(value as Record<string, unknown>);
      onOpenChange(false);
    } catch (cause) {
      if (cause instanceof ApiError && cause.validationErrors.length) {
        setFieldErrors(
          cause.validationErrors.map((item) => ({
            path: item.loc.filter((part) => part !== "body").join("."),
            message: item.msg,
          })),
        );
        setError(cause.message);
      } else {
        setError(
          cause instanceof Error ? cause.message : "Something went wrong. Please try again.",
        );
      }
    } finally {
      setSubmitting(false);
    }
  }

  function formatJson() {
    try {
      setJson(JSON.stringify(JSON.parse(json), null, 2));
      setError(null);
    } catch (cause) {
      setError(cause instanceof Error ? `Invalid JSON: ${cause.message}` : "Invalid JSON.");
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(nextOpen) => {
        if (!submitting) onOpenChange(nextOpen);
      }}
    >
      <DialogContent aria-describedby="agent-json-description" className="max-w-2xl">
        <div className="flex items-start gap-3 pt-8">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600">
            <Braces size={19} />
          </div>
          <div className="pr-8">
            <DialogTitle className="text-xl font-semibold tracking-[-0.04em] text-slate-900">
              {title}
            </DialogTitle>
            <DialogDescription
              id="agent-json-description"
              className="mt-1 text-sm leading-5 text-slate-500"
            >
              {description}
            </DialogDescription>
          </div>
        </div>
        <form onSubmit={(event) => void handleSubmit(event)} className="mt-6">
          <div className="mb-2 flex items-center justify-between">
            <label htmlFor="agent-json" className="text-xs font-semibold text-slate-700">
              {fieldLabel}
            </label>
            <div className="flex items-center gap-1">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="h-8 px-2 text-xs text-slate-500"
                onClick={() => {
                  setJson(JSON.stringify(example, null, 2));
                  setError(null);
                  setFieldErrors([]);
                }}
              >
                <ClipboardPaste size={13} />
                Example
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="h-8 px-2 text-xs text-slate-500"
                onClick={formatJson}
              >
                <WandSparkles size={13} />
                Format
              </Button>
            </div>
          </div>
          <textarea
            id="agent-json"
            aria-invalid={Boolean(error)}
            spellCheck={false}
            autoCapitalize="off"
            autoCorrect="off"
            value={json}
            onChange={(event) => {
              setJson(event.target.value);
              setError(null);
              setFieldErrors([]);
            }}
            className="min-h-[340px] w-full resize-y rounded-xl border border-slate-200 bg-slate-950 p-4 font-mono text-[12px] leading-[1.7] text-slate-100 shadow-inner outline-none placeholder:text-slate-500 focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 aria-[invalid=true]:border-rose-400"
          />
          <p className="mt-2 text-[11px] text-slate-400">
            Paste the JSON body expected by{" "}
            <code className="rounded bg-slate-100 px-1 py-0.5 font-mono text-slate-600">
              {endpoint}
            </code>
            . The API validates the fields when you save.
          </p>
          {error && (
            <div
              role="alert"
              className="mt-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800"
            >
              <p>{error}</p>
              {fieldErrors.length > 0 && (
                <ul className="mt-2 space-y-1">
                  {fieldErrors.map((item) => (
                    <li key={`${item.path}-${item.message}`} className="font-mono text-xs">
                      <span className="font-semibold">{item.path || "request"}</span>:{" "}
                      {item.message}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
          <div className="mt-5 flex justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              disabled={submitting}
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={submitting} className="min-w-32">
              {submitting ? (
                <LoaderCircle size={15} className="animate-spin" />
              ) : (
                <Check size={15} />
              )}
              {submitting ? "Saving…" : submitLabel}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
