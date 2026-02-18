# from typing import ClassVar
import struct
import time
from dataclasses import dataclass

from equipments.models import cnfEquipment
from general.models import cnfAttribute, cnfCommands, cnfController
from services.mb_client import SelfModbusTcpClient
from variables.models import cnfVariable

from iriusconfig.constants import (AttributeFieldType, GlobalObjectID,
                                   PlcAddressBlockConstants,
                                   PlcCommandConstants,
                                   CommandInterfaceConstants)
from iriusconfig.settings import PLC_IP

# CLIENTS = {
#     plc_item.id: SelfModbusTcpClient(plc_item.c_ip_controller, 502)
#     for plc_item in cnfController.objects.all()
# }

# client = SelfModbusTcpClient(PLC_IP,502)

# prev_return_rec_last = None  # Переменная, хранящая последние значения Rec_last d ReturnDataBlocks

def get_plc_clients():
    """Формирование экземпляров подключения
    к контроллерам проекта с учетом резервирования.
    """

    CLIENTS = {}
    for plc_item in cnfController.objects.all():

        plc_list = plc_item.c_ip_controller.strip().split(',')
        if len(plc_list) == 2:
            CLIENTS[plc_item.id] = [SelfModbusTcpClient(plc_list[0], 502),
                                     SelfModbusTcpClient(plc_list[1], 502)]
        else:
            CLIENTS[plc_item.id] = [SelfModbusTcpClient(plc_list[0], 502)]

    return CLIENTS
    # CLIENTS = {plc_item.id:SelfModbusTcpClient(plc_item.c_ip_controller,502) for plc_item in cnfController.object.all()}

CLIENTS = get_plc_clients()

@dataclass
class DownloadToPLC:
    download_count: int = -1
    download_max_count: int = 0

    percent_num: int = 0

    def clear(self):
        self.download_count = 0
        self.download_max_count = 0
        self.percent_num = 0

    def download_next(self, next_value):
        if self.download_max_count != 0:
            self.percent_num = round((next_value * 100) / self.download_max_count, 0)
            self.percent_num = self.percent_num if self.percent_num <= 100 else 100


def get_int_from_bytes(value_hi, value_lo):
    result_int = value_hi << 8 | value_lo
    return result_int


def get_bytes_from_int(value):
    return (value & 0xFFFFFFFF).to_bytes(4, "little")


def get_2_words_from_float(value):
    word1, word2 = struct.unpack(">HH", struct.pack(">f", value))
    return word1, word2


def get_float_from_2_words1(*words):
    word1, word2 = words
    return struct.unpack("f", struct.pack("HH", word2, word1))


def get_float_from_2_words(*words):
    word1, word2 = words
    return struct.unpack("f", struct.pack("HH", word2, word1))[0]


def add_telegram(current_item, tlm_num, telegram):
    """Расширение телеграммы."""
    for item in current_item:
        word2 = get_2_words_from_float(item[1])
        telegram.extend([get_int_from_bytes(item[0], tlm_num), word2[1], word2[0]])
    return telegram

def get_last_command(client):
    cmd_rec_last = client.read_holding_registers(
        PlcAddressBlockConstants.CMD_DATA_BLOCKS_REC_LAST_ADDRESS, 3
    )
    if cmd_rec_last:
        cmd_rec_last_tlm, cmd_rec_last_nn, _, _ = get_bytes_from_int(cmd_rec_last[0])
        cmd_rec_last_val = int(get_float_from_2_words(cmd_rec_last[2], cmd_rec_last[1]))
        return cmd_rec_last_tlm, cmd_rec_last_nn, cmd_rec_last_val
    else:
        return None, None, None
    
