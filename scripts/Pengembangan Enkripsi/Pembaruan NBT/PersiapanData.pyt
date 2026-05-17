from datetime import datetime
import json
import sys
import arcpy, os, math

# Tambahkan parent directory ke sys.path
script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from nbtutils import constant, persil
from zntutils.document import validate_document_type, get_credentials
from zntutils.system_utils import get_user_data, renew_user_data, get_all_berkas_id, setup_user_data
from zntutils.constant import PREFERRED_BERKAS_ID, CREDENTIAL_KEY, PREFERRED_SERVER_KEY, AUTH_KEY, NAMA_PROVINSI, KAB_KOTA
from zntutils.upload_utils import upload_shapefile_to_sipenta
from zntutils import zona_layer

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
        self.label = "Toolbox"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [Upload_Peta_Rencana_Lokasi_Kegiatan_AOI,
                      Upload_Peta_Lokasi_Kegiatan_Disepakati_AOI,
                      Upload_Peta_Peta_Area_Kerja_AOI,
                      Buat_Workspace_Pembaruan_NBT,
                      Masukkan_Data_NBT_Sebelumnya, 
                      Tes_Buat_Workspace_Pembaruan_NBT,
                      ImportDataNBTSebelumnya
                      ]

class Upload_Peta_Rencana_Lokasi_Kegiatan_AOI(object):
    def __init__(self):
        self.label = "Upload Peta Rencana Lokasi Kegiatan (AOI)"
        self.description = ""
        self.canRunInBackground = False


    def getParameterInfo(self):
        berkas_list = get_all_berkas_id(process_type='Pembaruan NBT')
        berkas_show = []
        if berkas_list is not None:
            for berkas in berkas_list:
                if berkas[1] is True:
                    berkas_show.append(f"{berkas[0]}")
        else:
            berkas_show = ['Tidak ada berkas yang dapat dipilih']

        shapefile = arcpy.Parameter(
            displayName="Shapefile Rencana Lokasi Kegiatan (.shp)",
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
            preferred_berkas = get_user_data(PREFERRED_BERKAS_ID)

            if preferred_berkas and preferred_berkas.startswith('04'):
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
        
        shapefile_path = parameters[0].valueAsText
        berkas_value = parameters[1].valueAsText

        server = get_user_data(PREFERRED_SERVER_KEY)
        use_production = True if server == "Produksi" or server == None else False
        token = user_data.get(AUTH_KEY, None)

        validate_document_type(
            document_id=berkas_value,
            target='Pembaruan NBT')
        
        upload_shapefile_to_sipenta(
            nomor_berkas=berkas_value,
            token=token,
            param="pembaruan_nbt_peta_rencana_lokasi_kegiatan",
            in_feature="Persil",
            shapefile_path=shapefile_path,
            use_production=use_production)

        setup_user_data(PREFERRED_BERKAS_ID, berkas_value)
        return

class Upload_Peta_Lokasi_Kegiatan_Disepakati_AOI(object):
    def __init__(self):
        self.label = "Upload Peta Lokasi Kegiatan Disepakati (AOI)"
        self.description = ""
        self.canRunInBackground = False


    def getParameterInfo(self):
        berkas_list = get_all_berkas_id(process_type='Pembaruan NBT')
        berkas_show = []
        if berkas_list is not None:
            for berkas in berkas_list:
                if berkas[1] is True:
                    berkas_show.append(f"{berkas[0]}")
        else:
            berkas_show = ['Tidak ada berkas yang dapat dipilih']

        shapefile = arcpy.Parameter(
            displayName="Shapefile Lokasi Kegiatan Disepakati(.shp)",
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
            preferred_berkas = get_user_data(PREFERRED_BERKAS_ID)

            if preferred_berkas and preferred_berkas.startswith('04'):
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
        
        shapefile_path = parameters[0].valueAsText
        berkas_value = parameters[1].valueAsText
        server = get_user_data(PREFERRED_SERVER_KEY)
        use_production = True if server == "Produksi" or server == None else False
        token = user_data.get(AUTH_KEY, None)

        validate_document_type(
            document_id=berkas_value,
            target='Pembaruan NBT')
        
        upload_shapefile_to_sipenta(
            nomor_berkas=berkas_value,
            token=token,
            param="pembaruan_nbt_peta_lokasi_kegiatan_yang_disepakati",
            in_feature="Persil",
            shapefile_path=shapefile_path,
            use_production=use_production)

        setup_user_data(PREFERRED_BERKAS_ID, berkas_value)
        return

class Upload_Peta_Peta_Area_Kerja_AOI(object):
    def __init__(self):
        self.label = "Upload Peta Area Kerja (AOI)"
        self.description = ""
        self.canRunInBackground = False


    def getParameterInfo(self):
        berkas_list = get_all_berkas_id(process_type='Pembaruan NBT')
        berkas_show = []
        if berkas_list is not None:
            for berkas in berkas_list:
                if berkas[1] is True:
                    berkas_show.append(f"{berkas[0]}")
        else:
            berkas_show = ['Tidak ada berkas yang dapat dipilih']

        shapefile = arcpy.Parameter(
            displayName="Shapefile Peta Area Kerja(.shp)",
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
            preferred_berkas = get_user_data(PREFERRED_BERKAS_ID)

            if preferred_berkas and preferred_berkas.startswith('04'):
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
        
        shapefile_path = parameters[0].valueAsText
        berkas_value = parameters[1].valueAsText
        server = get_user_data(PREFERRED_SERVER_KEY)
        use_production = True if server == "Produksi" or server == None else False
        token = user_data.get(AUTH_KEY, None)

        validate_document_type(
            document_id=berkas_value,
            target='Pembaruan NBT')
        
        upload_shapefile_to_sipenta(
            nomor_berkas=berkas_value,
            token=token,
            param="pembaruan_nbt_peta_area_kerja",
            in_feature="Persil",
            shapefile_path=shapefile_path,
            use_production=use_production)

        setup_user_data(PREFERRED_BERKAS_ID, berkas_value)
        return

class Buat_Workspace_Pembaruan_NBT(object):
    def __init__(self):
        self.label = "Buat Workspace"
        self.description = ""
        self.canRunInBackground = False


    def getParameterInfo(self):
        
        workspace_folder = arcpy.Parameter(
            displayName='Folder Penyimpanan',
            name = 'folder_path',
            datatype='DEFolder',
            parameterType='Required',
            direction='Input'
        )

        feature_layer = arcpy.Parameter(
            displayName='Persil Baru',
            name="feature_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )

        output_fl = arcpy.Parameter(
            name = 'fl_output',
            datatype='GPFeatureLayer',
            parameterType='Derived',
            direction='Output'
        )
        
        return [workspace_folder, feature_layer, output_fl]
        

        
    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return   
    
    def updateParameters(self, parameters):
        return

    
    def execute(self, parameters, messages):
        # Kondisi yang harus dipenuhi
        # 1. Ambil input dari user/tool ArcGIS
        # 2. Mengecek Koordinat harus TM-3
        # 3. Bersihkan dan buat ulang file konfigurasi
        # 4. Menentukan seluruh struktur nama dataset
        # 5: Menulis File Kofigurasi dan Menyiapkan Dataset Kosong

        # Kondisi 1: Ambil input dari user/tool ArcGIS
        folder_path = parameters[0].valueAsText 
        fl_path = parameters[1].valueAsText

        appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

        # Kondisi 3: Bersihkan dan buat ulang file konfigurasi
        conf_path = os.path.join(folder_path, "project_config.json")
        if arcpy.Exists(conf_path):
            arcpy.management.Delete(conf_path)

        # Kondisi 4: Menentukan seluruh struktur nama dataset
        gdbname = "NilaiBidangTanah.gdb"
        dataset = "nbt_ds"
        dataset_fasilitas = "fasilitas"
        dataset_resiko = "resiko"

        gdbtemplate = "ds_znt_template"
        utils_folder = os.path.join(appdata, 'nbtutils')
        gdbtemplate_path = os.path.join(utils_folder, "template.gdb", gdbtemplate)

        tbl = "template_var"
        tbltemplate_path = os.path.join(utils_folder, "template.gdb", tbl)

        temporary = "temporary.gdb"
        temporary_path = os.path.join(utils_folder, temporary)
        
        gdb_path = os.path.join(folder_path, gdbname)
        dataset_path = os.path.join(gdb_path, dataset)
        dataset_fasilitas_path = os.path.join(gdb_path, dataset_fasilitas)
        dataset_resiko_path = os.path.join(gdb_path, dataset_resiko)

        sisi_jalan_path = os.path.join(dataset_path, constant.LAYER_SISI_JALAN)
        jaringan_jalan_path = os.path.join(dataset_path, constant.LAYER_JARINGAN_JALAN)
        mid_point_jaringanjalan_path = os.path.join(dataset_path, constant.LAYER_TITIK_TENGAH_JARINGAN_JALAN )


        nd_path = os.path.join(gdb_path, gdbtemplate, constant.TEMPLATE_LAYER_NETWORK_DATASET_JARINGAN_JALAN )
        jaringan_jalan_nd_path = os.path.join(gdb_path, gdbtemplate, constant.TEMPLATE_LAYER_FEATURE_CLASS_JARINGAN_JALAN)

        persil_path = os.path.join(dataset_path, constant.LAYER_PERSIL)
        persil_line_path = os.path.join(dataset_path, constant.LAYER_PERSIL_LINE)
        persil_split_path = os.path.join(dataset_path, constant.LAYER_BELAHAN_PERSIL)
        persil_centroid_path = os.path.join(dataset_path, constant.LAYER_CENTROID_PERSIL)
        persil_split_midpoint_path = os.path.join(dataset_path, constant.LAYER_TITIK_TENGAH_BELAHAN_PERSIL)
        
        json_config = {
            'project_config' : {
                'ws_path' : folder_path,
                'conf_path' : conf_path,
                'gdb_path' : gdb_path,
                'dataset_path' : dataset_path,
                'daftar_variabel_path' : os.path.join(folder_path, constant.KONFIG_DAFTAR_VARIABEL)
            },
            'jaringan_jalan_config' :{
                'path' : { 
                    constant.LAYER_SISI_JALAN  : sisi_jalan_path,
                    constant.LAYER_JARINGAN_JALAN: jaringan_jalan_path,
                    constant.LAYER_TITIK_TENGAH_JARINGAN_JALAN: mid_point_jaringanjalan_path,
                    constant.TEMPLATE_LAYER_NETWORK_DATASET_JARINGAN_JALAN: nd_path,
                    constant.TEMPLATE_LAYER_FEATURE_CLASS_JARINGAN_JALAN: jaringan_jalan_nd_path
                    },
                'skoring' : {
                    'kelas_jalan' :  {
                        'Lokal Setapak' : 1,
                        'Lokal Sekunder' : 2,
                        'Lokal Primer' : 3,
                        'Kolektor Sekunder' : 4,
                        'Kolektor Primer' : 5,
                        'Arteri Sekunder' : 6,
                        'Arteri Primer' : 7
                        },
                }
            
            }, 
            'persil_config' : {
                'path':{
                    constant.LAYER_PERSIL: persil_path,
                    constant.LAYER_PERSIL_LINE: persil_line_path,
                    constant.LAYER_BELAHAN_PERSIL: persil_split_path,
                    constant.LAYER_CENTROID_PERSIL: persil_centroid_path,
                    constant.LAYER_TITIK_TENGAH_BELAHAN_PERSIL: persil_split_midpoint_path
                },
                'skoring' : {
                    'zonasi' : {
                        'Pertanian' : 1,
                        'Industri' : 2,
                        'Perkampungan' : 3,
                        'Perumahan Sederhana' : 4,
                        'Perumahan Menengah' : 5,
                        'Perumahan Mewah' : 6,
                        'Komersil' : 7
                    
                    },
                    'bentuk_persil' : {
                        'Segi Banyak Tidak Beraturan' : 1,
                        'Segitiga' : 2,
                        'Segi Empat Tidak Beraturan' : 3,
                        'Segi Empat Beraturan' : 4
                    },
                    'letak' : {
                        'Lain-lain' : 1,
                        'Normal' : 2,
                        'Tusuk sate' : 3,
                        'Hook' : 4
                    }
                }

                },
            'fasilitas_config' : {
                'dataset_path' : dataset_fasilitas_path},
            
            'resiko_config' : {
                'dataset_path' : dataset_resiko_path
            }
            
        }
        # Kondisi 5: Menulis File Kofigurasi dan Menyiapkan Dataset Kosong
        conf_file = open(conf_path, "w")
        conf_file.write(json.dumps(json_config, indent=4))
        conf_file.close()

        if arcpy.Exists(gdb_path):
            arcpy.management.Delete(gdb_path)
        
        arcpy.management.CreateFileGDB(folder_path, gdbname)

        arcpy.management.CreateFeatureDataset(gdb_path, dataset, fl_path)
        arcpy.management.CreateFeatureDataset(gdb_path, dataset_fasilitas, fl_path)
        arcpy.management.CreateFeatureDataset(gdb_path, dataset_resiko, fl_path)

        arcpy.conversion.FeatureClassToFeatureClass(fl_path, dataset_path, constant.LAYER_PERSIL)

        arcpy.AddMessage("== Sesuaikan proyeksi pada network dataset ==")

        sr = arcpy.Describe(fl_path).spatialReference
        arcpy.AddMessage(sr.name)
        inproject = gdbtemplate_path
        outproject = os.path.join(gdb_path, gdbtemplate)
        arcpy.management.Project(inproject, outproject, sr)

        arcpy.AddMessage("== Mempersiapkan field-field pada persil ==")
        field_names = [field.name for field in arcpy.ListFields(persil_path)]

        deleted_field = ['NEAR_DIST', 'NEAR_FID', 'NEAR_X', 'NEAR_Y']
        for field in deleted_field:
            arcpy.management.DeleteField(persil_path, field)


        if 'IdBidang' not in field_names:
            arcpy.management.AddField(persil_path, 'IdBidang', "LONG")
        arcpy.management.CalculateField(persil_path, 'IdBidang', "!OBJECTID!", "PYTHON")
        if 'ls_tnh' not in field_names:
            arcpy.management.AddField(persil_path, 'ls_tnh', "DOUBLE")

        if arcpy.Exists("tempo"):
            arcpy.management.Delete("tempo")
        arcpy.management.MakeFeatureLayer(persil_path, "tempo")

        arcpy.management.AddGeometryAttributes("tempo", "AREA", "", "SQUARE_METERS")

        arcpy.management.CalculateField(persil_path, 'ls_tnh', "!POLY_AREA!", "PYTHON")
        arcpy.management.DeleteField(persil_path, 'POLY_AREA')

        if 'lb_dpn' not in field_names:
            arcpy.management.AddField(persil_path, 'lb_dpn', "DOUBLE")
        if 'bentuk' not in field_names:
            arcpy.management.AddField(persil_path, 'bentuk', "TEXT")
        if 's_bentuk' not in field_names:
            arcpy.management.AddField(persil_path, 's_bentuk', "DOUBLE")
        if 'zonasi' not in field_names:
            arcpy.management.AddField(persil_path, 'zonasi', "TEXT")
        if 's_zonasi' not in field_names:
            arcpy.management.AddField(persil_path, 's_zonasi', "DOUBLE")
        if 'letak' not in field_names:
            arcpy.management.AddField(persil_path, 'letak', "TEXT")
        if 's_letak' not in field_names:
            arcpy.management.AddField(persil_path, 's_letak', "DOUBLE")
        if 'elevasi' not in field_names:
            arcpy.management.AddField(persil_path, 'elevasi', "TEXT")
        if 's_elevasi' not in field_names:
            arcpy.management.AddField(persil_path, 's_elevasi', "DOUBLE")
        arcpy.management.CalculateField(persil_path, 'elevasi', "'Sama'", "PYTHON")
        arcpy.management.CalculateField(persil_path, 's_elevasi', "2", "PYTHON")
        if 'min_lb_jln' not in field_names:
            arcpy.management.AddField(persil_path, 'min_lb_jln', "DOUBLE")

        arcpy.management.PolygonToLine(persil_path, persil_line_path, "IGNORE_NEIGHBORS")
        arcpy.management.SplitLine(persil_line_path, persil_split_path)

        field_names = [field.name for field in arcpy.ListFields(persil_split_path)]
        if 'LebarSisi' not in field_names:
            arcpy.management.AddField(persil_split_path, 'LebarSisi', "DOUBLE")


        if arcpy.Exists("tempo"):
            arcpy.management.Delete("tempo")
        arcpy.management.MakeFeatureLayer(persil_split_path, "tempo")

        arcpy.management.AddGeometryAttributes("tempo", "LENGTH", "METERS", "")
        arcpy.management.CalculateField(persil_split_path, 'LebarSisi', "!LENGTH!", "PYTHON")

        if 'XStart' not in field_names:
            arcpy.management.AddField(persil_split_path, 'XStart', "DOUBLE")
        if 'XEnd' not in field_names:
            arcpy.management.AddField(persil_split_path, 'XEnd', "DOUBLE")
        if 'YStart' not in field_names:
            arcpy.management.AddField(persil_split_path, 'YStart', "DOUBLE")
        if 'YEnd' not in field_names:
            arcpy.management.AddField(persil_split_path, 'YEnd', "DOUBLE")
        if 'Azimuth' not in field_names:
            arcpy.management.AddField(persil_split_path, 'Azimuth', "DOUBLE")
        if 'ATrans' not in field_names:
            arcpy.management.AddField(persil_split_path, 'ATrans', "DOUBLE")

        arcpy.management.FeatureToPoint(persil_path, persil_centroid_path, "INSIDE")
        arcpy.management.FeatureToPoint(persil_split_path, persil_split_midpoint_path, "INSIDE")

        field_names = [field.name for field in arcpy.ListFields(persil_split_midpoint_path)]
        if 'X' not in field_names:
            arcpy.management.AddField(persil_split_midpoint_path, 'X', "DOUBLE")

        exp = "!Shape.firstpoint.x!"
        code_block = """
        def get(b):
            return b.split(' ')[0]"""
        arcpy.management.CalculateField(persil_split_midpoint_path, "X", exp, "PYTHON")

        if 'Y' not in field_names:
            arcpy.management.AddField(persil_split_midpoint_path, 'Y', "DOUBLE")

        exp = "!Shape.firstpoint.y!"
        code_block = """
        def get(b):
            return b.split(' ')[1]"""
        arcpy.management.CalculateField(persil_split_midpoint_path, "Y", exp, "PYTHON")

        desc = arcpy.Describe(persil_split_path)
        shapename = desc.ShapeFieldName
        cur = arcpy.UpdateCursor(persil_split_path)
        try:
            for row in cur:
                start_fitur = row.getValue(shapename)
                row.XStart = start_fitur.firstPoint.X
                row.XEnd = start_fitur.lastPoint.X
                row.YStart = start_fitur.firstPoint.Y
                row.YEnd = start_fitur.lastPoint.Y
                if (row.YEnd - row.YStart) == 0:
                    if (row.XEnd - row.YStart) >= 0:
                        row.Azimuth = 90
                    else:
                        row.Azimuth = -90
                else:
                    row.Azimuth = math.atan((row.XEnd - row.XStart) / (row.YEnd - row.YStart)) * (180 / math.pi)
                if row.Azimuth < -45:
                    row.ATrans = row.Azimuth + 180
                elif row.Azimuth >= -45 and row.Azimuth <= 45:
                    row.ATrans = row.Azimuth + 90
                else:
                    row.ATrans = row.Azimuth
                cur.updateRow(row)
            del cur
        except:
            del cur

        arcpy.MakeFeatureLayer_management(persil_path, "Persil")
        arcpy.SetParameterAsText(2, "Persil")
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        folder_connections = aprx.folderConnections

        # Path folder yang ingin ditambahkan
        new_folder = folder_path

        # Cek apakah folder sudah ada
        if not any(fc['connectionString'] == new_folder for fc in folder_connections):            
            # Tambahkan folder baru ke list
            folder_connections.append({
                        'connectionString': new_folder,
                        'isHomeFolder': False
                    })

                    # Update folder connections
            aprx.updateFolderConnections(folder_connections, validate=True)
        else:
            arcpy.AddMessage("Workspace sudah terhubung di ArcGIS Pro")
        return
    
class Masukkan_Data_NBT_Sebelumnya(object):

    def __init__(self):
        self.label = "Masukkan Data NBT Sebelumnya"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):

        nbt_awal = arcpy.Parameter(
            displayName="Pilih Data NBT",
            name="old_nbt_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )

        daftar_variabel = arcpy.Parameter(
            displayName='Mapping Variabel Prediksi',
            name='define_variable',
            datatype='GPValueTable',
            parameterType='Required',
            direction='Input'
        )

        daftar_variabel.columns = [
            ['GPString', 'Nama Variabel'],
            ['Field', 'Field Dataset']
        ]

        daftar_variabel.parameterDependencies = [
            nbt_awal.name
        ]

        daftar_variabel.filters[1].list = []

        output_lama = arcpy.Parameter(
            displayName="Output Peta Lama",
            name="output_lama",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        output_baru = arcpy.Parameter(
            displayName="Output Peta Baru",
            name="output_baru",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        output_indikator = arcpy.Parameter(
            displayName="Output Indikator",
            name="output_indikator",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [
            nbt_awal,
            daftar_variabel,
            output_lama,
            output_baru,
            output_indikator
        ]

    def isLicensed(self):
        return True

    def cari_field(self, field_names, kandidat):

        for nama in kandidat:

            if nama.upper() in field_names:
                return nama

        return None

    def delete_if_exists(self, path):

        if arcpy.Exists(path):

            try:
                arcpy.management.Delete(path)

            except Exception as e:

                arcpy.AddWarning(
                    f"Gagal menghapus {path}: {e}"
                )

    def clear_memory_layers(self, layers):

        for lyr in layers:
            self.delete_if_exists(lyr)

    def bersihkan_field(self, fc, allowed_fields):

        protected_fields = {
            "FID"
        }

        for field in arcpy.ListFields(fc):

            field_name = field.name

            is_protected = (
                field.type in ["Geometry", "OID"]
                or "shape" in field_name.lower()
                or field_name in allowed_fields
                or field_name in protected_fields
            )

            if not is_protected:

                try:

                    arcpy.management.DeleteField(
                        fc,
                        field_name
                    )

                except Exception as e:

                    arcpy.AddWarning(str(e))

    def calculate_area_field(
        self,
        fc,
        field_name="ls_asal"
    ):

        field_names = [
            f.name
            for f in arcpy.ListFields(fc)
        ]

        if field_name not in field_names:

            arcpy.management.AddField(
                fc,
                field_name,
                "DOUBLE"
            )

        arcpy.management.CalculateField(
            fc,
            field_name,
            "!shape.area!",
            "PYTHON3"
        )

    def extract_changed_features(
        self,
        source_fc,
        compare_fc,
        layer_name,
        output_fc
    ):

        self.delete_if_exists(layer_name)
        self.delete_if_exists(output_fc)

        arcpy.management.MakeFeatureLayer(
            source_fc,
            layer_name
        )

        arcpy.management.SelectLayerByLocation(
            layer_name,
            "CONTAINS",
            compare_fc,
            selection_type="NEW_SELECTION",
            invert_spatial_relationship="INVERT"
        )

        arcpy.management.CopyFeatures(
            layer_name,
            output_fc
        )

    def set_default_value(
        self,
        fc,
        field_name,
        value,
        field_type="TEXT"
    ):

        field_names = [
            f.name
            for f in arcpy.ListFields(fc)
        ]

        if field_name not in field_names:

            arcpy.management.AddField(
                fc,
                field_name,
                field_type
            )

        arcpy.management.CalculateField(
            fc,
            field_name,
            f'"{value}"',
            "PYTHON3"
        )

    def save_layer(
        self,
        source_fc,
        dataset_path,
        output_name
    ):

        output_path = os.path.join(
            dataset_path,
            output_name
        )

        self.delete_if_exists(output_path)

        arcpy.management.CopyFeatures(
            source_fc,
            output_path
        )

        return arcpy.management.MakeFeatureLayer(
            output_path,
            output_name
        )[0]

    def validate_variabel_table(
        self,
        daftar_variabel,
        messages
    ):

        nama_variabel = set()
        nama_akronim = set()

        hasil_validasi = []

        for row in daftar_variabel:

            if not row or len(row) < 2:
                continue

            variabel = str(row[0]).strip()
            akronim = str(row[1]).strip()

            if not variabel or not akronim:

                messages.addErrorMessage(
                    "== Variabel dan akronim tidak boleh kosong =="
                )

                raise arcpy.ExecuteError

            if variabel.lower() in nama_variabel:

                messages.addErrorMessage(
                    f"== Variabel '{variabel}' duplikat =="
                )

                raise arcpy.ExecuteError

            if akronim.lower() in nama_akronim:

                messages.addErrorMessage(
                    f"== Field dataset '{akronim}' duplikat =="
                )

                raise arcpy.ExecuteError

            nama_variabel.add(
                variabel.lower()
            )

            nama_akronim.add(
                akronim.lower()
            )

            hasil_validasi.append([
                variabel,
                akronim
            ])

        return hasil_validasi

    def updateParameters(self, parameters):

        nbt_layer = parameters[0].valueAsText
        daftar_variable = parameters[1]

        if nbt_layer:

            if daftar_variable.value is None:

                field_names = [
                    f.name.upper()
                    for f in arcpy.ListFields(nbt_layer)
                ]

                default_variabel = [
                    ['Tipe Hak', self.cari_field(field_names, ['TIPEHAK', 'STATUS_PER'])],
                    ["Lebar Depan", self.cari_field(field_names, ['LBRDPN', 'LB_DPN'])],
                    ["Luas Tanah", self.cari_field(field_names, ['LUASM2', 'LS_TNH'])],
                    ["Zonasi", self.cari_field(field_names, ['ZONASI'])],
                    ["Skoring Zonasi", self.cari_field(field_names, ['S_ZONASI'])],
                    ["Letak", self.cari_field(field_names, ['LETAK'])],
                    ["Skoring Letak", self.cari_field(field_names, ['S_LETAK'])],
                    ["Elevasi", self.cari_field(field_names, ['ELVASI'])],
                    ["Skoring Elevasi", self.cari_field(field_names, ['S_ELVASI'])],
                    ["Lebar Jalan", self.cari_field(field_names, ['LBRJLN', 'LB_JLN'])],
                    ["Kelas Jalan", self.cari_field(field_names, ['KLSJLN', 'KLS_JLN'])],
                    ["Skoring Kelas Jalan", self.cari_field(field_names, ['S_KLS_JLN', 'S_KLS_JLN'])],
                    ["Jarak Arteri Primer", self.cari_field(field_names, ['JKATRP', 'JK_ATRP'])],
                    ["Jarak Arteri Sekunder", self.cari_field(field_names, ['JKATRS', 'JK_ATRS'])],
                    ["Jarak Kolektor Primer", self.cari_field(field_names, ['JKKOLP', 'JK_KOLP'])],
                    ["Jarak Kolektor Sekunder", self.cari_field(field_names, ['JKKOLS', 'JK_KOLS'])],
                    ["Jarak CBD", self.cari_field(field_names, ['JKCBD', 'JK_CBD'])],
                    ["Jarak Fasilitas Kesehatan", self.cari_field(field_names, ['JKKES', 'JK_KES'])],
                    ["Jarak Fasilitas Pendidikan", self.cari_field(field_names, ['JKPDDKN', 'JK_EDU'])],
                    ["Jarak Fasilitas Transportasi", self.cari_field(field_names, ['JKTRANSP', 'JK_TRAN'])],
                    ["Jarak Fasilitas Pemerintahan", self.cari_field(field_names, ['JKPMRNTH', 'JK_PEM'])],
                    ["Banjir", self.cari_field(field_names, ['BANJIR'])],
                    ["Longsor", self.cari_field(field_names, ['LONGSOR'])],
                    ["Nilai Bidang Tanah", self.cari_field(field_names, ['NILAIBD'])],
                    ['NIB', self.cari_field(field_names, ['NIB'])],
                    ['IdBidang', self.cari_field(field_names, ['IDBIDANG'])]
                ]

                daftar_variable.value = default_variabel

            spatial_ref = arcpy.Describe(
                nbt_layer
            ).spatialReference

            if 'DGN_1995_Indonesia_TM-3_Zone' not in spatial_ref.name:

                nbt_layer.setErrorMessage(
                    "Koordinat Persil harus DGN_1995_Indonesia_TM-3"
                )

                return

        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):

        messages.addMessage(
            "== Proses dimulai =="
        )

        daftar_variabel = parameters[1].value

        if not daftar_variabel:

            messages.addErrorMessage(
                "== Daftar variabel tidak boleh kosong =="
            )

            raise arcpy.ExecuteError

        hasil_validasi = self.validate_variabel_table(
            daftar_variabel,
            messages
        )

        configs = persil.get_config_values()

        dataset_path = (
            configs["project_config"]["dataset_path"]
        )

        persil_path = (
            configs["persil_config"]["path"]["Persil"]
        )

        konfigurasi_variabel_path = (
            configs["project_config"]["daftar_variabel_path"]
        )

        folder_config = os.path.dirname(
            konfigurasi_variabel_path
        )

        if not os.path.exists(folder_config):

            os.makedirs(folder_config)

        json_config = {
            "daftar_variabel": hasil_validasi
        }

        with open(
            konfigurasi_variabel_path,
            "w"
        ) as conf_file:

            json.dump(
                json_config,
                conf_file,
                indent=4
            )

        messages.addMessage(
            "== Konfigurasi variabel berhasil disimpan =="
        )

        fields_dont_delete = []

        for row in hasil_validasi:

            akronim = row[1]

            fields_dont_delete.append(
                akronim
            )

            fields_dont_delete.append(
                "s_" + akronim
            )

        dest_lama_path = r"in_memory\PersilPetaLama"
        dest_baru_path = r"in_memory\PersilPetaBaru"

        temp_lama_path = r"in_memory\Peta_Temp_Lama"
        temp_baru_path = r"in_memory\Peta_Temp_Baru"

        peta_indikator_temp = (
            r"in_memory\Indikator_Perubahan"
        )

        memory_layers = [
            dest_lama_path,
            dest_baru_path,
            temp_lama_path,
            temp_baru_path,
            peta_indikator_temp
        ]

        try:

            self.clear_memory_layers(
                memory_layers
            )

            peta_lama_input = (
                parameters[0].valueAsText
            )

            arcpy.management.CopyFeatures(
                peta_lama_input,
                dest_lama_path
            )

            arcpy.management.CopyFeatures(
                persil_path,
                dest_baru_path
            )

            for fc in [
                dest_lama_path,
                dest_baru_path
            ]:

                self.bersihkan_field(
                    fc,
                    fields_dont_delete
                )

                self.calculate_area_field(fc)

            self.extract_changed_features(
                dest_lama_path,
                dest_baru_path,
                "PetaLamaLayer_Temp",
                temp_lama_path
            )

            self.extract_changed_features(
                dest_baru_path,
                dest_lama_path,
                "PetaBaruLayer_Temp",
                temp_baru_path
            )

            arcpy.management.Merge(
                [
                    temp_baru_path,
                    temp_lama_path
                ],
                peta_indikator_temp
            )

            self.set_default_value(
                peta_indikator_temp,
                "indikator_perubahan",
                "Indikator Periksa"
            )

            lyr_indikator = self.save_layer(
                peta_indikator_temp,
                dataset_path,
                "Indikator_Perubahan_Persil"
            )

            lyr_lama = self.save_layer(
                dest_lama_path,
                dataset_path,
                "Persil_Lama"
            )

            lyr_baru = self.save_layer(
                dest_baru_path,
                dataset_path,
                "Persil_Baru"
            )

            parameters[2].value = lyr_lama
            parameters[3].value = lyr_baru
            parameters[4].value = lyr_indikator

            messages.addMessage(
                "== Proses selesai =="
            )

        finally:

            self.clear_memory_layers(
                memory_layers
            )

        return

class Tes_Buat_Workspace_Pembaruan_NBT(object):

    def __init__(self):
        self.label = "Buat Workspace NBT"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):

        workspace_folder = arcpy.Parameter(
            displayName='Folder Penyimpanan',
            name='folder_path',
            datatype='DEFolder',
            parameterType='Required',
            direction='Input'
        )

        koordinat_system = arcpy.Parameter(
            displayName='Koordinat / Spatial Reference',
            name='spatial_reference',
            datatype='GPSpatialReference',
            parameterType='Required',
            direction='Input'
        )

        output_fl = arcpy.Parameter(
            name='fl_output',
            datatype='GPFeatureLayer',
            parameterType='Derived',
            direction='Output'
        )

        return [workspace_folder, koordinat_system, output_fl]

    def execute(self, parameters, messages):

        folder_path = parameters[0].valueAsText
        spatial_reference = parameters[1].value

        appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

        conf_path = os.path.join(folder_path, "project_config.json")

        if arcpy.Exists(conf_path):
            arcpy.management.Delete(conf_path)

        gdbname = "NilaiBidangTanah.gdb"

        dataset = "nbt_ds"
        dataset_fasilitas = "fasilitas"
        dataset_resiko = "resiko"

        gdbtemplate = "ds_znt_template"

        utils_folder = os.path.join(appdata, 'nbtutils')

        gdbtemplate_path = os.path.join(
            utils_folder,
            "template.gdb",
            gdbtemplate
        )

        gdb_path = os.path.join(folder_path, gdbname)

        dataset_path = os.path.join(gdb_path, dataset)
        dataset_fasilitas_path = os.path.join(gdb_path, dataset_fasilitas)
        dataset_resiko_path = os.path.join(gdb_path, dataset_resiko)

        sisi_jalan_path = os.path.join(dataset_path, constant.LAYER_SISI_JALAN)

        jaringan_jalan_path = os.path.join(
            dataset_path,
            constant.LAYER_JARINGAN_JALAN
        )

        midpoint_jalan_path = os.path.join(
            dataset_path,
            constant.LAYER_TITIK_TENGAH_JARINGAN_JALAN
        )

        nd_path = os.path.join(
            gdb_path,
            gdbtemplate,
            constant.TEMPLATE_LAYER_NETWORK_DATASET_JARINGAN_JALAN
        )

        jaringan_jalan_nd_path = os.path.join(
            gdb_path,
            gdbtemplate,
            constant.TEMPLATE_LAYER_FEATURE_CLASS_JARINGAN_JALAN
        )

        persil_path = os.path.join(dataset_path, constant.LAYER_PERSIL)

        persil_line_path = os.path.join(
            dataset_path,
            constant.LAYER_PERSIL_LINE
        )

        persil_split_path = os.path.join(
            dataset_path,
            constant.LAYER_BELAHAN_PERSIL
        )

        persil_centroid_path = os.path.join(
            dataset_path,
            constant.LAYER_CENTROID_PERSIL
        )

        persil_split_midpoint_path = os.path.join(
            dataset_path,
            constant.LAYER_TITIK_TENGAH_BELAHAN_PERSIL
        )

        json_config = {
            'project_config': {
                'ws_path': folder_path,
                'conf_path': conf_path,
                'gdb_path': gdb_path,
                'dataset_path': dataset_path,
                'daftar_variabel_path': os.path.join(
                    folder_path,
                    constant.KONFIG_DAFTAR_VARIABEL
                )
            },

            'jaringan_jalan_config': {
                'path': {
                    constant.LAYER_SISI_JALAN: sisi_jalan_path,
                    constant.LAYER_JARINGAN_JALAN: jaringan_jalan_path,
                    constant.LAYER_TITIK_TENGAH_JARINGAN_JALAN: midpoint_jalan_path,
                    constant.TEMPLATE_LAYER_NETWORK_DATASET_JARINGAN_JALAN: nd_path,
                    constant.TEMPLATE_LAYER_FEATURE_CLASS_JARINGAN_JALAN: jaringan_jalan_nd_path
                }
            },

            'persil_config': {
                'path': {
                    constant.LAYER_PERSIL: persil_path,
                    constant.LAYER_PERSIL_LINE: persil_line_path,
                    constant.LAYER_BELAHAN_PERSIL: persil_split_path,
                    constant.LAYER_CENTROID_PERSIL: persil_centroid_path,
                    constant.LAYER_TITIK_TENGAH_BELAHAN_PERSIL: persil_split_midpoint_path
                }
            },

            'fasilitas_config': {
                'dataset_path': dataset_fasilitas_path
            },

            'resiko_config': {
                'dataset_path': dataset_resiko_path
            }
        }

        conf_file = open(conf_path, "w")
        conf_file.write(json.dumps(json_config, indent=4))
        conf_file.close()

        if arcpy.Exists(gdb_path):
            arcpy.management.Delete(gdb_path)

        arcpy.management.CreateFileGDB(folder_path, gdbname)

        arcpy.management.CreateFeatureDataset(
            gdb_path,
            dataset,
            spatial_reference
        )

        arcpy.management.CreateFeatureDataset(
            gdb_path,
            dataset_fasilitas,
            spatial_reference
        )

        arcpy.management.CreateFeatureDataset(
            gdb_path,
            dataset_resiko,
            spatial_reference
        )

        fl = arcpy.management.CreateFeatureclass(
            dataset_path,
            constant.LAYER_PERSIL,
            "POLYGON",
            spatial_reference=spatial_reference
        )[0]

        arcpy.AddMessage("== Project template ==")

        outproject = os.path.join(gdb_path, gdbtemplate)

        arcpy.management.Project(
            gdbtemplate_path,
            outproject,
            spatial_reference
        )

        aprx = arcpy.mp.ArcGISProject("CURRENT")

        folder_connections = aprx.folderConnections

        if not any(
            fc['connectionString'] == folder_path
            for fc in folder_connections
        ):

            folder_connections.append({
                'connectionString': folder_path,
                'isHomeFolder': False
            })

            aprx.updateFolderConnections(
                folder_connections,
                validate=True
            )
        arcpy.SetParameter(2, fl)
        arcpy.AddMessage("Workspace berhasil dibuat")

class Tes_Masukkan_Data_NBT_Sebelumnya(object):

    def __init__(self):
        self.label = "Masukkan Data NBT Sebelumnya"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):

        nbt_awal = arcpy.Parameter(
            displayName="Pilih Data NBT",
            name="old_nbt_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )

        daftar_variabel = arcpy.Parameter(
            displayName='Sesuaikan Field',
            name='define_variable',
            datatype='GPValueTable',
            parameterType='Required',
            direction='Input'
        )

        daftar_variabel.columns = [
            ['GPString', 'Nama Variabel'],
            ['Field', 'Field Dataset']
        ]

        daftar_variabel.parameterDependencies = [
            nbt_awal.name
        ]

        daftar_variabel.filters[1].list = []

        output_lama = arcpy.Parameter(
            displayName="Output Peta Lama",
            name="output_lama",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        output_baru = arcpy.Parameter(
            displayName="Output Peta Baru",
            name="output_baru",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        output_indikator = arcpy.Parameter(
            displayName="Output Indikator",
            name="output_indikator",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [
            nbt_awal,
            daftar_variabel,
            output_lama,
            output_baru,
            output_indikator
        ]

    def isLicensed(self):
        return True

    def cari_field(self, field_names, kandidat):

        for nama in kandidat:

            if nama.upper() in field_names:
                return nama

        return None

    def delete_if_exists(self, path):

        if arcpy.Exists(path):

            try:
                arcpy.management.Delete(path)

            except Exception as e:

                arcpy.AddWarning(
                    f"Gagal menghapus {path}: {e}"
                )

    def clear_memory_layers(self, layers):

        for lyr in layers:
            self.delete_if_exists(lyr)

    def bersihkan_field(self, fc, allowed_fields):

        protected_fields = {
            "FID"
        }

        for field in arcpy.ListFields(fc):

            field_name = field.name

            is_protected = (
                field.type in ["Geometry", "OID"]
                or "shape" in field_name.lower()
                or field_name in allowed_fields
                or field_name in protected_fields
            )

            if not is_protected:

                try:

                    arcpy.management.DeleteField(
                        fc,
                        field_name
                    )

                except Exception as e:

                    arcpy.AddWarning(str(e))

    def calculate_area_field(
        self,
        fc,
        field_name="ls_asal"
    ):

        field_names = [
            f.name
            for f in arcpy.ListFields(fc)
        ]

        if field_name not in field_names:

            arcpy.management.AddField(
                fc,
                field_name,
                "DOUBLE"
            )

        arcpy.management.CalculateField(
            fc,
            field_name,
            "!shape.area!",
            "PYTHON3"
        )

    def extract_changed_features(
        self,
        source_fc,
        compare_fc,
        layer_name,
        output_fc
    ):

        self.delete_if_exists(layer_name)
        self.delete_if_exists(output_fc)

        arcpy.management.MakeFeatureLayer(
            source_fc,
            layer_name
        )

        arcpy.management.SelectLayerByLocation(
            layer_name,
            "CONTAINS",
            compare_fc,
            selection_type="NEW_SELECTION",
            invert_spatial_relationship="INVERT"
        )

        arcpy.management.CopyFeatures(
            layer_name,
            output_fc
        )

    def set_default_value(
        self,
        fc,
        field_name,
        value,
        field_type="TEXT"
    ):

        field_names = [
            f.name
            for f in arcpy.ListFields(fc)
        ]

        if field_name not in field_names:

            arcpy.management.AddField(
                fc,
                field_name,
                field_type
            )

        arcpy.management.CalculateField(
            fc,
            field_name,
            f'"{value}"',
            "PYTHON3"
        )

    def save_layer(
        self,
        source_fc,
        dataset_path,
        output_name
    ):

        output_path = os.path.join(
            dataset_path,
            output_name
        )

        self.delete_if_exists(output_path)

        arcpy.management.CopyFeatures(
            source_fc,
            output_path
        )

        return arcpy.management.MakeFeatureLayer(
            output_path,
            output_name
        )[0]

    def validate_variabel_table(
        self,
        daftar_variabel,
        messages
    ):

        nama_variabel = set()
        nama_akronim = set()

        hasil_validasi = []

        for row in daftar_variabel:

            if not row or len(row) < 2:
                continue

            variabel = str(row[0]).strip()
            akronim = str(row[1]).strip()

            if not variabel or not akronim:

                messages.addErrorMessage(
                    "== Variabel dan akronim tidak boleh kosong =="
                )

                raise arcpy.ExecuteError

            if variabel.lower() in nama_variabel:

                messages.addErrorMessage(
                    f"== Variabel '{variabel}' duplikat =="
                )

                raise arcpy.ExecuteError

            if akronim.lower() in nama_akronim:

                messages.addErrorMessage(
                    f"== Field dataset '{akronim}' duplikat =="
                )

                raise arcpy.ExecuteError

            nama_variabel.add(
                variabel.lower()
            )

            nama_akronim.add(
                akronim.lower()
            )

            hasil_validasi.append([
                variabel,
                akronim
            ])

        return hasil_validasi

    def updateParameters(self, parameters):

        nbt_layer = parameters[0].valueAsText
        daftar_variable = parameters[1]

        if nbt_layer:

            if daftar_variable.value is None:

                field_names = [
                    f.name.upper()
                    for f in arcpy.ListFields(nbt_layer)
                ]

                default_variabel = [
                    ['Tipe Hak', self.cari_field(field_names, ['TIPEHAK', 'STATUS_PER'])],
                    ["Lebar Depan", self.cari_field(field_names, ['LBRDPN', 'LB_DPN'])],
                    ["Luas Tanah", self.cari_field(field_names, ['LUASM2', 'LS_TNH'])],
                    ["Zonasi", self.cari_field(field_names, ['ZONASI'])],
                    ["Skoring Zonasi", self.cari_field(field_names, ['S_ZONASI'])],
                    ["Letak", self.cari_field(field_names, ['LETAK'])],
                    ["Skoring Letak", self.cari_field(field_names, ['S_LETAK'])],
                    ["Elevasi", self.cari_field(field_names, ['ELVASI'])],
                    ["Skoring Elevasi", self.cari_field(field_names, ['S_ELVASI'])],
                    ["Lebar Jalan", self.cari_field(field_names, ['LBRJLN', 'LB_JLN'])],
                    ["Kelas Jalan", self.cari_field(field_names, ['KLSJLN', 'KLS_JLN'])],
                    ["Skoring Kelas Jalan", self.cari_field(field_names, ['S_KLS_JLN', 'S_KLS_JLN'])],
                    ["Jarak Arteri Primer", self.cari_field(field_names, ['JKATRP', 'JK_ATRP'])],
                    ["Jarak Arteri Sekunder", self.cari_field(field_names, ['JKATRS', 'JK_ATRS'])],
                    ["Jarak Kolektor Primer", self.cari_field(field_names, ['JKKOLP', 'JK_KOLP'])],
                    ["Jarak Kolektor Sekunder", self.cari_field(field_names, ['JKKOLS', 'JK_KOLS'])],
                    ["Jarak CBD", self.cari_field(field_names, ['JKCBD', 'JK_CBD'])],
                    ["Jarak Fasilitas Kesehatan", self.cari_field(field_names, ['JKKES', 'JK_KES'])],
                    ["Jarak Fasilitas Pendidikan", self.cari_field(field_names, ['JKPDDKN', 'JK_EDU'])],
                    ["Jarak Fasilitas Transportasi", self.cari_field(field_names, ['JKTRANSP', 'JK_TRAN'])],
                    ["Jarak Fasilitas Pemerintahan", self.cari_field(field_names, ['JKPMRNTH', 'JK_PEM'])],
                    ["Banjir", self.cari_field(field_names, ['BANJIR'])],
                    ["Longsor", self.cari_field(field_names, ['LONGSOR'])],
                    ["Nilai Bidang Tanah", self.cari_field(field_names, ['NILAIBD'])],
                    ['NIB', self.cari_field(field_names, ['NIB'])],
                    ['IdBidang', self.cari_field(field_names, ['IDBIDANG'])]
                ]

                daftar_variable.value = default_variabel

            spatial_ref = arcpy.Describe(
                nbt_layer
            ).spatialReference

            if 'DGN_1995_Indonesia_TM-3_Zone' not in spatial_ref.name:

                nbt_layer.setErrorMessage(
                    "Koordinat Persil harus DGN_1995_Indonesia_TM-3"
                )

                return

        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):

        messages.addMessage(
            "== Proses dimulai =="
        )

        daftar_variabel = parameters[1].value

        if not daftar_variabel:

            messages.addErrorMessage(
                "== Daftar variabel tidak boleh kosong =="
            )

            raise arcpy.ExecuteError

        hasil_validasi = self.validate_variabel_table(
            daftar_variabel,
            messages
        )

        configs = persil.get_config_values()

        dataset_path = (
            configs["project_config"]["dataset_path"]
        )

        persil_path = (
            configs["persil_config"]["path"]["Persil"]
        )

        konfigurasi_variabel_path = (
            configs["project_config"]["daftar_variabel_path"]
        )

        folder_config = os.path.dirname(
            konfigurasi_variabel_path
        )

        if not os.path.exists(folder_config):

            os.makedirs(folder_config)

        json_config = {
            "daftar_variabel": hasil_validasi
        }

        with open(
            konfigurasi_variabel_path,
            "w"
        ) as conf_file:

            json.dump(
                json_config,
                conf_file,
                indent=4
            )

        messages.addMessage(
            "== Konfigurasi variabel berhasil disimpan =="
        )

        fields_dont_delete = []

        for row in hasil_validasi:

            akronim = row[1]

            fields_dont_delete.append(
                akronim
            )

            fields_dont_delete.append(
                "s_" + akronim
            )

        dest_lama_path = r"in_memory\PersilPetaLama"
        dest_baru_path = r"in_memory\PersilPetaBaru"

        temp_lama_path = r"in_memory\Peta_Temp_Lama"
        temp_baru_path = r"in_memory\Peta_Temp_Baru"

        peta_indikator_temp = (
            r"in_memory\Indikator_Perubahan"
        )

        memory_layers = [
            dest_lama_path,
            dest_baru_path,
            temp_lama_path,
            temp_baru_path,
            peta_indikator_temp
        ]

        try:

            self.clear_memory_layers(
                memory_layers
            )

            peta_lama_input = (
                parameters[0].valueAsText
            )

            arcpy.management.CopyFeatures(
                peta_lama_input,
                dest_lama_path
            )

            arcpy.management.CopyFeatures(
                persil_path,
                dest_baru_path
            )

            for fc in [
                dest_lama_path,
                dest_baru_path
            ]:

                self.bersihkan_field(
                    fc,
                    fields_dont_delete
                )

                self.calculate_area_field(fc)

            self.extract_changed_features(
                dest_lama_path,
                dest_baru_path,
                "PetaLamaLayer_Temp",
                temp_lama_path
            )

            self.extract_changed_features(
                dest_baru_path,
                dest_lama_path,
                "PetaBaruLayer_Temp",
                temp_baru_path
            )

            arcpy.management.Merge(
                [
                    temp_baru_path,
                    temp_lama_path
                ],
                peta_indikator_temp
            )

            self.set_default_value(
                peta_indikator_temp,
                "indikator_perubahan",
                "Indikator Periksa"
            )

            lyr_indikator = self.save_layer(
                peta_indikator_temp,
                dataset_path,
                "Indikator_Perubahan_Persil"
            )

            lyr_lama = self.save_layer(
                dest_lama_path,
                dataset_path,
                "Persil_Lama"
            )

            lyr_baru = self.save_layer(
                dest_baru_path,
                dataset_path,
                "Persil_Baru"
            )

            parameters[2].value = lyr_lama
            parameters[3].value = lyr_baru
            parameters[4].value = lyr_indikator

            messages.addMessage(
                "== Proses selesai =="
            )

        finally:

            self.clear_memory_layers(
                memory_layers
            )

        return

class ImportDataNBTSebelumnya(object):

    def __init__(self):
        self.label = "Import Data NBT Sebelumnya"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):

        nbt_awal = arcpy.Parameter(
            displayName="Pilih Data NBT",
            name="old_nbt_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )

        daftar_variabel = arcpy.Parameter(
            displayName='Sesuaikan Field',
            name='define_variable',
            datatype='GPValueTable',
            parameterType='Required',
            direction='Input'
        )

        daftar_variabel.columns = [
            ['GPString', 'Nama Variabel'],
            ['Field', 'Field Dataset']
        ]

        daftar_variabel.parameterDependencies = [
            nbt_awal.name
        ]

        output_lama = arcpy.Parameter(
            displayName="Output Peta Lama",
            name="output_lama",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [
            nbt_awal,
            daftar_variabel,
            output_lama
        ]
    
    def updateParameters(self, parameters):

        nbt_layer = parameters[0].valueAsText
        daftar_variable = parameters[1]
        if nbt_layer:
            if daftar_variable.value is None:
                field_names = [
                    f.name.upper()
                    for f in arcpy.ListFields(nbt_layer)
                ]

                default_variabel = [
                    ['Tipe Hak', self.cari_field(field_names, ['TIPEHAK', 'STATUS_PER'])],
                    ["Lebar Depan", self.cari_field(field_names, ['LBRDPN', 'LB_DPN'])],
                    ["Luas Tanah", self.cari_field(field_names, ['LUASM2', 'LS_TNH'])],
                    ["Zonasi", self.cari_field(field_names, ['ZONASI'])],
                    ["Skoring Zonasi", self.cari_field(field_names, ['S_ZONASI'])],
                    ["Letak", self.cari_field(field_names, ['LETAK'])],
                    ["Skoring Letak", self.cari_field(field_names, ['S_LETAK'])],
                    ["Elevasi", self.cari_field(field_names, ['ELVASI'])],
                    ["Skoring Elevasi", self.cari_field(field_names, ['S_ELVASI'])],
                    ["Lebar Jalan", self.cari_field(field_names, ['LBRJLN', 'LB_JLN'])],
                    ["Kelas Jalan", self.cari_field(field_names, ['KLSJLN', 'KLS_JLN'])],
                    ["Skoring Kelas Jalan", self.cari_field(field_names, ['S_KLS_JLN', 'S_KLS_JLN'])],
                    ["Jarak Arteri Primer", self.cari_field(field_names, ['JKATRP', 'JK_ATRP'])],
                    ["Jarak Arteri Sekunder", self.cari_field(field_names, ['JKATRS', 'JK_ATRS'])],
                    ["Jarak Kolektor Primer", self.cari_field(field_names, ['JKKOLP', 'JK_KOLP'])],
                    ["Jarak Kolektor Sekunder", self.cari_field(field_names, ['JKKOLS', 'JK_KOLS'])],
                    ["Jarak CBD", self.cari_field(field_names, ['JKCBD', 'JK_CBD'])],
                    ["Jarak Fasilitas Kesehatan", self.cari_field(field_names, ['JKKES', 'JK_KES'])],
                    ["Jarak Fasilitas Pendidikan", self.cari_field(field_names, ['JKPDDKN', 'JK_EDU'])],
                    ["Jarak Fasilitas Transportasi", self.cari_field(field_names, ['JKTRANSP', 'JK_TRAN'])],
                    ["Jarak Fasilitas Pemerintahan", self.cari_field(field_names, ['JKPMRNTH', 'JK_PEM'])],
                    ["Banjir", self.cari_field(field_names, ['BANJIR'])],
                    ["Longsor", self.cari_field(field_names, ['LONGSOR'])],
                    ["Nilai Bidang Tanah", self.cari_field(field_names, ['NILAIBD'])],
                    ['NIB', self.cari_field(field_names, ['NIB'])],
                    ['IdBidang', self.cari_field(field_names, ['IDBIDANG'])]
                ]

                daftar_variable.value = default_variabel

            spatial_ref = arcpy.Describe(
                nbt_layer
            ).spatialReference

            if 'DGN_1995_Indonesia_TM-3_Zone' not in spatial_ref.name:

                nbt_layer.setErrorMessage(
                    "Koordinat Persil harus DGN_1995_Indonesia_TM-3"
                )

                return

        return

    def execute(self, parameters, messages):
        peta_lama_input = parameters[0].valueAsText
        daftar_variabel = parameters[1].value
        configs = persil.get_config_values()
        dataset_path = configs["project_config"]["dataset_path"]
        konfigurasi_variabel_path =  configs["project_config"]["daftar_variabel_path"]

        # Convert GPValueTable / ValueObject rows to plain Python lists
        daftar_variabel_python = []
        protected_fields = { "FID"}
        for row in daftar_variabel:
            if not row:
                continue
            try:
                if len(row) >= 2:
                    daftar_variabel_python.append([
                        str(row[0]),
                        str(row[1])
                    ])
                    protected_fields.add(str(row[1]))
                else:
                    daftar_variabel_python.append([str(row)])
            except Exception:
                daftar_variabel_python.append([str(row)])

        json_config = {
            "daftar_variabel": daftar_variabel_python
        }

        with open(
            konfigurasi_variabel_path,
            "w"
        ) as conf_file:
            json.dump(
                json_config,
                conf_file,
                indent=4
            )
        
        dest_lama_path = r"in_memory\PersilPetaLama"
        
        arcpy.management.CopyFeatures(
            peta_lama_input,
            dest_lama_path
        )
        arcpy.AddMessage(daftar_variabel_python)

        for field in arcpy.ListFields(dest_lama_path):
            field_name = field.name
            is_protected = (
                field.type in ["Geometry", "OID"]
                or "shape" in field_name.lower()
                or field_name in protected_fields
            )
            if not is_protected:
                try:
                    arcpy.management.DeleteField(
                        dest_lama_path,
                        field_name
                    )
                except Exception as e:
                    arcpy.AddWarning(str(e))

        self.calculate_area_field(
            dest_lama_path
        )

        persil_layer = arcpy.conversion.FeatureClassToFeatureClass(
            dest_lama_path,
            dataset_path,
            constant.LAYER_PERSIL
        )[0]

        parameters[2].value = persil_layer

        return
    def cari_field(self, field_names, kandidat):

        for nama in kandidat:

            if nama.upper() in field_names:
                return nama

        return None

    def delete_if_exists(self, path):

        if arcpy.Exists(path):

            try:
                arcpy.management.Delete(path)

            except Exception as e:

                arcpy.AddWarning(
                    f"Gagal menghapus {path}: {e}"
                )

    def clear_memory_layers(self, layers):

        for lyr in layers:
            self.delete_if_exists(lyr)

    def calculate_area_field(
        self,
        fc,
        field_name="ls_asal"
    ):

        field_names = [
            f.name
            for f in arcpy.ListFields(fc)
        ]

        if field_name not in field_names:

            arcpy.management.AddField(
                fc,
                field_name,
                "DOUBLE"
            )

        arcpy.management.CalculateField(
            fc,
            field_name,
            "!shape.area!",
            "PYTHON3"
        )

class CekPerubahanPersilNBT(object):

    def __init__(self):
        self.label = "Cek Perubahan Persil"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):

        output_baru = arcpy.Parameter(
            displayName="Output Peta Baru",
            name="output_baru",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        output_indikator = arcpy.Parameter(
            displayName="Output Indikator",
            name="output_indikator",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [
            output_baru,
            output_indikator
        ]

    def execute(self, parameters, messages):

        configs = persil.get_config_values()

        dataset_path = (
            configs["project_config"]["dataset_path"]
        )

        persil_path = (
            configs["persil_config"]["path"]["Persil"]
        )

        persil_lama_path = os.path.join(
            dataset_path,
            "Persil_Lama"
        )

        dest_baru_path = r"in_memory\PersilPetaBaru"

        temp_lama_path = r"in_memory\Peta_Temp_Lama"

        temp_baru_path = r"in_memory\Peta_Temp_Baru"

        indikator_temp = (
            r"in_memory\Indikator_Perubahan"
        )

        arcpy.management.CopyFeatures(
            persil_path,
            dest_baru_path
        )

        self.calculate_area_field(
            dest_baru_path
        )

        self.extract_changed_features(
            persil_lama_path,
            dest_baru_path,
            "PetaLamaLayer_Temp",
            temp_lama_path
        )

        self.extract_changed_features(
            dest_baru_path,
            persil_lama_path,
            "PetaBaruLayer_Temp",
            temp_baru_path
        )

        arcpy.management.Merge(
            [
                temp_baru_path,
                temp_lama_path
            ],
            indikator_temp
        )

        self.set_default_value(
            indikator_temp,
            "indikator_perubahan",
            "Indikator Periksa"
        )

        lyr_indikator = self.save_layer(
            indikator_temp,
            dataset_path,
            "Indikator_Perubahan_Persil"
        )

        lyr_baru = self.save_layer(
            dest_baru_path,
            dataset_path,
            "Persil_Baru"
        )

        parameters[0].value = lyr_baru
        parameters[1].value = lyr_indikator

        return
    
class Tes_Masukkan_Persil_Baru(object):

    def __init__(self):
        self.label = "Import Persil Baru NBT"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):

        feature_layer = arcpy.Parameter(
            displayName='Persil Baru',
            name='feature_layer',
            datatype='GPFeatureLayer',
            parameterType='Required',
            direction='Input'
        )

        output_fl = arcpy.Parameter(
            name='fl_output',
            datatype='GPFeatureLayer',
            parameterType='Derived',
            direction='Output'
        )

        return [feature_layer, output_fl]

    def execute(self, parameters, messages):

        configs = persil.get_config_values()
        folder_path = configs['project_config']['ws_path']
        fl_path = parameters[1].valueAsText

        conf_path = os.path.join(
            folder_path,
            "project_config.json"
        )

        conf_file = open(conf_path, "r")
        config = json.load(conf_file)
        conf_file.close()

        persil_path = config['persil_config']['path'][constant.LAYER_PERSIL]

        persil_line_path = config['persil_config']['path'][constant.LAYER_PERSIL_LINE]

        persil_split_path = config['persil_config']['path'][constant.LAYER_BELAHAN_PERSIL]

        persil_centroid_path = config['persil_config']['path'][constant.LAYER_CENTROID_PERSIL]

        persil_split_midpoint_path = config['persil_config']['path'][constant.LAYER_TITIK_TENGAH_BELAHAN_PERSIL]

        if arcpy.Exists(persil_path):
            arcpy.management.Delete(persil_path)

        arcpy.conversion.FeatureClassToFeatureClass(
            fl_path,
            os.path.dirname(persil_path),
            os.path.basename(persil_path)
        )

        field_names = [f.name for f in arcpy.ListFields(persil_path)]

        required_fields = [
            ('IdBidang', 'LONG'),
            ('ls_tnh', 'DOUBLE'),
            ('lb_dpn', 'DOUBLE'),
            ('bentuk', 'TEXT'),
            ('s_bentuk', 'DOUBLE'),
            ('zonasi', 'TEXT'),
            ('s_zonasi', 'DOUBLE'),
            ('letak', 'TEXT'),
            ('s_letak', 'DOUBLE'),
            ('elevasi', 'TEXT'),
            ('s_elevasi', 'DOUBLE'),
            ('min_lb_jln', 'DOUBLE')
        ]

        for field_name, field_type in required_fields:

            if field_name not in field_names:

                arcpy.management.AddField(
                    persil_path,
                    field_name,
                    field_type
                )

        arcpy.management.CalculateField(
            persil_path,
            'IdBidang',
            '!OBJECTID!',
            'PYTHON'
        )

        arcpy.management.CalculateField(
            persil_path,
            'elevasi',
            "'Sama'",
            'PYTHON'
        )

        arcpy.management.CalculateField(
            persil_path,
            's_elevasi',
            '2',
            'PYTHON'
        )

        arcpy.management.PolygonToLine(
            persil_path,
            persil_line_path,
            "IGNORE_NEIGHBORS"
        )

        arcpy.management.SplitLine(
            persil_line_path,
            persil_split_path
        )

        arcpy.management.FeatureToPoint(
            persil_path,
            persil_centroid_path,
            "INSIDE"
        )

        arcpy.management.FeatureToPoint(
            persil_split_path,
            persil_split_midpoint_path,
            "INSIDE"
        )

        arcpy.management.MakeFeatureLayer(
            persil_path,
            "Persil"
        )

        arcpy.SetParameterAsText(2, "Persil")

        arcpy.AddMessage("Import persil selesai")