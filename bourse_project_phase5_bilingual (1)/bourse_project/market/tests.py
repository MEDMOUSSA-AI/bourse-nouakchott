from decimal import Decimal

from django.test import TestCase

from accounts.models import User
from companies.models import Company
from portfolios.models import Holding, Portfolio

from .matching import match_stock_orders
from .models import Order, Stock, Trade
from .services import submit_order


class MatchingEngineTests(TestCase):
    """
    اختبارات محرك مطابقة الأوامر والتسوية: تغطي التنفيذ الكامل، الجزئي،
    أولوية السعر/الزمن، وحالة عجز أحد الطرفين عن الوفاء وقت التسوية.
    """

    def _make_trader(self, username, cash):
        user = User.objects.create_user(username=username, password="Pass@12345", role=User.Role.TRADER)
        Portfolio.objects.create(owner=user, cash_balance=Decimal(cash))
        return user

    def _make_stock(self, symbol="TEST", price="100.00"):
        company_user = User.objects.create_user(
            username=f"co_{symbol.lower()}", password="Pass@12345", role=User.Role.COMPANY
        )
        company = Company.objects.create(
            user=company_user,
            legal_name=f"شركة {symbol}",
            registration_number=f"RC-{symbol}",
            sector="اختبار",
            listing_status=Company.ListingStatus.LISTED,
            total_shares_issued=1_000_000,
        )
        return Stock.objects.create(
            company=company,
            symbol=symbol,
            current_price=Decimal(price),
            previous_close=Decimal(price),
            day_high=Decimal(price),
            day_low=Decimal(price),
        )

    def _give_holding(self, trader, stock, quantity, avg_price="100.00"):
        portfolio, _ = Portfolio.objects.get_or_create(owner=trader)
        Holding.objects.create(
            portfolio=portfolio, stock=stock, quantity=quantity, average_buy_price=Decimal(avg_price)
        )

    def test_full_match_settles_cash_and_shares(self):
        stock = self._make_stock()
        seller = self._make_trader("seller1", cash=0)
        buyer = self._make_trader("buyer1", cash=100_000)
        self._give_holding(seller, stock, quantity=100)

        # البائع يضع أمر بيع أولاً (صانع السوق)
        sell_order, err = submit_order(
            trader=seller, stock=stock, order_type=Order.OrderType.SELL,
            quantity=50, price_per_share=Decimal("100.00"),
        )
        self.assertIsNone(err)

        # المشتري يضع أمر شراء بسعر يساوي أو يفوق سعر البيع => مطابقة فورية
        buy_order, err = submit_order(
            trader=buyer, stock=stock, order_type=Order.OrderType.BUY,
            quantity=50, price_per_share=Decimal("100.00"),
        )
        self.assertIsNone(err)

        buy_order.refresh_from_db()
        sell_order.refresh_from_db()
        self.assertEqual(buy_order.status, Order.OrderStatus.FILLED)
        self.assertEqual(sell_order.status, Order.OrderStatus.FILLED)
        self.assertEqual(Trade.objects.filter(stock=stock).count(), 1)

        buyer_portfolio = Portfolio.objects.get(owner=buyer)
        seller_portfolio = Portfolio.objects.get(owner=seller)
        self.assertEqual(buyer_portfolio.cash_balance, Decimal("95000.00"))
        self.assertEqual(seller_portfolio.cash_balance, Decimal("5000.00"))

        buyer_holding = Holding.objects.get(portfolio=buyer_portfolio, stock=stock)
        seller_holding = Holding.objects.get(portfolio=seller_portfolio, stock=stock)
        self.assertEqual(buyer_holding.quantity, 50)
        self.assertEqual(seller_holding.quantity, 50)

        stock.refresh_from_db()
        self.assertEqual(stock.current_price, Decimal("100.00"))
        self.assertEqual(stock.volume_today, 50)

    def test_partial_fill_leaves_remainder_open(self):
        stock = self._make_stock()
        seller = self._make_trader("seller2", cash=0)
        buyer = self._make_trader("buyer2", cash=100_000)
        self._give_holding(seller, stock, quantity=30)

        sell_order, _ = submit_order(
            trader=seller, stock=stock, order_type=Order.OrderType.SELL,
            quantity=30, price_per_share=Decimal("50.00"),
        )
        buy_order, _ = submit_order(
            trader=buyer, stock=stock, order_type=Order.OrderType.BUY,
            quantity=100, price_per_share=Decimal("50.00"),
        )

        buy_order.refresh_from_db()
        sell_order.refresh_from_db()
        self.assertEqual(sell_order.status, Order.OrderStatus.FILLED)
        self.assertEqual(buy_order.status, Order.OrderStatus.PARTIALLY_FILLED)
        self.assertEqual(buy_order.filled_quantity, 30)

    def test_maker_price_used_not_taker_price(self):
        stock = self._make_stock()
        seller = self._make_trader("seller3", cash=0)
        buyer = self._make_trader("buyer3", cash=100_000)
        self._give_holding(seller, stock, quantity=20)

        # البائع (صانع السوق) يضع أمرًا بسعر 90
        submit_order(
            trader=seller, stock=stock, order_type=Order.OrderType.SELL,
            quantity=20, price_per_share=Decimal("90.00"),
        )
        # المشتري مستعد لدفع حتى 110، لكن التنفيذ يجب أن يتم بسعر صانع السوق (90)
        submit_order(
            trader=buyer, stock=stock, order_type=Order.OrderType.BUY,
            quantity=20, price_per_share=Decimal("110.00"),
        )

        trade = Trade.objects.get(stock=stock)
        self.assertEqual(trade.price_per_share, Decimal("90.00"))

    def test_no_crossing_orders_stay_open(self):
        stock = self._make_stock()
        seller = self._make_trader("seller4", cash=0)
        buyer = self._make_trader("buyer4", cash=100_000)
        self._give_holding(seller, stock, quantity=20)

        submit_order(
            trader=seller, stock=stock, order_type=Order.OrderType.SELL,
            quantity=20, price_per_share=Decimal("120.00"),
        )
        buy_order, _ = submit_order(
            trader=buyer, stock=stock, order_type=Order.OrderType.BUY,
            quantity=20, price_per_share=Decimal("100.00"),
        )

        buy_order.refresh_from_db()
        self.assertEqual(buy_order.status, Order.OrderStatus.OPEN)
        self.assertEqual(Trade.objects.filter(stock=stock).count(), 0)

    def test_settlement_time_insufficient_funds_cancels_order(self):
        stock = self._make_stock()
        seller = self._make_trader("seller5", cash=0)
        self._give_holding(seller, stock, quantity=50)

        sell_order, _ = submit_order(
            trader=seller, stock=stock, order_type=Order.OrderType.SELL,
            quantity=50, price_per_share=Decimal("100.00"),
        )

        # مشتر برصيد كافٍ عند تقديم الأمر لكن يُسحب لاحقًا قبل أن تتم المطابقة يدويًا
        buyer = self._make_trader("buyer5", cash=5_000_000)
        buy_order = Order.objects.create(
            trader=buyer, stock=stock, order_type=Order.OrderType.BUY,
            quantity=50, price_per_share=Decimal("100.00"),
        )
        # نُفرغ رصيد المشتري يدويًا لمحاكاة تغيّر الرصيد بين التقديم والتسوية
        buyer_portfolio = Portfolio.objects.get(owner=buyer)
        buyer_portfolio.cash_balance = Decimal("0.00")
        buyer_portfolio.save(update_fields=["cash_balance"])

        match_stock_orders(stock.id)

        buy_order.refresh_from_db()
        sell_order.refresh_from_db()
        self.assertEqual(buy_order.status, Order.OrderStatus.CANCELLED)
        # أمر البيع يبقى مفتوحًا بانتظار مشترٍ آخر قادر فعليًا على الدفع
        self.assertEqual(sell_order.status, Order.OrderStatus.OPEN)