def get_param_active_plc(client):
    """Получение флага активного ПЛК на текущий момент в резервной паре."""
    raw_data_active_plc_1 = client.read_holding_registers(PlcAddressBlockConstants.PLC_1_TAG_MAIN_ADDRESS, 2)
    raw_data_active_plc_2 = client.read_holding_registers(PlcAddressBlockConstants.PLC_2_TAG_MAIN_ADDRESS, 2)
    # print(f" raw_data_active_plc_1 = {raw_data_active_plc_1}, raw_data_active_plc_2: {raw_data_active_plc_2}")
    active_plc_1 = int(get_float_from_2_words(raw_data_active_plc_1[1], raw_data_active_plc_1[0]))
    active_plc_2 = int(get_float_from_2_words(raw_data_active_plc_2[1], raw_data_active_plc_2[0]))    
    if active_plc_1 == active_plc_2:
        return 0 # None
    elif active_plc_1 == 1:
        return 1
    else:
        return 2

def get_active_client(clients:list[SelfModbusTcpClient]):
    """Получение активного клиента в резервной паре."""
    for num, client in enumerate(clients):
        try:
            client.connect()
            if client.is_connected:
                act_plc = get_param_active_plc(client)
                if act_plc is not None:
                    if act_plc == (num + 1) or act_plc == 0:
                        return client
                    else:
                        client.disconnect()
                        return clients.get(act_plc).connect()
        except Exception as error:
            # logger.warning(error)
            print(error)
    return None

def get_sending_data(sending_data, sending_data_additional, telegram, cmd_rec_last_val, rec_last_value_for_writing, current_item, idle_data):
    if not sending_data_additional:

        block_length = len(sending_data["data"]) + len(telegram)

        compare_value = (255 - (cmd_rec_last_val + 1)) * 3
        if block_length <= compare_value:
            # Если вмещается телеграмма, то добавляем
            if sending_data.get("data"):
                sending_data["data"].extend(telegram)
            else:
                sending_data["data"] = telegram
        else:
            # Не вместилась телеграмма в первый блок отправки.
            # Проверяем, вместится ли она с переходом на начало буфера
            # Если вмещается, то добавляем, иначе пишем данные в ожидаемый список

            if block_length <= 255 * 3:

                before_256 = (255 - (cmd_rec_last_val + 1)) * 3
                num = int(
                    before_256 - len(sending_data["data"])
                )  # сколько нужно добрать

                sending_data["data"].extend(telegram[:num])

                if sending_data_additional and sending_data_additional.get("data"):
                    sending_data_additional["data"].extend(telegram[num:])
                else:
                    sending_data_additional = {"data": telegram[num:]}

                sending_data_additional["start_address"] = (
                    PlcAddressBlockConstants.CMD_DATA_BLOCKS_REC_ADDRESS
                )
            else:
                idle_data = telegram
                rec_last_value_for_writing = (
                    (rec_last_value_for_writing - len(current_item))
                    if rec_last_value_for_writing > len(current_item)
                    else 255 + rec_last_value_for_writing - len(current_item)
                )
    else:
        # Уже распечатали sending_data_additional
        block_length = len(sending_data_additional["data"]) + len(telegram)
        if block_length <= cmd_rec_last_val * 3:
            sending_data_additional["data"].extend(telegram)
        else:
            idle_data = telegram  # записываем в лист ожидания телеграмму, для следующей итерации записи
            compare_value = len(telegram) / PlcAddressBlockConstants.REC_LENGTH
            rec_last_value_for_writing = (
                rec_last_value_for_writing - compare_value
                if rec_last_value_for_writing > compare_value
                else (255 + rec_last_value_for_writing) - compare_value
            )

    return sending_data, sending_data_additional, rec_last_value_for_writing, idle_data

def send_wd_to_plc(client):
    wd = client.read_holding_registers(
        PlcAddressBlockConstants.RETURN_DATA_BLOCKS_WD_ADDRESS, 2
    )
    client.write_holding_registers(
        PlcAddressBlockConstants.CMD_DATA_BLOCKS_WD_ADDRESS, wd
    )
    time.sleep(0.2)

