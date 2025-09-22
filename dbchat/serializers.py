from rest_framework import serializers
from django.utils import timezone
from .models import ChatThread, ChatMessage

class ChatMessageSerializer(serializers.ModelSerializer):
    created_at = serializers.SerializerMethodField()

    class Meta:
        model = ChatMessage
        fields = ["id", "role", "content", "created_at", "meta"]

    def get_created_at(self, obj):
        return obj.created_at.isoformat(timespec="seconds")

class ChatThreadSerializer(serializers.ModelSerializer):
    updated_at = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()

    class Meta:
        model = ChatThread
        fields = ["id", "title", "updated_at"]

    def get_updated_at(self, obj):
        local_dt = timezone.localtime(obj.updated_at)   # KST
        return local_dt.strftime("%Y-%m-%d %H:%M:%S")

    def get_title(self, obj):
        return obj.title or "(제목 없음)"
