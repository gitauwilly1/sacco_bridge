from rest_framework import serializers

from apps.chatbot.models import ChatMessage, ChatSession, KnowledgeArticle


class ChatMessageSerializer(serializers.ModelSerializer):

    role_display = serializers.SerializerMethodField()

    class Meta:
        model = ChatMessage
        fields = [
            'id', 'session', 'role', 'role_display', 'content',
            'intent_detected', 'confidence_score', 'action_type',
            'action_data', 'sources', 'tokens_used',
            'created_at',
        ]
        read_only_fields = [
            'id', 'role', 'intent_detected', 'confidence_score',
            'action_type', 'action_data', 'sources', 'tokens_used',
            'created_at',
        ]

    def get_role_display(self, obj):
        return obj.get_role_display()


class ChatSessionSerializer(serializers.ModelSerializer):

    session_type_display = serializers.SerializerMethodField()
    message_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = ChatSession
        fields = [
            'id', 'user', 'session_type', 'session_type_display',
            'title', 'is_active', 'context_data', 'total_tokens_used',
            'resolved', 'feedback_rating', 'message_count',
            'last_message', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'user', 'total_tokens_used', 'created_at', 'updated_at',
        ]

    def get_session_type_display(self, obj):
        return obj.get_session_type_display()

    def get_message_count(self, obj):
        return obj.messages.count()

    def get_last_message(self, obj):
        last = obj.messages.order_by('-created_at').first()
        if last:
            return {
                'content': last.content[:100],
                'role': last.role,
                'timestamp': last.created_at.isoformat(),
            }
        return None


class ChatRequestSerializer(serializers.Serializer):

    message = serializers.CharField(
        required=True,
        help_text="User message text"
    )
    session_type = serializers.ChoiceField(
        choices=[
            ('GENERAL_SUPPORT', 'General Support'),
            ('CHAMA_SETUP', 'Chama Setup Help'),
            ('INVESTMENT_GUIDANCE', 'Investment Guidance'),
            ('SETTLEMENT_HELP', 'Settlement Help'),
        ],
        required=False,
    )


class KnowledgeArticleSerializer(serializers.ModelSerializer):

    category_display = serializers.SerializerMethodField()
    authored_by_name = serializers.SerializerMethodField()

    class Meta:
        model = KnowledgeArticle
        fields = [
            'id', 'title', 'content', 'category', 'category_display',
            'tags', 'is_published', 'priority', 'view_count',
            'authored_by', 'authored_by_name',
            'reviewed_by', 'reviewed_at', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'view_count', 'reviewed_at', 'created_at', 'updated_at',
        ]

    def get_category_display(self, obj):
        return obj.get_category_display()

    def get_authored_by_name(self, obj):
        if obj.authored_by:
            return obj.authored_by.get_full_name()
        return None