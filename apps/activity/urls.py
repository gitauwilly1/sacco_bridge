from django.urls import path
from apps.activity.views import UserActivityFeedView, ChamaActivityFeedView

urlpatterns = [
    path('', UserActivityFeedView.as_view(), name='activity-feed'),
    path('chama/<uuid:chama_id>/', ChamaActivityFeedView.as_view(), name='chama-activity-feed'),
]