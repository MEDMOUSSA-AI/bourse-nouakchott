from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _

from accounts.decorators import role_required
from accounts.models import User

from .forms import CompanyProfileForm, ListingRequestForm
from .models import Company


@role_required(User.Role.COMPANY)
def dashboard(request):
    company = getattr(request.user, "company_profile", None)
    return render(request, "companies/dashboard.html", {"company": company})


@role_required(User.Role.COMPANY)
def profile_edit(request):
    company = getattr(request.user, "company_profile", None)
    instance = company

    if request.method == "POST":
        form = CompanyProfileForm(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            new_company = form.save(commit=False)
            new_company.user = request.user
            new_company.save()
            messages.success(request, _("تم حفظ بيانات الشركة بنجاح."))
            return redirect("companies:dashboard")
    else:
        form = CompanyProfileForm(instance=instance)

    return render(request, "companies/profile_form.html", {"form": form, "company": company})


@role_required(User.Role.COMPANY)
def listing_request_create(request):
    company = get_object_or_404(Company, user=request.user)

    if request.method == "POST":
        form = ListingRequestForm(request.POST)
        if form.is_valid():
            listing_request = form.save(commit=False)
            listing_request.company = company
            listing_request.save()
            if company.listing_status == Company.ListingStatus.DRAFT:
                company.listing_status = Company.ListingStatus.PENDING_REVIEW
                company.save(update_fields=["listing_status"])
            messages.success(request, _("تم إرسال طلب الإدراج بنجاح، بانتظار مراجعة إدارة المنصة."))
            return redirect("companies:dashboard")
    else:
        form = ListingRequestForm()

    return render(request, "companies/listing_request_form.html", {"form": form, "company": company})
