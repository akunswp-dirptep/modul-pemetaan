# -*- coding: utf-8 -*-

from datetime import datetime
import sys
import arcpy, os, json
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

arcpy.env.outputZFlag = "Disabled"
arcpy.env.outputMFlag = "Disabled"

# Tambahkan parent directory ke sys.path
script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from zntutils.constant import NAMA_PROVINSI, KAB_KOTA
from zntutils.document import validate_document_type, get_credentials
from zntutils.upload_utils import main_upload_shapefile, main_upload
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
def generate_key():
    password = 'bpnri-jakarta'
    salt = b'Sisinga@2-Jakarta'  

    # Derive proper key dari password
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key

def simpan_ke_bin(data_terenkripsi, nama_file):
    """Menyimpan data bytes ke dalam file biner."""
    try:
        with open(nama_file, 'wb') as file:
            file.write(data_terenkripsi)
        print(f"Pesan berhasil disimpan ke {nama_file}")
    except IOError as e:
        print(f"Terjadi kesalahan saat menulis ke file: {e}")

def baca_dari_bin(nama_file):
    """Membaca data bytes dari file biner."""
    data_terenkripsi = None
    try:
        with open(nama_file, 'rb') as file:
            data_terenkripsi = file.read()
        print(f"Pesan berhasil dibaca dari {nama_file}")
        return data_terenkripsi
    except IOError as e:
        print(f"Terjadi kesalahan saat membaca file: {e}")
        return None
    
def encrypt_message(message: str, key: bytes, path) -> bytes:
    fernet = Fernet(key)
    encrypted_message = fernet.encrypt(message.encode())
    simpan_ke_bin(encrypted_message, path)
    return encrypted_message

def decrypt_message(key: bytes, path) -> str:
    encrypted_message = baca_dari_bin(path)
    fernet = Fernet(key)
    decrypted_message = fernet.decrypt(encrypted_message).decode()
    data = json.loads(decrypted_message)
    return data

def get_preferred_server_connection():
    config_path = r'C:\PenilaianTanah\config\penilaiantanah.bin'

    try:
        if os.path.exists(config_path):
            data = decrypt_message(generate_key(), config_path) 
            preferred_server = data.get('preferred_server', None)
            return preferred_server
        else:
            return None
        
    except Exception as e:
        arcpy.AddError(f"Gagal membaca user config: {str(e)}")
        return None
    
def setup_preferred_server_connection(preferred_server: str):

    config_path = r'C:\PenilaianTanah\config\penilaiantanah.bin'

    try:
        # Cek apakah file ada
        if os.path.exists(config_path):
            # File ada, baca isinya
            try:
                data = decrypt_message(generate_key(), config_path)                    
                # Validasi format JSON
                if 'preferred_server' not in data or not isinstance(data['preferred_server'], str):
                    # Format tidak sesuai, buat struktur baru
                    data = {"preferred_server": preferred_server}
                
                if data['preferred_server'] != preferred_server:
                    data['preferred_server'] = preferred_server
                    
            except json.JSONDecodeError:
                # File rusak/tidak valid, buat struktur baru
                arcpy.AddWarning("File config.json rusak, membuat struktur baru...")
                data = {"preferred_server": preferred_server}
        else:
            # File belum ada, buat struktur baru
            # Pastikan direktori Menu ada
            menu_dir = os.path.dirname(config_path)
            if not os.path.exists(menu_dir):
                os.makedirs(menu_dir)
            
            data = {"preferred_server": preferred_server}
        

        # Simpan kembali ke file
        encrypt_message(json.dumps(data), generate_key(), config_path)
        
        return True
        
    except Exception as e:
        arcpy.AddError(f"Gagal menyimpan user config: {str(e)}")
        return False

def reload_all_toolboxes_in_folder(toolbox_folder):
     
    if not os.path.exists(toolbox_folder):
        arcpy.AddError(f"Folder toolbox tidak ditemukan: {toolbox_folder}")
        return
        
     # Cari semua file .pyt di folder
    pyt_files = [f for f in os.listdir(toolbox_folder) if f.endswith('.pyt')]
        
    if not pyt_files:
        arcpy.AddWarning(f"Tidak ada file .pyt ditemukan di {toolbox_folder}")
        return
        
    # Load toolbox di proyek saat ini
    try:
        # Hapus dan reload menggunakan ImportToolbox (lebih reliable)
        for pyt_file in pyt_files:
            pyt_path = os.path.join(toolbox_folder, pyt_file)
            try:
                arcpy.ImportToolbox(pyt_path)
            except Exception as e:
                arcpy.AddWarning(f"Gagal memuat ulang {pyt_file}: {str(e)}")
            
    except Exception as e:
        arcpy.AddWarning(f"Error saat reload toolbox: {str(e)}")

