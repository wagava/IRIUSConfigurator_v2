from django.contrib import admin

from .models import (cnfEquipmentPIDVariableRole, cnfEquipmentRole,
                     cnfEquipmentType, cnfEquipmentVariableRole)


class cnfEquipmentTypeAdmin(admin.ModelAdmin):
    list_display = (
        "n_type_value",
        "c_type_name",
        "c_type_desc",
        "n_global_object_type",
    )

    list_display_links = ("c_type_name",)


class cnfEquipmentRoleAdmin(admin.ModelAdmin):
    list_display = (
        "n_role_index",
        "c_role_name",
        "c_role_desc",
    )

    list_display_links = ("c_role_desc",)


class cnfEquipmentVariableRoleAdmin(admin.ModelAdmin):
    list_display = (
        "n_role_index",
        "c_role_name",
        "c_role_desc",
    )

    list_display_links = ("c_role_desc",)


class cnfEquipmentPIDVariableRoleAdmin(admin.ModelAdmin):
    list_display = (
        "n_role_index",
        "c_role_name",
        "c_role_desc",
    )

    list_display_links = ("c_role_desc",)


admin.site.empty_value_display = "Не выбран"
admin.site.register(cnfEquipmentType, cnfEquipmentTypeAdmin)
admin.site.register(cnfEquipmentRole, cnfEquipmentRoleAdmin)
admin.site.register(cnfEquipmentVariableRole, cnfEquipmentVariableRoleAdmin)
admin.site.register(cnfEquipmentPIDVariableRole, cnfEquipmentPIDVariableRoleAdmin)
