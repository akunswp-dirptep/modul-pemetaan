import arcpy
from datetime import datetime
import requests, os, sys, time
import json, subprocess, shutil, subprocess

script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from zntutils.system_utils import renew_user_data, get_all_config, get_user_data, clear_user_data, get_all_berkas_id, renew_multiple_user_data
from zntutils.constant import THIRD_PARTY_DATA_KEY, TIPE_USER_PIHAK_KETIGA, TIPE_USER_SSO, AUTH_KEY, PREFERRED_SERVER_KEY, YEAR_KEY, SSO_DATA_KEY, CREDENTIAL_KEY

def prepare_restart_arcgis_bat(project_path=None):
    restart_bat_path = r"C:\PenilaianTanah\ui\restart_arcgis.bat"
    arcgis_exe_path = r"C:\Program Files\ArcGIS\Pro\bin\ArcGISPro.exe"
    sanitized_project_path = (project_path or "").replace('"', "")

    bat_content = (
        "@echo off\n"
        "echo Membuka ulang ArcGIS...\n"
        "timeout /t 2\n"
        f"set \"ARCGIS_EXE={arcgis_exe_path}\"\n"
        f"set \"ARCGIS_PROJECT={sanitized_project_path}\"\n"
        "\n"
        "if exist \"%ARCGIS_PROJECT%\" (\n"
        "    start \"\" \"%ARCGIS_EXE%\" \"%ARCGIS_PROJECT%\"\n"
        ") else (\n"
        "    start \"\" \"%ARCGIS_EXE%\"\n"
        ")\n"
    )

    with open(restart_bat_path, "w") as bat_file:
        bat_file.write(bat_content)

    return restart_bat_path

class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [Login_Pemeta_Nilai_Tanah, Login_SSO]


