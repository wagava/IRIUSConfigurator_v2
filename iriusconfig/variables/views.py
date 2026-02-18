import csv
from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import connection
from django.db.models import Q
from django.forms import BaseModelForm
from django.http import HttpRequest, HttpResponseRedirect, JsonResponse
from django.http.response import HttpResponse as HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import (CreateView, DeleteView, DetailView, ListView,
                                  TemplateView, UpdateView)
from equipments.models import cnfEquipment
from general.models import (cnfAttribute, cnfController,
                            cnfEquipmentAttributes, cnfVariableAttributes)
# from .forms import ModuleForm
from general.utils import get_bits_from_int, get_int_from_bits
from modules.models import cnfModule
from services.utils import DownloadToPLC, get_count_precision, send_data_to_plc
from iriusconfig.constants import (AttributeFieldType, AttributesIDs,
                                   CommandInterfaceConstants, GlobalObjectID,
                                   PlcCommandConstants,
                                   PLCModbusVarEQBaseAddress, ViewConstants)

from .mixins import VariableMixin, VariableAuthMixin
from .models import (cnfVariable, cnfVariableDataType, cnfVariableType,
                     cnfVariableValue)
from .utils import (get_formula_data, get_variable_data_to_plc,
                    get_variables_data_custom,
                    get_variables_data_custom_filter,
                    get_variables_data_custom_filter1)

User = get_user_model()
DownloadToPLCInstance = (
    DownloadToPLC()
)  # Экземпляр нужен для подсчета числа прогресс-бара на фронте


from csv import DictReader

from django.db.models import Q

from iriusconfig.settings import CUSTOM_STATIC_ROOT  # STATICFILES_DIRS

ORDER_FOR_IMPORT = {
    "variables": cnfVariable,
    # 'equipment': cnfVariableValue,
}
FIELDS_IMPORT = {
    "variables": [
        "n_variable_index",
        "c_name_variable",
        "c_desc_variable",
        "c_signal_ident",
        "c_name_section",
        "c_name_position",
        "c_num_position",
        "n_variable_data_type_id",
        "n_variable_type_id",
        "n_module_channel",
        # "n_module_id_id",
        "n_module_index",
    ],
    "variable_field_types": {
        "n_variable_index": int,
        "c_name_variable": str,
        "c_desc_variable": str,
        "c_signal_ident": str,
        "c_name_section": str,
        "c_name_position": str,
        "c_num_position": str,
        "n_controller_id": int,
        "n_variable_data_type_id": int,
        "n_variable_type_id": int,
        "n_module_channel": int,
        # "n_module_id_id": int,
        "n_module_index": int,
        "PPI.FilterTime": float,
        "PPI.mCodeScaleMin": float,
        "PPI.mCodeScaleMax": float,
        "PPI.mCodeLowThreshold": float,
        "PPI.mCodeHighThreshold": float,
        "PPI.Hysteresis": float,
        "PPI.MediaLen": float,
        "PPI.LocalOverrideValue": float,
        "PPI.MinEU": float,
        "PPI.MaxEU": float,
        "SP.SP": float,
        "SP.TechHi": float,
        "SP.TechLo": float,
        "CW": int,
        "Alarms.HiThreshold": float,
        "Alarms.HiHiThreshold": float,
        "Alarms.LoThreshold": float,
        "Alarms.LoLoThreshold": float,
        "HILO_CW": int,
        "Formula": str,
    },
    "variables_value": list(
        cnfAttribute.objects.filter(
            Q(n_global_object_type=GlobalObjectID.VARIABLE),
            # ~Q(n_attr_display_order=0)
        ).values_list(
            "id", "c_name_attribute"
        )  # ,flat=True)
    ),
    # 'equipment': cnfVariableValue,
}


