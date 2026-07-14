import arcpy
import requests, os, time, sys, json
from datetime import datetime

script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from zntutils.constant import CURRENT_VERSION, UPDATE_URL, VERSION_ID

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
        response = fetch(url=UPDATE_URL)
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
        self.description = "Alat untuk mengecek ketersediaan versi terbaru aplikasi Penilaian Tanah."

    def getParameterInfo(self):
        """Define the tool parameters."""
        
        penjelasan = arcpy.Parameter(
            displayName='Tentang Aplikasi',
            name='penjelasan',
            datatype='GPString',
            parameterType='Required',
            direction='Input'
        )

        penjelasan.value = (
            f"Penilaian Tanah versi {CURRENT_VERSION} \n"
            "Jalankan tools untuk mengecek pembaruan aplikasi \n\n"
            "Direktorat Penilaian Tanah dan Ekonomi Pertanahan\n"
            "Kementerian ATR/BPN\n"
            f"Tahun: {current_year()}\n"
        )

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
        
        arcpy.AddMessage("Sedang memeriksa pembaruan di server...\n")
        hasil = check_update()

        if hasil["status"] == "update_available":
            arcpy.AddMessage(
                f"Penilaian Tanah di perangkat ini memiliki versi {CURRENT_VERSION}\n"
                f"Terdapat versi baru: {hasil['version']}\n"
                f"Catatan Rilis: {hasil['changelog']}\n"
            )

            message_structure = {
                "element": "content",
                "data": [
                    "Unduh melalui tautan berikut: ",
                    {
                        "element": "hyperlink",
                        "data": "Unduh Pembaruan Aplikasi",
                        "link": hasil["url"]
                    }
                ]
            }

            arcpy.AddMessage(f"json:{json.dumps(message_structure)}")

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