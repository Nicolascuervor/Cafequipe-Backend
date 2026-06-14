from django.urls import path
from .views import AssistantChatView

urlpatterns = [
    path('assistant/chat/', AssistantChatView.as_view(), name='assistant-chat'),
]
