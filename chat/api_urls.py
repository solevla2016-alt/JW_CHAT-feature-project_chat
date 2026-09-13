from django.urls import path

from .api_views import (
    room_add_member_view,
    room_create_view,
    room_join_view,
    room_leave_view,
    room_messages_view,
    room_search_view,
    room_transcribe_view,
    room_upload_view,
    rooms_list_view,
    server_create_view,
    server_invite_view,
    server_join_view,
    servers_list_view,
)

urlpatterns = [
    path("servers/", servers_list_view, name="api_servers"),
    path("servers/create/", server_create_view, name="api_server_create"),
    path("servers/<int:server_id>/invite/", server_invite_view, name="api_server_invite"),
    path("servers/join/<str:token>/", server_join_view, name="api_server_join"),
    path("rooms/", rooms_list_view, name="api_rooms"),
    path("rooms/create/", room_create_view, name="api_room_create"),
    path("rooms/<int:room_id>/messages/", room_messages_view, name="api_room_messages"),
    path("rooms/<int:room_id>/search/", room_search_view, name="api_room_search"),
    path("rooms/<int:room_id>/join/", room_join_view, name="api_room_join"),
    path("rooms/<int:room_id>/leave/", room_leave_view, name="api_room_leave"),
    path("rooms/<int:room_id>/members/", room_add_member_view, name="api_room_add_member"),
    path("rooms/<int:room_id>/upload/", room_upload_view, name="api_room_upload"),
    path("rooms/<int:room_id>/transcribe/", room_transcribe_view, name="api_room_transcribe"),
]
