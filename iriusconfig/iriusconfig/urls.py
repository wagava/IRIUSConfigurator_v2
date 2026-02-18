# from django.conf import settings
# from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
# from django.views.generic.edit import CreateView

# handler404 = 'pages.views.page_not_found'
# handler500 = 'pages.views.server_error'

urlpatterns = [
    path('api/', include('api.urls')),
    path("admin/", admin.site.urls),
    path("modules/", include("modules.urls", namespace="modules")),
    path("general/", include("general.urls", namespace="general")),
    path("variables/", include("variables.urls", namespace="variables")),
    path("equipments/", include("equipments.urls", namespace="equipments")),
    path('accounts/', include('accounts.urls')),
    # path('accounts/', include('django_pam.accounts.urls')),
    # re_path(r'^django-pam/', include('django_pam.urls')),
    # re_path(r'^login/$', LoginView.as_view(template_name='<your template dir>/login.html'),
    # name='login'),
    # re_path(r"^logout/(?P<next>[\w\-\:/]+)?$", LogoutView.as_view(
    # template_name='<your template dir>/logout.html'), name='logout'),
]

# if settings.DEBUG:
#     import debug_toolbar
#     urlpatterns += (path('__debug__/', include(debug_toolbar.urls)),)

# urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
