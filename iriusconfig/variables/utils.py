from django.db import connection
from django.db.models import Case, CharField, F, Max, Q, Value, When
from django.db.models.functions import Concat
from django.forms import FloatField
from modules.models import cnfModuleValue

from iriusconfig.constants import AttributeFieldType, FieldMainTable

from .models import cnfFormulaSymbol, cnfVariable, cnfVariableValue


def get_variables_data_custom(**kwargs):
    """Выборка данных из таблицы переменных с дополнительным фильтром."""
    queryset = (
        cnfVariable.objects.select_related(
            "n_controller",
        )
        .filter(**kwargs)
        .order_by("n_variable_index")
    )
    return (queryset, queryset.count())


def get_variables_data_custom_filter1(plc_id, filter_value):
    """Выборка данных из таблицы переменных с дополнительным фильтром."""
    filter_index, filter = filter_value
    if filter_index != "" and filter != "":
        queryset = (
            cnfVariable.objects.select_related(
                "n_controller",
            )
            .filter(
                Q(n_controller=plc_id)
                & (
                    Q(c_name_variable__icontains=filter)
                    | Q(
                        c_desc_variable__icontains=filter
                        | Q(c_signal_ident__icontains=filter)
                    )
                    or Q(n_variable_index__icontains=filter_index)
                )
            )
            .order_by("n_variable_index")
        )
    else:
        flt = (
            Q(n_controller=plc_id)
            & (
                Q(c_name_variable__icontains=filter)
                | Q(c_desc_variable__icontains=filter)
                | Q(c_signal_ident__icontains=filter)
            )
            if filter != ""
            else Q(n_controller=plc_id) & (Q(n_variable_index__icontains=filter_index))
        )
        queryset = (
            cnfVariable.objects.select_related(
                "n_controller",
            )
            .filter(flt)
            .order_by("n_variable_index")
        )
    return (queryset, queryset.count())


def get_variables_extra_data(**kwargs):
    """Выборка всех данных по определенной переменной."""
    return cnfVariableValue.objects.select_related(
        "n_variable",
    ).filter(**kwargs)


def get_variables_data_custom_filter(plc_id, filter_value=None):
    filter_clause = ""
    if filter_value:
        filter_index, filter, filter_cvv, filter_module, filter_channel = filter_value

        if filter_index and filter_index != "":
            filter_clause = (
                f" and CAST(vc.n_variable_index AS TEXT) LIKE '%%{filter_index}%%' "
            )
        if filter and filter != "":
            filter_clause += f" and (vc.c_name_variable ilike '%%{filter}%%' or vc.c_desc_variable ilike '%%{filter}%%' or vc.c_signal_ident ilike '%%{filter}%%') "

    raw_sql = f"""
               select vc.id, vc.n_variable_index , vc.c_name_variable , vc.c_desc_variable, vc.c_signal_ident,
                    MAX(CASE WHEN gc.c_name_attribute = 'SlotID' THEN mc2.f_value END) AS SlotID,
                    MAX(CASE WHEN gc.c_name_attribute = 'StationID' THEN mc2.f_value END) AS StationID,
                    vc.n_module_channel 
            from variables_cnfvariable vc
            left join modules_cnfmodule mc on mc.id = vc.n_module_id_id
            left join modules_cnfmodulevalue mc2 on mc2.n_module_id = mc.id
            left join general_cnfattribute gc on gc.id = mc2.n_attribute_id
            where vc.n_controller_id = {plc_id}
            {filter_clause}
            group by vc.id, vc.n_variable_index , vc.c_name_variable, vc.c_desc_variable, vc.c_signal_ident, vc.n_module_channel
            order by vc.n_variable_index
    """
    if filter_value:
        filter_clause = ""
        if filter_cvv and filter_cvv != '':
            filter_clause += f" tbl.stationid = {filter_cvv} and "
                
        if filter_module and filter_module != '':
            filter_clause += f" tbl.slotid = {filter_module} and "
                
        if filter_channel and filter_channel != '':
            filter_clause += f" tbl.n_module_channel = {filter_channel} and "

        if filter_clause:
            raw_sql = f" select * from ({raw_sql}) tbl where {filter_clause[:-5]};"

    queryset = cnfVariable.objects.raw(raw_sql)

    return (queryset, len(list(queryset)))


def download_variables_to_plc():
    pass


def get_formula_data(data):  # , symbols):
    """
    Формирование посылки для формулы
    """
    formulas_symbol_type_values = {
        items["c_symbol"]: items["n_chr"]
        for items in cnfFormulaSymbol.objects.all().values("n_chr", "c_symbol")
    }
    parameter_parsed = []
    for raw_symbol in data:
        parameter_parsed.append(formulas_symbol_type_values.get(raw_symbol))
        # parameter_parsed.append(symbols.get(raw_symbol))
    return parameter_parsed


def set_formula_to_param_list(
    param_list, variable_item, n_variable, items_parsed, command
):
    # Формируем сначала заголовок для формулы, затем тело, потом считаем длиину
    param_list[f"{variable_item.n_variable_id}f"] = [
        [2, command + 1],
        [3, variable_item.n_variable.n_variable_index],
    ]
    for idx, item_value in enumerate(items_parsed[n_variable]):
        # print(idx,item_value)
        param_list[f"{variable_item.n_variable_id}f"].extend(
            [[idx + 4, float(item_value)]]
        )
    param_list[f"{variable_item.n_variable_id}f"].insert(
        0, [1, len(param_list[f"{variable_item.n_variable_id}f"]) + 1]
    )
    # return param_list


