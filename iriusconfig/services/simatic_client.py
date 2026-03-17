import snap7
from dataclasses import dataclass, field
from snap7.client import Client
from typing import List, Optional, Any
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
    CHAR = 'char'
    WORD = 'word'
    DWORD = 'dword'
    STRING = 'string'
    TIME = 'time'
    DATE = 'date'
    TOD = 'tod'
    DT = 'dt'

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

    def is_connected(self)-> bool:
        """Проверка состояния соединения."""
        try:
            return self.client.get_connected()
        except Exception:
            return False

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
            res = self.client.db_write(db_num,start_pos,data)
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
            # return bytearray([data[0],data[1]])
            return data
        #
        # return bytearray([data[2],data[3], data[0], data[1]])
        return bytearray([data[0],data[1], data[2], data[3]])
        # return bytearray([data[1],data[0], data[3], data[2]])
        # return bytearray([data[3],data[2], data[1], data[0]]) # что-то похоже
        # return bytearray([data[0],data[1], data[2], data[3]])

    def _get_type_size(self, data_type: DataTypes) -> int:
        """Получение размера типа в байтах."""
        type_sizes = {
            DataTypes.BOOL: 1,
            DataTypes.BYTE: 1,
            DataTypes.CHAR: 1,
            DataTypes.INT: 2,
            DataTypes.WORD: 2,
            DataTypes.DINT: 4,
            DataTypes.DWORD: 4,
            DataTypes.REAL: 4,
            DataTypes.TIME: 4,
            DataTypes.DATE: 2,
            DataTypes.TOD: 4,
            DataTypes.DT: 8,
        }
        return type_sizes.get(data_type, 1)

    def read_by_type(self, db_num: int, start_pos: int, data_type: DataTypes, bit_pos: Optional[bool] = None):
        # type_sizes = {DataTypes.BOOL: 1,
        #               DataTypes.BYTE: 1,
        #               DataTypes.INT: 2,
        #               DataTypes.DINT: 4,
        #               DataTypes.REAL: 4}
        # size = type_sizes.get(data_type)
        if data_type == DataTypes.STRING:
            length_byte = self.read_data(db_num, start_pos, 1)
            str_length = length_byte[0]
            size = str_length + 2
        else:
            size = self._get_type_size(data_type)
        if size is None:
            raise ValueError(f'Неизвестный тип данных: {data_type}')
        
        data = self.read_data(db_num, start_pos, size)

        data_converted = self._convert_from_bytes(data,data_type,bit_pos)

        return data_converted

    def _convert_from_bytes(self, data: bytearray, data_type: DataTypes, bit_pos: Optional[int] = None):
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
            # data_swapped = self._swap_words(data[:2])
            # return struct.unpack('>h', data_swapped)[0] 
            return struct.unpack('>h', data[:2])[0]
        elif data_type == DataTypes.WORD:
            # data_swapped = self._swap_words(data[:2])
            # return struct.unpack('>H', data_swapped)[0]        
            return struct.unpack('>H', data[:2])[0]        
        elif data_type == DataTypes.DINT:
            return struct.unpack('>h', data[:4])[0]
        elif data_type == DataTypes.DWORD:
            # DWORD (32-bit unsigned)
            return struct.unpack('>I', data[:4])[0]        
        elif data_type == DataTypes.REAL:
            data_swapped = self._swap_words(data[:4])
            return struct.unpack('>f', data_swapped)[0]
        else:
            raise ValueError('Неподдерживаемый тип данных')

    def read_int(self, db_num: int, start_pos: int) -> int:
        return self.read_by_type(db_num, start_pos, DataTypes.INT)
    
    def read_dint(self, db_num: int, start_pos: int) -> int:
        return self.read_by_type(db_num, start_pos, DataTypes.DINT)    
    
    def read_real(self, db_num: int, start_pos: int) -> int:
        return self.read_by_type(db_num, start_pos, DataTypes.REAL)
    
    def write_by_type(self, db_num: int, start_pos: int, value: Any, data_type: DataTypes, bit_pos: Optional[bool] = None):

        if data_type == DataTypes.BOOL and bit_pos is not None:
           pass # byte_from_plc = self.re
        else:
            data_to_write = self._convert_to_bytes(value,data_type)
        self.write_data(db_num, start_pos,data_to_write)


    def _convert_to_bytes(self, value: Any, data_type: DataTypes) -> bytearray:
        if data_type == DataTypes.BOOL:
            if not isinstance(value,bool):
                value = bool(value)
                return bytearray([int(value)])
        elif data_type == DataTypes.BYTE:
            return bytearray([value & 0xFF])
        elif data_type == DataTypes.INT:
            return bytearray(struct.pack('>h', int(value)))
        elif data_type == DataTypes.WORD:
            return bytearray(struct.pack('>H', value & 0xFFFF))
        elif data_type == DataTypes.DINT:
            return bytearray(struct.pack('>i', int(value)))
        elif data_type == DataTypes.DWORD:
            val = int(value)
            # if val < 0 or val > 4294967295:
            #     raise ValueError(f"Значение {val} выходит за пределы DWORD")
            return bytearray(struct.pack('>I', val & 0xFFFFFFFF))        
        elif data_type == DataTypes.REAL:
            packed = struct.pack('>f', float(value))
            return bytearray([packed[0],packed[1], packed[2], packed[3]])
        else:
            raise ValueError('Неподдерживаемый тип данных')
    
   
    def write_int(self, db_num: int, start_pos: int, value: int):
        self.write_by_type(db_num, start_pos, value, DataTypes.INT)

    def write_real(self, db_num: int, start_pos: int, value: float):
        self.write_by_type(db_num, start_pos, value, DataTypes.REAL)

    def read_array(self, db_num: int, start_pos: int, data_type: DataTypes, 
                   count: int, bit_positions: Optional[List[int]] = None) -> List[Any]:
        """
        Чтение массива данных одного типа.
        """
        if data_type == DataTypes.BOOL:
            if bit_positions is None or len(bit_positions) != count:
                raise ValueError("Для BOOL массива требуется список bit_positions длиной count")
            
            # Для BOOL читаем байты и извлекаем биты
            byte_count = (max(bit_positions) // 8 + count // 8 + 1)  # Оценка количества байт
            data = self.read_data(db_num, start_pos, byte_count)
            
            result = []
            for i, bit_pos in enumerate(bit_positions):
                byte_index = bit_pos // 8
                bit_index = bit_pos % 8
                if byte_index < len(data):
                    byte_value = data[byte_index]
                    result.append(bool((byte_value >> bit_index) & 1))
                else:
                    result.append(False)
            return result
        
        else:
            # Для остальных типов читаем непрерывный блок
            element_size = self._get_type_size(data_type)
            total_size = element_size * count
            data = self.read_data(db_num, start_pos, total_size)
            
            result = []
            for i in range(count):
                element_data = data[i * element_size:(i + 1) * element_size]
                result.append(self._convert_from_bytes(element_data, data_type))
            
            return result
    
    def write_array(self, db_num: int, start_pos: int, data_type: DataTypes, 
                    values: List[Any], bit_positions: Optional[List[int]] = None) -> None:
        """
        Запись массива данных одного типа.
        """
        if not values:
            return
        
        if data_type == DataTypes.BOOL:
            if bit_positions is None or len(bit_positions) != len(values):
                raise ValueError("Для BOOL массива требуется список bit_positions длиной values")
            
            # Для BOOL нужно читать, модифицировать и записывать байты
            max_byte = max(bit_positions) // 8
            min_byte = min(bit_positions) // 8
            byte_count = max_byte - min_byte + 1
            
            # Читаем текущие байты
            current_bytes = self.read_data(db_num, start_pos + min_byte, byte_count)
            current_bytes = bytearray(current_bytes)
            
            # Модифицируем биты
            for value, bit_pos in zip(values, bit_positions):
                byte_index = (bit_pos // 8) - min_byte
                bit_index = bit_pos % 8
                if value:
                    current_bytes[byte_index] |= (1 << bit_index)
                else:
                    current_bytes[byte_index] &= ~(1 << bit_index)
            
            # Записываем обратно
            self.write_data(db_num, start_pos + min_byte, current_bytes)
        
        else:
            # Для остальных типов записываем непрерывный блок
            element_size = self._get_type_size(data_type)
            total_data = bytearray()
            
            for value in values:
                total_data.extend(self._convert_to_bytes(value, data_type))
            
            self.write_data(db_num, start_pos, total_data)

    def read_array_of_reals(self, db_num: int, start_pos: int, count: int) -> List[float]:
        """Чтение массива REAL (float) из ПЛК."""
        return self.read_array(db_num, start_pos, DataTypes.REAL, count)

    def read_array_of_ints(self, db_num: int, start_pos: int, count: int) -> List[int]:
        """Чтение массива INT из ПЛК."""
        return self.read_array(db_num, start_pos, DataTypes.INT, count)

    def read_array_of_dints(self, db_num: int, start_pos: int, count: int) -> List[int]:
        """Чтение массива DINT из ПЛК."""
        return self.read_array(db_num, start_pos, DataTypes.DINT, count)

    def read_array_of_words(self, db_num: int, start_pos: int, count: int) -> List[int]:
        """Чтение массива WORD из ПЛК."""
        return self.read_array(db_num, start_pos, DataTypes.WORD, count)

    def read_array_of_bytes(self, db_num: int, start_pos: int, count: int) -> List[int]:
        """Чтение массива BYTE из ПЛК."""
        return self.read_array(db_num, start_pos, DataTypes.BYTE, count)

    def read_array_of_bools(self, db_num: int, start_pos: int, 
                           bit_positions: List[int]) -> List[bool]:
        """Чтение массива BOOL из ПЛК."""
        return self.read_array(db_num, start_pos, DataTypes.BOOL, len(bit_positions), bit_positions)

    def write_array_of_reals(self, db_num: int, start_pos: int, values: List[float]) -> None:
        """Запись массива REAL (float) в ПЛК."""
        self.write_array(db_num, start_pos, DataTypes.REAL, values)

    def write_array_of_ints(self, db_num: int, start_pos: int, values: List[int]) -> None:
        """Запись массива INT в ПЛК."""
        self.write_array(db_num, start_pos, DataTypes.INT, values)

    def write_array_of_dints(self, db_num: int, start_pos: int, values: List[int]) -> None:
        """Запись массива DINT в ПЛК."""
        self.write_array(db_num, start_pos, DataTypes.DINT, values)

    def write_array_of_words(self, db_num: int, start_pos: int, values: List[int]) -> None:
        """Запись массива WORD в ПЛК."""
        self.write_array(db_num, start_pos, DataTypes.WORD, values)

    def write_array_of_bytes(self, db_num: int, start_pos: int, values: List[int]) -> None:
        """Запись массива BYTE в ПЛК."""
        self.write_array(db_num, start_pos, DataTypes.BYTE, values)

    def write_array_of_bools(self, db_num: int, start_pos: int, 
                            values: List[bool], bit_positions: List[int]) -> None:
        """Запись массива BOOL в ПЛК."""
        self.write_array(db_num, start_pos, DataTypes.BOOL, values, bit_positions)