from general.models import cnfAttribute
from iriusconfig.constants import AttributeFieldType
                                   

def get_int_from_bits(bits: tuple) -> int:
    int_result = 0
    for item in bits:
        int_result = int_result | (item[1] << item[0])
    return int_result


def get_bits_from_int(word2: int) -> dict:
    bits = {}
    for num in range(0, 32):
        bits[num] = 1 if (1 & word2 >> num) == 1 else 0

    return bits


def set_mask_to_config_words(cfg_word):
    """Применение маски для полученного значения из ПЛК для конфигурационных слов."""

    config_word = int(cfg_word)
    # Сохраняем знак, но для битовых операций используем абсолютное значение
    is_negative = config_word < 0
    abs_value = abs(config_word)
    
    # Для битовой маски используем абсолютное значение
    config_word = abs_value & 0xFFFF if is_negative else config_word & 0xFFFF
        # В слове разбираем только нужные биты
    attr_CW_mask = []  # [0]*16
    attr_CW_bit_info = [] 
    for item_attr in cnfAttribute.objects.filter(
        n_global_object_type=1,
        n_attribute_type=AttributeFieldType.BOOLEAN_FIELD,
        c_name_attribute__contains="CW.",
    ).exclude(n_attr_display_order=0):
        attr_CW_mask.append((item_attr.n_parameter_bit, 1))
        attr_CW_bit_info.append((item_attr, item_attr.n_parameter_bit))
    attr_CW_mask_int = get_int_from_bits(attr_CW_mask)
    attr_CW_mask_int = attr_CW_mask_int & config_word

    return attr_CW_mask_int, attr_CW_bit_info