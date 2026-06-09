from django.urls import path
from .views import SystemEmailConfigurationView

app_name = 'notifications'

urlpatterns = [
    path('config/', SystemEmailConfigurationView.as_view(), name='email-config'),
]
