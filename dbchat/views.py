import json
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from .models import ChatThread, ChatMessage
from .serializers import ChatThreadSerializer, ChatMessageSerializer
from .utils import make_auto_title, run_dbchat_pipeline


def _ensure_session(request):
    if not request.session.session_key:
        request.session.save()
    return request.session.session_key

def chat_page(request):
    _ensure_session(request)
    return render(request, "dbchat/dbchat.html")


# 좌측 히스토리 목록
class ThreadListAPI(APIView):
    def get(self, request):
        session_key = _ensure_session(request)
        qs = ChatThread.objects.filter(
            django_session_key=session_key,
            is_archived=False, page="dbchat"
        ).order_by("-updated_at")[:200]
        data = ChatThreadSerializer(qs, many=True).data
        return Response({"threads": data}, status=status.HTTP_200_OK)


# 새 스레드 생성
class NewThreadAPI(APIView):
    def post(self, request):
        session_key = _ensure_session(request)
        t = ChatThread.objects.create(
            django_session_key=session_key, page="dbchat", title=""
        )
        return Response({"thread_id": str(t.id)}, status=status.HTTP_201_CREATED)


# 스레드 제목 변경
class RenameThreadAPI(APIView):
    def post(self, request, thread_id):
        title = (request.data.get("title") or "").strip()
        thread = get_object_or_404(ChatThread, pk=thread_id)
        thread.title = title[:120]
        thread.updated_at = timezone.now()
        thread.save(update_fields=["title", "updated_at"])
        return Response({"ok": True}, status=status.HTTP_200_OK)

# 우측 말풍선 로드
class MessageListAPI(APIView):
    def get(self, request, thread_id):
        thread = get_object_or_404(ChatThread, pk=thread_id)
        msgs = thread.messages.order_by("created_at")
        data = ChatMessageSerializer(msgs, many=True).data
        return Response({"messages": data}, status=status.HTTP_200_OK)


class AskAPI(APIView):
    """
    POST /dbchat/ask  — 질문 전송
    Body JSON:
    {
      "thread_id": "UUID or null",
      "question": "string",
      "options": {"stream": false, "lang": "ko"},
      "ui_context": {"page": "dbchat"}
    }
    """
    def post(self, request):
        session_key = _ensure_session(request)

        question = (request.data.get("question") or "").strip()
        if not question:
            return Response({"detail": "Empty question"}, status=status.HTTP_400_BAD_REQUEST)

        thread_id = request.data.get("thread_id")
        if thread_id:
            thread = get_object_or_404(ChatThread, pk=thread_id)
        else:
            thread = ChatThread.objects.create(
                django_session_key=session_key, page="dbchat", title=""
            )

        # 사용자 메시지 저장
        ChatMessage.objects.create(thread=thread, role="user", content=question)

        # LLM/SQL-Agent 호출 (utils.run_dbchat_pipeline)
        answer_text, meta = run_dbchat_pipeline(thread)

        # 어시스턴트 메시지 저장
        asst = ChatMessage.objects.create(
            thread=thread, role="assistant", content=answer_text, meta=meta or {}
        )

        # 제목 자동 설정 + 업데이트 시간 갱신
        if not thread.title:
            thread.title = make_auto_title(question)
        thread.updated_at = timezone.now()
        thread.save(update_fields=["title", "updated_at"])

        msg_payload = ChatMessageSerializer(asst).data
        return Response({"thread_id": str(thread.id), "message": msg_payload}, status=status.HTTP_200_OK)


class DeleteThreadAPI(APIView):
    def delete(self, request, thread_id):
        thread = get_object_or_404(ChatThread, pk=thread_id)
        thread.delete()  
        return Response({"ok": True}, status=status.HTTP_204_NO_CONTENT)