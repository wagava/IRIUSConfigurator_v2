# from typing import Any, Mapping

from django import forms
from django.core.files.base import File
# from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Count, Q
# from django.db.models.base import Model
# from django.forms.utils import ErrorList
from general.models import cnfAttribute
from modules.utils import get_module_extra_data, get_modules_data_custom

from iriusconfig.constants import GlobalObjectID

from .models import cnfModule, cnfModuleValue
from .utils import get_module_types

MODULE_TYPE = get_module_types()

NUM_INTEGER_FIELD = 128  # Тип поля: целое число
NUM_BOOLEAN_FIELD = 129  # Тип поля: логический тип
GLOBAL_OBJECT_TYPE = GlobalObjectID.MODULE  # Тип глобального объекта: Модули


class ModuleForm(forms.ModelForm):
    """Класс формы для модулей."""

    value_id_by_order = {}
    invisible_fields = {}
    MOVEMENT_ID = None
    PLC_ID = None
    action = None
    OBJ_NEW = False

    def __init__(self, *args, **kwargs):
        self.MOVEMENT_ID = {}
        self.value_id_by_order = {}
        self.invisible_fields = {}
        module_id = kwargs.pop("id")  # Получаем аргумент из view

        plc_id = kwargs.pop("plc_id")
        self.PLC_ID = plc_id

        if not module_id:
            self.OBJ_NEW = True
            # при создании модуля берем последний индекс и прописываем автоматически
            if cnfModule.objects.filter(n_controller=plc_id).count() > 0:
                id_new = (
                    cnfModule.objects.filter(n_controller=plc_id)
                    .latest("n_module_index")
                    .n_module_index
                    + 1
                )
            else:
                id_new = 1

            self.base_fields["n_module_index"].initial = id_new
            self.base_fields["n_controller"].initial = plc_id

            # self.base_fields["c_name_module"].initial = 'Module'
            # self.base_fields["c_desc_module"].initial = 'Desc'
        super(ModuleForm, self).__init__(*args, **kwargs)

        fileds_attrs = list(
            # cnfAttribute.objects.exclude(n_attr_display_order=0).filter(
            cnfAttribute.objects.filter(
                (
                    Q(n_attribute_type=NUM_INTEGER_FIELD)
                    | Q(n_attribute_type=NUM_BOOLEAN_FIELD)
                )
                & Q(n_global_object_type=GlobalObjectID.MODULE)
                # & ~Q(n_attr_display_order=0)
            )
            .order_by("n_attr_display_order")
            .values()
        )
        if not self.OBJ_NEW:
            self.fields['n_module_index'].widget.attrs['readonly'] = 'readonly'
            
        if module_id is not None:
            extra_data = list(get_module_extra_data(n_module=module_id).values())
            value_data_by_order = []
            module = cnfModule.objects.get(pk=module_id)

            # Вычисляем следующий и предыдущий индекс

            step_module = (
                get_modules_data_custom(
                    n_module_index__lt=module.n_module_index,
                    n_controller=module.n_controller_id,
                )
                .exclude(n_module_index=module.n_module_index)
                .order_by("-n_module_index")
                .first()
            )
            self.MOVEMENT_ID["prev"] = step_module.id if step_module else module.id

            step_module = (
                get_modules_data_custom(
                    n_module_index__gt=module.n_module_index,
                    n_controller=module.n_controller_id,
                )
                .exclude(n_module_index=module.n_module_index)
                .order_by("n_module_index")
                .first()
            )
            self.MOVEMENT_ID["next"] = step_module.id if step_module else module.id

            for (
                attribute
            ) in fileds_attrs:  # fileds_attributes.values(): #values_list():
                attr_in_extra_data = False
                for item in extra_data:  # values_list():
                    # if attribute["n_attr_display_order"] == 0:
                    #     attr_in_extra_data = True

                    if attribute["id"] == item["n_attribute_id"]:
                        attr_in_extra_data = True
                        if attribute["n_attr_display_order"] == 0:  # exlude for visible

                            self.invisible_fields[attribute["c_name_attribute"]] = (
                                item["id"],
                                attribute["c_name_attribute"],
                            )
                        else:

                            value_data_by_order.append(item["f_value"])
                            # self.value_id_by_order.append(item["id"])
                            self.value_id_by_order[attribute["c_name_attribute"]] = item["id"]
                            break
                if not attr_in_extra_data and attribute["n_attr_display_order"] != 0:
                    value_data_by_order.append(0.0)
                    self.value_id_by_order[attribute["c_name_attribute"]] = None      

        # # Переводим данные в список, чтобы при обращении Джанго не делал запрос для каждого объекта

        list_attributes = []  # list(fileds_attrs)
        for item in list(fileds_attrs):
            if item["n_attr_display_order"] != 0:
                list_attributes.append(item)

        for index in range(len(list_attributes)):
            param_dict = {
                "label": list_attributes[index]["c_display_attribute"],
            }
            init = module_id is not None and len(value_data_by_order) >= index
            if (
                list_attributes[index]["n_attr_display_order"] != 0
            ):  # exlude for visible
                if list_attributes[index]["c_name_attribute"] == "TypeID":

                    param_dict = {
                        "widget": forms.Select(choices=MODULE_TYPE["module_types"]),
                        "label": "Тип модуля",
                    }

                    if init:
                        param_dict["initial"] = (
                            None
                            if value_data_by_order[index] is None
                            else int(value_data_by_order[index])
                        )
                    self.fields[
                        "attr_" + list_attributes[index]["c_name_attribute"]
                    ] = forms.IntegerField(**param_dict)
                elif list_attributes[index]["c_name_attribute"] == "DataTypeID":

                    param_dict = {
                        "widget": forms.Select(
                            choices=MODULE_TYPE["module_data_types"]
                        ),
                        "label": "Тип данных модуля",
                    }
                    if init:
                        param_dict["initial"] = (
                            None
                            if value_data_by_order[index] is None
                            else int(value_data_by_order[index])
                        )
                    self.fields[
                        "attr_" + list_attributes[index]["c_name_attribute"]
                    ] = forms.IntegerField(**param_dict)
                else:

                    if list_attributes[index]["n_attribute_type"] == NUM_INTEGER_FIELD:
                        if (
                            list_attributes[index]["n_attr_display_order"] != 0
                        ):  # exlude for visible
                            if init:
                                param_dict["initial"] = int(value_data_by_order[index])
                            else:
                                param_dict["initial"] = 0
                            self.fields[
                                "attr_" + list_attributes[index]["c_name_attribute"]
                            ] = forms.IntegerField(**param_dict)

                    else:
                        if init:
                            param_dict["initial"] = (
                                None
                                if value_data_by_order[index] is None
                                else bool(value_data_by_order[index])
                            )
                        param_dict["required"] = False
                        num = (
                            "0"
                            if list_attributes[index]["n_parameter_bit"] < 10
                            else ""
                        )
                        num += str(list_attributes[index]["n_parameter_bit"])
                        self.fields[
                            "attrb_" + num + list_attributes[index]["c_name_attribute"]
                        ] = forms.BooleanField(**param_dict)

    class Meta:
        model = cnfModule
        exclude = ("c_user_edit", "d_last_edit")


class ModulePropertiesForm(forms.ModelForm):
    """Класс формы для всех полей модулей."""

    class Meta:
        model = cnfModuleValue
        exclude = ("c_user_edit", "d_last_edit")
