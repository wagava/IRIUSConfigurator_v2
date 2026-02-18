from itertools import chain

from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import (BooleanField, ExpressionWrapper, F, FloatField,
                              TextField, Value)
from django.http import HttpResponseRedirect, JsonResponse
from django.http.response import HttpResponse as HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import (CreateView, DeleteView, DetailView, ListView,
                                  TemplateView, UpdateView)
from general.models import cnfAttribute, cnfController
from general.utils import get_int_from_bits
from services.utils import DownloadToPLC, get_count_precision, send_data_to_plc
from variables.models import cnfVariable

from iriusconfig.constants import (AttributeFieldType,
                                   CommandInterfaceConstants,
                                   EquipmentTypeConstants, GlobalObjectID,
                                   PlcCommandConstants, ViewConstants)
from .mixins import EquipmentViewMixin, EquipmentAuthMixin
from .models import (cnfEquipment, cnfEquipmentLinkedEquipment,
                     cnfEquipmentLinkedPIDVariable, cnfEquipmentLinkedVariable,
                     cnfEquipmentLinkedWord, cnfEquipmentPIDVariableRole,
                     cnfEquipmentRole, cnfEquipmentValue,
                     cnfEquipmentVariableRole, cnfSequenceLinkedEquipment,
                     cnfSequenceLinkedVariable, cnfSequenceRole)
from .utils import (get_equipment_data_to_plc, get_equipments_data_custom,
                    get_equipments_data_custom_filter)

User = get_user_model()

DownloadToPLCInstance = (
    DownloadToPLC()
)  # Экземпляр нужен для подсчета числа прогресс-бара на фронте


def equipment_home(request):
    """Функция перехода на домашнюю страницу.
    В текущей реализации - на страницу оборудования.
    """

    # return HttpResponse('Empty')
    return HttpResponseRedirect(
        reverse("equipments:equipment_by_plc", kwargs={"plc_id": 1})
    )
    # return HttpResponseRedirect(reverse("variables:variable_by_plc", kwargs={"plc_id": 1}))


class EquipmentListView(LoginRequiredMixin, ListView):
    """Отображение всего оборудования."""

    paginate_by = ViewConstants.MAX_ITEMS_ON_PAGE
    template_name = "equipments/index.html"
    pk_url_kwarg = "plc_id"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["plc_list"] = cnfController.objects.all().order_by("c_desc_controller").values_list(
            "id", "c_desc_controller"
        )
        context["plc_id"] = int(self.kwargs["plc_id"])
        context["filter"] = self.kwargs.get("filter")
        context["all_count"] = self.kwargs.get("all_count")

        return context

    def get_queryset(self):
        plc_selector = self.request.GET.get("plc_selector")
        filter = self.request.GET.get("filter")

        if filter is not None and filter != "":
            self.kwargs["filter"] = filter
            self.kwargs["plc_id"] = int(plc_selector)
            queryset = get_equipments_data_custom_filter(
                plc_id=plc_selector, filter_value=self.request.GET["filter"]
            )
            self.kwargs["all_count"] = queryset[1]
            return queryset[0]

        if plc_selector is not None:
            if plc_selector != "":
                self.kwargs["plc_id"] = int(plc_selector)
                queryset = get_equipments_data_custom(n_controller=plc_selector)
        else:
            queryset = get_equipments_data_custom(n_controller=self.kwargs["plc_id"])

        self.kwargs["all_count"] = queryset[1]
        return queryset[0]