def tags_update(request, plc_id):
    """Функция."""

    modules = {
        index: pk
        for index, pk in cnfModule.objects.filter(n_controller_id=plc_id)
        .values_list("n_module_index", "pk")
        .order_by("n_module_index")
    }

    var_types = {
        n_type_value: id
        for id, n_type_value in cnfVariableType.objects.values_list(
            "id", "n_type_value"
        )
    }

    var_data_types = {
        n_type_value: id
        for id, n_type_value in cnfVariableDataType.objects.values_list(
            "id", "n_type_value"
        )
    }
    
    for item_name, item_model in ORDER_FOR_IMPORT.items():
        # records = []
        with open(
            f"{CUSTOM_STATIC_ROOT}/data/{item_name}.csv", encoding="utf8"
        ) as csv_file:
            for row in DictReader(csv_file, delimiter=";"):
                # kwargs_fields_add = {}
                # for row in DictReader(
                #     # open(f'{STATICFILES_DIRS[0]}/data/{item_name}.csv',
                #     open(f"{CUSTOM_STATIC_ROOT}/data/{item_name}.csv", encoding="utf8"),delimiter=";"
                # ):  # ,delimiter=';'):
                #     # kwargs_fields_main = {'n_controller_id':plc_id}

                kwargs_fields_main = {"n_controller_id": plc_id}
                fields_db = []
                values_db = []
                for row_key, row_value in row.items():
                    fields_db.append(row_key)
                    values_db.append(row_value)

                # fields_db = list(row.keys())[0].split(";")
                # values_db = list(row.values())[0].split(";")
                # отделяем отдельно словарь для cnfVariable, отдельно для cnfVariableValue
                fields_values = [x[1] for x in FIELDS_IMPORT["variables_value"]]
                fields_id = {x[1]: x[0] for x in FIELDS_IMPORT["variables_value"]}
                for idx, item in enumerate(fields_db, 0):
                    # if item == "id":
                    #     id_var = values_db[idx]
                    if item in FIELDS_IMPORT[item_name]:
                        if FIELDS_IMPORT["variable_field_types"][item] == int:
                            # if isinstance(FIELDS_IMPORT["variable_field_types"][item], int):
                            if item == "n_module_index":
                                values_db[idx] = modules.get(int(float(values_db[idx])))
                                # values_db[idx] = (
                                #     modules[int(float(values_db[idx]))]
                                #     if modules.get(int(float(values_db[idx])))
                                #     else None
                                # )
                            if item == "n_variable_type_id":
                                values_db[idx] = var_types.get(
                                    int(float(values_db[idx]))
                                )
                                # values_db[idx] = (
                                #     var_types[int(float(values_db[idx]))]
                                #     if var_types.get(int(float(values_db[idx])))
                                #     else None
                                # )
                            if item == "n_variable_data_type_id":
                                values_db[idx] = var_data_types.get(
                                    int(float(values_db[idx]))
                                )
                                # values_db[idx] = (
                                #     var_data_types[int(float(values_db[idx]))]
                                #     if var_data_types.get(int(float(values_db[idx])))
                                #     else None
                                # )
                            kwargs_fields_main[
                                item if item != "n_module_index" else "n_module_id_id"
                            ] = (
                                FIELDS_IMPORT["variable_field_types"][item](
                                    float(values_db[idx])
                                )
                                if values_db[idx]
                                else None
                            )
                        else:
                            kwargs_fields_main[item] = (
                                FIELDS_IMPORT["variable_field_types"][item](
                                    values_db[idx]
                                )
                                if values_db[idx]
                                else None
                            )
                        #     kwargs_fields_main[item] = values_db[idx]

                object_new = False
                # raise Exception('e')
                variable_object = cnfVariable.objects.filter(
                    n_variable_index=kwargs_fields_main["n_variable_index"],n_controller_id=plc_id
                ).first()
                
                if not variable_object:
                    variable_object = cnfVariable.objects.create(**kwargs_fields_main)
                    object_new = True
                    print(
                        f"Создана новая переменная: {variable_object.n_variable_index}"
                    )
                else:
                    cnfVariable.objects.filter(id=variable_object.id).update(
                        **kwargs_fields_main
                    )
                    print(f"Обновлена переменная: {variable_object.n_variable_index}")
                # object_values = cnfVariableValue.objects.select_related('n_variable','n_attribute').filter(n_variable__pk=variable_object.pk).values('n_attribute__c_name_attribute', 'id')
                # все, что останется в object_values - удаляем в конце
                object_values = {
                    row["n_attribute__c_name_attribute"]: row["id"]
                    for row in cnfVariableValue.objects.select_related(
                        "n_variable", "n_attribute"
                    )
                    .filter(n_variable__pk=variable_object.pk)
                    .values("n_attribute__c_name_attribute", "id")
                }
                records_values = []
                cw_bits = []
                cw_hilo_bits = []
                cw_bits_attr = []
                cw_hilo_bits_attr = []
                cw_bits_calc = None
                cw_hilo_bits_calc = None
                for idx, item in enumerate(fields_db, 0):

                    if item in fields_values:  # FIELDS_IMPORT['variables_value']:

                        # if object_values.get(item):
                        object_values.pop(item, None)  # Удаляем из списка параметров

                        attribute_object = cnfAttribute.objects.filter(
                            n_global_object_type=GlobalObjectID.VARIABLE,
                            id=fields_id[item],
                        ).first()
                        if "CW." in attribute_object.c_name_attribute:
                            if values_db[idx] != "":
                                if "HILO_CW." in attribute_object.c_name_attribute:
                                    cw_hilo_bits.append(
                                        (
                                            attribute_object.n_parameter_bit,
                                            int(float(values_db[idx])),
                                        )
                                    )
                                else:
                                    cw_bits.append(
                                        (
                                            attribute_object.n_parameter_bit,
                                            int(float(values_db[idx])),
                                        )
                                    )
                            else:
                                if "HILO_CW." in attribute_object.c_name_attribute:
                                    cw_hilo_bits_attr.append(
                                        (
                                            attribute_object.n_parameter_bit,
                                            attribute_object,
                                        )
                                    )
                                else:
                                    cw_bits_attr.append(
                                        (
                                            attribute_object.n_parameter_bit,
                                            attribute_object,
                                        )
                                    )
                        # разбивка на биты слова из csv-файла
                        if attribute_object.c_name_attribute == "CW":
                            cw_bits_calc = get_bits_from_int(int(float(values_db[idx])))
                        elif attribute_object.c_name_attribute == "HILO_CW":
                            cw_hilo_bits_calc = get_bits_from_int(
                                int(float(values_db[idx]))
                            )
                        if object_new:
                            if values_db[idx] != "":
                                records_values.append(
                                    cnfVariableValue(
                                        n_variable=variable_object,
                                        n_attribute=cnfAttribute.objects.filter(
                                            n_global_object_type=GlobalObjectID.VARIABLE
                                        ).get(id=fields_id[item]),
                                        f_value=(
                                            values_db[idx] if item != "Formula" else 0
                                        ),
                                        c_note="---",
                                        c_formula=(
                                            values_db[idx] if item == "Formula" else ""
                                        ),
                                    )
                                )
                        else:
                            try:
                                if "CW." not in item:
                                    item_value = cnfVariableValue.objects.filter(
                                        n_variable=variable_object.id,
                                        n_attribute=attribute_object,
                                    ).first()
                                    set_value = FIELDS_IMPORT["variable_field_types"][
                                        item
                                    ](
                                        values_db[idx]
                                        if item == "Formula"
                                        else float(values_db[idx])
                                    )
                                    if item_value:

                                        cnfVariableValue.objects.filter(
                                            n_variable=variable_object,
                                            n_attribute=attribute_object.id,
                                        ).update(
                                            f_value=(
                                                set_value if item != "Formula" else 0
                                            ),
                                            c_formula=(
                                                set_value if item == "Formula" else ""
                                            ),
                                        )
                                    else:
                                        if values_db[idx] != "":
                                            cnfVariableValue.objects.create(
                                                n_variable=variable_object,
                                                n_attribute=attribute_object,
                                                f_value=(
                                                    set_value
                                                    if item != "Formula"
                                                    else 0
                                                ),
                                                c_note="---",
                                                c_formula=(
                                                    set_value
                                                    if item == "Formula"
                                                    else ""
                                                ),
                                            )
                            except Exception:
                                print("error", item)
                # id_cw = (
                #     cnfAttribute.objects.filter(
                #         n_global_object_type=GlobalObjectID.VARIABLE,
                #         c_name_attribute="CW",
                #     ).first()
                # ).id
                # id_hilo_cw = (
                #     cnfAttribute.objects.filter(
                #         n_global_object_type=GlobalObjectID.VARIABLE,
                #         c_name_attribute="HILO_CW",
                #     ).first()
                # ).id
                if object_values:  # удаляем неиспользуемые атрибуты
                    for id in object_values.values():
                        cnfVariableValue.objects.filter(id=id).delete()
                # если новая переменная - создаем новые записи значений переменной
                if object_new:
                    cnfVariableValue.objects.bulk_create(records_values)

                # нужно проверить, если CW передано, значит его сразу записываем, потом пересчитываем биты и тоже пишем, остальное (переданные флаги) игнорим
                # #####!!!!!!!!!!!!
                # делаем пересчет CW,чтобы записать как параметр в БД
                # cw_bits - {<номер бита>: <значение>}
                # cw_bits_calc - {<номер бита>: <True/False>}
                # cw_bits_attr - (<номер бита>, <экземпляр атрибута>) атрибуты, которые имеют префикс CW.
                if (
                    cw_bits_attr or cw_hilo_bits_attr
                ):  # если заполнен список, значит записан CW/HILO_CW и нужно рассчитать биты
                    for item in cw_bits_attr:
                        item_value = cnfVariableValue.objects.filter(
                            n_variable=variable_object.id,
                            n_attribute=item[1],
                                    ).first()
                        if object_new or item_value is None:
                            cnfVariableValue.objects.create(
                                n_variable=variable_object,
                                n_attribute=item[1],
                                f_value=cw_bits_calc[item[0]],
                                c_note="---",
                                c_formula="",
                            )
                        else:
                            cnfVariableValue.objects.filter(
                                n_variable=variable_object, n_attribute=item[1]
                            ).update(f_value=cw_bits_calc[item[0]])
                    for item in cw_hilo_bits_attr:
                        # pass
                        item_value = cnfVariableValue.objects.filter(
                                        n_variable=variable_object.id,
                                        n_attribute=item[1],
                                    ).first()
                        if object_new or item_value is None:
                            cnfVariableValue.objects.create(
                                n_variable=variable_object,
                                n_attribute=item[1],
                                f_value=cw_hilo_bits_calc[item[0]],
                                c_note="---",
                                c_formula="",
                            )
                        else:
                            cnfVariableValue.objects.filter(
                                    n_variable=variable_object, n_attribute=item[1]
                                ).update(f_value=cw_hilo_bits_calc[item[0]])


                                
                                
                                
    return HttpResponseRedirect(
        reverse("variables:variable_by_plc", kwargs={"plc_id": plc_id})
    )


