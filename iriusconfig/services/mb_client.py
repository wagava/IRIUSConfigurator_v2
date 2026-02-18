from dataclasses import dataclass
from typing import ClassVar

from pymodbus.client import ModbusTcpClient
from pymodbus.client.mixin import ModbusClientMixin

from services import custom_logger

logger = custom_logger.get_logger(__name__)


def separate_on_packets(lst, n):
    """Деление на пакеты по заданному числу n."""
    for i in range(0, len(lst), n):
        yield lst[i: i + n]


@dataclass
class ModbusTcpClientCustom(ModbusClientMixin):
    pass


@dataclass
class SelfModbusTcpClient:
    """
    Клиент ModbusTcp с реализацией
    чтения/записи в Holding Registers.
    """

    client: ModbusTcpClient
    is_connected: bool
    # hr_read_buffer: dict
    hr_read_buffer: list
    ENDPOINT: ClassVar[str]

    def __init__(self, host: str, port: int):

        self.client = ModbusTcpClient(
            host,
            port=port,
            # Common optional parameters:
            # framer=Framer.SOCKET,
            timeout=5,
            retries=5,
            #    retry_on_empty=False,y
            #    strict=True,
            # TCP setup parameters
            #    source_address=("localhost", 0),
        )
        self.hr_read_buffer = {}
        # self.client = ModbusTcpClientCustom(host, port)
        self.ENDPOINT = f"{host}:{port}"

    def connect(self):
        try:
            self.is_connected = self.client.connect()
            assert self.client.connected
            return True
        except Exception as error:
            print(f"Невозможно подключиться к {self.ENDPOINT}, {error}")
            logger.error(f"Невозможно подключиться к {self.ENDPOINT}, {error}")
            return False

    def disconnect(self):
        try:
            self.client.close()
        except Exception as error:
            print(f"Сбой при отключении от {self.ENDPOINT}, {error}")
            logger.error(f"Сбой при отключении от {self.ENDPOINT}, {error}")

    def read_coils(self):
        pass

    def read_discrete_inputs(self):
        pass

    def read_holding_registers(self, start_address, length):

        read_iteration = 1
        local_length = length
        if length > 120:
            read_iteration = (length // 120) + 1

        self.hr_read_buffer = []
        try:
            if self.is_connected:
                for iter in range(0, read_iteration):
                    if iter < read_iteration - 1:
                        local_length = 120
                    else:
                        local_length = length - iter * 120
                    request = self.client.read_holding_registers(
                        start_address, local_length
                    )
                    if not request.registers:
                        raise Exception(f"Данные с адреса {start_address} не могут быть прочитаны!")
                    self.hr_read_buffer.extend(request.registers)
                    start_address += 120

                return self.hr_read_buffer
            else:
                print(f"Нет подключения к {self.ENDPOINT}")
                logger.error(f"Нет подключения к {self.ENDPOINT}")
        except Exception as error:
            print(f"Сбой при получении данных, {error}")
            logger.error("Сбой при получении данных")

    def read_input_registers(self):
        pass

    def write_coils(self):
        pass

    def write_discrete_inputs(self):
        pass

    def write_holding_registers(self, start_address, values):
        try:
            if self.is_connected:
                values_list = list(
                    separate_on_packets(values, 120)
                )  # Разбиваем список значений на 120 регистров
                # (должно быть в посылке не более 255 байт)
                calc_start_address = start_address
                first_writing = True
                for item_values in values_list:
                    self.client.write_registers(
                        address=calc_start_address, values=item_values
                    )
                    if first_writing:
                        self.client.write_registers(
                            address=calc_start_address, values=item_values
                        )
                        first_writing = False
                    calc_start_address += int(
                        len(item_values)
                    )
                    
                return True
            else:
                print(f"Нет подключения к {self.ENDPOINT}")
                logger.error(f"Нет подключения к {self.ENDPOINT}")
        except Exception as error:
            print(f"Сбой при отправке данных, {error}")
            logger.error("Сбой при отправке данных")
        return False

    def write_input_registers(self):
        pass
