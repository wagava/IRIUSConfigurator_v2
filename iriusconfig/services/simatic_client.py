import snap7
from dataclasses import dataclass, field
from snap7.client import Client
from typing import Optional, Any
import logging
from enum import Enum

import struct

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataTypes(Enum):
    """Типы данных S7 PLC."""
    BOOL = 'bool'
    BYTE = 'byte'
    INT = 'int'
    DINT = 'dint'
    REAL = 'real'

@dataclass(slots=True)
class Snap7Client:
    """Класс реализации коннектора к ПЛК SIMATIC S7."""

    host: str
    port: Optional[int] = 102
    rack: Optional[int] = 0
    slot: Optional[int] = 0
    timeout: Optional[int] = 5000  # мс
    local_tsap: int = 0x0100
    remote_tsap: int = 0x0102
    client: Client = field(init=False, default_factory=Client)

    def __post_init__(self):
        self.client.set_connection_params(self.host, self.local_tsap, self.remote_tsap)


    def connect(self) -> bool:
        try:
        # self.client = Client()
        # self.client.connect(self.host, 0, 0, self.port)
            self.client.connect(self.host, self.rack, self.slot, self.port)
            if self.client.get_connected():
                logger.info(f'Успешное подключение к {self.host}:{self.port}')
                return True
            return False
        except Exception as er:
            logger.error(f'Ошибка подключения к {self.host}:{self.port}: {er}')
            return False

    def disconnect(self):
        try:
            if self.client.get_connected():
                self.client.disconnect()
                logger.info(f'Отключено от {self.host}:{self.port}')
        except Exception as er:
            logger.error(f'Ошибка при отключении от {self.host}')

    def read_data(self, db_num: int, start_pos: int, size: int) -> bytearray:
        if not self.client.get_connected():
            raise ConnectionError(f'Нет подключения к ПЛК {self.host}')
        try:
            data = self.client.db_read(db_num,start_pos,size)
            logger.debug(f'Прочитано {size} байт из DB{db_num}[{start_pos}:{start_pos+size}]')
            return data
        except Exception as er:
            logger.error(f'Ошибка чтения DB{db_num}:[{start_pos}:{start_pos+size}]')

    def write_data(self, db_num: int, start_pos: int, data: bytearray) -> bool:
        if not self.client.get_connected():
            raise ConnectionError(f'Нет подключения к ПЛК {self.host}')
        try:
            data = self.client.db_write(db_num,start_pos,data)
            logger.debug(f'Записано {len(data)} байт в DB{db_num}[{start_pos}]')
        except Exception as er:
            logger.error(f'Ошибка записи в DB{db_num}: {er}')
            return False
        return True
    
    def __enter__(self):
        if not self.connect():
            raise ConnectionError(f'Не удалось подключиться к {self.host}...')
        return self
    
    def __exit__(self,exc_type, exc_val, exc_tb):
        self.disconnect()
        if exc_type:
            logger.error(f'Ошибка в контекстном менеджере: {exc_val}')

    def _swap_words(self, data: bytearray):
        if len(data) < 4:
            return data
        #
        # return bytearray([data[2],data[3], data[0], data[1]])
        return bytearray([data[0],data[1], data[2], data[3]])
        # return bytearray([data[1],data[0], data[3], data[2]])
        # return bytearray([data[3],data[2], data[1], data[0]]) # что-то похоже
        # return bytearray([data[0],data[1], data[2], data[3]])

    def read_by_type(self, db_num: int, start_pos: int, data_type: DataTypes, bit_pos: Optional[bool] = None):
        type_sizes = {DataTypes.BOOL: 1,
                      DataTypes.BYTE: 1,
                      DataTypes.INT: 2,
                      DataTypes.DINT: 4,
                      DataTypes.REAL: 4}
        size = type_sizes.get(data_type)
        if size is None:
            raise ValueError(f'Неизвестный тип данных: {data_type}')
        
        data = self.read_data(db_num, start_pos, size)

        data_converted = self.convert_from_bytes(data,data_type,bit_pos)

        return data_converted

    def convert_from_bytes(self, data: bytearray, data_type: DataTypes, bit_pos: Optional[int] = None):
        if data_type == DataTypes.BOOL:
            if bit_pos is None:
                raise ValueError('Для BOOL необходимо указать номер бита!')
            if bit_pos < 0 or bit_pos > 7:
                raise ValueError('Номер бита должен быть от 0 до 7')
            byte_val = data[0]
            return bool((byte_val >> bit_pos) & 1)
        elif data_type == DataTypes.BYTE:
            return data[0]
        elif data_type == DataTypes.INT:
            return struct.unpack('>h', data[:2])[0]
        elif data_type == DataTypes.DINT:
            return struct.unpack('>h', data[:4])[0]        
        elif data_type == DataTypes.REAL:
            data_swapped = self._swap_words(data[:4])
            return struct.unpack('>f', data_swapped)[0]
        else:
            raise ValueError('Неподдерживаемый тип данных')

    def read_int(self, db_num: int, start_pos: int) -> int:
        return self.read_by_type(db_num, start_pos, DataTypes.INT)
    
    def read_real(self, db_num: int, start_pos: int) -> int:
        return self.read_by_type(db_num, start_pos, DataTypes.REAL)
    
    def write_by_type(self, db_num: int, start_pos: int, value: Any, data_type: DataTypes, bit_pos: Optional[bool] = None):

        if data_type == DataTypes.BOOL and bit_pos is not None:
           pass # byte_from_plc = self.re
        else:
            data_to_write = self.convert_to_bytes(value,data_type)
        self.write_data(db_num, start_pos,data_to_write)


    def convert_to_bytes(self, value: Any, data_type: DataTypes) -> bytearray:
        if data_type == DataTypes.BOOL:
            if not isinstance(value,bool):
                value = bool(value)
                return bytearray([int(value)])
        elif data_type == DataTypes.BYTE:
            return bytearray([value & 0xFF])
        elif data_type == DataTypes.INT:
            return bytearray(struct.pack('>h', int(value)))
        elif data_type == DataTypes.DINT:
            return bytearray(struct.pack('>i', int(value)))
        elif data_type == DataTypes.REAL:
            packed = struct.pack('>f', float(value))
            return bytearray([packed[0],packed[1], packed[2], packed[3]])
        else:
            raise ValueError('Неподдерживаемый тип данных')
    
   
    def write_int(self, db_num: int, start_pos: int, value: int):
        self.write_by_type(db_num, start_pos, value, DataTypes.INT)

    def write_real(self, db_num: int, start_pos: int, value: float):
        self.write_by_type(db_num, start_pos, value, DataTypes.REAL)