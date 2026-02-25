from datetime import datetime
import sys
import arcpy, os, json

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64


script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from zntutils.document import validate_document_type, get_credentials
from zntutils.upload_utils import main_upload_shapefile, main_upload
from zntutils.zona_layer import get_config_values
from zntutils.system_utils import get_user_data, renew_user_data
arcpy.env.outputZFlag = "Disabled"
arcpy.env.outputMFlag = "Disabled"

#Helper Functions
def is_internal():
    try:
        return bool(get_credentials(credential_type="OperatorGISInternal", use_for_tools_validity=True))
        # return True
    except Exception:
        return False

def current_year():
    try:
        return int(datetime.now().year)
    except Exception:
        return None


# Cryptography Functions
# def generate_key():
#     password = 'bpnri-jakarta'
#     salt = b'Sisinga@2-Jakarta'  

#     # Derive proper key dari password
#     kdf = PBKDF2HMAC(
#         algorithm=hashes.SHA256(),
#         length=32,
#         salt=salt,
#         iterations=100000,
#     )
#     key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
#     return key

# def simpan_ke_bin(data_terenkripsi, nama_file):
#     """Menyimpan data bytes ke dalam file biner."""
#     try:
#         with open(nama_file, 'wb') as file:
#             file.write(data_terenkripsi)
#         print(f"Pesan berhasil disimpan ke {nama_file}")
#     except IOError as e:
#         print(f"Terjadi kesalahan saat menulis ke file: {e}")

# def baca_dari_bin(nama_file):
#     """Membaca data bytes dari file biner."""
#     data_terenkripsi = None
#     try:
#         with open(nama_file, 'rb') as file:
#             data_terenkripsi = file.read()
#         print(f"Pesan berhasil dibaca dari {nama_file}")
#         return data_terenkripsi
#     except IOError as e:
#         print(f"Terjadi kesalahan saat membaca file: {e}")
#         return None
    
# def encrypt_message(message: str, key: bytes, path) -> bytes:
#     fernet = Fernet(key)
#     encrypted_message = fernet.encrypt(message.encode())
#     simpan_ke_bin(encrypted_message, path)
#     return encrypted_message

# def decrypt_message(key: bytes, path) -> str:
#     encrypted_message = baca_dari_bin(path)
#     fernet = Fernet(key)
#     decrypted_message = fernet.decrypt(encrypted_message).decode()
#     data = json.loads(decrypted_message)
#     return data

# def reload_all_toolboxes_in_folder(toolbox_folder):
     
#     if not os.path.exists(toolbox_folder):
#         arcpy.AddError(f"Folder toolbox tidak ditemukan: {toolbox_folder}")
#         return
        
#      # Cari semua file .pyt di folder
#     pyt_files = [f for f in os.listdir(toolbox_folder) if f.endswith('.pyt')]
        
#     if not pyt_files:
#         arcpy.AddWarning(f"Tidak ada file .pyt ditemukan di {toolbox_folder}")
#         return
        
#     # Load toolbox di proyek saat ini
#     try:
#         # Hapus dan reload menggunakan ImportToolbox (lebih reliable)
#         for pyt_file in pyt_files:
#             pyt_path = os.path.join(toolbox_folder, pyt_file)
#             try:
#                 arcpy.ImportToolbox(pyt_path)
#             except Exception as e:
#                 arcpy.AddWarning(f"Gagal memuat ulang {pyt_file}: {str(e)}")
            
#     except Exception as e:
#         arcpy.AddWarning(f"Error saat reload toolbox: {str(e)}")

# def renew_user_data(key:str, value:str):
    
#     setup_user_data(key, value)
#     all_toolboxes_folder_need_reload = [
#                 r"C:\PenilaianTanah\scripts\Pengembangan Enkripsi\Pembaruan ZNT",
#                 r"C:\PenilaianTanah\scripts\Pengembangan Enkripsi\Pembuatan ZNT",
#                 r"C:\PenilaianTanah\scripts\Pengembangan Enkripsi\Toolboxes Umum ZNT"
#             ]

#     try:
#         for folder in all_toolboxes_folder_need_reload:
#             reload_all_toolboxes_in_folder(folder)

#     except Exception as e:
#         arcpy.AddWarning(f"Gagal memuat ulang toolbox: {str(e)}")

# def setup_user_data(key:str, value:str):

#     config_path = r'C:\PenilaianTanah\config\penilaiantanah.bin'