class Login_Pemeta_Nilai_Tanah:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Kredensial Pemeta Nilai Tanah"
        self.description = ""

    def getParameterInfo(self):
        """Define the tool parameters."""
        user_data = get_user_data(CREDENTIAL_KEY)

        pilihan_jenis_login = arcpy.Parameter(
            displayName="Login Sebagai",
            name="pilihan_jenis_login",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )

        pilihan_jenis_login.filter.type = "ValueList"
        pilihan_jenis_login.filter.list = ["Pemeta Pihak Ketiga", "Pemeta ASN ATR/BPN (SSO)"]
        pilihan_jenis_login.enabled = False

        penjelasan = arcpy.Parameter(
            displayName="Penjelasan",
            name="penjelasan",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )

        input_nik = arcpy.Parameter(
            displayName="NIK Pemeta Nilai Tanah (16 digit)",
            name="username",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
            )
        
        input_nik.enabled = False

        input_password = arcpy.Parameter(
            displayName="Password",
            name="password",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")
        
        input_password.enabled = False
        
        server = arcpy.Parameter(
            displayName="Server Sipenta",
            name="link",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        server.filter.type = "ValueList"
        server.filter.list = ["Belajar", "Produksi"]
        server.value = "Belajar"
        server.enabled = False
        
        automatic_reload = arcpy.Parameter(
            displayName="Reload Otomatis ArcGIS Pro",
            name="automatic_reload",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )

        automatic_reload.value = False
        automatic_reload.enabled = False

        pilihan_jenis_kegiatan = arcpy.Parameter(
            displayName="Pilih Jenis Kegiatan",
            name="pilihan_jenis_kegiatan",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )
        pilihan_jenis_kegiatan.filter.type = "ValueList"
        pilihan_jenis_kegiatan.filter.list = ["Pembuatan ZNT", "Pembaruan ZNT", "Pembuatan NBT", "Pembaruan NBT"]
        pilihan_jenis_kegiatan.value = "Pembuatan ZNT"
        pilihan_jenis_kegiatan.enabled = False

        daftar_berkas = arcpy.Parameter(   
            displayName="Daftar Berkas",
            name="daftar_berkas",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )
        daftar_berkas.filter.type = "ValueList"
        daftar_berkas.enabled = False

        
        if user_data is not None:           
            akun_tipe = "Login berhasil sebagai Pemeta Pihak Ketiga.\n" if user_data['tipe_kredensial'] == TIPE_USER_PIHAK_KETIGA else "Login berhasil sebagai Pemeta ASN ATR/BPN.\n"
            already_user_login_explanation = (
                    akun_tipe +
                    "Informasi akun:\n\n"
                    f"Nama: {user_data['nama_pengguna']}\n"
                    f"Instansi: {user_data['instansi']}\n\n"
                    "Kalau baru saja login, silakan restart ArcGIS Pro\n"
                    "agar fitur terbaru bisa digunakan. Untuk logout, \n"
                    "jalankan kembali tool ini.\n\n"
                    "Direktorat Penilaian Tanah & Ekonomi Pertanahan\n"
                    "Kementerian ATR/BPN\n"
                    f"Tahun: {datetime.now().year}"
                )
            penjelasan.value = already_user_login_explanation

        else:
            penjelasan.value = (
                "Silahkan Login untuk dapat mengakses Fitur\n"
                "lengkap Plugin Penilaian Tanah. Pilih jenis\n"
                "Pemeta Nilai Tanah pada kolom dibawah.\n\n"

                "Direktorat Penilaian Tanah & Ekonomi Pertanahan\n"
                "Kementerian ATR/BPN\n"
                "Tahun: {}".format(datetime.now().year) 
            )
        return [penjelasan, pilihan_jenis_login, input_nik, input_password, server, pilihan_jenis_kegiatan, daftar_berkas, automatic_reload]

    def isLicensed(self):
        """Set whether the tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        user_data = get_user_data(CREDENTIAL_KEY)

        penjelasan = parameters[0]
        pilihan_login = parameters[1]   
        input_nik = parameters[2]
        input_password = parameters[3]
        server = parameters[4]
        pilihan_jenis_kegiatan = parameters[5]
        daftar_berkas = parameters[6]
        automatic_reload = parameters[7]

        if user_data is not None:
            pilihan_login.enabled = False
            input_nik.enabled = False
            input_password.enabled = False
            server.enabled = False
            pilihan_jenis_kegiatan.enabled = True
            daftar_berkas.enabled = True
            automatic_reload.enabled = True
            akun_tipe = "Login berhasil sebagai Pemeta Pihak Ketiga.\n" if user_data['tipe_kredensial'] == TIPE_USER_PIHAK_KETIGA else "Login berhasil sebagai Pemeta ASN ATR/BPN.\n"
            already_user_login_explanation = (
                    akun_tipe +
                    "Informasi akun:\n\n"
                    f"Nama: {user_data['nama_pengguna']}\n"
                    f"Instansi: {user_data['instansi']}\n\n"
                    "Kalau baru saja login, silakan restart ArcGIS Pro\n"
                    "agar fitur terbaru bisa digunakan. Untuk logout, \n"
                    "jalankan kembali tool ini.\n\n"
                    "Direktorat Penilaian Tanah & Ekonomi Pertanahan\n"
                    "Kementerian ATR/BPN\n"
                    f"Tahun: {datetime.now().year}"
                )
            penjelasan.value = already_user_login_explanation
            input_pilihan_jenis_kegiatan = pilihan_jenis_kegiatan.valueAsText
            if input_pilihan_jenis_kegiatan:
                daftar_berkas.value = ""
                berkas_list = get_all_berkas_id(process_type=input_pilihan_jenis_kegiatan)
                simplifyed_berkas_list = [f"{berkas[0]} - {'Pemeta' if berkas[1] else 'Bukan Pemeta'}" for berkas in berkas_list] if berkas_list else []
                daftar_berkas.filter.list = simplifyed_berkas_list
                daftar_berkas.value = simplifyed_berkas_list[0] if len(simplifyed_berkas_list) > 0 else "Tidak ada berkas"
            else:
                daftar_berkas.filter.list = []
            return


        else:
            pilihan_jenis_kegiatan.enabled = False
            daftar_berkas.enabled = False
            pilihan_login.enabled = True
            automatic_reload.enabled = True
            server.enabled = True

            if pilihan_login.value == "Pemeta Pihak Ketiga":
                input_nik.enabled = True
                input_password.enabled = True
                
                
                penjelasan.value = (
                    "Anda akan login sebagai Pemeta Pihak Ketiga.\n"
                    "Silakan masukkan NIK dan Password yang terdaftar\n"
                    "di SIPENTA. Jika sudah login, Anda perlu menutup \n"
                    "ArcGIS Pro kemudian membuka kembali Aplikasi \n"
                    "agar dapat menggunakan fitur lengkap dari Plugin \n"
                    "Penilaian Tanah atau Anda juga bisa mencentang \n"
                    "opsi [Reload Otomatis ArcGIS Pro] jika Anda\n"
                    "ingin ArcGIS Pro otomatis restart setelah login\n"
                    "berhasil. Namun pastikan untuk menyimpan pekerjaan \n"
                    "Anda sebelum login jika memilih opsi ini.\n\n"
                    "Direktorat Penilaian Tanah & Ekonomi Pertanahan\n"
                    "Kementerian ATR/BPN\n"
                    "Tahun: {}".format(datetime.now().year))

            elif pilihan_login.value == "Pemeta ASN ATR/BPN (SSO)":
                input_nik.enabled = False
                input_password.enabled = False
                penjelasan.value = (
                    "Anda akan login sebagai Pemeta ASN ATR/BPN (SSO).\n"
                    "Silakan gunakan akun SSO Anda untuk login.\n"
                    "Jika sudah login, Anda perlu menutup \n"
                    "ArcGIS Pro kemudian membuka kembali Aplikasi \n"
                    "agar dapat menggunakan fitur lengkap dari Plugin \n"
                    "Penilaian Tanah atau Anda juga bisa mencentang \n"
                    "opsi [Reload Otomatis ArcGIS Pro] jika Anda\n"
                    "ingin ArcGIS Pro otomatis restart setelah login \n"
                    "berhasil. Namun pastikan untuk menyimpan pekerjaan \n"
                    "Anda sebelum login jika memilih opsi ini.\n\n"
                    "Direktorat Penilaian Tanah & Ekonomi Pertanahan\n"
                    "Kementerian ATR/BPN\n"
                    "Tahun: {}".format(datetime.now().year))

            # ===== Validasi NIK hanya kalau aktif =====
            if input_nik.enabled and input_nik.value:
                nik_str = str(input_nik.value).replace(" ", "")
                input_nik.value = nik_str

                if not nik_str.isdigit():
                    input_nik.setErrorMessage("NIK harus berisi angka saja")
                elif len(nik_str) != 16:
                    input_nik.setErrorMessage(f"NIK harus tepat 16 digit (saat ini: {len(nik_str)} digit)")
                else:
                    input_nik.clearMessage()

        return
    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter. This method is called after internal validation."""
        user_data = get_user_data(CREDENTIAL_KEY)
        if user_data is None:
            pilihan_login = parameters[1]
            input_nik = parameters[2]
            input_password = parameters[3]
            server = parameters[4]
            automatic_reload = parameters[7]

            if automatic_reload.value == True:
                automatic_reload.clearMessage()
                automatic_reload.setWarningMessage(
                    "Setelah login berhasil, ArcGIS Pro akan otomatis restart. Simpan pekerjaan Anda terlebih dahulu untuk mencegah kehilangan data."
                )

        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        user_data = get_user_data(CREDENTIAL_KEY)
        server = parameters[4].value
        automatic_reload = parameters[7].value
        if user_data is None:
            pilihan_login = parameters[1].valueAsText
            
            if pilihan_login == "Pemeta ASN ATR/BPN (SSO)":
                self.login_sso(server, automatic_reload)
                
            else:
                nik = parameters[2].value
                password = parameters[3].value
                use_production = True if server == "Produksi" or server == None else False

                self.login_pihak_ketiga(nik, password, use_production, automatic_reload)
                 
        if user_data:
            self.logout_pemeta_nilai_tanah(automatic_reload=automatic_reload)



        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""


        return
    
    def login_pihak_ketiga(self, nik, password, use_production=True, automatic_reload=False):
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
                arcpy.AddMessage(f"Response API: {json.dumps(data, indent=4)}")  # Log response API dengan format yang lebih rapi
                if data.get("success"):
                    renew_data = {
                        CREDENTIAL_KEY: {
                            'nama_pengguna': data['user']['nama'],
                            'instansi': data['user']['perusahaan_nama'],
                            AUTH_KEY: data['token'],
                            'berkas': data['berkas'],
                            'role': data['user']['roles'],
                            'instansi_id': data['user']['perusahaan_id'],
                            'tipe_kredensial': TIPE_USER_PIHAK_KETIGA},
                        PREFERRED_SERVER_KEY: "Produksi" if use_production else "Belajar",
                    }
                    renew_multiple_user_data(renew_data)
                    shutil.copy(r'C:\PenilaianTanah\ui\nik_login\Arcgis.Desktop.Config.daml', os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local', 'ESRI', 'Arcgis.Desktop.Config.daml'))
                    aprx = arcpy.mp.ArcGISProject("CURRENT")
                    aprx.save()
                    if automatic_reload:
                        restart_bat_path = prepare_restart_arcgis_bat(aprx.filePath)
                        subprocess.Popen(restart_bat_path)
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

    def logout_pemeta_nilai_tanah(self, automatic_reload=False):
        clear_user_data()      
        shutil.copy(r'C:\PenilaianTanah\ui\Arcgis.Desktop.Config.daml', os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local', 'ESRI', 'Arcgis.Desktop.Config.daml'))
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        aprx.save()
        if automatic_reload == True:
            restart_bat_path = prepare_restart_arcgis_bat(aprx.filePath)
            subprocess.Popen(restart_bat_path)
            
            os.system("taskkill /f /im ArcGISPro.exe")
        else:
            arcpy.AddMessage("Logout berhasil. Silakan restart ArcGIS Pro untuk menerapkan perubahan.")

    def login_sso(self, server, automatic_reload=False):
        mapping_server = {
            'Belajar': 'belajar-2',
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

            renew_data = {
                        CREDENTIAL_KEY: {
                                'nama_pengguna': data['user']['nama'],
                                'instansi': data['user']['nama_kantor'],
                                AUTH_KEY: data['token'],
                                'berkas': data['berkas'],
                                'role': data['user']['roles'],
                                'instansi_id': data['user']['kantor_id'],
                                'tipe_kantor_id': data['user']['tipe_kantor_id'],
                                'tipe_kredensial': TIPE_USER_SSO },
                        PREFERRED_SERVER_KEY: server,
                    }
            renew_multiple_user_data(renew_data)
            
            arcpy.AddMessage("Login OK")
            shutil.copy(r'C:\PenilaianTanah\ui\penjatek\Arcgis.Desktop.Config.daml', os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local', 'ESRI', 'Arcgis.Desktop.Config.daml'))
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            aprx.save()

            if automatic_reload:
                restart_bat_path = prepare_restart_arcgis_bat(aprx.filePath)
                subprocess.Popen(restart_bat_path)
                os.system("taskkill /f /im ArcGISPro.exe")
            else:
                arcpy.AddMessage("Login berhasil. Silakan restart ArcGIS Pro untuk menerapkan perubahan.")

        except Exception as e:
            arcpy.AddError(str(e))
   
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
            "di lingkungan Kementerian ATR/BPN.\n\n"
            "Direktorat Penilaian Tanah & Ekonomi Pertanahan\n"
            "Kementerian ATR/BPN\n"
            "Tahun: {}".format(datetime.now().year))
        


        server = arcpy.Parameter(
            displayName="Server Sipenta",
            name="server",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
        )

        server.filter.type = "ValueList"
        server.filter.list = ["Belajar", "Produksi"]

        automatic_reload = arcpy.Parameter(
            displayName="Reload Otomatis ArcGIS Pro setelah login berhasil",   
            name="automatic_reload",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"  
        )

        if user_data:
            already_user_login_explanation = (
            
                "Anda sudah login sebagai Pemeta Pihak Ketiga\n"
                "Dengan Kredensial sebagai berikut:\n\n"
                f"Nama Pemeta: {user_data['user']['nama']}\n"
                f"Badan Usaha : {user_data['user']['perusahaan_nama']}\n\n"

                "Untuk menggunakan SSO, Anda harus logout\n"
                "terlebih dahulu\n\n"
                "Direktorat Penilaian Tanah & Ekonomi Pertanahan\n"
                "Kementerian ATR/BPN\n"
                "Tahun: {}".format(datetime.now().year)
            )
            penjelasan.value = already_user_login_explanation
            return [penjelasan]
        if sso_data:

            already_login_sso_explanation = (
                "Anda sudah login sebagai Pemeta \n"
                "ASN Kementerian ATR/BPN\n"
                "Dengan Kredensial sebagai berikut:\n\n"
                f"Nama Pemeta: {sso_data['user']['nama']}\n"
                f"Badan Usaha : {sso_data['user']['nama_kantor']}\n\n"

                "Untuk menggunakan SSO, Anda harus logout\n"
                "terlebih dahulu\n\n"
                "Direktorat Penilaian Tanah & Ekonomi Pertanahan\n"
                "Kementerian ATR/BPN\n"
                "Tahun: {}".format(datetime.now().year)
            )
            penjelasan.value = already_login_sso_explanation
            return [penjelasan]
        else:
            penjelasan.value = not_login_explanation
            return [penjelasan, server, automatic_reload]

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
        automatic_reload = parameters[2].valueAsText

        mapping_server = {
            'Belajar': 'belajar-2',
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

            renew_data = {
                        'nama_pengguna': data['user']['nama'],
                        'instansi': data['user']['nama_kantor'],
                        'token': data['token'],
                        'berkas': data['berkas'],
                        'role': data['user']['roles'],
                        'instansi_id': data['user']['kantor_id'],
                        'tipe_kantor_id': data['user']['tipe_kantor_id'],
                        'tipe_kredensial': 'SSO',
                        PREFERRED_SERVER_KEY: server,
                    }
            renew_multiple_user_data(renew_data)
            
            arcpy.AddMessage("Login OK")
            shutil.copy(r'C:\PenilaianTanah\ui\penjatek\Arcgis.Desktop.Config.daml', os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local', 'ESRI', 'Arcgis.Desktop.Config.daml'))
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            aprx.save()

            if automatic_reload:
                restart_bat_path = prepare_restart_arcgis_bat(aprx.filePath)
                subprocess.Popen(restart_bat_path)
                os.system("taskkill /f /im ArcGISPro.exe")
            else:
                arcpy.AddMessage("Login berhasil. Silakan restart ArcGIS Pro untuk menerapkan perubahan.")

        except Exception as e:
            arcpy.AddError(str(e))
