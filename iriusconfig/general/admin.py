from django.contrib import admin

from .models import cnfAttribute, cnfController  # cnfValueList,


class cnfControllerAdmin(admin.ModelAdmin):
    list_display = (
        "c_name_controller",
        "c_ip_controller",
        "c_desc_controller",
    )

    list_editable = ("c_desc_controller",)
    search_fields = ("c_name_controller",)
    list_display_links = ("c_name_controller",)


class cnfAttributeAdmin(admin.ModelAdmin):
    list_display = (
        "c_name_attribute",
        "c_display_attribute",
    )

    list_display_links = ("c_name_attribute",)


admin.site.empty_value_display = "Не выбран"
admin.site.register(cnfController, cnfControllerAdmin)
admin.site.register(cnfAttribute, cnfAttributeAdmin)
