import arcpy
from datetime import datetime
import requests, os, sys, time
import json, subprocess, shutil, subprocess

script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from zntutils.system_utils import renew_user_data, get_all_config, get_user_data, clear_user_data, get_all_berkas_id, renew_multiple_user_data
from zntutils.constant import PREFERRED_BERKAS_ID, TIPE_USER_PIHAK_KETIGA, TIPE_USER_SSO, AUTH_KEY, PREFERRED_SERVER_KEY, YEAR_KEY, SSO_DATA_KEY, CREDENTIAL_KEY

class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [Login_Pemeta_Nilai_Tanah]


class Login_Pemeta_Nilai_Tanah:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Akun Pemeta Nilai Tanah"
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
            parameterType="Required",
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
            parameterType="Required",
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
        return [penjelasan, pilihan_jenis_login, input_nik, 
                input_password, server, pilihan_jenis_kegiatan, daftar_berkas, automatic_reload]

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
            automatic_reload.enabled = False
            akun_tipe = "Login berhasil sebagai Pemeta Pihak Ketiga.\n" if user_data['tipe_kredensial'] == TIPE_USER_PIHAK_KETIGA else "Login berhasil sebagai Pemeta ASN ATR/BPN.\n"
            already_user_login_explanation = (
                    akun_tipe +
                    "Informasi akun:\n\n"
                    f"Nama: {user_data['nama_pengguna']}\n"
                    f"Instansi: {user_data['instansi']}\n\n"

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
            automatic_reload.enabled = False
            server.enabled = True
            penjelasan.value = (
                "Silahkan Login untuk dapat mengakses Fitur\n"
                "lengkap Plugin Penilaian Tanah. Pilih jenis\n"
                "Pemeta Nilai Tanah pada kolom dibawah.\n\n"

                "Direktorat Penilaian Tanah & Ekonomi Pertanahan\n"
                "Kementerian ATR/BPN\n"
                "Tahun: {}".format(datetime.now().year) 
            )

            if pilihan_login.value == "Pemeta Pihak Ketiga":
                input_nik.enabled = True
                input_password.enabled = True
                
                
                penjelasan.value = (
                    "Anda akan login sebagai Pemeta Pihak Ketiga.\n"
                    "Silakan masukkan NIK dan Password yang terdaftar\n"
                    "di Sipenta.\n\n"
                    "Direktorat Penilaian Tanah & Ekonomi Pertanahan\n"
                    "Kementerian ATR/BPN\n"
                    "Tahun: {}".format(datetime.now().year))
                


            elif pilihan_login.value == "Pemeta ASN ATR/BPN (SSO)":
                input_nik.enabled = False
                input_password.enabled = False
                penjelasan.value = (
                    "Anda akan login sebagai Pemeta ASN ATR/BPN (SSO).\n"
                    "Silakan gunakan akun SSO Anda untuk login.\n\n"
                    "Direktorat Penilaian Tanah & Ekonomi Pertanahan\n"
                    "Kementerian ATR/BPN\n"
                    "Tahun: {}".format(datetime.now().year))



        return
    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter. This method is called after internal validation."""

        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        user_data = get_user_data(CREDENTIAL_KEY)
        server = parameters[4].value

        if user_data is None:
            pilihan_login = parameters[1].valueAsText
            
            if pilihan_login == "Pemeta ASN ATR/BPN (SSO)":
                self.login_sso(server)
                
            else:
                nik = parameters[2].value
                password = parameters[3].value
                nik_str = str(nik).replace(" ", "")

                if not nik_str.isdigit():
                        arcpy.AddError("NIK hanya boleh berisi angka")
                        return
                elif len(nik_str) != 16:
                        arcpy.AddError(
                            f"NIK harus tepat 16 digit (saat ini: {len(nik_str)} digit)"
                        )
                        return
                if not nik:
                    arcpy.AddError("NIK wajib diisi")
                    return

                if not password:
                    arcpy.AddError("Password wajib diisi")
                    return
                use_production = True if server == "Produksi" or server == None else False

                self.login_pihak_ketiga(nik, password, use_production)
                 
        if user_data:
            self.logout_pemeta_nilai_tanah()



        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""


        return
    
    def login_pihak_ketiga(self, nik, password, use_production=True):
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
                        PREFERRED_BERKAS_ID: None
                    }
                    renew_multiple_user_data(renew_data)
                    
                else:
                    arcpy.AddError(f"Login gagal: {data.get('message', 'Tidak ada pesan error yang diberikan')}")
                    return
            else:
                result = response.json()
                arcpy.AddError(f"Login gagal {result.get('message','')} (HTTP {response.status_code})")
                return

            
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

    def logout_pemeta_nilai_tanah(self):
        clear_user_data()      

    def login_sso(self, server):
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
                        PREFERRED_BERKAS_ID: None
                    }
            renew_multiple_user_data(renew_data)
            
            arcpy.AddMessage("Login OK")

        except Exception as e:
            arcpy.AddError(str(e))
   
