# wa-bridge — Puente WhatsApp no oficial (temporal)

Conecta un número de WhatsApp vía **whatsapp-web.js** (QR, como WhatsApp Web) y
enlaza los mensajes con el backend del CRM para que el agente de IA responda.
Es **temporal**, para probar el flujo hasta tener la API oficial de Meta.

> ⚠️ **Riesgo:** las librerías no oficiales violan los Términos de WhatsApp y el
> número puede ser **baneado**. Usá un **número de prueba**, nunca tu línea
> principal/comercial.

## Cómo correrlo

1. Tené el backend corriendo en `http://localhost:8000` con:
   - `GEMINI_API_KEY` cargada en su `.env` (o el proveedor que uses),
   - Gemini activo: `python manage.py ai_setup_gemini --organization-id <ORG_ID>`,
   - `WA_BRIDGE_SHARED_SECRET` definido (debe coincidir con el de acá).
2. En esta carpeta:
   ```bash
   cp .env.example .env      # completá ORGANIZATION_ID (el uuid de tu organización)
   pnpm install              # baja whatsapp-web.js + Chromium (pesado la 1ª vez)
   pnpm start
   ```
3. Abrí el panel en **Config › WhatsApp**: ahí aparece el **QR**. Escanealo con
   el número de prueba. Cuando diga **Conectado**, escribile a ese número desde
   otro celular y el bot responde solo.

## Cómo obtener el ORGANIZATION_ID

En el panel, **Config › Organización** (o desde `/api/v1/auth/me`, campo
`organization.id`).

## Notas

- La sesión se guarda en `.wwebjs_auth/` (no hace falta re-escanear cada vez).
- Ignora grupos, estados y mensajes propios.
- Cuando tengas Meta Cloud API oficial, apagás este puente y el backend sigue
  funcionando con lo oficial sin cambios.
