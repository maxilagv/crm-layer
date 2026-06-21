/**
 * Temporary WhatsApp bridge using whatsapp-web.js.
 *
 * Use only with a test number. This unofficial bridge is for local validation
 * until the official Meta Cloud API flow is configured.
 */
import { existsSync, lstatSync, readdirSync, rmSync } from "node:fs";
import { join } from "node:path";
import QRCode from "qrcode";
import pkg from "whatsapp-web.js";

const { Client, LocalAuth, MessageMedia } = pkg;

// Chromium deja SingletonLock/Cookie/Socket en el perfil. Si el proceso anterior
// muere sin limpiar (un restart forzado del contenedor), el nuevo Chromium no
// arranca: "profile appears to be in use". Borramos esos locks rancios al inicio.
function clearChromiumLocks(dir = ".wwebjs_auth") {
  if (!existsSync(dir)) return;
  for (const name of readdirSync(dir)) {
    const full = join(dir, name);
    // Los locks (SingletonLock/Cookie/Socket) son SYMLINKS colgados al host viejo.
    // Hay que borrarlos sin seguir el symlink (lstat, no stat) — si no, stat falla
    // sobre el target inexistente y el lock rancio sobrevive.
    if (name.startsWith("Singleton")) {
      try {
        rmSync(full, { force: true, recursive: true });
        console.log(`cleared stale chromium lock: ${full}`);
      } catch {
        /* best-effort */
      }
      continue;
    }
    let st;
    try {
      st = lstatSync(full);
    } catch {
      continue;
    }
    if (st.isDirectory()) {
      clearChromiumLocks(full);
    }
  }
}

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";
const ORGANIZATION_ID = process.env.ORGANIZATION_ID;
const BRIDGE_SECRET = process.env.WA_BRIDGE_SHARED_SECRET ?? "dev-bridge-secret";

if (!ORGANIZATION_ID) {
  console.error("Missing ORGANIZATION_ID. Copy .env.example to .env and set it.");
  process.exit(1);
}

function maskPhone(value) {
  const digits = String(value ?? "").replace(/\D/g, "");
  return digits.length > 4 ? `***${digits.slice(-4)}` : "****";
}

function isDirectUserChat(chatId) {
  return typeof chatId === "string" && (chatId.endsWith("@c.us") || chatId.endsWith("@lid"));
}

function isAudioMimeType(mimeType) {
  return String(mimeType ?? "").toLowerCase().startsWith("audio/");
}

async function resolveSenderId(msg) {
  const rawFrom = String(msg.from ?? "");
  if (rawFrom.endsWith("@c.us")) {
    return "+" + rawFrom.replace("@c.us", "");
  }

  // Newer WhatsApp uses @lid (privacy ids) that are NOT phone numbers. The real
  // phone lives on contact.id (server "c.us"); contact.number can itself be the
  // LID in this case, so the c.us id is the trustworthy source — prefer it.
  try {
    const contact = await msg.getContact();
    if (contact?.id?.server === "c.us" && contact?.id?.user) {
      return "+" + String(contact.id.user).replace(/\D/g, "");
    }
    const number = String(contact?.number ?? "").replace(/\D/g, "");
    if (number) {
      return `+${number}`;
    }
  } catch (err) {
    console.log(`contact lookup failed: ${err.message}`);
  }

  return `lid:${rawFrom.replace("@lid", "")}`;
}

