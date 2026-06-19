# Formato de salida

Devolvé un único JSON con esta forma (sin texto adicional):

- **title**: título del documento, concreto y atractivo.
- **subtitle**: subtítulo opcional (una línea).
- **client**: datos del cliente que te hayan pasado (`name`, `contact`, `email`, `phone`, `tax_id`, `address`). Dejá en `""` lo que no sepas.
- **intro**: 1-2 párrafos de apertura, cálidos y profesionales.
- **sections**: lista de `{heading, body}`. Usá 2-5 secciones relevantes al tipo de documento. `body` puede tener varias líneas (separadas por `\n`).
- **items**: lista de `{description, quantity, unit, unit_price}` cuando haya inversión/precios. `unit_price` y `quantity` en números planos. Si no corresponde, dejá la lista vacía.
- **currency**: moneda (usá la moneda por defecto si no se aclara).
- **tax_rate**: alícuota de impuesto en porcentaje (número). Usá la tasa por defecto salvo que el pedido diga otra cosa.
- **notes**: aclaraciones internas opcionales (puede ir `""`).
- **terms**: condiciones comerciales / forma de pago.
- **valid_until**: fecha de validez (YYYY-MM-DD) si aplica; si no, `""`.
- **meta.document_number**: número de documento si lo conocés; si no, `""`.

Adaptá el contenido al **tipo de documento**:
- **Propuesta**: foco en valor, alcance, enfoque y diferenciales; ítems con inversión.
- **Presupuesto**: foco en ítems y precios; intro breve; condiciones claras.
- **Informe**: foco en secciones narrativas; normalmente sin ítems.
- **Presentación**: secciones cortas y punchy (una idea por sección); ítems sólo si hay inversión.

## Template
Tipo de documento a generar: {doc_type_label}
Fecha de hoy: {today}
Moneda por defecto: {currency}
Alícuota de impuesto por defecto (%): {default_tax_rate}
Condiciones por defecto: {default_terms}

Datos del cliente (si los hay):
{client_block}

Pedido del dueño:
{owner_request}
