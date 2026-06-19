from django.db import transaction

from crm.sales.models import SalesPlaybook

DEFAULT_PLAYBOOKS = [
    {
        "key": "diagnostic_first",
        "name": "Diagnostico antes de vender",
        "trigger_intents": ["new_interest", "has_problem", "asking_how_it_works"],
        "content": {
            "principles": [
                "hacer una pregunta de contexto",
                "no cotizar sin entender alcance",
                "llevar a llamada si hay fit",
            ]
        },
    },
    {
        "key": "price_objection",
        "name": "Objecion de precio",
        "trigger_intents": ["objecting_price", "asking_price"],
        "content": {
            "principles": [
                "validar la objecion",
                "explicar criterio de valor",
                "ofrecer llamada breve",
            ]
        },
    },
]


@transaction.atomic
def seed_default_playbooks(*, organization_id) -> int:
    created = 0
    for item in DEFAULT_PLAYBOOKS:
        _playbook, was_created = SalesPlaybook.objects.get_or_create(
            organization_id=organization_id,
            key=item["key"],
            defaults={
                "name": item["name"],
                "trigger_intents": item["trigger_intents"],
                "content": item["content"],
            },
        )
        created += int(was_created)
    return created


class PlaybookService:
    @staticmethod
    def seed_defaults(*, organization_id) -> int:
        return seed_default_playbooks(organization_id=organization_id)
