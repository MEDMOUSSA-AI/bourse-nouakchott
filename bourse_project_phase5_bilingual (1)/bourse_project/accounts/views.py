from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _

from .forms import RegisterForm, VerificationDocumentForm
from .models import User


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
def admin_dashboard(request):
    return render(request, "accounts/admin_dashboard.html")


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
