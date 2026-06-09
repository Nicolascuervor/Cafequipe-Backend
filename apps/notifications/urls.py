from django.urls import path
from .views import SystemEmailConfigurationView, NotificationLogListView, NotificationMarkReadView

app_name = 'notifications'

urlpatterns = [
    path('config/', SystemEmailConfigurationView.as_view(), name='email-config'),
    path('logs/', NotificationLogListView.as_view(), name='notification-logs'),
    path('logs/<int:pk>/read/', NotificationMarkReadView.as_view(), name='notification-mark-read'),
]
