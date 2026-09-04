from django.urls import path

from .api_views import login_view, logout_view, me_view, register_view, users_list_view

urlpatterns = [
    path("register/", register_view, name="api_register"),
    path("login/", login_view, name="api_login"),
    path("logout/", logout_view, name="api_logout"),
    path("me/", me_view, name="api_me"),
    path("users/", users_list_view, name="api_users"),
]