class EquipmentCreateView(LoginRequiredMixin, EquipmentViewMixin, EquipmentAuthMixin, CreateView):
    """Создание оборудования."""

    pk_url_kwarg = "plc_id"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["plc_id"] = int(self.kwargs["plc_id"])
        return kwargs

    def form_valid(self, form):

        setattr(form.instance, "c_user_edit", User.objects.get(username=self.request.user.username))
        setattr(form.instance, "d_last_edit", timezone.now())

        """
        в form.data хранятся в ключах по имени (name) select выбранные
        значения option по value
        """
        linked_variable_records = None
        linked_equipment_records = None
        linked_variable_pid_records = None
        linked_sequences_records = None

        cfg_equipment_type = None

        for item_type in form.equipment_types:
            if int(form.data["n_type_id"]) == item_type["id"]:
                cfg_equipment_type = item_type["n_type_value"]
                break

        # Вынимаем поля с формы для сохренения в БД, нужно добавить остальные для сохранения

        if (
            cfg_equipment_type == EquipmentTypeConstants.TYPE_PID_AI
            or cfg_equipment_type == EquipmentTypeConstants.TYPE_PID_DC
            or cfg_equipment_type == EquipmentTypeConstants.TYPE_P_DC
        ):

            linked_variable_pid_records = self.get_roles(
                form,
                cnfEquipmentLinkedPIDVariable,
                cnfEquipmentPIDVariableRole,
                cnfVariable,
            )

        if cfg_equipment_type == EquipmentTypeConstants.TYPE_EQ14:
            linked_sequences_records = self.get_sequences_roles(
                form,
                cnfSequenceLinkedVariable,
                cnfSequenceLinkedEquipment,
                cnfSequenceRole,
                cnfVariable,
                cnfEquipment,
            )

        linked_variable_records = self.get_roles(
            form, cnfEquipmentLinkedVariable, cnfEquipmentVariableRole, cnfVariable
        )

        linked_equipment_records = self.get_roles(
            form, cnfEquipmentLinkedEquipment, cnfEquipmentRole, cnfEquipment
        )

        linked_equipment_word_records = []
        if (
            cfg_equipment_type == EquipmentTypeConstants.TYPE_EQ03
            or cfg_equipment_type == EquipmentTypeConstants.TYPE_EQ04
        ):
            item_var_sw = form.data.get("sw_variable")
            item_var_cw = form.data.get("cw_variable")
            if item_var_sw is not None:
                for item in range(0, 16):
                    item_sw_bit_role_value = form.data.get(f"sw_role_bit{item}")
                    item_cw_bit_role_value = form.data.get(f"cw_role_bit{item}")
                    if (
                        item_sw_bit_role_value
                        and item_sw_bit_role_value != "select_item"
                    ):
                        linked_equipment_word_records.append(
                            cnfEquipmentLinkedWord(
                                n_bit=item,
                                n_word_type=EquipmentTypeConstants.WORD_TYPE_STATUSWORD,
                                n_equipment=form.instance,
                                n_role=cnfEquipmentVariableRole.objects.get(
                                    id=item_sw_bit_role_value
                                ),
                                n_variable=cnfVariable.objects.get(id=item_var_sw),
                            )
                        )

                    if (
                        item_cw_bit_role_value
                        and item_cw_bit_role_value != "select_item"
                    ):
                        linked_equipment_word_records.append(
                            cnfEquipmentLinkedWord(
                                n_bit=item,
                                n_word_type=EquipmentTypeConstants.WORD_TYPE_CONTROLWORD,
                                n_equipment=form.instance,
                                n_role=cnfEquipmentVariableRole.objects.get(
                                    id=item_cw_bit_role_value
                                ),
                                n_variable=cnfVariable.objects.get(id=item_var_cw),
                            )
                        )

        # получаем доп.данные с формы и отправляем в соответствующие таблицы cnfVariableValue
        # в cleaned_data хранятся только те данные, что сформированы через form

        prep_data = []
        cw_word = []
        for item in form.cleaned_data:
            if item.__contains__("attr_"):
                prep_data.append(
                    (
                        int(form.cleaned_data[item]),
                        cnfAttribute.objects.filter(
                            n_global_object_type=GlobalObjectID.EQUIPMENT
                        ).get(c_name_attribute=item.replace("attr_", "")),
                    )
                )
            elif item.__contains__("attrf_"):
                prep_data.append(
                    (
                        float(form.cleaned_data[item]),
                        cnfAttribute.objects.filter(
                            n_global_object_type=GlobalObjectID.EQUIPMENT
                        ).get(c_name_attribute=item.replace("attrf_", "")),
                    )
                )
            elif item.__contains__("attrb_"):
                bit = int(item.replace("attrb_", "")[0:2])
                cw_word.append((bit, int(form.cleaned_data[item])))
                name_attribute = item.replace("attrb_", "")[2:]
                prep_data.append(
                    (
                        int(form.cleaned_data[item]),
                        cnfAttribute.objects.filter(
                            n_global_object_type=GlobalObjectID.EQUIPMENT
                        ).get(c_name_attribute=name_attribute),
                    )
                )

        type_cw_word = []
        global_object_type = None
        # только параметры ПИД-регуляторов
        if cfg_equipment_type in [
            EquipmentTypeConstants.TYPE_PID_AI,
            EquipmentTypeConstants.TYPE_PID_DC,
            EquipmentTypeConstants.TYPE_P_DC,
            EquipmentTypeConstants.TYPE_ATS,
            EquipmentTypeConstants.TYPE_EQ14,
        ]:
            str_to_replace = None
            for item_key, item_value in form.data.items():
                if item_key.__contains__("_pid"):
                    global_object_type = GlobalObjectID.PID
                elif item_key.__contains__("_ats"):
                    global_object_type = GlobalObjectID.ATS
                elif item_key.__contains__("_seq"):
                    global_object_type = GlobalObjectID.SEQUENCE

                if item_key.__contains__("attr_pid"):
                    str_to_replace = "attr_pid"
                elif item_key.__contains__("attr_ats"):
                    str_to_replace = "attr_ats"
                elif item_key.__contains__("attr_seq"):
                    str_to_replace = "attr_seq"
                elif item_key.__contains__("attrf_pid"):
                    str_to_replace = "attrf_pid"
                elif item_key.__contains__("attrf_ats"):
                    str_to_replace = "attrf_ats"
                elif item_key.__contains__("attrf_seq"):
                    str_to_replace = "attrf_seq"
                elif item_key.__contains__("attrb_pid_"):
                    str_to_replace = "attrb_pid_"
                elif item_key.__contains__("attrb_ats_"):
                    str_to_replace = "attrb_ats_"
                elif item_key.__contains__("attrb_seq_"):
                    str_to_replace = "attrb_seq_"
                if (
                    (
                        item_key.__contains__("_pid")
                        and (
                            cfg_equipment_type
                            in [
                                EquipmentTypeConstants.TYPE_PID_AI,
                                EquipmentTypeConstants.TYPE_PID_DC,
                                EquipmentTypeConstants.TYPE_P_DC,
                            ]
                        )
                    )
                    or
                    (
                        item_key.__contains__("_seq")
                        and (cfg_equipment_type == EquipmentTypeConstants.TYPE_EQ14)
                    )
                    or (
                        item_key.__contains__("_ats")
                        and (cfg_equipment_type == EquipmentTypeConstants.TYPE_ATS)
                    )
                ):
                    if item_key.__contains__("attr_"):

                        prep_data.append(
                            (
                                int(item_value),
                                cnfAttribute.objects.filter(
                                    n_global_object_type=global_object_type
                                ).get(
                                    c_name_attribute=item_key.replace(
                                        str_to_replace, ""
                                    )
                                ),
                            )
                        )
                    elif item_key.__contains__("attrf_"):

                        prep_data.append(
                            (
                                float(item_value),
                                cnfAttribute.objects.filter(
                                    n_global_object_type=global_object_type
                                ).get(
                                    c_name_attribute=item_key.replace(
                                        str_to_replace, ""
                                    )
                                ),
                            )
                        )
                    elif item_key.__contains__("attrb_"):

                        bit = int(item_key.replace(str_to_replace, "")[0:2])
                        converted_value = 1 if item_value == "on" else 0
                        type_cw_word.append((bit, converted_value))
                        name_attribute = item_key.replace(str_to_replace, "")[2:]

                        prep_data.append(
                            (
                                converted_value,
                                cnfAttribute.objects.filter(
                                    n_global_object_type=global_object_type
                                ).get(c_name_attribute=name_attribute),
                            )
                        )
        # только параметры SEQUENCE
        # if int(form.data['n_type_id']) == EquipmentTypeConstants.TYPE_EQ14:
        #         for item_key, item_value in form.data.items():
        #             if item_key.__contains__("attr_seq"):
        #                 prep_data.append(
        #                     (
        #                         int(item_value),
        #                         cnfAttribute.objects.filter(n_global_object_type=GlobalObjectID.SEQUENCE).get(
        #                             c_name_attribute=item_key.replace("attr_seq", "")
        #                         ),
        #                     )
        #                 )
        #             elif item_key.__contains__("attrf_seq"):
        #                 prep_data.append(
        #                     (
        #                         float(item_value),
        #                         cnfAttribute.objects.filter(n_global_object_type=GlobalObjectID.SEQUENCE).get(
        #                             c_name_attribute=item_key.replace("attrf_seq", "")
        #                         ),
        #                     )
        #                 )
        #             elif item_key.__contains__("attrb_seq_"):
        #                 bit = int(item_key.replace("attrb_seq_", "")[0:2])
        #                 converted_value = 1 if item_value == 'on' else 0
        #                 type_cw_word.append((bit,converted_value))
        #                 name_attribute  = item_key.replace("attrb_seq_", "")[2:]

        #                 prep_data.append(
        #                     (
        #                         converted_value,
        #                         cnfAttribute.objects.filter(n_global_object_type=GlobalObjectID.SEQUENCE).get(
        #                             c_name_attribute=name_attribute
        #                         ),
        #                     )
        #                 )
        # хард-код, переделать на более гибкую конструкцию
        if cw_word:
            prep_data.append(
                (
                    get_int_from_bits(cw_word),
                    cnfAttribute.objects.filter(
                        n_global_object_type=GlobalObjectID.EQUIPMENT
                    ).get(c_name_attribute="CW"),
                )
            )
        if type_cw_word:
            prep_data.append(
                (
                    get_int_from_bits(type_cw_word),
                    cnfAttribute.objects.filter(
                        n_global_object_type=global_object_type
                    ).get(c_name_attribute="CW"),
                )
            )

        records = [
            cnfEquipmentValue(
                n_equipment=form.instance,
                n_attribute=n_attribute,
                f_value=f_value,
                c_note="---",
            )
            for f_value, n_attribute in prep_data
        ]

        if form.is_valid:
            form.save()  # Сначала сохраняем данные модуля из формы, чтобы FK таблицы значений было на что ссылаться при сохранении

            cnfEquipmentValue.objects.bulk_create(records)
            if linked_variable_records and linked_variable_records.get("creating"):
                if len(linked_variable_records["creating"]) > 0:
                    cnfEquipmentLinkedVariable.objects.bulk_create(
                        linked_variable_records["creating"]
                    )
            if linked_variable_pid_records and linked_variable_pid_records.get(
                "creating"
            ):
                if len(linked_variable_pid_records["creating"]) > 0:
                    cnfEquipmentLinkedPIDVariable.objects.bulk_create(
                        linked_variable_pid_records["creating"]
                    )

            # cnfEquipmentLinkedPIDVariable.objects.bulk_create(linked_variable_pid_records)
            if linked_equipment_records and linked_equipment_records.get("creating"):
                if len(linked_equipment_records["creating"]) > 0:
                    cnfEquipmentLinkedEquipment.objects.bulk_create(
                        linked_equipment_records["creating"]
                    )
            # cnfEquipmentLinkedEquipment.objects.bulk_create(linked_equipment_records)
            if linked_sequences_records and linked_sequences_records["variable_create"]:
                cnfSequenceLinkedVariable.objects.bulk_create(
                    linked_sequences_records["variable_create"]
                )
            if (
                linked_sequences_records
                and linked_sequences_records["equipment_create"]
            ):
                cnfSequenceLinkedEquipment.objects.bulk_create(
                    linked_sequences_records["equipment_create"]
                )
            if len(linked_equipment_word_records) > 0:
                cnfEquipmentLinkedWord.objects.bulk_create(
                    linked_equipment_word_records
                )

        if self.request.POST.get("download_to_plc") == "on":
            self.RETURN_BLOCK_FROM_PLC = download_equipments(
                plc_id=form.instance.n_controller.pk,
                min=form.instance.pk,
                max=form.instance.pk,
                ajax=False,
            )
            if not self.RETURN_BLOCK_FROM_PLC.get("return_block"):
                self.RETURN_BLOCK_FROM_PLC["return_block"] = [
                    {
                        "error_num": "Оборудование успешно загружено в ПЛК",
                        "index_num": "None",
                        "param_num": "None",
                    }
                ]
        return super().form_valid(form)

    def form_invalid(self, form):
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse(
            "equipments:equipment_create", kwargs={"plc_id": self.kwargs["plc_id"]}
        )


