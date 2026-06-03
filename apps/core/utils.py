import uuid
import hashlib
import hmac
from decimal import Decimal
from django.utils import timezone
from django.conf import settings
from cryptography.fernet import Fernet


def generate_unique_id(prefix='SB'):
    timestamp = timezone.now().strftime('%Y%m%d')
    random_suffix = uuid.uuid4().hex[:6].upper()
    return f"{prefix}-{timestamp}-{random_suffix}"


def generate_reference_number(transaction_type):
    now = timezone.now()
    random_sequence = uuid.uuid4().hex[:4].upper()
    return f"{transaction_type}-{now.year}-{now.month:02d}-{random_sequence}"


def generate_idempotency_key(*args):
    combined = '|'.join(str(arg) for arg in args)
    return hashlib.sha256(combined.encode()).hexdigest()


def generate_otp(length=6):
    import random
    import string
    return ''.join(random.choices(string.digits, k=length))


def calculate_settlement_fee(amount):
    amount = Decimal(str(amount))
    minimum_fee = Decimal('100.00')
    maximum_fee = Decimal('10000.00')

    if amount <= Decimal('100000.00'):
        fee_rate = Decimal('0.01')
    elif amount <= Decimal('500000.00'):
        fee_rate = Decimal('0.008')
    else:
        fee_rate = Decimal('0.005')

    calculated_fee = amount * fee_rate

    if calculated_fee < minimum_fee:
        return minimum_fee
    elif calculated_fee > maximum_fee:
        return maximum_fee

    return calculated_fee.quantize(Decimal('0.01'))


def calculate_loan_interest(principal, interest_rate, duration_months):
    principal = Decimal(str(principal))
    rate = Decimal(str(interest_rate)) / Decimal('100')
    duration = Decimal(str(duration_months))

    interest = principal * rate * duration
    total_repayment = principal + interest

    return {
        'principal': principal,
        'interest_rate': interest_rate,
        'duration_months': duration_months,
        'total_interest': interest.quantize(Decimal('0.01')),
        'total_repayment': total_repayment.quantize(Decimal('0.01')),
        'monthly_installment': (total_repayment / duration).quantize(Decimal('0.01')),
    }


def mask_phone_number(phone_number):
    if len(phone_number) >= 10:
        return phone_number[:4] + '***' + phone_number[-3:]
    return phone_number


def mask_email(email):
    if '@' in email:
        local, domain = email.split('@')
        if len(local) > 3:
            masked_local = local[:3] + '***'
        else:
            masked_local = local[0] + '***'
        return f"{masked_local}@{domain}"
    return email


def format_kes_amount(amount):
    amount = Decimal(str(amount))
    if amount >= 0:
        parts = f"{amount:,.2f}".split('.')
        return f"KSh {parts[0]}.{parts[1]}"
    else:
        amount = abs(amount)
        parts = f"{amount:,.2f}".split('.')
        return f"-KSh {parts[0]}.{parts[1]}"


def encrypt_data(data):
    key = settings.ENCRYPTION_KEY.encode()
    fernet = Fernet(key)
    return fernet.encrypt(str(data).encode()).decode()


def decrypt_data(encrypted_data):
    key = settings.ENCRYPTION_KEY.encode()
    fernet = Fernet(key)
    return fernet.decrypt(encrypted_data.encode()).decode()


def generate_signature(payload, secret):
    message = '&'.join(f"{k}={v}" for k, v in sorted(payload.items()))
    signature = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    return signature


def verify_signature(payload, signature, secret):
    expected_signature = generate_signature(payload, secret)
    return hmac.compare_digest(expected_signature, signature)