def read_response_from_plc(client, response_bad_data, download, return_block, prev_return_rec_last):
    time_fix = time.time()
    response_ready = False
    tlm_data = {}
    rec_last = None
    # #=======================================================================================================================
    # send_wd_to_plc(client)
    
    return_timeout = False
    while not response_ready:
        send_wd_to_plc(client)
        if time.time() - time_fix < CommandInterfaceConstants.RESPONSE_TIMEOUT:
            # print(f"Время ожидания: {(time.time()-time_fix):.2f}")
            time.sleep(0.1)
            rec_last = client.read_holding_registers(
                PlcAddressBlockConstants.RETURN_DATA_BLOCKS_REC_LAST_ADDRESS, 3
            )
            if rec_last != prev_return_rec_last and (rec_last and (rec_last[1] != 0 or rec_last[2] != 0)):
                print(
                    "RETURN_DATA_BLOCKS_REC_LAST = ",
                    rec_last[0],
                    rec_last[1],
                    rec_last[2],
                )
                cmd_rec_last_val = int(
                    get_float_from_2_words(rec_last[2], rec_last[1])
                )

                # time.sleep(0.1)
                return_records = client.read_holding_registers(
                    PlcAddressBlockConstants.RETURN_DATA_BLOCKS_REC_ADDRESS,
                    cmd_rec_last_val * PlcAddressBlockConstants.REC_LENGTH,
                )

                prev_tlm = None
                # разбираем весь буфер, который получили
                for item_num in range(0, len(return_records), 3):
                    cmd_rec_tlm, cmd_rec_nn, _, _ = get_bytes_from_int(
                        return_records[item_num]
                    )

                    cmd_rec_val = get_float_from_2_words(
                        return_records[item_num + 2],
                        return_records[item_num + 1],
                    )

                    if not cmd_rec_tlm or cmd_rec_tlm != prev_tlm:
                        tlm_data[cmd_rec_tlm] = {cmd_rec_nn: cmd_rec_val}
                    else:
                        tlm_data[cmd_rec_tlm][cmd_rec_nn] = cmd_rec_val
                    # tlm_data[cmd_rec_tlm] = {cmd_rec_nn:cmd_rec_val,
                    prev_tlm = cmd_rec_tlm
                # Находим успешные и удаляем из словаря
                resp_keys = response_bad_data.keys()
                # temp_list.extend(tlm_data)
                for item_key, item_val in tlm_data.items():
                    if download:
                        if (
                            item_val.get(2) == 1
                        ):  # Если порядковый номер параметра = 2, и там результат "успешно" - выбрасываем
                            if (
                                item_val.get(3) in resp_keys
                            ):  # При хорошем ответе в третьем параметре пишется номер телеграммы
                                # if item_val[1] == 1: # Если порядковый номер параметра = 1, и там результат "успешно" - выбрасываем
                                response_bad_data.pop(item_val[3])
                        else:
                            # смотрим ошибку
                            # разбираем ошибку по справочнику и указываем для каого элементы
                            # т.е. формируем понятный ответ для пользователя
                            item_dict = {
                                "error_num": item_val.get(2),
                                "index_num": item_val.get(3),
                                "param_num": item_val.get(4),
                            }
                            # if item_val.get(2) is None and item_val.get(4) is None:
                            print("=============", item_val)
                            # temp_list.append(item_val)
                            if item_dict not in return_block:
                                return_block.append(item_dict)
                    else:
                        if item_val not in return_block:
                            return_block.append(
                                item_val
                            )  # = item_val # tlm_data
                response_ready = True
        else:
            print("timeout")
            if not tlm_data:
                return_timeout = True
                # print("timeout")
            response_ready = True
    prev_return_rec_last = rec_last
    return return_block, response_bad_data, return_timeout

