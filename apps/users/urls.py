# apps/users/urls.py

from django.urls import path
from rest_framework_simplejwt.views import (
    TokenRefreshView,
    TokenVerifyView,
)

from . import views

app_name = 'users'

urlpatterns = [
    
    path('login/',   views.AuditedLoginView.as_view(),  name='login'),
    path('refresh/', TokenRefreshView.as_view(),        name='token-refresh'),
    path('verify/',  TokenVerifyView.as_view(),         name='token-verify'),
    path('logout/',  views.AuditedLogoutView.as_view(), name='logout'),

    path('register/', views.UserRegisterView.as_view(), name='register'),

 
    path('me/',                 views.UserMeView.as_view(),          name='me'),
    path('me/change-password/', views.ChangePasswordView.as_view(),  name='change-password'),

    # Recuperación de contraseña
    path('password-reset/',         views.PasswordResetRequestView.as_view(), name='password-reset'),
    path('password-reset-confirm/', views.PasswordResetConfirmView.as_view(), name='password-reset-confirm'),

  
    path('users/',       views.UserListView.as_view(),   name='user-list'),
    path('users/<uuid:pk>/', views.UserDetailView.as_view(), name='user-detail'),
]