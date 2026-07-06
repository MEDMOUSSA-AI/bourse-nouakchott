from django.utils.translation import gettext as _

from portfolios.models import Holding, Portfolio

from .matching import match_stock_orders
from .models import Order


def submit_order(*, trader, stock, order_type, quantity, price_per_share, broker=None):
    """
    ينشئ أمر تداول جديدًا في دفتر الأوامر بعد التحقق من كفاية الرصيد النقدي
    (لأوامر الشراء) أو كفاية الحيازة الفعلية (لأوامر البيع)، ثم يستدعي فورًا
    محرك المطابقة (matching engine) على هذا السهم لمحاولة تنفيذه كليًا أو جزئيًا
    مقابل الأوامر المعاكسة الموجودة في دفتر الأوامر.

    تُستخدم هذه الدالة من ثلاث جهات مختلفة في المنصة:
    - المتداول نفسه عند تقديم أمر مباشرة من صفحة السهم.
    - السمسار عند تنفيذ أمر نيابة عن أحد عملائه.
    - مدير المحفظة عند تنفيذ أمر نيابة عن صاحب محفظة يديرها.

    تُعيد زوجًا (order, error_message) بحيث يكون أحدهما دومًا None:
    نجاح العملية يُعيد (order, None)، وفشلها يُعيد (None, "رسالة الخطأ").
    الأمر المُعاد بعد النجاح يعكس حالته النهائية بعد محاولة المطابقة
    (قد يبقى مفتوحًا، أو يُنفَّذ جزئيًا، أو يُنفَّذ بالكامل فورًا بحسب ما توفر من طرف مقابل).
    """
    portfolio, _created = Portfolio.objects.get_or_create(owner=trader)
    estimated_total = quantity * price_per_share

    if order_type == Order.OrderType.BUY:
        if estimated_total > portfolio.cash_balance:
            return None, (
                _(
                    "الرصيد النقدي في محفظة %(username)s غير كافٍ لتغطية قيمة هذا الأمر "
                    "(%(total)s مقابل رصيد متاح %(balance)s)."
                )
                % {
                    "username": trader.username,
                    "total": estimated_total,
                    "balance": portfolio.cash_balance,
                }
            )
    else:
        holding = Holding.objects.filter(portfolio=portfolio, stock=stock).first()
        available = holding.quantity if holding else 0
        if quantity > available:
            return None, (
                _(
                    "لا تملك محفظة %(username)s عددًا كافيًا من أسهم %(symbol)s لتنفيذ هذا الأمر "
                    "(المتاح حاليًا: %(available)s)."
                )
                % {
                    "username": trader.username,
                    "symbol": stock.symbol,
                    "available": available,
                }
            )

    order = Order.objects.create(
        trader=trader,
        broker=broker,
        stock=stock,
        order_type=order_type,
        quantity=quantity,
        price_per_share=price_per_share,
    )

    match_stock_orders(stock.id)
    order.refresh_from_db()

    return order, None


def order_result_message(order, on_behalf_of=None):
    """
    يبني رسالة نجاح تعكس النتيجة الفعلية لمحاولة المطابقة الفورية بعد تقديم الأمر،
    بدل رسالة عامة ثابتة، بما أن محرك المطابقة قد يُنفّذ الأمر كليًا أو جزئيًا فورًا.
    تُستخدم من لوحات المتداول والسمسار ومدير المحفظة على حد سواء.
    """
    verb = order.get_order_type_display()
    subject = _("نيابة عن %(name)s") % {"name": on_behalf_of} if on_behalf_of else ""

    if order.status == Order.OrderStatus.FILLED:
        return _("تم تنفيذ أمر %(verb)s %(subject)s بالكامل فورًا بسعر السوق المتاح (%(price)s للسهم).") % {
            "verb": verb,
            "subject": subject,
            "price": order.price_per_share,
        }
    if order.status == Order.OrderStatus.PARTIALLY_FILLED:
        return _(
            "تم تنفيذ %(filled)s من أصل %(total)s سهم في أمر %(verb)s %(subject)s فورًا، "
            "والباقي أُدرج في دفتر الأوامر بانتظار طرف مقابل."
        ) % {
            "filled": order.filled_quantity,
            "total": order.quantity,
            "verb": verb,
            "subject": subject,
        }
    if order.status == Order.OrderStatus.CANCELLED:
        return _("تعذّر تنفيذ أمر %(verb)s %(subject)s: لم يعد الرصيد أو الحيازة كافيَين وقت المطابقة، فأُلغي الأمر.") % {
            "verb": verb,
            "subject": subject,
        }
    return _("تم إدخال أمر %(verb)s %(subject)s في دفتر الأوامر بنجاح، بانتظار طرف مقابل مطابق.") % {
        "verb": verb,
        "subject": subject,
    }
