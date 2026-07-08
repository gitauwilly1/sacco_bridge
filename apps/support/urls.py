from django.urls import path

from apps.support.views import (
    AdminTicketDetailView,
    AdminTicketListView,
    MyTicketCreateView,
    MyTicketDetailView,
    MyTicketListView,
    MyTicketMessageCreateView,
)

urlpatterns = [
    # User-facing
    path('tickets/', MyTicketListView.as_view(), name='my-tickets'),
    path('tickets/create/', MyTicketCreateView.as_view(), name='my-ticket-create'),
    path('tickets/<uuid:pk>/', MyTicketDetailView.as_view(), name='my-ticket-detail'),
    path('tickets/<uuid:pk>/messages/', MyTicketMessageCreateView.as_view(), name='my-ticket-message'),
    # Admin
    path('admin/tickets/', AdminTicketListView.as_view(), name='admin-tickets'),
    path('admin/tickets/<uuid:pk>/', AdminTicketDetailView.as_view(), name='admin-ticket-detail'),
]
