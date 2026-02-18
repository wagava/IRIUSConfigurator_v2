from dataclasses import dataclass


@dataclass(frozen=True)
class ViewConstants:
    MAX_ITEMS_ON_PAGE = 25


@dataclass(frozen=True)
class ModelConstants:
    FIELD_MAX_LENGTH2 = 2
    FIELD_MAX_LENGTH16 = 16
    FIELD_MAX_LENGTH32 = 32
    FIELD_MAX_LENGTH64 = 64
    FIELD_MAX_LENGTH128 = 128
    FIELD_MAX_LENGTH255 = 255
    FIELD_MAX_LENGTH256 = 256
    FIELD_MAX_LENGTH512 = 512
    FIELD_MAX_LENGTH2000 = 2000


@dataclass(frozen=True)
class GlobalObjectID:
    MODULE = 1
    VARIABLE = 2
    EQUIPMENT = 3
    PID = 31
    ATS = 32
    SEQUENCE = 33


@dataclass(frozen=True)
class AttributeFieldType:
    INTEGER_FIELD = 128  # Тип поля: целое число
    BOOLEAN_FIELD = 129  # Тип поля: логический тип
    FLOAT_FIELD = 130  # Тип поля: тип с плавающей запятой
    TEXT_FIELD = 134  # Тип поля: текстовый тип


@dataclass(frozen=True)
class EquipmentTypeConstants:
    """
    Типы оборудования в соотвтствии с таблицей
    cnfEquipmentType (используется значение n_type_value)
    """

    TYPE_EQ01 = 1
    TYPE_EQ02 = 2
    TYPE_PID_AI = 10
    TYPE_PID_DC = 11
    TYPE_P_DC = 12
    TYPE_EQ14 = 14
    TYPE_ATS = 15
    TYPE_EQ03 = 3
    TYPE_EQ04 = 4

    WORD_TYPE_STATUSWORD = 1
    WORD_TYPE_CONTROLWORD = 2
    WORD_TYPE_ERRORWORD = 3

    # TYPE_EQ01 = 'TYPE_EQ01'
    # TYPE_EQ02 = 'TYPE_EQ02'
    # TYPE_PID_AI = 'TYPE_PID_AI'
    # TYPE_PID_DC = 'TYPE_PID_DC'
    # TYPE_P_DC = 'TYPE_P_DC'
    # TYPE_EQ14 = 'TYPE_EQ14'
    # TYPE_ATS = 'TYPE_ATS'
    # TYPE_EQ03 = 'TYPE_EQ03'
    # TYPE_EQ04 = 'TYPE_EQ04'
    TYPE_EQ14_MAX_STEPS = 50


@dataclass(frozen=True)
class PlcCommandConstants:
    """
    Команды для работы с командным
    интерфейсом ПЛК
    """

    CMD_READ_MODULE_CONFIG = 257
    CMD_READ_VARIABLE_CONFIG = 513
    CMD_READ_VARIABLE_FORMULA_CONFIG = 514
    CMD_READ_EQUIPMENT_CONFIG = 769
    CMD_READ_EQUIPMENT_SEQ1_CONFIG = 771
    CMD_READ_EQUIPMENT_SEQ2_CONFIG = 772
    CMD_READ_EQUIPMENT_SEQ3_CONFIG = 773
    CMD_READ_EQUIPMENT_SEQ4_CONFIG = 774
    CMD_READ_EQUIPMENT_LINK_VDB_CONFIG = 817
    CMD_READ_EQUIPMENT_LINK_EQ_CONFIG = 818
    CMD_READ_EQUIPMENT_LINK_PID_CONFIG = 770

    # ответная команда
    RETURN_CMD_READ_EQUIPMENT_CONFIG = 850
    RETURN_CMD_READ_EQUIPMENT_SEQ1_CONFIG = 852
    RETURN_CMD_READ_EQUIPMENT_SEQ2_CONFIG = 854
    RETURN_CMD_READ_EQUIPMENT_SEQ3_CONFIG = 853
    RETURN_CMD_READ_EQUIPMENT_SEQ4_CONFIG = 855
    RETURN_CMD_READ_EQUIPMENT_LINK_VDB_CONFIG = 875
    RETURN_CMD_READ_EQUIPMENT_LINK_EQ_CONFIG = 876
    RETURN_CMD_READ_EQUIPMENT_LINK_PID_CONFIG = 851

    CMD_WRITE_MODULE_CONFIG = 258
    CMD_WRITE_VARIABLE_CONFIG = 515
    CMD_WRITE_EQUIPMENT_BASE_CONFIG = 775
    CMD_WRITE_EQUIPMENT_PID_CONFIG = 776
    CMD_WRITE_EQUIPMENT_LINKED_VAR_CONFIG = 819  # Связанные переменные
    CMD_WRITE_EQUIPMENT_LINKED_EQ_CONFIG = 820  # Связанное оборудование
    CMD_WRITE_EQUIPMENT_LINKED_PID_VAR_CONFIG = 776  # Связанные переменные ПИД
    CMD_WRITE_EQUIPMENT_SEQ1_CONFIG = 777  # Последовательность запуска
    CMD_WRITE_EQUIPMENT_SEQ2_CONFIG = 779  # Последовательность быстрого запуска
    CMD_WRITE_EQUIPMENT_SEQ3_CONFIG = 778  # Последовательность останова
    CMD_WRITE_EQUIPMENT_SEQ4_CONFIG = 780  # Последовательность авар.останова


