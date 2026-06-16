import csv
import io
import logging
from datetime import datetime
from decimal import Decimal

from celery import shared_task
from django.core.files.base import ContentFile
from django.utils import timezone

from apps.reports.models import ReportRequest, ReportType

logger = logging.getLogger(__name__)


@shared_task(
    name='apps.reports.tasks.generate_report',
    bind=True,
    max_retries=2,
    default_retry_delay=300,
)
def generate_report(self, report_id):
    try:
        report = ReportRequest.objects.get(id=report_id)
    except ReportRequest.DoesNotExist:
        logger.error(f"Report {report_id} not found")
        return {'error': 'Report not found'}

    report.mark_processing(self.request.id)

    try:
        if report.report_type == ReportType.TRANSACTION_HISTORY:
            content, count = generate_transaction_history(report)
        elif report.report_type == ReportType.CONTRIBUTION_REPORT:
            content, count = generate_contribution_report(report)
        elif report.report_type == ReportType.LOAN_STATEMENT:
            content, count = generate_loan_statement(report)
        elif report.report_type == ReportType.MEMBER_LIST:
            content, count = generate_member_list(report)
        elif report.report_type == ReportType.CHAMA_FINANCIAL:
            content, count = generate_chama_financial(report)
        elif report.report_type == ReportType.DIVIDEND_STATEMENT:
            content, count = generate_dividend_statement(report)
        else:
            report.mark_failed(f"Unknown report type: {report.report_type}")
            return {'error': 'Unknown report type'}

        # Save the file
        filename = f"{report.report_type.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        report.mark_completed(
            report_file=ContentFile(content, name=filename),
            file_size=len(content),
            record_count=count,
        )

        logger.info(f"Report {report_id} generated: {count} records, {len(content)} bytes")
        return {'status': 'completed', 'record_count': count}

    except Exception as e:
        logger.error(f"Report generation failed for {report_id}: {str(e)}")
        report.mark_failed(str(e))
        raise self.retry(exc=e)


def format_kes(amount):
    """Format amount in Kenyan Shillings."""
    if amount is None:
        return '0.00'
    return f"{Decimal(str(amount)):,.2f}"


def write_csv_header(writer, headers):
    writer.writerow(headers)


def generate_transaction_history(report):
    from apps.transactions.models import SettlementIntent

    filters = report.filters or {}
    date_from = filters.get('date_from')
    date_to = filters.get('date_to')

    settlements = SettlementIntent.objects.filter(
        models.Q(buyer=report.user) | models.Q(seller=report.user),
        is_deleted=False,
    ).select_related('buyer', 'seller')

    if date_from:
        settlements = settlements.filter(created_at__date__gte=date_from)
    if date_to:
        settlements = settlements.filter(created_at__date__lte=date_to)

    settlements = settlements.order_by('-created_at')

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    write_csv_header(writer, [
        'Date', 'Transaction ID', 'Type', 'SACCO', 'Shares',
        'Price/Share (KSh)', 'Total (KSh)', 'Fee (KSh)',
        'Counterparty', 'Status'
    ])

    count = 0
    for s in settlements:
        is_buyer = s.buyer == report.user
        counterparty = s.seller.get_full_name() if is_buyer else s.buyer.get_full_name()
        tx_type = 'Purchase' if is_buyer else 'Sale'

        writer.writerow([
            s.created_at.strftime('%Y-%m-%d %H:%M'),
            str(s.uuid)[:8],
            tx_type,
            s.seller_sacco_name,
            str(s.share_quantity),
            format_kes(s.price_per_share),
            format_kes(s.amount),
            format_kes(s.platform_fee),
            counterparty,
            s.get_state_display(),
        ])
        count += 1

    return buffer.getvalue(), count


def generate_contribution_report(report):
    from apps.chamas.models import ChamaMember, Contribution

    filters = report.filters or {}
    chama_id = filters.get('chama_id')
    date_from = filters.get('date_from')
    date_to = filters.get('date_to')

    member = ChamaMember.objects.filter(
        user=report.user, is_active=True
    ).first()

    if not member:
        return '', 0

    contributions = Contribution.objects.filter(
        member=member,
        is_deleted=False,
    )

    if chama_id:
        contributions = contributions.filter(chama_id=chama_id)
    if date_from:
        contributions = contributions.filter(period_start__gte=date_from)
    if date_to:
        contributions = contributions.filter(period_end__lte=date_to)

    contributions = contributions.select_related('chama').order_by('-period_start')

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    write_csv_header(writer, [
        'Period Start', 'Period End', 'Chama', 'Amount (KSh)',
        'Payment Method', 'Reference', 'Status', 'Paid Date'
    ])

    count = 0
    for c in contributions:
        writer.writerow([
            c.period_start.strftime('%Y-%m-%d') if c.period_start else '',
            c.period_end.strftime('%Y-%m-%d') if c.period_end else '',
            c.chama.name,
            format_kes(c.amount),
            c.get_payment_method_display(),
            c.payment_reference,
            c.get_status_display(),
            c.paid_at.strftime('%Y-%m-%d %H:%M') if c.paid_at else '',
        ])
        count += 1

    return buffer.getvalue(), count


