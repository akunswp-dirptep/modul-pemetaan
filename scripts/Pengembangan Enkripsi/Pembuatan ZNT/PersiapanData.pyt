from datetime import datetime
import sys
import arcpy, os, math
import arcpy, os, math

arcpy.env.outputZFlag = "Disabled"
arcpy.env.outputMFlag = "Disabled"

# Tambahkan parent directory ke sys.path
script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from zntutils.constant import PREFERRED_SERVER_KEY, PREFERRED_BERKAS_ID, CREDENTIAL_KEY, AUTH_KEY
from zntutils.document import validate_document_type, get_credentials
from zntutils.upload_utils import upload_shapefile_to_sipenta, upload_feature_layer_to_sipenta
from zntutils.system_utils import get_user_data, get_all_berkas_id, setup_user_data 
from zntutils.zona_layer import check_if_there_selected_field, get_config_values, validate_zona_layer_before_upload, check_if_there_selected_field


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
        berkas_list = get_all_berkas_id(process_type='Pembuatan ZNT')
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
            
        shapefile = arcpy.Parameter(
            displayName="Shapefile Rencana Area Kerja (.shp)",
            name="shapefile_path",
            datatype="DEFile",  
            parameterType="Required",
            direction="Input")
        
        shapefile.filter.list = ["shp"]
        
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
                if '01/' in preferred_berkas:
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
        params = [shapefile, berkas, penjelasan]
        return params
    
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
            penjelasan.value = (
                "Pastikan data sudah benar sebelum diupload.\n\n"
                "Direktorat Penilaian Tanah dan Ekonomi Pertanahan,\n"
                "Kementerian ATR/BPN.\n"
                "Tahun: {}\n".format(datetime.now().year))
        
        return 

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        shapefile_param = parameters[0]
        
        if shapefile_param.valueAsText:
            shapefile_path = shapefile_param.valueAsText
            shapefile_base = os.path.splitext(shapefile_path)[0]
            required_ext = [".shp", ".shx", ".dbf", ".prj", ".cpg", ".shp.xml", ".sbn", ".sbx"]
            missing = [
                ext for ext in required_ext
                if not os.path.exists(shapefile_base + ext)
            ]

            if missing:
                shapefile_param.setErrorMessage(
                    f"Komponen shapefile tidak lengkap.\nFile dengan ekstensi berikut tidak ditemukan: {', '.join(missing)}"
                )

        return   
    
    def execute(self, parameters, messages):
        user_data = get_user_data(CREDENTIAL_KEY)
        berkas_list = get_all_berkas_id(process_type='Pembuatan ZNT')

        if berkas_list is None:
            arcpy.AddWarning("Tidak ada berkas yang tersedia untuk dipilih. Pastikan Anda tidak salah memilih menu atau memiliki berkas yang valid untuk proses Pembuatan ZNT.")
            return
        
        shapefile_path = parameters[0].valueAsText
        berkas_value = parameters[1].valueAsText

        server = get_user_data(PREFERRED_SERVER_KEY)
        use_production = True if server == "Produksi" or server == None else False
        token = user_data.get(AUTH_KEY, None)


        validate_document_type(
            document_id=berkas_value,
            target='Pembuatan ZNT')
        
        upload_shapefile_to_sipenta(
            nomor_berkas=berkas_value,
            token=token,
            param="pembuatan_znt_peta_rencana_area_kerja",
            in_feature="Zona_Layer",
            shapefile_path=shapefile_path,
            use_production=use_production)

        setup_user_data(PREFERRED_BERKAS_ID, berkas_value)
        return

