from django.contrib import admin

# Register your models here.
# from .models import cnfVariableType


# class cnfVariableTypeAdmin(admin.ModelAdmin):
#     list_display = (
#         'c_variable_type',
#         'n_variable_type',
#     )

#     list_display_links = ('c_variable_type',)


admin.site.empty_value_display = "Не выбран"
# admin.site.register(cnfVariableType, cnfVariableTypeAdmin)
