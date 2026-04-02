# -*- coding: utf-8 -*-

import arcpy
from datetime import datetime
import requests, os, sys
import json

script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from zntutils.system_utils import renew_user_data, get_all_config, get_user_data, clear_user_data, get_all_berkas_id, renew_multiple_user_data
from zntutils.constant import USER_DATA_KEY, NIK_KEY, NOMOR_KONTRAK_KEY, PREFERRED_SERVER_KEY   

class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [Login_Pengguna, Logout_Pengguna]


class Login_Pengguna:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Login Pemeta Nilai Tanah"
        self.description = ""

    def getParameterInfo(self):
        """Define the tool parameters."""

        input_nik = arcpy.Parameter(
            displayName="NIK Pemeta Nilai Tanah (16 digit)",
            name="username",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
            )

        input_nomor_kontrak = arcpy.Parameter(
            displayName="Nomor Kontrak",
            name="project_id",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        tahun  = arcpy.Parameter(
            displayName="Tahun",
            name="tahun",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        
        tahun.value = datetime.now().year
        
        server = arcpy.Parameter(
            displayName="Server Sipenta",
            name="link",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        server.filter.type = "ValueList"
        server.filter.list = ["Belajar", "Produksi"]
        server.value = "Belajar"

        return [input_nik, input_nomor_kontrak, tahun, server]

    def isLicensed(self):
        """Set whether the tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        input_nik = parameters[0]

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
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        nik = parameters[0].value
        nomor_kontrak = parameters[1].value
        tahun = parameters[2].value
        server = parameters[3].value
        use_production = True if server == "Produksi" or server == None else False

        self.call_sipenta_api(nik, nomor_kontrak, tahun, use_production)


        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""


        return
    
    def call_sipenta_api(self, nik, nomor_kontrak, tahun, use_production=True):
        """
        Fungsi untuk memanggil API SIPENTA dan mendapatkan data survey.
        
        Parameters:
        nik (str): NIK pengguna untuk autentikasi API
        nomor_kontrak (str): Nomor kontrak proyek
        tahun (int): Tahun proyek
        use_production (bool): True untuk production URL, False untuk testing URL
        
        Returns:
        dict: Data response dari API dalam format dictionary
        """
        
        # URL untuk testing dan produksi
        test_url = f"https://belajar.atrbpn.go.id/sipenta/tatausaha/apis/login-pemeta"
        prod_url = f"https://sipenta.atrbpn.go.id/tatausaha/apis/login-pemeta"
    
        # url = prod_url if use_production else test_url
        url = prod_url if use_production else test_url

        try:
            # Mengambil data dari API

            payload = {
                "nik": nik,
                "nomor_sk_kontrak": nomor_kontrak,
                "tahun": tahun
            }

            response = requests.post(url, data=payload, timeout=60)  
            arcpy.AddMessage(f"Status Code: {response.status_code}")


            if response.status_code == 200:
                data = response.json()
                if data.get("success"):

                    renew_data = {
                        USER_DATA_KEY: data,
                        NIK_KEY: nik,
                        NOMOR_KONTRAK_KEY: nomor_kontrak,
                        PREFERRED_SERVER_KEY: "Produksi" if use_production else "Belajar"
                    }
                    renew_multiple_user_data(renew_data)

                else:
                    arcpy.AddError(f"Login gagal: {data.get('message', 'Tidak ada pesan error yang diberikan')}")
            
            
            return 
            
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

        user_data = get_user_data(USER_DATA_KEY)


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
            nik = get_user_data(NIK_KEY)
            kontrak = get_user_data(NOMOR_KONTRAK_KEY)

            penjelasan.value = (
                f"Anda saat ini masuk sebagai Pemeta Nilai Tanah\n\n"
                f"NIK: {nik}\n"
                f"Nomor Kontrak: {kontrak}\n"
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

        if get_user_data(USER_DATA_KEY):
            clear_user_data()
        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""


        return
    