#     try:
#         # Cek apakah file ada
#         if os.path.exists(config_path):
#             # File ada, baca isinya
#             try:
#                 data = decrypt_message(generate_key(), config_path)                    
#                 # Validasi format JSON
#                 if key not in data or not isinstance(data.get(key), str):
#                     # Format tidak sesuai, tambahkan atau perbarui data
#                     data[key] = value
                
#                 if data[key] != value:
#                     data[key] = value
                    
#             except json.JSONDecodeError:
#                 # File rusak/tidak valid, buat struktur baru
#                 arcpy.AddWarning("File config.json rusak, membuat struktur baru...")
#                 data = {key: value}
#         else:
#             # File belum ada, buat struktur baru
#             # Pastikan direktori Menu ada
#             menu_dir = os.path.dirname(config_path)
#             if not os.path.exists(menu_dir):
#                 os.makedirs(menu_dir)
            
#             data = {key: value}
        

#         # Simpan kembali ke file
#         encrypt_message(json.dumps(data), generate_key(), config_path)
        
#         return True
        
#     except Exception as e:
#         arcpy.AddError(f"Gagal menyimpan user config: {str(e)}")
#         return False

# def get_user_data(key:str):
#     config_path = r'C:\PenilaianTanah\config\penilaiantanah.bin'

#     try:
#         if os.path.exists(config_path):
#             data = decrypt_message(generate_key(), config_path) 
#             value = data.get(key, None)
#             return value
#         else:
#             return None
        
#     except Exception as e:
#         arcpy.AddError(f"Gagal membaca user config: {str(e)}")
#         return None

class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox Persiapan Data"
        self.alias = "Toolbox Persiapan Data"

        # List of tool classes associated with this toolbox
        self.tools = [Upload_Peta_Rencana_Area_Kerja,
                      Upload_Peta_Area_Kerja_Disepakati,
                      Upload_Peta_Area_Kerja_Pembuatan_ZNT_AOI,
                      Masukkan_Data_Dasar_Pembuatan_ZNT,
                      Upload_Delineasi_Zona_Awal_Nilai_Tanah_Pembuatan_ZNT
                      ]

