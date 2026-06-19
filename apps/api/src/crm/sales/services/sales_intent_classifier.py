from crm.sales.domain.rules import classify_intent


class SalesIntentClassifier:
    @staticmethod
    def classify(text: str) -> str:
        return classify_intent(text)
