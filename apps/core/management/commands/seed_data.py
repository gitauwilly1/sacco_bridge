import random
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

User = get_user_model()


class Command(BaseCommand):
    help = 'Seeds the database with comprehensive sample data for development and testing'

    def handle(self, *args, **options):
        self.stdout.write('Seeding Sacco Bridge database...')

        with transaction.atomic():
            self.create_platform_admin()
            self.create_saccos_and_share_classes()
            self.create_users_with_profiles()
            self.create_chamas_with_full_data()
            self.create_sacco_holdings()
            self.create_liquidity_requests_and_connections()
            self.create_settlements()
            self.create_notifications()
            self.create_analytics_data()
            self.create_knowledge_articles()
            self.create_chat_sessions()
            self.create_polls_and_votes()
            self.create_constitutions_and_agreements()
            self.create_disputes()
            self.create_fraud_assessments()
            self.create_credit_scores()
            self.create_escrow_accounts()
            self.create_webhook_subscriptions()
            self.create_legal_documents()

        self.stdout.write(self.style.SUCCESS('Database seeded successfully!'))

    # 1. PLATFORM ADMIN

    def create_platform_admin(self):
        from apps.users.models import Role

        admin, created = User.objects.get_or_create(
            email='admin@saccobridge.co.ke',
            defaults={
                'phone_number': '0700000000',
                'first_name': 'Platform',
                'last_name': 'Administrator',
                'is_staff': True,
                'is_superuser': True,
                'email_verified': True,
                'phone_verified': True,
                'id_verification_status': 'VERIFIED',
                'trust_score': Decimal('5.00'),
            }
        )
        admin.set_password('AdminPass@2026')
        admin.save()
        admin.add_role(Role.PLATFORM_ADMIN)
        admin.add_role(Role.SUPPORT_AGENT)
        if created:
            self.stdout.write(f'  Created platform admin: {admin.email}')

    # 2. SACCOS AND SHARE CLASSES

    def create_saccos_and_share_classes(self):
        """Create verified SACCOs with share classes and market data."""
        from apps.analytics.models import SACCOMarketAnalytics
        from apps.investments.models import (
            SACCO,
            SACCOShareClass,
            SACCOStatus,
            SASRATier,
            ShareClass,
        )

        saccos_data = [
            {
                'name': 'Mwalimu National SACCO',
                'registration_number': 'SACCO/REG/001/2020',
                'sasra_tier': SASRATier.TIER_1,
                'description': 'The largest SACCO in Kenya serving teachers and education professionals. Known for consistent dividend payments and strong financial performance.',
                'total_assets': Decimal('58000000000.00'),
                'total_members': 98000,
                'dividend_rate': Decimal('14.50'),
                'dividend_year': 2025,
                'share_classes': [
                    {'class': ShareClass.NON_WITHDRAWABLE, 'nominal': Decimal('100.00'), 'issued': Decimal('50000000.0000')},
                    {'class': ShareClass.WITHDRAWABLE, 'nominal': Decimal('100.00'), 'issued': Decimal('30000000.0000')},
                    {'class': ShareClass.DEVELOPMENT, 'nominal': Decimal('500.00'), 'issued': Decimal('10000000.0000')},
                ],
                'price_range': (Decimal('280.00'), Decimal('320.00')),
            },
            {
                'name': 'Stima SACCO',
                'registration_number': 'SACCO/REG/002/2020',
                'sasra_tier': SASRATier.TIER_1,
                'description': 'Premier SACCO for Kenya Power employees and energy sector workers. Strong asset base and reliable returns.',
                'total_assets': Decimal('45000000000.00'),
                'total_members': 75000,
                'dividend_rate': Decimal('12.80'),
                'dividend_year': 2025,
                'share_classes': [
                    {'class': ShareClass.NON_WITHDRAWABLE, 'nominal': Decimal('200.00'), 'issued': Decimal('35000000.0000')},
                    {'class': ShareClass.WITHDRAWABLE, 'nominal': Decimal('200.00'), 'issued': Decimal('20000000.0000')},
                ],
                'price_range': (Decimal('340.00'), Decimal('380.00')),
            },
            {
                'name': 'Harambee SACCO',
                'registration_number': 'SACCO/REG/003/2020',
                'sasra_tier': SASRATier.TIER_1,
                'description': 'One of the largest deposit-taking SACCOs in Kenya, serving civil servants and private sector employees.',
                'total_assets': Decimal('32000000000.00'),
                'total_members': 62000,
                'dividend_rate': Decimal('11.20'),
                'dividend_year': 2025,
                'share_classes': [
                    {'class': ShareClass.NON_WITHDRAWABLE, 'nominal': Decimal('150.00'), 'issued': Decimal('28000000.0000')},
                    {'class': ShareClass.WITHDRAWABLE, 'nominal': Decimal('150.00'), 'issued': Decimal('15000000.0000')},
                ],
                'price_range': (Decimal('250.00'), Decimal('290.00')),
            },
            {
                'name': 'Ukulima SACCO',
                'registration_number': 'SACCO/REG/004/2020',
                'sasra_tier': SASRATier.TIER_2,
                'description': 'Agricultural sector SACCO serving farmers and agribusiness professionals across Kenya.',
                'total_assets': Decimal('8500000000.00'),
                'total_members': 18000,
                'dividend_rate': Decimal('10.50'),
                'dividend_year': 2025,
                'share_classes': [
                    {'class': ShareClass.NON_WITHDRAWABLE, 'nominal': Decimal('100.00'), 'issued': Decimal('8000000.0000')},
                    {'class': ShareClass.WITHDRAWABLE, 'nominal': Decimal('100.00'), 'issued': Decimal('4000000.0000')},
                ],
                'price_range': (Decimal('180.00'), Decimal('220.00')),
            },
            {
                'name': 'Imarika SACCO',
                'registration_number': 'SACCO/REG/005/2021',
                'sasra_tier': SASRATier.TIER_2,
                'description': 'Teachers SACCO based in Kilifi County, serving coastal region educators with growing membership.',
                'total_assets': Decimal('5200000000.00'),
                'total_members': 12000,
                'dividend_rate': Decimal('9.80'),
                'dividend_year': 2025,
                'share_classes': [
                    {'class': ShareClass.NON_WITHDRAWABLE, 'nominal': Decimal('100.00'), 'issued': Decimal('5000000.0000')},
                    {'class': ShareClass.WITHDRAWABLE, 'nominal': Decimal('100.00'), 'issued': Decimal('2500000.0000')},
                ],
                'price_range': (Decimal('160.00'), Decimal('200.00')),
            },
            {
                'name': 'Unaitas SACCO',
                'registration_number': 'SACCO/REG/006/2021',
                'sasra_tier': SASRATier.TIER_1,
                'description': 'Fast-growing SACCO with diverse membership from various sectors. Known for innovative financial products.',
                'total_assets': Decimal('28000000000.00'),
                'total_members': 45000,
                'dividend_rate': Decimal('13.00'),
                'dividend_year': 2025,
                'share_classes': [
                    {'class': ShareClass.NON_WITHDRAWABLE, 'nominal': Decimal('100.00'), 'issued': Decimal('20000000.0000')},
                    {'class': ShareClass.WITHDRAWABLE, 'nominal': Decimal('100.00'), 'issued': Decimal('12000000.0000')},
                    {'class': ShareClass.SPECIAL, 'nominal': Decimal('1000.00'), 'issued': Decimal('2000000.0000')},
                ],
                'price_range': (Decimal('220.00'), Decimal('260.00')),
            },
        ]

        for sacco_data in saccos_data:
            share_classes = sacco_data.pop('share_classes')
            price_range = sacco_data.pop('price_range')

            sacco, created = SACCO.objects.get_or_create(
                registration_number=sacco_data['registration_number'],
                defaults={
                    **sacco_data,
                    'status': SACCOStatus.ACTIVE,
                    'last_disclosure_date': date.today() - timedelta(days=30),
                    'disclosure_due_date': date.today() + timedelta(days=335),
                    'verified_at': timezone.now(),
                }
            )

            for sc_data in share_classes:
                SACCOShareClass.objects.get_or_create(
                    sacco=sacco,
                    share_class=sc_data['class'],
                    defaults={
                        'nominal_value': sc_data['nominal'],
                        'total_issued': sc_data['issued'],
                        'minimum_holding': Decimal('1.0000'),
                        'is_transferable': True,
                        'dividend_eligible': True,
                        'voting_rights': (sc_data['class'] == ShareClass.NON_WITHDRAWABLE),
                    }
                )

            # Create 90 days of market analytics
            for days_ago in range(90, -1, -1):
                metric_date = date.today() - timedelta(days=days_ago)
                base_price = price_range[0] + (price_range[1] - price_range[0]) * Decimal(str(random.uniform(0.3, 0.7)))
                volatility = Decimal(str(random.uniform(-5, 5)))

                SACCOMarketAnalytics.objects.get_or_create(
                    sacco=sacco,
                    metric_date=metric_date,
                    defaults={
                        'average_price_per_share': base_price,
                        'highest_price': base_price + volatility + Decimal('5.00'),
                        'lowest_price': base_price - volatility - Decimal('5.00'),
                        'opening_price': base_price - Decimal('2.00'),
                        'closing_price': base_price + Decimal('2.00'),
                        'total_volume_shares': Decimal(str(random.randint(100, 5000))),
                        'total_volume_amount': Decimal(str(random.randint(50000, 2000000))),
                        'number_of_transactions': random.randint(1, 30),
                        'active_sellers': random.randint(0, 15),
                        'active_buyers': random.randint(0, 20),
                    }
                )

            self.stdout.write(f'  Created SACCO: {sacco.name}')

    # 3. USERS WITH PROFILES

    def create_users_with_profiles(self):
        from apps.users.models import Role

        users_data = [
            # Sellers seeking liquidity
            {
                'email': 'mary.akinyi@example.com',
                'phone': '0711000001',
                'first': 'Mary', 'last': 'Akinyi',
                'roles': [Role.SELLER],
                'occupation': 'Primary School Teacher',
                'employer': 'TSC',
                'county': 'Kisumu',
                'monthly_income': '30000-50000',
                'risk': 'MODERATE',
                'experience': 'INTERMEDIATE',
                'bio': 'Teaching for 15 years. Needs liquidity for children school fees.',
            },
            {
                'email': 'peter.kamau@example.com',
                'phone': '0711000002',
                'first': 'Peter', 'last': 'Kamau',
                'roles': [Role.SELLER],
                'occupation': 'Boda Boda Operator',
                'employer': 'Self-Employed',
                'county': 'Nairobi',
                'monthly_income': '15000-30000',
                'risk': 'CONSERVATIVE',
                'experience': 'BEGINNER',
                'bio': 'Selling shares to expand boda boda fleet.',
            },
            {
                'email': 'grace.wanjala@example.com',
                'phone': '0711000003',
                'first': 'Grace', 'last': 'Wanjala',
                'roles': [Role.SELLER],
                'occupation': 'Nurse',
                'employer': 'Kenyatta National Hospital',
                'county': 'Nairobi',
                'monthly_income': '50000-80000',
                'risk': 'MODERATE',
                'experience': 'INTERMEDIATE',
                'bio': 'Medical emergency requires quick access to savings.',
            },
            # Buyers seeking yield
            {
                'email': 'james.omo@example.com',
                'phone': '0711000004',
                'first': 'James', 'last': 'Omondi',
                'roles': [Role.INVESTOR],
                'occupation': 'Bank Manager',
                'employer': 'Equity Bank',
                'county': 'Kisumu',
                'monthly_income': '100000-150000',
                'risk': 'AGGRESSIVE',
                'experience': 'EXPERT',
                'bio': 'Experienced investor looking for cooperative yield opportunities.',
            },
            {
                'email': 'faith.wambui@example.com',
                'phone': '0711000005',
                'first': 'Faith', 'last': 'Wambui',
                'roles': [Role.INVESTOR],
                'occupation': 'Software Developer',
                'employer': 'Safaricom',
                'county': 'Nairobi',
                'monthly_income': '80000-100000',
                'risk': 'AGGRESSIVE',
                'experience': 'INTERMEDIATE',
                'bio': 'Tech professional diversifying into cooperative investments.',
            },
            {
                'email': 'david.mutua@example.com',
                'phone': '0711000006',
                'first': 'David', 'last': 'Mutua',
                'roles': [Role.INVESTOR],
                'occupation': 'Accountant',
                'employer': 'KPMG',
                'county': 'Nairobi',
                'monthly_income': '100000-150000',
                'risk': 'MODERATE',
                'experience': 'EXPERT',
                'bio': 'Building a cooperative shares portfolio for retirement.',
            },
            # Institutional buyer
            {
                'email': 'investments@acme.co.ke',
                'phone': '0711000007',
                'first': 'Acme', 'last': 'Investments Ltd',
                'roles': [Role.INSTITUTIONAL_BUYER],
                'occupation': 'Investment Director',
                'employer': 'Acme Investments Ltd',
                'county': 'Nairobi',
                'monthly_income': '200000+',
                'risk': 'AGGRESSIVE',
                'experience': 'EXPERT',
                'bio': 'Institutional investor deploying capital in cooperative sector.',
            },
            # Chama-focused users
            {
                'email': 'agnes.muthoni@example.com',
                'phone': '0711000008',
                'first': 'Agnes', 'last': 'Muthoni',
                'roles': [],
                'occupation': 'Small Business Owner',
                'employer': 'Self-Employed',
                'county': 'Machakos',
                'monthly_income': '15000-30000',
                'risk': 'CONSERVATIVE',
                'experience': 'BEGINNER',
                'bio': 'Runs a grocery store. Active in three different chamas.',
            },
            {
                'email': 'john.kibet@example.com',
                'phone': '0711000009',
                'first': 'John', 'last': 'Kibet',
                'roles': [],
                'occupation': 'High School Teacher',
                'employer': 'TSC',
                'county': 'Eldoret',
                'monthly_income': '30000-50000',
                'risk': 'MODERATE',
                'experience': 'BEGINNER',
                'bio': 'Manages chama records and meeting minutes.',
            },
            {
                'email': 'sarah.chebet@example.com',
                'phone': '0711000010',
                'first': 'Sarah', 'last': 'Chebet',
                'roles': [Role.SELLER],
                'occupation': 'Farmer',
                'employer': 'Self-Employed',
                'county': 'Kericho',
                'monthly_income': '10000-15000',
                'risk': 'CONSERVATIVE',
                'experience': 'NONE',
                'bio': 'Tea farmer saving through chamas for farm expansion.',
            },
        ]

        for data in users_data:
            roles = data.pop('roles')
            occupation = data.pop('occupation')
            employer = data.pop('employer')
            county = data.pop('county')
            monthly_income = data.pop('monthly_income')
            risk = data.pop('risk')
            experience = data.pop('experience')
            bio = data.pop('bio')

            user, created = User.objects.get_or_create(
                email=data['email'],
                defaults={
                    'phone_number': data['phone'],
                    'first_name': data['first'],
                    'last_name': data['last'],
                    'email_verified': True,
                    'phone_verified': True,
                    'id_verification_status': 'VERIFIED',
                    'trust_score': Decimal(str(round(random.uniform(2.0, 5.0), 2))),
                }
            )
            if created:
                user.set_password('UserPass@2026')
                user.save()
                if roles:
                    for role in roles:
                        user.add_role(role)

                profile = user.profile
                profile.occupation = occupation
                profile.employer = employer
                profile.county = county
                profile.monthly_income_range = monthly_income
                profile.risk_tolerance = risk
                profile.investment_experience = experience
                profile.source_of_funds = bio
                profile.save()

            self.stdout.write(f'  Created user: {user.email}')

    # 4. CHAMAS WITH FULL DATA

    def create_chamas_with_full_data(self):
        from apps.chamas.models import (
            Chama,
            ChamaMember,
            Contribution,
            ContributionFrequency,
            ContributionStatus,
            Loan,
            LoanRepayment,
            LoanStatus,
            Meeting,
            MeetingAttendance,
            MeetingStatus,
        )
        from apps.chamas.models import MemberRole as ChamaMemberRole
        from apps.chamas.models import PaymentMethod

        chamas_data = [
            {
                'name': 'Upendo Women Group',
                'type': 'WELFARE_GROUP',
                'amount': Decimal('2000.00'),
                'frequency': ContributionFrequency.WEEKLY,
                'members': 15,
                'loan_rate': Decimal('10.00'),
                'description': 'Women welfare group supporting members during emergencies and celebrations.',
                'member_emails': [
                    'mary.akinyi@example.com', 'grace.wanjala@example.com',
                    'agnes.muthoni@example.com', 'sarah.chebet@example.com',
                    'faith.wambui@example.com',
                ],
            },
            {
                'name': 'Jitegemee Investment Club',
                'type': 'INVESTMENT_CLUB',
                'amount': Decimal('5000.00'),
                'frequency': ContributionFrequency.MONTHLY,
                'members': 10,
                'loan_rate': Decimal('12.00'),
                'description': 'Investment club pooling funds for SACCO share purchases and real estate.',
                'member_emails': [
                    'james.omo@example.com', 'david.mutua@example.com',
                    'peter.kamau@example.com', 'john.kibet@example.com',
                ],
            },
            {
                'name': 'Wote Pamoja Merry-Go-Round',
                'type': 'MERRY_GO_ROUND',
                'amount': Decimal('3000.00'),
                'frequency': ContributionFrequency.MONTHLY,
                'members': 12,
                'loan_rate': Decimal('5.00'),
                'description': 'Monthly merry-go-round rotating savings among friends and neighbors.',
                'member_emails': [
                    'agnes.muthoni@example.com', 'sarah.chebet@example.com',
                    'mary.akinyi@example.com',
                ],
            },
            {
                'name': 'Kilimo Table Banking',
                'type': 'TABLE_BANKING',
                'amount': Decimal('1000.00'),
                'frequency': ContributionFrequency.WEEKLY,
                'members': 20,
                'loan_rate': Decimal('8.00'),
                'description': 'Table banking group for small-scale farmers in Kiambu County.',
                'member_emails': [
                    'sarah.chebet@example.com', 'peter.kamau@example.com',
                ],
            },
            {
                'name': 'Family Welfare Fund',
                'type': 'FAMILY_GROUP',
                'amount': Decimal('10000.00'),
                'frequency': ContributionFrequency.MONTHLY,
                'members': 8,
                'loan_rate': Decimal('5.00'),
                'description': 'Extended family savings for education and medical emergencies.',
                'member_emails': [
                    'grace.wanjala@example.com', 'james.omo@example.com',
                    'faith.wambui@example.com',
                ],
            },
        ]

        all_members = []

        for chama_data in chamas_data:
            member_emails = chama_data.pop('member_emails')

            chama, created = Chama.objects.get_or_create(
                name=chama_data['name'],
                defaults={
                    'chama_type': chama_data['type'],
                    'contribution_amount': chama_data['amount'],
                    'contribution_frequency': chama_data['frequency'],
                    'max_members': 50,
                    'loan_interest_rate': chama_data['loan_rate'],
                    'max_loan_multiple': Decimal('3.00'),
                    'max_loan_duration_months': 12,
                    'payout_cycle_months': 12,
                    'payout_method': 'EQUAL',
                    'late_fee_amount': Decimal('200.00'),
                    'grace_period_days': 3,
                    'description': chama_data['description'],
                    'status': 'ACTIVE',
                }
            )

            # Add members
            roles_cycle = [
                ChamaMemberRole.CHAIRPERSON,
                ChamaMemberRole.TREASURER,
                ChamaMemberRole.SECRETARY,
                ChamaMemberRole.LOAN_OFFICER,
                ChamaMemberRole.VICE_CHAIRPERSON,
            ]

            for i, email in enumerate(member_emails):
                try:
                    user = User.objects.get(email=email)
                except User.DoesNotExist:
                    continue

                role = roles_cycle[i % len(roles_cycle)] if i < len(roles_cycle) else ChamaMemberRole.MEMBER

                member, created = ChamaMember.objects.get_or_create(
                    chama=chama,
                    user=user,
                    defaults={
                        'role': role,
                        'is_active': True,
                        'joined_at': timezone.now() - timedelta(days=random.randint(30, 730)),
                    }
                )
                all_members.append(member)

                # Create contributions for the last 12 weeks
                for weeks_ago in range(12, -1, -1):
                    period_start = date.today() - timedelta(weeks=weeks_ago, days=date.today().weekday())
                    period_end = period_start + timedelta(days=6)

                    if weeks_ago == 0:
                        # Current week might be pending
                        status = random.choice([ContributionStatus.PAID, ContributionStatus.PAID, ContributionStatus.PENDING])
                        paid_at = timezone.now() - timedelta(days=random.randint(0, 2)) if status == ContributionStatus.PAID else None
                    elif weeks_ago <= 2:
                        status = random.choice([ContributionStatus.PAID, ContributionStatus.PAID, ContributionStatus.PAID, ContributionStatus.LATE])
                        paid_at = timezone.now() - timedelta(weeks=weeks_ago, days=random.randint(0, 3))
                    else:
                        status = ContributionStatus.PAID
                        paid_at = timezone.now() - timedelta(weeks=weeks_ago, days=random.randint(0, 2))

                    contribution = Contribution.objects.create(
                        chama=chama,
                        member=member,
                        amount=chama.contribution_amount,
                        expected_amount=chama.contribution_amount,
                        status=status,
                        payment_method=PaymentMethod.MPESA,
                        payment_reference=f'TXN{random.randint(100000, 999999)}',
                        period_start=period_start,
                        period_end=period_end,
                        paid_at=paid_at,
                    )

                    if status == ContributionStatus.PAID and paid_at:
                        member.total_contributions += contribution.amount
                        member.current_balance += contribution.amount
                        member.last_contribution_date = paid_at.date()
                        member.contribution_streak += 1
                        member.save()

            # Create loans
            for _ in range(random.randint(3, 8)):
                borrower = random.choice([m for m in all_members if m.chama == chama])
                principal = Decimal(str(random.choice([5000, 10000, 15000, 20000, 30000, 50000])))
                duration = random.choice([3, 6, 12])

                from apps.core.utils import calculate_loan_interest
                terms = calculate_loan_interest(principal, chama.loan_interest_rate, duration)

                loan_status = random.choice([
                    LoanStatus.FULLY_REPAID, LoanStatus.FULLY_REPAID,
                    LoanStatus.PARTIALLY_REPAID, LoanStatus.DISBURSED,
                    LoanStatus.APPROVED,
                ])

                loan = Loan.objects.create(
                    chama=chama,
                    borrower=borrower,
                    principal=principal,
                    interest_rate=chama.loan_interest_rate,
                    duration_months=duration,
                    total_interest=terms['total_interest'],
                    total_repayable=terms['total_repayment'],
                    monthly_installment=terms['monthly_installment'],
                    outstanding_balance=terms['total_repayment'],
                    status=loan_status,
                    purpose=random.choice([
                        'Business expansion', 'School fees', 'Medical emergency',
                        'Home improvement', 'Debt consolidation', 'Farm inputs',
                    ]),
                    approved_by=random.choice([m for m in all_members if m.chama == chama and m.role in [
                        ChamaMemberRole.CHAIRPERSON, ChamaMemberRole.TREASURER
                    ]]),
                    approved_at=timezone.now() - timedelta(days=random.randint(30, 180)),
                    disbursed_at=timezone.now() - timedelta(days=random.randint(25, 175)) if loan_status not in [LoanStatus.PENDING, LoanStatus.APPROVED] else None,
                    due_date=date.today() + timedelta(days=random.randint(30, 365)),
                )

                # Create repayments for active loans
                if loan_status in [LoanStatus.PARTIALLY_REPAID, LoanStatus.FULLY_REPAID]:
                    num_repayments = random.randint(1, duration) if loan_status == LoanStatus.PARTIALLY_REPAID else duration
                    total_repaid = Decimal('0')
                    for r in range(num_repayments):
                        if r == num_repayments - 1 and loan_status == LoanStatus.FULLY_REPAID:
                            repayment_amount = loan.total_repayable - total_repaid
                        else:
                            repayment_amount = min(
                                loan.monthly_installment,
                                loan.total_repayable - total_repaid
                            )

                        LoanRepayment.objects.create(
                            loan=loan,
                            amount=repayment_amount,
                            payment_method=PaymentMethod.MPESA,
                            payment_reference=f'REP{random.randint(100000, 999999)}',
                            paid_at=timezone.now() - timedelta(days=random.randint(0, 180)),
                        )
                        total_repaid += repayment_amount

                    loan.outstanding_balance = loan.total_repayable - total_repaid
                    if loan.outstanding_balance <= Decimal('0'):
                        loan.outstanding_balance = Decimal('0')
                        loan.status = LoanStatus.FULLY_REPAID
                    loan.save()

                    borrower.outstanding_loans = max(Decimal('0'), borrower.outstanding_loans - total_repaid)
                    borrower.save()

            # Create meetings
            for month_ago in range(6, -1, -1):
                meeting_date = date.today().replace(day=random.randint(1, 28)) - timedelta(days=month_ago * 30)
                if meeting_date > date.today():
                    meeting_date = date.today() - timedelta(days=random.randint(1, 7))

                meeting = Meeting.objects.create(
                    chama=chama,
                    title=random.choice([
                        'Monthly Review Meeting', 'Loan Approval Session',
                        'Quarterly Planning', 'Emergency Meeting',
                        'Group Training Session',
                    ]),
                    description='Regular chama meeting for review and planning.',
                    date=meeting_date,
                    start_time=time(17, 30),
                    end_time=time(19, 0),
                    location=random.choice([
                        'Chairpersons residence', 'Community Hall',
                        'Church Hall', 'Virtual (WhatsApp)',
                    ]),
                    status=MeetingStatus.COMPLETED if meeting_date < date.today() else MeetingStatus.SCHEDULED,
                    organizer=random.choice([m for m in all_members if m.chama == chama]),
                )

                # Record attendance
                for m in [m for m in all_members if m.chama == chama]:
                    MeetingAttendance.objects.create(
                        meeting=meeting,
                        member=m,
                        attended=random.choice([True, True, True, False]),
                        arrived_at=timezone.make_aware(
                            datetime.combine(meeting_date, time(17, random.randint(30, 50)))
                        ) if meeting_date < date.today() else None,
                    )

            # Update chama financials
            chama.update_financials()

            self.stdout.write(f'  Created chama: {chama.name}')

    # 5. SACCO HOLDINGS

    def create_sacco_holdings(self):
        from apps.investments.models import SACCO, SACCOMemberHolding

        sacco = SACCO.objects.first()
        if not sacco:
            return

        share_class = sacco.share_classes.first()

        holdings_data = [
            {'email': 'mary.akinyi@example.com', 'shares': Decimal('1250.0000')},
            {'email': 'grace.wanjala@example.com', 'shares': Decimal('800.0000')},
            {'email': 'peter.kamau@example.com', 'shares': Decimal('350.0000')},
            {'email': 'james.omo@example.com', 'shares': Decimal('3000.0000')},
            {'email': 'david.mutua@example.com', 'shares': Decimal('2000.0000')},
            {'email': 'sarah.chebet@example.com', 'shares': Decimal('200.0000')},
        ]

        for data in holdings_data:
            try:
                user = User.objects.get(email=data['email'])
            except User.DoesNotExist:
                continue

            SACCOMemberHolding.objects.get_or_create(
                user=user,
                sacco=sacco,
                share_class=share_class,
                defaults={
                    'total_shares': data['shares'],
                    'member_since': date.today() - timedelta(days=random.randint(365, 1825)),
                    'member_number': f'{sacco.registration_number}-{random.randint(1000, 9999)}',
                    'verification_status': 'VERIFIED',
                    'last_verified_at': timezone.now() - timedelta(days=random.randint(1, 30)),
                }
            )

        # Add holdings in other SACCOs for some users
        other_saccos = list(SACCO.objects.exclude(id=sacco.id)[:3])
        for user_email in ['james.omo@example.com', 'david.mutua@example.com', 'faith.wambui@example.com']:
            try:
                user = User.objects.get(email=user_email)
            except User.DoesNotExist:
                continue

            for s in random.sample(other_saccos, min(2, len(other_saccos))):
                sc = s.share_classes.first()
                SACCOMemberHolding.objects.get_or_create(
                    user=user,
                    sacco=s,
                    share_class=sc,
                    defaults={
                        'total_shares': Decimal(str(random.randint(100, 2000))),
                        'member_since': date.today() - timedelta(days=random.randint(365, 1825)),
                        'verification_status': 'VERIFIED',
                        'last_verified_at': timezone.now(),
                    }
                )

        self.stdout.write('  Created SACCO holdings')

    # 6. LIQUIDITY REQUESTS AND CONNECTIONS

    def create_liquidity_requests_and_connections(self):
        from apps.investments.models import (
            BuyerInterest,
            Connection,
            ConnectionStatus,
            LiquidityRequest,
            Offer,
            SACCOMemberHolding,
            UrgencyLevel,
        )

        holdings = SACCOMemberHolding.objects.filter(
            verification_status='VERIFIED', is_deleted=False
        )

        liquidity_requests = []

        # Active requests from sellers
        seller_scenarios = [
            {'email': 'mary.akinyi@example.com', 'quantity': Decimal('200.0000'), 'price': Decimal('350.00'), 'urgency': UrgencyLevel.PRIORITY, 'note': 'Need funds for children school fees next term'},
            {'email': 'grace.wanjala@example.com', 'quantity': Decimal('150.0000'), 'price': Decimal('360.00'), 'urgency': UrgencyLevel.URGENT, 'note': 'Medical emergency - need quick liquidity'},
            {'email': 'peter.kamau@example.com', 'quantity': Decimal('100.0000'), 'price': Decimal('340.00'), 'urgency': UrgencyLevel.STANDARD, 'note': 'Expanding my boda boda business'},
            {'email': 'sarah.chebet@example.com', 'quantity': Decimal('50.0000'), 'price': Decimal('330.00'), 'urgency': UrgencyLevel.STANDARD, 'note': 'Buying farm inputs for next planting season'},
        ]

        for scenario in seller_scenarios:
            try:
                user = User.objects.get(email=scenario['email'])
                holding = holdings.filter(user=user).first()
                if not holding:
                    continue
            except User.DoesNotExist:
                continue

            lr = LiquidityRequest.objects.create(
                seller=user,
                sacco=holding.sacco,
                share_class=holding.share_class,
                holding=holding,
                share_quantity=scenario['quantity'],
                expected_price_per_share=scenario['price'],
                minimum_price_per_share=scenario['price'] - Decimal('20.00'),
                urgency=scenario['urgency'],
                allow_institutional_buyers=True,
                notes=scenario['note'],
            )
            liquidity_requests.append(lr)

            # Create buyer interests
            buyer_emails = ['james.omo@example.com', 'faith.wambui@example.com', 'david.mutua@example.com']
            interested_buyers = random.sample(buyer_emails, min(2, len(buyer_emails)))
            for buyer_email in interested_buyers:
                try:
                    buyer = User.objects.get(email=buyer_email)
                except User.DoesNotExist:
                    continue

                BuyerInterest.objects.get_or_create(
                    liquidity_request=lr,
                    buyer=buyer,
                    defaults={
                        'buyer_message': random.choice([
                            'Interested in these shares. What discount can you offer?',
                            'I can close quickly if the price is right.',
                            'Looking to add to my cooperative portfolio.',
                        ]),
                        'viewed_by_seller': random.choice([True, False]),
                    }
                )

        # Create connections with negotiations
        active_lr = liquidity_requests[0] if liquidity_requests else None
        if active_lr:
            buyers = list(User.objects.filter(email__in=[
                'james.omo@example.com', 'faith.wambui@example.com'
            ]))

            for buyer in buyers:
                connection = Connection.objects.create(
                    liquidity_request=active_lr,
                    buyer=buyer,
                    seller=active_lr.seller,
                    status=random.choice([
                        ConnectionStatus.CONNECTED,
                        ConnectionStatus.OFFER_MADE,
                        ConnectionStatus.OFFER_COUNTERED,
                    ]),
                )

                if connection.status in [ConnectionStatus.OFFER_MADE, ConnectionStatus.OFFER_COUNTERED]:
                    offer = Offer.objects.create(
                        connection=connection,
                        offered_by=buyer,
                        price_per_share=active_lr.expected_price_per_share - Decimal(str(random.randint(5, 25))),
                        quantity=active_lr.share_quantity,
                        message='My offer for these shares.',
                    )

                    if connection.status == ConnectionStatus.OFFER_COUNTERED:
                        offer.counter(
                            new_price_per_share=offer.price_per_share + Decimal(str(random.randint(5, 15))),
                            message='Can you meet me halfway?',
                        )

        # Create an accepted connection ready for settlement
        if len(liquidity_requests) >= 2:
            lr2 = liquidity_requests[1]
            buyer2 = User.objects.get(email='david.mutua@example.com')
            connection2 = Connection.objects.create(
                liquidity_request=lr2,
                buyer=buyer2,
                seller=lr2.seller,
                status=ConnectionStatus.OFFER_MADE,
            )
            accepted_offer = Offer.objects.create(
                connection=connection2,
                offered_by=buyer2,
                price_per_share=lr2.expected_price_per_share - Decimal('10.00'),
                quantity=lr2.share_quantity,
            )

        self.stdout.write('  Created liquidity requests, interests, connections, and offers')

    # 7. SETTLEMENTS

    def create_settlements(self):
        from apps.investments.models import Connection, ConnectionStatus
        from apps.transactions.models import (
            LedgerEntry,
            SettlementEvent,
            SettlementEventTrigger,
            SettlementIntent,
            SettlementState,
        )

        accepted_connections = Connection.objects.filter(
            status=ConnectionStatus.OFFER_MADE
        )

        for conn in accepted_connections[:3]:
            from apps.core.utils import (
                calculate_settlement_fee,
                generate_idempotency_key,
            )

            latest_offer = conn.offers.first()
            if not latest_offer:
                continue

            amount = latest_offer.total_amount
            fee = calculate_settlement_fee(amount)

            intent = SettlementIntent.objects.create(
                idempotency_key=generate_idempotency_key(
                    str(conn.id), str(conn.buyer.id), str(conn.seller.id),
                    str(amount), str(latest_offer.quantity)
                ),
                state=SettlementState.LEDGER_FINALIZED,
                connection=conn,
                liquidity_request_id=conn.liquidity_request.id if conn.liquidity_request else None,
                buyer=conn.buyer,
                seller=conn.seller,
                amount=amount,
                share_quantity=latest_offer.quantity,
                price_per_share=latest_offer.price_per_share,
                platform_fee=fee,
                buyer_sacco_id=1,
                buyer_sacco_name='Stima SACCO',
                seller_sacco_id=1,
                seller_sacco_name='Stima SACCO',
                buyer_debit_ref=f'DEBIT-{random.randint(100000, 999999)}',
                seller_credit_ref=f'CREDIT-{random.randint(100000, 999999)}',
                matched_at=timezone.now() - timedelta(days=random.randint(1, 30)),
                locked_at=timezone.now() - timedelta(days=random.randint(1, 30), hours=1),
                buyer_debited_at=timezone.now() - timedelta(days=random.randint(1, 30), minutes=30),
                seller_credited_at=timezone.now() - timedelta(days=random.randint(1, 30), minutes=15),
                finalized_at=timezone.now() - timedelta(days=random.randint(1, 30)),
            )

            # Create settlement events
            events_sequence = [
                (SettlementState.MATCH_PROPOSED, SettlementEventTrigger.SYSTEM_MATCH, intent.matched_at),
                (SettlementState.INTENT_LOCKED, SettlementEventTrigger.INTENT_CREATED, intent.locked_at),
                (SettlementState.BUYER_DEBIT_INITIATED, SettlementEventTrigger.INTENT_CREATED, intent.locked_at),
                (SettlementState.BUYER_DEBIT_CONFIRMED, SettlementEventTrigger.BUYER_SACCO_SUCCESS, intent.buyer_debited_at),
                (SettlementState.SELLER_CREDIT_INITIATED, SettlementEventTrigger.INTENT_CREATED, intent.buyer_debited_at),
                (SettlementState.SELLER_CREDIT_CONFIRMED, SettlementEventTrigger.SELLER_SACCO_SUCCESS, intent.seller_credited_at),
                (SettlementState.LEDGER_FINALIZED, SettlementEventTrigger.SYSTEM_MATCH, intent.finalized_at),
            ]

            for state, trigger, timestamp in events_sequence:
                SettlementEvent.objects.create(
                    intent=intent,
                    from_state=events_sequence[events_sequence.index((state, trigger, timestamp)) - 1][0] if events_sequence.index((state, trigger, timestamp)) > 0 else SettlementState.MATCH_PROPOSED,
                    to_state=state,
                    trigger=trigger,
                    timestamp=timestamp,
                )

            # Create ledger entry
            LedgerEntry.objects.create(
                settlement=intent,
                buyer=conn.buyer,
                seller=conn.seller,
                sacco_id=1,
                share_quantity=latest_offer.quantity,
                price_per_share=latest_offer.price_per_share,
                total_amount=amount,
                platform_fee=fee,
            )

            # Update connection
            conn.status = ConnectionStatus.SETTLED
            conn.settlement_intent_id = intent.id
            conn.settled_at = intent.finalized_at
            conn.agreed_price_per_share = latest_offer.price_per_share
            conn.agreed_quantity = latest_offer.quantity
            conn.total_amount = amount
            conn.accepted_at = intent.buyer_debited_at
            conn.save()

            # Update liquidity request
            if conn.liquidity_request:
                conn.liquidity_request.status = 'SETTLED'
                conn.liquidity_request.save()

        # Create one disputed settlement
        if accepted_connections.count() >= 2:
            conn2 = accepted_connections[1]
            offer2 = conn2.offers.first()

            disputed = SettlementIntent.objects.create(
                idempotency_key=generate_idempotency_key(
                    str(conn2.id), 'disputed', str(conn2.buyer.id), str(conn2.seller.id)
                ),
                state=SettlementState.DISPUTED_MANUAL,
                connection=conn2,
                buyer=conn2.buyer,
                seller=conn2.seller,
                amount=offer2.total_amount if offer2 else Decimal('50000.00'),
                share_quantity=offer2.quantity if offer2 else Decimal('200.0000'),
                price_per_share=offer2.price_per_share if offer2 else Decimal('250.00'),
                platform_fee=Decimal('500.00'),
                buyer_sacco_id=1,
                buyer_sacco_name='Stima SACCO',
                seller_sacco_id=1,
                seller_sacco_name='Stima SACCO',
                buyer_debit_ref=f'DEBIT-{random.randint(100000, 999999)}',
                dispute_opened_at=timezone.now() - timedelta(hours=2),
            )

            SettlementEvent.objects.create(
                intent=disputed,
                from_state=SettlementState.BUYER_DEBIT_CONFIRMED,
                to_state=SettlementState.DISPUTED_MANUAL,
                trigger=SettlementEventTrigger.SELLER_SACCO_FAILURE,
                metadata={'error': 'API timeout on seller credit'},
            )

        self.stdout.write('  Created settlements with events and ledger entries')

    # 8. NOTIFICATIONS

    def create_notifications(self):
        from apps.notifications.models import (
            Notification,
            NotificationCategory,
            NotificationChannel,
            NotificationPriority,
        )

        users = User.objects.filter(is_active=True)[:8]

        notification_scenarios = [
            {
                'category': NotificationCategory.CHAMA_CONTRIBUTION,
                'priority': NotificationPriority.MEDIUM,
                'title': 'Contribution Received',
                'body': 'Your contribution of KSh 2,000 to Upendo Women Group has been received.',
                'action_url': '/chamas/contributions/',
            },
            {
                'category': NotificationCategory.CHAMA_LOAN,
                'priority': NotificationPriority.HIGH,
                'title': 'Loan Approved',
                'body': 'Your loan of KSh 20,000 from Jitegemee Investment Club has been approved.',
                'action_url': '/chamas/loans/',
            },
            {
                'category': NotificationCategory.INVESTMENT_OFFER,
                'priority': NotificationPriority.URGENT,
                'title': 'New Offer Received',
                'body': 'James O. offered KSh 350/share for your 200 shares in Mwalimu SACCO.',
                'action_url': '/investments/connections/',
            },
            {
                'category': NotificationCategory.SETTLEMENT,
                'priority': NotificationPriority.URGENT,
                'title': 'Settlement Complete',
                'body': 'Transaction complete: 200 shares transferred. KSh 70,000 credited.',
                'action_url': '/transactions/settlements/',
            },
            {
                'category': NotificationCategory.SYSTEM,
                'priority': NotificationPriority.LOW,
                'title': 'Welcome to Sacco Bridge',
                'body': 'Start by creating or joining a chama, or explore SACCO investment opportunities.',
                'action_url': '/dashboard/',
            },
            {
                'category': NotificationCategory.SECURITY,
                'priority': NotificationPriority.URGENT,
                'title': 'New Login Detected',
                'body': 'A new login was detected from Nairobi. If this was not you, secure your account.',
                'action_url': '/settings/security/',
            },
            {
                'category': NotificationCategory.CHAMA_MEETING,
                'priority': NotificationPriority.HIGH,
                'title': 'Meeting Reminder',
                'body': 'Monthly review meeting tomorrow at 5:30 PM at the Community Hall.',
                'action_url': '/chamas/meetings/',
            },
            {
                'category': NotificationCategory.INVESTMENT_CONNECTION,
                'priority': NotificationPriority.HIGH,
                'title': 'Buyer Interested',
                'body': 'Faith W. is interested in purchasing your shares in Stima SACCO.',
                'action_url': '/investments/connections/',
            },
        ]

        for user in users:
            for scenario in random.sample(notification_scenarios, min(3, len(notification_scenarios))):
                is_read = random.choice([True, False, False])
                read_at = timezone.now() - timedelta(hours=random.randint(1, 72)) if is_read else None
                created_at = timezone.now() - timedelta(
                    hours=random.randint(1, 168),
                    minutes=random.randint(0, 59)
                )

                Notification.objects.create(
                    user=user,
                    category=scenario['category'],
                    priority=scenario['priority'],
                    title=scenario['title'],
                    body=scenario['body'],
                    action_url=scenario['action_url'],
                    is_read=is_read,
                    read_at=read_at,
                    channels_sent=[NotificationChannel.IN_APP, NotificationChannel.PUSH],
                    created_at=created_at,
                    updated_at=created_at,
                )

        self.stdout.write('  Created sample notifications')

    # 9. ANALYTICS DATA

    def create_analytics_data(self):
        from apps.analytics.models import ChamaAnalytics, PlatformMetric
        from apps.chamas.models import Chama

        # Platform metrics for last 30 days
        for days_ago in range(30, -1, -1):
            metric_date = date.today() - timedelta(days=days_ago)
            PlatformMetric.objects.get_or_create(
                metric_date=metric_date,
                defaults={
                    'total_users': 100 + days_ago,
                    'new_users': random.randint(0, 10),
                    'verified_users': 80 + days_ago // 2,
                    'active_users': random.randint(30, 60),
                    'total_chamas': 20 + days_ago // 5,
                    'new_chamas': random.randint(0, 3),
                    'total_chama_members': 150 + days_ago,
                    'total_chama_savings': Decimal(str(500000 + days_ago * 10000)),
                    'total_chama_loans': Decimal(str(200000 + days_ago * 5000)),
                    'total_liquidity_requests': 15 + days_ago // 2,
                    'active_liquidity_requests': random.randint(3, 10),
                    'total_connections': 25 + days_ago,
                    'total_settlements': 10 + days_ago // 2,
                    'completed_settlements': 8 + days_ago // 2,
                    'reversed_settlements': random.randint(0, 2),
                    'disputed_settlements': random.randint(0, 1),
                    'total_settlement_volume': Decimal(str(200000 + days_ago * 5000)),
                    'total_platform_fees': Decimal(str(2000 + days_ago * 50)),
                    'total_saccos': 6,
                    'active_saccos': 6,
                }
            )

        # Chama analytics
        for chama in Chama.objects.filter(status='ACTIVE')[:3]:
            for month_ago in range(6, -1, -1):
                period_end = date.today().replace(day=1) - timedelta(days=1)
                for _ in range(month_ago):
                    if period_end.month == 1:
                        period_end = period_end.replace(year=period_end.year - 1, month=12, day=31)
                    else:
                        period_end = period_end.replace(month=period_end.month) - timedelta(days=1)

                period_start = period_end.replace(day=1)

                ChamaAnalytics.objects.get_or_create(
                    chama=chama,
                    period_start=period_start,
                    period_end=period_end,
                    defaults={
                        'period_type': 'MONTHLY',
                        'total_members': random.randint(8, 15),
                        'active_members': random.randint(6, 12),
                        'total_contributions': Decimal(str(random.randint(20000, 80000))),
                        'average_contribution': Decimal(str(random.randint(1000, 5000))),
                        'on_time_rate': Decimal(str(random.randint(70, 98))),
                        'late_contributions': random.randint(0, 5),
                        'missed_contributions': random.randint(0, 3),
                        'total_loans_issued': random.randint(2, 8),
                        'total_loan_amount': Decimal(str(random.randint(20000, 150000))),
                        'total_meetings': random.randint(1, 4),
                    }
                )

        self.stdout.write('  Created analytics data')

    # 10. KNOWLEDGE ARTICLES

    def create_knowledge_articles(self):
        from apps.chatbot.models import KnowledgeArticle, KnowledgeCategory

        articles = [
            {
                'title': 'How to Create a Chama on Sacco Bridge',
                'content': 'To create a chama on Sacco Bridge:\n\n1. Navigate to the Chamas section from your dashboard\n2. Click the "Create Chama" button\n3. Fill in your group details including name, type, and contribution amount\n4. Set your loan parameters and meeting schedule\n5. Share the invite code with your members\n\nYour chama will be ready immediately after creation.',
                'category': KnowledgeCategory.CHAMA_SETUP,
                'tags': ['chama', 'create', 'setup', 'group', 'invite'],
                'priority': 10,
            },
            {
                'title': 'Understanding SACCO Share Classes',
                'content': 'SACCOs typically offer different share classes:\n\n- Non-Withdrawable Deposits: Core membership shares that carry voting rights\n- Withdrawable Deposits: Savings that can be withdrawn subject to SACCO rules\n- Development Shares: Long-term investment shares for major projects\n- Special Class Shares: Custom share types for specific purposes\n\nEach class may have different dividend rates and transfer restrictions.',
                'category': KnowledgeCategory.SACCO_SHARES,
                'tags': ['sacco', 'shares', 'classes', 'dividends', 'voting'],
                'priority': 8,
            },
            {
                'title': 'How Loan Applications Work in Chamas',
                'content': 'Loan application process:\n\n1. Ensure you are up-to-date with your contributions\n2. Navigate to your chama and click "Request Loan"\n3. Enter the loan amount and purpose\n4. Your eligibility is calculated based on your total contributions\n5. The loan goes through your groups approval process\n6. Once approved, funds are disbursed to your account\n\nTypical interest rates range from 5-12% depending on your chama settings.',
                'category': KnowledgeCategory.LOANS,
                'tags': ['loan', 'borrow', 'application', 'approval', 'repayment'],
                'priority': 9,
            },
            {
                'title': 'Selling SACCO Shares for Liquidity',
                'content': 'To access liquidity from your SACCO shares:\n\n1. Go to Investments > My Holdings\n2. Select the shares you want to sell\n3. Create a Liquidity Request with your preferred timeline:\n   - Standard: Best price, within 1 week\n   - Priority: Faster match, within 48 hours\n   - Urgent: Quickest liquidity, within 24 hours\n4. Review buyer interests and connect with potential buyers\n5. Negotiate and accept an offer\n6. Settlement is handled securely by Sacco Bridge',
                'category': KnowledgeCategory.SELLING_SHARES,
                'tags': ['sell', 'liquidity', 'shares', 'buyer', 'cash'],
                'priority': 10,
            },
            {
                'title': 'How Settlement Works on Sacco Bridge',
                'content': 'Sacco Bridge uses a secure settlement process:\n\n1. Buyer and seller agree on terms\n2. Buyer funds are reserved in their SACCO account\n3. Funds are transferred to the seller\n4. Shares are transferred to the buyer\n5. The transaction is recorded in the immutable ledger\n\nAll settlements are guaranteed. If anything goes wrong, our trustee bank ensures your funds are protected.',
                'category': KnowledgeCategory.SETTLEMENTS,
                'tags': ['settlement', 'transfer', 'secure', 'guarantee', 'trustee'],
                'priority': 8,
            },
            {
                'title': 'M-Pesa Integration for Contributions',
                'content': 'Sacco Bridge integrates with M-Pesa for seamless contributions:\n\n1. Your chama can set up a Paybill number\n2. Members contribute via M-Pesa using the chama Paybill\n3. Contributions are automatically recorded and verified\n4. You receive instant confirmation\n\nTo set up M-Pesa integration, the chama treasurer needs to configure the Paybill details in chama settings.',
                'category': KnowledgeCategory.CONTRIBUTIONS,
                'tags': ['mpesa', 'paybill', 'contribution', 'payment', 'automatic'],
                'priority': 9,
            },
            {
                'title': 'Platform Fees and Pricing',
                'content': 'Sacco Bridge fee structure:\n\nChama Management:\n- Free tier: Basic tracking for up to 30 members\n- Premium tier: KSh 500-1,500/month per group\n\nSettlement Fees:\n- 1% for transactions up to KSh 100,000\n- 0.8% for KSh 100,001 to 500,000\n- 0.5% for transactions above KSh 500,000\n- Minimum fee: KSh 100\n- Maximum fee: KSh 10,000\n\nAll fees are transparent and displayed before you confirm any transaction.',
                'category': KnowledgeCategory.FEES_PRICING,
                'tags': ['fees', 'pricing', 'cost', 'premium', 'settlement'],
                'priority': 7,
            },
            {
                'title': 'Account Security Best Practices',
                'content': 'Protect your Sacco Bridge account:\n\n1. Enable two-factor authentication (2FA)\n2. Use a strong, unique password\n3. Never share your verification codes\n4. Review your login history regularly\n5. Log out from devices you no longer use\n6. Report any suspicious activity immediately\n\nSacco Bridge uses bank-grade encryption to protect your data and transactions.',
                'category': KnowledgeCategory.ACCOUNT_SECURITY,
                'tags': ['security', 'password', '2fa', 'authentication', 'safe'],
                'priority': 8,
            },
            {
                'title': 'Chama Meeting Management',
                'content': 'Managing chama meetings on Sacco Bridge:\n\n1. Schedule meetings with date, time, and location\n2. Members receive automatic notifications\n3. Record attendance during or after the meeting\n4. Document meeting minutes and decisions\n5. Track attendance history for all members\n\nRegular meetings help maintain group cohesion and ensure transparent operations.',
                'category': KnowledgeCategory.MEETINGS,
                'tags': ['meeting', 'schedule', 'attendance', 'minutes', 'group'],
                'priority': 6,
            },
            {
                'title': 'Getting Started with Sacco Bridge',
                'content': 'Welcome to Sacco Bridge! Here is how to get started:\n\n1. Complete your profile with KYC information\n2. Verify your email and phone number\n3. Choose your path:\n   - Chama Member: Create or join a chama\n   - Investor: Browse SACCO investment opportunities\n   - Seller: List your SACCO shares for liquidity\n4. Explore the dashboard for personalized insights\n5. Use the AI assistant for any questions\n\nWe are here to help you make the most of cooperative finance!',
                'category': KnowledgeCategory.PLATFORM_BASICS,
                'tags': ['getting started', 'welcome', 'onboarding', 'new user', 'guide'],
                'priority': 10,
            },
                        {
                'title': 'How Bulk Contributions Work',
                'content': 'Bulk contributions allow chama treasurers and officials to record contributions for multiple members at once.\n\nHow to use:\n1. Navigate to your chama > Contributions > Bulk Record\n2. Enter the contribution period (start and end dates)\n3. Add each member\'s contribution:\n   - Select the member\n   - Enter the amount\n   - Choose payment method (M-Pesa, Cash, Bank Transfer)\n   - Add a payment reference if available\n4. Submit all contributions at once\n\nBenefits:\n- Save time after physical meetings\n- Reduce data entry errors\n- All contributions are recorded in a single transaction for consistency\n\nOnly chama officials (Chairperson, Treasurer, Secretary) can record bulk contributions.',
                'category': KnowledgeCategory.CONTRIBUTIONS,
                'tags': ['bulk', 'contributions', 'treasurer', 'multiple', 'batch'],
                'priority': 8,
            },
            {
                'title': 'How to Sign Up with Google',
                'content': 'You can create a Sacco Bridge account using your Google account:\n\n1. On the login screen, tap "Continue with Google"\n2. Select your Google account\n3. Grant the requested permissions\n4. Your account is created automatically with your Google email and name\n\nAfter Google sign-up:\n- Your email is automatically verified by Google\n- You need to add a Kenyan phone number to access all features\n- Go to Profile > Add Phone Number\n- Enter your phone number and verify it with the SMS code\n\nNote: Google OAuth users start with a basic profile. Complete your profile by adding your phone number, occupation, and county for full access.',
                'category': KnowledgeCategory.ACCOUNT_SECURITY,
                'tags': ['google', 'oauth', 'signup', 'login', 'phone', 'verify'],
                'priority': 9,
            },
            {
                'title': 'How to Reset Your Password',
                'content': 'Forgot your password? Here is how to reset it:\n\n1. On the login screen, tap "Forgot Password?"\n2. Enter your registered email address\n3. Check your email for a password reset link\n4. Click the link (valid for 24 hours)\n5. Enter your new password (minimum 12 characters with uppercase, lowercase, numbers, and special characters)\n6. Confirm your new password\n7. Login with your new password\n\nIf you do not receive the email:\n- Check your spam/junk folder\n- Ensure you entered the correct email address\n- Contact support if the issue persists\n\nSecurity tip: Never share your password reset link with anyone. Sacco Bridge will never ask for your password.',
                'category': KnowledgeCategory.ACCOUNT_SECURITY,
                'tags': ['password', 'reset', 'forgot', 'email', 'security'],
                'priority': 9,
            },
            {
                'title': 'How to Download Receipts and View Statements',
                'content': 'Sacco Bridge generates receipts for all your financial transactions:\n\nReceipts are created for:\n- Chama contributions\n- Loan repayments\n- SACCO share purchases and sales\n\nTo download a receipt:\n1. Go to your profile or transaction history\n2. Find the transaction you want a receipt for\n3. Tap the receipt icon or "Download PDF"\n4. The receipt includes:\n   - Transaction details (date, amount, reference)\n   - Parties involved\n   - QR code for verification\n   - Sacco Bridge branding\n\nReceipts are PDF files that you can save, print, or share. Each receipt has a unique verification code that can be checked on the platform.',
                'category': KnowledgeCategory.SETTLEMENTS,
                'tags': ['receipt', 'download', 'pdf', 'statement', 'transaction', 'history'],
                'priority': 8,
            },
            {
                'title': 'Understanding Dispute Resolution',
                'content': 'Sacco Bridge guarantees every settlement. If something goes wrong, here is how disputes are handled:\n\nWhat triggers a dispute:\n- A SACCO\'s banking system fails during settlement\n- A network timeout occurs during funds transfer\n- Conflicting transaction confirmations\n\nOur dispute process:\n1. The system automatically detects settlement issues\n2. Automated recovery attempts are made (up to 3 retries)\n3. If unresolved, our disputes team is notified immediately\n4. The team contacts the involved SACCOs to verify transaction status\n5. Resolution is applied based on verified information:\n   - If seller was credited: settlement is completed\n   - If seller was not credited: buyer\'s funds are reversed\n\nAll disputes are tracked with a unique reference number. You can check the status anytime from your transaction history.\n\nTrustee Guarantee: If a dispute cannot be resolved within 48 hours, our partner trustee bank intervenes to ensure no member loses their funds.',
                'category': KnowledgeCategory.DISPUTES,
                'tags': ['dispute', 'resolution', 'settlement', 'trustee', 'guarantee'],
                'priority': 10,
            },
            {
                'title': 'How to Pay Using M-Pesa STK Push',
                'content': 'Sacco Bridge integrates with M-Pesa for seamless payments:\n\nTo make a payment:\n1. Navigate to the payment section (contributions, loan repayments, etc.)\n2. Select M-Pesa as your payment method\n3. Enter the amount and confirm\n4. An STK Push notification will appear on your phone\n5. Enter your M-Pesa PIN to complete the payment\n6. The payment is confirmed automatically\n\nImportant notes:\n- The phone number must match your registered Sacco Bridge number\n- Ensure you have sufficient M-Pesa balance\n- Keep your phone unlocked to receive the STK Push\n- The payment reference is recorded automatically\n\nIf the STK Push does not arrive:\n- Check your phone network connection\n- Ensure you are not in a USSD session\n- Wait 2 minutes and try again\n- Contact support if the issue persists',
                'category': KnowledgeCategory.CONTRIBUTIONS,
                'tags': ['mpesa', 'stk', 'push', 'payment', 'pin', 'lipa'],
                'priority': 10,
            },
            {
                'title': 'How Offer Negotiation Works',
                'content': 'When buying or selling SACCO shares, you negotiate directly with the other party:\n\nMaking an Offer:\n1. After connecting with a buyer/seller, you can make an offer\n2. Enter your price per share and quantity\n3. Add an optional message\n4. Submit the offer\n\nResponding to Offers:\n- Accept: Agree to the terms. Settlement begins immediately.\n- Decline: Reject the offer. You can make a new offer.\n- Counter: Propose different terms. The other party can then accept, decline, or counter back.\n\nTips for negotiation:\n- Review the SACCO\'s current market price and dividend history\n- Consider the seller\'s urgency level (Standard, Priority, Urgent)\n- Urgent sellers may accept lower prices for faster liquidity\n- All offers are non-binding until accepted\n\nOnce an offer is accepted, Sacco Bridge handles the secure settlement. Neither party can back out after acceptance.',
                'category': KnowledgeCategory.BUYING_SHARES,
                'tags': ['offer', 'negotiate', 'counter', 'accept', 'decline', 'price'],
                'priority': 9,
            },
            {
                'title': 'Chama Roles and Permissions Explained',
                'content': 'Each chama has different roles with specific responsibilities:\n\nChairperson:\n- Oversees all chama operations\n- Can approve loans and manage members\n- Has full access to chama settings and reports\n\nTreasurer:\n- Manages chama finances\n- Records contributions (including bulk recording)\n- Approves and disburses loans\n- Tracks chama savings and loan repayments\n\nSecretary:\n- Manages meetings and attendance\n- Sends announcements to members\n- Maintains chama records\n\nLoan Officer:\n- Reviews loan applications\n- Makes recommendations on approvals\n\nMember:\n- Makes contributions\n- Applies for loans\n- Views own records and chama information\n\nNote: These roles are specific to each chama. Being a Treasurer in one chama does not give you any privileges in another chama.',
                'category': KnowledgeCategory.CHAMA_BASICS,
                'tags': ['roles', 'chairperson', 'treasurer', 'secretary', 'permissions', 'admin'],
                'priority': 9,
            },
            {
                'title': 'How to Set Up Two-Factor Authentication',
                'content': 'Two-factor authentication (2FA) adds an extra layer of security to your account:\n\nTo enable 2FA:\n1. Go to Profile > Security > Two-Factor Authentication\n2. Tap "Enable 2FA"\n3. A QR code will appear\n4. Open your authenticator app (Google Authenticator, Authy, etc.)\n5. Scan the QR code or enter the setup key manually\n6. Enter the 6-digit code from your authenticator app to verify\n7. 2FA is now enabled\n\nAfter enabling:\n- Each login will require your password AND a code from your authenticator app\n- Save your backup codes in a safe place\n- If you lose access to your authenticator app, contact support\n\nTo disable 2FA:\n1. Go to Profile > Security > Two-Factor Authentication\n2. Enter your current authenticator code\n3. Confirm to disable',
                'category': KnowledgeCategory.ACCOUNT_SECURITY,
                'tags': ['2fa', 'two-factor', 'authenticator', 'security', 'totp'],
                'priority': 7,
            },
            {
                'title': 'Understanding Your Trust Score',
                'content': 'Your trust score is a measure of your reliability on Sacco Bridge (0.00 to 5.00):\n\nWhat improves your score:\n- Consistent on-time chama contributions (+0.05 per contribution)\n- Repaying loans fully and on time (+0.20 per loan)\n- Completing SACCO share transactions successfully (+0.10 per settlement)\n- Verifying your identity (+1.00)\n\nWhat affects your score negatively:\n- Late or missed contributions\n- Defaulting on loans\n- Disputed transactions\n\nWhy your trust score matters:\n- Higher scores may qualify you for larger loans\n- Buyers and sellers see your score during negotiations\n- Some chamas may require a minimum trust score to join\n\nYour trust score is calculated automatically based on your platform activity. It updates after each relevant transaction.',
                'category': KnowledgeCategory.PLATFORM_BASICS,
                'tags': ['trust', 'score', 'reputation', 'reliability', 'rating'],
                'priority': 7,
            },
            {
                'title': 'SACCO Dividends When Buying Shares Mid-Cycle',
                'content': 'When you buy SACCO shares through Sacco Bridge, dividend treatment depends on timing:\n\nBefore dividend declaration:\n- If you buy shares before the SACCO declares dividends, you receive the full dividend for that period\n\nAfter dividend declaration but before payment:\n- The seller typically retains the right to the declared dividend\n- This should be negotiated as part of your offer\n\nAfter dividend payment:\n- You will receive dividends from the next declaration cycle\n- Past dividends belong to the previous owner\n\nImportant:\n- Different SACCOs have different dividend schedules\n- Check the SACCO\'s dividend history and declaration dates before buying\n- Dividend rates shown are historical and not guaranteed for future periods\n- Sacco Bridge does not guarantee dividend payments - these are determined by each SACCO',
                'category': KnowledgeCategory.BUYING_SHARES,
                'tags': ['dividend', 'shares', 'timing', 'cycle', 'payment'],
                'priority': 8,
            },
            {
                'title': 'How Loan Guarantors Work',
                'content': 'Some chamas require guarantors for loans:\n\nWhat is a guarantor:\n- A fellow chama member who agrees to repay your loan if you cannot\n- Guarantors share the responsibility for loan repayment\n\nGuarantor requirements (set by each chama):\n- Number of guarantors needed (typically 1-3)\n- Guarantors must be active members in good standing\n- Guarantors must have sufficient savings to cover the loan\n\nGuarantor responsibilities:\n- If the borrower defaults, guarantors are contacted to repay\n- Guarantor\'s own savings may be used to cover the defaulted loan\n- Being a guarantor affects your ability to borrow (your guarantee counts as a liability)\n\nBefore agreeing to be a guarantor:\n- Ensure you trust the borrower\n- Understand the loan terms and repayment schedule\n- Know that your savings could be at risk\n\nTip: Check a member\'s contribution history and trust score before agreeing to guarantee their loan.',
                'category': KnowledgeCategory.LOANS,
                'tags': ['guarantor', 'loan', 'liability', 'repayment', 'default'],
                'priority': 8,
            },
            {
                'title': 'How to Leave a Chama',
                'content': 'You can leave a chama through Sacco Bridge, but there are important conditions:\n\nRequirements to leave:\n1. You must have no outstanding loans\n2. All your loan guarantor obligations must be cleared\n3. Any pending contributions should be settled\n\nHow to leave:\n1. Go to your chama > Settings > Leave Chama\n2. Review your current balance and any restrictions\n3. Confirm you want to leave\n4. Your membership is deactivated\n\nWhat happens to your savings:\n- Your accumulated contributions remain in the chama records\n- Payout follows the chama\'s normal distribution schedule\n- You cannot withdraw your savings early unless the chama allows it\n\nBefore leaving:\n- Check if there are any pending loan approvals you guaranteed\n- Download your contribution history for your records\n- Inform your chama officials\n\nNote: Leaving a chama may affect your trust score if you have unfulfilled obligations.',
                'category': KnowledgeCategory.CHAMA_BASICS,
                'tags': ['leave', 'exit', 'withdraw', 'membership', 'chama'],
                'priority': 7,
            },
            {
                'title': 'How to Configure Notification Preferences',
                'content': 'Control how Sacco Bridge communicates with you:\n\nNotification channels:\n- In-App: Messages within the Sacco Bridge app\n- Push: Notifications on your phone (requires Firebase setup)\n- SMS: Text messages to your phone\n- Email: Messages to your email address\n\nTo configure:\n1. Go to Profile > Notifications > Preferences\n2. For each category, toggle which channels you want:\n   - Chama Contributions\n   - Chama Loans\n   - Investment Opportunities\n   - Settlement Updates\n   - Security Alerts\n\nQuiet Hours:\n- Set times when push notifications are silenced\n- SMS and email are not affected by quiet hours\n\nRecommended settings:\n- Keep security alerts enabled on all channels\n- Enable SMS for urgent updates (loan approvals, settlements)\n- Use in-app notifications for general updates',
                'category': KnowledgeCategory.PLATFORM_BASICS,
                'tags': ['notifications', 'preferences', 'sms', 'email', 'push', 'quiet hours'],
                'priority': 6,
            },
        ]

        admin = User.objects.filter(email='admin@saccobridge.co.ke').first()

        for article_data in articles:
            KnowledgeArticle.objects.get_or_create(
                title=article_data['title'],
                defaults={
                    **article_data,
                    'is_published': True,
                    'authored_by': admin,
                    'reviewed_by': admin,
                    'reviewed_at': timezone.now(),
                }
            )

        self.stdout.write('  Created knowledge base articles')

    # 11. CHAT SESSIONS

    def create_chat_sessions(self):
        from apps.chatbot.models import ChatMessage, ChatSession, SessionType

        users = User.objects.filter(is_active=True)[:5]

        sample_conversations = [
            {
                'session_type': SessionType.CHAMA_SETUP,
                'messages': [
                    ('USER', 'How do I create a chama for my women group?'),
                    ('ASSISTANT', 'To create a chama on Sacco Bridge, navigate to the Chamas section and click "Create Chama". You will need to provide your group name, contribution amount, frequency, and member details. Would you like step-by-step guidance?'),
                    ('USER', 'Yes please, and what contribution frequency works best?'),
                    ('ASSISTANT', 'For most welfare groups, weekly contributions of KSh 1,000-2,000 work well as they are manageable and build savings quickly. Monthly contributions of KSh 3,000-5,000 are better for investment clubs. What type of group are you forming?'),
                ],
            },
            {
                'session_type': SessionType.INVESTMENT_GUIDANCE,
                'messages': [
                    ('USER', 'I want to buy SACCO shares. Which SACCO has the best dividends?'),
                    ('ASSISTANT', 'Based on current platform data, Mwalimu National SACCO offers 14.5% dividends, Stima SACCO offers 12.8%, and Unaitas SACCO offers 13.0%. However, past dividends do not guarantee future returns. Would you like to browse current sellers for any of these SACCOs?'),
                    ('USER', 'Show me what is available for Mwalimu SACCO.'),
                    ('ASSISTANT', 'There are currently 3 sellers offering Mwalimu SACCO shares ranging from KSh 280-320 per share. You can browse these opportunities in the Investments section under "Opportunities". Would you like me to help you express interest in any of them?'),
                ],
            },
            {
                'session_type': SessionType.SETTLEMENT_HELP,
                'messages': [
                    ('USER', 'My settlement has been stuck for over an hour. What should I do?'),
                    ('ASSISTANT', 'I understand your concern. Settlement delays can happen due to SACCO system issues. Your funds are protected by our settlement guarantee. Can you provide your transaction reference number so I can check the status?'),
                    ('USER', 'The reference is CHX-SET-abc-123'),
                    ('ASSISTANT', 'I can see your settlement is in the "Seller Credit Initiated" state. This means the buyer funds have been debited and we are waiting for confirmation from the seller SACCO. Our recovery system automatically retries every few minutes. If not resolved within 2 hours, our disputes team will be notified. Your funds are secure.'),
                ],
            },
        ]

        for i, user in enumerate(users):
            if i >= len(sample_conversations):
                break

            conv = sample_conversations[i]
            session = ChatSession.objects.create(
                user=user,
                session_type=conv['session_type'],
                title=conv['messages'][0][1][:80] + '...',
                is_active=True,
                context_data={
                    'user_name': user.get_full_name(),
                },
            )

            for role, content in conv['messages']:
                ChatMessage.objects.create(
                    session=session,
                    role=role,
                    content=content,
                    ai_model='gemini-1.5-flash' if role == 'ASSISTANT' else '',
                )

        self.stdout.write('  Created sample chat sessions')

    # 12. POLLS AND VOTES

    def create_polls_and_votes(self):
        from apps.chamas.models import Chama, ChamaMember, Poll, PollOption, Vote

        chamas = Chama.objects.filter(status='ACTIVE')[:3]

        for chama in chamas:
            members = list(chama.memberships.filter(is_active=True)[:10])
            if len(members) < 3:
                continue

            admin = members[0]

            poll = Poll.objects.create(
                chama=chama,
                title=random.choice([
                    'Should we increase monthly contributions?',
                    'Approve new member: Jane Doe?',
                    'Change meeting day to Saturday?',
                    'Invest group savings in SACCO shares?',
                ]),
                description='Please cast your vote on this important matter.',
                created_by=admin,
                voting_method=random.choice(['MAJORITY', 'TWO_THIRDS', 'UNANIMOUS']),
                is_anonymous=False,
                is_active=True,
            )

            options = ['Yes', 'No', 'Abstain']
            for i, opt_text in enumerate(options):
                PollOption.objects.create(poll=poll, option_text=opt_text, order=i)

            for member in members[1:6]:
                option = poll.options.order_by('?').first()
                if option and not Vote.objects.filter(poll=poll, voter=member).exists():
                    Vote.objects.create(poll=poll, option=option, voter=member)

        self.stdout.write('  Created polls and votes')

    # 13. CONSTITUTIONS AND AGREEMENTS

    def create_constitutions_and_agreements(self):
        from apps.chamas.models import Chama, ChamaMember, ConstitutionAgreement

        chamas = Chama.objects.filter(status='ACTIVE')[:2]

        for chama in chamas:
            chama.constitution_version = '1.0'
            chama.constitution_uploaded_at = timezone.now() - timedelta(days=30)
            chama.save(update_fields=['constitution_version', 'constitution_uploaded_at'])

            members = chama.memberships.filter(is_active=True)[:5]
            for member in members:
                ConstitutionAgreement.objects.get_or_create(
                    member=member,
                    chama=chama,
                    version='1.0',
                    defaults={'agreed_at': timezone.now() - timedelta(days=random.randint(1, 30))},
                )

        self.stdout.write('  Created constitutions and agreements')

    # 14. DISPUTES

    def create_disputes(self):
        from apps.transactions.models import (
            Dispute,
            DisputeReason,
            DisputeStatus,
            SettlementIntent,
            SettlementState,
        )

        settlements = SettlementIntent.objects.filter(
            state__in=['INTENT_LOCKED', 'BUYER_DEBIT_CONFIRMED', 'SELLER_CREDIT_INITIATED']
        )[:2]

        for settlement in settlements:
            Dispute.objects.get_or_create(
                settlement=settlement,
                raised_by=settlement.buyer,
                defaults={
                    'reason': random.choice([
                        DisputeReason.FUNDS_DEBITED_NO_SHARES,
                        DisputeReason.SETTLEMENT_STUCK,
                    ]),
                    'description': 'Automated test dispute for development.',
                    'status': DisputeStatus.OPEN,
                },
            )

        self.stdout.write('  Created sample disputes')

    # 15. FRAUD ASSESSMENTS

    def create_fraud_assessments(self):
        from apps.fraud.models import (
            RiskLevel,
            FraudAction,
            TransactionRiskAssessment,
        )
        from apps.transactions.models import SettlementIntent

        users = User.objects.filter(is_active=True)[:5]
        settlements = SettlementIntent.objects.filter(
            state='LEDGER_FINALIZED'
        )[:5]

        for i, settlement in enumerate(settlements):
            user = users[i % len(users)] if users else settlement.buyer

            TransactionRiskAssessment.objects.create(
                user=user,
                transaction_type='SETTLEMENT',
                transaction_reference=str(settlement.uuid),
                amount=settlement.amount,
                risk_score=random.randint(5, 45),
                risk_level=RiskLevel.LOW,
                recommended_action=FraudAction.ALLOW,
                applied_action=FraudAction.ALLOW,
                triggers=['NORMAL_TRANSACTION'],
                velocity_24h_count=random.randint(0, 5),
                velocity_24h_total=settlement.amount,
                ip_address='127.0.0.1',
                ip_reputation_score=random.randint(50, 100),
            )

        self.stdout.write('  Created fraud assessments')

    # 16. CREDIT SCORES

    def create_credit_scores(self):
        from apps.chamas.models import Chama, ChamaMember
        from apps.scoring.models import CreditScore

        chamas = Chama.objects.filter(status='ACTIVE')[:3]

        for chama in chamas:
            members = chama.memberships.filter(is_active=True)[:5]
            for member in members:
                score = random.randint(450, 850)

                CreditScore.objects.create(
                    user=member.user,
                    chama=chama,
                    score=score,
                    grade=CreditScore.get_grade(score),
                    contribution_score=random.randint(50, 250),
                    repayment_score=random.randint(50, 250),
                    attendance_score=random.randint(30, 150),
                    savings_score=random.randint(20, 100),
                    trust_score=random.randint(20, 100),
                    valid_until=timezone.now() + timedelta(days=30),
                )

        self.stdout.write('  Created credit scores')

    # 17. ESCROW ACCOUNTS

    def create_escrow_accounts(self):
        from apps.escrow.models import EscrowAccount, EscrowStatus
        from apps.transactions.models import SettlementIntent

        settlements = SettlementIntent.objects.filter(
            state='LEDGER_FINALIZED'
        )[:3]

        for settlement in settlements:
            EscrowAccount.objects.get_or_create(
                settlement=settlement,
                defaults={
                    'buyer': settlement.buyer,
                    'seller': settlement.seller,
                    'amount': settlement.amount,
                    'platform_fee': settlement.platform_fee,
                    'status': EscrowStatus.RELEASED,
                    'buyer_ref': settlement.buyer_debit_ref,
                    'seller_ref': settlement.seller_credit_ref,
                    'funded_at': settlement.buyer_debited_at,
                    'released_at': settlement.seller_credited_at,
                    'completed_at': settlement.finalized_at,
                },
            )

        self.stdout.write('  Created escrow accounts')

    # 18. WEBHOOK SUBSCRIPTIONS

    def create_webhook_subscriptions(self):
        from apps.webhooks.models import WebhookSubscription, WebhookEventType

        WebhookSubscription.objects.get_or_create(
            url='https://webhook.site/test-sacco-bridge',
            defaults={
                'name': 'Test Webhook Endpoint',
                'is_active': True,
                'events': [
                    WebhookEventType.SETTLEMENT_COMPLETED,
                    WebhookEventType.OFFER_ACCEPTED,
                    WebhookEventType.LIQUIDITY_REQUEST_CREATED,
                ],
            },
        )

        self.stdout.write('  Created webhook subscriptions')

    # 19. LEGAL DOCUMENTS

    def create_legal_documents(self):
        from apps.legal.models import LegalDocument, LegalDocumentType

        admin = User.objects.filter(email='admin@saccobridge.co.ke').first()

        terms, _ = LegalDocument.objects.get_or_create(
            document_type=LegalDocumentType.TERMS_AND_CONDITIONS,
            version='1.0.0',
            defaults={
                'title': 'Terms & Conditions v1.0',
                'content': 'These are the Terms and Conditions for Sacco Bridge. By using this platform, you agree to these terms.\n\n1. Account Registration\n2. Chama Operations\n3. SACCO Share Trading\n4. Fees and Payments\n5. Dispute Resolution\n6. Limitation of Liability\n7. Same-SACCO Trading Restriction',
                'summary': 'Initial release of Terms and Conditions covering platform usage, chama operations, SACCO trading, and dispute resolution.',
                'is_current': True,
                'published_at': timezone.now() - timedelta(days=90),
                'published_by': admin,
            },
        )

        privacy, _ = LegalDocument.objects.get_or_create(
            document_type=LegalDocumentType.PRIVACY_POLICY,
            version='1.0.0',
            defaults={
                'title': 'Privacy Policy v1.0',
                'content': 'This Privacy Policy explains how Sacco Bridge collects, uses, and protects your personal data.\n\n1. Information We Collect\n2. How We Use Your Data\n3. Data Protection\n4. Your Rights\n5. Contact Information',
                'summary': 'Initial release of Privacy Policy covering data collection, usage, protection, and user rights.',
                'is_current': True,
                'published_at': timezone.now() - timedelta(days=90),
                'published_by': admin,
            },
        )

        self.stdout.write('  Created legal documents')