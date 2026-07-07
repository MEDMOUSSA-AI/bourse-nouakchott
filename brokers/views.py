from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _

from accounts.decorators import role_required
from accounts.models import User
from market.services import order_result_message, submit_order
from portfolios.models import Holding, Portfolio

from .forms import AddClientForm, BrokerOrderForm, BrokerProfileForm
from .models import Broker, BrokerClient


@role_required(User.Role.BROKER)
def dashboard(request):
    broker = getattr(request.user, "broker_profile", None)
    clients = broker.clients.select_related("client").all() if broker else []
    return render(request, "brokers/dashboard.html", {"broker": broker, "clients": clients})


@role_required(User.Role.BROKER)
def profile_edit(request):
    broker = getattr(request.user, "broker_profile", None)

    if request.method == "POST":
        form = BrokerProfileForm(request.POST, instance=broker)
        if form.is_valid():
            new_broker = form.save(commit=False)
            new_broker.user = request.user
            new_broker.save()
            messages.success(request, _("تم حفظ بيانات ملفك كسمسار بنجاح."))
            return redirect("brokers:dashboard")
    else:
        form = BrokerProfileForm(instance=broker)

    return render(request, "brokers/profile_form.html", {"form": form, "broker": broker})


@role_required(User.Role.BROKER)
def add_client(request):
    broker = get_object_or_404(Broker, user=request.user)

    if request.method == "POST":
        form = AddClientForm(request.POST, broker=broker)
        if form.is_valid():
            BrokerClient.objects.create(broker=broker, client=form.cleaned_data["client_user"])
            messages.success(
                request,
                _("تم ربط %(username)s كعميل لك بنجاح.") % {
                    "username": form.cleaned_data["client_user"].username
                },
            )
            return redirect("brokers:dashboard")
    else:
        form = AddClientForm(broker=broker)

    return render(request, "brokers/add_client.html", {"form": form, "broker": broker})


@role_required(User.Role.BROKER)
def toggle_client(request, client_link_id):
    broker = get_object_or_404(Broker, user=request.user)
    link = get_object_or_404(BrokerClient, id=client_link_id, broker=broker)

    if request.method == "POST":
        link.is_active = not link.is_active
        link.save(update_fields=["is_active"])
        messages.success(
            request,
            _("تم تفعيل العميل بنجاح.") if link.is_active else _("تم إيقاف العميل بنجاح."),
        )

    return redirect("brokers:dashboard")


@role_required(User.Role.BROKER)
def client_detail(request, client_link_id):
    broker = get_object_or_404(Broker, user=request.user)
    link = get_object_or_404(
        BrokerClient.objects.select_related("client"), id=client_link_id, broker=broker
    )
    client = link.client

    portfolio, _ = Portfolio.objects.get_or_create(owner=client)
    holdings = Holding.objects.filter(portfolio=portfolio, quantity__gt=0).select_related("stock")
    recent_orders = client.orders.select_related("stock").filter(broker=broker)[:15]

    form = BrokerOrderForm() if link.is_active else None

    return render(
        request,
        "brokers/client_detail.html",
        {
            "broker": broker,
            "link": link,
            "client": client,
            "portfolio": portfolio,
            "holdings": holdings,
            "recent_orders": recent_orders,
            "form": form,
        },
    )


@role_required(User.Role.BROKER)
def place_order_for_client(request, client_link_id):
    broker = get_object_or_404(Broker, user=request.user)
    link = get_object_or_404(BrokerClient, id=client_link_id, broker=broker)

    if request.method != "POST":
        return redirect("brokers:client_detail", client_link_id=link.id)

    if not link.is_active:
        messages.error(request, _("هذا العميل موقوف حاليًا، لا يمكن تنفيذ أوامر نيابة عنه."))
        return redirect("brokers:client_detail", client_link_id=link.id)

    form = BrokerOrderForm(request.POST)
    if form.is_valid():
        order, error = submit_order(
            trader=link.client,
            stock=form.cleaned_data["stock"],
            order_type=form.cleaned_data["order_type"],
            quantity=form.cleaned_data["quantity"],
            price_per_share=form.cleaned_data["price_per_share"],
            broker=broker,
        )
        if error:
            messages.error(request, error)
        else:
            messages.success(request, order_result_message(order, on_behalf_of=link.client.username))
    else:
        messages.error(request, _("تعذّر تقديم الأمر، يرجى مراجعة البيانات المدخلة."))

    return redirect("brokers:client_detail", client_link_id=link.id)
