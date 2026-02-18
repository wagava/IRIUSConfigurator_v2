import struct
import time
from dataclasses import dataclass

# from services.mb_client import SelfModbusTcpClient
from iriusconfig.constants import AttributeFieldType
from .models import cnfModule, cnfModuleDataType, cnfModuleType, cnfModuleValue

DW_CNT = 0
# client = SelfModbusTcpClient("192.168.222.22", 502)


def get_module_types() -> dict:
    """Выборка типов данных и типов модулей."""
    module_types = []
    module_data_types = []

    for item in list(cnfModuleType.objects.all()):
        module_types.append((item.id, item.c_type_desc))
    for item in list(cnfModuleDataType.objects.all()):
        module_data_types.append((item.id, item.c_type_desc))
    return {
        "module_types": module_types,
        "module_data_types": module_data_types,
    }


def get_modules_data_custom(**kwargs):
    """Выборка данных из таблицы модулей с дополнительным фильтром."""
    return cnfModule.objects.select_related(
        "c_user_edit",
        "n_controller",
    ).filter(**kwargs)


def get_module_extra_data(**kwargs):
    """Выборка всех данных по определенному модулю."""
    return cnfModuleValue.objects.select_related(
        "n_module",
    ).filter(**kwargs)


def download_modules_to_plc():
    global DW_CNT
    for item in range(10):
        DW_CNT += 1
        time.sleep(1)
    DW_CNT = 0


@dataclass
class DownloadToPLC:
    download_count: int = -1
    download_max_count: int = 0

    percent_num: int = 0

    def clear(self):
        self.download_count = 0
        self.download_max_count = 0
        self.percent_num = 0

    def download_next(self, next_value):  # len_num = None):
        if self.download_max_count != 0:
            self.percent_num += round((next_value * 100) / self.download_max_count, 0)
            self.percent_num = self.percent_num if self.percent_num <= 100 else 100


def get_module_data_to_plc(data, command):
    """
    Формирование телеграммы для отправки в ПЛК по формату:
    NN      Val
    1       длина телеграммы
    2       команда для ПЛК
    3       индекс модуля
    4..13   параметры конфигурации
    .
    """
    param_list = {}
    n_module = None
    for module_item in data:

        if n_module != module_item.n_module_id:
            param_list[module_item.n_module_id] = [
                [2, command],
                [3, module_item.n_module.n_module_index],
            ]
            if n_module is not None:
                param_list[n_module].insert(0, [1, len(param_list[n_module]) + 1])
            n_module = module_item.n_module_id

        if module_item.n_attribute.n_attribute_type != AttributeFieldType.BOOLEAN_FIELD:
            param_list[module_item.n_module_id].extend(
                [[module_item.n_attribute.n_parameter_id, float(module_item.f_value)]]
            )

    param_list[n_module].insert(0, [1, len(param_list[n_module]) + 1])
    return param_list


def get_int_from_bytes(value_hi, value_lo):
    result_int = value_hi << 8 | value_lo
    return result_int


def get_bytes_from_int(value):
    return (value & 0xFFFFFFFF).to_bytes(4, "little")


def get_2_words_from_float(value):
    word1, word2 = struct.unpack(">HH", struct.pack(">f", value))
    return word1, word2


def get_float_from_2_words(*words):
    word1, word2 = words
    return struct.unpack("f", struct.pack("HH", word2, word1))[0]
