import logging

logger = logging.getLogger(__name__)


def user_locked_out(request, credentials, **kwargs):
    logger.warning(f"User locked out: {credentials.get('email', 'unknown')}")