from django.contrib import admin

from .models import cnfModule, cnfModuleDataType, cnfModuleType


class cnfModuleTypeAdmin(admin.ModelAdmin):
    list_display = (
        "n_type_value",
        "c_type_name",
        "c_type_desc",
    )

    list_display_links = ("c_type_name",)


class cnfModuleDataTypeAdmin(admin.ModelAdmin):

    list_display = (
        "n_type_value",
        "c_type_name",
        "c_type_desc",
    )

    list_display_links = ("c_type_name",)


admin.site.empty_value_display = "Не выбран"
admin.site.register(cnfModule)
admin.site.register(cnfModuleType, cnfModuleTypeAdmin)
admin.site.register(cnfModuleDataType, cnfModuleDataTypeAdmin)
