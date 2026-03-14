import arcpy
import requests, os, time
from datetime import datetime

VERSION_NUMBER = '5.7'
VERSION_NAME = 'Jayawijaya'
CURRENT_VERSION = f'{VERSION_NUMBER} - {VERSION_NAME}'
SIPENTA_SERVER_INSTALLER_URL = 'https://belajar.atrbpn.go.id/sipenta/tatausaha/apis/installer'
UPDATE_URL = "https://raw.githubusercontent.com/Akring-creator/update-version-repo/main/realease-notes.json"

def current_year():
    try:
        return int(datetime.now().year)
    except Exception:
        return None

def fetch(url, retries=3):
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

        latest_version = data["version"]

        if latest_version != CURRENT_VERSION:
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

        if self.update_check:
            if len(self.update_check) > 0:
                penjelasan.value = (
                    f"Penilaian Tanah versi {CURRENT_VERSION} \n"
                    f"Terdapat versi baru: {self.update_check[2]}\n"
                    "Unduh melalui link berikut:\n"
                    f"{self.update_check[1]}\n\n"
                    "Direktorat Penilaian Tanah dan Ekonomi Pertanahan\n"
                    "Kementrian ATR/BPN\n"
                    "Tahun: {}\n"
                ).format(current_year())

            elif len(self.update_check) == 0:
                penjelasan.value = (
                    f"Penilaian Tanah versi {CURRENT_VERSION} \n"
                    "Belum ada pembaruan aplikasi \n\n"

                    "Direktorat Penilaian Tanah dan Ekonomi Pertanahan\n"
                    "Kementrian ATR/BPN\n"
                    "Tahun: {}\n"

                ).format(current_year())
        else:
            penjelasan.value = (
                f"Penilaian Tanah versi {CURRENT_VERSION} \n"
                "Terdapat kendala mengecek pembaruan aplikasi \n\n"

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

        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return
