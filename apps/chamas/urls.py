from django.urls import path, include
from rest_framework.routers import SimpleRouter
from apps.chamas.views import (
    AdminChamaManagementView, BulkInviteMembersView, ChamaViewSet, ChamaMemberViewSet, ContributionViewSet,
    LoanViewSet, MeetingViewSet,BulkContributionView, PollViewSet,
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
    path(
        '<uuid:chama_pk>/contributions/bulk/',
        BulkContributionView.as_view(),
        name='chama-contributions-bulk'
    ),

    # Contributions - add update and delete
    path(
        '<uuid:chama_pk>/contributions/<uuid:pk>/',
        ContributionViewSet.as_view({
            'get': 'retrieve',
            'patch': 'partial_update',
            'put': 'update',
            'delete': 'destroy',
        }),
        name='chama-contribution-detail'
    ),

    # Loans - add update and delete
    path(
        '<uuid:chama_pk>/loans/<uuid:pk>/',
        LoanViewSet.as_view({
            'get': 'retrieve',
            'patch': 'partial_update',
            'put': 'update',
            'delete': 'destroy',
        }),
        name='chama-loan-detail'
    ),

    # Meetings - add delete
    path(
        '<uuid:chama_pk>/meetings/<uuid:pk>/',
        MeetingViewSet.as_view({
            'get': 'retrieve',
            'patch': 'partial_update',
            'put': 'update',
            'delete': 'destroy',
        }),
        name='chama-meeting-detail'
    ),

    # Meeting attendance - add update and delete
    path(
        '<uuid:chama_pk>/meetings/<uuid:pk>/attendance/<uuid:attendance_pk>/',
        MeetingViewSet.as_view({
            'patch': 'partial_update',
            'delete': 'destroy',
        }),
        name='chama-meeting-attendance-detail'
    ),
    path(
        '<uuid:chama_pk>/members/bulk-invite/',
        BulkInviteMembersView.as_view(),
        name='chama-members-bulk-invite'
    ),
    path(
        '<uuid:chama_pk>/polls/',
        PollViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='chama-polls'
    ),
    path(
        '<uuid:chama_pk>/polls/<uuid:pk>/',
        PollViewSet.as_view({'get': 'retrieve'}),
        name='chama-poll-detail'
    ),
    path(
        '<uuid:chama_pk>/polls/<uuid:pk>/vote/',
        PollViewSet.as_view({'post': 'vote'}),
        name='chama-poll-vote'
    ),
    path(
        '<uuid:chama_pk>/polls/<uuid:pk>/close/',
        PollViewSet.as_view({'post': 'close'}),
        name='chama-poll-close'
    ),
    path(
        '<uuid:chama_pk>/loans/<uuid:pk>/early-repayment-calculation/',
        LoanViewSet.as_view({'get': 'early_repayment_calculation'}),
        name='chama-loan-early-repayment-calculation'
    ),
    path(
        '<uuid:chama_pk>/loans/<uuid:pk>/early-repay/',
        LoanViewSet.as_view({'post': 'early_repay'}),
        name='chama-loan-early-repay'
    ),
    path(
        '<uuid:chama_pk>/loans/<uuid:pk>/restructure/',
        LoanViewSet.as_view({'post': 'restructure'}),
        name='chama-loan-restructure'
    ),
    path(
        '<uuid:chama_pk>/loans/<uuid:pk>/mark-default/',
        LoanViewSet.as_view({'post': 'mark_default'}),
        name='chama-loan-mark-default'
    ),

    path('admin/manage/', AdminChamaManagementView.as_view(), name='admin-chama-manage'),
]