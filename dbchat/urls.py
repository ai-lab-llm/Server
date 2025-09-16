from django.urls import path
from .views import chat_page, ask_api

app_name = "dbchat"

urlpatterns = [
    path("", chat_page, name="chat_page"),
    path("ask", ask_api, name="ask_api"),
]