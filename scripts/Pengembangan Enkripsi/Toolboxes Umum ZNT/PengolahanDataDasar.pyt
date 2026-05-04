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
from zntutils.upload_utils import upload_feature_layer_to_sipenta
from zntutils.zona_layer import get_config_values, check_if_there_selected_field, validate_zona_layer_before_upload
from zntutils.system_utils import get_user_data, renew_user_data, get_all_berkas_id
from zntutils.constant import CREDENTIAL_KEY, AUTH_KEY, PREFERRED_SERVER_KEY, PREFERRED_BERKAS_ID

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
            "Menghitung luas masing-masing zona (m²)\n"
            "dan menyimpannya ke field [Luas_M2].\n\n"
            " - Field dibuat jika belum ada\n"
            " - Nilai diperbarui jika sudah ada\n\n"
            "Direktorat Penilaian Tanah & Ekonomi Pertanahan\n"
            "Kementerian ATR/BPN\n"
            "Tahun: {}".format(datetime.now().year)
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
            "Membuat atau memperbarui field [HISTZONE]\n"
            "berdasarkan nomor zona dan jenis zona.\n\n"
            " - Menggabungkan nilai [NOZN] dan [JNSZN]\n"
            " - Menyimpan riwayat perubahan zona\n"
            " - Field diperbarui jika sudah ada\n\n"
            "Direktorat Penilaian Tanah & Ekonomi Pertanahan\n"
            "Kementerian ATR/BPN\n"
            "Tahun: {}".format(datetime.now().year)
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

        config_dan_paths = get_config_values()
        zl_path = config_dan_paths['zl_path']

        check_if_there_selected_field()

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
            arcpy.management.CalculateField(zl_path, "HISTZONE", "!temp3!", "PYTHON3")
            
            # Membersihkan semua field sementara
            arcpy.management.DeleteField(zl_path, "temp2")
            arcpy.management.DeleteField(zl_path, "temp")
            arcpy.management.DeleteField(zl_path, "temp1")
            arcpy.management.DeleteField(zl_path, "temp3")

        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return

class Upload_Peta_Zona_Awal_Nilai_Tanah_Pembuatan_ZNT(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Upload Peta Survei Batas ZANT"
        self.description = ""
        self.canRunInBackground = False


    def getParameterInfo(self):
        """Define parameter definitions"""
        
        berkas_list = get_all_berkas_id(process_type='Pembuatan ZNT')
        berkas_show = []
        if berkas_list is not None:
            for berkas in berkas_list:
                if berkas[1] is True:
                    berkas_show.append(f"{berkas[0]}")
        else:
            berkas_show = ['Tidak ada berkas yang dapat dipilih']

        feature_layer = arcpy.Parameter(
            displayName="Zona Layer (Feature Layer)",
            name="feature_layer",
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
        berkas.filter.type = "ValueList"
        berkas.filter.list = berkas_show
        if berkas_list:
            preferred_berkas = get_user_data(PREFERRED_BERKAS_ID)
            if '01/' in preferred_berkas:
                berkas.value = preferred_berkas if preferred_berkas else berkas_show[0]
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
        params = [feature_layer, berkas, penjelasan]
        return params


    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        feature_layer = parameters[0]
        berkas = parameters[1]
        penjelasan = parameters[2]

        is_login = get_user_data(CREDENTIAL_KEY)

        if is_login is None:
            feature_layer.enabled = False
            berkas.enabled = False
            penjelasan.enabled = True
        else:
            feature_layer.enabled = True
            berkas.enabled = True
            penjelasan.enabled = False
        return

        
    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        return   

    def execute(self, parameters, messages):
        """The source code of the tool."""
        check_if_there_selected_field()
        user_data = get_user_data(CREDENTIAL_KEY)

        berkas_list = get_all_berkas_id(process_type='Pembaruan ZNT')

        if berkas_list is None:
            arcpy.AddWarning("Tidak ada berkas yang tersedia untuk dipilih. Pastikan Anda tidak salah memilih menu atau memiliki berkas yang valid untuk proses Pembaruan ZNT.")
            return
        
        feature_layer = parameters[0].valueAsText
        berkas_value = parameters[1].valueAsText

        server = get_user_data(PREFERRED_SERVER_KEY)
        use_production = True if server == "Produksi" or server == None else False
        token = user_data.get(AUTH_KEY, None)

        validation_error = validate_zona_layer_before_upload(feature_layer)
        if validation_error:
            arcpy.AddError(validation_error)
            return



        validate_document_type(berkas_value, target='Pembaruan ZNT')
        upload_feature_layer_to_sipenta(
            nomor_berkas=berkas_value,
            token=token,
            param="pembuatan_znt_survei_batas_zona_awal",
            in_feature="Zona_Layer",
            feature_layer=feature_layer,
            use_production=use_production)
        return             

class Upload_Peta_Zona_Awal_Nilai_Tanah_Pembaruan_ZNT(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Upload Peta Hasil Survei Batas ZNT Diperbarui"
        self.description = ""
        self.canRunInBackground = False


    def getParameterInfo(self):
        """Define parameter definitions"""
        berkas_list = get_all_berkas_id(process_type='Pembaruan ZNT')
        berkas_show = []
        if berkas_list is not None:
            for berkas in berkas_list:
                if berkas[1] is True:
                    berkas_show.append(f"{berkas[0]}")
        else:
            berkas_show = ['Tidak ada berkas yang dapat dipilih']

        feature_layer = arcpy.Parameter(
            displayName="Zona Layer (Feature Layer)",
            name="feature_layer",
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
        berkas.filter.type = "ValueList"
        berkas.filter.list = berkas_show
        if berkas_list:
            preferred_berkas = get_user_data(PREFERRED_BERKAS_ID)
            if '02/' in preferred_berkas:
                berkas.value = preferred_berkas if preferred_berkas else berkas_show[0]
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
        params = [feature_layer, berkas, penjelasan]
        return params


    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        feature_layer = parameters[0]
        berkas = parameters[1]
        penjelasan = parameters[2]

        is_login = get_user_data(CREDENTIAL_KEY)

        if is_login is None:
            feature_layer.enabled = False
            berkas.enabled = False
            penjelasan.enabled = True
        else:
            feature_layer.enabled = True
            berkas.enabled = True
            penjelasan.enabled = False
        
        return


        
    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        return   

    def execute(self, parameters, messages):
        """The source code of the tool."""
        check_if_there_selected_field()
        user_data = get_user_data(CREDENTIAL_KEY)

        berkas_list = get_all_berkas_id(process_type='Pembaruan ZNT')

        if berkas_list is None:
            arcpy.AddWarning("Tidak ada berkas yang tersedia untuk dipilih. Pastikan Anda tidak salah memilih menu atau memiliki berkas yang valid untuk proses Pembaruan ZNT.")
            return
        
        feature_layer = parameters[0].valueAsText
        berkas_value = parameters[1].valueAsText

        server = get_user_data(PREFERRED_SERVER_KEY)
        use_production = True if server == "Produksi" or server == None else False
        token = user_data.get(AUTH_KEY, None)

        validation_error = validate_zona_layer_before_upload(feature_layer)
        if validation_error:
            arcpy.AddError(validation_error)
            return



        validate_document_type(berkas_value, target='Pembaruan ZNT')
        upload_feature_layer_to_sipenta(
            nomor_berkas=berkas_value,
            token=token,
            param="pembaruan_znt_peta_hasil_survei_batas_zona_shp",
            in_feature="Zona_Layer",
            feature_layer=feature_layer,
            use_production=use_production)
        return      
