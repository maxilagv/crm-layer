from collections import OrderedDict

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from .responses import meta_for_request


class StandardPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200

    def get_paginated_response(self, data):
        return Response(
            OrderedDict(
                [
                    ("data", data),
                    (
                        "pagination",
                        {
                            "page": self.page.number,
                            "page_size": self.get_page_size(self.request),
                            "total": self.page.paginator.count,
                            "has_next": self.page.has_next(),
                        },
                    ),
                    ("meta", meta_for_request(self.request)),
                ]
            )
        )