def tags_delete(request, plc_id):
    """Функция."""
    cnfVariable.objects.all().delete()
    return HttpResponseRedirect(
        reverse("variables:variable_by_plc", kwargs={"plc_id": plc_id})
    )


def variable_home(request):
    """Функция перехода на домашнюю страницу.
    В текущей реализации - на страницу переменных.
    """
    # return HttpResponse('Empty')
    return HttpResponseRedirect(
        reverse("variables:variable_by_plc", kwargs={"plc_id": 1})
    )


class VariableListView(LoginRequiredMixin, ListView):
    """Отображение всех переменных."""

    paginate_by = ViewConstants.MAX_ITEMS_ON_PAGE
    template_name = "variables/index.html"
    pk_url_kwarg = "plc_id"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["plc_list"] = cnfController.objects.all().order_by("c_desc_controller").values_list(
            "id", "c_desc_controller"
        )
        context["plc_id"] = int(self.kwargs["plc_id"])
        context["filter"] = self.kwargs.get("filter")
        context["filter_index"] = self.kwargs.get("filter_index")
        context["filter_cvv"] = self.kwargs.get("filter_cvv")
        context["filter_module"] = self.kwargs.get("filter_module")
        context["filter_channel"] = self.kwargs.get("filter_channel")

        context["all_count"] = self.kwargs.get("all_count")
        return context

    def get_queryset(self):
        plc_selector = self.request.GET.get("plc_selector")
        filter = self.request.GET.get("filter")
        filter_index = self.request.GET.get("filter_index")
        filter_cvv = self.request.GET.get("filter_cvv")
        filter_module = self.request.GET.get("filter_module")
        filter_channel = self.request.GET.get("filter_channel")
        # if "plc_selector" in self.request.GET:
        #     new_plc_id = self.request.GET.get("plc_selector")
        #     return redirect(
        #         "variables:variable_by_plc_filter",
        #         plc_id=new_plc_id,
        #         filter=filter,
        #         filter_index=filter_index,
        #         filter_cvv=filter_cvv,
        #         filter_module=filter_module,
        #         filter_channel=filter_channel,
        #     )

        if (
            filter is not None
            and filter != ""
            or filter_index is not None
            and filter_index != ""
            or filter_cvv is not None
            and filter_cvv != ""
            or filter_module is not None
            and filter_module != ""
            or filter_channel is not None
            and filter_channel != ""
        ):
            self.kwargs["filter"] = filter
            self.kwargs["filter_index"] = filter_index
            self.kwargs["filter_cvv"] = filter_cvv
            self.kwargs["filter_module"] = filter_module
            self.kwargs["filter_channel"] = filter_channel
            self.kwargs["plc_id"] = int(plc_selector)
            queryset = get_variables_data_custom_filter(
                plc_id=plc_selector,
                filter_value=[
                    self.request.GET["filter_index"],
                    self.request.GET["filter"],
                    self.request.GET["filter_cvv"],
                    self.request.GET["filter_module"],
                    self.request.GET["filter_channel"],
                ],
            )
            self.kwargs["all_count"] = queryset[1]
            return queryset[0]

        if plc_selector is not None:
            if plc_selector != "":
                self.kwargs["plc_id"] = int(plc_selector)
                queryset = get_variables_data_custom_filter(plc_id=plc_selector)
                # queryset = get_variables_data_custom(n_controller=plc_selector)
        else:
            # queryset = get_variables_data_custom(n_controller=self.kwargs["plc_id"])
            queryset = get_variables_data_custom_filter(plc_id=self.kwargs["plc_id"])
        self.kwargs["all_count"] = queryset[1]
        return queryset[0]


