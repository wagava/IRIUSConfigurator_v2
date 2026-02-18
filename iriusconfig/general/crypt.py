from cryptography.fernet import Fernet
import os


# def get_secret_key(key_file="secret.key"):
#     """
#     Генерирует новый секретный ключ или загружает существующий из файла.
#     """
#     if os.path.exists(key_file):
#         with open(key_file, "rb") as key_file:
#             key = key_file.read()
#     else:
#         key = Fernet.generate_key()
#         with open(key_file, "wb") as key_file:
#             key_file.write(key)
#     return key


def encrypt_password(password, key):
    """
    Шифрует пароль с использованием секретного ключа.
    """
    cipher_suite = Fernet(key)
    encrypted_password = cipher_suite.encrypt(password.encode())
    return encrypted_password


def decrypt_password(encrypted_password, key):
    """
    Дешифрует пароль с использованием секретного ключа.
    """
    cipher_suite = Fernet(key)
    decrypted_password = cipher_suite.decrypt(encrypted_password).decode()
    return decrypted_password


# def save_encrypted_password_to_file(encrypted_password, file_name="password.enc"):
#     """
#     Сохраняет зашифрованный пароль в файл.
#     """
#     with open(file_name, "wb") as file:
#         file.write(encrypted_password)


# def load_encrypted_password_from_file(file_name="password.enc"):
#     """
#     Читает зашифрованный пароль из файла.
#     """
#     with open(file_name, "rb") as file:
#         encrypted_password = file.read()
#     return encrypted_password