@dataclass(frozen=True)
class PlcAddressBlockConstants:
    """
    Адреса блоков для чтения/записи
    командного интерфейса ПЛК
    """

    REC_LENGTH = 3
    MODBUS_PACKET_MAX_LENTGH = 120

    # Первый поток
    # CMD_DATA_BLOCKS_BASE_ADDRESS = 0
    # CMD_DATA_BLOCKS_REC_LAST_ADDRESS = 3
    # CMD_DATA_BLOCKS_REC_ADDRESS = 9

    # # Второй поток
    CMD_DATA_BLOCKS_WD_ADDRESS = 2001
    CMD_DATA_BLOCKS_BASE_ADDRESS = 2000
    CMD_DATA_BLOCKS_REC_LAST_ADDRESS = 2003
    CMD_DATA_BLOCKS_REC_ADDRESS = 2009

    # Первый поток
    # RETURN_DATA_BLOCKS_BASE_ADDRESS = 5000
    # RETURN_DATA_BLOCKS_REC_LAST_ADDRESS = 5012
    # RETURN_DATA_BLOCKS_REC_ADDRESS = 5018

    # # Второй поток
    RETURN_DATA_BLOCKS_WD_ADDRESS = 3006
    RETURN_DATA_BLOCKS_BASE_ADDRESS = 3000
    RETURN_DATA_BLOCKS_REC_LAST_ADDRESS = 3012
    RETURN_DATA_BLOCKS_REC_ADDRESS = 3018

    PLC_1_TAG_MAIN_ADDRESS=7265  # Адрес, где хранится значение переменной об активном контроллере №1. ПЛК1 - активный = 1
    PLC_2_TAG_MAIN_ADDRESS=7269  # Адрес, где хранится значение переменной об активном контроллере №2. ПЛК2 - активный = 2  

@dataclass(frozen=True)
class CommandInterfaceConstants:
    """
    Константы для командного интерфейса и
    модулей для обработки/подготовки данных.
    """

    ACTION_DOWNLOAD_TO_PLC = "download"

    LINKED_VAR_MAX_ITEM = 81  # Ограничение количества записей связанных переменных

    RESPONSE_TIMEOUT = 5  # Таймаут для ответа от ПЛК в секундах

@dataclass(frozen=True)
class FieldMainTable:
    """
    Константы для указания id параметров для
    конфигурационных данных, передаваемых
    в контроллер.
    """

    VAR_FIELD_TYPE = 23
    VAR_FIELD_DATA_TYPE = 24
    VAR_FIELD_MODULE = 30
    VAR_FIELD_CHANNEL = 8

    EQ_FIELD_TYPE = 10
    EQ_FIELD_SW_INDEX = 11
    EQ_FIELD_CW_INDEX = 12
    EQ_FIELD_SW_BITS_START_INDEX = 13  # 13..28
    EQ_FIELD_CW_BITS_START_INDEX = 29  # 29..44


@dataclass(frozen=True)
class AttributesIDs:
    """
    Константы для parameter_id в таблице атрибутов.
    """

    VAR_FORMULA = 1000


@dataclass(frozen=True)
class PLCModbusVarEQBaseAddress:
    """
    Константы для базовых адресов для переменных и оборудования.
    """

    VAR_BASE_ADDRESS = 6000
    EQ_BASE_ADDRESS = 16000
    VAR_INDEX_OFFSET = 4
    EQ_INDEX_OFFSET = 82  # 79
