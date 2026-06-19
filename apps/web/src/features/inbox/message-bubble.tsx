import {
  AlertCircle,
  Check,
  CheckCheck,
  Clock,
  FileAudio,
  FileText,
  ImageIcon,
} from "lucide-react";
import {
  MESSAGE_TYPE_LABELS,
  type Message,
  type MessageStatus,
  type MessageType,
} from "@/lib/api/conversations";
import { cn } from "@/lib/cn";
import { shortTime } from "@/lib/format";

function StatusIcon({ status }: { status: MessageStatus }) {
  if (status === "failed")
    return <AlertCircle className="h-3 w-3 text-danger" />;
  if (status === "read")
    return <CheckCheck className="h-3 w-3 text-info" />;
  if (status === "delivered") return <CheckCheck className="h-3 w-3" />;
  if (status === "sent" || status === "processed")
    return <Check className="h-3 w-3" />;
  return <Clock className="h-3 w-3" />;
}

const MEDIA_ICON: Partial<Record<MessageType, typeof FileAudio>> = {
  audio: FileAudio,
  image: ImageIcon,
  video: ImageIcon,
  document: FileText,
};

function MediaChip({ m, outbound }: { m: Message; outbound: boolean }) {
  const Icon = MEDIA_ICON[m.message_type] ?? FileText;
  const label = m.attachments[0]?.file_name || MESSAGE_TYPE_LABELS[m.message_type];
  return (
    <div
      className={cn(
        "mb-1 flex items-center gap-2 rounded-lg px-2 py-1.5 text-xs",
        outbound ? "bg-white/15" : "bg-card-hover",
      )}
    >
      <Icon className="h-4 w-4 shrink-0" />
      <span className="truncate">{label}</span>
    </div>
  );
}

export function MessageBubble({ m }: { m: Message }) {
  const outbound = m.direction === "outbound";
  const isSystem = m.direction === "system" || m.message_type === "system";

  if (isSystem) {
    return (
      <div className="my-1 flex justify-center">
        <span className="rounded-full bg-card px-3 py-1 text-[11px] text-muted ring-1 ring-border">
          {m.body || MESSAGE_TYPE_LABELS[m.message_type]}
        </span>
      </div>
    );
  }

  return (
    <div className={cn("flex", outbound ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[80%] rounded-2xl px-3.5 py-2 text-sm leading-relaxed shadow-card sm:max-w-[70%]",
          outbound
            ? "rounded-br-md bg-primary text-primary-foreground"
            : "rounded-bl-md bg-card text-foreground ring-1 ring-border",
        )}
      >
        {m.message_type !== "text" && (
          <MediaChip m={m} outbound={outbound} />
        )}
        {m.body && (
          <p className="whitespace-pre-wrap break-words">{m.body}</p>
        )}
        <div
          className={cn(
            "mt-1 flex items-center justify-end gap-1 text-[10px]",
            outbound ? "text-primary-foreground/70" : "text-muted",
          )}
        >
          <span>{shortTime(m.created_at)}</span>
          {outbound && <StatusIcon status={m.status} />}
        </div>
      </div>
    </div>
  );
}
