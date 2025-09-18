from django.urls import path
from . import views

app_name = "dbchat"

# urlpatterns = [
#     # 화면 /dbchat
#     path("dbchat", views.chat_page, name="chat_page"),

#     # API
#     path("dbchat/sessions", views.create_or_list_sessions, name="sessions"),        # POST 생성 / GET 목록
#     path("dbchat/ask", views.ask_api, name="ask_api"),                               # POST 질문 전송
#     path("dbchat/stream", views.stream_answer_sse, name="stream_answer_sse"),       # GET SSE 토큰 스트림
#     path("dbchat/history", views.history_api, name="history_api"),                  # GET 질문 내역 조회
# ]

urlpatterns = [
    path("", views.chat_page, name="chat_page"),
    path("history", views.history_api, name="history_api"),
    path("ask", views.ask_api, name="ask_api"),
]