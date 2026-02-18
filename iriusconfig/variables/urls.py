from django.urls import path

from . import views

app_name = "variables"

urlpatterns = [
    path("", views.variable_home, name="variable_home"),
    path(
        "plc/<int:plc_id>/",
        views.VariableListView.as_view(),
        name="variable_by_plc",
    ),
    path(
        "plc/<int:plc_id>/filter/",
        views.VariableListView.as_view(),
        name="variable_by_plc_filter",
    ),
    path(
        "plc/<int:plc_id>/create/",
        views.VariableCreateView.as_view(),
        name="variable_create",
    ),
    path(
        "plc/<int:plc_id>/edit/<int:var_id>/",
        views.VariableUpdateView.as_view(),
        name="variable_edit",
    ),
    path(
        "plc/<int:plc_id>/delete/<int:var_id>/",
        views.VariableDeleteView.as_view(),
        name="variable_delete",
    ),
    path("plc/tags_update/<int:plc_id>", views.tags_update, name="tags_update"),
    path("plc/tags_delete/<int:plc_id>", views.tags_delete, name="tags_delete"),
    path("check_state/", views.check_state, name="check_state"),
    path(
        "variables/download/<int:plc_id>/",
        views.download_variables,
        name="download_variables",
    ),
    path(
        "variables/upload/<int:plc_id>/",
        views.upload_variables,
        name="upload_variables",
    ),
    path(
        "export/",
        views.export_csv,
        name="export_csv",
    ),
]
