from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import F, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _

from accounts.models import User
from accounts.decorators import role_required
from portfolios.models import Holding

from .forms import OrderForm
from .models import Order, PriceHistory, Stock, Trade
from .services import order_result_message, submit_order

# عدد مستويات الأسعار المعروضة في كل جهة من دفتر الأوامر (شراء/بيع)
ORDER_BOOK_DEPTH = 8


@login_required
def dashboard(request):
    stocks = Stock.objects.filter(is_active=True).select_related("company")
    portfolio = getattr(request.user, "portfolio", None)

    # أكثر الأسهم ارتفاعًا وانخفاضًا اليوم، لعرضها كبطاقات سريعة أعلى لوحة السوق
    ranked = sorted(stocks, key=lambda s: s.change_percent, reverse=True)
    top_gainers = [s for s in ranked if s.change_percent > 0][:3]
    top_losers = [s for s in ranked[::-1] if s.change_percent < 0][:3]

    return render(
        request,
        "market/dashboard.html",
        {
            "stocks": stocks,
            "portfolio": portfolio,
            "top_gainers": top_gainers,
            "top_losers": top_losers,
        },
    )


def _build_chart_points(history_qs, width=640, height=180, padding=10):
    """
    يبني نقاط SVG polyline لمخطط سعر مبسّط من سجل الأسعار التاريخي،
    بدون أي مكتبة جافاسكريبت خارجية.
    """
    points = list(history_qs.order_by("date").values_list("date", "close_price"))
    if len(points) < 2:
        return None

    prices = [float(p[1]) for p in points]
    min_price, max_price = min(prices), max(prices)
    price_range = (max_price - min_price) or 1.0

    usable_w = width - 2 * padding
    usable_h = height - 2 * padding
    step = usable_w / (len(points) - 1)

    coords = []
    for i, price in enumerate(prices):
        x = padding + i * step
        y = padding + usable_h - ((price - min_price) / price_range) * usable_h
        coords.append((round(x, 1), round(y, 1)))

    polyline = " ".join(f"{x},{y}" for x, y in coords)
    # منطقة تعبئة أسفل الخط لإعطاء إحساس "منطقة الرسم البياني المالي"
    area = f"{padding},{height - padding} " + polyline + f" {width - padding},{height - padding}"

    return {
        "width": width,
        "height": height,
        "polyline": mark_safe(polyline),
        "area": mark_safe(area),
        "is_up": prices[-1] >= prices[0],
        "min_price": round(min_price, 2),
        "max_price": round(max_price, 2),
    }


def _order_book(stock):
    """
    يجمّع أوامر الشراء والبيع المفتوحة حسب مستوى السعر، بأسلوب دفتر أوامر
    حقيقي (Depth of Market): أفضل سعر شراء في الأعلى، وأفضل سعر بيع في الأعلى أيضًا.
    """
    open_statuses = [Order.OrderStatus.OPEN, Order.OrderStatus.PARTIALLY_FILLED]

    remaining = F("quantity") - F("filled_quantity")

    bids = (
        Order.objects.filter(stock=stock, order_type=Order.OrderType.BUY, status__in=open_statuses)
        .values("price_per_share")
        .annotate(total_quantity=Sum(remaining))
        .filter(total_quantity__gt=0)
        .order_by("-price_per_share")[:ORDER_BOOK_DEPTH]
    )
    asks = (
        Order.objects.filter(stock=stock, order_type=Order.OrderType.SELL, status__in=open_statuses)
        .values("price_per_share")
        .annotate(total_quantity=Sum(remaining))
        .filter(total_quantity__gt=0)
        .order_by("price_per_share")[:ORDER_BOOK_DEPTH]
    )
    return list(bids), list(asks)


@login_required
def stock_detail(request, symbol):
    stock = get_object_or_404(Stock.objects.select_related("company"), symbol=symbol.upper(), is_active=True)

    recent_dates = PriceHistory.objects.filter(stock=stock).order_by("-date").values_list("date", flat=True)[:90]
    history = PriceHistory.objects.filter(stock=stock, date__in=list(recent_dates))
    chart = _build_chart_points(history)

    bids, asks = _order_book(stock)
    recent_trades = Trade.objects.filter(stock=stock).select_related("buy_order", "sell_order")[:15]

    holding = None
    portfolio = getattr(request.user, "portfolio", None)
    if portfolio:
        holding = Holding.objects.filter(portfolio=portfolio, stock=stock).first()

    my_open_orders = Order.objects.filter(
        trader=request.user,
        stock=stock,
        status__in=[Order.OrderStatus.OPEN, Order.OrderStatus.PARTIALLY_FILLED],
    ).order_by("-created_at")

    can_trade = request.user.role == User.Role.TRADER
    form = OrderForm() if can_trade else None

    return render(
        request,
        "market/stock_detail.html",
        {
            "stock": stock,
            "chart": chart,
            "bids": bids,
            "asks": asks,
            "recent_trades": recent_trades,
            "holding": holding,
            "my_open_orders": my_open_orders,
            "form": form,
            "can_trade": can_trade,
        },
    )


@role_required(User.Role.TRADER)
def place_order(request, symbol):
    stock = get_object_or_404(Stock, symbol=symbol.upper(), is_active=True)

    if request.method != "POST":
        return redirect("market:stock_detail", symbol=stock.symbol)

    form = OrderForm(request.POST)
    if form.is_valid():
        order, error = submit_order(
            trader=request.user,
            stock=stock,
            order_type=form.cleaned_data["order_type"],
            quantity=form.cleaned_data["quantity"],
            price_per_share=form.cleaned_data["price_per_share"],
        )
        if error:
            messages.error(request, error)
        else:
            messages.success(request, order_result_message(order))
    else:
        messages.error(request, _("تعذّر تقديم الأمر، يرجى مراجعة البيانات المدخلة."))

    return redirect("market:stock_detail", symbol=stock.symbol)


@login_required
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, trader=request.user)

    if request.method == "POST" and order.status in (
        Order.OrderStatus.OPEN,
        Order.OrderStatus.PARTIALLY_FILLED,
    ):
        order.status = Order.OrderStatus.CANCELLED
        order.save(update_fields=["status", "updated_at"])
        messages.success(request, _("تم إلغاء الأمر بنجاح."))
    else:
        messages.error(request, _("لا يمكن إلغاء هذا الأمر."))

    return redirect("market:my_orders")


@login_required
def my_orders(request):
    orders = (
        Order.objects.filter(trader=request.user)
        .select_related("stock", "stock__company")
        .order_by("-created_at")
    )
    return render(request, "market/my_orders.html", {"orders": orders})
