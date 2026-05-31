from django.urls import path, include
from rest_framework.routers import SimpleRouter
from apps.chamas.views import (
    ChamaViewSet, ChamaMemberViewSet, ContributionViewSet,
    LoanViewSet, MeetingViewSet,
)

router = SimpleRouter()
router.register(r'', ChamaViewSet, basename='chama')

urlpatterns = [
    path('', include(router.urls)),

    # Nested routes for chama members
    path(
        '<uuid:chama_pk>/members/',
        ChamaMemberViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='chama-members'
    ),
    path(
        '<uuid:chama_pk>/members/<uuid:pk>/',
        ChamaMemberViewSet.as_view({'get': 'retrieve', 'patch': 'partial_update', 'delete': 'destroy'}),
        name='chama-member-detail'
    ),

    # Nested routes for contributions
    path(
        '<uuid:chama_pk>/contributions/',
        ContributionViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='chama-contributions'
    ),
    path(
        '<uuid:chama_pk>/contributions/<uuid:pk>/',
        ContributionViewSet.as_view({'get': 'retrieve'}),
        name='chama-contribution-detail'
    ),
    path(
        '<uuid:chama_pk>/contributions/<uuid:pk>/verify/',
        ContributionViewSet.as_view({'post': 'verify'}),
        name='chama-contribution-verify'
    ),

    # Nested routes for loans
    path(
        '<uuid:chama_pk>/loans/',
        LoanViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='chama-loans'
    ),
    path(
        '<uuid:chama_pk>/loans/<uuid:pk>/',
        LoanViewSet.as_view({'get': 'retrieve'}),
        name='chama-loan-detail'
    ),
    path(
        '<uuid:chama_pk>/loans/<uuid:pk>/approve/',
        LoanViewSet.as_view({'post': 'approve'}),
        name='chama-loan-approve'
    ),
    path(
        '<uuid:chama_pk>/loans/<uuid:pk>/disburse/',
        LoanViewSet.as_view({'post': 'disburse'}),
        name='chama-loan-disburse'
    ),
    path(
        '<uuid:chama_pk>/loans/<uuid:pk>/repay/',
        LoanViewSet.as_view({'post': 'repay'}),
        name='chama-loan-repay'
    ),

    # Nested routes for meetings
    path(
        '<uuid:chama_pk>/meetings/',
        MeetingViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='chama-meetings'
    ),
    path(
        '<uuid:chama_pk>/meetings/<uuid:pk>/',
        MeetingViewSet.as_view({'get': 'retrieve', 'patch': 'partial_update'}),
        name='chama-meeting-detail'
    ),
    path(
        '<uuid:chama_pk>/meetings/<uuid:pk>/attendance/',
        MeetingViewSet.as_view({'post': 'record_attendance'}),
        name='chama-meeting-attendance'
    ),
]