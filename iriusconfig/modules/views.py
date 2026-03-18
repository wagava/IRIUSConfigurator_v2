from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models.base import Model as Model
from django.db.models.query import QuerySet
from django.http import HttpRequest, HttpResponseRedirect, JsonResponse
from django.http.response import HttpResponse as HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import (CreateView, DeleteView, DetailView, ListView,
                                  TemplateView, UpdateView)
from general.models import cnfAttribute, cnfController
from general.utils import get_int_from_bits, set_mask_to_config_words
from services.mb_client import SelfModbusTcpClient
from services.utils import send_data_to_plc, get_plc_data

from iriusconfig.constants import (AttributeFieldType,
                                   CommandInterfaceConstants, GlobalObjectID,
                                   PlcCommandConstants, ViewConstants)
from .forms import ModuleForm
from .mixins import ModuleMixin, ModuleAuthMixin
from .models import cnfModule, cnfModuleValue  # , cnfModuleAttribute
from .utils import (DW_CNT, DownloadToPLC,  # , send_data_to_plc
                    download_modules_to_plc, get_module_data_to_plc,
                    get_module_extra_data, get_modules_data_custom,
                    get_bytes_from_int, get_2_words_from_float,
                    get_float_from_2_words)

User = get_user_model()

TEST_PROGRESS = 0

DownloadToPLCInstance = DownloadToPLC()


def module_home(request):
    """Функция перехода на домашнюю страницу.
    В текущей реализации - на страницу модулей.
    """
    return HttpResponseRedirect(reverse("modules:module_by_plc", kwargs={"plc_id": 1}))


class ModuleListView(LoginRequiredMixin, ListView):
    """Отображение всех модулей."""

    paginate_by = ViewConstants.MAX_ITEMS_ON_PAGE
    template_name = "modules/index.html"
    pk_url_kwarg = "plc_id"

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)

        context["plc_list"] = cnfController.objects.all().order_by("c_desc_controller").values_list(
            "id", "c_desc_controller"
        )
        context["plc_id"] = int(self.kwargs["plc_id"])
        context["all_count"] = self.kwargs.get("all_count")
        return context

    def get_queryset(self):
        if self.request.GET.get("plc_selector") is not None:
            if self.request.GET.get("plc_selector") != "":
                self.kwargs["plc_id"] = self.request.GET["plc_selector"]
                return get_modules_data_custom(
                    n_controller=self.request.GET["plc_selector"],
                )[0]

        queryset = get_modules_data_custom(n_controller=self.kwargs["plc_id"])
        self.kwargs["all_count"] = queryset[1]
        return queryset[0]

class ModuleCreateView(LoginRequiredMixin, ModuleMixin, ModuleAuthMixin, CreateView):
    """Создание модуля."""

    pk_url_kwarg = "plc_id"


    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["id"] = None
        kwargs["plc_id"] = int(self.kwargs["plc_id"])
        return kwargs

    def form_valid(self, form):

        setattr(form.instance, "c_user_edit", User.objects.get(username=self.request.user.username))
        setattr(form.instance, "d_last_edit", timezone.now())

        # получаем доп.данные с формы и отправляем в соответствующие таблицы cnfModuleValue
 
        if not form.is_valid():
            return super().form_invalid(form)

        form.save()  # Сначала сохраняем данные модуля из формы, чтобы FK таблицы значений было на что ссылаться при сохранении
        
        prep_data = []
        cw_word = []
        
        def set_prep_data_item(item):
            bit = None
            if item.__contains__("attr_"):
                name_attribute = item.replace("attr_", "")
            else:
                bit = int(item[6:8]) if item.startswith("attrb_") else None
                name_attribute = item.replace("attrb_", "")[2:]
            
            value = int(form.cleaned_data[item]) if form.cleaned_data[item] else 0
            
            if bit is not None:
                cw_word.append((bit, value))

            prep_data.append((
                value,
                cnfAttribute.objects.filter(n_global_object_type=GlobalObjectID.MODULE).get(c_name_attribute=name_attribute),
            ))
        for item in form.cleaned_data:
            if item.startswith("attr_") or item.startswith("attrb_"):
                set_prep_data_item(item)

        if cw_word:
            prep_data.append(
                (
                    get_int_from_bits(cw_word),
                    cnfAttribute.objects.filter(
                        n_global_object_type=GlobalObjectID.MODULE
                    ).get(c_name_attribute="CW"),
                )
            )

        records = [
            cnfModuleValue(
                n_module=form.instance,
                n_attribute=n_attribute,
                f_value=f_value,
                c_note="---",
            )
            for f_value, n_attribute in prep_data
        ]

        cnfModuleValue.objects.bulk_create(records)
        if self.request.POST.get("download_to_plc") == "on":
            self.RETURN_BLOCK_FROM_PLC = download_modules(
                plc_id=form.instance.n_controller.pk,
                min=form.instance.pk,
                max=form.instance.pk,
                ajax=False,
            )
            # ERRORS_FROM_PLC['return_block'] = {'r':444}
            if not self.RETURN_BLOCK_FROM_PLC.get("return_block"):
                self.RETURN_BLOCK_FROM_PLC["return_block"] = [
                    {
                        "error_num": "Модуль успешно загружен в ПЛК",
                        "index_num": "None",
                        "param_num": "None",
                    }
                ]
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            "modules:create_module", kwargs={"plc_id": self.kwargs["plc_id"]}
        )


