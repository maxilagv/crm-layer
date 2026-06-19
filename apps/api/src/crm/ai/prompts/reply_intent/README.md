# reply_intent

Classifies the first inbound reply from an outbound prospect.

- **Purpose:** `AIPurpose.REPLY_INTENT`
- **Schema:** `crm.ai.schemas.reply_intent.ReplyIntentSchema`
- **Variables:** `business_name`, `services_offered`, `prospect_profile`,
  `outbound_message`, `reply_message`, `recent_messages`.
- **Runtime:** `generate_structured`, no tool-calling, no SafetyGuard.
