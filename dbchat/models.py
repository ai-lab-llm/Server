from django.db import models
import uuid


class ChatSession(models.Model):
    """
    DB Chat의 대화 세션.
    - session_id: 프론트가 보관/요청에 사용하는 공개용 UUID
    """
    session_id = models.CharField(max_length=64, unique=True, default=lambda: str(uuid.uuid4()))
    title = models.CharField(max_length=255, default="데이터 조회")
    origin = models.CharField(max_length=50, default="dbchat")   # 페이지/출처 구분
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["origin", "-updated_at"]),
        ]


class ChatMessage(models.Model):
    """
    한 '질문-답변(turn)' 단위.
    - message_id: 질문 식별자(qid). SSE 스트림과 히스토리 조회에 사용
    - question / answer: 간단히 한 row에 묶음(필요하면 나중에 role-메시지 테이블로 분리)
    - status: generating / done / error 등
    - options/ui_context: 요청 원본을 남겨 디버깅 및 재현 편의
    """
    message_id = models.CharField(max_length=64, unique=True, default=lambda: str(uuid.uuid4()))
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name="messages")
    question = models.TextField()
    answer = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, default="queued")   # queued|generating|done|error
    error = models.JSONField(blank=True, null=True)

    options = models.JSONField(blank=True, null=True)
    ui_context = models.JSONField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=["session", "-created_at"]),
            models.Index(fields=["message_id"]),
        ]
