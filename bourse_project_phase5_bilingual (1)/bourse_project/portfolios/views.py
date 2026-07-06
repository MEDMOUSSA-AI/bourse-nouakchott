from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _

from accounts.decorators import role_required
from accounts.models import User
from market.services import order_result_message, submit_order

from .forms import AdoptPortfolioForm, ManagerOrderForm, PortfolioManagerProfileForm
from .models import Holding, Portfolio, PortfolioManager


@role_required(User.Role.PORTFOLIO_MANAGER)
def dashboard(request):
    manager = getattr(request.user, "portfolio_manager_profile", None)
    portfolios = manager.managed_portfolios.select_related("owner").all() if manager else []
    return render(request, "portfolios/dashboard.html", {"manager": manager, "portfolios": portfolios})


@role_required(User.Role.PORTFOLIO_MANAGER)
def profile_edit(request):
    manager = getattr(request.user, "portfolio_manager_profile", None)

    if request.method == "POST":
        form = PortfolioManagerProfileForm(request.POST, instance=manager)
        if form.is_valid():
            new_manager = form.save(commit=False)
            new_manager.user = request.user
            new_manager.save()
            messages.success(request, _("تم حفظ بيانات ملفك كمدير محفظة بنجاح."))
            return redirect("portfolios:dashboard")
    else:
        form = PortfolioManagerProfileForm(instance=manager)

    return render(request, "portfolios/profile_form.html", {"form": form, "manager": manager})


@role_required(User.Role.PORTFOLIO_MANAGER)
def adopt_portfolio(request):
    manager = get_object_or_404(PortfolioManager, user=request.user)

    if request.method == "POST":
        form = AdoptPortfolioForm(request.POST)
        if form.is_valid():
            portfolio = form.cleaned_data["portfolio"]
            portfolio.manager = manager
            portfolio.save(update_fields=["manager"])
            messages.success(
                request,
                _("تم إسناد محفظة %(username)s إليك بنجاح.") % {"username": portfolio.owner.username},
            )
            return redirect("portfolios:dashboard")
    else:
        form = AdoptPortfolioForm()

    return render(request, "portfolios/adopt_form.html", {"form": form, "manager": manager})


@role_required(User.Role.PORTFOLIO_MANAGER)
def release_portfolio(request, portfolio_id):
    manager = get_object_or_404(PortfolioManager, user=request.user)
    portfolio = get_object_or_404(Portfolio, id=portfolio_id, manager=manager)

    if request.method == "POST":
        portfolio.manager = None
        portfolio.save(update_fields=["manager"])
        messages.success(request, _("تم إلغاء إدارتك لمحفظة %(username)s.") % {"username": portfolio.owner.username})

    return redirect("portfolios:dashboard")


@role_required(User.Role.PORTFOLIO_MANAGER)
def portfolio_detail(request, portfolio_id):
    manager = get_object_or_404(PortfolioManager, user=request.user)
    portfolio = get_object_or_404(
        Portfolio.objects.select_related("owner"), id=portfolio_id, manager=manager
    )

    holdings = Holding.objects.filter(portfolio=portfolio, quantity__gt=0).select_related("stock")
    recent_orders = portfolio.owner.orders.select_related("stock")[:15]
    form = ManagerOrderForm()

    return render(
        request,
        "portfolios/portfolio_detail.html",
        {
            "manager": manager,
            "portfolio": portfolio,
            "holdings": holdings,
            "recent_orders": recent_orders,
            "form": form,
        },
    )


@role_required(User.Role.PORTFOLIO_MANAGER)
def place_order_for_portfolio(request, portfolio_id):
    manager = get_object_or_404(PortfolioManager, user=request.user)
    portfolio = get_object_or_404(Portfolio, id=portfolio_id, manager=manager)

    if request.method != "POST":
        return redirect("portfolios:portfolio_detail", portfolio_id=portfolio.id)

    form = ManagerOrderForm(request.POST)
    if form.is_valid():
        order, error = submit_order(
            trader=portfolio.owner,
            stock=form.cleaned_data["stock"],
            order_type=form.cleaned_data["order_type"],
            quantity=form.cleaned_data["quantity"],
            price_per_share=form.cleaned_data["price_per_share"],
        )
        if error:
            messages.error(request, error)
        else:
            messages.success(request, order_result_message(order, on_behalf_of=portfolio.owner.username))
    else:
        messages.error(request, _("تعذّر تقديم الأمر، يرجى مراجعة البيانات المدخلة."))

    return redirect("portfolios:portfolio_detail", portfolio_id=portfolio.id)