class EquipmentUpdateView(LoginRequiredMixin, EquipmentViewMixin, EquipmentAuthMixin, UpdateView):
    """Редактирование информации по выбранному оборудованию."""

    RETURN_BLOCK_FROM_PLC = []
    pk_url_kwarg = "eq_id"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["id"] = self.kwargs["eq_id"]
        kwargs["plc_id"] = self.kwargs["plc_id"]
        kwargs["n_type_value"] = (
            cnfEquipment.objects.get(id=self.kwargs["eq_id"]).n_type_id
        ).n_type_value

        return kwargs

    def get(self, request, *args, **kwargs):

        min = request.GET.get("min")
        max = request.GET.get("max")
        action = request.GET.get("action")
        plc_id = self.kwargs["plc_id"]
        aaa = self.args
        kkk = self.kwargs
        self.kwargs["RETURN_BLOCK_FROM_PLC"] = self.request.session.get(
            "RETURN_BLOCK_FROM_PLC"
        )
        if self.request.session.get("RETURN_BLOCK_FROM_PLC"):
            self.request.session["RETURN_BLOCK_FROM_PLC"] = []

        if not None in [min, max, action]:
            if action == CommandInterfaceConstants.ACTION_DOWNLOAD_TO_PLC:
                result_errors = download_equipments(
                    request=request, plc_id=plc_id, min=min, max=max, ajax=False
                )
                self.kwargs["download_errors"] = result_errors
        # self.object
        # equipment_index= self.kwargs['eq_id'] # при переходе назад используется не id, а индекс модуля module_index, т.к. id может быть любой
        # plc_id = self.kwargs['plc_id'] # request.GET.get('plc')
        # movement = request.GET.get('movement')
        # if None not in (plc_id, movement):
        #     if movement=='prev':
        #         query_object = get_equipments_data_custom(n_equipment_index__lt=equipment_index,n_controller=plc_id).exclude(n_equipment_index__lt=equipment_index).order_by('-n_equipment_index').first()
        #     else:
        #         query_object = get_equipments_data_custom(n_equipment_index__gt=equipment_index,n_controller=plc_id).exclude(n_equipment_index__lt=equipment_index).order_by('n_equipment_index').first()
        #     if query_object:
        #         self.kwargs['eq_id'] = query_object.id

        return super(EquipmentUpdateView, self).get(request, *args, **kwargs)

    def get_success_url(self):
        if self.RETURN_BLOCK_FROM_PLC:
            self.request.session["RETURN_BLOCK_FROM_PLC"] = self.RETURN_BLOCK_FROM_PLC[
                "return_block"
            ]
        return reverse(
            "equipments:equipment_edit",
            args=[self.kwargs["plc_id"], self.kwargs["eq_id"]],
        )

    def form_valid(self, form):

        if self.request.session.get("RETURN_BLOCK_FROM_PLC"):
            self.request.session["RETURN_BLOCK_FROM_PLC"] = []

        form_equipment_index_bottom = self.request.POST.get('equipment_index')
        form_equipment_index_below = self.request.POST.get('equipment_index_below')
        form_equipment_index = None
        
        if not (form_equipment_index_bottom == str(form.cleaned_data.get('n_equipment_index'))):
            form_equipment_index = form_equipment_index_bottom
        if not (form_equipment_index_below == str(form.cleaned_data.get('n_equipment_index'))):
            form_equipment_index = form_equipment_index_below
            
        if form_equipment_index:
            if form_equipment_index.isdigit():
                equipments = cnfEquipment.objects.filter(
                            n_equipment_index=form_equipment_index,
                            n_controller=self.kwargs["plc_id"]
                        )
                equipment = equipments.first()
                return redirect(
            "equipments:equipment_edit",
            plc_id=self.kwargs["plc_id"],
            eq_id=equipment.id if equipment else self.kwargs["eq_id"],
        )

        setattr(form.instance, "c_user_edit", User.objects.get(username=self.request.user.username))
        setattr(form.instance, "d_last_edit", timezone.now())

        linked_variable_records = None
        linked_equipment_records = None
        linked_variable_pid_records = None
        linked_sequences_records = None

        cfg_equipment_type = None  # int(form.data['n_type_id'])

        for item_type in form.equipment_types:
            if int(form.data["n_type_id"]) == item_type["id"]:
                cfg_equipment_type = item_type["n_type_value"]
                break

        if cfg_equipment_type in [
            EquipmentTypeConstants.TYPE_PID_AI,
            EquipmentTypeConstants.TYPE_PID_DC,
            EquipmentTypeConstants.TYPE_P_DC,
        ]:

            linked_variable_pid_records = self.get_roles(
                form,
                cnfEquipmentLinkedPIDVariable,
                cnfEquipmentPIDVariableRole,
                cnfVariable,
                form.VAR_PID_DATA_ROLES,
            )

        # if cfg_equipment_type != EquipmentTypeConstants.TYPE_EQ14:
        linked_variable_records = self.get_roles(
            form,
            cnfEquipmentLinkedVariable,
            cnfEquipmentVariableRole,
            cnfVariable,
            form.VAR_DATA_ROLES,
        )

        # if cfg_equipment_type != EquipmentTypeConstants.TYPE_EQ14:
        linked_equipment_records = self.get_roles(
            form,
            cnfEquipmentLinkedEquipment,
            cnfEquipmentRole,
            cnfEquipment,
            form.EQ_DATA_ROLES,
        )

        if cfg_equipment_type == EquipmentTypeConstants.TYPE_EQ14:

            linked_sequences_records = self.get_sequences_roles(
                form,
                cnfSequenceLinkedVariable,
                cnfSequenceLinkedEquipment,
                cnfSequenceRole,
                cnfVariable,
                cnfEquipment,
                form.EQ_SEQ_DATA_STEPS,
            )

        # только типы с ЧРП
        linked_equipment_word_records = []
        linked_equipment_word_records_create = (
            []
        )  # для новых записей, добавляемых при редактировании

        if (
            cfg_equipment_type == EquipmentTypeConstants.TYPE_EQ03
            or cfg_equipment_type == EquipmentTypeConstants.TYPE_EQ04
        ):
            item_var_sw = form.data.get("sw_variable")
            item_var_cw = form.data.get("cw_variable")

            if item_var_sw is not None:
                for item in range(0, 16):
                    item_sw_bit_role_value = form.data.get(f"sw_role_bit{item}")
                    item_cw_bit_role_value = form.data.get(f"cw_role_bit{item}")

                    if (
                        item_sw_bit_role_value
                        and item_sw_bit_role_value != "select_item"
                    ):
                        sw_idx = None
                        for item_row in form.EQ_DATA_ROLES_BIT_SW_WORDS:
                            if item == item_row["n_bit"]:
                                sw_idx = item_row["id"]
                                form.EQ_DATA_ROLES_BIT_SW_WORDS.remove(item_row)
                                break
                        if sw_idx:

                            linked_equipment_word_records.append(
                                cnfEquipmentLinkedWord(
                                    id=sw_idx,
                                    n_bit=item,
                                    n_word_type=EquipmentTypeConstants.WORD_TYPE_STATUSWORD,
                                    n_equipment=form.instance,
                                    n_role=cnfEquipmentVariableRole.objects.get(
                                        id=item_sw_bit_role_value
                                    ),
                                    # n_equipment_link=cnfEquipment.objects.get(id=item_eq_value),
                                    n_variable=cnfVariable.objects.get(id=item_var_sw),
                                )
                            )
                        else:
                            linked_equipment_word_records_create.append(
                                cnfEquipmentLinkedWord(
                                    n_bit=item,
                                    n_word_type=EquipmentTypeConstants.WORD_TYPE_STATUSWORD,
                                    n_equipment=form.instance,
                                    n_role=cnfEquipmentVariableRole.objects.get(
                                        id=item_sw_bit_role_value
                                    ),
                                    # n_equipment_link=cnfEquipment.objects.get(id=item_eq_value),
                                    n_variable=cnfVariable.objects.get(id=item_var_sw),
                                )
                            )

                    if (
                        item_cw_bit_role_value
                        and item_cw_bit_role_value != "select_item"
                    ):
                        cw_idx = None
                        for item_row in form.EQ_DATA_ROLES_BIT_CW_WORDS:
                            if item_row["n_bit"] == item:
                                cw_idx = item_row["id"]
                                form.EQ_DATA_ROLES_BIT_CW_WORDS.remove(item_row)
                                break
                        if cw_idx:
                            linked_equipment_word_records.append(
                                cnfEquipmentLinkedWord(
                                    id=cw_idx,
                                    n_bit=item,
                                    n_word_type=EquipmentTypeConstants.WORD_TYPE_CONTROLWORD,
                                    n_equipment=form.instance,
                                    n_role=cnfEquipmentVariableRole.objects.get(
                                        id=item_cw_bit_role_value
                                    ),
                                    # n_equipment_link=cnfEquipment.objects.get(id=item_eq_value),
                                    n_variable=cnfVariable.objects.get(id=item_var_cw),
                                )
                            )
                        else:
                            linked_equipment_word_records_create.append(
                                cnfEquipmentLinkedWord(
                                    n_bit=item,
                                    n_word_type=EquipmentTypeConstants.WORD_TYPE_CONTROLWORD,
                                    n_equipment=form.instance,
                                    n_role=cnfEquipmentVariableRole.objects.get(
                                        id=item_cw_bit_role_value
                                    ),
                                    # n_equipment_link=cnfEquipment.objects.get(id=item_eq_value),
                                    n_variable=cnfVariable.objects.get(id=item_var_cw),
                                )
                            )

        # получаем данные с формы и отправляем в соответствующие таблицы cnfVariableValue
        index = 0
        prep_data = []
        prep_data_for_create = []
        cw_word = []
        for item in form.cleaned_data:
            if item.__contains__("attr_"):
                attr_name = item.replace("attr_", "")
                # if len(form.value_id_by_order) > index:
                if form.value_id_by_order.get(attr_name):
                    prep_data.append(
                        (
                            # form.value_id_by_order[index],
                            form.value_id_by_order[attr_name],                            
                            int(form.cleaned_data[item]),
                            cnfAttribute.objects.filter(
                                n_global_object_type=GlobalObjectID.EQUIPMENT
                            ).get(c_name_attribute=attr_name),
                        )
                    )
                    index += 1
                else:
                    prep_data_for_create.append(
                        (
                            int(form.cleaned_data[item]),
                            cnfAttribute.objects.filter(
                                n_global_object_type=GlobalObjectID.EQUIPMENT
                            ).get(c_name_attribute=attr_name),
                        )
                    )

            elif item.__contains__("attrf_"):
                attr_name = item.replace("attrf_", "")
                if form.value_id_by_order.get(attr_name):
                    prep_data.append(
                        (
                            form.value_id_by_order[attr_name],
                            float(form.cleaned_data[item]),
                            cnfAttribute.objects.filter(
                                n_global_object_type=GlobalObjectID.EQUIPMENT
                            ).get(c_name_attribute=attr_name),
                        )
                    )
                    index += 1
                else:
                    prep_data_for_create.append(
                        (
                            float(form.cleaned_data[item]),
                            cnfAttribute.objects.filter(
                                n_global_object_type=GlobalObjectID.EQUIPMENT
                            ).get(c_name_attribute=attr_name),
                        )
                    )

            elif item.__contains__("attrb_"):
                # if len(form.value_id_by_order) > index:
                attr_name = item.replace("attrb_", "")[2:]
                if form.value_id_by_order.get(attr_name):
                    bit = int(item.replace("attrb_", "")[0:2])
                    cw_word.append((bit, int(form.cleaned_data[item])))
                    # name_attribute = item.replace("attrb_", "")[2:]
                    prep_data.append(
                        (
                            form.value_id_by_order[attr_name],
                            int(form.cleaned_data[item]),
                            cnfAttribute.objects.filter(
                                n_global_object_type=GlobalObjectID.EQUIPMENT
                            ).get(c_name_attribute=attr_name),
                        )
                    )
                    index += 1
                else:
                    bit = int(item.replace("attrb_", "")[0:2])
                    cw_word.append((bit, int(form.cleaned_data[item])))
                    # name_attribute = item.replace("attrb_", "")[2:]
                    prep_data_for_create.append(
                        (
                            int(form.cleaned_data[item]),
                            cnfAttribute.objects.filter(
                                n_global_object_type=GlobalObjectID.EQUIPMENT
                            ).get(c_name_attribute=attr_name),
                        )
                    )
        index = cnfEquipmentValue.objects.latest("id").id + 1
        type_cw_word = []
        data_field_ids = None  # Словарь, хранящий id для целевого параметра
        global_object_type = None  # Тип объекта
        # только параметры ПИД-регуляторов
        if cfg_equipment_type in [
            EquipmentTypeConstants.TYPE_PID_AI,
            EquipmentTypeConstants.TYPE_PID_DC,
            EquipmentTypeConstants.TYPE_P_DC,
            EquipmentTypeConstants.TYPE_ATS,
            EquipmentTypeConstants.TYPE_EQ14,
        ]:

            str_to_replace = (
                None  # Префикс для замены и получения данных из таблицы атрибутов
            )

            for item_key, item_value in form.data.items():
                if item_key.__contains__("_pid"):
                    global_object_type = GlobalObjectID.PID
                    data_field_ids = form.EQ_PID_DATA_FIELDS_IDS
                elif item_key.__contains__("_ats"):
                    global_object_type = GlobalObjectID.ATS
                    data_field_ids = form.EQ_ATS_DATA_FIELDS_IDS
                elif item_key.__contains__("_seq"):
                    global_object_type = GlobalObjectID.SEQUENCE
                    data_field_ids = form.EQ_SEQ_DATA_FIELDS_IDS

                if item_key.__contains__("attr_pid"):
                    str_to_replace = "attr_pid"
                elif item_key.__contains__("attr_ats"):
                    str_to_replace = "attr_ats"
                elif item_key.__contains__("attr_seq"):
                    str_to_replace = "attr_seq"
                elif item_key.__contains__("attrf_pid"):
                    str_to_replace = "attrf_pid"
                elif item_key.__contains__("attrf_ats"):
                    str_to_replace = "attrf_ats"
                elif item_key.__contains__("attrf_seq"):
                    str_to_replace = "attrf_seq"
                elif item_key.__contains__("attrb_pid_"):
                    str_to_replace = "attrb_pid_"
                elif item_key.__contains__("attrb_ats_"):
                    str_to_replace = "attrb_ats_"
                elif item_key.__contains__("attrb_seq_"):
                    str_to_replace = "attrb_seq_"

                if (
                    (
                        item_key.__contains__("_pid")
                        and (
                            cfg_equipment_type
                            in [
                                EquipmentTypeConstants.TYPE_PID_AI,
                                EquipmentTypeConstants.TYPE_PID_DC,
                                EquipmentTypeConstants.TYPE_P_DC,
                            ]
                        )
                    )
                    or (
                        item_key.__contains__("_seq")
                        and (cfg_equipment_type == EquipmentTypeConstants.TYPE_EQ14)
                    )
                    or (
                        item_key.__contains__("_ats")
                        and (cfg_equipment_type == EquipmentTypeConstants.TYPE_ATS)
                    )
                ):

                    if item_key.__contains__("attr_"):
                        # local_index = form.EQ_PID_DATA_FIELDS_IDS.get(item_key.replace("attr_pid", ""))
                        local_index = data_field_ids.get(
                            item_key.replace(str_to_replace, "")
                        )
                        if not local_index:
                            # local_index = index
                            prep_data_for_create.append(
                                (
                                    int(item_value),
                                    cnfAttribute.objects.filter(
                                        n_global_object_type=global_object_type
                                    ).get(
                                        c_name_attribute=item_key.replace(
                                            str_to_replace, ""
                                        )
                                    ),
                                )
                            )
                        else:
                            del data_field_ids[item_key.replace(str_to_replace, "")]
                            prep_data.append(
                                (
                                    # Здесь нужно указать айдишник, подумать как его определить или забрать
                                    local_index,
                                    # form.value_id_by_order[index],
                                    int(item_value),
                                    cnfAttribute.objects.filter(
                                        n_global_object_type=global_object_type
                                    ).get(
                                        c_name_attribute=item_key.replace(
                                            str_to_replace, ""
                                        )
                                    ),
                                )
                            )
                        index += 1
                    elif item_key.__contains__("attrf_"):

                        local_index = data_field_ids.get(
                            item_key.replace(str_to_replace, "")
                        )
                        if not local_index:
                            # local_index = index
                            prep_data_for_create.append(
                                (
                                    float(item_value),
                                    cnfAttribute.objects.filter(
                                        n_global_object_type=global_object_type
                                    ).get(
                                        c_name_attribute=item_key.replace(
                                            str_to_replace, ""
                                        )
                                    ),
                                )
                            )
                        else:
                            del data_field_ids[item_key.replace(str_to_replace, "")]
                            prep_data.append(
                                (
                                    # Здесь нужно указать айдишник, подумать как его определить или забрать
                                    local_index,
                                    # form.value_id_by_order[index],
                                    float(item_value),
                                    cnfAttribute.objects.filter(
                                        n_global_object_type=global_object_type
                                    ).get(
                                        c_name_attribute=item_key.replace(
                                            str_to_replace, ""
                                        )
                                    ),
                                )
                            )
                        # index += 1
                    elif item_key.__contains__("attrb_"):
                        bit = int(item_key.replace(str_to_replace, "")[0:2])
                        converted_value = 1 if item_value == "on" else 0
                        type_cw_word.append((bit, converted_value))
                        name_attribute = item_key.replace(str_to_replace, "")[2:]
                        local_index = data_field_ids.get(name_attribute)

                        if not local_index:
                            # local_index = index
                            prep_data_for_create.append(
                                (
                                    converted_value,
                                    cnfAttribute.objects.filter(
                                        n_global_object_type=global_object_type
                                    ).get(c_name_attribute=name_attribute),
                                )
                            )
                        else:
                            del data_field_ids[name_attribute]
                            prep_data.append(
                                (
                                    local_index,
                                    converted_value,
                                    cnfAttribute.objects.filter(
                                        n_global_object_type=global_object_type
                                    ).get(c_name_attribute=name_attribute),
                                )
                            )

        # хард-код, переделать на более гибкую конструкцию
        if cw_word:
            if len(form.invisible_fields_id) > 0:
                prep_data.append(
                    (
                        form.invisible_fields_id[0][0],
                        get_int_from_bits(cw_word),
                        cnfAttribute.objects.filter(
                            n_global_object_type=GlobalObjectID.EQUIPMENT
                        ).get(c_name_attribute="CW"),
                    )
                )
            else:
                prep_data_for_create.append(
                    (
                        get_int_from_bits(cw_word),
                        cnfAttribute.objects.filter(
                            n_global_object_type=GlobalObjectID.EQUIPMENT
                        ).get(c_name_attribute="CW"),
                    )
                )
        if type_cw_word:
            if len(form.invisible_fields_eq_types) > 0 and form.invisible_fields_eq_types.get("CW"):
                prep_data.append(
                    (
                        form.invisible_fields_eq_types["CW"],
                        get_int_from_bits(type_cw_word),
                        cnfAttribute.objects.filter(
                            n_global_object_type=global_object_type
                        ).get(c_name_attribute="CW"),
                    )
                )
            else:
                prep_data_for_create.append(
                    (
                        get_int_from_bits(type_cw_word),
                        cnfAttribute.objects.filter(
                            n_global_object_type=global_object_type
                        ).get(c_name_attribute="CW"),
                    )
                )
        # Здесь подумать!!!!!!!!!!!!!!
        # if pid_cw_word:
        # prep_data.append((form.invisible_fields_id[0][0],
        #                 get_int_from_bits(cw_word),
        #                 cnfAttribute.objects.filter(n_global_object_type=GlobalObjectID.EQUIPMENT).get(
        #                 c_name_attribute='CW'),))

        records = [
            cnfEquipmentValue(
                idx,
                n_equipment=form.instance,
                n_attribute=n_attribute,
                f_value=f_value,
                c_note="---",
            )
            for idx, f_value, n_attribute in prep_data
        ]
        records_for_create = [
            cnfEquipmentValue(
                n_equipment=form.instance,
                n_attribute=n_attribute,
                f_value=f_value,
                c_note="---",
            )
            for f_value, n_attribute in prep_data_for_create
        ]
        # raise
        if form.is_valid:
            form.save()  # Сначала сохраняем данные модуля из формы, чтобы FK таблицы значений было на что ссылаться при сохранении
            cnfEquipmentValue.objects.bulk_update(records, ["f_value"])
            if records_for_create:
                cnfEquipmentValue.objects.bulk_create(records_for_create)

            data_field_ids = (
                form.EQ_PID_DATA_FIELDS_IDS
                | form.EQ_ATS_DATA_FIELDS_IDS
                | form.EQ_SEQ_DATA_FIELDS_IDS
            )
            # for value in form.EQ_ATS_DATA_FIELDS_IDS.values():
            if data_field_ids:
                for value in data_field_ids.values():
                    cnfEquipmentValue.objects.filter(id=value).delete()

            if form.VAR_DATA_ROLES and len(form.VAR_DATA_ROLES) > 0:
                for item in form.VAR_DATA_ROLES:
                    cnfEquipmentLinkedVariable.objects.filter(id=item["id"]).delete()

            if linked_variable_records and linked_variable_records.get("updating"):
                if len(linked_variable_records["updating"]) > 0:
                    cnfEquipmentLinkedVariable.objects.bulk_update(
                        linked_variable_records["updating"],
                        ["n_timer", "n_equipment", "n_role", "n_variable", "b_masked",  "n_index",],
                    )
            if linked_variable_records and linked_variable_records.get("creating"):
                if len(linked_variable_records["creating"]) > 0:
                    cnfEquipmentLinkedVariable.objects.bulk_create(
                        linked_variable_records["creating"]
                    )

            # if linked_variable_records_create and len(linked_variable_records_create) > 0:
            #     cnfEquipmentLinkedVariable.objects.bulk_create(linked_variable_records_create)

            if linked_variable_pid_records and linked_variable_pid_records.get(
                "updating"
            ):
                if len(linked_variable_pid_records["updating"]) > 0:
                    cnfEquipmentLinkedPIDVariable.objects.bulk_update(
                        linked_variable_pid_records["updating"],
                        [
                            "n_timer",
                            "n_equipment",
                            "n_role",
                            "n_variable_link",
                            "b_masked",
                            "n_index",
                        ],
                    )
            if linked_variable_pid_records and linked_variable_pid_records.get(
                "creating"
            ):
                if len(linked_variable_pid_records["creating"]) > 0:
                    cnfEquipmentLinkedPIDVariable.objects.bulk_create(
                        linked_variable_pid_records["creating"]
                    )

            if form.VAR_PID_DATA_ROLES and len(form.VAR_PID_DATA_ROLES) > 0:
                for item in form.VAR_PID_DATA_ROLES:
                    cnfEquipmentLinkedPIDVariable.objects.filter(id=item["id"]).delete()


            if linked_equipment_records and linked_equipment_records.get("updating"):
                if len(linked_equipment_records["updating"]) > 0:
                    cnfEquipmentLinkedEquipment.objects.bulk_update(
                        linked_equipment_records["updating"],
                        [
                            "n_timer",
                            "n_equipment",
                            "n_role",
                            "n_equipment_link",
                            "b_masked",
                            "n_index",
                        ],
                    )
            if linked_equipment_records and linked_equipment_records.get("creating"):
                if len(linked_equipment_records["creating"]) > 0:
                    cnfEquipmentLinkedEquipment.objects.bulk_create(
                        linked_equipment_records["creating"]
                    )

            if form.EQ_DATA_ROLES and len(form.EQ_DATA_ROLES) > 0:
                for item in form.EQ_DATA_ROLES:
                    cnfEquipmentLinkedEquipment.objects.filter(id=item["id"]).delete()

            if linked_equipment_word_records and len(linked_equipment_word_records) > 0:
                cnfEquipmentLinkedWord.objects.bulk_update(
                    linked_equipment_word_records,
                    ["n_bit", "n_word_type", "n_equipment", "n_role", "n_variable"],
                )
            if (
                linked_equipment_word_records_create
                and len(linked_equipment_word_records_create) > 0
            ):
                cnfEquipmentLinkedWord.objects.bulk_create(
                    linked_equipment_word_records_create
                )

            if (
                form.EQ_DATA_ROLES_BIT_SW_WORDS
                and len(form.EQ_DATA_ROLES_BIT_SW_WORDS) > 0
            ):
                for item in form.EQ_DATA_ROLES_BIT_SW_WORDS:
                    cnfEquipmentLinkedWord.objects.filter(id=item["id"]).delete()

            if (
                form.EQ_DATA_ROLES_BIT_CW_WORDS
                and len(form.EQ_DATA_ROLES_BIT_CW_WORDS) > 0
            ):
                for item in form.EQ_DATA_ROLES_BIT_CW_WORDS:
                    cnfEquipmentLinkedWord.objects.filter(id=item["id"]).delete()

            if form.EQ_SEQ_DATA_STEPS and len(form.EQ_SEQ_DATA_STEPS) > 0:
                for item in form.EQ_SEQ_DATA_STEPS.items():
                    if len(item[1]) > 0:
                        for item_del in item[1]:
                            if item_del[1]["n_role__b_role_equipment"]:
                                cnfSequenceLinkedEquipment.objects.filter(
                                    id=item_del[1]["id"]
                                ).delete()
                            else:
                                cnfSequenceLinkedVariable.objects.filter(
                                    id=item_del[1]["id"]
                                ).delete()

                        # cnfSequenceLinkedEquipment.objects.filter(id=item['id']).delete()

            if linked_sequences_records and linked_sequences_records.get(
                "variable_create"
            ):
                cnfSequenceLinkedVariable.objects.bulk_create(
                    linked_sequences_records["variable_create"]
                )
            if linked_sequences_records and linked_sequences_records.get(
                "equipment_create"
            ):
                cnfSequenceLinkedEquipment.objects.bulk_create(
                    linked_sequences_records["equipment_create"]
                )
            if linked_sequences_records and linked_sequences_records.get("variable"):
                cnfSequenceLinkedVariable.objects.bulk_update(
                    linked_sequences_records["variable"],
                    [
                        "n_equipment",
                        "n_role",
                        "n_timer",
                        "n_step",
                        "n_variable_link",
                        "n_seq_type",
                        "b_masked",
                    ],
                )
            if linked_sequences_records and linked_sequences_records.get("equipment"):
                cnfSequenceLinkedEquipment.objects.bulk_update(
                    linked_sequences_records["equipment"],
                    [
                        "n_equipment",
                        "n_role",
                        "n_timer",
                        "n_step",
                        "n_equipment_link",
                        "n_seq_type",
                        "b_masked",
                    ],
                )
        if self.request.POST.get("download_to_plc") == "on":
            self.RETURN_BLOCK_FROM_PLC = download_equipments(
                plc_id=form.instance.n_controller.pk,
                min=form.instance.pk,
                max=form.instance.pk,
                ajax=False,
            )
            if self.RETURN_BLOCK_FROM_PLC.get("error_back"):
                self.RETURN_BLOCK_FROM_PLC["return_block"] = self.RETURN_BLOCK_FROM_PLC[
                    "error_back"
                ]
            elif not self.RETURN_BLOCK_FROM_PLC.get("return_block"):
                self.RETURN_BLOCK_FROM_PLC["return_block"] = [
                    {
                        "error_num": "Оборудование успешно загружено в ПЛК",
                        "index_num": "None",
                        "param_num": "None",
                    }
                ]

        return super().form_valid(form)

    def form_invalid(self, form):
        return super().form_invalid(form)


