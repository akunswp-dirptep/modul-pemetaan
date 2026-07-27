import arcpy
import os, sys
import json, shutil, requests
import zipfile
import tempfile
from datetime import datetime

# Tambahkan parent directory ke sys.path
script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from zntutils.document import validate_document_type, get_credentials
from zntutils.system_utils import get_user_data, renew_user_data, get_all_berkas_id, setup_user_data
from zntutils.constant import PREFERRED_BERKAS_ID, CREDENTIAL_KEY, PREFERRED_SERVER_KEY, AUTH_KEY, NAMA_PROVINSI, KAB_KOTA
from zntutils.upload_utils import upload_feature_layer_to_sipenta


class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [Upload_Titik_Sampel, Upload_Titik_Zona, Upload_Nilai_Bidang_Tanah]


class Upload_Titik_Sampel(object):
    def __init__(self):
        self.label = "Upload Titik Sampel"
        self.description = ""
        self.canRunInBackground = False


    def getParameterInfo(self):
        berkas_list = get_all_berkas_id(process_type='Pembaruan NBT')
        berkas_show = []
        can_show = 0
        if berkas_list is not None:
            for berkas in berkas_list:
                if berkas[1] is True:
                    berkas_show.append(f"{berkas[0]}")
                    can_show += 1
            if can_show == 0:
                berkas_show = ['Tidak ada berkas yang dapat dipilih']
        else:
            berkas_show = ['Tidak ada berkas yang dapat dipilih']

        fl = arcpy.Parameter(
            displayName="Titik Sampel (Feature Layer)",
            name="fl",
            datatype="GPFeatureLayer",  
            parameterType="Required",
            direction="Input") 

        berkas = arcpy.Parameter(
            displayName="Berkas",
            name="link",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
               
        berkas.filter.type = "ValueList"
        berkas.filter.list = berkas_show
        if berkas_list and can_show > 0:
            preferred_berkas=get_user_data(PREFERRED_BERKAS_ID)
            if preferred_berkas:
                if '04/' in preferred_berkas:
                    berkas.value = preferred_berkas
                else:
                    berkas.value = berkas_show[0]           
        elif berkas_list and can_show == 0:
            berkas.value = 'Tidak ada berkas yang dapat dipilih'
        else:
            berkas.value = 'Tidak ada berkas yang dapat dipilih'
        
        penjelasan = arcpy.Parameter(
            displayName="Informasi Tools",
            name="petunjuk",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        penjelasan.value = (
                "Login terlebih dahulu untuk mengakses fitur ini.\n\n"
                "Direktorat Penilaian Tanah dan Ekonomi Pertanahan,\n"
                "Kementerian ATR/BPN.\n"
                "Tahun: {}\n".format(datetime.now().year))
        params = [fl, berkas, penjelasan]
        return params
        
    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        return   
    
    def updateParameters(self, parameters):
            """Modify the values and properties of parameters before internal
            validation is performed.  This method is called whenever a parameter
            has been changed."""

            shapefile_path = parameters[0]
            berkas = parameters[1]
            penjelasan = parameters[2]

            is_login = get_user_data(CREDENTIAL_KEY)

            if is_login is None:
                shapefile_path.enabled = False
                berkas.enabled = False
                penjelasan.enabled = True
            else:
                shapefile_path.enabled = True
                berkas.enabled = True
                penjelasan.enabled = False
            
            return
   
    def execute(self, parameters, messages):
        user_data = get_user_data(CREDENTIAL_KEY)

        berkas_list = get_all_berkas_id(process_type='Pembaruan NBT')

        if berkas_list is None:
            arcpy.AddWarning("Tidak ada berkas yang tersedia untuk dipilih. Pastikan Anda tidak salah memilih menu atau memiliki berkas yang valid untuk proses Pembaruan NBT.")
            return
        
        fl_path = parameters[0].valueAsText
        berkas_value = parameters[1].valueAsText
        server = get_user_data(PREFERRED_SERVER_KEY)
        use_production = True if server == "Produksi" or server == None else False
        token = user_data.get(AUTH_KEY, None)

        validate_document_type(
            document_id=berkas_value,
            target='Pembaruan NBT')
        
        upload_feature_layer_to_sipenta(
            nomor_berkas=berkas_value,
            token=token,
            param="pembaruan_nbt_titik_sampel_nilai_tanah_shp",
            in_feature="Titik_Sampel",
            feature_layer=fl_path,
            use_production=use_production)

        setup_user_data(PREFERRED_BERKAS_ID, berkas_value)
        return

class Upload_Titik_Zona(object):
    def __init__(self):
        self.label = "Upload Titik Zona"
        self.description = ""
        self.canRunInBackground = False


    def getParameterInfo(self):
        berkas_list = get_all_berkas_id(process_type='Pembaruan NBT')
        berkas_show = []
        can_show = 0
        if berkas_list is not None:
            for berkas in berkas_list:
                if berkas[1] is True:
                    berkas_show.append(f"{berkas[0]}")
                    can_show += 1
            if can_show == 0:
                berkas_show = ['Tidak ada berkas yang dapat dipilih']
        else:
            berkas_show = ['Tidak ada berkas yang dapat dipilih']

        fl = arcpy.Parameter(
            displayName="Titik Zona (Feature Layer)",
            name="fl",
            datatype="GPFeatureLayer",  
            parameterType="Required",
            direction="Input") 

        berkas = arcpy.Parameter(
            displayName="Berkas",
            name="link",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
               
        berkas.filter.type = "ValueList"
        berkas.filter.list = berkas_show
        if berkas_list and can_show > 0:
            preferred_berkas=get_user_data(PREFERRED_BERKAS_ID)
            if preferred_berkas:
                if '04/' in preferred_berkas:
                    berkas.value = preferred_berkas
                else:
                    berkas.value = berkas_show[0]           
        elif berkas_list and can_show == 0:
            berkas.value = 'Tidak ada berkas yang dapat dipilih'
        else:
            berkas.value = 'Tidak ada berkas yang dapat dipilih'
        
        penjelasan = arcpy.Parameter(
            displayName="Informasi Tools",
            name="petunjuk",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        penjelasan.value = (
                "Login terlebih dahulu untuk mengakses fitur ini.\n\n"
                "Direktorat Penilaian Tanah dan Ekonomi Pertanahan,\n"
                "Kementerian ATR/BPN.\n"
                "Tahun: {}\n".format(datetime.now().year))
        params = [fl, berkas, penjelasan]
        return params
        
    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        return   
    
    def updateParameters(self, parameters):
            """Modify the values and properties of parameters before internal
            validation is performed.  This method is called whenever a parameter
            has been changed."""

            shapefile_path = parameters[0]
            berkas = parameters[1]
            penjelasan = parameters[2]

            is_login = get_user_data(CREDENTIAL_KEY)

            if is_login is None:
                shapefile_path.enabled = False
                berkas.enabled = False
                penjelasan.enabled = True
            else:
                shapefile_path.enabled = True
                berkas.enabled = True
                penjelasan.enabled = False
            
            return
   
    def execute(self, parameters, messages):
        user_data = get_user_data(CREDENTIAL_KEY)

        berkas_list = get_all_berkas_id(process_type='Pembaruan NBT')

        if berkas_list is None:
            arcpy.AddWarning("Tidak ada berkas yang tersedia untuk dipilih. Pastikan Anda tidak salah memilih menu atau memiliki berkas yang valid untuk proses Pembaruan NBT.")
            return
        
        fl_path = parameters[0].valueAsText
        berkas_value = parameters[1].valueAsText
        server = get_user_data(PREFERRED_SERVER_KEY)
        use_production = True if server == "Produksi" or server == None else False
        token = user_data.get(AUTH_KEY, None)

        validate_document_type(
            document_id=berkas_value,
            target='Pembaruan NBT')
        
        upload_feature_layer_to_sipenta(
            nomor_berkas=berkas_value,
            token=token,
            param="pembaruan_nbt_titik_zona_shp",
            in_feature="Titik_Sampel",
            feature_layer=fl_path,
            use_production=use_production)

        setup_user_data(PREFERRED_BERKAS_ID, berkas_value)
        return

class Upload_Nilai_Bidang_Tanah(object):
    def __init__(self):
        self.label = "Upload Nilai Bidang Tanah"
        self.description = "Mengonversi layer ke custom JSON, mengompresnya ke ZIP, lalu mengunggahnya ke API SIPENTA."
        self.canRunInBackground = False

    def getParameterInfo(self):
        berkas_list = get_all_berkas_id(process_type='Pembaruan NBT')
        berkas_show = []
        can_show = 0
        if berkas_list is not None:
            for berkas in berkas_list:
                if berkas[1] is True:
                    berkas_show.append(f"{berkas[0]}")
                    can_show += 1
            if can_show == 0:
                berkas_show = ['Tidak ada berkas yang dapat dipilih']
        else:
            berkas_show = ['Tidak ada berkas yang dapat dipilih']

        param_in_feature = arcpy.Parameter(
            name="in_feature",
            displayName="Input Layer (Persil)",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")

        # 2. Parameter Nomor Berkas
        berkas = arcpy.Parameter(
            name="nomor_berkas",
            displayName="Nomor Berkas",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        berkas.filter.type = "ValueList"
        berkas.filter.list = berkas_show
        if berkas_list and can_show > 0:
            preferred_berkas=get_user_data(PREFERRED_BERKAS_ID)
            if preferred_berkas:
                if '04/' in preferred_berkas:
                    berkas.value = preferred_berkas
                else:
                    berkas.value = berkas_show[0]           
        elif berkas_list and can_show == 0:
            berkas.value = 'Tidak ada berkas yang dapat dipilih'
        else:
            berkas.value = 'Tidak ada berkas yang dapat dipilih'

        penjelasan = arcpy.Parameter(
            displayName="Informasi Tools",
            name="petunjuk",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        penjelasan.value = (
                "Login terlebih dahulu untuk mengakses fitur ini.\n\n"
                "Direktorat Penilaian Tanah dan Ekonomi Pertanahan,\n"
                "Kementerian ATR/BPN.\n"
                "Tahun: {}\n".format(datetime.now().year))
        
        return [param_in_feature, berkas, penjelasan]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):

            shapefile_path = parameters[0]
            berkas = parameters[1]
            penjelasan = parameters[2]

            is_login = get_user_data(CREDENTIAL_KEY)

            if is_login is None:
                shapefile_path.enabled = False
                berkas.enabled = False
                penjelasan.enabled = True
            else:
                shapefile_path.enabled = True
                berkas.enabled = True
                penjelasan.enabled = False
            return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        # Mengambil nilai dari antarmuka ArcGIS Pro

        user_data = get_user_data(CREDENTIAL_KEY)

        berkas_list = get_all_berkas_id(process_type='Pembaruan NBT')

        if berkas_list is None:
            arcpy.AddWarning("Tidak ada berkas yang tersedia untuk dipilih. Pastikan Anda tidak salah memilih menu atau memiliki berkas yang valid untuk proses Pembaruan NBT.")
            return
        
        in_feature = parameters[0].valueAsText
        nomor_berkas = parameters[1].valueAsText

        api_param = 'pembaruan_nbt_nilai_bidang_tanah'
        server = get_user_data(PREFERRED_SERVER_KEY)
        use_production = True if server == "Produksi" or server == None else False
        token = user_data.get(AUTH_KEY, None)

        # Persiapan nama file dan folder sementara menggunakan scratchFolder bawaan ArcPy
        temp_dir = os.path.join(arcpy.env.scratchFolder, "sipenta_temp")
        layer_name = os.path.basename(in_feature)
        json_filename = "data.json"
        zip_filename = f"{layer_name}.zip"
        
        json_path = os.path.join(temp_dir, json_filename)
        zip_path = os.path.join(temp_dir, zip_filename)

        arcpy.AddMessage('Mempersiapkan folder sementara untuk proses data...')
        try:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            os.makedirs(temp_dir)
        except Exception as e:
            arcpy.AddError(f"Terdapat kesalahan saat membuat folder sementara: {str(e)}")
            return

        try:
            # ==========================================
            # FASE 1: KONVERSI LAYER KE CUSTOM JSON
            # ==========================================
            arcpy.AddMessage("1. Membaca layer dan membuat file JSON...")
            fields_info = arcpy.ListFields(in_feature)
            # Mengecualikan OID dan Geometry
            headers = [f.name for f in fields_info if f.type not in ["OID", "Geometry"]]
            
            rows = []
            with arcpy.da.SearchCursor(in_feature, headers) as cursor:
                for row in cursor:
                    rows.append(list(row))
                    
            custom_json = {
                "headers": headers,
                "rows": rows
            }
            
            # Simpan JSON ke folder sementara
            with open(json_path, "w") as f:
                json.dump(custom_json, f)

            # ==========================================
            # FASE 2: KOMPRESI KE ZIP
            # ==========================================
            arcpy.AddMessage("2. Mengompresi JSON ke dalam file ZIP...")
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Simpan file di dalam zip dengan nama yang sama
                zipf.write(json_path, arcname=json_filename)

            # ==========================================
            # FASE 3: UPLOAD KE API SIPENTA
            # ==========================================
            arcpy.AddMessage("3. Mengupload file ZIP ke server SIPENTA...")
            test_url = "https://belajar.atrbpn.go.id/sipenta/tatausaha-2/api/pemetaan/upload"
            prod_url = "https://sipenta.atrbpn.go.id/tatausaha/api/pemetaan/upload"
            url = prod_url if use_production else test_url

            api_headers = {
                "Authorization": f"Bearer {token}"
            }
            
            data = {
                "no_berkas": str(nomor_berkas),
                "param": str(api_param)
            }

            with open(zip_path, "rb") as zip_file:
                files = {
                    "file": (
                        zip_filename,
                        zip_file,
                        "application/zip"
                    )
                }

                response = requests.post(
                    url,
                    headers=api_headers,
                    data=data,
                    files=files
                )
                response.raise_for_status()

            arcpy.AddMessage("File berhasil diupload ke modul tatausaha SIPENTA.")

        # ==========================================
        # FASE ERROR HANDLING (Milik Anda)
        # ==========================================
        except requests.exceptions.HTTPError as e:
            response = e.response
            message = ""
            try:
                error_json = response.json()
                message = error_json.get("message", "")
            except Exception:
                pass

            if response.status_code == 403 and "expired" in message.lower():
                # Catatan: Jika ada fungsi internal untuk hapus data user, panggil di sini
                # clear_user_data() 
                arcpy.AddError("Token Anda kadaluarsa, silakan login ulang.")
            elif response.status_code == 403:
                error_message = message if message else "Periksa hak akses atau token."
                arcpy.AddError(f"Akses ditolak (403). Pesan: {error_message}")
            else:
                arcpy.AddError(f"HTTP Error {response.status_code}: {message or str(e)}")

        except requests.exceptions.RequestException as e:
            arcpy.AddError(f"Error during file upload: {str(e)}")

        except Exception as e:
            arcpy.AddError(f"Terjadi kesalahan sistem: {str(e)}")

        # ==========================================
        # FASE 4: CLEANUP FOLDER SEMENTARA
        # ==========================================
        finally:
            arcpy.AddMessage("4. Membersihkan file sementara...")
            if os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except Exception as cleanup_error:
                    arcpy.AddWarning(f"Gagal menghapus folder sementara: {str(cleanup_error)}")
            return