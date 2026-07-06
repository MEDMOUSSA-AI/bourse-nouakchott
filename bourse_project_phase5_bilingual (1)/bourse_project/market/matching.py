"""
محرك مطابقة الأوامر والتسوية (Order Matching & Settlement Engine).

المبدأ: أولوية السعر ثم الزمن (Price-Time Priority) — نفس مبدأ أي بورصة حقيقية:
- أفضل أمر شراء (أعلى سعر) يُطابَق مع أفضل أمر بيع (أدنى سعر).
- عند تساوي السعر بين عدة أوامر، يُقدَّم الأمر الأقدم زمنيًا (created_at).
- التنفيذ يتم بسعر الأمر "الأقدم" بين الطرفين المتطابقين (صاحب الأولوية الزمنية)،
  وهو نفس مبدأ "صانع السوق" (Maker Price) المعتمد في معظم أسواق الأسهم.

التسوية (Settlement) تتم فورًا وذريًا مع كل صفقة:
- خصم القيمة النقدية من محفظة المشتري وإضافتها لمحفظة البائع.
- خصم عدد الأسهم من حيازة البائع وإضافتها لحيازة المشتري (بتحديث متوسط سعر الشراء المرجّح).
- تحديث السعر الحالي للسهم، أعلى/أدنى سعر اليوم، وحجم التداول.

ملاحظة مهمة: التحقق من كفاية الرصيد/الحيازة يتم مرتين:
1. عند تقديم الأمر (submit_order) — كتحقق أولي سريع لتجربة مستخدم أفضل.
2. عند لحظة التسوية الفعلية هنا — كتحقق نهائي وحاسم، لأن رصيد أو حيازة المتداول قد
   يتغيّر بين لحظة تقديم الأمر ولحظة تنفيذه الفعلي (مثلاً بسبب تنفيذ أمر آخر أولاً).
   إن تبيّن عند التسوية أن أحد الطرفين لم يعد قادرًا على الوفاء، يُلغى أمره تلقائيًا
   بدل تعليق دفتر الأوامر بالكامل.
"""

from decimal import Decimal

from django.db import transaction
from django.db.models import F

from portfolios.models import Holding, Portfolio

from .models import Order, Stock, Trade

OPEN_STATUSES = [Order.OrderStatus.OPEN, Order.OrderStatus.PARTIALLY_FILLED]


def _mark_status(order, matched_qty):
    order.filled_quantity += matched_qty
    if order.filled_quantity >= order.quantity:
        order.status = Order.OrderStatus.FILLED
    else:
        order.status = Order.OrderStatus.PARTIALLY_FILLED
    order.save(update_fields=["filled_quantity", "status", "updated_at"])


