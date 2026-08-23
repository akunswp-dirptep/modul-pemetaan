import arcpy
import requests, os, time, sys, json
from datetime import datetime
import urllib.parse

script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

import json
import os

from zntutils.system_utils import generate_key, decrypt_message

# Path ke file metadata
metadata_path = r'C:\PenilaianTanah\app-metadata.bin'

# Nilai default jika file gagal dibaca (opsional, tapi disarankan)
CURRENT_VERSION = None
VERSION_ID = None
CHECK_UPDATE_URL = None

# Membaca file JSON dengan penanganan error (Try-Except)
try:
    metadata = decrypt_message(generate_key(), metadata_path)
    
    # Ekstrak data menggunakan key yang sesuai di JSON
    CURRENT_VERSION = metadata.get("nomor_versi")
    VERSION_ID = metadata.get("id_versi")
    CHECK_UPDATE_URL = metadata.get("check_update_url")
    INSTALLER_URL = metadata.get("installer_url")

except Exception as e:
    arcpy.AddMessage(f"Terjadi kesalahan tak terduga: {e}")

def current_year():
    try:
        return int(datetime.now().year)
    except Exception:
        return None

def fetch(url, retries=3):
    # Mengurangi retries menjadi 3 agar tidak menunggu terlalu lama jika internet mati
    for i in range(retries):
        try:
            r = requests.get(
                url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=5 # Menurunkan timeout agar lebih responsif
            )
            r.raise_for_status()
            return r
        except requests.exceptions.RequestException:
            if i == retries - 1:
                raise
            time.sleep(2)

def check_update():
    try:
        response = fetch(url=CHECK_UPDATE_URL)
        data = response.json()

        latest_version_id = data.get("version_id")
        latest_version = data.get("version")
        update_url = data.get("url")
        changelog = data.get("changelog", "Tidak ada informasi pembaruan tambahan.")

        if latest_version_id != VERSION_ID:
            return {
                "status": "update_available",
                "version": latest_version,
                "url": update_url,
                "changelog": changelog
            }
        else:
            return {"status": "up_to_date"}

    except Exception as e:
        return {"status": "error"}

class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the .pyt file)."""
        self.label = "Toolbox"
        self.alias = "toolbox"
        self.tools = [Catatan_Aplikasi]

class Catatan_Aplikasi:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Cek Pembaruan Aplikasi"
        self.description = "Alat untuk mengecek dan mengunduh versi terbaru aplikasi Penilaian Tanah."

    def getParameterInfo(self):
        """Define the tool parameters."""
        
        penjelasan = arcpy.Parameter(
            displayName='Tentang Aplikasi & Status Pembaruan',
            name='penjelasan',
            datatype='GPString',
            parameterType='Required',
            direction='Input'
        )

        # Teks dasar
        info_teks = (
            f"Penilaian Tanah versi {CURRENT_VERSION} \n\n"
            "Direktorat Penilaian Tanah dan Ekonomi Pertanahan\n"
            "Kementerian ATR/BPN\n"
            f"Tahun: {current_year()}\n"
        )

        # Cek pembaruan otomatis saat tool diklik
        hasil = check_update()

        if hasil["status"] == "update_available":
            info_teks =  (
                f"PEMBARUAN TERSEDIA\n\n"
                f"Versi Sekarang: {CURRENT_VERSION}\n"
                f"Versi Terbaru: {hasil['version']}\n"
                f"Catatan Rilis: {hasil['changelog']}\n\n"
                "Klik tombol 'Run' (Jalankan) di bawah ini\nuntuk mengunduh pembaruan secara otomatis."
            )
        elif hasil["status"] == "up_to_date":
            info_teks = "Aplikasi Anda sudah versi yang paling baru.\nBelum ada pembaruan.\n\n" + info_teks
        else:
            info_teks = "Gagal terhubung ke server untuk mengecek pembaruan.\nPastikan koneksi internet aktif.\n\n" +info_teks

        penjelasan.value = info_teks

        return [penjelasan]

    def isLicensed(self):
        """Set whether the tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        
        arcpy.AddMessage("Memeriksa pembaruan di server...\n")
        hasil = check_update()

        if hasil["status"] == "update_available":
            url_unduh = hasil["url"]
            versi_baru = hasil["version"]
            
            arcpy.AddMessage(f"Ditemukan versi {versi_baru}. Memulai proses pengunduhan...")
            
            # Menentukan lokasi penyimpanan di folder Downloads pengguna
            download_dir = os.path.join(os.path.expanduser('~'), 'Downloads')
            
            # Mencoba mengambil nama file dari URL, atau menggunakan nama default
            parsed_url = urllib.parse.urlparse(url_unduh)
            file_name = os.path.basename(parsed_url.path)
            if not file_name or "." not in file_name:
                file_name = f"Update_Penilaian_Tanah_v{versi_baru}.zip" # Ekstensi default
                
            download_path = os.path.join(download_dir, file_name)

            try:
                # Proses mengunduh file secara chunk (potongan) agar memori aman
                response = requests.get(url_unduh, stream=True)
                response.raise_for_status()
                
                with open(download_path, 'wb') as file:
                    for chunk in response.iter_content(chunk_size=8192):
                        file.write(chunk)
                
                arcpy.AddMessage(f"\n✅ PENGUNDUHAN BERHASIL!")
                arcpy.AddMessage(f"File pembaruan telah disimpan di: {download_path}")
                
            except Exception as e:
                arcpy.AddError(f"❌ Gagal mengunduh file: {str(e)}")

        elif hasil["status"] == "up_to_date":
            arcpy.AddMessage(
                f"Penilaian Tanah di perangkat ini memiliki versi {CURRENT_VERSION}\n"
                "Belum ada pembaruan aplikasi (Anda menggunakan versi terbaru).\n"
            )
            
        else:
            arcpy.AddError(
                f"Penilaian Tanah di perangkat ini memiliki versi {CURRENT_VERSION}\n"
                "Terdapat kendala saat mengecek pembaruan aplikasi. Pastikan koneksi internet Anda stabil."
            )
            
        return