class VariableCreateView(LoginRequiredMixin, VariableMixin, VariableAuthMixin, CreateView):
    """Создание переменной."""

    pk_url_kwarg = "plc_id"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["id"] = None
        kwargs["plc_id"] = int(self.kwargs["plc_id"])
        return kwargs

    def form_valid(self, form):

        setattr(form.instance, "c_user_edit", User.objects.get(username=self.request.user.username))
        setattr(form.instance, "d_last_edit", timezone.now())

        # Вынимаем поля с формы для сохренения в БД, нужно добавить остальные для сохранения

        if not form.is_valid():
            return super().form_invalid(form)

        form.save()  # Сначала сохраняем данные модуля из формы, чтобы FK таблицы значений было на что ссылаться при сохранении

        # получаем доп.данные с формы и отправляем в соответствующие таблицы cnfVariableValue

        prep_data = []
        cw_word = []
        cw_word_hilo = []
        for item in form.cleaned_data:
            if item.__contains__("attr_"):
                prep_data.append(
                    (
                        int(form.cleaned_data[item]),
                        cnfAttribute.objects.filter(
                            n_global_object_type=GlobalObjectID.VARIABLE
                        ).get(c_name_attribute=item.replace("attr_", "")),
                    )
                )
            elif item.__contains__("attrf_"):
                prep_data.append(
                    (
                        float(form.cleaned_data[item]),
                        cnfAttribute.objects.filter(
                            n_global_object_type=GlobalObjectID.VARIABLE
                        ).get(c_name_attribute=item.replace("attrf_", "")),
                    )
                )
            elif item.__contains__("attrb_"):

                bit = int(item.replace("attrb_", "")[0:2])

                # cw_word.append((bit,int(form.cleaned_data[item])))
                name_attribute = item.replace("attrb_", "")[2:]
                if name_attribute[:4] == "HILO":
                    cw_word_hilo.append((bit, int(form.cleaned_data[item])))
                else:
                    cw_word.append((bit, int(form.cleaned_data[item])))

                prep_data.append(
                    (
                        int(form.cleaned_data[item]),
                        cnfAttribute.objects.filter(
                            n_global_object_type=GlobalObjectID.VARIABLE
                        ).get(c_name_attribute=name_attribute),
                    )
                )
            elif item.__contains__("attrtxt_"):
                if form.cleaned_data[item] and form.cleaned_data[item] != "":
                    cnfVariableValue.objects.create(
                        n_variable=form.instance,
                        n_attribute=cnfAttribute.objects.filter(
                            n_global_object_type=GlobalObjectID.VARIABLE
                        ).get(c_name_attribute=item.replace("attrtxt_", "")),
                        f_value=0.0,
                        c_note="---",
                        c_formula=form.cleaned_data[item],
                    )
            # хард-код, переделать на более гибкую конструкцию
        if cw_word:
            prep_data.append(
                (
                    get_int_from_bits(cw_word),
                    cnfAttribute.objects.filter(
                        n_global_object_type=GlobalObjectID.VARIABLE
                    ).get(c_name_attribute="CW"),
                )
            )
        if cw_word_hilo:
            prep_data.append(
                (
                    get_int_from_bits(cw_word_hilo),
                    cnfAttribute.objects.filter(
                        n_global_object_type=GlobalObjectID.VARIABLE
                    ).get(c_name_attribute="HILO_CW"),
                )
            )

        records = [
            cnfVariableValue(
                n_variable=form.instance,
                n_attribute=n_attribute,
                f_value=f_value,
                c_note="---",
            )
            for f_value, n_attribute in prep_data
        ]

        cnfVariableValue.objects.bulk_create(records)

        if self.request.POST.get("download_to_plc") == "on":
            self.RETURN_BLOCK_FROM_PLC = download_variables(
                plc_id=form.instance.n_controller.pk,
                min=form.instance.pk,
                max=form.instance.pk,
                ajax=False,
            )
            # ERRORS_FROM_PLC['return_block'] = {'r':444}
            if not self.RETURN_BLOCK_FROM_PLC.get("return_block"):
                self.RETURN_BLOCK_FROM_PLC["return_block"] = [
                    {
                        "error_num": "Переменная успешно загружена в ПЛК",
                        "index_num": "None",
                        "param_num": "None",
                    }
                ]
        return super().form_valid(form)

    def form_invalid(self, form):
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse(
            "variables:variable_create",
            kwargs={"plc_id": self.kwargs["plc_id"]},
        )


