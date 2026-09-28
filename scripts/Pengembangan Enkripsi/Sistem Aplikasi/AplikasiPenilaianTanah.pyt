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
        self.tools = [Catatan_Aplikasi, Cek_Zona_Awal]

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


class Cek_Zona_Awal(object):
    def __init__(self):
        self.label = "Cek Aturan Zona Berdasarkan Persil"
        self.description = "Validasi: 1) Tidak memotong persil, 2) Tidak boleh 1 persil, 3) Luas minimum sesuai skala."
        self.canRunInBackground = False

    def getParameterInfo(self):
        param0 = arcpy.Parameter(
            displayName="Layer Zona (Target)",
            name="in_zona",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        param0.filter.list = ["Polygon"]

        param1 = arcpy.Parameter(
            displayName="Layer Persil (Bidang Tanah)",
            name="in_persil",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        param1.filter.list = ["Polygon"]

        param2 = arcpy.Parameter(
            displayName="Skala Peta",
            name="in_skala",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        param2.value = 5000 

        param3 = arcpy.Parameter(
            displayName="Output Hasil Pengecekan",
            name="out_zona",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output")

        return [param0, param1, param2, param3]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        in_zona = parameters[0].valueAsText
        in_persil = parameters[1].valueAsText
        skala = parameters[2].value
        out_zona = parameters[3].valueAsText

        # --- 1. Tentukan Luas Minimal ---
        if skala == 25000:
            luas_minimal = 15625.0
        elif skala == 10000:
            luas_minimal = 2500.0
        elif skala == 5000:
            luas_minimal = 625.0
        elif skala == 2500:
            luas_minimal = 156.25
        else:
            luas_minimal = (0.005 * skala) ** 2
            
        messages.addMessage(f"--> Target Skala: 1:{skala} | Luas minimal: {luas_minimal} m2")

        # Samakan Environment Koordinat agar hitungan luas akurat
        arcpy.env.outputCoordinateSystem = arcpy.Describe(in_zona).spatialReference

        # --- 2. Persiapkan Output ---
        messages.addMessage("--> Membuat output layer...")
        arcpy.management.CopyFeatures(in_zona, out_zona)

        arcpy.management.AddField(out_zona, "Err_Luas", "TEXT", field_length=10)
        arcpy.management.AddField(out_zona, "Err_Potong", "TEXT", field_length=10)
        arcpy.management.AddField(out_zona, "Err_1Prsl", "TEXT", field_length=10)
        arcpy.management.AddField(out_zona, "Luas_M2", "DOUBLE")
        arcpy.management.AddField(out_zona, "Jml_Prsl", "SHORT")

        zona_status = {}
        with arcpy.da.SearchCursor(out_zona, ['OID@', 'SHAPE@AREA']) as cursor:
            for row in cursor:
                oid = row[0]
                area = row[1]
                zona_status[oid] = {
                    'err_luas': "Ya" if area < luas_minimal else "Tidak",
                    'luas': area
                }

        # --- 3. Kumpulkan Area Persil ---
        messages.addMessage("--> Membaca area Persil Asli...")
        persil_area_dict = {}
        with arcpy.da.SearchCursor(in_persil, ['OID@', 'SHAPE@AREA']) as cursor:
            for row in cursor:
                persil_area_dict[row[0]] = row[1]

        # --- 4. Intersect ---
        messages.addMessage("--> Menjalankan perpotongan (Pairwise Intersect)...")
        memory_intersect = r"memory\intersect_zona_persil"
        if arcpy.Exists(memory_intersect):
            arcpy.management.Delete(memory_intersect)

        # Menggunakan PairwiseIntersect (lebih tahan error topologi)
        arcpy.analysis.PairwiseIntersect([in_zona, in_persil], memory_intersect, "ONLY_FID")

        # Deteksi urutan kolom FID secara dinamis untuk mencegah BUG ArcGIS 
        fid_fields = [f.name for f in arcpy.ListFields(memory_intersect) if f.name.startswith("FID_")]
        if len(fid_fields) < 2:
            messages.addErrorMessage("Gagal memproses perpotongan (Kolom FID tidak lengkap).")
            return
            
        fid_zona_field = fid_fields[0]
        fid_persil_field = fid_fields[1]

        # Cek jika arcgis memutar urutan kolom ID
        swap_detected = False
        with arcpy.da.SearchCursor(memory_intersect, [fid_fields[0], fid_fields[1]]) as cur:
            for row in cur:
                if (row[0] not in zona_status) and (row[0] in persil_area_dict) and (row[1] in zona_status):
                    swap_detected = True
                    break
                    
        if swap_detected:
            messages.addMessage("--> [INFO] Mengkoreksi bug urutan ID dari ArcGIS...")
            fid_zona_field = fid_fields[1]
            fid_persil_field = fid_fields[0]

        # --- 5. Analisis Perpotongan ---
        messages.addMessage("--> Mengevaluasi Aturan Potongan & Jumlah Persil...")
        
        # PARAMETER ATURAN:
        TOLERANCE_FULL = 0.995 # Jika > 99.5% dari Persil masuk ke zona, dianggap masuk utuh.
        MIN_AREA_POTONG = 0.1  # Jika potongan > 0.1 m2 (10x10 cm), langsung tercatat sebagai MEMOTONG.

        zona_persil_count = {oid: 0 for oid in zona_status.keys()}
        zona_potong_flag = {oid: False for oid in zona_status.keys()}

        with arcpy.da.SearchCursor(memory_intersect, [fid_zona_field, fid_persil_field, 'SHAPE@AREA']) as cursor:
            for row in cursor:
                z_oid = row[0]
                p_oid = row[1]
                int_area = row[2]

                if p_oid not in persil_area_dict or z_oid not in zona_status:
                    continue
                
                p_area = persil_area_dict[p_oid]
                if p_area == 0:
                    continue

                rasio_irisan = int_area / p_area

                if rasio_irisan >= TOLERANCE_FULL:
                    # Persil SEPENUHNYA ada di dalam zona
                    zona_persil_count[z_oid] += 1
                elif int_area > MIN_AREA_POTONG:
                    # Persil HANYA SEBAGIAN berada di dalam zona (terpotong oleh batas)
                    zona_potong_flag[z_oid] = True
                    zona_persil_count[z_oid] += 1

        # --- 6. Simpan Hasil ---
        messages.addMessage("--> Menyimpan hasil ke Attribute Table...")
        with arcpy.da.UpdateCursor(out_zona, ['OID@', 'Err_Luas', 'Err_Potong', 'Err_1Prsl', 'Luas_M2', 'Jml_Prsl']) as cursor:
            for row in cursor:
                oid = row[0]
                if oid in zona_status:
                    # Err_Luas
                    row[1] = zona_status[oid]['err_luas']
                    
                    # Err_Potong
                    row[2] = "Ya" if zona_potong_flag.get(oid, False) else "Tidak"
                    
                    # Err_1Prsl
                    jml = zona_persil_count.get(oid, 0)
                    row[3] = "Ya" if jml == 1 else "Tidak"
                    
                    row[4] = zona_status[oid]['luas']
                    row[5] = jml

                    cursor.updateRow(row)

        if arcpy.Exists(memory_intersect):
            arcpy.management.Delete(memory_intersect)

        messages.addMessage("✅ Proses Selesai. Silakan periksa Layer Output.")
        return