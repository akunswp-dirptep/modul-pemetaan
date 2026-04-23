import arcpy
from datetime import datetime
import requests, os, sys, time
import json, subprocess, shutil, subprocess

script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from zntutils.system_utils import renew_user_data, get_all_config, get_user_data, clear_user_data, get_all_berkas_id, renew_multiple_user_data
from zntutils.constant import THIRD_PARTY_DATA_KEY, NIK_KEY, AUTH_KEY, PREFERRED_SERVER_KEY, YEAR_KEY, SSO_DATA_KEY

class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [Login_Pihak_Ketiga, Logout_Pengguna, Login_SSO]


class Login_Pihak_Ketiga:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Login Pemeta Pihak Ketiga"
        self.description = ""

    def getParameterInfo(self):
        """Define the tool parameters."""
        user_data = get_user_data(THIRD_PARTY_DATA_KEY)
        sso_data = get_user_data(SSO_DATA_KEY)

        penjelasan = arcpy.Parameter(
            displayName="Penjelasan",
            name="penjelasan",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )
        already_user_login_explanation = (
            "Anda sudah login sebagai Pemeta Pihak Ketiga\n"
            "Dengan Kredensial sebagai berikut:\n"
                f"NIK: {user_data.get(NIK_KEY, 'N/A')}\n"
            "Untuk menggunakan SSO, Anda harus logout\n"
            "terlebih dahulu\n\n"
            "Direktorat Penilaian Tanah & Ekonomi Pertanahan\n"
            "Kementerian ATR/BPN\n"
            "Tahun: {}".format(datetime.now().year)
        )
        already_login_sso_explanation = (
            "Anda sudah login menggunakan SSO\n"
            "Untuk menggunakan Pemeta, Anda harus logout\n"
            "terlebih dahulu\n\n"
            "Direktorat Penilaian Tanah & Ekonomi Pertanahan\n"
            "Kementerian ATR/BPN\n"
            "Tahun: {}".format(datetime.now().year)
        )
        input_nik = arcpy.Parameter(
            displayName="NIK Pemeta Nilai Tanah (16 digit)",
            name="username",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
            )

        input_password = arcpy.Parameter(
            displayName="Password",
            name="password",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        server = arcpy.Parameter(
            displayName="Server Sipenta",
            name="link",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        automatic_reload = arcpy.Parameter(
            displayName="Reload Otomatis ArcGIS Pro setelah login berhasil",
            name="automatic_reload",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )

        automatic_reload.value = False
        
        server.filter.type = "ValueList"
        server.filter.list = ["Belajar", "Produksi"]
        server.value = "Belajar"
        if user_data:
            penjelasan.value = already_user_login_explanation
            return [penjelasan]
        if sso_data:
            penjelasan.value = already_login_sso_explanation
            return [penjelasan]
        else: 
            return [input_nik, input_password, server, automatic_reload]

    def isLicensed(self):
        """Set whether the tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        user_data = get_user_data(THIRD_PARTY_DATA_KEY)
        sso_data = get_user_data(SSO_DATA_KEY)
        if user_data is None and sso_data is None:
            input_nik = parameters[0]
            reload_automatic = parameters[3]

            if input_nik.value:
                # Trim semua spasi (leading, trailing, dan di tengah)
                nik_str = str(input_nik.value).replace(" ", "")
                # sinkronkan nilai parameter yang ditampilkan
                input_nik.value = nik_str
                
                # Cek apakah hanya berisi angka
                if not nik_str.isdigit():
                    input_nik.setErrorMessage("NIK harus berisi angka saja")
                # Cek apakah panjangnya tepat 16
                elif len(nik_str) != 16:
                    input_nik.setErrorMessage(f"NIK harus tepat 16 digit (saat ini: {len(nik_str)} digit)")
                else:
                    input_nik.clearMessage()
            

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter. This method is called after internal validation."""
        user_data = get_user_data(THIRD_PARTY_DATA_KEY)
        sso_data = get_user_data(SSO_DATA_KEY)
        if user_data is None and sso_data is None:
            automatic_reload = parameters[3]
            if automatic_reload.value == True:
                automatic_reload.clearMessage()
                automatic_reload.setWarningMessage(
                    "Setelah login berhasil, ArcGIS Pro akan otomatis restart. Simpan pekerjaan Anda terlebih dahulu untuk mencegah kehilangan data."
                )

        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        user_data = get_user_data(THIRD_PARTY_DATA_KEY)
        sso_data = get_user_data(SSO_DATA_KEY)
        if user_data is None and sso_data is None:
            nik = parameters[0].value
            password = parameters[1].value
            server = parameters[2].value
            automatic_reload = parameters[3].value
            use_production = True if server == "Produksi" or server == None else False

            self.call_sipenta_api(nik, password, use_production, automatic_reload)


        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""


        return
    
    def call_sipenta_api(self, nik, password, use_production=True, automatic_reload=False):
        """
        Fungsi untuk memanggil API SIPENTA dan mendapatkan data survey.
        
        Parameters:
        nik (str): NIK pengguna untuk autentikasi API
        password (str): Password pengguna untuk autentikasi API
        use_production (bool): True untuk production URL, False untuk testing URL
        automatic_reload (bool): True untuk reload otomatis setelah login berhasil
        
        Returns:
        dict: Data response dari API dalam format dictionary
        """
        
        # URL untuk testing dan produksi
        test_url = f"https://belajar.atrbpn.go.id/sipenta/tatausaha-2/login/3/pemeta"
        prod_url = f"https://sipentan.go.id/tatausaha-2/login/3/pemeta"
    
        # url = prod_url if use_production else test_url
        url = prod_url if use_production else test_url

        try:
            # Mengambil data dari API

            payload = {
                "nik": nik,
                "password": password
            }

            response = requests.post(url, data=payload, timeout=60)  

            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    with open(os.path.join(os.path.dirname(__file__), "login_response_pk.json"), "w") as f:
                        json.dump(data, f, indent=4)
                    renew_data = {
                        THIRD_PARTY_DATA_KEY: data,
                        PREFERRED_SERVER_KEY: "Produksi" if use_production else "Belajar",
                    }
                    renew_multiple_user_data(renew_data)
                    shutil.copy(r'C:\PenilaianTanah\ui\nik_login\Arcgis.Desktop.Config.daml', os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local', 'ESRI', 'Arcgis.Desktop.Config.daml'))
                    aprx = arcpy.mp.ArcGISProject("CURRENT")
                    aprx.save()
                    if automatic_reload:
                        subprocess.Popen(r"C:\PenilaianTanah\ui\restart_arcgis.bat")
                        # Tutup ArcGIS Pro
                        os.system("taskkill /f /im ArcGISPro.exe")
                    else:
                        arcpy.AddMessage("Login berhasil. Silakan restart ArcGIS Pro untuk menerapkan perubahan.")
                else:
                    arcpy.AddError(f"Login gagal: {data.get('message', 'Tidak ada pesan error yang diberikan')}")

            
            return 
            
        except requests.exceptions.ConnectTimeout:
            arcpy.AddError("Server sedang sibuk, coba beberapa saat lagi")
            raise arcpy.ExecuteError
        except requests.exceptions.Timeout:
            arcpy.AddError("Server sedang sibuk, coba beberapa saat lagi")
            raise arcpy.ExecuteError
        except requests.exceptions.RequestException as e:
            arcpy.AddError(f"Error dalam pemanggilan API: {str(e)}")
            raise arcpy.ExecuteError
        except json.JSONDecodeError as e:
            arcpy.AddError(f"Error dalam parsing response API: {str(e)}")
            raise arcpy.ExecuteError

class Logout_Pengguna:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Logout Pemeta Nilai Tanah"
        self.description = ""

    def getParameterInfo(self):
        """Define the tool parameters."""

        user_data = get_user_data(THIRD_PARTY_DATA_KEY)
        sso_data = get_user_data(SSO_DATA_KEY)


        penjelasan = arcpy.Parameter(
            displayName="Penjelasan",
            name="penjelasan",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )
        if user_data:
            berkas_list = get_all_berkas_id()
            berkas_messages = "\n".join([f"{berkas[0]} - {berkas[1]}" for berkas in berkas_list])
            server = get_user_data(PREFERRED_SERVER_KEY)
            kontrak = '20202020'
            tahun = get_user_data(YEAR_KEY)
            nama_pengguna = user_data['berkas'][0]['nama_petugas']

            penjelasan.value = (
                f"Anda saat ini masuk sebagai Pemeta Nilai Tanah\n\n"
                f"Nama Pemeta: {nama_pengguna}\n"
                f"Nomor Kontrak: {kontrak}\n"
                f"Tahun Kontrak: {tahun}\n"
                f"Server Sipenta: {server}\n\n"
                "Anda memiliki akses ke berkas-berkas berikut:\n"
                f"{berkas_messages}\n\n"
                "Gunakan tools ini untuk logout"
                "\n----------------------------------------------\n"
                "Dikembangkan oleh:\n"
                "Direktorat Penilaian Tanah dan Ekonomi Pertanahan,\n"
                "Kementerian ATR/BPN.\n"
            )
        elif sso_data:
            berkas_list = get_all_berkas_id(THIRD_PARTY_DATA_KEY=SSO_DATA_KEY)
            berkas_messages = "\n".join([f"{berkas[0]} - {berkas[1]}" for berkas in berkas_list])
            server = get_user_data(PREFERRED_SERVER_KEY)
            nama_pengguna = sso_data['user']['nama']
            penjelasan.value = (
                f"Anda saat ini masuk sebagai ASN ATR/BPN\n\n"
                f"Nama ASN: {nama_pengguna}\n"
                f"Server Sipenta: {server}\n\n"
                "Anda memiliki akses ke berkas-berkas berikut:\n"
                f"{berkas_messages}\n\n"
                "Gunakan tools ini untuk logout"
                "\n----------------------------------------------\n"
                "Dikembangkan oleh:\n"
                "Direktorat Penilaian Tanah dan Ekonomi Pertanahan,\n"
                "Kementerian ATR/BPN.\n"
            )
        else:       
            penjelasan.value = (
                "Anda belum login.\n"
                "Tools ini hanya untuk logout"
                "\n----------------------------------------------\n"
                "Dikembangkan oleh:\n"
                "Direktorat Penilaian Tanah dan Ekonomi Pertanahan,\n"
                "Kementerian ATR/BPN.\n"
            )

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
        user_data = get_user_data(THIRD_PARTY_DATA_KEY)
        sso_data = get_user_data(SSO_DATA_KEY)
        if user_data is None and sso_data is None:
            arcpy.AddMessage("Anda belum login, tidak perlu logout")
            return

        if get_user_data(THIRD_PARTY_DATA_KEY):
            clear_user_data()
        elif get_user_data(SSO_DATA_KEY):
            clear_user_data(SSO_DATA_KEY)
        shutil.copy(r'C:\PenilaianTanah\ui\Arcgis.Desktop.Config.daml', os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local', 'ESRI', 'Arcgis.Desktop.Config.daml'))
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        aprx.save()
        subprocess.Popen(r"C:\PenilaianTanah\ui\restart_arcgis.bat")
        
        os.system("taskkill /f /im ArcGISPro.exe")
        
        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""


        return
    
class Login_SSO(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Login Single Sign-On (SSO) ATR/BPN"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        user_data = get_user_data(THIRD_PARTY_DATA_KEY)
        sso_data = get_user_data(SSO_DATA_KEY)

        penjelasan = arcpy.Parameter(
            displayName="Penjelasan",
            name="penjelasan",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )
        not_login_explanation = (
            "Login menggunakan Single Sign-On (SSO) memungkinkan\n"
            "Anda untuk masuk ke aplikasi menggunakan kredensial\n" 
            "yang sama dengan yang Anda gunakan untuk layanan lain\n"
            "di lingkungan Kementerian ATR/BPN.")
        already_user_login_explanation = (
            "Anda sudah login menggunakan Pemeta\n"
            "Untuk menggunakan SSO, Anda harus logout terlebih dahulu"
        )
        already_login_sso_explanation = (
            "Anda sudah login menggunakan SSO\n")
        server = arcpy.Parameter(
            displayName="Server Sipenta",
            name="server",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
        )

        server.filter.type = "ValueList"
        server.filter.list = ["Belajar", "Produksi"]

        if user_data:
            penjelasan.value = already_user_login_explanation
            return [penjelasan]
        if sso_data:
            penjelasan.value = already_login_sso_explanation
            return [penjelasan]
        else:
            penjelasan.value = not_login_explanation
            return [penjelasan, server]

    def execute(self, parameters, messages):
        """The source code of the tool."""
        user_data = get_user_data(THIRD_PARTY_DATA_KEY)
        if user_data:
            arcpy.AddMessage("Anda sudah login, logout terlebih dahulu untuk login dengan SSO")
            return
        if get_user_data(SSO_DATA_KEY):
            arcpy.AddMessage("Anda sudah login dengan SSO")
            return
        server = parameters[1].valueAsText

        mapping_server = {
            'Belajar': 'belajar',
            'Produksi': 'prod'
        }

        mapping_server = {
            'Belajar': 'belajar',
            'Produksi': 'prod'
        }

        exe_path = os.path.join(os.path.dirname(__file__), "login.exe")

        try:
            result = subprocess.run(
                [exe_path, mapping_server.get(server, server)],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )

            if not result.stdout:
                arcpy.AddError("Login failed: no response")
                return

            data = json.loads(result.stdout.strip())

            if not data.get("success", False):
                arcpy.AddError("Login failed")
                arcpy.AddError(data.get("message", "Unknown error"))
                return

            with open(os.path.join(os.path.dirname(__file__), "login_response.json"), "w") as f:
                json.dump(data, f, indent=4)
            
            renew_user_data(SSO_DATA_KEY, data)
            arcpy.AddMessage("Login OK")
            shutil.copy(r'C:\PenilaianTanah\ui\penjatek\Arcgis.Desktop.Config.daml', os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local', 'ESRI', 'Arcgis.Desktop.Config.daml'))
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            aprx.save()
            subprocess.Popen(r"C:\PenilaianTanah\ui\restart_arcgis.bat")
            
            os.system("taskkill /f /im ArcGISPro.exe")

        except Exception as e:
            arcpy.AddError(str(e))