from itertools import chain

from django.db.models import Q
from variables.models import cnfVariable

from iriusconfig.constants import (AttributeFieldType,
                                   CommandInterfaceConstants,
                                   EquipmentTypeConstants, FieldMainTable,
                                   PlcCommandConstants)

from .models import (cnfEquipment, cnfEquipmentLinkedWord, cnfEquipmentValue,
                     cnfSequenceLinkedEquipment, cnfSequenceLinkedVariable)


def get_equipments_data_custom(**kwargs):
    """Выборка данных из таблицы переменных с дополнительным фильтром."""
    queryset = (
        cnfEquipment.objects.select_related(
            "n_controller",
        )
        .filter(**kwargs)
        .order_by("n_equipment_index")
    )
    return (queryset, queryset.count())


def get_equipments_data_custom_filter(plc_id, filter_value):
    """Выборка данных из таблицы переменных с дополнительным фильтром."""
    queryset = (
        cnfEquipment.objects.select_related(
            "n_controller",
        )
        .filter(
            Q(n_controller=plc_id)
            & (
                Q(c_name_equipment__icontains=filter_value)
                | Q(c_desc_equipment__icontains=filter_value)
            )
        )
        .order_by("n_equipment_index")
    )
    return (queryset, queryset.count())


def get_equipments_extra_data(**kwargs):
    """Выборка всех данных по определенной переменной."""
    return cnfEquipmentValue.objects.select_related(
        "n_equipment",
    ).filter(**kwargs)


# def download_equipments_to_plc():
#     pass
#     '''
#     1 - простой агрегат
#     2 - роли переменных, роли агрегатов
#     3 - переменные ПИД
#     4 - Последовательности
#     4.1 - старт
#     4.2 - быстрый старт
#     4.3 - останов
#     4.4 - авар.останов
#     .'''


def get_data_linked_words(data):
    """Подготовка данных для вордов в формате:
    {<object_id>:[QueryObject,]}
    ."""
    words = {}
    for item in data:
        if not words.get(item.n_equipment_id):
            words[item.n_equipment_id] = {item.n_bit: item}
        else:
            words[item.n_equipment_id].update({item.n_bit: item})

    return words


def get_data_linked_roles(data):
    """Подготовка данных для вордов в формате:
    {<object_id>:{<role_id>:[[QueryObject,]]}
    ."""
    linked_dict = {}
    i = 0 # добавлено
    for item in data:
        # linked_dict[item.n_equipment_id] = {i:[[item.n_role.n_role_index, item]]}# добавлено
        
        if not linked_dict.get(item.n_equipment_id):
            linked_dict[item.n_equipment_id] = {i:[item.n_role.n_role_index, item]}
        else:
            if linked_dict[item.n_equipment_id].get(i):
                linked_dict[item.n_equipment_id][i].append(
                   item.n_role.n_role_index, item
                )
            else:
                linked_dict[item.n_equipment_id][i] = [item.n_role.n_role_index, item]
        i += 1# добавлено
        
        # if not linked_dict.get(item.n_equipment_id):
        #     linked_dict[item.n_equipment_id] = {item.n_role.n_role_index: [[item]]}
        # else:
        #     if linked_dict[item.n_equipment_id].get(item.n_role.n_role_index):
        #         linked_dict[item.n_equipment_id][item.n_role.n_role_index].append(
        #             [item]
        #         )
        #     else:
        #         linked_dict[item.n_equipment_id][item.n_role.n_role_index] = [[item]]
    return linked_dict