class VariableUpdateView(LoginRequiredMixin, VariableMixin, VariableAuthMixin, UpdateView):
    """Редактирование информации по выбранной переменной."""

    pk_url_kwarg = "var_id"
    RETURN_BLOCK_FROM_PLC = []
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["id"] = self.kwargs["var_id"]
        kwargs["plc_id"] = self.kwargs["plc_id"]
        return kwargs

    def get(self, request, *args, **kwargs):

        min = request.GET.get("min")
        max = request.GET.get("max")
        action = request.GET.get("action")
        plc_id = self.kwargs["plc_id"]
        self.kwargs["RETURN_BLOCK_FROM_PLC"] = self.request.session.get(
            "RETURN_BLOCK_FROM_PLC"
        )
        if self.request.session.get("RETURN_BLOCK_FROM_PLC"):
            self.request.session["RETURN_BLOCK_FROM_PLC"] = []

        if all([min, max, action]):
            if action == CommandInterfaceConstants.ACTION_DOWNLOAD_TO_PLC:
                result_errors = download_variables(
                    request=request,
                    plc_id=plc_id,
                    min=min,
                    max=max,
                    ajax=False,
                )
                self.kwargs["download_errors"] = result_errors

        return super(VariableUpdateView, self).get(request, *args, **kwargs)

    def get_success_url(self):
        if (
            self.RETURN_BLOCK_FROM_PLC
        ):  # and self.request.session.get('RETURN_BLOCK_FROM_PLC'):
            self.request.session["RETURN_BLOCK_FROM_PLC"] = self.RETURN_BLOCK_FROM_PLC[
                "return_block"
            ]
        return reverse(
            "variables:variable_edit",
            args=[self.kwargs["plc_id"], self.kwargs["var_id"]],
        )

    def form_invalid(self, form: BaseModelForm) -> HttpResponse:
        return super().form_invalid(form)

    def form_valid(self, form):

        if self.request.session.get("RETURN_BLOCK_FROM_PLC"):
            self.request.session["RETURN_BLOCK_FROM_PLC"] = []

        form_variable_index_bottom = self.request.POST.get('variable_index')
        form_variable_index_below = self.request.POST.get('variable_index_below')
        form_variable_index = None
        
        if not (form_variable_index_bottom == str(form.cleaned_data.get('n_variable_index'))):
            form_variable_index = form_variable_index_bottom
        if not (form_variable_index_below == str(form.cleaned_data.get('n_variable_index'))):
            form_variable_index = form_variable_index_below
            
        if form_variable_index:
            if form_variable_index.isdigit():
                # variable = cnfvariable.objects.get(n_variable_index=form_variable_index,n_controller=self.kwargs["plc_id"])
                variables = cnfVariable.objects.filter(
                            n_variable_index=form_variable_index,
                            n_controller=self.kwargs["plc_id"]
                        )
                variable = variables.first()
                return redirect(
            "variables:variable_edit",
            plc_id=self.kwargs["plc_id"],
            var_id=variable.id if variable else self.kwargs["var_id"],
        )

        setattr(form.instance, "c_user_edit", User.objects.get(username=self.request.user.username))
        setattr(form.instance, "d_last_edit", timezone.now())

        if not form.is_valid():
            return super().form_invalid(form)

        form.save() 

        # получаем доп.даннsые с формы и отправляем в соответствующие таблицы cnfVariableValue
        index = 0
        prep_data = []
        prep_data_create = []
        # prep_formula = []
        # prep_formula_create = []
        cw_word = []
        cw_word_hilo = []
        name_attribute = ""

        for item_key, item_value in form.cleaned_data.items():
            if item_key.__contains__("attr_"):
                name_attribute = item_key.replace("attr_", "")
                if form.value_id_by_order.get(name_attribute):
                    prep_data.append(
                        (
                            # form.value_id_by_order[index],
                            form.value_id_by_order[name_attribute],
                            # int(form.cleaned_data[item]),
                            int(item_value),
                            cnfAttribute.objects.filter(
                                n_global_object_type=GlobalObjectID.VARIABLE
                            ).get(
                                c_name_attribute=name_attribute
                                # c_name_attribute=item.replace("attr_", "")
                            ),
                        )
                    )
                else:
                    prep_data_create.append(
                        (
                            int(item_value),
                            cnfAttribute.objects.filter(
                                n_global_object_type=GlobalObjectID.VARIABLE
                            ).get(c_name_attribute=name_attribute),
                        )
                    )

                index += 1
            elif item_key.__contains__("attrf_"):
                name_attribute = item_key.replace("attrf_", "")
                if form.value_id_by_order.get(name_attribute):
                    prep_data.append(
                        (
                            form.value_id_by_order[name_attribute],
                            float(item_value),
                            cnfAttribute.objects.filter(
                                n_global_object_type=GlobalObjectID.VARIABLE
                            ).get(c_name_attribute=name_attribute),
                        )
                    )
                else:
                    prep_data_create.append(
                        (
                            float(item_value),
                            cnfAttribute.objects.filter(
                                n_global_object_type=GlobalObjectID.VARIABLE
                            ).get(c_name_attribute=name_attribute),
                        )
                    )
                index += 1
            elif item_key.__contains__("attrb_"):
                bit = int(item_key.replace("attrb_", "")[0:2])
                # cw_word.append((bit,int(item_value)))
                name_attribute = item_key.replace("attrb_", "")[2:]
                if name_attribute[:4] == "HILO":
                    cw_word_hilo.append((bit, int(item_value)))
                else:
                    cw_word.append((bit, int(item_value)))
                if form.value_id_by_order.get(name_attribute):
                    prep_data.append(
                        (
                            form.value_id_by_order[name_attribute],
                            int(item_value),
                            cnfAttribute.objects.filter(
                                n_global_object_type=GlobalObjectID.VARIABLE
                            ).get(c_name_attribute=name_attribute),
                        )
                    )
                else:
                    prep_data_create.append(
                        (
                            int(item_value),
                            cnfAttribute.objects.filter(
                                n_global_object_type=GlobalObjectID.VARIABLE
                            ).get(c_name_attribute=name_attribute),
                        )
                    )
                index += 1
            elif item_key.__contains__("attrtxt_"):
                # idx = form.value_id_by_order[index]
                name_attribute = item_key.replace("attrtxt_", "")
                if item_value is not None:
                    if form.value_id_by_order.get(name_attribute):

                        cnfVariableValue.objects.filter(
                            id=form.value_id_by_order[name_attribute]
                        ).update(c_formula=item_value)

                    else:
                        cnfVariableValue.objects.create(
                            n_variable=form.instance,
                            n_attribute=cnfAttribute.objects.filter(
                                n_global_object_type=GlobalObjectID.VARIABLE
                            ).get(c_name_attribute=name_attribute),
                            f_value=0.0,
                            c_note="---",
                            c_formula=item_value,
                        )

                index += 1
            if form.value_id_by_order.get(name_attribute):
                del form.value_id_by_order[name_attribute]

        # хард-код, переделать на более гибкую конструкцию
        if cw_word:
            if form.invisible_fields_id.get("CW"):
                prep_data.append(
                    (
                        form.invisible_fields_id["CW"],
                        get_int_from_bits(cw_word),
                        cnfAttribute.objects.filter(
                            n_global_object_type=GlobalObjectID.VARIABLE
                        ).get(c_name_attribute="CW"),
                    )
                )
            else:
                prep_data_create.append(
                    (
                        get_int_from_bits(cw_word),
                        cnfAttribute.objects.filter(
                            n_global_object_type=GlobalObjectID.VARIABLE
                        ).get(c_name_attribute="CW"),
                    )
                )
        if cw_word_hilo:
            if form.invisible_fields_id.get("HILO_CW"):
                prep_data.append(
                    (
                        form.invisible_fields_id["HILO_CW"],
                        get_int_from_bits(cw_word_hilo),
                        cnfAttribute.objects.filter(
                            n_global_object_type=GlobalObjectID.VARIABLE
                        ).get(c_name_attribute="HILO_CW"),
                    )
                )
            else:
                prep_data_create.append(
                    (
                        get_int_from_bits(cw_word_hilo),
                        cnfAttribute.objects.filter(
                            n_global_object_type=GlobalObjectID.VARIABLE
                        ).get(c_name_attribute="HILO_CW"),
                    )
                )
        records = [
            cnfVariableValue(
                idx,
                n_variable=form.instance,
                n_attribute=n_attribute,
                f_value=f_value,
                c_note="---",
            )
            for idx, f_value, n_attribute in prep_data
        ]

        records_to_create = [
            cnfVariableValue(
                n_variable=form.instance,
                n_attribute=n_attribute,
                f_value=f_value,
                c_note="---",
            )
            for f_value, n_attribute in prep_data_create
        ]

        cnfVariableValue.objects.bulk_update(records, ["f_value"])

        if records_to_create:
            cnfVariableValue.objects.bulk_create(records_to_create)

        if self.request.POST.get("download_to_plc") == "on":
            self.RETURN_BLOCK_FROM_PLC = download_variables(
                plc_id=form.instance.n_controller.pk,
                min=form.instance.pk,
                max=form.instance.pk,
                ajax=False,
            )

            if not self.RETURN_BLOCK_FROM_PLC.get("return_block"):
                if self.RETURN_BLOCK_FROM_PLC.get("error_back"):
                    self.RETURN_BLOCK_FROM_PLC["return_block"] = [
                        {
                            "error_num": self.RETURN_BLOCK_FROM_PLC["error_back"][0].get("error_num"),
                            "index_num": self.RETURN_BLOCK_FROM_PLC["error_back"][0].get("index_num"),
                            "param_num": self.RETURN_BLOCK_FROM_PLC["error_back"][0].get("param_num"),
                        }
                    ]
                else:
                    self.RETURN_BLOCK_FROM_PLC["return_block"] = [
                        {
                            "error_num": "Переменная успешно загружена в ПЛК",
                            "index_num": "",
                            "param_num": "",
                        }
                    ]

        return super().form_valid(form)