def match_stock_orders(stock_id):
    """
    يحاول مطابقة أكبر عدد ممكن من أوامر الشراء/البيع المفتوحة على سهم معيّن،
    وينشئ صفقة (Trade) لكل مطابقة ناجحة مع تسوية فورية للنقد والأسهم.

    تُستدعى هذه الدالة تلقائيًا بعد كل تقديم أمر جديد (من متداول، أو نيابة عنه
    من سمسار أو مدير محفظة)، وتُعيد قائمة الصفقات المُنفَّذة فعليًا.
    """
    trades_created = []

    while True:
        with transaction.atomic():
            stock = Stock.objects.select_for_update().get(id=stock_id)

            best_buy = (
                Order.objects.select_for_update()
                .filter(stock=stock, order_type=Order.OrderType.BUY, status__in=OPEN_STATUSES)
                .order_by("-price_per_share", "created_at")
                .first()
            )
            best_sell = (
                Order.objects.select_for_update()
                .filter(stock=stock, order_type=Order.OrderType.SELL, status__in=OPEN_STATUSES)
                .order_by("price_per_share", "created_at")
                .first()
            )

            if not best_buy or not best_sell:
                break
            if best_buy.price_per_share < best_sell.price_per_share:
                break  # لا يوجد تقاطع بين أفضل سعري شراء وبيع، لا مزيد من المطابقات الممكنة

            # صاحب الأولوية الزمنية (الأمر الأسبق) هو من يحدد سعر التنفيذ
            maker, taker = (
                (best_buy, best_sell) if best_buy.created_at <= best_sell.created_at else (best_sell, best_buy)
            )
            trade_price = maker.price_per_share

            buy_remaining = best_buy.quantity - best_buy.filled_quantity
            sell_remaining = best_sell.quantity - best_sell.filled_quantity
            match_qty = min(buy_remaining, sell_remaining)

            buyer_portfolio = Portfolio.objects.select_for_update().get(owner=best_buy.trader)
            seller_portfolio, _ = Portfolio.objects.select_for_update().get_or_create(owner=best_sell.trader)
            seller_holding = (
                Holding.objects.select_for_update().filter(portfolio=seller_portfolio, stock=stock).first()
            )

            affordable_qty = (
                int(buyer_portfolio.cash_balance // trade_price) if trade_price > 0 else 0
            )
            available_qty = seller_holding.quantity if seller_holding else 0
            match_qty = min(match_qty, affordable_qty, available_qty)

            if match_qty <= 0:
                # رصيد المشتري أو حيازة البائع لم تعد كافية وقت التنفيذ الفعلي (تغيّرت
                # منذ تقديم الأمر) — نُلغي الطرف العاجز فقط لتحرير دفتر الأوامر ومتابعة المطابقة.
                if affordable_qty <= 0:
                    best_buy.status = Order.OrderStatus.CANCELLED
                    best_buy.save(update_fields=["status", "updated_at"])
                if available_qty <= 0:
                    best_sell.status = Order.OrderStatus.CANCELLED
                    best_sell.save(update_fields=["status", "updated_at"])
                continue

            trade_total = trade_price * match_qty

            # --- التسوية النقدية ---
            Portfolio.objects.filter(pk=buyer_portfolio.pk).update(
                cash_balance=F("cash_balance") - trade_total
            )
            Portfolio.objects.filter(pk=seller_portfolio.pk).update(
                cash_balance=F("cash_balance") + trade_total
            )

            # --- تسوية حيازة المشتري (متوسط سعر شراء مرجّح) ---
            buyer_holding, _ = Holding.objects.select_for_update().get_or_create(
                portfolio=buyer_portfolio, stock=stock
            )
            prev_qty, prev_avg = buyer_holding.quantity, buyer_holding.average_buy_price
            new_qty = prev_qty + match_qty
            new_avg = (
                ((prev_avg * prev_qty) + (trade_price * match_qty)) / new_qty
                if new_qty > 0
                else Decimal("0")
            )
            buyer_holding.quantity = new_qty
            buyer_holding.average_buy_price = new_avg
            buyer_holding.save(update_fields=["quantity", "average_buy_price", "updated_at"])

            # --- تسوية حيازة البائع ---
            Holding.objects.filter(pk=seller_holding.pk).update(quantity=F("quantity") - match_qty)

            # --- تحديث الأوامر ---
            _mark_status(best_buy, match_qty)
            _mark_status(best_sell, match_qty)

            trade = Trade.objects.create(
                stock=stock,
                buy_order=best_buy,
                sell_order=best_sell,
                quantity=match_qty,
                price_per_share=trade_price,
            )
            trades_created.append(trade.id)

            # --- تحديث بيانات السهم اللحظية ---
            stock.current_price = trade_price
            stock.day_high = max(stock.day_high, trade_price) if stock.day_high else trade_price
            stock.day_low = min(stock.day_low, trade_price) if stock.day_low else trade_price
            stock.save(update_fields=["current_price", "day_high", "day_low", "updated_at"])
            Stock.objects.filter(pk=stock.pk).update(volume_today=F("volume_today") + match_qty)

    return Trade.objects.filter(id__in=trades_created)
