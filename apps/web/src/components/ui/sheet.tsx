"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useEffect } from "react";
import { cn } from "@/lib/cn";

type Side = "left" | "right" | "bottom";

const panelClasses: Record<Side, string> = {
  left: "inset-y-0 left-0 h-full w-[84%] max-w-xs rounded-r-2xl border-r",
  right: "inset-y-0 right-0 h-full w-[84%] max-w-xs rounded-l-2xl border-l",
  bottom: "inset-x-0 bottom-0 max-h-[88dvh] rounded-t-2xl border-t",
};

const offscreen: Record<Side, Record<string, number | string>> = {
  left: { x: "-100%" },
  right: { x: "100%" },
  bottom: { y: "100%" },
};

export function Sheet({
  open,
  onClose,
  side = "left",
  label,
  className,
  children,
}: {
  open: boolean;
  onClose: () => void;
  side?: Side;
  label?: string;
  className?: string;
  children: React.ReactNode;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-50">
          <motion.div
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={onClose}
          />
          <motion.div
            role="dialog"
            aria-modal="true"
            aria-label={label}
            className={cn(
              "absolute border-border bg-card shadow-soft",
              panelClasses[side],
              className,
            )}
            initial={offscreen[side]}
            animate={{ x: 0, y: 0 }}
            exit={offscreen[side]}
            transition={{ type: "spring", stiffness: 380, damping: 38 }}
          >
            {children}
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