class VariableDeleteView(LoginRequiredMixin, VariableAuthMixin, DeleteView):
    """Удаление выбранной переменной."""

    model = cnfVariable
    template_name = "variables/create.html"
    pk_url_kwarg = "var_id"

    def get_success_url(self):
        return reverse(
            "variables:variable_home",
        )


def download_variables(request=None, plc_id=None, min=None, max=None, ajax=True):

    return_block_errors = None
    DownloadToPLCInstance.clear()
    time_fix = timezone.now()
    if None in [min, max]:
        min = request.GET.get("min")
        max = request.GET.get("max")
        action = request.GET.get("action")
    par_kwargs = {}
    if request:
        filter = request.GET.get("filter")
        if filter and filter != "":  # если есть фильтр - делаем запрос ID-шников
            query_ids = list(
                get_variables_data_custom_filter(plc_id=plc_id, filter_value=filter)[
                    0
                ].values_list("pk", flat=True)
            )
            par_kwargs = {
                "n_variable__n_controller": plc_id,
                "n_variable__id__in": query_ids,
            }
    else:
        par_kwargs = {
            "n_variable__n_controller": plc_id,
            "n_variable__id__gte": min,
            "n_variable__id__lte": max,
        }
# # ========================TEST=========================
#     par_kwargs = {
#             "n_variable__n_controller": plc_id,
#             "n_variable__n_variable_index__gte": 1,
#             "n_variable__n_variable_index__lte": 20,
#         }
# # ========================TEST=========================
    data = list(
        cnfVariableValue.objects.filter(**par_kwargs)
        .exclude(n_attribute__n_parameter_id=0)
        .select_related("n_variable", "n_attribute")
        .all()
        .order_by("n_variable", "n_attribute__n_parameter_id")
    )
    par_kwargs["n_attribute__n_parameter_id"] = AttributesIDs.VAR_FORMULA
    data_formulas = (
        cnfVariableValue.objects.filter(**par_kwargs)
        .exclude(c_formula="")
        .select_related("n_variable", "n_attribute")
        .all()
        .order_by("n_variable", "n_attribute__n_parameter_id")
    )

    if data:
        clean_data, errors = get_variable_data_to_plc(
            data, data_formulas, PlcCommandConstants.CMD_WRITE_VARIABLE_CONFIG
        )
        if errors:
            DownloadToPLCInstance.download_max_count = 1
            return_block_errors = errors
        else:
            DownloadToPLCInstance.download_max_count = len(
                clean_data
            )  # передаем количество записываемых объектов

            return_block_errors = send_data_to_plc(
                plc_id,
                clean_data,
                GlobalObjectID.VARIABLE,
                DownloadToPLCInstance,
                True,
            )  # DownloadToPLCInstance)
    else:
        print("Данные не найдены с индексами от", min, " до", max)
    # DownloadToPLCInstance.download_next(DownloadToPLCInstance.download_max_count)
    print(f"Время заливки: {(timezone.now()-time_fix).seconds} сек.")
    if ajax:
        response = {"error_back": return_block_errors}
        return JsonResponse(response)
    if return_block_errors is None:
        return {"error_back": "Нет ответа от ПЛК!"}
    else:
        return {"error_back": return_block_errors}


