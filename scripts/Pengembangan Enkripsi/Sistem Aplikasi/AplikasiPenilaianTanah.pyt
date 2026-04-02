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

def fetch(url, retries=5):
    for i in range(retries):
        try:
            r = requests.get(
                url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=10
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

        latest_version = data["version_id"]

        if latest_version != VERSION_ID:
            pesan = 'Versi terbaru tersedia: {}.\nJalankan tool untuk mendownload versi terbaru.'.format(latest_version)    
            return [pesan, data["url"], latest_version]
        else:
            return []

    except Exception as e:
        return None

class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [Catatan_Aplikasi]


class Catatan_Aplikasi:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Cek Pembaruan Aplikasi"
        self.description = ""

    def getParameterInfo(self):
        """Define the tool parameters."""

        self.update_check = check_update()
        
        penjelasan = arcpy.Parameter(
            displayName='Tentang Aplikasi',
            name = 'penjelasan',
            datatype = 'GPString',
            parameterType='Required',
            direction='Input'
        )

        penjelasan.value = (
                f"Penilaian Tanah versi {CURRENT_VERSION} \n"
                "Jalankan tools untuk mengecek pembaruan aplikasi \n\n"

                "Direktorat Penilaian Tanah dan Ekonomi Pertanahan\n"
                "Kementrian ATR/BPN\n"
                "Tahun: {}\n"

            ).format(current_year())

        return [penjelasan]

    def isLicensed(self):
        """Set whether the tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter. This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        hasil = check_update()


        if hasil is not None:
            if len(hasil) > 0:
                arcpy.AddMessage(
                    f"Penilaian Tanah di perangkat ini\n"
                    f"memiliki versi {CURRENT_VERSION} \n"
                    f"Terdapat versi baru: {hasil[2]}\n"

                )

                link_variable = f"{hasil[1]}"
                message_structure = {
                    "element": "content",
                    "data": [
                        "Unduh melalui link berikut: ",
                        {
                            "element": "hyperlink",
                            "data": "Pembaruan Aplikasi",
                            "link": link_variable
                        }
                    ]
                }

                arcpy.AddMessage(f"json:{json.dumps(message_structure)}")

            elif len(hasil) == 0:
                arcpy.AddMessage(
                    f"Penilaian Tanah di perangkat ini\n"
                    f"memiliki versi {CURRENT_VERSION} \n"
                    "Belum ada pembaruan aplikasi \n\n"
                )
        else:
            arcpy.AddMessage(
                    f"Penilaian Tanah di perangkat ini\n"
                    f"memiliki versi {CURRENT_VERSION} \n"
                    "Terdapat kendala mengecek pembaruan aplikasi \n\n"
            )
        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return