class Upload_Peta_Area_Kerja_Disepakati(object):
    def __init__(self):
        self.label = "Upload Peta Area Kerja Disepakati"
        self.description = ""
        self.canRunInBackground = False


    def getParameterInfo(self):
        berkas_list = get_all_berkas_id(process_type='Pembuatan ZNT')
        berkas_show = []
        if berkas_list is not None:
            can_show = 0
            for berkas in berkas_list:
                if berkas[1] is True:
                    berkas_show.append(f"{berkas[0]}")
                    can_show += 1
            if can_show == 0:
                berkas_show = ['Tidak ada berkas yang dapat dipilih']
        else:
            berkas_show = ['Tidak ada berkas yang dapat dipilih']
            
        shapefile = arcpy.Parameter(
            displayName="Shapefile Peta Area Kerja Disepakati (.shp)",
            name="shapefile_path",
            datatype="DEFile",  
            parameterType="Required",
            direction="Input")
        
        shapefile.filter.list = ["shp"]
        
        berkas = arcpy.Parameter(
            displayName="Berkas",
            name="link",
            datatype="GPString",
            parameterType="Required",
            direction="Input")

        berkas.filter.type = "ValueList"
        berkas.filter.list = berkas_show
        if berkas_list:
            preferred_berkas=get_user_data(PREFERRED_BERKAS_ID)
            if preferred_berkas:
                if '01/' in preferred_berkas:
                    berkas.value = preferred_berkas
                else:
                    berkas.value = berkas_show[0]     
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
        params = [shapefile, berkas, penjelasan]
        return params
    
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
            penjelasan.value = (
                "Pastikan data sudah benar sebelum diupload.\n\n"
                "Direktorat Penilaian Tanah dan Ekonomi Pertanahan,\n"
                "Kementerian ATR/BPN.\n"
                "Tahun: {}\n".format(datetime.now().year))
        
        return 

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        shapefile_param = parameters[0]
        
        if shapefile_param.valueAsText:
            shapefile_path = shapefile_param.valueAsText
            shapefile_base = os.path.splitext(shapefile_path)[0]
            required_ext = [".shp", ".shx", ".dbf", ".prj", ".cpg", ".shp.xml", ".sbn", ".sbx"]
            missing = [
                ext for ext in required_ext
                if not os.path.exists(shapefile_base + ext)
            ]

            if missing:
                shapefile_param.setErrorMessage(
                    f"Komponen shapefile tidak lengkap.\nFile dengan ekstensi berikut tidak ditemukan: {', '.join(missing)}"
                )

        return   
    
   
    def execute(self, parameters, messages):
        user_data = get_user_data(CREDENTIAL_KEY)
        berkas_list = get_all_berkas_id(process_type='Pembuatan ZNT')

        if berkas_list is None:
            arcpy.AddWarning("Tidak ada berkas yang tersedia untuk dipilih. Pastikan Anda tidak salah memilih menu atau memiliki berkas yang valid untuk proses Pembuatan ZNT.")
            return
        
        shapefile_path = parameters[0].valueAsText
        berkas_value = parameters[1].valueAsText

        server = get_user_data(PREFERRED_SERVER_KEY)
        use_production = True if server == "Produksi" or server == None else False
        token = user_data.get(AUTH_KEY, None)


        validate_document_type(
            document_id=berkas_value,
            target='Pembuatan ZNT')
        
        upload_shapefile_to_sipenta(
            nomor_berkas=berkas_value,
            token=token,
            param="pembuatan_znt_peta_area_kerja_disepakati",
            in_feature="Zona_Layer",
            shapefile_path=shapefile_path,
            use_production=use_production)
        setup_user_data(PREFERRED_BERKAS_ID, berkas_value)
        return

class Upload_Peta_Area_Kerja_Pembuatan_ZNT_AOI(object):
    
    def __init__(self):
        self.label = "Upload Peta Area Kerja (AOI)"
        self.description = ""
        self.canRunInBackground = False


    def getParameterInfo(self):
        berkas_list = get_all_berkas_id(process_type='Pembuatan ZNT')
        berkas_show = []
        if berkas_list is not None:
            can_show = 0
            for berkas in berkas_list:
                if berkas[1] is True:
                    berkas_show.append(f"{berkas[0]}")
                    can_show += 1
            if can_show == 0:
                berkas_show = ['Tidak ada berkas yang dapat dipilih']
        else:
            berkas_show = ['Tidak ada berkas yang dapat dipilih']
            
        shapefile = arcpy.Parameter(
            displayName="Shapefile Peta Area Kerja (AOI) (.shp)",
            name="shapefile_path",
            datatype="DEFile",  
            parameterType="Required",
            direction="Input")
        
        shapefile.filter.list = ["shp"]
        
        berkas = arcpy.Parameter(
            displayName="Berkas",
            name="link",
            datatype="GPString",
            parameterType="Required",
            direction="Input")

        berkas.filter.type = "ValueList"
        berkas.filter.list = berkas_show
        if berkas_list:
            preferred_berkas=get_user_data(PREFERRED_BERKAS_ID)
            if preferred_berkas:
                if '01/' in preferred_berkas:
                    berkas.value = preferred_berkas
                else:
                    berkas.value = berkas_show[0]     
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
        params = [shapefile, berkas, penjelasan]
        return params
    
    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True
    
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
            penjelasan.value = (
                "Pastikan data sudah benar sebelum diupload.\n\n"
                "Direktorat Penilaian Tanah dan Ekonomi Pertanahan,\n"
                "Kementerian ATR/BPN.\n"
                "Tahun: {}\n".format(datetime.now().year))
        
        return 

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        shapefile_param = parameters[0]
        
        if shapefile_param.valueAsText:
            shapefile_path = shapefile_param.valueAsText
            shapefile_base = os.path.splitext(shapefile_path)[0]
            required_ext = [".shp", ".shx", ".dbf", ".prj", ".cpg", ".shp.xml", ".sbn", ".sbx"]
            missing = [
                ext for ext in required_ext
                if not os.path.exists(shapefile_base + ext)
            ]

            if missing:
                shapefile_param.setErrorMessage(
                    f"Komponen shapefile tidak lengkap.\nFile dengan ekstensi berikut tidak ditemukan: {', '.join(missing)}"
                )

        return   
    
   
    def execute(self, parameters, messages):
        user_data = get_user_data(CREDENTIAL_KEY)
        berkas_list = get_all_berkas_id(process_type='Pembuatan ZNT')

        if berkas_list is None:
            arcpy.AddWarning("Tidak ada berkas yang tersedia untuk dipilih. Pastikan Anda tidak salah memilih menu atau memiliki berkas yang valid untuk proses Pembuatan ZNT.")
            return
        
        shapefile_path = parameters[0].valueAsText
        berkas_value = parameters[1].valueAsText

        server = get_user_data(PREFERRED_SERVER_KEY)
        use_production = True if server == "Produksi" or server == None else False
        token = user_data.get(AUTH_KEY, None)


        validate_document_type(
            document_id=berkas_value,
            target='Pembuatan ZNT')
        
        upload_shapefile_to_sipenta(
            nomor_berkas=berkas_value,
            token=token,
            param="pembuatan_znt_peta_area_kerja_aoi",
            in_feature="Zona_Layer",
            shapefile_path=shapefile_path,
            use_production=use_production)
        
        setup_user_data(PREFERRED_BERKAS_ID, berkas_value)

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

        dataset_path = config_dan_paths['dataset_path']  # Path dataset utama
        symbology_folder = config_dan_paths['symbology_folder']
        zl_path = os.path.join(dataset_path, "Zona_Layer")

        zl_path = os.path.join(dataset_path, "Zona_Layer")
        sim_path = os.path.join(symbology_folder, "Simbologi_Jenis_Penggunaan_Dengan_Transparansi.lyrx")

        # Membuat feature layer untuk data Zona_Layer
        arcpy.management.MakeFeatureLayer(zl_path, "Zona_Layer")
        
        arcpy.SetParameter(1, "Zona_Layer") 
        
        return
 