def upload_variables(request, plc_id, min=None, max=None, ajax=True):

    if None in [min, max]:
        min = request.GET.get("min")
        max = request.GET.get("max")
        # action = request.GET.get("action")
    object_index = cnfVariable.objects.get(id=min).n_variable_index

    clean_data = {
        min: [
            [1, 3],
            [2, PlcCommandConstants.CMD_READ_VARIABLE_CONFIG],
            [3, object_index],
        ]
    }

    return_block = send_data_to_plc(
        plc_id, clean_data, GlobalObjectID.VARIABLE, None, False
    )  # DownloadToPLCInstance)

    if ajax:
        data_mismatch = []
        if isinstance(return_block, dict) and return_block.get("error_num"):
            pass
        elif not return_block:
            data_mismatch.append("Нет ответа от ПЛК!")
        else:
            variable_info = (
                cnfVariableValue.objects.select_related("n_variable", "n_attribute")
                .exclude(n_attribute__n_parameter_id=0)
                .filter(
                    n_variable__n_variable_index=return_block[0].get(3),
                    n_variable__n_controller_id=plc_id,
                )
            )
            # varlist = [item for item in variable_info.values()]

            # Разбор основных данных из 0 индекса списка
            for item in variable_info:
                if item.n_attribute.c_name_attribute == "CW":
                    # В слове разбираем только нужные биты
                    attr_CW_mask = []  # [0]*16
                    # masklist = [
                    #     item
                    #     for item in cnfAttribute.objects.filter(
                    #         n_global_object_type=2,
                    #         n_attribute_type=AttributeFieldType.BOOLEAN_FIELD,
                    #         c_name_attribute__startswith="CW.",
                    #     )
                    #     .exclude(n_attr_display_order=0)
                    #     .values()
                    # ]
                    for item_attr in cnfAttribute.objects.filter(
                        n_global_object_type=2,
                        n_attribute_type=AttributeFieldType.BOOLEAN_FIELD,
                        c_name_attribute__startswith="CW.",
                    ).exclude(n_attr_display_order=0):
                        attr_CW_mask.append((item_attr.n_parameter_bit, 1))
                    attr_CW_mask_int = get_int_from_bits(attr_CW_mask)
                    attr_CW_mask_int = attr_CW_mask_int & int(
                        return_block[0].get(item.n_attribute.n_parameter_id)
                    )
                    if item.f_value != attr_CW_mask_int:
                        data_mismatch.append(
                            f"{item.n_attribute.c_display_attribute}: БД[{int(item.f_value)}], ПЛК[{attr_CW_mask_int}]"
                        )
                elif item.n_attribute.c_name_attribute == "Formula":
                    # Разбор данных формулы из БД
                    formula_parsed = get_formula_data(item.c_formula)
                else:
                    precision = get_count_precision(item.f_value)
                    if return_block[0].get(
                        item.n_attribute.n_parameter_id
                    ) is not None and item.f_value != round(
                        return_block[0].get(item.n_attribute.n_parameter_id),
                        precision,
                    ):
                        # if return_block.get(item.n_attribute.n_parameter_id) != None and item.f_value != return_block.get(item.n_attribute.n_parameter_id):
                        data_mismatch.append(
                            f"{item.n_attribute.c_display_attribute}:"
                            f"{item.f_value}:  "
                            f"{round(return_block[0].get(item.n_attribute.n_parameter_id),precision)}"
                        )
            # Разбор данных формулы из 1 индекса списка

        return JsonResponse({"return_block": data_mismatch})
    return {"return_block": return_block[0]}