class EquipmentDeleteView(LoginRequiredMixin, EquipmentAuthMixin, DeleteView):
    """Удаление выбранной переменной."""

    model = cnfEquipment
    template_name = "equipments/create.html"
    pk_url_kwarg = "eq_id"

    # def get_form_kwargs(self):
    #     kwargs = super().get_form_kwargs()
    #     kwargs["id"] = int(self.kwargs["eq_id"])
    #     kwargs["plc_id"] = int(self.kwargs["plc_id"])
    #     return kwargs

    def get_success_url(self):
        return reverse(
            "equipments:equipment_home",
        )


def download_equipments(request=False, plc_id=False, min=None, max=None, ajax=True):

    return_block_errors = None
    DownloadToPLCInstance.clear()
    time_fix = timezone.now()

    if None in [min, max]:
        min = request.GET.get("min")
        max = request.GET.get("max")
        action = request.GET.get("action")

    par_kwargs = {
        "n_equipment__n_controller": plc_id,
        "n_equipment__id__gte": min,
        "n_equipment__id__lte": max,
    }

    if request:
        filter = request.GET.get("filter")
        if filter and filter != "":  # если есть фильтр - делаем запрос ID-шников
            query_ids = list(
                get_equipments_data_custom_filter(plc_id=plc_id, filter_value=filter)[
                    0
                ].values_list("pk", flat=True)
            )
            par_kwargs = {
                "n_equipment__n_controller": plc_id,
                "n_equipment__id__in": query_ids,
            }

    # Данные простого агрегата + ПИД + АВР + CW(Sequence)
    data = (
        cnfEquipmentValue.objects.filter(
            **par_kwargs
        )
        .exclude(n_attribute__n_parameter_id=0)
        .select_related("n_equipment", "n_attribute")
        .all()
        .order_by("n_equipment", "n_attribute__n_parameter_id")
    )

    data_sw = cnfEquipmentLinkedWord.objects.filter(**par_kwargs, n_word_type=1)
    data_cw = cnfEquipmentLinkedWord.objects.filter(**par_kwargs, n_word_type=2)
    data_linked_var = cnfEquipmentLinkedVariable.objects.filter(**par_kwargs).order_by('n_index')
    data_linked_eq = cnfEquipmentLinkedEquipment.objects.filter(**par_kwargs).order_by('n_index')
    data_linked_pid_var = cnfEquipmentLinkedPIDVariable.objects.filter(**par_kwargs).order_by('n_index')
    data_linked_seq_var = cnfSequenceLinkedVariable.objects.filter(
        **par_kwargs
    ).order_by("n_equipment_id", "n_seq_type", "n_step")
    data_linked_seq_eq = cnfSequenceLinkedEquipment.objects.filter(
        **par_kwargs
    ).order_by("n_equipment_id", "n_seq_type", "n_step")

    # raise Exception('err')

    if data:
        clean_data = get_equipment_data_to_plc(
            data,
            PlcCommandConstants.CMD_WRITE_EQUIPMENT_BASE_CONFIG,
            data_sw=data_sw,
            data_cw=data_cw,
            data_linked_var=data_linked_var,
            data_linked_eq=data_linked_eq,
            data_linked_pid_var=data_linked_pid_var,
            data_linked_seq_var=data_linked_seq_var,
            data_linked_seq_eq=data_linked_seq_eq,
        )
        DownloadToPLCInstance.download_max_count = len(
            clean_data
        )  # передаем количество записываемых объектов
        # raise
        return_block_errors = send_data_to_plc(
            plc_id, clean_data, GlobalObjectID.EQUIPMENT, DownloadToPLCInstance, True
        )  # DownloadToPLCInstance)
    else:
        print("Данные не найдены с индексами от", min, " до", max)
        DownloadToPLCInstance.download_max_count = 10
    DownloadToPLCInstance.download_max_count = 1
    DownloadToPLCInstance.download_next(DownloadToPLCInstance.download_max_count)
    # DownloadToPLCInstance.clear()
    print(f"Время заливки: {(timezone.now()-time_fix).seconds} сек.")
    if ajax:
        response = {"error_back": return_block_errors}
        # response =  return_block_errors
        return JsonResponse(response)
    return {"error_back": return_block_errors}


