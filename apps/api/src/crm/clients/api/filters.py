def client_filters(query_params) -> dict:
    return {
        "status": query_params.get("status"),
        "support_level": query_params.get("support_level"),
        "service_plan": query_params.get("service_plan"),
        "search": query_params.get("search"),
    }
