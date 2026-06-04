import logging
from google import genai
from google.genai import types
from django.conf import settings
from django.utils import timezone

from apps.chatbot.models import (
    ChatSession, ChatMessage, KnowledgeArticle,
    SessionType, MessageRole, KnowledgeCategory
)

logger = logging.getLogger(__name__)


class GeminiService:

    _initialized = False
    _client = None
    _model_name = None

    SYSTEM_PROMPT = """You are the Sacco Bridge AI Assistant, a helpful and knowledgeable guide for Kenyan cooperative finance.

Your role is to help users with:
1. Chama (informal savings group) management - setting up groups, tracking contributions, managing loans, scheduling meetings
2. SACCO share investments - understanding share classes, buying shares from sellers, selling shares for liquidity
3. Platform navigation - how to use Sacco Bridge features
4. Financial guidance - explaining cooperative finance concepts in simple terms

Key facts about Sacco Bridge:
- It connects chama members and SACCO shareholders
- Users can digitize their chama operations (contributions, loans, meetings)
- Users can buy/sell SACCO shares through verified connections
- All settlements are guaranteed with trustee bank backing
- M-Pesa integration for contributions and payments
- Platform fee is 1% on settlements (min KSh 100, max KSh 10,000)

Guidelines:
- Be friendly, professional, and use simple language
- Use Kenyan Shillings (KSh) for all monetary values
- Understand Swahili terms commonly used in cooperatives
- Never provide financial advice that could be construed as investment recommendations
- For specific account queries, guide users to check their dashboard
- For disputes, direct users to the structured dispute resolution process
- Always prioritize user data privacy and security

If you don't know something, say so honestly and suggest contacting human support."""

    @classmethod
    def initialize(cls):
        if cls._initialized:
            return

        try:
            api_key = settings.GEMINI_API_KEY
            if not api_key:
                logger.warning("Gemini API key not configured.")
                return

            cls._client = genai.Client(api_key=api_key)
            cls._model_name = getattr(settings, 'GEMINI_MODEL', 'gemini-2.5-flash')

            cls._initialized = True
            logger.info(f"Gemini AI initialized with model: {cls._model_name}")

        except Exception as e:
            logger.error(f"Failed to initialize Gemini AI: {str(e)}")

    @classmethod
    def generate_response(cls, user_message, session, conversation_history=None):
        cls.initialize()

        if not cls._initialized:
            return {
                'response_text': (
                    "I apologize, but I'm currently unable to process your request. "
                    "Please try again later or contact our support team for assistance."
                ),
                'intent': 'error',
                'confidence': 0.0,
                'sources': [],
            }

        try:
            relevant_articles = KnowledgeService.retrieve_relevant_articles(user_message)

            knowledge_context = ""
            sources = []
            for article in relevant_articles:
                knowledge_context += f"\n\n### {article.title}\n{article.content}"
                sources.append({
                    'id': str(article.id),
                    'title': article.title,
                    'category': article.get_category_display(),
                })
                article.record_usage()

            context = cls._build_context(session)
            full_prompt = cls._build_prompt(
                user_message, context, knowledge_context, conversation_history
            )

            config = types.GenerateContentConfig(
                system_instruction=cls.SYSTEM_PROMPT,
                temperature=0.7,
                max_output_tokens=1024,
                top_p=0.95,
            )

            response = cls._client.models.generate_content(
                model=cls._model_name,
                contents=full_prompt,
                config=config,
            )

            response_text = response.text if response.text else ""

            intent = cls._classify_intent(user_message, response_text)
            tokens_used = cls._estimate_tokens(full_prompt + response_text)

            return {
                'response_text': response_text,
                'intent': intent,
                'confidence': 0.85,
                'sources': sources,
                'tokens_used': tokens_used,
            }

        except Exception as e:
            logger.error(f"Gemini response generation failed: {str(e)}")
            return {
                'response_text': (
                    "I apologize, but I encountered an error processing your request. "
                    "Please try again or contact our support team."
                ),
                'intent': 'error',
                'confidence': 0.0,
                'sources': [],
            }

    @classmethod
    def _build_context(cls, session):
        context_parts = []
        context_data = session.context_data or {}

        if context_data.get('user_name'):
            context_parts.append(f"User: {context_data['user_name']}")

        if context_data.get('chama_name'):
            context_parts.append(f"Active Chama: {context_data['chama_name']}")
            if context_data.get('chama_role'):
                context_parts.append(f"Role: {context_data['chama_role']}")

        if context_data.get('sacco_holdings'):
            holdings = context_data['sacco_holdings']
            if holdings:
                context_parts.append("SACCO Holdings:")
                for holding in holdings[:3]:
                    context_parts.append(
                        f"- {holding['sacco_name']}: {holding['shares']} shares"
                    )

        if context_data.get('active_requests'):
            context_parts.append(
                f"Active liquidity requests: {context_data['active_requests']}"
            )

        if context_data.get('active_connections'):
            context_parts.append(
                f"Active buyer/seller connections: {context_data['active_connections']}"
            )

        return "\n".join(context_parts) if context_parts else "New user exploring the platform."

    @classmethod
    def _build_prompt(cls, user_message, context, knowledge_context, history=None):
        prompt_parts = []

        prompt_parts.append("### User Context ###")
        prompt_parts.append(context)

        if knowledge_context:
            prompt_parts.append("\n### Relevant Knowledge Base ###")
            prompt_parts.append(knowledge_context)

        if history:
            prompt_parts.append("\n### Conversation History ###")
            for msg in history[-6:]:
                role = "User" if msg.get('role') == 'USER' else "Assistant"
                prompt_parts.append(f"{role}: {msg.get('content', '')}")

        prompt_parts.append("\n### Current Message ###")
        prompt_parts.append(f"User: {user_message}")
        prompt_parts.append("\nAssistant: ")

        return "\n".join(prompt_parts)

    @classmethod
    def _classify_intent(cls, user_message, response_text):
        message_lower = user_message.lower()

        intent_keywords = {
            'chama_setup': ['create chama', 'start chama', 'new group', 'setup chama', 'register chama', 'anzisha chama'],
            'chama_contribution': ['contribution', 'contribute', 'pay chama', 'mchango', 'lipa'],
            'chama_loan': ['loan', 'borrow', 'mkopo', 'kukopa', 'request loan'],
            'chama_meeting': ['meeting', 'mkutano', 'schedule meeting', 'attendance'],
            'investment_buy': ['buy shares', 'invest', 'purchase shares', 'dividend', 'nunua hisa'],
            'investment_sell': ['sell shares', 'liquidity', 'need cash', 'uuza hisa', 'pata pesa'],
            'settlement': ['settlement', 'transaction', 'payment', 'malipo', 'status'],
            'dispute': ['dispute', 'problem', 'complaint', 'tatizo', 'shida', 'issue'],
            'account': ['account', 'profile', 'password', 'login', 'verify', 'akaunti'],
            'platform_help': ['how to', 'help', 'guide', 'explain', 'what is', 'msaada', 'jinsi'],
            'greeting': ['hello', 'hi', 'hey', 'habari', 'jambo', 'good morning', 'good afternoon'],
        }

        matched_intents = []
        for intent, keywords in intent_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                matched_intents.append(intent)

        if matched_intents:
            return matched_intents[0]

        return 'general_inquiry'

    @classmethod
    def _estimate_tokens(cls, text):
        return max(1, len(text) // 4)


class KnowledgeService:

    @classmethod
    def retrieve_relevant_articles(cls, query, max_results=3):
        query_lower = query.lower()
        query_words = set(query_lower.split())

        articles = KnowledgeArticle.objects.filter(
            is_published=True,
            is_deleted=False
        )

        scored_articles = []
        for article in articles:
            score = cls._calculate_relevance_score(query_words, query_lower, article)
            if score > 0:
                scored_articles.append((score, article))

        scored_articles.sort(key=lambda x: x[0], reverse=True)

        return [article for score, article in scored_articles[:max_results]]

    @classmethod
    def _calculate_relevance_score(cls, query_words, query_lower, article):
        score = 0

        title_lower = article.title.lower()
        content_lower = article.content.lower()

        for word in query_words:
            if word in title_lower:
                score += 3
            elif word in content_lower:
                score += 1

        if any(tag.lower() in query_lower for tag in (article.tags or [])):
            score += 5

        score += article.priority

        if query_lower in title_lower:
            score += 10

        return score

    @classmethod
    def get_onboarding_articles(cls):
        return KnowledgeArticle.objects.filter(
            category__in=[
                KnowledgeCategory.PLATFORM_BASICS,
                KnowledgeCategory.CHAMA_BASICS,
                KnowledgeCategory.CHAMA_SETUP,
            ],
            is_published=True,
            is_deleted=False
        ).order_by('-priority')[:5]

    @classmethod
    def get_category_articles(cls, category, limit=10):
        return KnowledgeArticle.objects.filter(
            category=category,
            is_published=True,
            is_deleted=False
        ).order_by('-priority')[:limit]