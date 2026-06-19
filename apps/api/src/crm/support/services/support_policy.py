"""SupportPolicy adapter.

Reads ``business_settings.SupportPolicy`` when present; otherwise applies a
conservative default policy: never ask for passwords/tokens, never promise
immediate resolution, critical tickets require a human, and ask for minimal
diagnostic data.
"""

_DEFAULT_REQUIRED_DATA = [
    "captura del error",
    "email con el que intentás ingresar",
    "hora aproximada del problema",
    "pasos para reproducirlo",
]

_DEFAULT_FORBIDDEN = [
    "pedir contraseñas",
    "pedir tokens privados",
    "prometer resolución inmediata",
    "cerrar tickets críticos automáticamente",
    "exponer datos de otros clientes",
]


class SupportPolicyAdapter:
    @staticmethod
    def _policy(organization_id):
        if not organization_id:
            return None
        from crm.business_settings.models import SupportPolicy

        return SupportPolicy.objects.filter(organization_id=organization_id).first()

    @classmethod
    def urgent_keywords(cls, organization_id) -> list[str]:
        policy = cls._policy(organization_id)
        return list(getattr(policy, "urgent_keywords", []) or [])

    @classmethod
    def required_data(cls, organization_id) -> list[str]:
        return list(_DEFAULT_REQUIRED_DATA)

    @classmethod
    def forbidden_actions(cls, organization_id) -> list[str]:
        policy = cls._policy(organization_id)
        configured = list(getattr(policy, "forbidden_support_actions", []) or [])
        return configured or list(_DEFAULT_FORBIDDEN)

    @classmethod
    def default_reply(cls, organization_id) -> str:
        policy = cls._policy(organization_id)
        return getattr(policy, "default_support_reply", "") or (
            "Recibimos tu mensaje y ya lo estamos revisando. "
            "Para avanzar más rápido, ¿podrías darnos un poco más de detalle?"
        )
