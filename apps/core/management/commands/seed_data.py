import random
from decimal import Decimal
from datetime import date, timedelta, datetime, time
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import transaction

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

        self.stdout.write(self.style.SUCCESS('Database seeded successfully!'))

    # ============================================================
    # 1. PLATFORM ADMIN
    # ============================================================

    def create_platform_admin(self):
        """Create platform admin user with all permissions."""
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
        if created:
            admin.set_password('AdminPass@2026')
            admin.save()
            admin.add_role(Role.PLATFORM_ADMIN)
            admin.add_role(Role.SUPPORT_AGENT)
            self.stdout.write(f'  Created platform admin: {admin.email}')

    # ============================================================
    # 2. SACCOS AND SHARE CLASSES
    # ============================================================

    def create_saccos_and_share_classes(self):
        """Create verified SACCOs with share classes and market data."""
        from apps.investments.models import (
            SACCO, SACCOShareClass, ShareClass, SASRATier, SACCOStatus,
            SACCOMarketAnalytics
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

    # ============================================================
    # 3. USERS WITH PROFILES
    # ============================================================

    def create_users_with_profiles(self):
        """Create diverse user personas with profiles and roles."""
        from apps.users.models import Role, UserProfile

        users_data = [
            # Sellers seeking liquidity
            {
                'email': 'mary.akinyi@example.com',
                'phone': '0711000001',
                'first': 'Mary', 'last': 'Akinyi',
                'roles': [Role.SELLER, Role.CHAMA_MEMBER],
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
                'roles': [Role.SELLER, Role.CHAMA_TREASURER],
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
                'roles': [Role.INVESTOR, Role.CHAMA_CHAIRPERSON],
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
                'roles': [Role.INVESTOR, Role.CHAMA_MEMBER],
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
                'roles': [Role.CHAMA_TREASURER, Role.CHAMA_MEMBER],
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
                'roles': [Role.CHAMA_SECRETARY],
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
                'roles': [Role.CHAMA_MEMBER, Role.SELLER],
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

    # ============================================================
    # 4. CHAMAS WITH FULL DATA
    # ============================================================

    def create_chamas_with_full_data(self):
        """Create chamas with members, contributions, loans, and meetings."""
        from apps.chamas.models import (
            Chama, ChamaMember, Contribution, Loan, LoanRepayment,
            Meeting, MeetingAttendance, MemberRole as ChamaMemberRole,
            ContributionFrequency, ContributionStatus, LoanStatus,
            PaymentMethod, MeetingStatus
        )
        from apps.users.models import Role as UserRole

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
                        'member_since': date.today() - timedelta(days=random.randint(30, 730)),
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

    # ============================================================
    # 5. SACCO HOLDINGS
    # ============================================================

    def create_sacco_holdings(self):
        """Create SACCO share holdings for users."""
        from apps.investments.models import SACCO, SACCOShareClass, SACCOMemberHolding

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

    # ============================================================
    # 6. LIQUIDITY REQUESTS AND CONNECTIONS
    # ============================================================

    def create_liquidity_requests_and_connections(self):
        """Create liquidity requests with buyer interests and connections."""
        from apps.investments.models import (
            SACCO, SACCOShareClass, SACCOMemberHolding,
            LiquidityRequest, BuyerInterest, Connection, Offer,
            LiquidityRequestStatus, UrgencyLevel, ConnectionStatus
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

    # ============================================================
    # 7. SETTLEMENTS
    # ============================================================

    def create_settlements(self):
        """Create settlement intents with events and ledger entries."""
        from apps.transactions.models import (
            SettlementIntent, SettlementEvent, LedgerEntry,
            SettlementState, SettlementEventTrigger
        )
        from apps.investments.models import Connection, ConnectionStatus

        accepted_connections = Connection.objects.filter(
            status=ConnectionStatus.OFFER_MADE
        )

        for conn in accepted_connections[:3]:
            from apps.core.utils import calculate_settlement_fee, generate_idempotency_key

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

    # ============================================================
    # 8. NOTIFICATIONS
    # ============================================================

    def create_notifications(self):
        """Create sample notifications for users."""
        from apps.notifications.models import (
            Notification, NotificationCategory, NotificationPriority,
            NotificationChannel
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

    # ============================================================
    # 9. ANALYTICS DATA
    # ============================================================

    def create_analytics_data(self):
        """Create platform metrics and chama analytics."""
        from apps.analytics.models import PlatformMetric, ChamaAnalytics
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

    # ============================================================
    # 10. KNOWLEDGE ARTICLES
    # ============================================================

    def create_knowledge_articles(self):
        """Create knowledge base articles for the AI chatbot."""
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

    # ============================================================
    # 11. CHAT SESSIONS
    # ============================================================

    def create_chat_sessions(self):
        """Create sample chat sessions with messages."""
        from apps.chatbot.models import ChatSession, ChatMessage, SessionType, MessageRole

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