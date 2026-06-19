from crm.documents.models import BrandKit


class BrandKitService:
    @staticmethod
    def get_or_create(organization) -> BrandKit:
        kit = BrandKit.objects.filter(organization_id=organization.id).first()
        if kit is not None:
            return kit
        # Seed sensible defaults from the business profile when available.
        business_name = getattr(organization, "name", "") or ""
        email = ""
        phone = ""
        try:
            from crm.business_settings.models import BusinessProfile

            profile = BusinessProfile.objects.filter(organization_id=organization.id).first()
            if profile is not None:
                business_name = profile.business_name or business_name
                phone = profile.owner_phone or ""
        except Exception:  # noqa: BLE001 — business_settings is optional context
            pass
        return BrandKit.objects.create(
            organization_id=organization.id,
            business_name=business_name,
            email=email,
            phone=phone,
        )

    @staticmethod
    def as_render_dict(kit: BrandKit, *, logo_bytes: bytes | None = None) -> dict:
        return {
            "business_name": kit.business_name or "",
            "legal_name": kit.legal_name or "",
            "tax_id": kit.tax_id or "",
            "email": kit.email or "",
            "phone": kit.phone or "",
            "website": kit.website or "",
            "address": kit.address or "",
            "primary_color": kit.primary_color or "#7C6CFF",
            "accent_color": kit.accent_color or "#22C55E",
            "text_color": kit.text_color or "#16161D",
            "currency": kit.currency or "ARS",
            "default_terms": kit.default_terms or "",
            "footer_note": kit.footer_note or "",
            "logo_bytes": logo_bytes,
        }
