from django.urls import path

from .views import (
    APIKeyDetailView,
    APIKeysView,
    LoginView,
    LogoutView,
    MeView,
    RefreshView,
    UserDetailView,
    UsersView,
)

urlpatterns = [
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/refresh/", RefreshView.as_view(), name="auth-refresh"),
    path("auth/me/", MeView.as_view(), name="auth-me"),
    path("users/", UsersView.as_view(), name="users"),
    path("users/<uuid:user_id>/", UserDetailView.as_view(), name="user-detail"),
    path("api-keys/", APIKeysView.as_view(), name="api-keys"),
    path("api-keys/<uuid:api_key_id>/", APIKeyDetailView.as_view(), name="api-key-detail"),
]