class Upload_Delineasi_Zona_Awal_Nilai_Tanah_Pembuatan_ZNT(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Upload Delineasi Zona Awal Nilai Tanah"
        self.description = ""
        self.canRunInBackground = False


    def getParameterInfo(self):
        """Define parameter definitions"""
        berkas_list = get_all_berkas_id(process_type='Pembuatan ZNT')
        berkas_show = []
        if berkas_list is not None:
            can_show = 0
            for berkas in berkas_list:
                if berkas[1] is True:
                    berkas_show.append(f"{berkas[0]}")
                    can_show += 1
            if can_show == 0:
                berkas_show = ['Tidak ada berkas yang dapat dipilih']
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
        if berkas_list:
            preferred_berkas=get_user_data(PREFERRED_BERKAS_ID)
            if preferred_berkas:
                if '01/' in preferred_berkas:
                    berkas.value = preferred_berkas
                else:
                    berkas.value = berkas_show[0]     
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
            penjelasan.value = (
                "Pastikan data sudah benar sebelum diupload.\n\n"
                "Direktorat Penilaian Tanah dan Ekonomi Pertanahan,\n"
                "Kementerian ATR/BPN.\n"
                "Tahun: {}\n".format(datetime.now().year))
        
        return
        
    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        return   

    def execute(self, parameters, messages):
        """The source code of the tool."""
        check_if_there_selected_field()
        user_data = get_user_data(CREDENTIAL_KEY)

        berkas_list = get_all_berkas_id(process_type='Pembuatan ZNT')

        if berkas_list is None:
            arcpy.AddWarning("Tidak ada berkas yang tersedia untuk dipilih. Pastikan Anda tidak salah memilih menu atau memiliki berkas yang valid untuk proses Pembuatan ZNT.")
            return
        
        feature_layer = parameters[0].valueAsText
        berkas_value = parameters[1].valueAsText

        server = get_user_data(PREFERRED_SERVER_KEY)
        use_production = True if server == "Produksi" or server == None else False
        token = user_data.get(AUTH_KEY, None)

        validation_error = validate_zona_layer_before_upload(feature_layer)
        if validation_error:
            arcpy.AddError(validation_error)
            sys.exit(1)
            return


        validate_document_type(berkas_value, target='Pembuatan ZNT')
        upload_feature_layer_to_sipenta(
            nomor_berkas=berkas_value,
            token=token,
            param="pembuatan_znt_delineasi_zona_awal",
            in_feature="Zona_Layer",
            feature_layer=feature_layer,
            use_production=use_production)
        
        setup_user_data(PREFERRED_BERKAS_ID, berkas_value)

        return        
