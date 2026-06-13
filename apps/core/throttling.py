from rest_framework.throttling import UserRateThrottle, AnonRateThrottle


class AuthRateThrottle(UserRateThrottle):
    rate = '5/minute'
    scope = 'auth'


class AuthAnonRateThrottle(AnonRateThrottle):
    rate = '3/minute'
    scope = 'auth_anon'


class MutationRateThrottle(UserRateThrottle):
    rate = '20/minute'
    scope = 'mutation'


class ReadRateThrottle(UserRateThrottle):
    rate = '100/minute'
    scope = 'read'


class SensitiveOperationThrottle(UserRateThrottle):
    rate = '3/minute'
    scope = 'sensitive'


class BulkOperationThrottle(UserRateThrottle):
    rate = '5/minute'
    scope = 'bulk'


class ReportGenerationThrottle(UserRateThrottle):
    rate = '5/hour'
    scope = 'report'