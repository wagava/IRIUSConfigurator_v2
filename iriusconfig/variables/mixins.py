from django.contrib.auth import get_user_model
from django.shortcuts import redirect

from .forms import VariableForm
from .models import cnfVariable

User = get_user_model()


class VariableMixin:
    """Миксин-класс переменной."""

    model = cnfVariable
    template_name = "variables/create.html"
    form_class = VariableForm

class VariableAuthMixin:
    """Миксин-класс переменных для проверки пользователя."""

    def dispatch(self, request, *args, **kwargs):
        user = User.objects.get(username=self.request.user.username)
        if not user.is_staff:
            return redirect('variables:variable_home')
        return super().dispatch(request, *args, **kwargs)