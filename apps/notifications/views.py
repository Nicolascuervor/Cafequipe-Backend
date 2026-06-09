from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import models
from .models import SystemEmailConfiguration, NotificationLog
from .serializers import SystemEmailConfigurationSerializer, NotificationLogSerializer

class SystemEmailConfigurationView(generics.RetrieveUpdateAPIView):
    serializer_class = SystemEmailConfigurationSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return SystemEmailConfiguration.load()

class NotificationLogListView(generics.ListAPIView):
    serializer_class = NotificationLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.rol == 'GER':
            # Admins see global notifications (where user is None) + their own
            return NotificationLog.objects.filter(models.Q(user=user) | models.Q(user__isnull=True)).order_by('-created_at')[:50]
        else:
            # Regular workers only see their assigned notifications
            return NotificationLog.objects.filter(user=user).order_by('-created_at')[:50]

class NotificationMarkReadView(generics.UpdateAPIView):
    serializer_class = NotificationLogSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.rol == 'GER':
            return NotificationLog.objects.filter(models.Q(user=user) | models.Q(user__isnull=True))
        return NotificationLog.objects.filter(user=user)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_read = True
        instance.save(update_fields=['is_read'])
        return Response({'status': 'ok'})
