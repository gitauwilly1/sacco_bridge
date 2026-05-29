from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class CustomPagination(PageNumberPagination):

    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
    page_query_param = 'page'

    def get_paginated_response(self, data):
        return Response({
            'success': True,
            'data': data,
            'pagination': {
                'count': self.page.paginator.count,
                'total_pages': self.page.paginator.num_pages,
                'current_page': self.page.number,
                'page_size': self.get_page_size(self.request),
                'has_next': self.page.has_next(),
                'has_previous': self.page.has_previous(),
                'next_page_number': self.page.next_page_number() if self.page.has_next() else None,
                'previous_page_number': self.page.previous_page_number() if self.page.has_previous() else None,
                'first_page': 1,
                'last_page': self.page.paginator.num_pages,
            }
        })


class SmallPagination(CustomPagination):
    page_size = 10
    max_page_size = 50


class LargePagination(CustomPagination):
    page_size = 50
    max_page_size = 200