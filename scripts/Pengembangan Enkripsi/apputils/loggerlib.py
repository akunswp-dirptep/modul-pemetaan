import arcpy
import time, requests
import json, os
from datetime import datetime
from .secure import get_all_config, generate_key, setup_project_config, renew_multiple_user_data
from cryptography.fernet import Fernet

class ToolLogger:
    def __init__(self, tool_name):
        self.tool_name = tool_name
        self.start_time = time.time()
        self.app_log_path = r'C:\PenilaianTanah\config\penilaiantanah.bin'
        arcpy.AddMessage(f"=== [{self.tool_name}] Start Time: {time.strftime('%A, %d %B %Y %H:%M:%S')} ===")

    def info(self, message, project_config_path=None):
        """Menandai tahapan utama proses dan mencatatnya ke file biner terenkripsi""" 
        json_app = get_all_config() 
        
        user_credential = json_app.get('user_credential', {})
        user_name = user_credential.get('nama_pengguna', 'Unknown')

        waktu = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        key = generate_key()
        fernet = Fernet(key)
        
        # 2. CATAT LOG APLIKASI
        log_teks_app = f'[INFO][{waktu}][{self.tool_name}][{user_name}]-{message}'
        encrypted_log_app = fernet.encrypt(log_teks_app.encode('utf-8'))

        app_dir = os.path.dirname(self.app_log_path)
        app_log_activity_path = os.path.join(app_dir, 'app_activity.bin')
        with open(app_log_activity_path, 'ab') as f:
            f.write(encrypted_log_app + b'\n')

        if project_config_path:
            json_project = get_all_config(project_config_path)
            kab_kota = json_project.get('WADMKK', 'Unknown')
            
            log_teks_project = f'[INFO][{waktu}][{self.tool_name}][{user_name}][{kab_kota}]-{message}'
            encrypted_log_project = fernet.encrypt(log_teks_project.encode('utf-8'))
            
            project_dir = os.path.dirname(project_config_path)
            project_log_path = os.path.join(project_dir, 'project_activity.bin')
            
            with open(project_log_path, 'ab') as f:
                f.write(encrypted_log_project + b'\n')

        arcpy.AddMessage(f"\n*** {message.upper()} ***")

    def step(self, message):
        """Pesan detail/sub-langkah"""
        arcpy.AddMessage(f"   -> {message}")

    def warning(self, message, project_config_path = None):
        """Peringatan non-fatal"""
        json_app = get_all_config() 
        
        user_credential = json_app.get('user_credential', {})
        user_name = user_credential.get('nama_pengguna', 'Unknown')

        waktu = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        key = generate_key()
        fernet = Fernet(key)
        
        # 2. CATAT LOG APLIKASI
        log_teks_app = f'[WARNING][{waktu}][{self.tool_name}][{user_name}]-{message}'
        encrypted_log_app = fernet.encrypt(log_teks_app.encode('utf-8'))

        app_dir = os.path.dirname(self.app_log_path)
        app_log_activity_path = os.path.join(app_dir, 'app_activity.bin')
        with open(app_log_activity_path, 'ab') as f:
            f.write(encrypted_log_app + b'\n')

        if project_config_path:
            json_project = get_all_config(project_config_path)
            kab_kota = json_project.get('WADMKK', 'Unknown')
            
            log_teks_project = f'[WARNING][{waktu}][{self.tool_name}][{user_name}][{kab_kota}]-{message}'
            encrypted_log_project = fernet.encrypt(log_teks_project.encode('utf-8'))
            
            project_dir = os.path.dirname(project_config_path)
            project_log_path = os.path.join(project_dir, 'project_activity.bin')
            
            with open(project_log_path, 'ab') as f:
                f.write(encrypted_log_project + b'\n')

        arcpy.AddWarning(f"[WARNING] {message}")

    def error(self, message, project_config_path = None):
        """Pesan kesalahan"""
        json_app = get_all_config() 
        
        user_credential = json_app.get('user_credential', {})
        user_name = user_credential.get('nama_pengguna', 'Unknown')

        waktu = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        key = generate_key()
        fernet = Fernet(key)
        
        # 2. CATAT LOG APLIKASI
        log_teks_app = f'[ERROR][{waktu}][{self.tool_name}][{user_name}]-{message}'
        encrypted_log_app = fernet.encrypt(log_teks_app.encode('utf-8'))

        app_dir = os.path.dirname(self.app_log_path)
        app_log_activity_path = os.path.join(app_dir, 'app_activity.bin')
        with open(app_log_activity_path, 'ab') as f:
            f.write(encrypted_log_app + b'\n')

        if project_config_path:
            json_project = get_all_config(project_config_path)
            kab_kota = json_project.get('WADMKK', 'Unknown')
            
            log_teks_project = f'[ERROR][{waktu}][{self.tool_name}][{user_name}][{kab_kota}]-{message}'
            encrypted_log_project = fernet.encrypt(log_teks_project.encode('utf-8'))
            
            project_dir = os.path.dirname(project_config_path)
            project_log_path = os.path.join(project_dir, 'project_activity.bin')
            
            with open(project_log_path, 'ab') as f:
                f.write(encrypted_log_project + b'\n')
        arcpy.AddError(f"[ERROR] {message}")

    def kirim_log_ke_server(self, log_path=r"C:\PenilaianTanah\config\app_activity.bin"):
        """Membaca log biner, mengirim ke server, dan menghapus log jika sukses terkirim."""

        if not os.path.exists(log_path):
            return
            
        processing_path = log_path + ".processing"
        
        # 1. KUNCI DATA: Ubah nama file agar log baru yang masuk tidak terganggu
        try:
            if os.path.exists(processing_path):
                with open(log_path, 'rb') as f_baru, open(processing_path, 'ab') as f_proses:
                    f_proses.write(f_baru.read())
                os.remove(log_path)
            else:
                os.rename(log_path, processing_path)
        except Exception as e:
            print(f"Gagal menyiapkan file log untuk dikirim: {e}")
            return

        # 2. DEKRIPSI DATA
        key = generate_key()
        fernet = Fernet(key)
        log_terkumpul = []
        
        with open(processing_path, 'rb') as f:
            baris_baris = f.readlines()
            
        for baris in baris_baris:
            if baris.strip():
                try:
                    decrypted = fernet.decrypt(baris.strip()).decode('utf-8')
                    log_terkumpul.append(decrypted)
                except Exception:
                    pass 
                    
        if not log_terkumpul:
            os.remove(processing_path)
            return

        # 3. KIRIM KE API (Gunakan form-data sesuai spesifikasi postman)
        # Anda bisa mengirim seluruh log sekaligus (digabung) atau satu per satu
        # Di sini kita gabungkan semua baris log menjadi 1 string panjang pada param 'deskripsi' agar hemat kuota request
        gabungan_log = "\n".join(log_terkumpul)
        
        url = "https://belajar.atrbpn.go.id/sipenta/tatausaha/api/pemetaan/log/send"
        
        payload = {
            'tipe': 'INFO_SISTEM',  # Sesuaikan dengan tipe yang Anda butuhkan (misal: "ERROR" atau "INFO")
            'deskripsi': gabungan_log
        }
        
        try:
            # Mengirim request HTTP POST, data otomatis dikonversi jadi form-data
            response = requests.post(url, data=payload, timeout=60)
            
            if response.status_code == 200:
                resp_json = response.json()
                # 4. HAPUS FILE JIKA SUKSES
                if resp_json.get('success') == True:
                    os.remove(processing_path)
                    print(resp_json.get('message', 'Berhasil menyimpan log pemetaan!'))
                else:
                    print(f"Gagal menyimpan di server: {resp_json}")
            else:
                print(f"Terjadi masalah pada server. Status Code: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"Gagal terhubung ke API SIPENTA: {e}")
            # Karena terjadi error (timeout/putus), file .processing dibiarkan saja 
            # sehingga datanya tidak hilang dan bisa dikirim ulang nanti.
            
    def finish(self, success=True):
        elapsed = time.time() - self.start_time
        status = "BERHASIL" if success else "GAGAL"
        arcpy.AddMessage(f"\n=== Proses {status} dalam {elapsed:.2f} detik ===")