class Upload_Peta_Rencana_Area_Kerja(object):
    def __init__(self):
        self.label = "Upload Peta Rencana Area Kerja"
        self.description = ""
        self.canRunInBackground = False


    def getParameterInfo(self):
        self.is_gis_internal = is_internal()
        self.preferred_server = get_user_data('preferred_server')
        self.nik = get_user_data('nik')
        self.berkas = get_user_data('berkas')
        self.current_year = current_year()

        param0 = arcpy.Parameter(
            displayName="Nomor Induk Kependudukan (NIK)",
            name="username",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        if self.nik:
            param0.value = self.nik

        param1 = arcpy.Parameter(
            displayName="Nomor Berkas",
            name="project_id",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        if self.berkas:
            param1.value = self.berkas

        param2 = arcpy.Parameter(
            displayName="Tahun",
            name="tahun",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")

        param3 = arcpy.Parameter(
            displayName="Shapefile Rencana Lokasi Kegiatan (.shp)",
            name="shapefile_path",
            datatype="DEFile",  
            parameterType="Required",
            direction="Input")
        
        param4 = arcpy.Parameter(
            displayName="Server Sipenta",
            name="link",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
               
        if self.current_year:
            param2.value = self.current_year

        if self.preferred_server:
            param4.value = self.preferred_server

        param4.filter.type = "ValueList"
        param4.filter.list = ["Produksi", "Belajar"]
        
        params = [param0, param1, param2, param3]
        # Periksa ulang status saat membuka parameter agar mengikuti login terbaru
        self.is_gis_internal = is_internal()
        if self.is_gis_internal:
            params.append(param4)
            return params
        else:
            return params
        
    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
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

        # Validasi format Nomor Berkas (project_id): harus seperti 01/2025/0020
        input_project = parameters[1]
        if input_project.value:
            pj_str = str(input_project.value).strip()
            input_project.value = pj_str

            # Pola: 2 digit / 4 digit (tahun) / 4 digit
            import re
            pattern = r"^\d{2}/\d{4}/\d{4}$"
            if not re.match(pattern, pj_str):
                input_project.setErrorMessage("Nomor Berkas harus berbentuk NN/YYYY/NNNN, contoh: 01/2025/0020")
            else:
                input_project.clearMessage()
        return   
    
    def execute(self, parameters, messages):
        username = str(parameters[0].valueAsText).replace(" ", "")
        project_id = str(parameters[1].valueAsText).replace(" ", "")
        tahun = parameters[2].valueAsText
        shapefile_path = parameters[3].valueAsText
        server = parameters[4].valueAsText if len(parameters) > 4 else None
        use_production = True if server == "Produksi" or server == None else False
        self.preferred_server = get_user_data('preferred_server')
        self.nik = get_user_data('nik')
        self.berkas = get_user_data('berkas')
        validate_document_type(project_id, target='Pembuatan ZNT')

        main_upload_shapefile(project_id, username, "Peta Rencana Lokasi Kegiatan", "Persiapan", "Zona_Layer", tahun, "ZNT", shapefile_path, use_production)
        
        if self.nik != username:
            renew_user_data('nik', username)
        if self.berkas != project_id:
            renew_user_data('berkas', project_id)
        if len(parameters) > 4 and server != self.preferred_server:
            renew_user_data('preferred_server', server)

        return

class Upload_Peta_Area_Kerja_Disepakati(object):
    def __init__(self):
        self.label = "Upload Peta Area Kerja Disepakati"
        self.description = ""
        self.canRunInBackground = False


    def getParameterInfo(self):
        self.is_gis_internal = is_internal()
        self.preferred_server = get_user_data('preferred_server')
        self.nik = get_user_data('nik')
        self.berkas = get_user_data('berkas')
        self.current_year = current_year()
        param0 = arcpy.Parameter(
            displayName="Nomor Induk Kependudukan (NIK)",
            name="username",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        if self.nik:
            param0.value = self.nik
        
        param1 = arcpy.Parameter(
            displayName="Nomor Berkas",
            name="project_id",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        if self.berkas:
            param1.value = self.berkas

        param2 = arcpy.Parameter(
            displayName="Tahun",
            name="tahun",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")

        param3 = arcpy.Parameter(
            displayName="Shapefile Lokasi Kegiatan (.shp)",
            name="shapefile_path",
            datatype="DEFile",  # Expect a shapefile (.shp)
            parameterType="Required",
            direction="Input")
        
        param4 = arcpy.Parameter(
            displayName="Server Sipenta",
            name="link",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        if self.current_year:
            param2.value = self.current_year

        if self.preferred_server:
            param4.value = self.preferred_server

        param4.filter.type = "ValueList"
        param4.filter.list = ["Produksi", "Belajar"]
        
        params = [param0, param1, param2, param3]
        # Periksa ulang status saat membuka parameter agar mengikuti login terbaru
        self.is_gis_internal = is_internal()

        if self.is_gis_internal:
            params.append(param4)
            return params
        else:
            return params
        
    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
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

        # Validasi format Nomor Berkas (project_id): harus seperti 01/2025/0020
        input_project = parameters[1]
        if input_project.value:
            pj_str = str(input_project.value).strip()
            input_project.value = pj_str

            # Pola: 2 digit / 4 digit (tahun) / 4 digit
            import re
            pattern = r"^\d{2}/\d{4}/\d{4}$"
            if not re.match(pattern, pj_str):
                input_project.setErrorMessage("Nomor Berkas harus berbentuk NN/YYYY/NNNN, contoh: 01/2025/0020")
            else:
                input_project.clearMessage()
        return   
   
    def execute(self, parameters, messages):
        username = str(parameters[0].valueAsText).replace(" ", "")
        project_id = str(parameters[1].valueAsText).replace(" ", "")
        tahun = parameters[2].valueAsText
        shapefile_path = parameters[3].valueAsText
        server = parameters[4].valueAsText if len(parameters) > 4 else None
        use_production = True if server == "Produksi" or server == None else False


        validate_document_type(project_id, target='Pembuatan ZNT')
        main_upload_shapefile(project_id, username, "Peta Lokasi Kegiatan", "Persiapan", "Zona_Layer", tahun, "ZNT", shapefile_path, use_production)
        
        self.preferred_server = get_user_data('preferred_server')
        self.nik = get_user_data('nik')
        self.berkas = get_user_data('berkas')
        if self.nik != username:
            renew_user_data('nik', username)
        if self.berkas != project_id:
            renew_user_data('berkas', project_id)
        if len(parameters) > 4 and server != self.preferred_server:
            renew_user_data('preferred_server', server)
            
        return

class Upload_Peta_Area_Kerja_Pembuatan_ZNT_AOI(object):
    def __init__(self):
        self.label = "Upload Peta Area Kerja (AOI)"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        self.preferred_server = get_user_data('preferred_server')
        self.nik = get_user_data('nik')
        self.berkas = get_user_data('berkas')
        self.current_year = current_year()
        param0 = arcpy.Parameter(
            displayName="Nomor Induk Kependudukan (NIK)",
            name="username",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        if self.nik:
            param0.value = self.nik
        param1 = arcpy.Parameter(
            displayName="Nomor Berkas",
            name="project_id",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        if self.berkas:
            param1.value = self.berkas
        param2 = arcpy.Parameter(
            displayName="Tahun",
            name="tahun",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        
        param3 = arcpy.Parameter(
            displayName="Shapefile Area Kerja (.shp)",
            name="shapefile_path",
            datatype="DEFile",  # Expect a shapefile (.shp)
            parameterType="Required",
            direction="Input")
        
        param4 = arcpy.Parameter(
            displayName="Server Sipenta",
            name="link",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        if self.current_year:
            param2.value = self.current_year
        
        if self.preferred_server:
            param4.value = self.preferred_server

        param4.filter.type = "ValueList"
        param4.filter.list = ["Produksi", "Belajar"]
        
        params = [param0, param1, param2, param3]
        # Periksa ulang status saat membuka parameter agar mengikuti login terbaru
        self.is_gis_internal = is_internal()
        if self.is_gis_internal:
            params.append(param4)
            return params
        else:
            return params
        
    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
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

        # Validasi format Nomor Berkas (project_id): harus seperti 01/2025/0020
        input_project = parameters[1]
        if input_project.value:
            pj_str = str(input_project.value).strip()
            input_project.value = pj_str

            # Pola: 2 digit / 4 digit (tahun) / 4 digit
            import re
            pattern = r"^\d{2}/\d{4}/\d{4}$"
            if not re.match(pattern, pj_str):
                input_project.setErrorMessage("Nomor Berkas harus berbentuk NN/YYYY/NNNN, contoh: 01/2025/0020")
            else:
                input_project.clearMessage()
        return   
   
    def execute(self, parameters, messages):
        username = str(parameters[0].valueAsText).replace(" ", "")
        project_id = str(parameters[1].valueAsText).replace(" ", "")
        tahun = parameters[2].valueAsText
        shapefile_path = parameters[3].valueAsText
        server = parameters[4].valueAsText if len(parameters) > 4 else None
        use_production = True if server == "Produksi" or server == None else False
        
        validate_document_type(project_id, target='Pembuatan ZNT')
        main_upload_shapefile(project_id, username, "Peta Area Kerja", "Pembuatan Zona Awal", "Zona_Layer", tahun, "ZNT", shapefile_path, use_production)

        self.preferred_server = get_user_data('preferred_server')
        self.nik = get_user_data('nik')
        self.berkas = get_user_data('berkas')
        if self.nik != username:
            renew_user_data('nik', username)
        if self.berkas != project_id:
            renew_user_data('berkas', project_id)
        if len(parameters) > 4 and server != self.preferred_server:
            renew_user_data('preferred_server', server)
        return        

class Masukkan_Data_Dasar_Pembuatan_ZNT(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Masukkan Data Dasar"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        input_fl = arcpy.Parameter(
            displayName="Layer Zona Awal",
            name="input_fl",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )

        output_zl = arcpy.Parameter(
            name="output_zl",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [input_fl, output_zl]


    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return
        
    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return   

    def execute(self, parameters, messages):
        """
        Fungsi ini digunakan untuk mempersiapkan data dasar yang akan digunakan dalam analisis zona nilai tanah.

        Kondisi yang harus terpenuhi:
        1. Data dasar yang diinputkan haruslah sebuah feature layer yang valid dan dapat diakses.
        2. Setelah data dasar diinputkan, sistem harus dapat membuat sebuah feature class baru dengan nama "Zona_Layer" di dalam geodatabase yang sudah ditentukan pada config.
        3. Feature Class ini hanya akan berisi field-field yang diperlukan untuk analisis zona nilai tanah, yaitu NOZN, PENGGUNAAN, SMPBKREL, SMPBAKU, NILAIZN, JMLSMPL, NILMIN, NILMAKS, WADMKK, WADMPR, THNNILAI, dan cluster.
        4. Jika sudah ada field JNSZN maka field tersebut akan dipertahankan, jika belum ada maka akan ditambahkan dengan nilai default 1 (Non-Pertanian).
        5. Field WADMKK, WADMPR, dan THNNILAI akan diisi sesuai dengan nilai yang ada pada config.
        6. Field cluster akan diisi dengan nilai default 1 untuk semua record.
        """
        input_fl = parameters[0].valueAsText

        config_dan_paths = get_config_values()
        # Mendapatkan daftar field OID dan semua field dari feature class input
        id = [f.name for f in arcpy.ListFields (input_fl, field_type="OID")]
        fields = [f.name for f in arcpy.ListFields(input_fl)]
        if 'OBJECTID' not in id and 'OBJECTID' in fields:
            arcpy.management.DeleteField(input_fl, "OBJECTID")
        arcpy.conversion.FeatureClassToFeatureClass(input_fl, config_dan_paths['dataset_path'], 'Zona_Layer_Temp')
        zl_temp_path = os.path.join(config_dan_paths['dataset_path'], 'Zona_Layer_Temp')

        in_table_fields = [f.name for f in arcpy.ListFields(zl_temp_path)]
        

        arcpy.management.AddField(zl_temp_path, "NOZN", "LONG")  # Nomor Zona
        arcpy.management.AddField(zl_temp_path, "PENGGUNAAN", "TEXT")  # Jenis Penggunaan Lahan
        arcpy.management.AddField(zl_temp_path, "SMPBKREL", "DOUBLE")  # Sample Relative Value
        arcpy.management.AddField(zl_temp_path, "SMPBAKU", "DOUBLE")  # Sample Standard Value
        arcpy.management.AddField(zl_temp_path, "NILAIZN", "LONG")  # Nilai Zona
        arcpy.management.AddField(zl_temp_path, "JMLSMPL", "DOUBLE")  # Jumlah Sample
        arcpy.management.AddField(zl_temp_path, "NILMIN", "LONG")  # Nilai Minimum
        arcpy.management.AddField(zl_temp_path, "NILMAKS", "LONG")  # Nilai Maksimum
        arcpy.management.AddField(zl_temp_path, "WADMKK", "TEXT")  # Kode Administrasi Kabupaten
        arcpy.management.AddField(zl_temp_path, "WADMPR", "TEXT")  # Kode Administrasi Provinsi
        arcpy.management.AddField(zl_temp_path, "THNNILAI", "LONG")  # Tahun Penilaian
        arcpy.management.AddField(zl_temp_path, "cluster", "TEXT", field_alias="CLUSTER")  # Cluster Zona

        arcpy.management.CalculateField(zl_temp_path, "NOZN", "!OBJECTID!", "PYTHON3")

        arcpy.management.CalculateField(zl_temp_path, "WADMKK", "'"+str(config_dan_paths['kota'])+"'", "PYTHON3")
        arcpy.management.CalculateField(zl_temp_path, "WADMPR", "'"+str(config_dan_paths['provinsi'])+"'", "PYTHON3")
        arcpy.management.CalculateField(zl_temp_path, "THNNILAI", config_dan_paths['tahun'], "PYTHON3")
        arcpy.management.CalculateField(zl_temp_path, "cluster", "1", "PYTHON3")
        
        # Tambah field JNSZN jika belum ada
        if 'JNSZN' not in in_table_fields:
            arcpy.management.AddField(zl_temp_path, "JNSZN", "SHORT")
            arcpy.management.CalculateField(zl_temp_path, "JNSZN", "1", "PYTHON3")

        # Tambah field PENGGUNAAN jika belum ada
        if 'PENGGUNAAN' not in in_table_fields:
            arcpy.management.AddField(zl_temp_path, "PENGGUNAAN", "TEXT")

        # Update nilai
        with arcpy.da.UpdateCursor(zl_temp_path, ["JNSZN", "PENGGUNAAN"]) as rows:
            for row in rows:
                if row[0] == 1:
                    row[1] = "Non-Pertanian"
                elif row[0] == 2:
                    row[1] = "Pertanian"

                rows.updateRow(row)

        # Bersihkan cursor
        del row
        del rows

                # --- Hapus field yang tidak diinginkan ---
        all_fields = [f.name for f in arcpy.ListFields(zl_temp_path)]
        
        # Dapatkan nama field geometri dan ObjectID
        desc = arcpy.Describe(zl_temp_path)
        shape_field_name = desc.shapeFieldName
        oid_field_name = desc.OIDFieldName

        desired_fields =[
            "NOZN",
            "NILAIZN",
            "JNSZN",
            "PENGGUNAAN",
            "NILBULAT",
            "HISTZONE",
            "SMPBKREL",
            "SMPBAKU",
            "JMLSMPL",
            "NILMIN",
            "NILMAKS",
            "WADMKK",
            "WADMPR",
            "THNNILAI",
            "cluster",
            shape_field_name,
            oid_field_name
        ]
        # Tambahkan field yang diperlukan sistem (seperti Shape_Length, Shape_Area) ke daftar yang dipertahankan
        for field in desc.fields:
            if not field.editable:
                if field.name not in desired_fields:
                    desired_fields.append(field.name)

        fields_to_delete = [f for f in all_fields if f not in desired_fields]

        if fields_to_delete:
            arcpy.management.DeleteField(zl_temp_path, fields_to_delete)

        arcpy.conversion.FeatureClassToFeatureClass(
            zl_temp_path,
            config_dan_paths['dataset_path'],
            'Zona_Layer',

        )
        arcpy.management.Delete(zl_temp_path)  # Hapus layer sementara      


        arcpy.SetParameter(1, config_dan_paths['zl_path'])
        
        return
 
class Upload_Delineasi_Zona_Awal_Nilai_Tanah_Pembuatan_ZNT(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Upload Delineasi Zona Awal Nilai Tanah"
        self.description = ""
        self.canRunInBackground = False


    def getParameterInfo(self):
        """Define parameter definitions"""
        self.is_gis_internal = is_internal()
        self.preferred_server = get_user_data('preferred_server')
        self.nik = get_user_data('nik')
        self.berkas = get_user_data('berkas')
        self.current_year = current_year()
        param0 = arcpy.Parameter(
            displayName="Nomor Induk Kependudukan (NIK)",
            name="username",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        if self.nik:
            param0.value = self.nik

        param1 = arcpy.Parameter(
            displayName="Nomor Berkas",
            name="project_id",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        if self.berkas:
            param1.value = self.berkas

        param2 = arcpy.Parameter(
            displayName="Tahun",
            name="tahun",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")

        param3 = arcpy.Parameter(
            displayName="Zona Layer (Feature Class)",
            name="feature_layer",
            datatype="GPFeatureLayer",  
            parameterType="Required",
            direction="Input")
        
        param4 = arcpy.Parameter(
            displayName="Server Sipenta",
            name="link",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        if self.current_year:
            param2.value = self.current_year

        if self.preferred_server:
            param4.value = self.preferred_server
        param4.filter.type = "ValueList"
        param4.filter.list = ["Produksi", "Belajar"]
        
        params = [param0, param1, param2, param3]
        # Periksa ulang status saat membuka parameter agar mengikuti login terbaru
        self.is_gis_internal = is_internal()
        if self.is_gis_internal:
            params.append(param4)
            return params
        else:
            return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return
        
    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
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

        # Validasi format Nomor Berkas (project_id): harus seperti 01/2025/0020
        input_project = parameters[1]
        if input_project.value:
            pj_str = str(input_project.value).strip()
            input_project.value = pj_str

            # Pola: 2 digit / 4 digit (tahun) / 4 digit
            import re
            pattern = r"^\d{2}/\d{4}/\d{4}$"
            if not re.match(pattern, pj_str):
                input_project.setErrorMessage("Nomor Berkas harus berbentuk NN/YYYY/NNNN, contoh: 01/2025/0020")
            else:
                input_project.clearMessage()
        return   

    def execute(self, parameters, messages):
        """The source code of the tool."""
        username = str(parameters[0].valueAsText).replace(" ", "")
        project_id = str(parameters[1].valueAsText).replace(" ", "")
        tahun = parameters[2].valueAsText
        feature_class = parameters[3].valueAsText
        server = parameters[4].valueAsText if len(parameters) > 4 else None
        use_production = True if server == "Produksi" or server == None else False
        
        validate_document_type(project_id, target='Pembuatan ZNT')
        main_upload(project_id, username, "Delineasi Zona Awal Nilai Tanah", "Pembuatan Zona Awal", "Zona_Layer", tahun, "ZNT", feature_class, use_production)

        self.preferred_server = get_user_data('preferred_server')
        self.nik = get_user_data('nik')
        self.berkas = get_user_data('berkas')
        if self.nik != username:
            renew_user_data('nik', username)
        if self.berkas != project_id:
            renew_user_data('berkas', project_id)
        if len(parameters) > 4 and server != self.preferred_server:
            renew_user_data('preferred_server', server)
        return        