def get_data_linked_seq_roles(eq_id, eq_index, data_var, data_eq):
    """Только для последовательностей
    Подготовка данных для вордов в формате:
    {<object_id>:{<role_id>:[[QueryObject,]]}
    ."""
    commands = {
        1: PlcCommandConstants.CMD_WRITE_EQUIPMENT_SEQ1_CONFIG,
        2: PlcCommandConstants.CMD_WRITE_EQUIPMENT_SEQ2_CONFIG,
        3: PlcCommandConstants.CMD_WRITE_EQUIPMENT_SEQ3_CONFIG,
        4: PlcCommandConstants.CMD_WRITE_EQUIPMENT_SEQ4_CONFIG,
    }
    seq_type_dict = {}
    # сначала нужно объединить данные
    # [{}]

    union_list = list(chain(data_var, data_eq))
    # Выписываем по типу последовательности
    for item in union_list:
        if item.n_equipment_id == eq_id:
            if not seq_type_dict.get(item.n_seq_type):
                seq_type_dict[item.n_seq_type] = [
                    None
                ] * EquipmentTypeConstants.TYPE_EQ14_MAX_STEPS
            multiplier = -1 if item.b_masked else 1
            # print(item.n_step)
            seq_type_dict[item.n_seq_type][item.n_step - 1] = [
                item.n_role_id,
                item.n_timer,
                multiplier
                * (
                    item.n_variable_link.n_variable_index
                    if isinstance(item, cnfSequenceLinkedVariable)
                    else item.n_equipment_link.n_equipment_index
                ),
            ]

    param_list = {}

    for seq_type, data_steps in seq_type_dict.items():
        if not param_list.get(f"{eq_id}seq{seq_type}"):
            param_list[f"{eq_id}seq{seq_type}"] = [
                [2, commands[seq_type]],
                [3, eq_index],
            ]
        nn = 5
        for row in data_steps:
            if row:
                param_list[f"{eq_id}seq{seq_type}"].extend(
                    [[nn, row[0]], [nn + 1, row[1]], [nn + 2, row[2]]]
                )
                nn += 3
        param_list[f"{eq_id}seq{seq_type}"].insert(
            0, [1, len(param_list[f"{eq_id}seq{seq_type}"]) + 1]
        )

    return param_list


def get_param_list_linked_roles(
    eq_id, eq_index, linked_roles, suffix_str: str, command
):
    """Подготовка данных для param_list."""
    param_list = {}
    data = linked_roles.get(eq_id)
    # for item_eq_id, item_val in linked_roles.items():
    if not param_list.get(f"{eq_id}{suffix_str}"):

        param_list[f"{eq_id}{suffix_str}"] = [[2, command], [3, eq_index]]

    if data:
        nn_value = 5

        # for item_role_id, item_list in data.items():
        #     for role_row in item_list:
        for item_role_id, role_row in data.values(): #'items():
            # for role_row in item_list:                
                # s_timer = locals()['role_row[0].n_timer']
                # n_id = locals()['role_row[0].n_variable_id']

            param_list[f"{eq_id}{suffix_str}"].append([nn_value, item_role_id])
            param_list[f"{eq_id}{suffix_str}"].append(
                [nn_value + 1, role_row.n_timer]
            )

            multiplier = -1 if role_row.b_masked else 1
            if suffix_str == "var":
                param_list[f"{eq_id}{suffix_str}"].append(
                    [
                        nn_value + 2,
                        multiplier * role_row.n_variable.n_variable_index,
                    ]
                )
            elif suffix_str == "pid_var":
                param_list[f"{eq_id}{suffix_str}"].append(
                    [
                        nn_value + 2,
                        multiplier * role_row.n_variable_link.n_variable_index,
                    ]
                )
            else:  # suffix_str == 'eq':
                param_list[f"{eq_id}{suffix_str}"].append(
                    [
                        nn_value + 2,
                        multiplier * role_row.n_equipment_link.n_equipment_index,
                    ]
                )
            nn_value += 3
        param_list[f"{eq_id}{suffix_str}"].insert(
            0, [1, len(param_list[f"{eq_id}{suffix_str}"]) + 1]
        )
    # raise Exception('er')
    return param_list


