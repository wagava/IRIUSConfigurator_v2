from django.contrib.auth import get_user_model
from django.shortcuts import redirect

from .forms import ModuleForm
from .models import cnfModule

User = get_user_model()


class ModuleMixin:
    """Миксин-класс модуля."""

    model = cnfModule
    template_name = "modules/create.html"
    form_class = ModuleForm

class ModuleAuthMixin:
    """Миксин-класс модуля проверки пользователя."""

    def dispatch(self, request, *args, **kwargs):
        user = User.objects.get(username=self.request.user.username)
        if not user.is_staff:
            return redirect('modules:module_home')
        return super().dispatch(request, *args, **kwargs)