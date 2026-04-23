import json
import os, datetime
from datetime import datetime
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

def current_year():
    try:
        return int(datetime.now().year)
    except Exception:
        return None
 
# Cryptography Functions
def generate_key():
    password = 'bpnri-jakarta'
    salt = b'Sisinga@2-Jakarta'  

    # Derive proper key dari password
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key

def simpan_ke_bin(data_terenkripsi, nama_file):
    """Menyimpan data bytes ke dalam file biner."""
    try:
        with open(nama_file, 'wb') as file:
            file.write(data_terenkripsi)
        print(f"Pesan berhasil disimpan ke {nama_file}")
    except IOError as e:
        print(f"Terjadi kesalahan saat menulis ke file: {e}")

def baca_dari_bin(nama_file):
    """Membaca data bytes dari file biner."""
    data_terenkripsi = None
    try:
        with open(nama_file, 'rb') as file:
            data_terenkripsi = file.read()
        print(f"Pesan berhasil dibaca dari {nama_file}")
        return data_terenkripsi
    except IOError as e:
        print(f"Terjadi kesalahan saat membaca file: {e}")
        return None
    
def encrypt_message(message: str, key: bytes, path) -> bytes:
    fernet = Fernet(key)
    encrypted_message = fernet.encrypt(message.encode())
    simpan_ke_bin(encrypted_message, path)
    return encrypted_message

def decrypt_message(key: bytes, path) -> str:
    encrypted_message = baca_dari_bin(path)
    fernet = Fernet(key)
    decrypted_message = fernet.decrypt(encrypted_message).decode()
    data = json.loads(decrypted_message)
    return data

def get_all_config(config_path = None):
    config_path = r'C:\PenilaianTanah\config\penilaiantanah.bin' if config_path is None else config_path
    try:
        if os.path.exists(config_path):
            data = decrypt_message(generate_key(), config_path) 
            return data
        else:
            return None
        
    except Exception as e:
        return None

print(get_all_config())