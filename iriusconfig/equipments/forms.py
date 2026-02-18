from django import forms
from django.core.files.base import File
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Count, Q, F
from django.db.models.base import Model
from django.forms.models import model_to_dict
from django.forms.utils import ErrorList
from django.utils import timezone
from general.models import cnfAttribute, cnfController
from modules.models import cnfModule
from variables.models import cnfVariable

from iriusconfig.constants import (AttributeFieldType, EquipmentTypeConstants,
                                   GlobalObjectID)

from .models import (cnfEquipment, cnfEquipmentLinkedEquipment,
                     cnfEquipmentLinkedPIDVariable, cnfEquipmentLinkedVariable,
                     cnfEquipmentLinkedWord, cnfEquipmentPIDVariableRole,
                     cnfEquipmentRole, cnfEquipmentType, cnfEquipmentValue,
                     cnfEquipmentVariableRole, cnfSequenceLinkedEquipment,
                     cnfSequenceLinkedVariable, cnfSequenceRole)
from .utils import get_equipments_data_custom, get_equipments_extra_data

GLOBAL_OBJECT_TYPE = GlobalObjectID.VARIABLE  # Тип глобального объекта: Переменные


class EquipmentForm(forms.ModelForm):
    """Класс формы для equipment."""

    attr_fields_by_group = (
        {}
    )  # словарь, где ключ - группа, и значения полей атрибутов, которые вход в группу
    base_fields_by_group = {
        "Основные": [
            "n_controller",
            "n_equipment_index",
            "c_name_equipment",
            "c_desc_equipment",
        ],
        "Принадлежность и тип": [
            "c_name_section",
            "c_name_position",
            "c_num_position",
            "n_type_id",
            "b_masked",
        ],
        # 'Адрес и тип':['n_controller',
        #                 'n_module_channel',
        #                 'n_module_id',
        #                 'n_variable_type',
        #                 'n_variable_data_type'],
        # 'ППИ':['n_controller_id',
        #                 'n_module_channel',
        #                 'n_module_id',
        #                 'n_variable_type',
        #                 'n_variable_data_type']
    }
    ROLES = {
        "variable": list(cnfEquipmentVariableRole.objects.all().order_by("n_role_index").values()),
        "equipment": list(cnfEquipmentRole.objects.all().order_by("n_role_index").values()),
        "variable_pid": list(cnfEquipmentPIDVariableRole.objects.all().order_by("n_role_index").values()),
        "sequence": list(cnfSequenceRole.objects.all().order_by("n_role_index").values()),
    }
    RANGE_100 = [x for x in range(2, 101)]
    DATA_ROLES = {}
    VAR_DATA_ROLES = None
    VAR_PID_DATA_ROLES = None
    EQ_DATA_ROLES = None
    EQ_DATA_ROLES_BIT_SW_WORDS = None
    pid_fields_attrs = None
    ats_fields_attrs = None
    seq_fields_attrs = None
    EQ_PID_DATA_FIELDS = None
    EQ_PID_DATA_FIELDS_IDS = None
    EQ_SEQ_DATA_FIELDS = None
    EQ_SEQ_DATA_STEPS = None
    EQ_ATS_DATA_FIELDS = None
    EQ_ATS_DATA_FIELDS_IDS = None
    EQ_SEQ_DATA_FIELDS_IDS = None
    OBJ_NEW = False
    
    value_id_by_order = []  #
    invisible_fields_id = []  #
    invisible_fields_eq_types = None

    list_plc = []
    equipment_types = []

    MOVEMENT_ID = None

    def __init__(self, *args, **kwargs):
        # !!! На уровне вью определить какого типа оборудования и делать выборки доп.конфигураций только по нему
        self.MOVEMENT_ID = {}
        self.attr_fields_by_group = {}
        self.DATA_ROLES = {}
        self.EQ_DATA_ROLES = None
        self.VAR_DATA_ROLES = None
        self.VAR_PID_DATA_ROLES = None
        self.EQ_DATA_ROLES_BIT_SW_WORDS = None
        self.EQ_PID_DATA_FIELDS = {}
        self.EQ_PID_DATA_FIELDS_IDS = {}
        self.EQ_SEQ_DATA_FIELDS = {}
        self.EQ_SEQ_DATA_STEPS = {}
        self.EQ_ATS_DATA_FIELDS = {}
        self.EQ_ATS_DATA_FIELDS_IDS = {}
        self.EQ_SEQ_DATA_FIELDS_IDS = {}

        self.pid_fields_attrs = {}
        self.ats_fields_attrs = {}
        self.seq_fields_attrs = {}
        self.value_id_by_order = {}
        self.invisible_fields_id = []
        self.invisible_fields_eq_types = {}
        self.list_plc = []

        self.equipment_types = []

        # Получаем аргумент из view
        equipment_id = kwargs.pop("id") if kwargs.get("id") else None
        plc_id = kwargs.pop("plc_id") if kwargs.get("plc_id") else None
        n_type_value = (
            kwargs.pop("n_type_value") if kwargs.get("n_type_value") else None
        )

        if not equipment_id:
            self.OBJ_NEW = True
            # при создании модуля берем последний индекс и прописываем автоматически
            if cnfEquipment.objects.filter(n_controller=plc_id).count() > 0:
                id_new = (
                    cnfEquipment.objects.filter(n_controller=plc_id)
                    .latest("n_equipment_index")
                    .n_equipment_index
                    + 1
                )
            else:
                id_new = 1

            self.base_fields["n_equipment_index"].initial = id_new
            self.base_fields["n_controller"].initial = plc_id

        super(EquipmentForm, self).__init__(*args, **kwargs)

        self.DATA_ROLES = {
            "variable": list(
                cnfVariable.objects.filter(n_controller=plc_id)
                .all()
                .order_by("n_variable_index")
                .values()
            ),
            "equipment": list(
                cnfEquipment.objects.filter(n_controller=plc_id)
                .all()
                .order_by("n_equipment_index")
                .values()
            ),
        }

        if equipment_id:
            equipment = cnfEquipment.objects.get(pk=equipment_id)
            step_eq = (
                get_equipments_data_custom(
                    n_equipment_index__lt=equipment.n_equipment_index,
                    n_controller=equipment.n_controller_id,
                )[0]
                .exclude(n_equipment_index=equipment.n_equipment_index)
                .order_by("-n_equipment_index")
                .first()
            )
            self.MOVEMENT_ID["prev"] = step_eq.id if step_eq else equipment.id

            step_eq = (
                get_equipments_data_custom(
                    n_equipment_index__gt=equipment.n_equipment_index,
                    n_controller=equipment.n_controller_id,
                )[0]
                .exclude(n_equipment_index=equipment.n_equipment_index)
                .order_by("n_equipment_index")
                .first()
            )
            self.MOVEMENT_ID["next"] = step_eq.id if step_eq else equipment.id

            # self.VAR_DATA_ROLES = [
            #     item_role
            #     for item_role in cnfEquipmentLinkedVariable.objects.filter(
            #         n_equipment=equipment_id
            #     ).order_by('n_index').values()
            # ]
            self.VAR_DATA_ROLES = [
                item_role
                for item_role in cnfEquipmentLinkedVariable.objects.filter(
                    n_equipment=equipment_id
                # ).annotate(
                #             n_role_id=F('n_role'),
                #             n_variable_id=F('n_variable'),
                #             n_equipment_id=F('n_equipment')
                            ).select_related('n_variable').order_by('n_index').values('id','n_index','n_equipment_id','n_role_id','n_timer','n_variable_id','b_masked','n_variable__n_variable_index')
            ]
            if (
                n_type_value == EquipmentTypeConstants.TYPE_P_DC
                or n_type_value == EquipmentTypeConstants.TYPE_PID_AI
                or n_type_value == EquipmentTypeConstants.TYPE_PID_DC
            ):
                self.VAR_PID_DATA_ROLES = [
                    item_role
                    for item_role in cnfEquipmentLinkedPIDVariable.objects.filter(
                        n_equipment=equipment_id
                        ).select_related('n_variable_link').order_by('n_index').values('id','n_index','n_equipment_id','n_role_id','n_timer','n_variable_link_id','b_masked','n_variable_link__n_variable_index')
                    # ).order_by('n_index').values()
                ]

            # if (type_id == EquipmentTypeConstants.TYPE_ATS):
            #     self.VAR_PID_DATA_ROLES = [
            #         item_role
            #         for item_role in cnfEquipmentLinkedPIDVariable.objects.filter(n_equipment=equipment_id).values()
            #     ]
            self.EQ_DATA_ROLES = [
                item_role
                for item_role in cnfEquipmentLinkedEquipment.objects.filter(
                    n_equipment=equipment_id
                ).select_related('n_equipment_link').order_by('n_index').values('id','n_index','n_equipment_id','n_role_id','n_timer','n_equipment_link_id','b_masked','n_equipment_link__n_equipment_index')
            ]
            self.EQ_DATA_ROLES_BIT_SW_WORDS = [
                item_role
                for item_role in cnfEquipmentLinkedWord.objects.filter(
                    n_equipment=equipment_id,
                    n_word_type=EquipmentTypeConstants.WORD_TYPE_STATUSWORD,
                ).values()
            ]
            self.EQ_DATA_ROLES_BIT_CW_WORDS = [
                item_role
                for item_role in cnfEquipmentLinkedWord.objects.filter(
                    n_equipment=equipment_id,
                    n_word_type=EquipmentTypeConstants.WORD_TYPE_CONTROLWORD,
                ).values()
            ]

            if n_type_value == EquipmentTypeConstants.TYPE_EQ14:
                # Sequence
                all_steps = {}
                var_steps = (
                    cnfSequenceLinkedVariable.objects.select_related("n_role","n_equipment","n_variable")
                    .all()
                    .filter(n_equipment=equipment_id, n_equipment__n_controller=plc_id)
                    .values(
                        "id",
                        "n_equipment_id",
                        "n_role_id",
                        "n_timer",
                        "n_step",
                        "n_variable_link_id",
                        "n_seq_type",
                        "b_masked",
                        "n_role__b_role_equipment",
                        "n_variable_link__n_variable_index",
                    )
                )
                eq_steps = (
                    cnfSequenceLinkedEquipment.objects.select_related("n_role","n_equipment","n_equipment_link")
                    .all()
                    .filter(n_equipment=equipment_id, n_equipment__n_controller=plc_id)
                    .values(
                        "id",
                        "n_equipment_id",
                        "n_role_id",
                        "n_timer",
                        "n_step",
                        "n_equipment_link_id",
                        "n_seq_type",
                        "b_masked",
                        "n_role__b_role_equipment",
                        "n_equipment_link__n_equipment_index",
                    )
                )

                for item_var in var_steps:
                    if not all_steps.get(item_var["n_seq_type"]):
                        all_steps[item_var["n_seq_type"]] = {}
                    all_steps[item_var["n_seq_type"]][item_var["n_step"]] = item_var

                for item_eq in eq_steps:
                    if not all_steps.get(item_eq["n_seq_type"]):
                        all_steps[item_eq["n_seq_type"]] = {}
                    all_steps[item_eq["n_seq_type"]][item_eq["n_step"]] = item_eq
                # SORTING!!!!!!!!!!!!!!!!

                for i in range(1, 5):
                    if all_steps.get(i):
                        self.EQ_SEQ_DATA_STEPS[i] = sorted(all_steps[i].items())

            # ATS
            ats_values = (
                cnfEquipmentValue.objects.filter(n_equipment=equipment_id)
                .select_related("n_attribute")
                .filter(n_attribute__n_global_object_type=GlobalObjectID.ATS)
                .order_by("n_attribute__n_attr_display_order")
            )
            
            for item in ats_values:
                if item.n_attribute.n_attr_display_order == 0:
                    self.invisible_fields_eq_types[
                        item.n_attribute.c_name_attribute
                    ] = item.pk
                else:
                    if not self.EQ_ATS_DATA_FIELDS.get(
                        item.n_attribute.c_attr_display_group
                    ):
                        self.EQ_ATS_DATA_FIELDS[
                            item.n_attribute.c_attr_display_group
                        ] = {}
                    self.EQ_ATS_DATA_FIELDS[item.n_attribute.c_attr_display_group][
                        item.n_attribute.c_name_attribute
                    ] = item.f_value
                    self.EQ_ATS_DATA_FIELDS_IDS[item.n_attribute.c_name_attribute] = (
                        item.id
                    )

            # PID
            equipment_values = (
                cnfEquipmentValue.objects.filter(n_equipment=equipment_id)
                .select_related("n_attribute")
                .filter(n_attribute__n_global_object_type=GlobalObjectID.PID)
                .order_by("n_attribute__n_attr_display_order")
            )

            for item in equipment_values:
                if item.n_attribute.n_attr_display_order == 0:
                    self.invisible_fields_eq_types[
                        item.n_attribute.c_name_attribute
                    ] = item.pk
                else:
                    if not self.EQ_PID_DATA_FIELDS.get(
                        item.n_attribute.c_attr_display_group
                    ):
                        self.EQ_PID_DATA_FIELDS[
                            item.n_attribute.c_attr_display_group
                        ] = {}
                    self.EQ_PID_DATA_FIELDS[item.n_attribute.c_attr_display_group][
                        item.n_attribute.c_name_attribute
                    ] = item.f_value
                    self.EQ_PID_DATA_FIELDS_IDS[item.n_attribute.c_name_attribute] = (
                        item.id
                    )

            # Sequences
            equipment_values = (
                cnfEquipmentValue.objects.filter(n_equipment=equipment_id)
                .select_related("n_attribute")
                .filter(n_attribute__n_global_object_type=GlobalObjectID.SEQUENCE)
                .order_by("n_attribute__n_attr_display_order")
            )

            for item in equipment_values:
                if item.n_attribute.n_attr_display_order == 0:
                    self.invisible_fields_eq_types[
                        item.n_attribute.c_name_attribute
                    ] = item.pk
                else:
                    if not self.EQ_SEQ_DATA_FIELDS.get(
                        item.n_attribute.c_attr_display_group
                    ):
                        self.EQ_SEQ_DATA_FIELDS[
                            item.n_attribute.c_attr_display_group
                        ] = {}
                    self.EQ_SEQ_DATA_FIELDS[item.n_attribute.c_attr_display_group][
                        item.n_attribute.c_name_attribute
                    ] = item
                    self.EQ_SEQ_DATA_FIELDS_IDS[item.n_attribute.c_name_attribute] = (
                        item.id
                    )

        fileds_attrs = list(
            cnfAttribute.objects.filter(n_global_object_type=GlobalObjectID.EQUIPMENT)
            .order_by("n_attr_display_order")
            .values()
        )

        display_group = None

        for item_pid in (
            cnfAttribute.objects.exclude(n_attr_display_order=0)
            .filter(n_global_object_type=GlobalObjectID.PID)
            .order_by("n_attr_display_order")
            .values()
        ):

            if display_group != item_pid["c_attr_display_group"]:
                self.pid_fields_attrs[item_pid["c_attr_display_group"]] = []

            if self.EQ_PID_DATA_FIELDS:  # если это выборка с данными для оборудования
                if self.EQ_PID_DATA_FIELDS.get(item_pid["c_attr_display_group"]):
                    for item_key, item_value in self.EQ_PID_DATA_FIELDS[
                        item_pid["c_attr_display_group"]
                    ].items():
                        if item_key == item_pid["c_name_attribute"]:
                            item_pid["f_value"] = item_value
                            break

            self.pid_fields_attrs[item_pid["c_attr_display_group"]].append(item_pid)

            display_group = item_pid["c_attr_display_group"]

        # для последовательности. Аналог кода выше, позже оптимизировать

        for item_pid in (
            cnfAttribute.objects.exclude(n_attr_display_order=0)
            .filter(n_global_object_type=GlobalObjectID.SEQUENCE)
            .order_by("n_attr_display_order")
            .values()
        ):
            if display_group != item_pid["c_attr_display_group"]:
                self.seq_fields_attrs[item_pid["c_attr_display_group"]] = []

            if self.EQ_SEQ_DATA_FIELDS:  # если это выборка с данными для оборудования
                if self.EQ_SEQ_DATA_FIELDS.get(item_pid["c_attr_display_group"]):
                    for item_key, item_value in self.EQ_SEQ_DATA_FIELDS[
                        item_pid["c_attr_display_group"]
                    ].items():
                        if item_key == item_pid["c_name_attribute"]:
                            item_pid["f_value"] = item_value.f_value
                            break

            self.seq_fields_attrs[item_pid["c_attr_display_group"]].append(item_pid)

            display_group = item_pid["c_attr_display_group"]

        display_group = None
        for item_ats in (
            cnfAttribute.objects.exclude(n_attr_display_order=0)
            .filter(n_global_object_type=GlobalObjectID.ATS)
            .order_by("n_attr_display_order")
            .values()
        ):
            if display_group != item_ats["c_attr_display_group"]:
                self.ats_fields_attrs[item_ats["c_attr_display_group"]] = []

            if self.EQ_ATS_DATA_FIELDS:  # если это выборка с данными для оборудования
                if self.EQ_ATS_DATA_FIELDS.get(item_ats["c_attr_display_group"]):
                    for item_key, item_value in self.EQ_ATS_DATA_FIELDS[
                        item_ats["c_attr_display_group"]
                    ].items():
                        if item_key == item_ats["c_name_attribute"]:
                            item_ats["f_value"] = item_value
                            break

            self.ats_fields_attrs[item_ats["c_attr_display_group"]].append(item_ats)

            display_group = item_ats["c_attr_display_group"]

        self.equipment_types = list(cnfEquipmentType.objects.all().values())
        self.list_plc = list(cnfController.objects.all().values())

        # пока хардкод, надо двигаться дальше, сроки...
        self.base_fields["c_name_equipment"].widget.attrs = {"class": "form-control"}
        self.base_fields["c_desc_equipment"].widget.attrs = {"class": "form-control"}
        self.base_fields["n_equipment_index"].widget.attrs = {"class": "form-control"}
        # self.base_fields["n_equipment_index"].widget.attrs.update({"class": "form-control", "disabled": True})
        # self.base_fields['n_equipment_index'].widget.attrs.update({'class': 'form-control', 'disabled': True})
        # self.fields['n_equipment_index'].widget.attrs['disabled'] = 'disabled'

        self.base_fields["n_controller"].widget.attrs = {"class": "form-select selcls"}

        self.base_fields["c_name_section"].widget.attrs = {"class": "form-control"}
        self.base_fields["c_name_position"].widget.attrs = {"class": "form-control"}
        self.base_fields["c_num_position"].widget.attrs = {"class": "form-control"}

        self.base_fields["n_type_id"].widget.attrs = {"class": "form-select selcls"}

        self.base_fields["c_name_equipment"].initial = (
            self.initial["c_name_equipment"] if equipment_id else None
        )
        self.base_fields["c_desc_equipment"].initial = (
            self.initial["c_desc_equipment"] if equipment_id else None
        )
        self.base_fields["n_equipment_index"].initial = (
            self.initial["n_equipment_index"] if equipment_id else id_new
        )
        self.base_fields["n_controller"].initial = (
            self.initial["n_controller"] if equipment_id else plc_id
        )

        self.base_fields["c_name_section"].initial = (
            self.initial["c_name_section"] if equipment_id else None
        )
        self.base_fields["c_name_position"].initial = (
            self.initial["c_name_position"] if equipment_id else None
        )
        self.base_fields["c_num_position"].initial = (
            self.initial["c_num_position"] if equipment_id else None
        )

        self.base_fields["n_type_id"].initial = (
            self.initial["n_type_id"] if equipment_id else None
        )
        # self.base_fields['b_masked'].initial = self.initial['b_masked'] if equipment_id else None
        if self.base_fields.get("b_masked"):
            del self.base_fields["b_masked"]

        value_data_by_order = []
        value_data_by_order_dict = {}
        if equipment_id is not None:
            extra_data = list(
                get_equipments_extra_data(n_equipment=equipment_id).values()
            )

            for (
                attribute
            ) in fileds_attrs:
                for item in extra_data:  # values_list():

                    if attribute["id"] == item["n_attribute_id"]:
                        if attribute["n_attr_display_order"] == 0:  # exlude for visible

                            self.invisible_fields_id.append(
                                (item["id"], attribute["c_name_attribute"])
                            )
                        else:
                            value_data_by_order.append(item["f_value"])
                            self.value_id_by_order[attribute["c_name_attribute"]] = item["id"]
                            value_data_by_order_dict[item["n_attribute_id"]] = item[
                                "f_value"
                            ]
                            break

        group_name = ""

        for item in fileds_attrs:

            init = equipment_id is not None
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
                        if value_data_by_order_dict.get(item["id"]):
                            
                            param_dict["initial"] = int(
                                value_data_by_order_dict.get(item["id"])
                            )  # value_data_by_order[index_iter]
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
                else:
                    if init:
                        param_dict["initial"] = bool(
                            value_data_by_order_dict.get(item["id"])
                        )  # bool(value_data_by_order[index_iter])

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
        model = cnfEquipment
        exclude = ("c_user_edit", "d_last_edit", "created_at")
