"use client";

import { usePathname } from "next/navigation";
import { ConversationList } from "@/features/inbox/conversation-list";
import { cn } from "@/lib/cn";

export default function InboxLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const detailOpen = pathname !== "/inbox";

  return (
    <div className="flex min-h-0 flex-1">
      <div
        className={cn(
          "w-full flex-col border-r border-border md:flex md:w-[360px] lg:w-[400px]",
          detailOpen ? "hidden md:flex" : "flex",
        )}
      >
        <ConversationList />
      </div>
      <div
        className={cn(
          "min-w-0 flex-1 flex-col",
          detailOpen ? "flex" : "hidden md:flex",
        )}
      >
        {children}
      </div>
    </div>
  );
}