def renew_preferred_server(server:str):
    
    setup_preferred_server_connection(server)
    all_toolboxes_folder_need_reload = [
                r"C:\PenilaianTanah\scripts\Pengembangan Enkripsi\Pembaruan ZNT",
                r"C:\PenilaianTanah\scripts\Pengembangan Enkripsi\Pembuatan ZNT",
                r"C:\PenilaianTanah\scripts\Pengembangan Enkripsi\Toolboxes Umum ZNT"
            ]

    try:
        for folder in all_toolboxes_folder_need_reload:
            reload_all_toolboxes_in_folder(folder)

    except Exception as e:
        arcpy.AddWarning(f"Gagal memuat ulang toolbox: {str(e)}")

class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [Upload_Peta_Sebaran_Sampel_Pembaruan, 
                      Upload_Peta_Sebaran_Titik_Zona, 
                      Upload_Peta_Zona_Nilai_Tanah_Pembaruan]


#========== Analisis dan Pengolahan Data - Peta Sebaran Sampel ==========
class Upload_Peta_Sebaran_Sampel_Pembaruan(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Upload Pembaruan Peta Sebaran Sampel"
        self.description = ""
        self.canRunInBackground = False


    def getParameterInfo(self):
        """Define parameter definitions"""
        self.is_gis_internal = is_internal()
        self.preferred_server = get_preferred_server_connection()
        self.current_year = current_year()
        param0 = arcpy.Parameter(
            displayName="Nomor Induk Kependudukan (NIK)",
            name="username",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param1 = arcpy.Parameter(
            displayName="Nomor Berkas",
            name="project_id",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
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

        if self.preferred_server:
            param4.value = self.preferred_server

        param4.filter.type = "ValueList"
        param4.filter.list = ["Produksi", "Belajar"]
        
        params = [param0, param1, param2, param3]

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
        self.preferred_server = get_preferred_server_connection()
        delete_topology_file()
        validate_document_type(project_id, target='Pembaruan ZNT')
        main_upload(project_id, username, "pembaruan_znt_data_shp_titik_sampel", "Analisis dan Pengolahan Data", "Titik_Sampel", tahun, "ZNT", feature_class, use_production)

        if len(parameters) > 4 and server != self.preferred_server:
            renew_preferred_server(server)

        return


class Upload_Peta_Sebaran_Titik_Zona(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Upload Pembaruan Peta Sebaran Titik Zona"
        self.description = ""
        self.canRunInBackground = False
        self.is_gis_internal = is_internal()

    def getParameterInfo(self):
        """Define parameter definitions"""
        self.is_gis_internal = is_internal()
        self.preferred_server = get_preferred_server_connection()
        self.current_year = current_year()
        param0 = arcpy.Parameter(
            displayName="Nomor Induk Kependudukan (NIK)",
            name="username",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param1 = arcpy.Parameter(
            displayName="Nomor Berkas",
            name="project_id",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param2 = arcpy.Parameter(
            displayName="Tahun",
            name="tahun",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        param3 = arcpy.Parameter(
            displayName="Titik Zona (Feature Class)",
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
        self.preferred_server = get_preferred_server_connection()
        delete_topology_file()
        validate_document_type(project_id, target='Pembaruan ZNT')
        main_upload(project_id, username, "pembaruan_znt_data_shp_titik_zona", "Analisis dan Pengolahan Data", "Zona_Layer", tahun, "ZNT", feature_class, use_production)
        if len(parameters) > 4 and server != self.preferred_server:
            renew_preferred_server(server)        
        return

#========== Analisis dan Pengolahan Data - Peta Zona Nilai Tanah ==========
class Upload_Peta_Zona_Nilai_Tanah_Pembaruan(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Upload Pembaruan Peta Zona Nilai Tanah"
        self.description = ""
        self.canRunInBackground = False
        self.is_gis_internal = is_internal()

    def getParameterInfo(self):
        """Define parameter definitions"""
        self.is_gis_internal = is_internal()
        self.preferred_server = get_preferred_server_connection()
        self.current_year = current_year()
        param0 = arcpy.Parameter(
            displayName="Nomor Induk Kependudukan (NIK)",
            name="username",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param1 = arcpy.Parameter(
            displayName="Nomor Berkas",
            name="project_id",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
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
        self.preferred_server = get_preferred_server_connection()
        delete_topology_file()
        validate_document_type(project_id, target='Pembaruan ZNT')
        main_upload(project_id, username, "pembaruan_znt_data_shp_zona_nilai_tanah", "Analisis dan Pengolahan Data", "Zona_Layer", tahun, "ZNT", feature_class, use_production)
        if len(parameters) > 4 and server != self.preferred_server:
            renew_preferred_server(server)        
        return