def send_data_to_plc(plc_id, data, object_type, handler_class=None, download=None):
    """
    Работа с ПЛК через командный интерфейс.
    """
    # Выполняем подключение/отключение клиента всегда, чтобы не занимать сокет на контроллере
    
    sending_data = {"data": []} # список для записи - ограничен 256 блоками
    sending_data_additional = {}
    response_bad_data = {}
    idle_data = []
    return_block = []
    tlm_send = 0  # счетчик отправляемых записей, для прогресс-бара во фронте
    temp_list = []

    client = get_active_client(CLIENTS[plc_id])

    if not client or not client.is_connected:
        print("Не удалось получить активного клиента подключения к ПЛК!")
        return [{"error_num": "Не найден активный ПЛК!" if not client else "TIMEOUT", "index_num": None, "param_num": None}] 

    # Получаем значения REC_LAST,чтобы понять с какого адреса писать
    print(client.client.connected)
    cmd_rec_last_tlm, cmd_rec_last_nn, cmd_rec_last_val = get_last_command(client)

    if None in [cmd_rec_last_tlm, cmd_rec_last_nn, cmd_rec_last_val]:
        return [{"error_num": "TIMEOUT", "index_num": None, "param_num": None}]

    if cmd_rec_last_tlm == 0 and cmd_rec_last_nn == 0 and cmd_rec_last_val == 0:
        rec_last_value_for_writing = 0
        cmd_rec_last_val = -1
    else:
        rec_last_value_for_writing = (
            cmd_rec_last_val
        )
        cmd_rec_last_val -= 1

    tlm_num = cmd_rec_last_tlm
    data_key_list = list(data.keys())
    print("tlm_num = ", tlm_num)
    # Готовим данные пакетами, исходя из положения указателя в cmd_rec_last_val
    for index_key in range(len(data_key_list) + 1):
        if index_key < len(data_key_list):
            current_item = data.pop(data_key_list[index_key])
        else:
            if not idle_data:
                break
            else:
                current_item = []

        if idle_data:
            cmd_rec_last_val = rec_last_value_for_writing - 1
        rec_last_value_for_writing += len(current_item) if current_item else 0
        rec_last_value_for_writing = rec_last_value_for_writing - (
            (rec_last_value_for_writing // 255) * 255
        )
        tlm_num = tlm_num + 1 if tlm_num <= 254 and tlm_num >= 0 else 1
        tlm_send += 1
        telegram = []

        temp_list.append(tlm_num)

        if idle_data:
            # Если в прошлый цикл обработки не поместились данные,
            # помещаем этот блок в telegram, который будет расширен
            # следующей записью
            telegram = idle_data

            sending_data["start_address"] = int(
                (cmd_rec_last_val + 1) * PlcAddressBlockConstants.REC_LENGTH
                + PlcAddressBlockConstants.CMD_DATA_BLOCKS_REC_ADDRESS
            )

            rec_last_value_for_writing += len(idle_data) / 3
            rec_last_value_for_writing = rec_last_value_for_writing - (
                (rec_last_value_for_writing // 255) * 255
            )
            idle_data = []

        telegram = add_telegram(current_item, tlm_num, telegram)

        response_bad_data[tlm_num] = {"data": current_item}
        # print('Rec = ',current_item)
        sending_data, sending_data_additional, rec_last_value_for_writing, idle_data = get_sending_data(
            sending_data,
            sending_data_additional,
            telegram,
            cmd_rec_last_val,
            rec_last_value_for_writing,
            current_item,
            idle_data)

        prev_return_rec_last = client.read_holding_registers(
            PlcAddressBlockConstants.RETURN_DATA_BLOCKS_REC_LAST_ADDRESS, 3
        )
        print('Sending new array of data...')
        # Если последний ключ обраотан, либо список ожидания заполнен (значит весь буфер забит уже), пишем в ПЛК
        if (
            idle_data
            or (index_key >= len(data_key_list))
            or data_key_list[index_key] == data_key_list[-1]
        ):
            # Сначала пишем sending_data, а потом sending_data_additional

            if not sending_data.get("start_address"):
                # Вычисляем адрес с которого нужно писать в контроллер
                # (Последний блок записи*длину блока(2 байта и один реал = 3 ворда)
                # и добавляем смещение от нуля, откуда начинаются блоки для записи)
                sending_data["start_address"] = (
                    (cmd_rec_last_val + 1) * PlcAddressBlockConstants.REC_LENGTH
                    + PlcAddressBlockConstants.CMD_DATA_BLOCKS_REC_ADDRESS
                )

            client.write_holding_registers(
                sending_data["start_address"], sending_data["data"]
            )

            if sending_data_additional and sending_data_additional.get("data"):
                client.write_holding_registers(
                    sending_data_additional["start_address"],
                    sending_data_additional["data"],
                )

            # time.sleep(0.5)
            # делаем паузу для отправки REC_LAST

            word2 = get_2_words_from_float(
                rec_last_value_for_writing
                if rec_last_value_for_writing <= 254
                else (rec_last_value_for_writing - 255)
            )

            rec_last = [
                (
                    sending_data["data"][-3]
                    if not sending_data_additional
                    or not sending_data_additional.get("data")
                    else sending_data_additional["data"][-3]
                ),
                word2[1],
                word2[0],
            ]

            cmd_1, cmd_2, _, _ = get_bytes_from_int(
                sending_data["data"][-3]
                if not sending_data_additional
                or not sending_data_additional.get("data")
                else sending_data_additional["data"][-3]
            )
            # temp_rec_last = [cmd_1, cmd_2, get_float_from_2_words(word2[0], word2[1])]
            # print('Rec_Last = ', temp_rec_last)
            client.write_holding_registers(
                PlcAddressBlockConstants.CMD_DATA_BLOCKS_REC_LAST_ADDRESS, rec_last
            )

            sending_data["data"] = []
            sending_data_additional = None
            # print('Rec all: ',response_bad_data)
            # получили данные для отправки в sending_data
            # Rec_last пишет в значение последний заполненный Rec, а начинает с 1 всегда (нет записи по кругу)
            if handler_class:
                handler_class.download_next(tlm_send)
                
            return_block, response_bad_data, return_timeout = read_response_from_plc(client,response_bad_data,download, return_block, prev_return_rec_last)

    client.disconnect()
    if handler_class:
        handler_class.download_next(handler_class.download_max_count)
        # handler_class.clear()

    if download:
        if return_timeout:
            return_block.append(
                {"error_num": "Превышено время ожидания ответа от ПЛК...", "index_num": "None", "param_num": "None"}
            )
        else:

            return_block = parse_error_data(
                return_block, response_bad_data, download=True, object_type=object_type
            )
    else:
        return_block = parse_error_data(
            return_block, response_bad_data, download=False, object_type=object_type
        )
    return return_block

def parse_error_data(data, bad_data, download, object_type):

    cmd_data = {item.n_command_index: item.c_desc for item in cnfCommands.objects.all()}
    attributes = {
        item.n_parameter_id: item.c_display_attribute
        for item in cnfAttribute.objects.all()
    }
    upload_data = None

    for item in data:
        if download:
            item["error_num"] = cmd_data.get(item["error_num"])
            item["index_num"] = (
                f'индекс {item["index_num"]}'  # f'телеграмма {item["index_num"]}'
            )
            if attributes.get(item["param_num"]):
                item["param_num"] = f'Параметр {attributes.get(item["param_num"])}'
            # if object_type == GlobalObjectID.VARIABLE:
            #     cnfVariable.objects.filter()
        else:
            if item[2] not in (
                PlcCommandConstants.RETURN_CMD_READ_EQUIPMENT_CONFIG,
                PlcCommandConstants.RETURN_CMD_READ_EQUIPMENT_LINK_EQ_CONFIG,
                PlcCommandConstants.RETURN_CMD_READ_EQUIPMENT_LINK_PID_CONFIG,
                PlcCommandConstants.RETURN_CMD_READ_EQUIPMENT_LINK_VDB_CONFIG,
                PlcCommandConstants.RETURN_CMD_READ_EQUIPMENT_SEQ1_CONFIG,
                PlcCommandConstants.RETURN_CMD_READ_EQUIPMENT_SEQ2_CONFIG,
                PlcCommandConstants.RETURN_CMD_READ_EQUIPMENT_SEQ3_CONFIG,
                PlcCommandConstants.RETURN_CMD_READ_EQUIPMENT_SEQ4_CONFIG,
            ):
                if upload_data:
                    upload_data.append(
                        {
                            "error_num": cmd_data.get(item[2]),
                            "index_num": f"телеграмма {item[3]}",
                            "param_num": "None",
                        }
                    )
                else:
                    upload_data = [
                        {
                            "error_num": cmd_data.get(item[2]),
                            "index_num": f"телеграмма {item[3]}",
                            "param_num": "None",
                        }
                    ]
    if not download:
        return data  # upload_data if upload_data else data
    return data


def get_count_precision(number):
    _, mantissa = str(number).split(".")
    return len(mantissa)
