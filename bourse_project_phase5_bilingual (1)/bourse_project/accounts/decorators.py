from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext as _


def role_required(role):
    """
    يمنع أي مستخدم من الوصول للوحة تحكم لا تطابق دوره
    (مثلاً منع سمسار من فتح لوحة تحكم شركة).
    """

    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.user.role != role:
                raise PermissionDenied(_("ليس لديك صلاحية الوصول لهذه الصفحة"))
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator
