from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import SystemEmailConfiguration
from .serializers import SystemEmailConfigurationSerializer

class SystemEmailConfigurationView(generics.RetrieveUpdateAPIView):
    serializer_class = SystemEmailConfigurationSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return SystemEmailConfiguration.load()
