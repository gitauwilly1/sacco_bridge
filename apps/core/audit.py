from auditlog.registry import auditlog
from django.contrib.auth import get_user_model

User = get_user_model()

# Chama models
from apps.chamas.models import (
    Chama, ChamaMember, Contribution, Loan, LoanRepayment,
    Meeting, MeetingAttendance,
)

# Investment models
from apps.investments.models import (
    SACCO, SACCOShareClass, SACCOMemberHolding,
    LiquidityRequest, BuyerInterest, Connection, Offer,
)

# Transaction models
from apps.transactions.models import (
    SettlementIntent, SettlementEvent, LedgerEntry, SettlementReversal,
)

# User models
from apps.users.models import UserRole, UserProfile

# Register all models
auditlog.register(User, exclude_fields=['last_login', 'password'])
auditlog.register(UserRole)
auditlog.register(UserProfile)

auditlog.register(Chama)
auditlog.register(ChamaMember)
auditlog.register(Contribution)
auditlog.register(Loan)
auditlog.register(LoanRepayment)
auditlog.register(Meeting)
auditlog.register(MeetingAttendance)

auditlog.register(SACCO)
auditlog.register(SACCOShareClass)
auditlog.register(SACCOMemberHolding)
auditlog.register(LiquidityRequest)
auditlog.register(BuyerInterest)
auditlog.register(Connection)
auditlog.register(Offer)

auditlog.register(SettlementIntent)
auditlog.register(SettlementEvent)
auditlog.register(LedgerEntry)
auditlog.register(SettlementReversal)