def get_variable_data_to_plc(data, data_formulas, command):
    """
    Формирование телеграммы для отправки в ПЛК по формату:
    NN      Val
    1       длина телеграммы
    2       команда для ПЛК
    3       индекс переменной
    4..13   параметры конфигурации
    .
    """

    items_parsed = {}
    for item in data_formulas:
        items_parsed[item.n_variable_id] = get_formula_data(
            item.c_formula.replace(" ", "")
        )  # , formulas_symbol_type_values);

    param_list = {}
    errors = []
    var_index = 0

    n_variable = None
    try:
        for variable_item in data:
            var_index = variable_item.n_variable.n_variable_index
            var_id = variable_item.n_variable_id
            if n_variable != var_id:
                param_list[var_id] = [
                    [2, command],
                    [
                        3,
                        (
                            variable_item.n_variable.n_variable_index
                            if not variable_item.n_variable.b_masked
                            else (-1) * variable_item.n_variable.n_variable_index
                        ),
                    ],
                ]
                # print(variable_item.n_variable.n_variable_index)
                # Добавляем тип переменной и тип данных
                param_list[var_id].append(
                    [
                        FieldMainTable.VAR_FIELD_TYPE,
                        variable_item.n_variable.n_variable_type.n_type_value,
                    ]
                )
                # Добавляем номер канала
                if variable_item.n_variable.n_module_channel:
                    param_list[var_id].append(
                        [
                            FieldMainTable.VAR_FIELD_CHANNEL,
                            variable_item.n_variable.n_module_channel,
                        ]
                    )
                param_list[var_id].append(
                    [
                        FieldMainTable.VAR_FIELD_DATA_TYPE,
                        variable_item.n_variable.n_variable_data_type.n_type_value,
                    ]
                )

                if variable_item.n_variable.n_module_id:
                    param_list[var_id].append(
                        [
                            FieldMainTable.VAR_FIELD_MODULE,
                            variable_item.n_variable.n_module_id.n_module_index,
                        ]
                    )

                if n_variable is not None:
                    param_list[n_variable].insert(
                        0, [1, len(param_list[n_variable]) + 1]
                    )

                    if items_parsed.get(n_variable):
                        set_formula_to_param_list(
                            param_list,
                            variable_item,
                            n_variable,
                            items_parsed,
                            command,
                        )
                        # Формируем сначала заголовок для формулы,
                        # затем тело, потом считаем длиину

                n_variable = var_id

            if variable_item.n_attribute.n_attribute_type not in [
                AttributeFieldType.BOOLEAN_FIELD,
                AttributeFieldType.TEXT_FIELD,
            ]:
                param_list[var_id].extend(
                    [
                        [
                            variable_item.n_attribute.n_parameter_id,
                            float(variable_item.f_value),
                        ]
                    ]
                )
        else:
            param_list[n_variable].insert(0, [1, len(param_list[n_variable]) + 1])
            if items_parsed.get(n_variable):
                set_formula_to_param_list(
                    param_list, variable_item, n_variable, items_parsed, command
                )
    except Exception as error:
        errors = [
            {
                "error_num": f"Ошибка в конфигурации переменной с индексом {var_index}",
                "index_num": "",
                "param_num": "",
            }
        ]

    return param_list, errors


# def get_variable_list_by_pmc():

#     subquery1 = cnfModuleValue.objects.filter(
#     n_attribute__c_name_attribute__in=['StationID', 'SlotID']
#     ).values(
#     'n_module__n_module_index_index',
#     # 'n_variable__c_name_variable',
#     # 'n_variable__c_desc_variable',
#     # 'n_variable__c_signal_ident',
#     # 'n_variable__n_module_channel'
#     ).annotate(
#     StationID=Max(F('f_value'), filter=Q(n_attribute_id__c_name_attribute='StationID')),
#     SlotID=Max(F('f_value'), filter=Q(n_attribute_id__c_name_attribute='SlotID'))
#     )


#     subquery2 = cnfVariable.objects.prefetch_related(Prefetch("n_module_id", queryset=subquery1)).values(
#     'n_variable_index',
#     'c_name_variable',
#     'c_desc_variable',
#     'c_signal_ident',
#     'n_module_channel'
#     ).annotate(
#     StationID=Max(F('f_value'), filter=Q(n_module_id__n_attribute_id__c_name_attribute='StationID')),
#     SlotID=Max(F('f_value'), filter=Q(n_module_id__n_attribute_id__c_name_attribute='SlotID'))
#     )

#     quer = 1
#     # subquery2 = cnfVariable.objects.select_related('n_module_id').filter(
#     # n_module_id__n_attribute__c_name_attribute__in=['StationID', 'SlotID']
#     # ).values(
#     # 'n_variable_index',
#     # 'c_name_variable',
#     # 'c_desc_variable',
#     # 'c_signal_ident',
#     # 'n_module_channel'
#     # ).annotate(
#     # StationID=Max(F('f_value'), filter=Q(n_module_id__n_attribute_id__c_name_attribute='StationID')),
#     # SlotID=Max(F('f_value'), filter=Q(n_module_id__n_attribute_id__c_name_attribute='SlotID'))
#     # )


#     return queryset