def check_state(request):
    download_count = DownloadToPLCInstance.percent_num
    return JsonResponse({"progress": download_count})


def export_csv(request):

    variables = cnfVariable.objects.all()
    variables_attrs = cnfVariableAttributes.objects.all()

    rows = []
    for variable in variables:
        for attr in variables_attrs:
            row = {
                "signal": f"{variable.c_name_variable}.{attr.c_attr_name}",
                "type": attr.c_data_type,
                "link": "непосредственно",
                "segment": attr.c_reg_type,
                "address": (variable.n_variable_index - 1)
                * PLCModbusVarEQBaseAddress.VAR_INDEX_OFFSET
                + PLCModbusVarEQBaseAddress.VAR_BASE_ADDRESS
                + attr.n_offset,
            }
            rows.append(row)

    equipments = cnfEquipment.objects.all()
    equipment_attrs = cnfEquipmentAttributes.objects.all()

    # rows = []
    for equipment in equipments:
        for attr in equipment_attrs:
            row = {
                "signal": f"{equipment.c_name_equipment}.{attr.c_attr_name}",
                "type": attr.c_data_type,
                "link": "непосредственно",
                "segment": attr.c_reg_type,
                "address": (equipment.n_equipment_index - 1)
                * PLCModbusVarEQBaseAddress.EQ_INDEX_OFFSET
                + PLCModbusVarEQBaseAddress.EQ_BASE_ADDRESS
                + attr.n_offset,
            }
            rows.append(row)
    # Генерация CSV-файла
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        f'attachment; filename="variables_{str(timezone.now())}.csv"'
    )

    writer = csv.DictWriter(
        response, fieldnames=["signal", "type", "link", "segment", "address"]
    )
    writer.writeheader()
    writer.writerows(rows)

    return response
