class SalesMemoryBuilder:
    @staticmethod
    def build(*, lead, conversation=None) -> dict:
        return {
            "lead_id": str(lead.id),
            "score": lead.score,
            "temperature": lead.temperature,
            "summary": lead.summary,
            "conversation_id": str(conversation.id) if conversation else None,
        }