def upload_equipments(request, plc_id, min=None, max=None, ajax=True):

    return_block_errors = None
    DownloadToPLCInstance.clear()
    time_fix = timezone.now()

    if None in [min, max]:
        min = request.GET.get("min")
        max = request.GET.get("max")
        action = request.GET.get("action")
    module_index = cnfEquipment.objects.get(id=min).n_equipment_index

    clean_data = {
        min: [
            [1, 3],
            [2, PlcCommandConstants.CMD_READ_EQUIPMENT_CONFIG],
            [3, module_index],
        ]
    }

    return_block = send_data_to_plc(
        plc_id, clean_data, GlobalObjectID.EQUIPMENT, None, False
    )  # DownloadToPLCInstance)
    data_mismatch = []
    if ajax:
        response = {"return_block": return_block}
        if isinstance(return_block, list) and return_block[0].get("error_num"):
            return JsonResponse({"return_block": return_block})
        elif not return_block:
            data_mismatch.append("Нет ответа от ПЛК!")
        else:
            # разбираем по категориям, чтобы корректно сравнить
            categories_data = {}
            for item_return_block in return_block:
                if (
                    item_return_block[2]
                    == PlcCommandConstants.RETURN_CMD_READ_EQUIPMENT_CONFIG
                ):
                    categories_data[
                        PlcCommandConstants.RETURN_CMD_READ_EQUIPMENT_CONFIG
                    ] = item_return_block
                elif (
                    item_return_block[2]
                    == PlcCommandConstants.RETURN_CMD_READ_EQUIPMENT_LINK_EQ_CONFIG
                ):
                    categories_data[
                        PlcCommandConstants.RETURN_CMD_READ_EQUIPMENT_LINK_EQ_CONFIG
                    ] = item_return_block
                elif (
                    item_return_block[2]
                    == PlcCommandConstants.RETURN_CMD_READ_EQUIPMENT_LINK_VDB_CONFIG
                ):
                    categories_data[
                        PlcCommandConstants.RETURN_CMD_READ_EQUIPMENT_LINK_VDB_CONFIG
                    ] = item_return_block
                elif (
                    item_return_block[2]
                    == PlcCommandConstants.RETURN_CMD_READ_EQUIPMENT_LINK_PID_CONFIG
                ):
                    categories_data[
                        PlcCommandConstants.RETURN_CMD_READ_EQUIPMENT_LINK_PID_CONFIG
                    ] = item_return_block
                elif (
                    item_return_block[2]
                    == PlcCommandConstants.RETURN_CMD_READ_EQUIPMENT_SEQ1_CONFIG
                ):
                    categories_data[
                        PlcCommandConstants.RETURN_CMD_READ_EQUIPMENT_SEQ1_CONFIG
                    ] = item_return_block
                elif (
                    item_return_block[2]
                    == PlcCommandConstants.RETURN_CMD_READ_EQUIPMENT_SEQ2_CONFIG
                ):
                    categories_data[
                        PlcCommandConstants.RETURN_CMD_READ_EQUIPMENT_SEQ2_CONFIG
                    ] = item_return_block
                elif (
                    item_return_block[2]
                    == PlcCommandConstants.RETURN_CMD_READ_EQUIPMENT_SEQ3_CONFIG
                ):
                    categories_data[
                        PlcCommandConstants.RETURN_CMD_READ_EQUIPMENT_SEQ3_CONFIG
                    ] = item_return_block
                elif (
                    item_return_block[2]
                    == PlcCommandConstants.RETURN_CMD_READ_EQUIPMENT_SEQ4_CONFIG
                ):
                    categories_data[
                        PlcCommandConstants.RETURN_CMD_READ_EQUIPMENT_SEQ4_CONFIG
                    ] = item_return_block
            object_info = (
                cnfEquipmentValue.objects.select_related("n_equipment", "n_attribute")
                .exclude(n_attribute__n_parameter_id=0)
                .filter(
                    n_equipment__n_equipment_index=return_block[0].get(3),
                    n_equipment__n_controller_id=plc_id,
                )
            )
            # Проверка по базовой конфигурации агрегата
            for item in object_info:
                if item.n_attribute.c_name_attribute == "CW":
                    # В слове разбираем только нужные биты
                    attr_CW_mask = []  # [0]*16
                    for item_attr in cnfAttribute.objects.filter(
                        n_global_object_type=item.n_attribute.n_global_object_type,
                        n_attribute_type=AttributeFieldType.BOOLEAN_FIELD,
                        c_name_attribute__contains="CW.",
                    ).exclude(n_attr_display_order=0):
                        attr_CW_mask.append((item_attr.n_parameter_bit, 1))
                    attr_CW_mask_int = get_int_from_bits(attr_CW_mask)
                    attr_CW_mask_int = attr_CW_mask_int & int(
                        categories_data[
                            PlcCommandConstants.RETURN_CMD_READ_EQUIPMENT_CONFIG
                        ].get(item.n_attribute.n_parameter_id)
                    )
                    if item.f_value != attr_CW_mask_int:
                        data_mismatch.append(
                            f"{item.n_attribute.c_display_attribute}: {int(item.f_value)} :  {attr_CW_mask_int}"
                        )
                else:
                    precision = get_count_precision(item.f_value)
                    if item.f_value != round(
                        categories_data[
                            PlcCommandConstants.RETURN_CMD_READ_EQUIPMENT_CONFIG
                        ].get(item.n_attribute.n_parameter_id),
                        precision,
                    ):
                        data_mismatch.append(
                            f"{item.n_attribute.c_display_attribute}: {item.f_value} :  {round(categories_data[PlcCommandConstants.RETURN_CMD_READ_EQUIPMENT_CONFIG].get(item.n_attribute.n_parameter_id),precision)}"
                        )

            # Проверка по связанным переменным
            if categories_data.get(
                PlcCommandConstants.RETURN_CMD_READ_EQUIPMENT_LINK_VDB_CONFIG
            ):
                parse_match_linked_object(
                    link_model=cnfEquipmentLinkedVariable,
                    categories_data=categories_data,
                    plc_id=plc_id,
                    data_mismatch=data_mismatch,
                )
            # Проверка по связанному оборудованию
            if categories_data.get(
                PlcCommandConstants.RETURN_CMD_READ_EQUIPMENT_LINK_EQ_CONFIG
            ):
                parse_match_linked_object(
                    link_model=cnfEquipmentLinkedEquipment,
                    categories_data=categories_data,
                    plc_id=plc_id,
                    data_mismatch=data_mismatch,
                )
            # Проверка по конфигурации ПИД
            if categories_data.get(
                PlcCommandConstants.RETURN_CMD_READ_EQUIPMENT_LINK_PID_CONFIG
            ):
                parse_match_linked_object(
                    link_model=cnfEquipmentLinkedPIDVariable,
                    categories_data=categories_data,
                    plc_id=plc_id,
                    data_mismatch=data_mismatch,
                )
            # Проверка по последовательности 1
            if categories_data.get(
                PlcCommandConstants.RETURN_CMD_READ_EQUIPMENT_SEQ1_CONFIG
            ):
                parse_match_linked_object(
                    link_model=cnfSequenceLinkedVariable,
                    categories_data=categories_data,
                    plc_id=plc_id,
                    data_mismatch=data_mismatch,
                    seq_type=1,
                )
            # Проверка по последовательности 2
            if categories_data.get(
                PlcCommandConstants.RETURN_CMD_READ_EQUIPMENT_SEQ2_CONFIG
            ):
                # pass
                parse_match_linked_object(
                    link_model=cnfSequenceLinkedVariable,
                    categories_data=categories_data,
                    plc_id=plc_id,
                    data_mismatch=data_mismatch,
                    seq_type=2,
                )
            # Проверка по последовательности 3
            if categories_data.get(
                PlcCommandConstants.RETURN_CMD_READ_EQUIPMENT_SEQ3_CONFIG
            ):
                parse_match_linked_object(
                    link_model=cnfSequenceLinkedVariable,
                    categories_data=categories_data,
                    plc_id=plc_id,
                    data_mismatch=data_mismatch,
                    seq_type=3,
                )
            # Проверка по последовательности 4
            if categories_data.get(
                PlcCommandConstants.RETURN_CMD_READ_EQUIPMENT_SEQ4_CONFIG
            ):
                parse_match_linked_object(
                    link_model=cnfSequenceLinkedVariable,
                    categories_data=categories_data,
                    plc_id=plc_id,
                    data_mismatch=data_mismatch,
                    seq_type=4,
                )
        return JsonResponse({"return_block": data_mismatch})
    return {"return_block": return_block}


