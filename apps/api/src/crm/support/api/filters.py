def ticket_filters(query_params) -> dict:
    return {
        "status": query_params.get("status"),
        "priority": query_params.get("priority"),
        "category": query_params.get("category"),
        "client_id": query_params.get("client_id"),
        "contact_id": query_params.get("contact_id"),
        "assigned_user_id": query_params.get("assigned_user_id"),
        "search": query_params.get("search"),
    }


def known_issue_filters(query_params) -> dict:
    return {
        "status": query_params.get("status"),
        "category": query_params.get("category"),
    }
