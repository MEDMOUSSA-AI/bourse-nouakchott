from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _

from .decorators import role_required
from .forms import RegisterForm, VerificationDocumentForm
from .models import User, VerificationDocument


class BourseLoginView(LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True


class BourseLogoutView(LogoutView):
    next_page = "accounts:login"


def register_view(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard_redirect")

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("accounts:dashboard_redirect")
    else:
        form = RegisterForm()

    return render(request, "accounts/register.html", {"form": form})


@login_required
def dashboard_redirect(request):
    """
    يوجّه كل مستخدم إلى لوحة التحكم الخاصة بدوره مباشرة بعد تسجيل الدخول.
    """
    role_url_map = {
        User.Role.ADMIN: "accounts:admin_dashboard",
        User.Role.COMPANY: "companies:dashboard",
        User.Role.BROKER: "brokers:dashboard",
        User.Role.PORTFOLIO_MANAGER: "portfolios:dashboard",
        User.Role.TRADER: "market:dashboard",
    }
    target = role_url_map.get(request.user.role, "market:dashboard")
    return redirect(target)


@login_required
def document_list(request):
    documents = request.user.documents.all()
    if request.method == "POST":
        form = VerificationDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.user = request.user
            doc.save()
            messages.success(request, _("تم رفع المستند بنجاح، بانتظار مراجعة الإدارة."))
            return redirect("accounts:documents")
    else:
        form = VerificationDocumentForm()

    return render(request, "accounts/documents.html", {"documents": documents, "form": form})


# ---------------------------------------------------------------------------
# لوحة تحكم إدارة المنصة — واجهة مخصّصة بنفس هوية الموقع البصرية
# (بديل عن استخدام /admin/ الخاصة بـ Django مباشرة أمام المستخدم النهائي)
# ---------------------------------------------------------------------------


@role_required(User.Role.ADMIN)
def admin_dashboard(request):
    from companies.models import Company, ListingRequest
    from market.models import Stock

    stats = {
        "total_users": User.objects.exclude(role=User.Role.ADMIN).count(),
        "total_companies": Company.objects.count(),
        "listed_companies": Company.objects.filter(
            listing_status=Company.ListingStatus.LISTED
        ).count(),
        "total_stocks": Stock.objects.count(),
        "pending_documents": VerificationDocument.objects.filter(
            status=VerificationDocument.DocStatus.PENDING
        ).count(),
        "pending_listing_requests": ListingRequest.objects.filter(
            status__in=[
                ListingRequest.RequestStatus.SUBMITTED,
                ListingRequest.RequestStatus.UNDER_REVIEW,
            ]
        ).count(),
    }
    return render(request, "accounts/admin_dashboard.html", {"stats": stats})


@role_required(User.Role.ADMIN)
def admin_users(request):
    users = User.objects.exclude(role=User.Role.ADMIN).order_by("-created_at")
    return render(request, "accounts/admin_users.html", {"users": users})


@role_required(User.Role.ADMIN)
def admin_documents(request):
    documents = VerificationDocument.objects.select_related("user").order_by(
        "status", "-uploaded_at"
    )
    return render(request, "accounts/admin_documents.html", {"documents": documents})


@role_required(User.Role.ADMIN)
def admin_document_review(request, document_id):
    document = get_object_or_404(VerificationDocument, id=document_id)
    if request.method == "POST":
        action = request.POST.get("action")
        note = request.POST.get("reviewer_note", "").strip()
        if action == "approve":
            document.status = VerificationDocument.DocStatus.APPROVED
            document.user.is_verified = True
            document.user.save(update_fields=["is_verified"])
        elif action == "reject":
            document.status = VerificationDocument.DocStatus.REJECTED
        document.reviewer_note = note
        document.reviewed_at = timezone.now()
        document.save()
        messages.success(request, _("تم تحديث حالة المستند بنجاح."))
    return redirect("accounts:admin_documents")


@role_required(User.Role.ADMIN)
def admin_listing_requests(request):
    from companies.models import ListingRequest

    listing_requests = ListingRequest.objects.select_related("company").order_by(
        "-submitted_at"
    )
    return render(
        request, "accounts/admin_listing_requests.html", {"listing_requests": listing_requests}
    )


@role_required(User.Role.ADMIN)
def admin_listing_request_review(request, request_id):
    from companies.models import Company, ListingRequest
    from market.models import Stock

    listing_request = get_object_or_404(ListingRequest, id=request_id)

    if request.method == "POST":
        action = request.POST.get("action")
        note = request.POST.get("admin_note", "").strip()
        listing_request.admin_note = note

        if action == "approve" and listing_request.status != ListingRequest.RequestStatus.APPROVED:
            company = listing_request.company
            stock, _created = Stock.objects.get_or_create(
                company=company,
                defaults={
                    "symbol": _generate_stock_symbol(company, listing_request.requested_symbol),
                    "current_price": listing_request.requested_price_per_share,
                    "previous_close": listing_request.requested_price_per_share,
                    "day_high": listing_request.requested_price_per_share,
                    "day_low": listing_request.requested_price_per_share,
                },
            )
            company.listing_status = Company.ListingStatus.LISTED
            company.total_shares_issued = listing_request.requested_shares
            company.nominal_share_value = listing_request.requested_price_per_share
            company.listed_at = timezone.now()
            company.save()

            listing_request.status = ListingRequest.RequestStatus.APPROVED
            listing_request.decided_at = timezone.now()
            listing_request.save()
            messages.success(request, _("تمت الموافقة على طلب الإدراج وإنشاء السهم بنجاح."))

        elif action == "reject":
            listing_request.status = ListingRequest.RequestStatus.REJECTED
            listing_request.decided_at = timezone.now()
            listing_request.save()
            messages.success(request, _("تم رفض طلب الإدراج."))

    return redirect("accounts:admin_listing_requests")


def _generate_stock_symbol(company, requested_symbol=""):
    """
    نفس منطق توليد الرمز المستخدم سابقًا في companies/admin.py، مكرَّر هنا
    لتوليد رمز السهم تلقائيًا عند الموافقة على طلب إدراج من لوحة التحكم المخصصة.
    """
    from market.models import Stock

    if requested_symbol:
        symbol = requested_symbol
        if not Stock.objects.filter(symbol=symbol).exclude(company=company).exists():
            return symbol

    source = company.trade_name or company.legal_name
    base = "".join(ch for ch in source if ch.isascii() and ch.isalnum())[:4].upper()
    if not base:
        base = "CO"
        suffix = Stock.objects.filter(symbol__startswith=base).count() + 1
        return f"{base}{suffix:03d}"

    symbol = base
    suffix = 1
    while Stock.objects.filter(symbol=symbol).exclude(company=company).exists():
        suffix += 1
        symbol = f"{base}{suffix}"
    return symbol