def parse_match_linked_object(
    link_model, categories_data, plc_id, data_mismatch, seq_type=None
):
    """Проверка на соответствие линкованных объектов."""
    table_name = link_model._meta.db_table
    mess_description = {
        cnfEquipmentLinkedVariable._meta.db_table: "переменной",
        cnfEquipmentLinkedEquipment._meta.db_table: "оборудования",
        cnfEquipmentLinkedPIDVariable._meta.db_table: "ПИД-переменной",
        cnfSequenceLinkedVariable._meta.db_table: "шага",
    }
    return_command = {
        cnfEquipmentLinkedVariable._meta.db_table: PlcCommandConstants.RETURN_CMD_READ_EQUIPMENT_LINK_VDB_CONFIG,
        cnfEquipmentLinkedEquipment._meta.db_table: PlcCommandConstants.RETURN_CMD_READ_EQUIPMENT_LINK_EQ_CONFIG,
        cnfEquipmentLinkedPIDVariable._meta.db_table: PlcCommandConstants.RETURN_CMD_READ_EQUIPMENT_LINK_PID_CONFIG,
        cnfSequenceLinkedVariable._meta.db_table: {
            1: PlcCommandConstants.RETURN_CMD_READ_EQUIPMENT_SEQ1_CONFIG,
            2: PlcCommandConstants.RETURN_CMD_READ_EQUIPMENT_SEQ2_CONFIG,
            3: PlcCommandConstants.RETURN_CMD_READ_EQUIPMENT_SEQ3_CONFIG,
            4: PlcCommandConstants.RETURN_CMD_READ_EQUIPMENT_SEQ4_CONFIG,
        },
    }
    query_values = {
        cnfEquipmentLinkedVariable._meta.db_table: (
            "n_variable",
            "n_variable__n_variable_index",
            "n_variable__c_name_variable",
            "c_name_variable",
        ),
        cnfEquipmentLinkedEquipment._meta.db_table: (
            "n_equipment_link",
            "n_equipment_link__n_equipment_index",
            "n_equipment_link__c_name_equipment",
            "c_name_equipment",
        ),
        cnfEquipmentLinkedPIDVariable._meta.db_table: (
            "n_variable_link",
            "n_variable_link__n_variable_index",
            "n_variable_link__c_name_variable",
            "c_name_variable",
        ),
        cnfSequenceLinkedVariable._meta.db_table: (
            "n_role__n_role_index",
            "n_timer",
            "n_variable_link__n_variable_index",
            "n_step",
            "n_variable_link__c_name_variable",
            "n_role__c_role_desc",
        ),
    }
    # Для шагов последовательности
    if table_name == cnfSequenceLinkedVariable._meta.db_table:

        link_objects = list(
            cnfSequenceLinkedVariable.objects.select_related(
                "n_equipment", "n_variable_link", "n_role"
            )
            .filter(
                n_equipment__n_equipment_index=categories_data[
                    return_command[table_name][seq_type]
                    # return_command[table_name][seq_type-1][seq_type]
                ].get(3),
                n_seq_type=seq_type,
                n_equipment__n_controller_id=plc_id
            )
            .values(
                "n_role__n_role_index",
                "n_timer",
                "n_variable_link__n_variable_index",
                "n_step",
                "n_variable_link__c_name_variable",
                "n_role__c_role_desc",
                "b_masked",
            )
            .annotate(obj=Value(True, output_field=BooleanField()))
            .union(
                cnfSequenceLinkedEquipment.objects.select_related(
                    "n_equipment", "n_equipment_link", "n_role"
                )
                .filter(
                    n_equipment__n_equipment_index=categories_data[
                        return_command[table_name][seq_type]
                        # return_command[table_name][seq_type-1][seq_type]
                    ].get(3),
                    n_seq_type=seq_type,
                    n_equipment__n_controller_id=plc_id
                )
                .values(
                    "n_role__n_role_index",
                    "n_timer",
                    "n_equipment_link__n_equipment_index",
                    "n_step",
                    "n_equipment_link__c_name_equipment",
                    "n_role__c_role_desc",
                    "b_masked",
                )
                .annotate(obj=Value(False, output_field=BooleanField()))
            )
            .order_by("n_step")
        )
    else:
        link_objects = list(
            link_model.objects.select_related(
                "n_role", "n_equipment", query_values[table_name][0]
            )
            .filter(
                n_equipment__n_equipment_index=categories_data[
                    return_command[table_name]
                ].get(3),
                n_equipment__n_controller_id=plc_id,
            )
            .values(
                "n_index",
                "n_role__n_role_index",
                "n_role__c_role_desc",
                query_values[table_name][1],
                query_values[table_name][2],
                "n_timer",
                "n_equipment__n_equipment_index",
            ).order_by("n_index")
        )
    # obj_role_timer_index = []
    obj_role_timer_index = {}
    for index in range(
        5,
        int(
            categories_data[
                (
                    return_command[table_name]
                    if seq_type == None
                    else return_command[table_name][seq_type]
                )
            ].get(1)
        ),
        3,
    ):
        obj_role_timer_index[(index - 2) // 3] = (
            categories_data[
                (
                    return_command[table_name]
                    if seq_type == None
                    else return_command[table_name][seq_type]
                )
            ].get(index),
            categories_data[
                (
                    return_command[table_name]
                    if seq_type == None
                    else return_command[table_name][seq_type]
                )
            ].get(index + 1),
            categories_data[
                (
                    return_command[table_name]
                    if seq_type == None
                    else return_command[table_name][seq_type]
                )
            ].get(index + 2),
        )

    # Проверка на совпадение
    for item_link in link_objects:
        #!!!!!!!!!! Шаги
        if seq_type != None:
            multiplier = -1 if item_link["b_masked"] else 1
        if any(
            (
                float(item_link["n_role__n_role_index"]),
                item_link["n_timer"],
                float(
                    item_link[query_values[table_name][1]]
                    if seq_type == None
                    else multiplier * item_link[query_values[table_name][2]]
                ),
            )
            == x
            for x in obj_role_timer_index.values()
        ):
            item_link["delete"] = True
            for k, v in obj_role_timer_index.items():
                if len(v) == 3:
                    if v == (
                        float(item_link["n_role__n_role_index"]),
                        item_link["n_timer"],
                        float(
                            item_link[query_values[table_name][1]]
                            if seq_type == None
                            else multiplier * item_link[query_values[table_name][2]]
                        ),
                    ):
                        obj_role_timer_index[k] = (True, v[0], v[1], v[2])
                        break

    for key, item in obj_role_timer_index.items():
        for item_link in link_objects:
            if len(item) == 3:
                if (
                    item_link.get("n_role__n_role_index") == item[0]
                    and item_link.get("n_variable__n_variable_index") == item[2]
                ):
                    precision = get_count_precision(item_link.get("n_timer"))
                    if item_link.get("n_timer") == round(item[1], precision):
                        item_link["delete"] = True
                        # del obj_role_timer_index[key]
                        obj_role_timer_index[key] = (True, item[0], item[1], item[2])

    # Если остались неудаленные элементы в link_objects- значит не совпадает с конфигом в ПЛК
    if link_objects:
        for item_link in link_objects:
            if not item_link.get("delete"):
                add_mes = (
                    f'Тип({seq_type}). Шаг {item_link["n_step"]}.' if seq_type else ""
                )
                data_mismatch.append(
                    f'{add_mes}В ПЛК нет роли {mess_description[table_name]}: [{item_link.get("n_index") if item_link.get("n_index") else ""}] {item_link["n_role__n_role_index"]}.{item_link["n_role__c_role_desc"]}, {item_link["n_timer"]} для {item_link[query_values[table_name][1]] if seq_type == None else item_link[query_values[table_name][4]]}'
                )
    # Если остались неудаленные элементы в obj_role_timer_index- значит не совпадает с конфигом в БД
    if obj_role_timer_index:
        # for item_role_timer_index in obj_role_timer_index:
        for item_key, item_role_timer_index in obj_role_timer_index.items():
            if len(item_role_timer_index) == 3:
                if table_name == cnfEquipmentLinkedVariable._meta.db_table:
                    role = cnfEquipmentVariableRole.objects.filter(
                        n_role_index=item_role_timer_index[0]
                    ).values("c_role_desc")[0]
                    obj = cnfVariable.objects.filter(
                        n_variable_index=item_role_timer_index[2]
                    ).values(query_values[table_name][3])[0]
                elif table_name == cnfEquipmentLinkedPIDVariable._meta.db_table:
                    role = cnfEquipmentPIDVariableRole.objects.filter(
                        n_role_index=item_role_timer_index[0]
                    ).values("c_role_desc")[0]
                    obj = cnfVariable.objects.filter(
                        n_variable_index=item_role_timer_index[2]
                    ).values(query_values[table_name][3])[0]
                elif table_name == cnfEquipmentLinkedEquipment._meta.db_table:
                    role = cnfEquipmentRole.objects.filter(
                        n_role_index=item_role_timer_index[0]
                    ).values("c_role_desc")[0]
                    obj = cnfEquipment.objects.filter(
                        n_equipment_index=item_role_timer_index[2]
                    ).values(query_values[table_name][3])[0]
                else:
                    role = cnfSequenceRole.objects.filter(
                        n_role_index=item_role_timer_index[0]
                    ).values("c_role_desc", "b_role_equipment")[0]
                    name_obj = None
                    if role["b_role_equipment"]:
                        obj = cnfEquipment.objects.filter(
                            n_equipment_index=abs(item_role_timer_index[2])
                        ).values("c_name_equipment")[0]
                        name_obj = obj["c_name_equipment"]
                    else:
                        obj = cnfVariable.objects.filter(
                            n_variable_index=abs(item_role_timer_index[2])
                        ).values("c_name_variable")[0]
                        name_obj = obj["c_name_variable"]
                add_mes = f"Тип({seq_type}).Шаг {item_key}." if seq_type else ""
                data_mismatch.append(
                    f'{add_mes}В БД нет роли {mess_description[table_name]}: {role["c_role_desc"]}, {item_role_timer_index[1]} для {obj[query_values[table_name][3]] if seq_type == None else name_obj}'
                )

def check_state(request):
    download_count = DownloadToPLCInstance.percent_num
    return JsonResponse({"progress": download_count})
