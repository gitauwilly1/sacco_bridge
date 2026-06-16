"""
Logging standards for Sacco Bridge.

Level definitions:
    ERROR:   Something broke that needs immediate attention
             (payment failed, data corruption, service unavailable)

    WARNING: Something unexpected but handled
             (retry succeeded, fallback used, degraded performance)

    INFO:    Normal business events
             (user registered, settlement completed, loan approved)

    DEBUG:   Detailed troubleshooting information
             (SQL queries, request/response bodies, state transitions)

Best practices:
    1. Always log the user ID and relevant object IDs
    2. Use structured logging with 'extra' dict when possible
    3. Never log sensitive data (passwords, full tokens, PINs)
    4. Include traceback for ERROR level logs
    5. Use logger.exception() in except blocks to auto-include traceback
"""