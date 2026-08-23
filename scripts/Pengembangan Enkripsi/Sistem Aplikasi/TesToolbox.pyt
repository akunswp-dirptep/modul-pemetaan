import arcpy
import requests
import time, os, sys

# Tambahkan parent directory ke sys.path
script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from zntutils.system_utils import decrypt_message, generate_key
# ==========================================
# 2. FUNGSI UTAMA ANDA
# ==========================================
def check_required_update():
    def fetch(url, retries=3):
        # Mengurangi retries menjadi 3 agar tidak menunggu terlalu lama jika internet mati
        for i in range(retries):
            try:
                r = requests.get(
                    url,
                    headers={"User-Agent": "Mozilla/5.0"},
                    timeout=5 
                )
                r.raise_for_status()
                return r
            except requests.exceptions.RequestException:
                if i == retries - 1:
                    raise
                time.sleep(2)

    # Path ke file metadata
    metadata_path = r'C:\PenilaianTanah\app-metadata.bin'

    CURRENT_VERSION = None
    CURRENT_NUMBER = None
    VERSION_ID = None
    CHECK_UPDATE_URL = None

    try:
        metadata = decrypt_message(generate_key(), metadata_path)
        
        # Ekstrak data menggunakan key yang sesuai di JSON
        CURRENT_VERSION = metadata.get("nomor_versi")
        CURRENT_NUMBER = metadata.get("current_number")
        VERSION_ID = metadata.get("id_versi")
        CHECK_UPDATE_URL = metadata.get("check_update_url")
        INSTALLER_URL = metadata.get("installer_url")

    except Exception as e:
        arcpy.AddError(f"Terjadi kesalahan saat dekripsi metadata: {e}")
        return {"status": "error"}

    try:
        # Tambahan validasi jika URL kosong agar tidak error di fungsi fetch
        if not CHECK_UPDATE_URL:
            arcpy.AddError("URL Update tidak ditemukan di file metadata.")
            return {"status": "error"}

        response = fetch(url=CHECK_UPDATE_URL)
        data = response.json()

        min_required_version = data.get('min_required_version')

        if CURRENT_NUMBER < min_required_version:
            return "Butuh Pembaruan"
        else:
            return "Tidak Butuh Pembaruan"

    except Exception as e:
        arcpy.AddError(f"Gagal mengambil data dari server: {e}")
        return {"status": "error"}


# ==========================================
# 3. STRUKTUR PYTHON TOOLBOX (PYT)
# ==========================================
class Toolbox(object):
    def __init__(self):
        self.label = "Pengembangan Enkripsi ZNT"
        self.alias = "znt_utils"
        self.tools = [TestCheckUpdate]


class TestCheckUpdate(object):
    def __init__(self):
        self.label = "Test Check Required Update"
        self.description = "Mengecek apakah aplikasi membutuhkan pembaruan berdasarkan metadata lokal."
        self.canRunInBackground = False

    def getParameterInfo(self):
        # Tidak ada parameter input yang dibutuhkan (path hardcoded di fungsi)
        return []

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        pass

    def updateMessages(self, parameters):
        pass

    def execute(self, parameters, messages):
        arcpy.AddMessage("Memulai pengecekan update...")
        
        # Eksekusi fungsi
        hasil = check_required_update()
        
        # Menampilkan output di Message Window ArcGIS
        if isinstance(hasil, str):
            if hasil == "Butuh Pembaruan":
                arcpy.AddWarning(f"STATUS: {hasil} (Aplikasi Harus Diupdate)")
            else:
                arcpy.AddMessage(f"STATUS: {hasil} (Aplikasi Aman Digunakan)")
        else:
            arcpy.AddError(f"STATUS: Gagal melakukan pengecekan update. Output: {hasil}")
        
        return