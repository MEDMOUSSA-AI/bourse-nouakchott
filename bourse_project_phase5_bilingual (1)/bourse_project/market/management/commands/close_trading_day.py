from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from market.models import PriceHistory, Stock


class Command(BaseCommand):
    help = (
        "يُغلق يوم التداول الحالي لكل الأسهم النشطة: يحفظ لقطة اليوم في السجل السعري "
        "(PriceHistory)، ثم يجعل سعر إغلاق اليوم هو 'سعر الإغلاق السابق' ليوم الغد، "
        "ويصفّر أعلى/أدنى سعر وحجم التداول استعدادًا لجلسة تداول جديدة. "
        "يُفترض تشغيله مرة واحدة يوميًا بعد إغلاق السوق (مثلاً عبر Cron/Scheduled Job على Render)."
    )

    def handle(self, *args, **options):
        today = timezone.now().date()
        stocks = Stock.objects.filter(is_active=True)
        closed_count = 0

        with transaction.atomic():
            for stock in stocks:
                # لا معنى لإغلاق يوم لم يشهد أي حركة تداول فعلية على هذا السهم
                if stock.volume_today <= 0:
                    continue

                PriceHistory.objects.update_or_create(
                    stock=stock,
                    date=today,
                    defaults={
                        "open_price": stock.previous_close,
                        "close_price": stock.current_price,
                        "high_price": stock.day_high or stock.current_price,
                        "low_price": stock.day_low or stock.current_price,
                        "volume": stock.volume_today,
                    },
                )

                stock.previous_close = stock.current_price
                stock.day_high = stock.current_price
                stock.day_low = stock.current_price
                stock.volume_today = 0
                stock.save(update_fields=["previous_close", "day_high", "day_low", "volume_today", "updated_at"])
                closed_count += 1

        self.stdout.write(
            self.style.SUCCESS(f"تم إغلاق جلسة التداول ليوم {today} على {closed_count} سهمًا نشطًا.")
        )
