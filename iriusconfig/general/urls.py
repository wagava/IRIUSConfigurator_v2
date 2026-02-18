from django.urls import path
from django.views.generic import TemplateView

from . import views

app_name = "general"

urlpatterns = [
    path(
        "about/", TemplateView.as_view(template_name="pages/about.html"), name="about"
    ),
    path("password/generate/", views.generate, name="generate"),
    path('', views.index, name='index'),
]
