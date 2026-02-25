import arcpy, os, json, sys

from datetime import datetime
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

arcpy.env.outputZFlag = "Disabled"
arcpy.env.outputMFlag = "Disabled"

script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from zntutils.document import validate_document_type, get_credentials
from zntutils.upload_utils import main_upload
from zntutils.system_utils import get_user_data, renew_user_data
from zntutils import zona_layer as zonalayer

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

def delete_topology_file():
    config_dan_paths = zonalayer.get_config_values()
    topology_path = os.path.join(config_dan_paths['dataset_path'], 'Zona_Layer_Topology')
    if arcpy.Exists(topology_path):
        arcpy.management.Delete(topology_path)
        
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
        self.label = "Toolbox"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [Upload_Peta_Sebaran_Sampel, 
                      Upload_Peta_Simpangan_Baku_Relatif, 
                      Upload_Peta_Zona_Nilai_Tanah]


class Upload_Peta_Sebaran_Sampel:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Upload Peta Sebaran Sampel"
        self.description = ""

    def getParameterInfo(self):
        """Define parameter definitions"""
        self.is_gis_internal = is_internal()
        preferred_server = get_user_data("preferred_server") if self.is_gis_internal else None
        nik = get_user_data('nik')
        berkas = get_user_data('berkas')
        self.current_year = current_year()
        param0 = arcpy.Parameter(
            displayName="Nomor Induk Kependudukan (NIK)",
            name="username",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        if nik:
            param0.value = nik

        param1 = arcpy.Parameter(
            displayName="Nomor Berkas",
            name="project_id",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        if berkas:
            param1.value = berkas

        param2 = arcpy.Parameter(
            displayName="Tahun",
            name="tahun",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        
        param3 = arcpy.Parameter(
            displayName="Titik Sampel (Feature Class)",
            name="feature_layer",
            datatype="GPFeatureLayer",
            direction="Input")
        
        param4 = arcpy.Parameter(
            displayName="Server Sipenta",
            name="link",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        if self.current_year:
            param2.value = self.current_year

        if preferred_server:
            param4.value = preferred_server

        param4.filter.type = "ValueList"
        param4.filter.list = ["Produksi", "Belajar"]
        
        params = [param0, param1, param2, param3]

        if self.is_gis_internal:
            params.append(param4)
            return params
        else:
            return params


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
        delete_topology_file()

        
        validate_document_type(project_id, target='Pembuatan ZNT')
        main_upload(project_id, username, "Peta Sebaran Sampel", "Analisis dan Pengolahan Data", "Titik_Sampel", tahun, "ZNT", feature_class, use_production)
 
        preferred_server = get_user_data('preferred_server')
        nik = get_user_data('nik')
        berkas = get_user_data('berkas')
        if nik != username:
            renew_user_data('nik', username)
        if berkas != project_id:
            renew_user_data('berkas', project_id)
        if len(parameters) > 4 and server != preferred_server:
            renew_user_data('preferred_server', server)
        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return

class Upload_Peta_Simpangan_Baku_Relatif:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Upload Peta Simpangan Baku Relatif"
        self.description = ""

    def getParameterInfo(self):
        """Define parameter definitions"""
        self.is_gis_internal = is_internal()
        preferred_server = get_user_data("preferred_server") if self.is_gis_internal else None
        nik = get_user_data('nik')
        berkas = get_user_data('berkas')
        self.current_year = current_year()
        param0 = arcpy.Parameter(
            displayName="Nomor Induk Kependudukan (NIK)",
            name="username",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        if nik:
            param0.value = nik

        param1 = arcpy.Parameter(
            displayName="Nomor Berkas",
            name="project_id",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        if berkas:
            param1.value = berkas

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
            direction="Input")
        
        param4 = arcpy.Parameter(
            displayName="Server Sipenta",
            name="link",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        if self.current_year:
            param2.value = self.current_year

        if preferred_server:
            param4.value = preferred_server

        param4.filter.type = "ValueList"
        param4.filter.list = ["Produksi", "Belajar"]
        
        params = [param0, param1, param2, param3]

        if self.is_gis_internal:
            params.append(param4)
            return params
        else:
            return params


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
        delete_topology_file()

        
        validate_document_type(project_id, target='Pembuatan ZNT')
        main_upload(project_id, username, "Peta Standar Deviasi", "Analisis dan Pengolahan Data", "Zona_Layer", tahun, "ZNT", feature_class, use_production)
 
        preferred_server = get_user_data('preferred_server')
        nik = get_user_data('nik')
        berkas = get_user_data('berkas')
        if nik != username:
            renew_user_data('nik', username)
        if berkas != project_id:
            renew_user_data('berkas', project_id)
        if len(parameters) > 4 and server != preferred_server:
            renew_user_data('preferred_server', server)
        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return

class Upload_Peta_Zona_Nilai_Tanah:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Upload Peta Zona Nilai Tanah"
        self.description = ""

    def getParameterInfo(self):
        """Define parameter definitions"""
        self.is_gis_internal = is_internal()
        preferred_server = get_user_data("preferred_server") if self.is_gis_internal else None
        nik = get_user_data('nik')
        berkas = get_user_data('berkas')
        self.current_year = current_year()
        param0 = arcpy.Parameter(
            displayName="Nomor Induk Kependudukan (NIK)",
            name="username",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        if nik:
            param0.value = nik

        param1 = arcpy.Parameter(
            displayName="Nomor Berkas",
            name="project_id",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        if berkas:
            param1.value = berkas

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
            direction="Input")
        
        param4 = arcpy.Parameter(
            displayName="Server Sipenta",
            name="link",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        if self.current_year:
            param2.value = self.current_year

        if preferred_server:
            param4.value = preferred_server

        param4.filter.type = "ValueList"
        param4.filter.list = ["Produksi", "Belajar"]
        
        params = [param0, param1, param2, param3]

        if self.is_gis_internal:
            params.append(param4)
            return params
        else:
            return params


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
        delete_topology_file()

        
        validate_document_type(project_id, target='Pembuatan ZNT')
        main_upload(project_id, username, "Peta Zona Nilai Tanah", "Analisis dan Pengolahan Data", "Zona_Layer", tahun, "ZNT", feature_class, use_production)
 
        preferred_server = get_user_data('preferred_server')
        nik = get_user_data('nik')
        berkas = get_user_data('berkas')
        if nik != username:
            renew_user_data('nik', username)
        if berkas != project_id:
            renew_user_data('berkas', project_id)
        if len(parameters) > 4 and server != preferred_server:
            renew_user_data('preferred_server', server)
        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return
