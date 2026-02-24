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
from zntutils.zona_layer import get_config_values, check_if_there_selected_field

# ======================
# ENVIRONMENT SETTINGS
# ======================
arcpy.env.outputZFlag = "Disabled"
arcpy.env.outputMFlag = "Disabled"


#Helper Functions
def is_internal():
    try:
        return bool(get_credentials(credential_type="OperatorGISInternal", use_for_tools_validity=True))
        # return True
    except Exception:
        return False


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
        
    # Refresh katalog
    try:
        arcpy.management.RefreshCatalog(toolbox_folder)
    except Exception:
        try:
            arcpy.RefreshCatalog(toolbox_folder)
        except Exception:
            pass
        
    # Load toolbox di proyek saat ini
    try:
        # Hapus dan reload menggunakan ImportToolbox (lebih reliable)
        for pyt_file in pyt_files:
            pyt_path = os.path.join(toolbox_folder, pyt_file)
            try:
                arcpy.ImportToolbox(pyt_path)
            except Exception as e:
                arcpy.AddWarning(f"? Gagal memuat {pyt_file}: {str(e)}")
            
    except Exception as e:
        arcpy.AddWarning(f"Error saat reload toolbox: {str(e)}")

def renew_preferred_server(server:str):
    
    setup_preferred_server_connection(server)
    all_toolboxes_folder_need_reload = [
                r"C:\PenilaianTanah\scripts\Pengembangan Enkripsi\Pembaruan ZNT",
                r"C:\PenilaianTanah\scripts\Pengembangan Enkripsi\Pembuatan ZNT"
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
        self.label = "Toolboxes Umum ZNT - Pengolahan Data Dasar"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [Hitung_Luas_Zona_M2, 
                      Kodifikasi_Zona, 
                      Upload_Peta_Zona_Awal_Nilai_Tanah_Pembuatan_ZNT,
                      Upload_Peta_Zona_Awal_Nilai_Tanah_Pembaruan_ZNT]


class Hitung_Luas_Zona_M2:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Hitung Luas Zona"
        self.description = "Tools untuk menghitung luas zona dalam meter persegi pada Zona Layer"

    def getParameterInfo(self):
        """Define the tool parameters."""

        penjelasan = arcpy.Parameter(
            displayName="Apa yang dilakukan tool ini?",
            name="penjelasan",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )

        penjelasan.value = (
        "Menambahkan field Luas_M2 apabila belum tersedia, serta\n" 
        "menghitung luas setiap fitur dalam satuan meter persegi (m²) dan\n"
        "menyimpannya ke field tersebut. Jika field Luas_M2 sudah ada,\n"
        "nilainya akan diperbarui dengan hasil perhitungan terbaru"
        )

        return [penjelasan]

        params = None
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
        return

    def execute(self, parameters, messages):
        """
        Kondisi yang harus dipenuhi oleh tools ini:

        1. Pastikan tidak ada field yang sedang dipilih (selected) di Zona_Layer.
        2. Hapus topologi Zona_Layer_Topology jika ada.
        3. Field Luas_M2 ditambahkan ke layer Zona_Layer dengan tipe data LONG (integer) dan diatur sebagai nullable.
        4. Hitung luas setiap fitur di Zona_Layer dalam meter persegi dan simpan nilainya di field Luas_M2.
        5. Jika field Luas_M2 sudah ada, perbarui nilainya dengan perhitungan terbaru.
        6. Pastikan tools dapat dijalankan berulang kali tanpa menimbulkan error
        """
        
        config_dan_paths = get_config_values()
        dataset_path = config_dan_paths["dataset_path"]

        # Pemenuhan kondisi No.1
        check_if_there_selected_field()
        zl = "Zona_Layer"
        topo = 'Zona_Layer_Topology'
        topologi = os.path.join(dataset_path, 'Zona_Layer_Topology')

        try:
            # Pemenuhan kondisi No.2
            if arcpy.Exists(topologi):
                arcpy.management.RemoveFeatureClassFromTopology(topologi, "Zona_Layer")

            if arcpy.Exists(topo):
                arcpy.management.Delete(topo)

            # Pemenuhan kondisi No.3 dan No.5
            arcpy.management.AddField(zl, "Luas_M2", "LONG", "", "", "", "", "NULLABLE", "NON_REQUIRED")
            
            # Pemenuhan kondisi No.4
            arcpy.management.CalculateField(zl, "Luas_M2", '!Shape.Area@meter!', "PYTHON3")
        
        except Exception as e:
            arcpy.AddWarning(f"Gagal menghitung luas zona: {str(e)}")

        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return

class Kodifikasi_Zona:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Kodifikasi Zona"
        self.description = "Tools untuk membuat kodifikasi zona pada Zona Layer (HISTZONE)"

    def getParameterInfo(self):
        """Define the tool parameters."""
        penjelasan = arcpy.Parameter(
            displayName="Apa yang dilakukan tool ini?",
            name="penjelasan",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )

        penjelasan.value = (
            "Tools membuat atau memperbarui field HISTZONE\n"
            "dengan menggabungkan nomor zona (NOZN)\n"
            "dan jenis zona (JNSZN) sambil mempertahankan\n"
            "riwayat perubahan zona.\n"
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
        # ======================
        # PATH CONFIGURATION
        # ======================

        config_dan_paths = get_config_values()
        zl_path = config_dan_paths['zl_path']

        
        # ======================
        # UNSELECT FIELD 
        # ======================

        check_if_there_selected_field()

        # ======================
        # MAIN PROCESSING
        # ======================
        # Mendapatkan daftar field yang ada dalam layer
        field_names = [field.name for field in arcpy.ListFields(zl_path)]

        # Memeriksa apakah field HISTZONE sudah ada
        if "HISTZONE" not in field_names:
            """
            JIKA HISTZONE BELUM ADA:
            Membuat field HISTZONE baru dengan urutan nomor dan tipe zona
            """

            # Membuat field sementara untuk menyimpan tipe zona
            arcpy.AddField_management(zl_path, "temp", "STRING")

            # Mengisi field temp dengan 'N' atau 'P' berdasarkan JNSZN. N berarti NON-PERTANIAN, P berarti PERTANIAN
            expression = "abc(!JNSZN!)"
            codeblock = """def abc(JNSZN):
                if JNSZN == 1:
                    return 'N'  
                elif JNSZN == 2:
                    return 'P'  
                else:
                    return ''   
                """
            arcpy.management.CalculateField(zl_path, "temp", expression, "PYTHON3", codeblock)
            
            # Menggabungkan NOZN dan temp menjadi HISTZONE (contoh: "1N", "2P")
            arcpy.management.CalculateField(zl_path, "HISTZONE", "str(!NOZN!) + !temp!", "PYTHON3")
            
            # Menghapus field sementara
            arcpy.management.DeleteField(zl_path, "temp")

        else:
            """
            JIKA HISTZONE SUDAH ADA:
            Memperbarui nilai HISTZONE dengan mempertahankan nilai historis
            """
            
            # Menyimpan nilai HISTZONE yang ada ke field sementara
            arcpy.management.AddField(zl_path, "temp1", "STRING")
            arcpy.management.CalculateField(zl_path, "temp1", "!HISTZONE!", "PYTHON3")


            # Membuat field sementara untuk nilai zona baru
            arcpy.management.AddField(zl_path, "temp2", "STRING")
            
            # Mengisi field temp2 dengan 'N' atau 'P' berdasarkan JNSZN
            expression = "abc(!JNSZN!)"
            codeblock = """def abc(JNSZN):
                if JNSZN == 1:
                    return 'N' 
                elif JNSZN == 2:
                    return 'P' 
                else:
                    return ''  
                """
            arcpy.management.CalculateField(zl_path, "temp2", expression, "PYTHON3", codeblock)
            
            # Membuat field sementara untuk gabungan NOZN + temp2
            arcpy.management.AddField(zl_path, "temp", "STRING")
            arcpy.management.CalculateField(zl_path, "temp", "str(!NOZN!) + !temp2!", "PYTHON3")
            
            # Membuat field sementara untuk hasil akhir
            arcpy.management.AddField(zl_path, "temp3", "STRING")
            """
            MEMPROSES LOGIKA HISTZONE:
            - Membandingkan nilai lama (temp1) dengan nilai baru (temp)
            - Menerapkan logika khusus untuk mempertahankan atau menggabungkan nilai
            """
            with arcpy.da.UpdateCursor(zl_path, ["temp1", "temp", "temp3"]) as rows:
                for row in rows:
                    # Jika nilai lama pendek (<3 karakter)
                    if len(row[0]) < 3:
                        if row[0] == row[1]:  # Jika nilai lama sama dengan baru
                            row[2] = row[1]   # Gunakan nilai baru
                        elif row[0] != row[1]:  # Jika berbeda
                            row[2] = row[0] + row[1]  # Gabungkan lama + baru
                    
                    # Jika nilai lama panjang (=3 karakter)
                    else:
                        if row[0][-2:] == row[1][-2:]:  # Jika 2 karakter akhir sama
                            row[2] = row[0]  # Pertahankan nilai lama
                        elif row[0][-2:] != row[1][-2:]:  # Jika 2 karakter akhir berbeda
                            row[2] = row[0] + row[1]  # Gabungkan lama + baru
                    
                    rows.updateRow(row)
            del rows, row
            
            # Memindahkan hasil akhir ke field HISTZONE
            arcpy.CalculateField_management(zl_path, "HISTZONE", "!temp3!", "PYTHON3")
            
            # Membersihkan semua field sementara
            arcpy.DeleteField_management(zl_path, "temp2")
            arcpy.DeleteField_management(zl_path, "temp")
            arcpy.DeleteField_management(zl_path, "temp1")
            arcpy.DeleteField_management(zl_path, "temp3")

        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return

class Upload_Peta_Zona_Awal_Nilai_Tanah_Pembuatan_ZNT(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Upload Peta Zona Awal Nilai Tanah"
        self.description = ""
        self.canRunInBackground = False


    def getParameterInfo(self):
        """Define parameter definitions"""
        self.is_gis_internal = is_internal()
        self.preferred_server = get_preferred_server_connection()
        self.current_year = int(datetime.now().year)
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
        self.preferred_server = get_preferred_server_connection()
        main_upload(project_id, username, "Survei Batas Zona Awal Nilai Tanah", "Survei Batas Zona Awal Nilai Tanah", "Zona_Layer", tahun, "ZNT", feature_class, use_production)
        if len(parameters) > 4 and server != self.preferred_server:
            renew_preferred_server(server)
        return        

class Upload_Peta_Zona_Awal_Nilai_Tanah_Pembaruan_ZNT(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Upload Peta Zona Awal Nilai Tanah"
        self.description = ""
        self.canRunInBackground = False


    def getParameterInfo(self):
        """Define parameter definitions"""
        self.is_gis_internal = is_internal()
        self.preferred_server = get_preferred_server_connection()
        self.current_year = int(datetime.now().year)
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
        
        self.preferred_server = get_preferred_server_connection()
        validate_document_type(project_id, target='Pembaruan ZNT')
        main_upload(project_id, username, "pembaruan_znt_peta_hasil_survei_batas_zona_shp", "Analisis dan Pengolahan Data", "Zona_Layer", tahun, "ZNT", feature_class, use_production)
        
        
        if len(parameters) > 4 and server != self.preferred_server:
            renew_preferred_server(server)
        return        
