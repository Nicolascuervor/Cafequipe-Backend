# apps/users/urls.py

from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
    TokenBlacklistView,
)

from . import views

app_name = 'users'

urlpatterns = [
    
    path('login/',   TokenObtainPairView.as_view(),  name='login'),
    path('refresh/', TokenRefreshView.as_view(),     name='token-refresh'),
    path('verify/',  TokenVerifyView.as_view(),      name='token-verify'),
    path('logout/',  TokenBlacklistView.as_view(),   name='logout'),

    path('register/', views.UserRegisterView.as_view(), name='register'),

 
    path('me/',                 views.UserMeView.as_view(),          name='me'),
    path('me/change-password/', views.ChangePasswordView.as_view(),  name='change-password'),

  
    path('users/',       views.UserListView.as_view(),   name='user-list'),
    path('users/<int:pk>/', views.UserDetailView.as_view(), name='user-detail'),
]