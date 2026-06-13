from decimal import Decimal
from django.utils import timezone
from django.conf import settings
from django.core.cache import cache


class TransactionLimitService:

    @classmethod
    def get_user_limits(cls, user):
        if user.id_verification_status == 'VERIFIED':
            tier = 'VERIFIED'
        else:
            tier = 'UNVERIFIED'

        defaults = settings.TRANSACTION_LIMITS.get(tier, settings.TRANSACTION_LIMITS['UNVERIFIED'])

        return {
            'daily': user.daily_transaction_limit or Decimal(str(defaults['daily'])),
            'monthly': user.monthly_transaction_limit or Decimal(str(defaults['monthly'])),
            'per_transaction': user.per_transaction_limit or Decimal(str(defaults['per_transaction'])),
        }

    @classmethod
    def check_limit(cls, user, amount):
        limits = cls.get_user_limits(user)
        amount = Decimal(str(amount))

        # Check per-transaction limit
        if amount > limits['per_transaction']:
            return False, (
                f"Transaction amount KSh {amount:,.2f} exceeds per-transaction limit "
                f"of KSh {limits['per_transaction']:,.2f}."
            )

        # Check daily limit
        daily_total = cls._get_daily_total(user)
        if (daily_total + amount) > limits['daily']:
            remaining = limits['daily'] - daily_total
            return False, (
                f"Daily limit reached. Remaining: KSh {remaining:,.2f}. "
                f"Limit: KSh {limits['daily']:,.2f}."
            )

        # Check monthly limit
        monthly_total = cls._get_monthly_total(user)
        if (monthly_total + amount) > limits['monthly']:
            remaining = limits['monthly'] - monthly_total
            return False, (
                f"Monthly limit reached. Remaining: KSh {remaining:,.2f}. "
                f"Limit: KSh {limits['monthly']:,.2f}."
            )

        return True, None

    @classmethod
    def get_remaining_limits(cls, user):
        limits = cls.get_user_limits(user)
        daily_total = cls._get_daily_total(user)
        monthly_total = cls._get_monthly_total(user)

        return {
            'per_transaction': str(limits['per_transaction']),
            'daily_limit': str(limits['daily']),
            'daily_used': str(daily_total),
            'daily_remaining': str(max(0, limits['daily'] - daily_total)),
            'monthly_limit': str(limits['monthly']),
            'monthly_used': str(monthly_total),
            'monthly_remaining': str(max(0, limits['monthly'] - monthly_total)),
        }

    @classmethod
    def record_transaction(cls, user, amount):
        amount = Decimal(str(amount))
        today = timezone.now().strftime('%Y-%m-%d')
        month = timezone.now().strftime('%Y-%m')

        cache_key_day = f'user_tx_total:{user.id}:{today}'
        cache_key_month = f'user_tx_total:{user.id}:{month}'

        # Increment daily total
        try:
            cache.incr(cache_key_day, amount)
        except ValueError:
            cache.set(cache_key_day, amount, 86400)

        # Increment monthly total
        try:
            cache.incr(cache_key_month, amount)
        except ValueError:
            cache.set(cache_key_month, amount, 2592000)

    @classmethod
    def _get_daily_total(cls, user):
        today = timezone.now().strftime('%Y-%m-%d')
        cache_key = f'user_tx_total:{user.id}:{today}'
        return Decimal(str(cache.get(cache_key, 0)))

    @classmethod
    def _get_monthly_total(cls, user):
        month = timezone.now().strftime('%Y-%m')
        cache_key = f'user_tx_total:{user.id}:{month}'
        return Decimal(str(cache.get(cache_key, 0)))