from django.urls import path

from .api_views import (
    avatar_upload_view,
    login_view,
    logout_view,
    me_view,
    profile_update_view,
    register_view,
    users_list_view,
)

urlpatterns = [
    path("register/", register_view, name="api_register"),
    path("login/", login_view, name="api_login"),
    path("logout/", logout_view, name="api_logout"),
    path("me/", me_view, name="api_me"),
    path("users/", users_list_view, name="api_users"),
    path("profile/", profile_update_view, name="api_profile"),
    path("avatar/", avatar_upload_view, name="api_avatar"),
]
