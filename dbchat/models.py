import uuid
from django.db import models
from django.utils import timezone

ROLE_CHOICES = (
    ("user", "User"),
    ("assistant", "Assistant"),
    ("system", "System"),
)

# 좌측 히스토리에 쌓이는 '대화 세션' 단위
class ChatThread(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=120, blank=True, default="")     
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now, db_index=True)
    is_archived = models.BooleanField(default=False)

    # 로그인 없이 쓰는 경우 세션키로 사용자 구분
    django_session_key = models.CharField(max_length=64, blank=True, default="", db_index=True)

    # 페이지 구분
    page = models.CharField(max_length=32, blank=True, default="dbchat", db_index=True)

    def touch(self):
        self.updated_at = timezone.now()
        self.save(update_fields=["updated_at"])

    def __str__(self):
        return self.title or f"대화 {self.pk}"

# 오른쪽 채팅창에 보이는 말풍선 한 줄
class ChatMessage(models.Model):
    thread = models.ForeignKey(ChatThread, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=16, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    # 분석/디버깅용 메타
    meta = models.JSONField(default=dict, blank=True)  # { "latency_ms":..., "tokens":..., "last_sql":... 등 }

    class Meta:
        indexes = [
            models.Index(fields=["thread", "created_at"]),
        ]

    def __str__(self):
        return f"[{self.role}] {self.content[:30]}"