async function postBackend(path, body) {
  try {
    const res = await fetch(`${BACKEND_URL}${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Bridge-Secret": BRIDGE_SECRET,
      },
      body: JSON.stringify({ organization_id: ORGANIZATION_ID, ...body }),
    });
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      console.error(`backend ${path} -> HTTP ${res.status} ${text}`);
      return null;
    }
    return await res.json();
  } catch (err) {
    console.error(`backend ${path} error:`, err.message);
    return null;
  }
}

async function getBackend(path, params = {}) {
  const search = new URLSearchParams({ organization_id: ORGANIZATION_ID, ...params });
  try {
    const res = await fetch(`${BACKEND_URL}${path}?${search.toString()}`, {
      method: "GET",
      headers: {
        "X-Bridge-Secret": BRIDGE_SECRET,
      },
    });
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      console.error(`backend ${path} -> HTTP ${res.status} ${text}`);
      return null;
    }
    return await res.json();
  } catch (err) {
    console.error(`backend ${path} error:`, err.message);
    return null;
  }
}

function deliveryFailureReason(err) {
  const message = String(err?.message ?? err ?? "").toLowerCase();
  if (message.includes("not on whatsapp") || message.includes("not registered")) {
    return "unregistered_number";
  }
  return message.slice(0, 200) || "send_failed";
}

let outboxPolling = false;
let outboxTimer = null;

async function pollOutbox() {
  if (outboxPolling) return;
  outboxPolling = true;
  try {
    const result = await getBackend("/api/v1/whatsapp/bridge/outbox/", { limit: "20" });
    const messages = Array.isArray(result?.data) ? result.data : [];
    for (const item of messages) {
      const digits = String(item.phone ?? "").replace(/\D/g, "");
      if (!digits) {
        await postBackend("/api/v1/whatsapp/bridge/delivery-status/", {
          message_id: item.id,
          status: "failed",
          reason: "invalid_phone",
        });
        continue;
      }
      const chatId = `${digits}@c.us`;
      try {
        await client.sendMessage(chatId, item.body);
        await postBackend("/api/v1/whatsapp/bridge/delivery-status/", {
          message_id: item.id,
          status: "sent",
        });
        console.log(`outbox sent phone=${maskPhone(item.phone)} chars=${String(item.body).length}`);
      } catch (err) {
        const reason = deliveryFailureReason(err);
        console.error(`outbox send failed phone=${maskPhone(item.phone)} reason=${reason}`);
        await postBackend("/api/v1/whatsapp/bridge/delivery-status/", {
          message_id: item.id,
          status: "failed",
          reason,
        });
      }
    }
  } finally {
    outboxPolling = false;
  }
}

async function fetchDocumentMedia(document) {
  // The backend returns a (usually relative) token-gated signed URL.
  const raw = String(document?.url ?? "");
  if (!raw) return null;
  const url = raw.startsWith("http") ? raw : `${BACKEND_URL}${raw}`;
  try {
    const res = await fetch(url);
    if (!res.ok) {
      console.error(`document fetch -> HTTP ${res.status}`);
      return null;
    }
    const buf = Buffer.from(await res.arrayBuffer());
    return new MessageMedia(
      document.mime_type || "application/octet-stream",
      buf.toString("base64"),
      document.file_name || "documento",
    );
  } catch (err) {
    console.error("document fetch error:", err.message);
    return null;
  }
}

const client = new Client({
  authStrategy: new LocalAuth({ dataPath: ".wwebjs_auth" }),
  puppeteer: {
    headless: true,
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
  },
});

client.on("qr", async (qr) => {
  console.log("QR generated. Scan it from Settings > WhatsApp.");
  const dataUrl = await QRCode.toDataURL(qr);
  await postBackend("/api/v1/whatsapp/bridge/event/", { type: "qr", qr: dataUrl });
});

client.on("authenticated", () => {
  console.log("WhatsApp authenticated.");
  postBackend("/api/v1/whatsapp/bridge/event/", { type: "authenticated" });
});

client.on("ready", () => {
  console.log("WhatsApp ready. Listening for incoming direct messages.");
  postBackend("/api/v1/whatsapp/bridge/event/", { type: "ready" });
  if (!outboxTimer) {
    outboxTimer = setInterval(pollOutbox, 5000);
  }
  pollOutbox();
});

client.on("disconnected", (reason) => {
  console.log("WhatsApp disconnected:", reason);
  postBackend("/api/v1/whatsapp/bridge/event/", {
    type: "disconnected",
    info: { reason: String(reason) },
  });
});

client.on("auth_failure", (message) => {
  console.error("WhatsApp auth failure:", message);
  postBackend("/api/v1/whatsapp/bridge/event/", {
    type: "disconnected",
    info: { reason: `auth_failure: ${String(message)}` },
  });
});

client.on("message", async (msg) => {
  console.log(
    `message event from=${maskPhone(msg.from)} fromMe=${Boolean(msg.fromMe)} hasBody=${Boolean(msg.body)}`,
  );

  if (msg.fromMe) {
    console.log("ignored: message was sent by the linked WhatsApp number");
    return;
  }
  if (!isDirectUserChat(msg.from)) {
    console.log(`ignored: not a direct user chat (${msg.from ?? "missing from"})`);
    return;
  }

  const body = (msg.body ?? "").trim();
  let audioPayload = null;
  if (!body && msg.hasMedia) {
    try {
      const media = await msg.downloadMedia();
      if (media?.data && isAudioMimeType(media.mimetype)) {
        audioPayload = {
          audio_base64: media.data,
          audio_mime_type: media.mimetype,
        };
        console.log(`audio media downloaded mime=${media.mimetype} bytes64=${media.data.length}`);
      } else {
        console.log(`ignored: unsupported media mime=${media?.mimetype ?? "unknown"}`);
      }
    } catch (err) {
      console.error("media download error:", err.message);
    }
  }

  if (!body && !audioPayload) {
    console.log("ignored: empty or unsupported non-text message");
    return;
  }

  const phone = await resolveSenderId(msg);
  console.log(
    `posting inbound to backend phone=${maskPhone(phone)} chars=${body.length} hasAudio=${Boolean(audioPayload)}`,
  );
  const result = await postBackend("/api/v1/whatsapp/bridge/inbound/", {
    from: phone,
    body,
    message_id: msg.id?._serialized ?? "",
    ...audioPayload,
  });

  const data = result?.data;
  if (data?.document?.url) {
    // Owner document command: send the generated file with a caption.
    const media = await fetchDocumentMedia(data.document);
    if (media) {
      try {
        await msg.reply(media, undefined, {
          caption: data.reply || data.document.title || "",
        });
        console.log(`document sent phone=${maskPhone(phone)} file=${data.document.file_name}`);
      } catch (err) {
        console.error("document send error:", err.message);
        if (data.reply) await msg.reply(data.reply).catch(() => {});
      }
    } else if (data.reply) {
      await msg
        .reply(`${data.reply}\n\n(No pude adjuntar el archivo, probá de nuevo.)`)
        .catch(() => {});
    }
  } else if (data?.should_send && data?.reply) {
    try {
      await msg.reply(data.reply);
      console.log(`reply sent phone=${maskPhone(phone)} chars=${data.reply.length}`);
    } catch (err) {
      console.error("reply send error:", err.message);
    }
  } else {
    console.log("backend did not return a reply to send");
  }
});

process.on("unhandledRejection", (err) => {
  console.error("unhandledRejection:", err?.message ?? err);
});

process.on("uncaughtException", (err) => {
  console.error("uncaughtException:", err?.message ?? err);
});

console.log("Starting WhatsApp bridge.");
clearChromiumLocks();
client.initialize();
