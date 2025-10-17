from django.urls import path
from . import views
from . import views_api

app_name = "dbchat"

urlpatterns = [
    path("", views.chat_page, name="chat_page"),

    path("threads", views.ThreadListAPI.as_view(), name="dbchat_threads"),
    path("threads/new", views.NewThreadAPI.as_view(), name="dbchat_new_thread"),
    path("threads/<uuid:thread_id>/rename", views.RenameThreadAPI.as_view(), name="dbchat_rename_thread"),
    path("threads/<uuid:thread_id>/messages", views.MessageListAPI.as_view(), name="dbchat_list_messages"),
    path("threads/<uuid:thread_id>/delete", views.DeleteThreadAPI.as_view(), name="dbchat_delete_thread"),
    path("ask", views.AskAPI.as_view(), name="dbchat_ask"),

    path("api/ask", views_api.api_ask),
    path("api/ask_stream", views_api.api_ask_stream),
]