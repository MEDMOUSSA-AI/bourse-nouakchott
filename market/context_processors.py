from .models import Stock


def market_ticker(request):
    """
    يوفّر لائحة بأكثر الأسهم تداولًا لعرضها في شريط المؤشر المتحرك (Ticker Tape)
    الظاهر أعلى كل صفحة بعد تسجيل الدخول.
    """
    if not request.user.is_authenticated:
        return {}

    ticker_stocks = Stock.objects.filter(is_active=True).select_related("company").order_by("-volume_today")[:10]
    return {"ticker_stocks": ticker_stocks}
