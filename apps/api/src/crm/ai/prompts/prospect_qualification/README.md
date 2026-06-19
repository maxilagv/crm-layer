# prospect_qualification

Scores a discovered prospect against campaign criteria and returns a stable AI verdict.

- **Purpose:** `AIPurpose.PROSPECT_QUALIFICATION`
- **Schema:** `crm.ai.schemas.prospect_qualification.ProspectQualificationSchema`
- **Variables:** `business_name`, `services_offered`, `campaign_vertical`,
  `campaign_target_profile`, `prospect_profile`.
- **Runtime:** `generate_structured`, no tool-calling, no SafetyGuard.
