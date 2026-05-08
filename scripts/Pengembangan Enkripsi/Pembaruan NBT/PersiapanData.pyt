from datetime import datetime
import json
import sys
import arcpy, os

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
                      Deklarasi_Variabel]

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
        coordinate_system = arcpy.Parameter(
            displayName="Referensi Sistem Koordinat",
            name="coordinate_system",
            datatype="GPCoordinateSystem",
            parameterType="Required",
            direction="Input")
        
        workspace_folder = arcpy.Parameter(
            displayName='Folder Penyimpanan',
            name = 'folder_path',
            datatype='DEFolder',
            parameterType='Required',
            direction='Input'
        )

        provinsi = arcpy.Parameter(
            displayName="Provinsi",
            name="provinsi",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        provinsi.filter.type = "ValueList"
        provinsi.filter.list = NAMA_PROVINSI

        kab_kota = arcpy.Parameter(
            displayName="Kabupaten/Kota",
            name="kab_kota",
            datatype="GPString",
            parameterType="Required",
            direction="Input")

        tahun_penilaian = arcpy.Parameter(
            displayName="Tahun Penilaian",
            name="tahun_penilaian",
            datatype="GPLong",
            parameterType="Required",
            direction="Input"
        )

        tahun_penilaian.value = current_year()

        feature_layer = arcpy.Parameter(
            name="feature_layer",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )
        
        return [coordinate_system, workspace_folder, provinsi, kab_kota, tahun_penilaian, feature_layer]
        

        
    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return   
    
    def updateParameters(self, parameters):
        prov = parameters[2].valueAsText  # parameter Provinsi
        kab = parameters[3]               # parameter Kab/Kota

        if prov:
            kab.filter.type = "ValueList"
            kab.filter.list = KAB_KOTA.get(prov, [])
        else:
            kab.filter.list = []

    
    def execute(self, parameters, messages):
        # Kondisi yang harus dipenuhi
        # 1. Ambil input dari user/tool ArcGIS
        # 2. Mengecek Koordinat harus TM-3
        # 3. Bersihkan dan buat ulang file konfigurasi
        # 4. Menentukan seluruh struktur nama dataset
        # 5: Menulis File Kofigurasi dan Menyiapkan Dataset Kosong

        # Kondisi 1: Ambil input dari user/tool ArcGIS
        coord = parameters[0].valueAsText
        folder_path = parameters[1].valueAsText 
        WADMPR = parameters[2].valueAsText
        WADMKK = parameters[3].valueAsText
        THNNILAI = parameters[4].valueAsText

        # Kondisi 2: Mengecek Koordinat harus TM-3
        if coord is None or 'DGN_1995_Indonesia_TM-3_Zone' not in coord.strip():
            arcpy.AddError( "Proyeksi Sistem Koordinat harus DGN_1995_Indonesia_TM-3 ")
            sys.exit(1)
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
                'provinsi': WADMPR,
                'kota': WADMKK,
                'coordinate': coord,
                'tahun': THNNILAI

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

        arcpy.management.CreateFeatureDataset(gdb_path, dataset, coord)
        arcpy.management.CreateFeatureDataset(gdb_path, dataset_fasilitas, coord)
        arcpy.management.CreateFeatureDataset(gdb_path, dataset_resiko, coord)

        persil_fc = arcpy.management.CreateFeatureclass(
            out_path=dataset_path,
            out_name=constant.LAYER_PERSIL,
            geometry_type="POLYGON",
            spatial_reference=coord
        )

        # field_names = [field.name for field in arcpy.ListFields(persil_path)]
        # if 'NEAR_DIST' in field_names:
        #     arcpy.management.DeleteField(persil_path, 'NEAR_DIST')
        # if 'NEAR_FID' in field_names:
        #     arcpy.management.DeleteField(persil_path, 'NEAR_FID')
        # if 'NEAR_X' in field_names:
        #     arcpy.management.DeleteField(persil_path, 'NEAR_X')
        # if 'NEAR_Y' in field_names:
        #     arcpy.management.DeleteField(persil_path, 'NEAR_Y')

        # if 'IdBidang' not in field_names:
        #     arcpy.management.AddField(persil_path, 'IdBidang', "LONG")
        # arcpy.management.CalculateField(persil_path, 'IdBidang', "!OBJECTID!", "PYTHON")

        # if 'ls_tnh' not in field_names:
        #     arcpy.management.AddField(persil_path, 'ls_tnh', "DOUBLE")
        # arcpy.management.CalculateField(persil_path, 'ls_tnh', "!SHAPE.area!", "PYTHON")

        # if 'lb_dpn' not in field_names:
        #     arcpy.management.AddField(persil_path, 'lb_dpn', "DOUBLE")
        # if 'bentuk' not in field_names:
        #     arcpy.management.AddField(persil_path, 'bentuk', "TEXT")
        # if 's_bentuk' not in field_names:
        #     arcpy.management.AddField(persil_path, 's_bentuk', "DOUBLE")
        # if 'zonasi' not in field_names:
        #     arcpy.management.AddField(persil_path, 'zonasi', "TEXT")
        # if 's_zonasi' not in field_names:
        #     arcpy.management.AddField(persil_path, 's_zonasi', "DOUBLE")
        # if 'letak' not in field_names:
        #     arcpy.management.AddField(persil_path, 'letak', "TEXT")
        # if 's_letak' not in field_names:
        #     arcpy.management.AddField(persil_path, 's_letak', "DOUBLE")
        # if 'elevasi' not in field_names:
        #     arcpy.management.AddField(persil_path, 'elevasi', "TEXT")
        # if 's_elevasi' not in field_names:
        #     arcpy.management.AddField(persil_path, 's_elevasi', "DOUBLE")
        # arcpy.management.CalculateField(persil_path, 'elevasi', "'Sama'", "PYTHON")
        # arcpy.management.CalculateField(persil_path, 's_elevasi', "2", "PYTHON")

        # if 'min_lb_jln' not in field_names:
        #     arcpy.management.AddField(persil_path, 'min_lb_jln', "DOUBLE")

        # arcpy.management.PolygonToLine(persil_path, persil_line_path, "IGNORE_NEIGHBORS")
        # arcpy.management.SplitLine(persil_line_path, persil_split_path)

        # field_names = [field.name for field in arcpy.ListFields(persil_split_path)]
        # if 'LebarSisi' not in field_names:
        #     arcpy.management.AddField(persil_split_path, 'LebarSisi', "DOUBLE")


        aprx = arcpy.mp.ArcGISProject("CURRENT")
        folder_connections = aprx.folderConnections

        arcpy.SetParameter(5, persil_fc[0])
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
    

class Deklarasi_Variabel(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Deklarasi Variabel"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        
        daftar_variabel = arcpy.Parameter(
            displayName='Daftar Variabel Prediksi',
            name='define_variable',
            datatype='GPValueTable',
            parameterType='Required',
            direction='Input')
        daftar_variabel.columns = [['GPString', 'Variabel'], ['GPString', 'Akronim']]
        params = [daftar_variabel]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed.
        Variabel-variabel yang tidak boleh dihapus:
        (Luas Tanah, Lebar Depan, Lebar Jalan, Kelas Jalan, Jarak ke Kelas Jalan, Bentuk Bidang, Letak Bidang, Zonasi)"""
        default_variabel = [
            ["LBRDPN", "LBRDPN"], # Lebar Depan
            ["Bentuk", "bentuk"],
            ["Lebar jalan", "lb_jln"],
            ["Kelas Jalan", "kls_jln"],
            ["Jarak ke Arteri Primer", "jk_atrp"],
            ["Jarak ke Arteri Sekunder", "jk_atrs"],
            ["Jarak ke Kolektor Primer", "jk_kolp"],
            ["Jarak ke Kolektor Sekunder", "jk_kols"],
            ["Letak Tanah", "letak"],
            ["Zonasi", "zonasi"],
            ["Luas Tanah", "ls_tnh"],
            ["Minimal Lebar Jalan", "min_lb_jln"]
        ]
        parameters[0].value = default_variabel
        return


    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        daftar_variabel = parameters[0].valueAsText

        return

class Masukkan_Data_NBT_Sebelumnya(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Masukkan Data NBT Sebelumnya"
        self.description = "Tools untuk memasukkan data NBT sebelumnya ke dalam sistem sebagai dasar perhitungan NBT baru. Pastikan data NBT lama sudah benar dan lengkap sebelum menggunakan tool ini."

    def getParameterInfo(self):
        """Define the tool parameters."""

        # 1. Input layer ZNT Lama
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
        daftar_variabel.parameterDependencies = [nbt_awal.name]
        daftar_variabel.filters[1].list = []
        
        
        return [
            nbt_awal, daftar_variabel
        ]
    def isLicensed(self):
        """Set whether the tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """
        Kondisi yang harus terpebuhi agar parameter field muncul:
        1. T
        """
        def cari_field(field_names, kandidat):
            for nama in kandidat:
                if nama.upper() in field_names:
                    return nama

            return None
        
        nbt_layer = parameters[0].valueAsText
        daftar_variable = parameters[1]
        
        if nbt_layer:
            if daftar_variable.value is None:
                field_names = [f.name.upper() for f in arcpy.ListFields(nbt_layer)]
            
                default_variabel = [
                    ['Tipe Hak', cari_field(field_names, ['TIPEHAK', 'STATUS_PER'])],
                    ["Lebar Depan", cari_field(field_names, ['LBRDPN', 'LB_DPN'])],         
                    ["Luas Tanah", cari_field(field_names, ['LUASM2', 'LS_TNH'])],
                    ["Zonasi", cari_field(field_names, ['ZONASI'])],
                    ["Letak", cari_field(field_names, ['LETAK'])],
                    ["Elevasi", cari_field(field_names, ['ELEVASI'])],
                    ["Lebar Jalan", cari_field(field_names, ['LBRJLN', 'LB_JLN'])],         
                    ["Kelas Jalan", cari_field(field_names, ['KLSJLN', 'KLS_JLN'])],        
                    ["Jarak Arteri Primer", cari_field(field_names, ['JKATRP', 'JK_ATRP'])],        
                    ["Jarak Arteri Sekunder", cari_field(field_names, ['JKATRS', 'JK_ATRS'])],        
                    ["Jarak Kolektor Primer", cari_field(field_names, ['JKKOLP', 'JK_KOLP'])],         
                    ["Jarak Kolektor Sekunder", cari_field(field_names, ['JKKOLS', 'JK_KOLS'])],         
                    ["Jarak CBD", cari_field(field_names, ['JKCBD', 'JK_CBD'])],          # 
                    ["Jarak Fasilitas Kesehatan", cari_field(field_names, ['JKKES', 'JK_KES'])],           
                    ["Jarak Fasilitas Pendidikan", cari_field(field_names, ['JKPDDKN', 'JK_EDU'])],      
                    ["Jarak Fasilitas Transportasi", cari_field(field_names, ['JKTRANSP', 'JK_TRAN'])],    
                    ["Jarak Fasilitas Pemerintahan", cari_field(field_names, ['JKPMRNTH', 'JK_PEM'])],    
                    ["Banjir", cari_field(field_names, ['BANJIR'])],
                    ["Longsor", cari_field(field_names, ['LONGSOR'])],
                    ["Nilai Bidang Tanah", cari_field(field_names, ['NILAIBD'])]
                ]


                daftar_variable.value = default_variabel
            spatial_ref = arcpy.Describe(nbt_layer).spatialReference
            if 'DGN_1995_Indonesia_TM-3_Zone' not in spatial_ref.name:
                nbt_layer.setErrorMessage("Koordinat Persil harus DGN_1995_Indonesia_TM-3")

                return

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter. This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        fields = parameters[0].valueAsText


        config_and_paths = persil.get_config_values()
        dataset_path = config_and_paths['dataset_path']
        arcpy.AddMessage(fields)

        # # --- Validasi: pastikan field nomorzone dan nilai tidak NULL dan bernilai numerik
        # fields = [nomorzone, nilai, jeniszona]

        # if not znt_lama:
        #     arcpy.AddError("File ZNT lama tidak ditemukan.")
        #     return

        # try:
        #     with arcpy.da.SearchCursor(znt_lama, fields) as cursor:

        #         for rownum, row in enumerate(cursor, start=1):
        #             for i, val in enumerate(row):
        #                 field_name = fields[i]


        #                 if val is None:
        #                     arcpy.AddError(f"{field_name} NULL di baris {rownum}")
        #                     return


        #                 try:
        #                     if isinstance(val, str):
        #                         val = float(val.strip())
        #                     elif isinstance(val, bool):
        #                         raise ValueError("Boolean tidak valid")
        #                     else:
        #                         val = float(val)
        #                 except:
        #                     arcpy.AddError(f"{field_name} tidak bisa dikonversi ke angka di baris {rownum}")
        #                     return

        #                 if math.isnan(val) or val <= 0:
        #                     arcpy.AddError(f"Field {field_name} memiliki nilai tidak valid (0, negatif, atau Null) di baris {rownum}")
        #                     return

        #                 if field_name == jeniszona:
        #                     if int(val) not in [1, 2]:
        #                         arcpy.AddError(f" Field {field_name} memiliki nilai tidak valid ({int(val)}) di baris {rownum}\nJenis Zona hanya boleh berisi angka 1 (Non-Pertanian) atau 2 (Pertanian)")
        #                         return           

        #                 try:
        #                     if isinstance(val, str):
        #                         val = float(val.strip())
        #                     elif isinstance(val, bool):
        #                         raise ValueError("Boolean tidak valid")
        #                     else:
        #                         val = float(val)
        #                 except:
        #                     arcpy.AddError(f"{field_name} tidak bisa dikonversi ke angka di baris {rownum}")
        #                     return

        #                 if math.isnan(val) or val <= 0:
        #                     arcpy.AddError(f"Field {field_name} memiliki nilai tidak valid (0, negatif, atau Null) di baris {rownum}")
        #                     return

        #                 if field_name == jeniszona:
        #                     if int(val) not in [1, 2]:
        #                         arcpy.AddError(f" Field {field_name} memiliki nilai tidak valid ({int(val)}) di baris {rownum}\nJenis Zona hanya boleh berisi angka 1 (Non-Pertanian) atau 2 (Pertanian)")
        #                         return           

        # except arcpy.ExecuteError:
        #     arcpy.AddError(f"Gagal membaca layer: {arcpy.GetMessages(2)}")
        #     return

        # arcpy.AddMessage("Validasi field nomor zona dan nilai: OK.")

        # # --- Proses memasukkan data ZNT sebelumnya ke layer ZNT saat ini
        # zona_layer_path = os.path.join(dataset_path, "Zona_Layer")
        # zona_layer_temp_path = 'in_memory/Zona_Layer_Temp'

        # # Hapus topology dan layer zona jika sudah ada
        # topo = os.path.join(dataset_path, "Zona_Layer_Topology")
        # if arcpy.Exists(topo):
        #     arcpy.management.Delete(topo)

        # if arcpy.Exists(zona_layer_path):
        #     arcpy.management.Delete(zona_layer_path)

        # if arcpy.Exists(zona_layer_temp_path):
        #     arcpy.management.Delete(zona_layer_temp_path)

        # field_mappings = arcpy.FieldMappings()
        # field_mappings.addTable(znt_lama)

        # # Hapus field OBJECTID dari field mappings
        # for field_map in field_mappings.fieldMappings:
        #     if field_map.outputField.name.upper() == "OBJECTID":
        #         field_mappings.removeFieldMap(field_mappings.findFieldMapIndex(field_map.outputField.name))


        # arcpy.conversion.FeatureClassToFeatureClass(
        #     znt_lama,
        #     'in_memory',
        #     "Zona_Layer_Temp",
        #     field_mapping=field_mappings
        # )

        # # ======================
        # # FIELD CALCULATIONS
        # # ======================

        # """
        # Simpan data lama dahulu
        # """

        # old_value_fields = [{'name': "NILAIZN_LAMA", 'data_type': "LONG"},
        #                 {'name': "NILBULAT_LAMA", 'data_type': "TEXT"}]
        # input_features_fields = [f.name for f in arcpy.ListFields(znt_lama)]

        # for field in old_value_fields:
        #     if field['name'] in input_features_fields:
        #         arcpy.management.CalculateField(zona_layer_temp_path, field['name'], "None", "PYTHON3") 
        #     else:
        #         arcpy.management.AddField(zona_layer_temp_path, field['name'], field['data_type'])

        # # Fungsi untuk pembulatan nilai zona
        # code_block = """def get(a):
        #     if a:
        #         return round(a) 
        #     else:
        #         return a  # Pertahankan nilai null"""

        # # Fungsi untuk format nilai mata uang dengan pembulatan
        # code_block2 = """def get(a, b):
        #     if a:
        #         # Bulatkan nilai berdasarkan parameter, format ke Rupiah
        #         valu = round((int(a)/int(b)), 0)*int(b)
        #         return 'Rp. ' + (f'{int(float(valu)):,}').replace(',', '.')  # Format dengan titik sebagai pemisah ribuan
        #     else:
        #         return a  # Pertahankan nilai null"""
        
        # kode_jenis_zona = """def get_jenis_zona(a):
        #     if a == 1:
        #         return 'Non-Pertanian'
        #     elif a == 2:
        #         return 'Pertanian'"""

        # # Perhitungan field untuk berbagai kolom:
        # arcpy.management.CalculateField(zona_layer_temp_path, "NILAIZN_LAMA", f"get(!{nilai}!)", "PYTHON3", code_block)  # Salin nilai asli
        # arcpy.management.CalculateField(zona_layer_temp_path, "NILBULAT_LAMA", f"get(!{nilai}!, '1000')", "PYTHON3", code_block2)  # Salin nilai bulat
        # arcpy.management.DeleteField(zona_layer_temp_path, nilai)  # Hapus field nilai asli jika berbeda
        
        # # NOZN tidak terbaca,
        # arcpy.management.AddField(zona_layer_temp_path, "NOZN", "LONG")
        # arcpy.management.CalculateField(zona_layer_temp_path, 'NOZN', f"int(!{nomorzone}!)", "PYTHON3")
        # if nomorzone != "NOZN":
        #     arcpy.management.DeleteField(zona_layer_temp_path, nomorzone)

        # if jeniszona:
        #     if jeniszona != "JNSZN":
        #         arcpy.management.AddField(zona_layer_temp_path, "JNSZN", "SHORT")
        #         arcpy.management.CalculateField(zona_layer_temp_path, 'JNSZN', f"!{jeniszona}!", "PYTHON3")
        #         arcpy.management.CalculateField(zona_layer_temp_path, 'PENGGUNAAN', f"get_jenis_zona(!{jeniszona}!)", "PYTHON3", kode_jenis_zona)
        #         arcpy.management.DeleteField(zona_layer_temp_path, jeniszona)
        # else:
        #         arcpy.management.AddField(zona_layer_temp_path, "JNSZN", "SHORT")
        #         arcpy.management.CalculateField(zona_layer_temp_path, "JNSZN", "1", "PYTHON3")  # Set default ke 1
        #         arcpy.management.AddField(zona_layer_temp_path, "PENGGUNAAN", "TEXT")
        #         arcpy.management.CalculateField(zona_layer_temp_path, "PENGGUNAAN", "'Non-Pertanian'", "PYTHON3")  # Set default

        # self.check_and_prepare_nomor_zona(zona_layer_temp_path)

        # # --- Hapus field yang tidak diinginkan ---
        # all_fields = [f.name for f in arcpy.ListFields(zona_layer_temp_path)]
        
        # # Dapatkan nama field geometri dan ObjectID
        # desc = arcpy.Describe(zona_layer_temp_path)
        # shape_field_name = desc.shapeFieldName
        # oid_field_name = desc.OIDFieldName

        # # Field yang ingin dipertahankan
        # desired_fields = ["NOZN", "NILAIZN", "JNSZN", "PENGGUNAAN", "NILAIZN_LAMA", "NILBULAT", "NILBULAT_LAMA", "HISTZONE", shape_field_name, oid_field_name]
        
        # # Tambahkan field yang diperlukan sistem (seperti Shape_Length, Shape_Area) ke daftar yang dipertahankan
        # for field in desc.fields:
        #     if not field.editable:
        #         if field.name not in desired_fields:
        #             desired_fields.append(field.name)

        # fields_to_delete = [f for f in all_fields if f not in desired_fields]

        # if fields_to_delete:
        #     arcpy.management.DeleteField(zona_layer_temp_path, fields_to_delete)

        # required_fields = [
        #                     {'name': "SMPBKREL", 'data_type': "DOUBLE"},
        #                     {'name': "SMPBAKU", 'data_type': "DOUBLE"},
        #                     {'name': "NILAIZN", 'data_type': "DOUBLE"},
        #                     {'name': "JMLSMPL", 'data_type': "SHORT"},
        #                     {'name': "NILBULAT", 'data_type': "TEXT"},
        #                     {'name': "NILMIN", 'data_type': "LONG"},
        #                     {'name': "NILMAKS", 'data_type': "LONG"},
        #                     {'name': "cluster", 'data_type': "TEXT"},
        #                     {'name': "WADMKK", 'data_type': "TEXT"},
        #                     {'name':"WADMPR", 'data_type': "TEXT"},
        #                     {'name': "THNNILAI", 'data_type': "SHORT"}]

        # existing_fields_details = {f.name: f.type for f in arcpy.ListFields(zona_layer_temp_path)}

        # for field_info in required_fields:
        #     field_name = field_info['name']
        #     field_type = field_info['data_type']
            
        #     # Periksa apakah field sudah ada
        #     if field_name in existing_fields_details:
        #         # Jika tipe data tidak sesuai, hapus field tersebut
        #         if existing_fields_details[field_name].upper() != field_type.upper():
        #             arcpy.management.DeleteField(zona_layer_temp_path, field_name)
        #             arcpy.management.AddField(zona_layer_temp_path, field_name, field_type)
        #         else:
        #             # Jika tipe data sudah benar, kosongkan nilainya
        #             arcpy.management.CalculateField(zona_layer_temp_path, field_name, "None", "PYTHON3")
        #     else:
        #         # Jika field belum ada, tambahkan
        #         arcpy.management.AddField(zona_layer_temp_path, field_name, field_type)

        # arcpy.management.AlterField(
        #     in_table=zona_layer_temp_path,
        #     field="cluster",
        #     new_field_name="cluster",        # boleh sama (tidak ganti nama)
        #     new_field_alias="KLASTER"
        # )
        #         # Set nilai default
        # arcpy.management.CalculateField(zona_layer_temp_path, "WADMKK", "'"+str(config_and_paths['kota'])+"'", "PYTHON3")  # Set kode kabupaten/kota
        # arcpy.management.CalculateField(zona_layer_temp_path, "WADMPR", "'"+str(config_and_paths['provinsi'])+"'", "PYTHON3")  # Set kode provinsi
        # arcpy.management.CalculateField(zona_layer_temp_path, "THNNILAI", config_and_paths['tahun'], "PYTHON3")  # Set tahun nilai
        # arcpy.management.CalculateField(zona_layer_temp_path, "cluster", "1", "PYTHON3")  # Set cluster default

        # zona_layer_fields = [f.name for f in arcpy.ListFields(zona_layer_temp_path)]
        # # Tambah field JNSZN (jenis zona) jika belum ada

        # if "HISTZONE" not in zona_layer_fields:
        #     """
        #     JIKA HISTZONE BELUM ADA:
        #     Membuat field HISTZONE baru dengan urutan nomor dan tipe zona
        #     """
            

        #     # Membuat field sementara untuk menyimpan tipe zona
        #     arcpy.management.AddField(zona_layer_temp_path, "temp", "STRING")

        #     # Mengisi field temp dengan 'N' atau 'P' berdasarkan JNSZN. N berarti NON-PERTANIAN, P berarti PERTANIAN
        #     expression = "abc(!JNSZN!)"
        #     codeblock = """def abc(JNSZN):
        #         if JNSZN == 1:
        #             return 'N'  
        #         elif JNSZN == 2:
        #             return 'P'  
        #         else:
        #             return ''   
        #         """
        #     arcpy.management.CalculateField(zona_layer_temp_path, "temp", expression, "PYTHON3", codeblock)
            
        #     # Menggabungkan NOZN dan temp menjadi HISTZONE (contoh: "1N", "2P")
        #     arcpy.management.CalculateField(zona_layer_temp_path, "HISTZONE", "str(!NOZN!) + !temp!", "PYTHON3")
            
        #     # Menghapus field sementara
        #     arcpy.management.DeleteField(zona_layer_temp_path, "temp")

        # # Update penggunaan lahan berdasarkan jenis zona
        # with arcpy.da.UpdateCursor(zona_layer_temp_path, ["JNSZN", "PENGGUNAAN"]) as rows:
        #     for row in rows:
        #         if row[0] == 1:  # Jika jenis zona = 1
        #             row[1] = "Non-Pertanian"
        #         elif row[0] == 2:  # Jika jenis zona = 2
        #             row[1] = "Pertanian"
        #         rows.updateRow(row)  # Update record
        # del row, rows  # Bersihkan cursor

        # zona_layer_lyr = "zona_layer_lyr_tmp"
        # arcpy.management.MakeFeatureLayer(zona_layer_temp_path, zona_layer_lyr)
        
        # existing_fields = [f.name for f in arcpy.ListFields(zona_layer_lyr)]
        # ordered_fields = [
        #     "NOZN",
        #     "cluster",
        #     "WADMKK",
        #     "WADMPR",
        #     "JNSZN",
        #     "PENGGUNAAN",
        #     "HISTZONE",
        #     "SMPBKREL",
        #     "SMPBAKU",
        #     "NILAIZN",
        #     "JMLSMPL",
        #     "NILMIN",
        #     "NILMAKS",
        #     "NILBULAT",
        #     "THNNILAI",
        #     "NILAIZN_LAMA",
        #     "NILBULAT_LAMA",
        # ]

        # fms = arcpy.FieldMappings()

        # for fld in ordered_fields:
        #     if fld not in existing_fields:
        #         arcpy.AddWarning(f"Field '{fld}' tidak ditemukan, dilewati")
        #         continue

        #     fm = arcpy.FieldMap()
        #     fm.addInputField(zona_layer_lyr, fld)
        #     fms.addFieldMap(fm)

        # arcpy.conversion.FeatureClassToFeatureClass(
        #     zona_layer_temp_path,
        #     dataset_path,
        #     'Zona_Layer',
        #     field_mapping=fms
        # )

        # arcpy.management.Delete(zona_layer_temp_path)  # Hapus layer sementara      

        # # BUG ERROR (Arcgis 3.6): Baca Lebih rinci di : https://www.notion.so/ZNT-002-2e42170c49e3807c9119ef76beb74a46?source=copy_link

        # if arcpy.Exists(zona_layer_path):
        #     p = arcpy.mp.ArcGISProject("CURRENT")
        #     m = p.activeMap
            
        #     # Tambahkan layer yang baru diproses
        #     m.addDataFromPath(zona_layer_path)
        
        # # End Of Bug 

        # return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""

        return
    
    def check_and_prepare_nomor_zona(self, layer):
        """
        Memastikan tidak ada nomor zona yang null atau terduplikat.
        Jika ada duplikasi, zona dengan nilai tertinggi mempertahankan nomor zonanya,
        yang lain di-null-kan kemudian diisi ulang dengan max(nozone) + 1.
        """
        nomorzone_field = 'NOZN'
        nilai_field = 'NILAIZN_LAMA'

        # Kumpulkan data zona: {nomorzone: [(FID, nilai), ...]}
        zona_data = {}
        max_nozone = 0
        with arcpy.da.SearchCursor(layer, ['OID@', nomorzone_field, nilai_field]) as cursor:
            for row in cursor:
                fid, nozone, nilai = row
                if nozone is not None:
                    if nozone > max_nozone:
                        max_nozone = nozone
                    if nozone not in zona_data:
                        zona_data[nozone] = []
                    zona_data[nozone].append((fid, nilai if nilai is not None else 0))
        
        # Tentukan FID mana yang harus di-null-kan (duplikat dengan nilai lebih rendah)
        fids_to_nullify = []
        
        for nozone, records in zona_data.items():
            if len(records) > 1:  # Ada duplikasi
                # Urutkan berdasarkan nilai (descending), ambil yang tertinggi
                records_sorted = sorted(records, key=lambda x: x[1], reverse=True)
                # Semua kecuali yang nilai tertinggi akan di-null-kan
                for fid, nilai in records_sorted[1:]:
                    fids_to_nullify.append(fid)
        
        # Null-kan nomor zona yang duplikat (kecuali yang nilai tertinggi)
        if fids_to_nullify:
            with arcpy.da.UpdateCursor(layer, ['OID@', nomorzone_field]) as cursor:
                for row in cursor:
                    if row[0] in fids_to_nullify:
                        row[1] = -1
                        cursor.updateRow(row)
        
        # Isi ulang nomor zona yang sudah ditandai dengan auto-increment
        current_nozone = max_nozone
        with arcpy.da.UpdateCursor(layer, [nomorzone_field]) as cursor:
            for row in cursor:
                if row[0] == -1:
                    current_nozone += 1
                    row[0] = current_nozone
                    cursor.updateRow(row)
 