class ModuleDetailView(LoginRequiredMixin, ModuleAuthMixin, DetailView):
    """Отображение детальной информации по выбранному модулю."""

    model = cnfModule
    template_name = "modules/detail.html"
    pk_url_kwarg = "module_id"

    def get_object(self, queryset=None):

        return get_object_or_404(
            cnfModule,
            pk=self.kwargs["module_id"],
        )


class ModuleUpdateView(LoginRequiredMixin, ModuleMixin, ModuleAuthMixin, UpdateView):
    """Редактирование информации по выбранному модулю."""

    RETURN_BLOCK_FROM_PLC = []
    pk_url_kwarg = "module_id"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["id"] = self.kwargs["module_id"]
        kwargs["plc_id"] = self.kwargs["plc_id"]

        return kwargs
    
    def dispatch(self, request, *args, **kwargs):
        user = User.objects.get(username=self.request.user.username)
        if not user.is_staff:
            return redirect('modules:module_home')
        return super().dispatch(request, *args, **kwargs)
    
    def get(self, request, *args, **kwargs):
        min = request.GET.get("min")
        max = request.GET.get("max")

        plc_id = self.kwargs["plc_id"]
        action = request.POST.get("action")

        self.kwargs["RETURN_BLOCK_FROM_PLC"] = self.request.session.get(
            "RETURN_BLOCK_FROM_PLC"
        )
        if self.request.session.get("RETURN_BLOCK_FROM_PLC"):
            self.request.session["RETURN_BLOCK_FROM_PLC"] = []

        if None not in [min, max, action]:
        # if not None in [min, max, action]:
            if action == CommandInterfaceConstants.ACTION_DOWNLOAD_TO_PLC:
                result_errors = download_modules(
                    request=request, plc_id=plc_id, min=min, max=max, ajax=False
                )
                self.kwargs["download_errors"] = result_errors

        return super(ModuleUpdateView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

    def get_success_url(self):
        if (
            self.RETURN_BLOCK_FROM_PLC
        ):  # and self.request.session.get('RETURN_BLOCK_FROM_PLC'):
            self.request.session["RETURN_BLOCK_FROM_PLC"] = self.RETURN_BLOCK_FROM_PLC[
                "return_block"
            ]
        # self.request.modified=True

        return reverse(
            "modules:module_edit",
            args=[self.kwargs["plc_id"], self.kwargs["module_id"]],
        )

    def form_valid(self, form):

        # user = User.objects.get(username=self.request.user.username)
        # if not user.is_staff:
        #     return redirect('accounts:login')
        setattr(form.instance, "c_user_edit", User.objects.get(username=self.request.user.username))
        setattr(form.instance, "d_last_edit", timezone.now())

        if self.request.session.get("RETURN_BLOCK_FROM_PLC"):
            self.request.session["RETURN_BLOCK_FROM_PLC"] = []
        form_module_index_bottom = self.request.POST.get('module_index')
        form_module_index_below = self.request.POST.get('module_index_below')
        form_module_index = None
        
        if not (form_module_index_bottom == str(form.cleaned_data.get('n_module_index'))):
            form_module_index = form_module_index_bottom
        if not (form_module_index_below == str(form.cleaned_data.get('n_module_index'))):
            form_module_index = form_module_index_below
            
        if form_module_index:
            if form_module_index.isdigit():
                # module = cnfModule.objects.get(n_module_index=form_module_index,n_controller=self.kwargs["plc_id"])
                modules = cnfModule.objects.filter(
                            n_module_index=form_module_index,
                            n_controller=self.kwargs["plc_id"]
                        )
                module = modules.first()
                return redirect(
            "modules:module_edit",
            plc_id=self.kwargs["plc_id"],
            module_id=module.id if module else self.kwargs["module_id"],
        )


        # получаем доп.данные с формы и отправляем в соответствующие таблицы cnfModuleValue
        if not form.is_valid():
            return super().form_invalid(form)
        form.save()  # Сначала сохраняем данные модуля из формы
        
        prep_data = []  # данные для таблицы значений для обновления
        prep_data_create = []  # данные для таблицы значений для создания
        cw_word = []  # список бит для составления int

        def set_prep_data_item(item):
            bit = None
            if item.__contains__("attr_"):
                name_attribute = item.replace("attr_", "")
            else:
                bit = int(item[6:8]) if item.startswith("attrb_") else None
                name_attribute = item.replace("attrb_", "")[2:]
            
            value = int(form.cleaned_data[item]) if form.cleaned_data[item] else 0
            
            if bit is not None:
                cw_word.append((bit, value))

            if form.value_id_by_order.get(name_attribute):
                prep_data.append((
                    form.value_id_by_order[name_attribute],
                    value,
                    cnfAttribute.objects.filter(n_global_object_type=GlobalObjectID.MODULE).get(c_name_attribute=name_attribute),
                ))
            else:
                prep_data_create.append((
                    value,
                    cnfAttribute.objects.filter(n_global_object_type=GlobalObjectID.MODULE).get(c_name_attribute=name_attribute),
                ))

        for item in form.cleaned_data:
            if item.startswith("attr_") or item.startswith("attrb_"):
                set_prep_data_item(item)

        if cw_word:
            if form.invisible_fields.get("CW"):
                prep_data.append(
                    (
                        form.invisible_fields.get("CW")[0],
                        get_int_from_bits(cw_word),
                        cnfAttribute.objects.filter(
                            n_global_object_type=GlobalObjectID.MODULE
                        ).get(c_name_attribute=form.invisible_fields.get("CW")[1]),
                    )
                )
            else:
                prep_data_create.append(
                    (
                        get_int_from_bits(cw_word),
                        cnfAttribute.objects.filter(
                            n_global_object_type=GlobalObjectID.MODULE
                        ).get(c_name_attribute="CW"),
                    )
                )
        records = [
            cnfModuleValue(
                idx,
                n_module=form.instance,
                n_attribute=n_attribute,
                f_value=f_value,
                c_note="---",
            )
            for idx, f_value, n_attribute in prep_data
        ]

        records_to_create = [
            cnfModuleValue(
                n_module=form.instance,
                n_attribute=n_attribute,
                f_value=f_value,
                c_note="---",
            )
            for f_value, n_attribute in prep_data_create
        ]

        cnfModuleValue.objects.bulk_update(records, ["f_value"])

        if records_to_create:
            cnfModuleValue.objects.bulk_create(records_to_create)

        if self.request.POST.get("download_to_plc") == "on":
            self.RETURN_BLOCK_FROM_PLC = download_modules(
                plc_id=form.instance.n_controller.pk,
                min=form.instance.pk,
                max=form.instance.pk,
                ajax=False,
            )

            if not self.RETURN_BLOCK_FROM_PLC.get("return_block"):
                if not self.RETURN_BLOCK_FROM_PLC.get("error_back"):
                    self.RETURN_BLOCK_FROM_PLC["return_block"] = [
                        {
                            "error_num": "Модуль успешно загружен в ПЛК",
                            "index_num": "None",
                            "param_num": "None",
                        }
                    ]
                else:
                    self.RETURN_BLOCK_FROM_PLC["return_block"]=self.RETURN_BLOCK_FROM_PLC.get("error_back")
        return super().form_valid(form)


class ModuleDeleteView(LoginRequiredMixin, ModuleAuthMixin, DeleteView):
    """Удаление выбранного модуля."""

    model = cnfModule
    template_name = "modules/create.html"
    pk_url_kwarg = "module_id"

    def dispatch(self, request, *args, **kwargs):
        user = User.objects.get(username=self.request.user.username)
        if not user.is_staff:
            return redirect('modules:module_home')
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse(
            "modules:module_home",
        )
def module_rec_last(request, plc_id, module_id):
    get_plc_data(plc_id)
    return HttpResponseRedirect(reverse(
            "modules:module_edit",
            args=[plc_id, module_id],
        ))

def download_modules(request=None, plc_id=None, min=None, max=None, ajax=True):

    return_block_errors = None
    DownloadToPLCInstance.clear()
    time_fix = timezone.now()

    if None in [min, max]:
        min = request.GET.get("min")
        max = request.GET.get("max")
        # action = request.GET.get("action")

    data = (
        cnfModuleValue.objects.filter(
            n_module__n_controller=plc_id, n_module__id__gte=min, n_module__id__lte=max
        )
        .exclude(n_attribute__n_parameter_id=0)
        .select_related("n_module", "n_attribute")
        .all()
        .order_by("n_module", "n_attribute__n_parameter_id")
    )
    if data:
        clean_data = get_module_data_to_plc(
            data, PlcCommandConstants.CMD_WRITE_MODULE_CONFIG
        )
        DownloadToPLCInstance.download_max_count = len(
            clean_data
        )  # передаем количество записываемых объектов
        return_block_errors = send_data_to_plc(
            plc_id, clean_data, GlobalObjectID.MODULE, DownloadToPLCInstance, True
        )

    else:
        print("Данные не найдены с индексами от", min, " до", max)

    # DownloadToPLCInstance.download_next(DownloadToPLCInstance.download_max_count)

    print(f"Время заливки: {(timezone.now()-time_fix).seconds} сек.")

    if ajax:
        response = {"error_back": return_block_errors}
        return JsonResponse(response)
    return {"error_back": return_block_errors}
    # return {"return_block": return_block_errors}

# def set_mask_to_config_words(cfg_word):
#     """Применение маски для полученного значения из ПЛК для конфигурационных слов."""

#     config_word = int(cfg_word)
#     # Сохраняем знак, но для битовых операций используем абсолютное значение
#     is_negative = config_word < 0
#     abs_value = abs(config_word)
    
#     # Для битовой маски используем абсолютное значение
#     config_word = abs_value & 0xFFFF if is_negative else config_word & 0xFFFF
#         # В слове разбираем только нужные биты
#     attr_CW_mask = []  # [0]*16
#     attr_CW_bit_info = [] 
#     for item_attr in cnfAttribute.objects.filter(
#         n_global_object_type=1,
#         n_attribute_type=AttributeFieldType.BOOLEAN_FIELD,
#         c_name_attribute__contains="CW.",
#     ).exclude(n_attr_display_order=0):
#         attr_CW_mask.append((item_attr.n_parameter_bit, 1))
#         attr_CW_bit_info.append((item_attr, item_attr.n_parameter_bit))
#     attr_CW_mask_int = get_int_from_bits(attr_CW_mask)
#     attr_CW_mask_int = attr_CW_mask_int & config_word

#     return attr_CW_mask_int, attr_CW_bit_info


def upload_module_save(plc_id, module_index, object_info, data) -> str:
    """Обновление данных модуля из ПЛК в БД."""
    # def get_or_create_module():
    #     """Получение или создание модуля."""
    #     module = cnfModule.objects.filter(
    #         n_module_index=module_index,
    #         n_controller=plc_id
    #     ).first()
        
    #     if not module:
    #         plc = cnfController.objects.get(id=plc_id)
    #         module = cnfModule.objects.create(
    #             n_module_index=module_index,
    #             c_name_module=f'Module {module_index}',
    #             c_desc_module=f'Module {module_index} description',
    #             n_controller=plc,
    #             c_user_edit=User.objects.first()
    #         )
    #     return module
    
    # def process_cw_attribute(attr, item_value, module, object_info_map, records, records_to_create):
    #     """Обработка атрибута CW (Config Word) с битовыми значениями."""
    #     item_value, attr_par_to_set = set_mask_to_config_words(item_value)
        
    #     for attr_info in attr_par_to_set:
    #         bit_value = 1 if (item_value >> attr_info[1]) & 1 else 0
    #         existing_id = object_info_map.get(attr_info[0].n_parameter_id)
            
    #         record_data = {
    #             'n_module': module,
    #             'n_attribute': attr_info[0],
    #             'f_value': bit_value,
    #             'c_note': "---"
    #         }
            
    #         if existing_id:
    #             records.append(cnfModuleValue(id=existing_id, **record_data))
    #         else:
    #             records_to_create.append(cnfModuleValue(**record_data))
    
    # def process_regular_attribute(item_key, item_value, attr, module, object_info_map, records, records_to_create):
    #     """Обработка обычного атрибута."""
    #     existing_id = object_info_map.get(item_key)
    #     record_data = {
    #         'n_module': module,
    #         'n_attribute': attr,
    #         'f_value': item_value,
    #         'c_note': "---"
    #     }
        
    #     if existing_id:
    #         records.append(cnfModuleValue(id=existing_id, **record_data))
    #     else:
    #         records_to_create.append(cnfModuleValue(**record_data))
    
    # # Получаем или создаем модуль
    # module = get_or_create_module()
    
    # # Создаем словарь существующих записей для быстрого поиска
    # object_info_map = {
    #     item.n_attribute.n_parameter_id: item.id 
    #     for item in object_info
    # } if object_info else {}
    
    # # Кэш для атрибутов, чтобы избежать повторных запросов к БД
    # attr_cache = {}
    
    # records = []
    # records_to_create = []
    
    # # Обрабатываем только ключи >= 5 (данные телеграммы)
    # for item_key, item_value in data[0].items():
    #     if item_key < 5:
    #         continue
            
    #     # Получаем атрибут из кэша или БД
    #     cache_key = (item_key, GlobalObjectID.MODULE)
    #     if cache_key not in attr_cache:
    #         attr_cache[cache_key] = cnfAttribute.objects.get(
    #             n_parameter_id=item_key,
    #             n_global_object_type=GlobalObjectID.MODULE
    #         )
    #     attr = attr_cache[cache_key]
        
    #     # Специальная обработка для CW атрибута
    #     if attr.c_name_attribute == "CW":
    #         process_cw_attribute(attr, item_value, module, object_info_map, records, records_to_create)
        
    #     # Обработка обычного атрибута
    #     process_regular_attribute(item_key, item_value, attr, module, object_info_map, records, records_to_create)
    
    # # Выполняем bulk операции
    # if records:
    #     cnfModuleValue.objects.bulk_update(records, ["f_value"])
    # if records_to_create:
    #     cnfModuleValue.objects.bulk_create(records_to_create)
    
    # return "Данные модуля обновлены."
    records = []
    records_to_create = []
    module = cnfModule.objects.filter(
                            n_module_index=module_index,
                            n_controller=plc_id
                        ).first()

    if not module:
        # next_index = cnfModule.objects.order_by('-n_module_index').first().n_module_index + 1
        user_editing = User.objects.first()
        plc = cnfController.objects.get(id=plc_id)
        module = cnfModule.objects.create(n_module_index=module_index,
                                          c_name_module=f'Module {module_index}',
                                          c_desc_module=f'Module {module_index} description',
                                          n_controller=plc,
                                          c_user_edit=user_editing)
        # module.save
    # Если модуль не существует в БД
        for item_key, item_value in data[0].items():
            if item_key >= 5:
                attr = cnfAttribute.objects.get(n_parameter_id=item_key,n_global_object_type=GlobalObjectID.MODULE)
                if attr.c_name_attribute == "CW":
                    item_value, attr_par_to_set = set_mask_to_config_words(item_value,GlobalObjectID.MODULE, 'CW')
                    # Сохраняем отдельно биты
                    for attr_info in attr_par_to_set:
                        records_to_create.append(cnfModuleValue(
                            n_module=module,
                            n_attribute=attr_info[0],
                            f_value=1 if (1 & item_value >> attr_info[1]) == 1 else 0,
                            c_note="---",
                        ))

                records_to_create.append(cnfModuleValue(
                    n_module=module,
                    n_attribute=cnfAttribute.objects.get(n_parameter_id=item_key,n_global_object_type=GlobalObjectID.MODULE),
                    f_value=item_value,
                    c_note="---",
                ))
        # cnfModuleValue.objects.bulk_create(records_to_create)
    else:
        
        module_info_bits = (
                    cnfModuleValue.objects.select_related("n_module", "n_attribute")
                    .filter(
                        n_attribute__n_parameter_id=0,
                        n_module__n_module_index=module_index,
                        n_module__n_controller_id=plc_id,
                    )
                )
        for item_key, item_value in data[0].items():
            if item_key >= 5:  # До 5 индекса - это данные по телеграмме
                attr = cnfAttribute.objects.get(n_parameter_id=item_key,n_global_object_type=GlobalObjectID.MODULE)
                if attr.c_name_attribute == "CW":
                    item_value, attr_par_to_set = set_mask_to_config_words(item_value,GlobalObjectID.MODULE, 'CW')
                    # Сохраняем отдельно биты
                    for attr_info in attr_par_to_set:
                        item_id = None
                        for item_info in module_info_bits:
                            if item_info.n_attribute_id == attr_info[0].id:
                                item_id = item_info.id
                                break
                        if item_id:
                            records.append(
                                    cnfModuleValue(
                                        item_id,
                                        n_module=module,
                                        n_attribute=attr_info[0],
                                        f_value= 1 if (1 & item_value >> attr_info[1]) == 1 else 0,
                                        c_note="---",
                                    ))
                        else:
                            records_to_create.append(cnfModuleValue(
                                n_module=module,
                                n_attribute=attr_info[0],
                                f_value=1 if (1 & item_value >> attr_info[1]) == 1 else 0,
                                c_note="---",
                            ))


                if not object_info:
                    records_to_create.append(cnfModuleValue(
                        n_module=module,
                        n_attribute=attr,
                        f_value=item_value,
                        c_note="---",
                    ))
                else:
                    item_found = False
                    for item in object_info:
                        if item.n_attribute.n_parameter_id == item_key:
                            item_found = True
                            records.append(
                                    cnfModuleValue(
                                        item.id,
                                        n_module=module,
                                        n_attribute=attr,
                                        f_value=item_value,
                                        c_note="---",
                                    ))
                            break
                    if not item_found:
                        records_to_create.append(cnfModuleValue(
                            n_module=module,
                            n_attribute=attr,
                            f_value=item_value,
                            c_note="---",
                        ))
                  

            else:
                pass
     
    if records:
        cnfModuleValue.objects.bulk_update(records, ["f_value"])
    if records_to_create:
        cnfModuleValue.objects.bulk_create(records_to_create)
    
    return "Данные модуля обновлены."
    


def upload_modules(request, plc_id, min=None, max=None, ajax=True):

    # return_block_errors = None
    DownloadToPLCInstance.clear()
    # time_fix = timezone.now()

    if None in [min, max]:
        min = int(request.GET.get("min"))
        max = int(request.GET.get("max"))
        # action = request.GET.get("action")
    action = request.GET.get("action")
    # if action == 'upload_save':
    #     return JsonResponse({"return_block": ["Кнопка не работает!"]})
    if min == max:  # Отправлено из редактирования модуля
        m_index = cnfModule.objects.get(id=min).n_module_index
        max = m_index
        min = m_index
    else:
        m_index = min  #начинается с 1-го индекса (не id)

    for module_index in range(m_index, max+1):
        clean_data = {
            min: [
                [1, 3],
                [2, PlcCommandConstants.CMD_READ_MODULE_CONFIG],
                [3, module_index],
            ]
        }
        
        return_block = send_data_to_plc(
            plc_id, clean_data, GlobalObjectID.MODULE, None, False, action if action else None
        )  # DownloadToPLCInstance)
        data_mismatch = []
        if ajax:
            # response = {"return_block": return_block}
            # if isinstance(return_block, dict) and return_block.get("error_num"):
            if isinstance(return_block, list) and return_block[0].get("error_num"):
                data_mismatch.append(return_block[0].get("error_num"))
                break
            elif not return_block:
                data_mismatch.append("Нет ответа от ПЛК!")
            else:
                
                object_info = (
                    cnfModuleValue.objects.select_related("n_module", "n_attribute")
                    .exclude(n_attribute__n_parameter_id=0)
                    .filter(
                        n_module__n_module_index=return_block[0].get(3),
                        n_module__n_controller_id=plc_id,
                    )
                )
                if action == "upload_save":
                    data_mismatch.append(upload_module_save(plc_id, module_index, object_info, return_block))
                    if min == max:
                        return JsonResponse({"return_block": data_mismatch})
                if object_info:
                    for item in object_info:
                        if item.n_attribute.c_name_attribute == "CW":
                            # В слове разбираем только нужные биты
                            attr_CW_mask = []  # [0]*16
                            for item_attr in cnfAttribute.objects.filter(
                                n_global_object_type=1,
                                n_attribute_type=AttributeFieldType.BOOLEAN_FIELD,
                                c_name_attribute__contains="CW.",
                            ).exclude(n_attr_display_order=0):
                                attr_CW_mask.append((item_attr.n_parameter_bit, 1))
                            attr_CW_mask_int = get_int_from_bits(attr_CW_mask)

                            config_word = int(return_block[0].get(item.n_attribute.n_parameter_id))
                            # Для битовой маски используем абсолютное значение
                            config_word = abs(config_word) & 0xFFFF if config_word < 0 else config_word & 0xFFFF
                            attr_CW_mask_int = attr_CW_mask_int & config_word


                            # attr_CW_mask_int = attr_CW_mask_int & int(
                            #     return_block[0].get(item.n_attribute.n_parameter_id)
                            # )
                            if item.f_value != attr_CW_mask_int:
                                data_mismatch.append(
                                    f"{item.n_attribute.c_display_attribute}: {int(item.f_value)} :  {attr_CW_mask_int}"
                                )
                        else:
                            if item.f_value != return_block[0].get(
                                item.n_attribute.n_parameter_id
                            ):
                                data_mismatch.append(
                                    f"{item.n_attribute.c_display_attribute}: БД[{item.f_value}], ПЛК[{return_block[0].get(item.n_attribute.n_parameter_id)}]"
                                )
                else:
                    data_mismatch.append(
                                    " Все позиции БД и ПЛК"
                                )
            if min == max:
                return JsonResponse({"return_block": data_mismatch})
        if min == max:
            return {"return_block": return_block}
    # return JsonResponse({"return_block": data_mismatch})
    return HttpResponseRedirect(reverse("modules:module_by_plc", kwargs={"plc_id": plc_id}))

def check_state(request):

    download_count = DownloadToPLCInstance.percent_num

    return JsonResponse({"progress": download_count})
    # return JsonResponse({'progress': DownloadToPLCInstance.download_count})


def modbus(request):  # request):
    # Read DB data

    # data = (
    #     cnfModuleValue.objects.select_related("n_module", "n_attribute")
    #     .all()
    #     .order_by("n_module", "n_attribute")
    # )
    # clean_data = get_module_data_to_plc(
    #     data, PlcCommandConstants.CMD_WRITE_MODULE_CONFIG
    # )

    return HttpResponseRedirect(reverse("modules:module_by_plc", kwargs={"plc_id": 1}))
