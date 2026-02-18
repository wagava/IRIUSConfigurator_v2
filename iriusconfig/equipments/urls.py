from django.urls import path

from . import views

app_name = "equipments"

# переделать все под роутер
urlpatterns = [
    path("", views.equipment_home, name="equipment_home"),
    # path("plc/<int:plc_id>/", views.equipment_home, name="equipment_home"),    
    path(
        "plc/<int:plc_id>/", views.EquipmentListView.as_view(), name="equipment_by_plc"
    ),
    path(
        "plc/<int:plc_id>/filter/",
        views.EquipmentListView.as_view(),
        name="equipment_by_plc_filter",
    ),
    path(
        "plc/<int:plc_id>/create/",
        views.EquipmentCreateView.as_view(),
        name="equipment_create",
    ),
    path(
        "plc/<int:plc_id>/edit/<int:eq_id>/",
        views.EquipmentUpdateView.as_view(),
        name="equipment_edit",
    ),
    path(
        "plc/<int:plc_id>/delete/<int:eq_id>/",
        views.EquipmentDeleteView.as_view(),
        name="equipment_delete",
    ),
    path(
        "download/<int:plc_id>/", views.download_equipments, name="download_equipments"
    ),
    path("upload/<int:plc_id>/", views.upload_equipments, name="upload_equipments"),
    path("check_state/", views.check_state, name="check_state"),
]
