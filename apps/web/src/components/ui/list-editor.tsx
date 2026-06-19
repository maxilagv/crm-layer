"use client";

import { Plus, X } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/cn";
import { Button } from "./button";
import { Input } from "./field";

export function ListEditor({
  value,
  onChange,
  placeholder,
  className,
}: {
  value: string[];
  onChange: (value: string[]) => void;
  placeholder?: string;
  className?: string;
}) {
  const [draft, setDraft] = useState("");

  const add = () => {
    const t = draft.trim();
    if (!t) return;
    if (!value.includes(t)) onChange([...value, t]);
    setDraft("");
  };

  return (
    <div className={cn("space-y-2", className)}>
      {value.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {value.map((item, i) => (
            <span
              key={`${item}-${i}`}
              className="inline-flex items-center gap-1 rounded-full bg-card-hover px-2.5 py-1 text-xs text-foreground ring-1 ring-border"
            >
              {item}
              <button
                type="button"
                onClick={() => onChange(value.filter((_, j) => j !== i))}
                aria-label={`Quitar ${item}`}
                className="cursor-pointer text-muted transition-colors hover:text-danger"
              >
                <X className="h-3 w-3" />
              </button>
            </span>
          ))}
        </div>
      )}
      <div className="flex gap-2">
        <Input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              add();
            }
          }}
          placeholder={placeholder ?? "Agregar y Enter…"}
        />
        <Button
          type="button"
          variant="secondary"
          size="icon"
          onClick={add}
          aria-label="Agregar"
        >
          <Plus className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
