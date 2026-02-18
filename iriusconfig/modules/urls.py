from django.urls import path

from . import views

app_name = "modules"

urlpatterns = [
    path("modbus/", views.modbus, name="modbus"),
    path("ch_st/", views.check_state, name="check_state"),
    path("", views.module_home, name="module_home"),
    path("plc/<int:plc_id>", views.ModuleListView.as_view(), name="module_by_plc"),
    path(
        "plc/<int:plc_id>/filter/",
        views.ModuleListView.as_view(),
        name="module_by_plc_filter",
    ),
    path(
        "plc/<int:plc_id>/create/",
        views.ModuleCreateView.as_view(),
        name="create_module",
    ),
    path("<int:module_id>/", views.ModuleDetailView.as_view(), name="module_detail"),
    path(
        "plc/<int:plc_id>/edit/<int:module_id>/",
        views.ModuleUpdateView.as_view(),
        name="module_edit",
    ),
    path(
        "plc/<int:plc_id>/delete/<int:module_id>/",
        views.ModuleDeleteView.as_view(),
        name="module_delete",
    ),
    path(
        "modules/download/<int:plc_id>/",
        views.download_modules,
        name="download_modules",
    ),
    path("modules/upload/<int:plc_id>/", views.upload_modules, name="upload_modules"),
]