def generate_loan_statement(report):
    from apps.chamas.models import ChamaMember, Loan

    filters = report.filters or {}
    chama_id = filters.get('chama_id')

    member = ChamaMember.objects.filter(
        user=report.user, is_active=True
    ).first()

    if not member:
        return '', 0

    loans = Loan.objects.filter(
        borrower=member,
        is_deleted=False,
    )

    if chama_id:
        loans = loans.filter(chama_id=chama_id)

    loans = loans.select_related('chama').order_by('-created_at')

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    write_csv_header(writer, [
        'Loan Date', 'Chama', 'Principal (KSh)', 'Interest Rate',
        'Duration (Months)', 'Total Repayable (KSh)',
        'Monthly Installment (KSh)', 'Outstanding (KSh)', 'Status'
    ])

    count = 0
    for loan in loans:
        writer.writerow([
            loan.created_at.strftime('%Y-%m-%d'),
            loan.chama.name,
            format_kes(loan.principal),
            f"{loan.interest_rate}%",
            loan.duration_months,
            format_kes(loan.total_repayable),
            format_kes(loan.monthly_installment),
            format_kes(loan.outstanding_balance),
            loan.get_status_display(),
        ])
        count += 1

    return buffer.getvalue(), count


def generate_member_list(report):
    from apps.chamas.models import Chama, ChamaMember

    filters = report.filters or {}
    chama_id = filters.get('chama_id')

    if not chama_id:
        return '', 0

    try:
        chama = Chama.objects.get(id=chama_id)
    except Chama.DoesNotExist:
        return '', 0

    members = ChamaMember.objects.filter(
        chama=chama,
        is_active=True,
    ).select_related('user').order_by('user__first_name')

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    write_csv_header(writer, [
        'Name', 'Email', 'Phone', 'Role', 'Joined',
        'Total Contributions (KSh)', 'Current Balance (KSh)',
        'Outstanding Loans (KSh)', 'Standing Score', 'Status'
    ])

    count = 0
    for m in members:
        writer.writerow([
            m.user.get_full_name(),
            m.user.email,
            m.user.phone_number or '',
            m.get_role_display(),
            m.joined_at.strftime('%Y-%m-%d') if m.joined_at else '',
            format_kes(m.total_contributions),
            format_kes(m.current_balance),
            format_kes(m.outstanding_loans),
            str(m.standing_score),
            'Active' if m.is_active else 'Inactive',
        ])
        count += 1

    return buffer.getvalue(), count


def generate_chama_financial(report):
    from apps.chamas.models import Chama, Contribution

    filters = report.filters or {}
    chama_id = filters.get('chama_id')

    if not chama_id:
        return '', 0

    try:
        chama = Chama.objects.get(id=chama_id)
    except Chama.DoesNotExist:
        return '', 0

    buffer = io.StringIO()
    writer = csv.writer(buffer)

    # Summary section
    writer.writerow(['CHAMA FINANCIAL SUMMARY'])
    writer.writerow(['Chama Name', chama.name])
    writer.writerow(['Type', chama.get_chama_type_display()])
    writer.writerow(['Total Savings', format_kes(chama.total_savings)])
    writer.writerow(['Available Balance', format_kes(chama.available_balance)])
    writer.writerow(['Outstanding Loans', format_kes(chama.outstanding_loans)])
    writer.writerow(['Active Members', str(chama.memberships.filter(is_active=True).count())])
    writer.writerow([])

    # Recent contributions
    writer.writerow(['RECENT CONTRIBUTIONS'])
    write_csv_header(writer, ['Date', 'Member', 'Amount (KSh)', 'Status'])

    count = 0
    contributions = Contribution.objects.filter(
        chama=chama, is_deleted=False
    ).select_related('member__user').order_by('-created_at')[:50]

    for c in contributions:
        writer.writerow([
            c.created_at.strftime('%Y-%m-%d'),
            c.member.user.get_full_name(),
            format_kes(c.amount),
            c.get_status_display(),
        ])
        count += 1

    return buffer.getvalue(), count


def generate_dividend_statement(report):
    from apps.investments.models import SACCOMemberHolding

    holdings = SACCOMemberHolding.objects.filter(
        user=report.user,
        is_deleted=False,
    ).select_related('sacco')

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(['DIVIDEND STATEMENT'])
    writer.writerow(['Generated', timezone.now().strftime('%Y-%m-%d %H:%M')])
    writer.writerow([])
    write_csv_header(writer, [
        'SACCO', 'Shares Held', 'Dividend Rate',
        'Estimated Annual Dividend (KSh)'
    ])

    count = 0
    for h in holdings:
        if h.sacco.dividend_rate > 0:
            estimated = h.total_shares * h.share_class.nominal_value * (h.sacco.dividend_rate / 100)
            writer.writerow([
                h.sacco.name,
                str(h.total_shares),
                f"{h.sacco.dividend_rate}%",
                format_kes(estimated),
            ])
            count += 1

    return buffer.getvalue(), count


# Import at bottom to avoid circular imports
