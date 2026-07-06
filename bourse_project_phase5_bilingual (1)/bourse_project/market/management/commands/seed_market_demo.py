import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import User
from companies.models import Company
from market.models import Order, PriceHistory, Stock, Trade
from portfolios.models import Portfolio


DEMO_PASSWORD = "Demo@12345"

DEMO_COMPANIES = [
    {
        "username": "co_sahara_bank",
        "legal_name": "بنك الصحراء للاستثمار",
        "registration_number": "RC-SB-001",
        "sector": "بنوك ومال",
        "symbol": "SHRB",
        "start_price": Decimal("1250.00"),
    },
    {
        "username": "co_atlantic_fish",
        "legal_name": "شركة الأطلسي للصيد البحري",
        "registration_number": "RC-AF-002",
        "sector": "صيد وتصنيع بحري",
        "symbol": "ATLF",
        "start_price": Decimal("430.00"),
    },
    {
        "username": "co_nkc_telecom",
        "legal_name": "شركة نواكشوط للاتصالات",
        "registration_number": "RC-NT-003",
        "sector": "اتصالات",
        "symbol": "NKCT",
        "start_price": Decimal("875.50"),
    },
    {
        "username": "co_desert_mining",
        "legal_name": "شركة الصحراء للتعدين",
        "registration_number": "RC-DM-004",
        "sector": "تعدين",
        "symbol": "DSRM",
        "start_price": Decimal("2100.00"),
    },
]

DEMO_TRADERS = ["trader_ahmed", "trader_fatima", "trader_yacoub"]


class Command(BaseCommand):
    help = "يزرع بيانات تجريبية (شركات مُدرجة، أسهم، سجل أسعار، أوامر وصفقات) لاختبار محرك السوق."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=45,
            help="عدد أيام سجل الأسعار التاريخي الذي سيُولَّد لكل سهم (افتراضيًا 45).",
        )

    def handle(self, *args, **options):
        days = options["days"]
        self.stdout.write("جاري إنشاء الشركات، الأسهم، وسجل الأسعار...")

        stocks = []
        for spec in DEMO_COMPANIES:
            user, created = User.objects.get_or_create(
                username=spec["username"],
                defaults={
                    "email": f"{spec['username']}@example.com",
                    "role": User.Role.COMPANY,
                    "is_verified": True,
                },
            )
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save()

            company, _ = Company.objects.get_or_create(
                user=user,
                defaults={
                    "legal_name": spec["legal_name"],
                    "registration_number": spec["registration_number"],
                    "sector": spec["sector"],
                    "listing_status": Company.ListingStatus.LISTED,
                    "total_shares_issued": 1_000_000,
                    "nominal_share_value": spec["start_price"],
                    "listed_at": timezone.now(),
                },
            )
            if company.listing_status != Company.ListingStatus.LISTED:
                company.listing_status = Company.ListingStatus.LISTED
                company.listed_at = timezone.now()
                company.save(update_fields=["listing_status", "listed_at"])

            stock, _ = Stock.objects.get_or_create(
                company=company,
                defaults={
                    "symbol": spec["symbol"],
                    "current_price": spec["start_price"],
                    "previous_close": spec["start_price"],
                    "day_high": spec["start_price"],
                    "day_low": spec["start_price"],
                },
            )
            stocks.append(stock)
            self._generate_price_history(stock, spec["start_price"], days)

        self.stdout.write("جاري إنشاء المتداولين والمحافظ...")
        traders = []
        for username in DEMO_TRADERS:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": f"{username}@example.com",
                    "role": User.Role.TRADER,
                    "is_verified": True,
                },
            )
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save()

            Portfolio.objects.get_or_create(
                owner=user,
                defaults={"cash_balance": Decimal(random.randint(50_000, 300_000))},
            )
            traders.append(user)

        self.stdout.write("جاري إنشاء أوامر مفتوحة في دفتر الأوامر...")
        for stock in stocks:
            self._seed_orders_and_trades(stock, traders)

        self.stdout.write(self.style.SUCCESS(
            f"تم بنجاح: {len(stocks)} سهم، {len(traders)} متداول تجريبي. "
            f"كلمة مرور جميع الحسابات التجريبية: {DEMO_PASSWORD}"
        ))

    def _generate_price_history(self, stock, start_price, days):
        if PriceHistory.objects.filter(stock=stock).exists():
            return

        price = float(start_price)
        today = timezone.now().date()
        history_objs = []

        for i in range(days, 0, -1):
            date = today - timedelta(days=i)
            open_price = price
            drift = random.uniform(-0.03, 0.03)
            close_price = max(1.0, open_price * (1 + drift))
            high_price = max(open_price, close_price) * random.uniform(1.0, 1.02)
            low_price = min(open_price, close_price) * random.uniform(0.98, 1.0)
            volume = random.randint(500, 15_000)

            history_objs.append(
                PriceHistory(
                    stock=stock,
                    date=date,
                    open_price=round(Decimal(open_price), 2),
                    close_price=round(Decimal(close_price), 2),
                    high_price=round(Decimal(high_price), 2),
                    low_price=round(Decimal(low_price), 2),
                    volume=volume,
                )
            )
            price = close_price

        PriceHistory.objects.bulk_create(history_objs)

        last = history_objs[-1]
        stock.previous_close = history_objs[-2].close_price if len(history_objs) > 1 else last.open_price
        stock.current_price = last.close_price
        stock.day_high = last.high_price
        stock.day_low = last.low_price
        stock.volume_today = last.volume
        stock.save()

    def _seed_orders_and_trades(self, stock, traders):
        if Order.objects.filter(stock=stock).exists():
            return

        price = float(stock.current_price)

        # أوامر شراء وبيع مفتوحة حول السعر الحالي، لتشكيل دفتر أوامر واقعي
        for i in range(1, 5):
            buyer = random.choice(traders)
            seller = random.choice(traders)
            Order.objects.create(
                trader=buyer,
                stock=stock,
                order_type=Order.OrderType.BUY,
                quantity=random.randint(10, 200),
                price_per_share=round(Decimal(price * (1 - 0.002 * i)), 2),
                status=Order.OrderStatus.OPEN,
            )
            Order.objects.create(
                trader=seller,
                stock=stock,
                order_type=Order.OrderType.SELL,
                quantity=random.randint(10, 200),
                price_per_share=round(Decimal(price * (1 + 0.002 * i)), 2),
                status=Order.OrderStatus.OPEN,
            )

        # صفقتان مُنفَّذتان تاريخيًا لعرضهما في "آخر الصفقات"
        for _ in range(2):
            buyer = random.choice(traders)
            seller = random.choice(traders)
            qty = random.randint(20, 150)
            trade_price = round(Decimal(price * random.uniform(0.995, 1.005)), 2)

            buy_order = Order.objects.create(
                trader=buyer,
                stock=stock,
                order_type=Order.OrderType.BUY,
                quantity=qty,
                filled_quantity=qty,
                price_per_share=trade_price,
                status=Order.OrderStatus.FILLED,
            )
            sell_order = Order.objects.create(
                trader=seller,
                stock=stock,
                order_type=Order.OrderType.SELL,
                quantity=qty,
                filled_quantity=qty,
                price_per_share=trade_price,
                status=Order.OrderStatus.FILLED,
            )
            Trade.objects.create(
                stock=stock,
                buy_order=buy_order,
                sell_order=sell_order,
                quantity=qty,
                price_per_share=trade_price,
            )
