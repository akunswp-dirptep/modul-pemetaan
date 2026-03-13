import arcpy
import requests, os
from datetime import datetime

CURRENT_VERSION = "5.8 - Jayawijaya"
UPDATE_URL = "https://drive.google.com/uc?export=download&id=15jGbZjP8bk0OFgg9voP4m_QCWBuWSkiK"


def current_year():
    try:
        return int(datetime.now().year)
    except Exception:
        return None

def check_update():
    try:
        response = requests.get(UPDATE_URL)
        data = response.json()

        latest_version = data["version"]

        if latest_version != CURRENT_VERSION:
            pesan = 'Versi terbaru tersedia: {}.\nJalankan tool untuk mendownload versi terbaru.'.format(latest_version)    
            return [pesan, data["url"], latest_version]
        else:
            return None

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
        self.label = "Tentang Aplikasi"
        self.description = ""

    def getParameterInfo(self):
        """Define the tool parameters."""

        update_check = check_update()
        
        penjelasan = arcpy.Parameter(
            displayName='Tentang Aplikasi',
            name = 'penjelasan',
            datatype = 'GPString',
            parameterType='Required',
            direction='Input'
        )


        if update_check:
            penjelasan.value = (
                "Penilaian Tanah versi 5.8 - Jayawijaya \n\n"
                "Direktorat Penilaian Tanah dan Ekonomi Pertanahan\n"
                "Kementrian ATR/BPN\n"
                "Tahun: {}\n\n"
            ).format(current_year()) + "{}".format(update_check[0])
        else:
            penjelasan.value = (
                "Penilaian Tanah versi 5.8 - Jayawijaya \n\n"
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
        update_check = check_update()

        if update_check:
            response =requests.get(update_check[1], timeout=60)
            data = response.json()
            link = data['data'][0]['url']

            downloads_folder = os.path.join(os.path.expanduser("~"), "Downloads")

            r = requests.get(link, stream=True)

            filename = os.path.join(downloads_folder, 'PenilaianTanah versi {}.exe'.format(update_check[2]))
            with open(filename, 'wb') as f:
                for chunk in r.iter_content(1024):
                    f.write(chunk)
        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return
