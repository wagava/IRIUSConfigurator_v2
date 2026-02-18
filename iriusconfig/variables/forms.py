from django import forms
from equipments.models import cnfEquipment
from general.models import cnfAttribute, cnfController
from modules.models import cnfModule
from variables.utils import get_variables_data_custom, get_variables_extra_data

from iriusconfig.constants import AttributeFieldType, GlobalObjectID

from .models import (User, cnfVariable, cnfVariableDataType, cnfVariableType,
                     cnfVariableValue)

GLOBAL_OBJECT_TYPE = GlobalObjectID.VARIABLE  # Тип глобального объекта: Переменные


class VariableForm(forms.ModelForm):
    """Класс формы для variable."""

    attr_fields_by_group = (
        {}
    )  # словарь, где ключ - группа, и значения полей атрибутов, которые вход в группу
    base_fields_by_group = {
        "Основные": [  # 'n_controller',
            "n_variable_index",
            "c_name_variable",
            "c_desc_variable",
            "c_signal_ident",
        ],
        "Принадлежность": ["c_name_section", "c_name_position", "c_num_position"],
        "Адрес и тип": [
            "n_controller",
            "n_module_channel",
            "n_module_id",
            "n_variable_type",
            "n_variable_data_type",
            "b_masked",
        ],
        # 'ППИ':['n_controller_id',
        #                 'n_module_channel',
        #                 'n_module_id',
        #                 'n_variable_type',
        #                 'n_variable_data_type']
    }
    variable_fields_model = {}
    value_id_by_order = {}  #  value_id_by_order = []
    invisible_fields_id = None  #
    list_modules = []  # список модулей выбранного ПЛК
    list_plc = []
    variable_types = []
    variable_data_types = []
    variable_list = None
    MOVEMENT_ID = None
    OBJ_NEW = False
    
    def __init__(self, *args, **kwargs):
        self.MOVEMENT_ID = {}
        self.attr_fields_by_group = {}

        self.value_id_by_order = {}  # []
        self.invisible_fields_id = {}
        self.list_plc = []
        self.list_modules = []
        self.variable_types = []
        self.variable_data_types = []
        self.variable_fields_model = {}

        variable_id = kwargs.pop("id")  # Получаем аргумент из view
        plc_id = kwargs.pop("plc_id")

        if not variable_id:
            self.OBJ_NEW = True
            # при создании модуля берем последний индекс и прописываем автоматически
            if cnfVariable.objects.filter(n_controller=plc_id).count() > 0:
                id_new = (
                    cnfVariable.objects.filter(n_controller=plc_id)
                    .latest("n_variable_index")
                    .n_variable_index
                    + 1
                )
            else:
                id_new = 1
        else:
            variable = cnfVariable.objects.get(pk=variable_id)
            step_var = (
                get_variables_data_custom(
                    n_variable_index__lt=variable.n_variable_index,
                    n_controller=variable.n_controller_id,
                )[0]
                .exclude(n_variable_index=variable.n_variable_index)
                .order_by("-n_variable_index")
                .first()
            )
            self.MOVEMENT_ID["prev"] = step_var.id if step_var else variable.id

            step_var = (
                get_variables_data_custom(
                    n_variable_index__gt=variable.n_variable_index,
                    n_controller=variable.n_controller_id,
                )[0]
                .exclude(n_variable_index=variable.n_variable_index)
                .order_by("n_variable_index")
                .first()
            )
            self.MOVEMENT_ID["next"] = step_var.id if step_var else variable.id

        super(VariableForm, self).__init__(*args, **kwargs)

        fileds_attrs = list(
            cnfAttribute.objects.filter(n_global_object_type=GlobalObjectID.VARIABLE)
            .order_by("n_attr_display_order")
            .values()
        )

        self.variable_types = list(cnfVariableType.objects.all().values())
        self.variable_data_types = list(cnfVariableDataType.objects.all().values())
        self.list_modules = list(
            cnfModule.objects.filter(n_controller=plc_id)
            .order_by("n_module_index")
            .values()
        )

        self.list_plc = list(cnfController.objects.all().values())
        self.variable_list = list(cnfVariable.objects.all().values())
        self.equipment_list = list(cnfEquipment.objects.all().values())

        # пока хардкод, надо двигаться дальше, сроки... Вернуться и переделать после командного интерфейса
        self.base_fields["c_name_variable"].widget.attrs = {"class": "form-control"}
        self.base_fields["c_desc_variable"].widget.attrs = {"class": "form-control"}
        self.base_fields["c_signal_ident"].widget.attrs = {"class": "form-control"}
        self.base_fields["n_variable_index"].widget.attrs = {"class": "form-control"}
        self.base_fields["n_controller"].widget.attrs = {"class": "form-select selcls"}

        self.base_fields["c_name_section"].widget.attrs = {"class": "form-control"}
        self.base_fields["c_name_position"].widget.attrs = {"class": "form-control"}
        self.base_fields["c_num_position"].widget.attrs = {"class": "form-control"}

        self.base_fields["n_module_channel"].widget.attrs = {"class": "form-control"}
        self.base_fields["n_module_id"].required = False
        self.base_fields["n_module_id"].widget.attrs = {"class": "form-control"}
        self.base_fields["n_variable_type"].widget.attrs = {
            "class": "form-select selcls"
        }
        self.base_fields["n_variable_data_type"].widget.attrs = {
            "class": "form-select selcls"
        }
        # self.base_fields['b_masked'].widget.attrs = {'class': 'form-check-label'}

        self.base_fields["c_name_section"].initial = (
            self.initial["c_name_section"] if variable_id else None
        )
        self.base_fields["c_desc_variable"].initial = (
            self.initial["c_desc_variable"] if variable_id else None
        )
        self.base_fields["c_signal_ident"].initial = (
            self.initial["c_signal_ident"] if variable_id else None
        )
        self.base_fields["n_variable_index"].initial = (
            self.initial["n_variable_index"] if variable_id else id_new
        )
        # if not self.OBJ_NEW:
        #     self.fields['n_variable_index'].widget.attrs['readonly'] = 'readonly'
        self.base_fields["n_controller"].initial = (
            self.initial["n_controller"] if variable_id else plc_id
        )

        self.base_fields["c_name_variable"].initial = (
            self.initial["c_name_variable"] if variable_id else None
        )
        self.base_fields["c_name_position"].initial = (
            self.initial["c_name_position"] if variable_id else None
        )
        self.base_fields["c_num_position"].initial = (
            self.initial["c_num_position"] if variable_id else None
        )

        self.base_fields["n_module_channel"].initial = (
            self.initial["n_module_channel"] if variable_id else None
        )
        self.base_fields["n_module_id"].initial = (
            self.initial["n_module_id"] if variable_id else None
        )
        self.base_fields["n_variable_type"].initial = (
            self.initial["n_variable_type"] if variable_id else None
        )
        self.base_fields["n_variable_data_type"].initial = (
            self.initial["n_variable_data_type"] if variable_id else None
        )
        # self.base_fields['b_masked'].initial = self.initial['b_masked'] if variable_id else None
        if self.base_fields.get("b_masked"):
            del self.base_fields["b_masked"]

        value_data_by_order = []
        value_data_by_order_dict = {}
        if variable_id is not None:
            extra_data = list(get_variables_extra_data(n_variable=variable_id).values())

            for attribute in fileds_attrs:
                for item in extra_data:

                    if attribute["id"] == item["n_attribute_id"]:
                        if attribute["n_attr_display_order"] == 0:  # exlude for visible

                            self.invisible_fields_id[attribute["c_name_attribute"]] = (
                                item["id"]
                            )
                        else:
                            value_data_by_order.append(item["f_value"])
                            # self.value_id_by_order.append(item["id"])
                            self.value_id_by_order[attribute["c_name_attribute"]] = (
                                item["id"]
                            )
                            if attribute["c_name_attribute"] != "Formula":
                                value_data_by_order_dict[item["n_attribute_id"]] = item[
                                    "f_value"
                                ]
                            else:
                                value_data_by_order_dict[item["n_attribute_id"]] = item[
                                    "c_formula"
                                ]
                            break

        group_name = ""
        index_iter = 0
        for item in fileds_attrs:

            init = variable_id is not None
            if item["n_attr_display_order"] != 0:
                if (
                    group_name != item["c_attr_display_group"]
                    and item["c_attr_display_group"] not in self.attr_fields_by_group
                ):
                    self.attr_fields_by_group[item["c_attr_display_group"]] = [
                        item
                    ]  # list.append(item)
                    group_name = item["c_attr_display_group"]
                else:
                    self.attr_fields_by_group[item["c_attr_display_group"]].append(item)

                param_dict = {
                    "label": item["c_display_attribute"],
                }

                if item["n_attribute_type"] == AttributeFieldType.INTEGER_FIELD:
                    if init:
                        self.attr_fields_by_group[item["c_attr_display_group"]][-1][
                            "initial"
                        ] = value_data_by_order_dict.get(item["id"])
                        #  здесь в текущий список по индексу добавить ключ инишиал со значением self.attr_fields_by_group[item['c_attr_display_group']]
                    self.fields["attr_" + item["c_name_attribute"]] = (
                        forms.IntegerField(**param_dict)
                    )
                    self.fields["attr_" + item["c_name_attribute"]].widget.attrs = {
                        "class": "form-control"
                    }

                elif item["n_attribute_type"] == AttributeFieldType.FLOAT_FIELD:
                    if init:
                        param_dict["initial"] = value_data_by_order_dict.get(
                            item["id"]
                        )  # value_data_by_order[index_iter]
                        self.attr_fields_by_group[item["c_attr_display_group"]][-1][
                            "initial"
                        ] = value_data_by_order_dict.get(item["id"])
                    self.fields["attrf_" + item["c_name_attribute"]] = forms.FloatField(
                        **param_dict
                    )
                    self.fields["attrf_" + item["c_name_attribute"]].widget.attrs = {
                        "class": "form-control"
                    }
                elif item["n_attribute_type"] == AttributeFieldType.TEXT_FIELD:
                    if init:
                        param_dict["initial"] = value_data_by_order_dict.get(
                            item["id"]
                        )  # value_data_by_order[index_iter]
                        self.attr_fields_by_group[item["c_attr_display_group"]][-1][
                            "initial"
                        ] = value_data_by_order_dict.get(item["id"])
                    param_dict |= {"widget": forms.Textarea, "required": False}
                    self.fields["attrtxt_" + item["c_name_attribute"]] = (
                        forms.CharField(**param_dict)
                    )  # , widget=forms.Textarea)
                    self.fields["attrtxt_" + item["c_name_attribute"]].widget.attrs = {
                        "class": "form-control"
                    }  # , 'widget':forms.Textarea}
                else:
                    if init:
                        param_dict["initial"] = bool(
                            value_data_by_order_dict.get(item["id"])
                        )  # bool(value_data_by_order[index_iter])
                        # fff = self.attr_fields_by_group[item["c_attr_display_group"]][
                        #     -1
                        # ]
                        self.attr_fields_by_group[item["c_attr_display_group"]][-1][
                            "initial"
                        ] = bool(value_data_by_order_dict.get(item["id"]))
                    param_dict["required"] = False
                    num = "0" if item["n_parameter_bit"] < 10 else ""
                    num += str(item["n_parameter_bit"])
                    self.fields["attrb_" + num + item["c_name_attribute"]] = (
                        forms.BooleanField(**param_dict)
                    )
                    self.fields[
                        "attrb_" + num + item["c_name_attribute"]
                    ].widget.attrs = {"class": "form-check-input"}

    class Meta:
        model = cnfVariable
        exclude = ("c_user_edit", "d_last_edit")
