import json
import os, arcpy, datetime
from datetime import datetime
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64



 
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
def setup_user_data(key:str, value:str):

    config_path = r'C:\PenilaianTanah\config\penilaiantanah.bin'

    try:
        # Cek apakah file ada
        if os.path.exists(config_path):
            # File ada, baca isinya
            try:
                data = decrypt_message(generate_key(), config_path)                    
                # Validasi format JSON
                if key not in data or not isinstance(data.get(key), str):
                    # Format tidak sesuai, tambahkan atau perbarui data
                    data[key] = value
                
                if data[key] != value:
                    data[key] = value
                    
            except json.JSONDecodeError:
                # File rusak/tidak valid, buat struktur baru
                arcpy.AddWarning("File config.json rusak, membuat struktur baru...")
                data = {key: value}
        else:
            # File belum ada, buat struktur baru
            # Pastikan direktori Menu ada
            menu_dir = os.path.dirname(config_path)
            if not os.path.exists(menu_dir):
                os.makedirs(menu_dir)
            
            data = {key: value}
        

        # Simpan kembali ke file
        encrypt_message(json.dumps(data), generate_key(), config_path)
        
        return True
        
    except Exception as e:
        arcpy.AddError(f"Gagal menyimpan user config: {str(e)}")
        return False
def setup_project_config(data_dict: dict, config_path):
    
    for key, value in data_dict.items():
        try:
            # Cek apakah file ada
            if os.path.exists(config_path):
                # File ada, baca isinya
                try:
                    data = decrypt_message(generate_key(), config_path)                    
                    # Validasi format JSON
                    if key not in data or not isinstance(data.get(key), str):
                        # Format tidak sesuai, tambahkan atau perbarui data
                        data[key] = value
                    
                    if data[key] != value:
                        data[key] = value
                        
                except json.JSONDecodeError:
                    # File rusak/tidak valid, buat struktur baru
                    arcpy.AddWarning("File config.json rusak, membuat struktur baru...")
                    data = {key: value}
            else:
                # File belum ada, buat struktur baru
                # Pastikan direktori Menu ada
                menu_dir = os.path.dirname(config_path)
                if not os.path.exists(menu_dir):
                    os.makedirs(menu_dir)
                
                data = {key: value}

            # Simpan kembali ke file
            encrypt_message(json.dumps(data), generate_key(), config_path)
            
        except Exception as e:
            arcpy.AddError(f"Gagal menyimpan user config: {str(e)}")
            return False
    return True
def get_all_berkas_id(process_type = None, DATA_KEY = "user_credential"):

    process_mapping = {
        'Pembuatan ZNT': '01',
        'Pembaruan ZNT': '02',
        'Pembuatan NBT': '03',
        'Pembaruan NBT': '04',
    }

    mapped_process_code = process_mapping.get(process_type) if process_type is not None else None

    config_path = r'C:\PenilaianTanah\config\penilaiantanah.bin'
    try:
        if os.path.exists(config_path):
            data = decrypt_message(generate_key(), config_path) 
            user_data = data.get(DATA_KEY, {})
            if len(user_data.get('berkas', [])) > 0:
                data_berkas = []
                for berkas in user_data['berkas']:
                    berkas_id_key = 'no_berkas'

                    no_berkas = berkas.get(berkas_id_key, None)
                    bisa_upload = berkas.get('can_upload', False)

                    if mapped_process_code is not None:
                        nomor_depan = (no_berkas or '').split('/')[0]
                        if nomor_depan != mapped_process_code:
                            continue

                    data_berkas.append((no_berkas, bisa_upload ))

                def sort_key(item):
                    no_berkas = item[0] or ""
                    parts = no_berkas.split('/')

                    if len(parts) < 3:
                        return (9999, 0, no_berkas)

                    try:
                        nomor_grup = int(parts[0])
                        nomor_urut = int(parts[-1])
                        return (nomor_grup, -nomor_urut, no_berkas)
                    except ValueError:
                        return (9999, 0, no_berkas)

                data_berkas.sort(key=sort_key)

                if len(data_berkas) == 0:
                    return None
                
                return data_berkas

        else:
            return None
        
    except Exception as e:
        return None

project_config = r'E:\Akmal\Jobdesk\Uji Coba Plugin Penilaian Tanah\Pembaruan ZNT\Uji Coba Versi 6 2704\penilaian_tanah_config.bin'

reset_last_sample = {
    'last_sample_id': 0
}
# setup_project_config(reset_last_sample, project_config)
print(get_all_config(r"E:\Majene_8\penilaian_tanah_config.bin"))
# print(get_user_data('preferred_berkas_id'))