def get_equipment_data_to_plc(data, command, **kwargs):
    """
    Формирование телеграммы для отправки в ПЛК по формату:
    NN      Val
    1       длина телеграммы
    2       команда для ПЛК
    3       индекс оборудования
    4..   параметры конфигурации
    .
    """

    # raise Exception('err')
    param_list = {}
    n_equipment = None
    # Ищем типы всего оборудования
    eq_types = {
        item.pk: item.n_type_id
        for item in cnfEquipment.objects.all().select_related("n_type_id")
    }
    eq_linked_status_words = {}
    eq_linked_control_words = {}
    eq_linked_var = {}
    eq_linked_eq = {}
    eq_linked_pid_var = {}
    if kwargs.get("data_sw"):
        eq_linked_status_words = get_data_linked_words(kwargs["data_sw"])

    if kwargs.get("data_cw"):
        eq_linked_control_words = get_data_linked_words(kwargs["data_cw"])
    # Готовим данные для дальнейшей работы с ними по индексу оборудования
    if kwargs.get("data_linked_var"):
        eq_linked_var = get_data_linked_roles(kwargs["data_linked_var"])
    if kwargs.get("data_linked_eq"):
        eq_linked_eq = get_data_linked_roles(kwargs["data_linked_eq"])
    if kwargs.get("data_linked_pid_var"):
        eq_linked_pid_var = get_data_linked_roles(kwargs["data_linked_pid_var"])

    # raise Exception('er')
    for equipment_item in data:

        if n_equipment != equipment_item.n_equipment_id:
            eq_id = equipment_item.n_equipment_id
            eq_index = equipment_item.n_equipment.n_equipment_index
            param_list[eq_id] = [
                [2, command],
                [
                    3,
                    (
                        eq_index
                        if not equipment_item.n_equipment.b_masked
                        else (-1) * eq_index
                    ),
                ],
            ]
            # raise Exception("er")
            # Добавляем тип оборудования

            param_list[eq_id].append(
                [FieldMainTable.EQ_FIELD_TYPE, eq_types[eq_id].n_type_value]
            )

            # Биты слов состояния и управления
            if equipment_item.n_equipment_id in eq_linked_status_words.keys():
                # Сначала добавляем переменную
                param_list[eq_id].extend(
                    [
                        [
                            FieldMainTable.EQ_FIELD_SW_INDEX,
                            eq_linked_status_words[eq_id][0].n_variable_id,
                        ]
                    ]
                )
                # Записываем биты
                for index in range(16):
                    val = 0
                    if eq_linked_status_words.get(index):
                        val = eq_linked_status_words[index].n_role_id
                    param_list[eq_id].extend(
                        [[FieldMainTable.EQ_FIELD_SW_BITS_START_INDEX + index, val]]
                    )
            if equipment_item.n_equipment_id in eq_linked_control_words.keys():
                # Сначала добавляем переменную
                param_list[eq_id].extend(
                    [
                        [
                            FieldMainTable.EQ_FIELD_CW_INDEX,
                            eq_linked_control_words[eq_id][0].n_variable_id,
                        ]
                    ]
                )
                # Записываем биты
                for index in range(0, 16):
                    val = 0
                    if eq_linked_control_words.get(index):
                        val = eq_linked_control_words[index].n_role_id
                    param_list[eq_id].extend(
                        [[FieldMainTable.EQ_FIELD_CW_BITS_START_INDEX + index, val]]
                    )
            # Здесь добавляем роли переменных, оборудования, пид-переменных,
            # чтобы для обрабатываемого индекса последовательно шли посылки с ролями
            if eq_linked_var:

                param_list.update(
                    get_param_list_linked_roles(
                        eq_id,
                        eq_index,
                        eq_linked_var,
                        "var",
                        PlcCommandConstants.CMD_WRITE_EQUIPMENT_LINKED_VAR_CONFIG,
                    )
                )

            if eq_linked_eq:
                param_list.update(
                    get_param_list_linked_roles(
                        eq_id,
                        eq_index,
                        eq_linked_eq,
                        "eq",
                        PlcCommandConstants.CMD_WRITE_EQUIPMENT_LINKED_EQ_CONFIG,
                    )
                )

            if eq_linked_pid_var:
                param_list.update(
                    get_param_list_linked_roles(
                        eq_id,
                        eq_index,
                        eq_linked_pid_var,
                        "pid_var",
                        PlcCommandConstants.CMD_WRITE_EQUIPMENT_LINKED_PID_VAR_CONFIG,
                    )
                )

            if kwargs.get("data_linked_seq_var") or kwargs.get("data_linked_seq_eq"):
                param_list.update(
                    get_data_linked_seq_roles(
                        eq_id,
                        eq_index,
                        kwargs["data_linked_seq_var"],
                        kwargs["data_linked_seq_eq"],
                    )
                )

            if n_equipment is not None:
                param_list[n_equipment].insert(0, [1, len(param_list[n_equipment]) + 1])

            n_equipment = equipment_item.n_equipment_id

        if equipment_item.n_attribute.n_attribute_type not in [
            AttributeFieldType.BOOLEAN_FIELD,
            AttributeFieldType.TEXT_FIELD,
        ]:
            param_list[equipment_item.n_equipment_id].extend(
                [
                    [
                        equipment_item.n_attribute.n_parameter_id,
                        float(equipment_item.f_value),
                    ]
                ]
            )
    else:
        param_list[n_equipment].insert(0, [1, len(param_list[n_equipment]) + 1])

    # print(len(param_list))
    # param_list[n_equipment].insert(0,[1, len(param_list[n_equipment])+1])

    # !!!!!!  Нужно поднять это вверх, т.к. данные должны писать сразу после записи простого агрегата
    # if kwargs.get('data_linked_var'):
    #     eq_linked_var = get_data_linked_roles(kwargs['data_linked_var'])
    #     param_list.update(get_param_list_linked_roles(eq_linked_var,'var', PlcCommandConstants.CMD_WRITE_EQUIPMENT_LINKED_VAR_CONFIG))
    #     # for item_eq_id, item_val in eq_linked_var.items():
    #     #     if not param_list.get(f'{item_eq_id}var'):
    #     #         param_list[f'{item_eq_id}var'] = [[2, PlcCommandConstants.CMD_WRITE_EQUIPMENT_LINKED_VAR_CONFIG],
    #     #                                 [3,item_eq_id]]
    #     #     nn_value = 5
    #     #     for item_role_id, list_var in item_val.items():
    #     #         for role_row in list_var:
    #     #             param_list[f'{item_eq_id}var'].append([nn_value, item_role_id])
    #     #             param_list[f'{item_eq_id}var'].append([nn_value+1, role_row[0].n_timer])
    #     #             param_list[f'{item_eq_id}var'].append([nn_value+2, role_row[0].n_variable_id])
    #     #             nn_value += 3
    #     # param_list[f'{item_eq_id}var'].insert(0,[1, len(param_list[f'{item_eq_id}var'])+1])

    # if kwargs.get('data_linked_eq'):
    #     eq_linked_eq = get_data_linked_roles(kwargs['data_linked_eq'])
    #     param_list.update(get_param_list_linked_roles(eq_linked_eq,'eq', PlcCommandConstants.CMD_WRITE_EQUIPMENT_LINKED_EQ_CONFIG))
    # if kwargs.get('data_linked_pid_var'):
    #     eq_linked_pid_var = get_data_linked_roles(kwargs['data_linked_pid_var'])
    #     param_list.update(get_param_list_linked_roles(eq_linked_pid_var,'pid_var', PlcCommandConstants.CMD_WRITE_EQUIPMENT_LINKED_PID_VAR_CONFIG))

    # raise Exception('err')
    return param_list
