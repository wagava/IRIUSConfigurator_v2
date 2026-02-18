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
