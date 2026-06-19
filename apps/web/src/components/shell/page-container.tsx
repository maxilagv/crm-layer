import { cn } from "@/lib/cn";

/** Scrollable, max-width page body for standard (non-inbox) screens. */
export function PageContainer({
  className,
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex-1 overflow-y-auto">
      <div
        className={cn(
          "mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 lg:px-8",
          className,
        )}
      >
        {children}
      </div>
    </div>
  );
}
