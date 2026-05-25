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
                      Masukkan_Data_Jaringan_Jalan,
                      Masukkan_Data_Fasilitas,
                      Masukkan_Data_Risiko
                      ]

class Upload_Peta_Rencana_Lokasi_Kegiatan_AOI(object):
    def __init__(self):
        self.label = "Upload Peta Rencana Lokasi Kegiatan (AOI)"
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
            in_feature="Persil_Layer",
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
            displayName="Shapefile Lokasi Kegiatan Disepakati (.shp)",
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
            displayName="Shapefile Peta Area Kerja (.shp)",
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

        output_fl = arcpy.Parameter(
            name='fl_output',
            datatype='GPFeatureLayer',
            parameterType='Derived',
            direction='Output'
        )

        return [workspace_folder, koordinat_system, provinsi, kab_kota, tahun_penilaian, output_fl]

    def updateParameters(self, parameters):
        prov = parameters[2].valueAsText  # parameter Provinsi
        kab = parameters[3]               # parameter Kab/Kota

        if prov:
            kab.filter.type = "ValueList"
            kab.filter.list = KAB_KOTA.get(prov, [])
        else:
            kab.filter.list = []

    def execute(self, parameters, messages):

        folder_path = parameters[0].valueAsText
        spatial_reference = parameters[1].value
        provinsi = parameters[2].valueAsText
        kab_kota = parameters[3].valueAsText
        tahun_penilaian = parameters[4].value

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
                'provinsi': provinsi,
                'kab_kota': kab_kota,
                'tahun_penilaian': tahun_penilaian,
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
                },
                'skoring' : constant.SKORING_KELAS_JALAN
            },

            'persil_config': {
                'path': {
                    constant.LAYER_PERSIL: persil_path,
                    constant.LAYER_PERSIL_LINE: persil_line_path,
                    constant.LAYER_BELAHAN_PERSIL: persil_split_path,
                    constant.LAYER_CENTROID_PERSIL: persil_centroid_path,
                    constant.LAYER_TITIK_TENGAH_BELAHAN_PERSIL: persil_split_midpoint_path
                },
                'skoring' : {
                    'zonasi' : constant.SKORING_ZONASI,
                    'bentuk_persil' : constant.SKORING_BENTUK_PERSIL,
                    'letak' : constant.SKORING_LETAK
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
        arcpy.SetParameter(5, fl)
        arcpy.AddMessage("Workspace berhasil dibuat")

class Masukkan_Data_NBT_Sebelumnya(object):

    def __init__(self):

        self.label = "Masukkan Data NBT Sebelumnya"
        self.description = ""
        self.canRunInBackground = False

    DEFAULT_VARIABEL = [

        ["Kelurahan", "WADMKD", ["KELURAHAN", "KEL", "WADMKD"]],
        ["Kecamatan", "WADMKC", ["KECAMATAN", "KEC", "WADMKC"]],
        ["Tipe Hak", "TIPEHAK", ["TIPEHAK", "STATUS_PER"]],

        ["Lebar Depan", "LBRDPN", ["LBRDPN", "LB_DPN"]],
        ["Luas Tanah", "LUASM2", ["LUASM2", "LS_TNH"]],

        ["Skoring Zonasi", "S_ZONASI", ["S_ZONASI"]],
        ["Skoring Bentuk Persil", "S_BENTUK", ["S_BENTUK"]],
        ["Skoring Letak", "S_LETAK", ["S_LETAK"]],
        ["Skoring Elevasi", "S_ELEVASI", ["S_ELEVASI", "S_ELVASI"]],

        ["Lebar Jalan", "LBRJLN", ["LBRJLN", "LB_JLN"]],
        ["Skoring Kelas Jalan", "S_KLS_JLN", ["S_KLS_JLN"]],

        ["Jarak Arteri Primer", "JKATRP", ["JKATRP", "JK_ATRP"]],
        ["Jarak Arteri Sekunder", "JKATRS", ["JKATRS", "JK_ATRS"]],
        ["Jarak Kolektor Primer", "JKKOLP", ["JKKOLP", "JK_KOLP"]],
        ["Jarak Kolektor Sekunder", "JKKOLS", ["JKKOLS", "JK_KOLS"]],

        ["Nilai Bidang Tanah", "NILAIBD", ["PREDICTED", "NILAIBD"]],

        ["NIB", "NIB", ["NIB"]],
        ["IdBidang", "IDBIDANG", ["IDBIDANG", "IDBID"]]
    ]

    AUTO_CREATE_FIELDS = [

        ("BENTUK", "TEXT", 50),
        ("LETAK", "TEXT", 50),
        ("ELEVASI", "TEXT", 50),
        ("KLSJLN", "TEXT", 50),
        ("ZONASI", "TEXT", 50),

        ("JKCBD", "DOUBLE"),
        ("JKKES", "DOUBLE"),
        ("JKPDDKN", "DOUBLE"),
        ("JKTRANSP", "DOUBLE"),
        ("JKPMRNTH", "DOUBLE"),

        ("BANJIR", "SHORT"),
        ("LONGSOR", "SHORT")
    ]



    def getParameterInfo(self):

        nbt_awal = arcpy.Parameter(
            displayName="Pilih Data NBT",
            name="old_nbt_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )

        daftar_variabel = arcpy.Parameter(
            displayName="Sesuaikan Field",
            name="define_variable",
            datatype="GPValueTable",
            parameterType="Required",
            direction="Input"
        )

        daftar_variabel.columns = [
            ["GPString", "Nama Variabel"],
            ["Field", "Field Dataset"]
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
        daftar_variabel = parameters[1]

        if not nbt_layer:
            return

        field_names = [
            f.name.upper()
            for f in arcpy.ListFields(nbt_layer)
        ]

        if daftar_variabel.value is None:

            default_variabel = []

            for nama, _, kandidat in self.DEFAULT_VARIABEL:

                hasil_field = self.cari_field(
                    field_names,
                    kandidat
                )

                default_variabel.append([
                    nama,
                    hasil_field
                ])

            daftar_variabel.value = default_variabel

        missing_fields = []

        for nama, _, kandidat in self.DEFAULT_VARIABEL:

            hasil = self.cari_field(
                field_names,
                kandidat
            )

            if not hasil:
                missing_fields.append(nama)

        if missing_fields:

            daftar_variabel.setErrorMessage(
                "Field berikut belum tersedia:\n- "
                + "\n- ".join(missing_fields)
            )

        spatial_ref = arcpy.Describe(
            nbt_layer
        ).spatialReference

        if "DGN_1995_Indonesia_TM-3_Zone" not in spatial_ref.name:

            parameters[0].setErrorMessage(
                "Koordinat Persil harus DGN_1995_Indonesia_TM-3"
            )

        return

    def execute(self, parameters, messages):

        peta_lama_input = parameters[0].valueAsText
        daftar_variabel = parameters[1].value

        configs = persil.get_config_values()

        dataset_path = configs["project_config"]["dataset_path"]

        konfigurasi_variabel_path = configs[
            "project_config"
        ]["daftar_variabel_path"]

        dest_temp_path = r"in_memory\Persil_Lama"

        self.delete_if_exists(dest_temp_path)



        arcpy.management.CopyFeatures(
            peta_lama_input,
            dest_temp_path
        )


        mapping_field = {

            'Kelurahan': 'WADMKD',
            'Kecamatan': 'WADMKC',
            'Tipe Hak': 'TIPEHAK',

            'Lebar Depan': 'LBRDPN',
            'Luas Tanah': 'LUASM2',

            'Skoring Zonasi': 'S_ZONASI',
            'Skoring Bentuk Persil': 'S_BENTUK',
            'Skoring Letak': 'S_LETAK',
            'Skoring Elevasi': 'S_ELEVASI',

            'Lebar Jalan': 'LBRJLN',
            'Skoring Kelas Jalan': 'S_KLS_JLN',

            'Jarak Arteri Primer': 'JKATRP',
            'Jarak Arteri Sekunder': 'JKATRS',
            'Jarak Kolektor Primer': 'JKKOLP',
            'Jarak Kolektor Sekunder': 'JKKOLS',

            'Nilai Bidang Tanah': 'NILAIBD',

            'NIB': 'NIB',
            'IdBidang': 'IDBIDANG'
        }

        rename_fields = {}

        daftar_variabel_python = []

        for row in daftar_variabel:

            if not row:
                continue

            try:

                if len(row) < 2:
                    continue

                nama_variabel = str(row[0]).strip()
                field_dataset = str(row[1]).strip()

                if not field_dataset:
                    continue

                daftar_variabel_python.append([
                    nama_variabel,
                    field_dataset
                ])

                field_standar = mapping_field.get(
                    nama_variabel
                )

                if field_standar:

                    rename_fields[
                        field_dataset
                    ] = field_standar

            except Exception:
                pass


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

  

        existing_fields = [
            f.name
            for f in arcpy.ListFields(dest_temp_path)
        ]

        existing_fields_upper = [
            f.upper()
            for f in existing_fields
        ]
        
        # Rename

        for old_field, new_field in rename_fields.items():

            existing_fields = [
                f.name.upper()
                for f in arcpy.ListFields(dest_temp_path)
            ]

            if old_field.upper() == new_field.upper():
                continue

            if old_field.upper() not in existing_fields:
                continue

            if new_field.upper() in existing_fields:
                continue

            arcpy.AddMessage(
                f"Rename field: "
                f"{old_field} -> {new_field}"
            )

            arcpy.management.AlterField(
                dest_temp_path,
                old_field,
                new_field,
                new_field
            )

        protected_fields = {

            "FID",
            "OBJECTID",
            "SHAPE",

            "WADMKD",
            "WADMKC",
            "TIPEHAK",

            "LBRDPN",
            "LUASM2",

            "S_ZONASI",
            "S_BENTUK",
            "S_LETAK",
            "S_ELEVASI",

            "LBRJLN",
            "S_KLS_JLN",

            "JKATRP",
            "JKATRS",
            "JKKOLP",
            "JKKOLS",

            "NILAIBD",

            "NIB",
            "IDBIDANG"
        }

        geometry_fields = {
            "SHAPE",
            "SHAPE_LENGTH",
            "SHAPE_AREA"
        }

        fields_data = arcpy.ListFields(
            dest_temp_path
        )


        for field in fields_data:

            field_name = field.name

            is_protected = (

                field.type in ["Geometry", "OID"]

                or field_name.upper in geometry_fields

                or field_name.upper() in protected_fields
            )

            if not is_protected:

                try:

                    arcpy.management.DeleteField(
                        dest_temp_path,
                        field_name
                    )

                except Exception as e:

                    arcpy.AddWarning(str(e))

        existing_fields = [
            f.name.upper()
            for f in arcpy.ListFields(dest_temp_path)
        ]

        for field_data in self.AUTO_CREATE_FIELDS:

            field_name = field_data[0]
            field_type = field_data[1]

            field_length = None

            if len(field_data) >= 3:
                field_length = field_data[2]

            if field_name.upper() not in existing_fields:

                arcpy.management.AddField(
                    dest_temp_path,
                    field_name,
                    field_type,
                    field_length=field_length,
                    field_alias=field_name
                )

                # Set default value 0 untuk field numerik
                if field_type.upper() in ["SHORT", "LONG", "DOUBLE", "FLOAT"]:
                    arcpy.management.CalculateField(
                        dest_temp_path,
                        field_name,
                        0,
                        "PYTHON3"
                    )

        validation_errors = []

        validation_errors.extend(
            self.validate_skoring(
                dest_temp_path,
                "S_ELEVASI",
                constant.SKORING_ELEVASI,
                "Skoring Elevasi"
            )
        )
        validation_errors.extend(
            self.validate_skoring(
                dest_temp_path,
                "S_ZONASI",
                constant.SKORING_ZONASI,
                "Skoring Zonasi"
            )
        )

        validation_errors.extend(
            self.validate_skoring(
                dest_temp_path,
                "S_LETAK",
                constant.SKORING_LETAK,
                "Skoring Letak"
            )
        )

        validation_errors.extend(
            self.validate_skoring(
                dest_temp_path,
                "S_BENTUK",
                constant.SKORING_BENTUK_PERSIL,
                "Skoring Bentuk Persil"
            )
        )

        validation_errors.extend(
            self.validate_skoring(
                dest_temp_path,
                "S_KLS_JLN",
                constant.SKORING_KELAS_JALAN["kelas_jalan"],
                "Skoring Kelas Jalan"
            )
        )

        if validation_errors:

            raise Exception(
                "\n".join(validation_errors)
            )

        reverse_bentuk = {
            v: k
            for k, v
            in constant.SKORING_BENTUK_PERSIL.items()
        }

        reverse_letak = {
            v: k
            for k, v
            in constant.SKORING_LETAK.items()
        }

        reverse_elevasi = {
            v: k
            for k, v
            in constant.SKORING_ELEVASI.items()
        }

        reverse_zonasi = {
            v: k
            for k, v
            in constant.SKORING_ZONASI.items()
        }
        
        reverse_kelas_jalan = {
            v: k
            for k, v
            in constant.SKORING_KELAS_JALAN[
                "kelas_jalan"
            ].items()
        }

        with arcpy.da.UpdateCursor(
            dest_temp_path,
            [
                "S_BENTUK",
                "BENTUK",

                "S_LETAK",
                "LETAK",

                "S_ELEVASI",
                "ELEVASI",

                "S_KLS_JLN",
                "KLSJLN",

                "S_ZONASI",
                "ZONASI"
            ]
        ) as cursor:

            for row in cursor:

                row[1] = reverse_bentuk.get(row[0])
                row[3] = reverse_letak.get(row[2])
                row[5] = reverse_elevasi.get(row[4])
                row[7] = reverse_kelas_jalan.get(row[6])
                row[9] = reverse_zonasi.get(row[8])

                cursor.updateRow(row)

        existing_field_names = [
            f.name.lower()
            for f in arcpy.ListFields(dest_temp_path)
        ]
        prov = configs['project_config']['provinsi']
        kab_kota = configs['project_config']['kab_kota']
        tahun = configs['project_config']['tahun_penilaian']

        field_from_project = [

            ['WADMPR', 'TEXT', prov, 'WADMPR',],
            ['WADMKK', 'TEXT', kab_kota, 'WADMKK',],
            ['THNNILAI', 'SHORT', tahun, 'THNNILAI'],
            ['KLSTRZ', 'SHORT', 1, 'KLASTER ZONASI']
        ]

        for field_name, field_type, field_value, field_alias in field_from_project:

            existing_fields = [
                f.name.upper()
                for f in arcpy.ListFields(dest_temp_path)
            ]

            if field_name.upper() not in existing_fields:

                arcpy.management.AddField(
                    dest_temp_path,
                    field_name,
                    field_type,
                    field_alias=field_alias
                )

            arcpy.management.CalculateField(
                dest_temp_path,
                field_name,
                repr(field_value),
                "PYTHON3"
            )
        
        
        if "ls_asal" not in existing_field_names:

            arcpy.management.AddField(
                dest_temp_path,
                "ls_asal",
                "DOUBLE"
            )

        arcpy.management.CalculateField(
            dest_temp_path,
            "ls_asal",
            "!shape.area!",
            "PYTHON3"
        )
        ordered_fields = [

            "WADMPR",
            "WADMKK",
            "WADMKC",
            "WADMKD",

            "TIPEHAK",

            "LUASM2",
            "LBRDPN",

            "ZONASI",
            "KLSTRZ",
            "LETAK",
            "BENTUK",
            "ELEVASI",

            "LBRJLN",
            "KLSJLN",

            "JKATRP",
            "JKATRS",
            "JKKOLP",
            "JKKOLS",
            "JKCBD",

            "JKKES",
            "JKPDDKN",
            "JKTRANSP",
            "JKPMRNTH",

            "BANJIR",
            "LONGSOR",

            "NILAIBD",
            "THNNILAI"
        ]


        persil_layer = os.path.join(
            dataset_path,
            constant.LAYER_PERSIL
        )

        self.reorder_fields(
            dest_temp_path,
            persil_layer,
            ordered_fields
        )

        # Reorder IDBIDANG berdasarkan OBJECTID
        with arcpy.da.UpdateCursor(
            persil_layer,
            ["OBJECTID", "IDBIDANG"],
            sql_clause=(None, "ORDER BY OBJECTID")
        ) as cursor:

            for nomor, row in enumerate(cursor, start=1):

                row[1] = nomor

                cursor.updateRow(row)

        arcpy.SetParameter(
            2,
            persil_layer
        )

        return

    def validate_skoring(
        self,
        layer_path,
        field_name,
        skor_dict,
        field_label
    ):

        if not field_name:
            return []

        errors = []

        nilai_maksimum = max(
            skor_dict.values()
        )

        nilai_minimum = min(
            skor_dict.values()
        )

        with arcpy.da.SearchCursor(
            layer_path,
            [field_name]
        ) as cursor:

            for idx, row in enumerate(
                cursor,
                start=1
            ):

                value = row[0]

                if value is None:

                    errors.append(
                        f"{field_label} "
                        f"baris {idx} NULL"
                    )

                    continue

                if not isinstance(
                    value,
                    (int, float)
                ):

                    errors.append(
                        f"{field_label} "
                        f"baris {idx} "
                        f"bukan angka"
                    )

                    continue

                if isinstance(value, float):

                    if not value.is_integer():

                        errors.append(
                            f"{field_label} "
                            f"baris {idx} "
                            f"harus berupa "
                            f"bilangan bulat"
                        )

                        continue

                value = int(value)

                if value > nilai_maksimum:

                    errors.append(
                        f"{field_label} "
                        f"baris {idx} "
                        f"nilainya tidak "
                        f"dalam rentang "
                        f"{nilai_minimum}"
                        f" - "
                        f"{nilai_maksimum}"
                    )

                if value < nilai_minimum:

                    errors.append(
                        f"{field_label} "
                        f"baris {idx} "
                        f"nilainya tidak "
                        f"dalam rentang "
                        f"{nilai_minimum}"
                        f" - "
                        f"{nilai_maksimum}"
                    )

        return errors

    def cari_field(
        self,
        field_names,
        kandidat
    ):

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
                    f"Gagal menghapus "
                    f"{path}: {e}"
                )
    def reorder_fields(
        self,
        input_fc,
        output_fc,
        ordered_fields
    ):

        existing_fields = arcpy.ListFields(input_fc)

        system_fields = {
            "OBJECTID",
            "FID",
            "SHAPE"
        }

        existing_field_names = [
            f.name
            for f in existing_fields
            if f.type not in ["OID", "Geometry"]
        ]

        ordered_existing = [

            f for f in ordered_fields
            if f in existing_field_names
        ]

        remaining_fields = [

            f for f in existing_field_names
            if f not in ordered_existing
        ]

        final_fields = (
            ordered_existing
            + remaining_fields
        )

        field_mappings = arcpy.FieldMappings()

        for field_name in final_fields:

            field_map = arcpy.FieldMap()

            field_map.addInputField(
                input_fc,
                field_name
            )

            output_field = field_map.outputField
            output_field.name = field_name.upper()
            output_field.aliasName = field_name.upper()

            field_map.outputField = output_field

            field_mappings.addFieldMap(field_map)

        arcpy.conversion.FeatureClassToFeatureClass(
            input_fc,
            os.path.dirname(output_fc),
            os.path.basename(output_fc),
            field_mapping=field_mappings
    )

class Masukkan_Data_Jaringan_Jalan(object):

    def __init__(self):
        self.label = "Masukkan Data Jaringan Jalan"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):

        jaringan_jalan=arcpy.Parameter(
            displayName="Jaringan Jalan (.shp)",
            name="jaringan_jalan",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input"
        )

        jaringan_jalan.filter.list = ["shp"]

        field_skor_jalan=arcpy.Parameter(
            displayName="Field Skor Kelas Jalan",
            name="field_skor_jalan",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        field_skor_jalan.parameterDependencies=[jaringan_jalan.name]

        field_lebar_jalan=arcpy.Parameter(
            displayName="Field Lebar Jalan",
            name="field_lebar_jalan",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        field_lebar_jalan.parameterDependencies=[jaringan_jalan.name]

        output_jaringan_jalan = arcpy.Parameter(
            displayName="Output Jaringan Jalan",
            name="output_jaringan_jalan",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [ jaringan_jalan, field_skor_jalan, field_lebar_jalan, output_jaringan_jalan ]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self,parameters,messages):

        in_jaringan_jalan=parameters[0].valueAsText
        field_skor_jalan = parameters[1].valueAsText
        field_lebar_jalan = parameters[2].valueAsText

        interest_fields = [field_skor_jalan, field_lebar_jalan]
        configs=persil.get_config_values()
        dataset_path=configs["project_config"]["dataset_path"]
        jaringan_jalan_path=configs["jaringan_jalan_config"]["path"]["Jaringan_Jalan"]
        jaringan_jalan="Jaringan_Jalan"
        topologi_jaringan_jalan_path=os.path.join(dataset_path,'Topologi_Jaringan_Jalan')
        if arcpy.Exists(topologi_jaringan_jalan_path):
            arcpy.management.Delete(topologi_jaringan_jalan_path)


        with arcpy.da.SearchCursor(in_jaringan_jalan, interest_fields) as cursor:
            for row in cursor:
                if row[0] is None or row[1] is None:
                    arcpy.AddError("Terdapat nilai kosong pada field skor kelas jalan atau field lebar jalan. Pastikan semua data pada kedua field tersebut terisi dengan benar.")
                    return
                if row[0] > 7 or row[0] < 1:
                    arcpy.AddError("Terdapat nilai pada field skor kelas jalan yang tidak valid. Pastikan semua nilai pada field tersebut berada dalam rentang 1 hingga 7.")
                    return

        del cursor

        if arcpy.Exists(jaringan_jalan_path):
            arcpy.management.Delete(jaringan_jalan_path)

        arcpy.conversion.FeatureClassToFeatureClass(
                in_jaringan_jalan,
                dataset_path,
                jaringan_jalan
        )

        arcpy.management.AlterField(
            jaringan_jalan_path,
            field_skor_jalan,
            "s_kls_jln",
            "Skor Kelas Jalan"
        )

        arcpy.management.AlterField(
            jaringan_jalan_path,
            field_lebar_jalan,
            "lb_jln",
            "Lebar Jalan"
        )
        arcpy.management.AddField(
            jaringan_jalan_path,
            "kls_jln",
            "TEXT",
            field_alias="Kelas Jalan"
        )
        kelas_mapping = {
            1: "Setapak",
            2: "Lokal Sekunder",
            3: "Lokal Primer",
            4: "Kolektor Sekunder",
            5: "Kolektor Primer",
            6: "Arteri Sekunder",
            7: "Arteri Primer"
        }
        with arcpy.da.UpdateCursor(jaringan_jalan_path, ["s_kls_jln", "kls_jln"]) as cursor:
            for row in cursor:
                skor = row[0]
                row[1] = kelas_mapping.get(skor, "Kelas Tidak Diketahui")

                cursor.updateRow(row)

        list_names=[f.name for f in arcpy.ListFields(jaringan_jalan_path)]

        if "status_jal" not in list_names:
            arcpy.management.AddField(
                jaringan_jalan_path,
                "status_jal",
                "TEXT"
            )

        arcpy.management.CalculateField(
            jaringan_jalan_path,
            "status_jal",
            '"Tetap"',
            "PYTHON3"
        )
        required_fields = {
            "OBJECTID",
            "Shape",
            "Shape_Length",
            "Shape_Area",
            "s_kls_jln",
            "lb_jln",
            "kls_jln",
            "status_jal"
        }

        delete_fields = [
            field.name
            for field in arcpy.ListFields(jaringan_jalan_path)
            if (
                field.type not in ["OID", "Geometry"] and
                field.name not in required_fields
            )
        ]

        if delete_fields:
            arcpy.management.DeleteField(
                jaringan_jalan_path,
                delete_fields
            )
        simbologi_path=r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Simbologi_Kelas_Jaringan_Jalan.lyrx"

        if arcpy.Exists(jaringan_jalan):
            try:
                arcpy.management.Delete(jaringan_jalan)
            except:
                pass

        arcpy.management.MakeFeatureLayer(
            jaringan_jalan_path,
            jaringan_jalan
        )
        arcpy.management.ApplySymbologyFromLayer(
            jaringan_jalan,
            simbologi_path
            )

        arcpy.SetParameter(3, jaringan_jalan)

        messages.addMessage("== Proses selesai ==")
        return

class Masukkan_Data_Fasilitas(object):

    def __init__(self):

        self.label = "Masukkan Data Fasilitas"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):

        mode_input = arcpy.Parameter(
            displayName="Mode Input",
            name="mode_input",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )

        mode_input.filter.type = "ValueList"

        mode_input.filter.list = [
            "Fasilitas Wajib",
            "Tambah Fasilitas Baru",
            "Tambah Fasilitas dari NBT Sebelumnya"
        ]

        mode_input.value = "Fasilitas Wajib"

        nbt_sebelumnya_path = arcpy.Parameter(
            displayName="Data NBT Sebelumnya",
            name="nbt_sebelumnya_path",
            datatype="DEFeatureClass",
            parameterType="Optional",
            direction="Input"
        )

        existing_field = arcpy.Parameter(
            displayName="Field Existing",
            name="existing_field",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )

        existing_field.filter.type = "ValueList"

        existing_field.filter.list = [
            "JKCBD",
            "JKKES",
            "JKPDDKN",
            "JKTRANSP",
            "JKPMRNTH"
        ]

        fasilitas_path = arcpy.Parameter(
            displayName="Feature Class Fasilitas",
            name="fasilitas_path",
            datatype="DEFeatureClass",
            parameterType="Optional",
            direction="Input"
        )

        nama_fasilitas = arcpy.Parameter(
            displayName="Nama Fasilitas Baru",
            name="nama_fasilitas",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )

        jarak_field = arcpy.Parameter(
            displayName="Field Jarak Fasilitas",
            name="jarak_field",
            datatype="Field",
            parameterType="Optional",
            direction="Input"
        )

        jarak_field.parameterDependencies = [
            nbt_sebelumnya_path.name
        ]

        output_layer = arcpy.Parameter(
            displayName="Output Fasilitas",
            name="output_layer",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [
            mode_input,
            nbt_sebelumnya_path,
            existing_field,
            fasilitas_path,
            nama_fasilitas,
            jarak_field,
            output_layer
        ]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):

        mode_input = parameters[0].valueAsText

        # =====================================================
        # FASILITAS WAJIB
        # =====================================================

        if mode_input == "Fasilitas Wajib":

            parameters[1].enabled = True
            parameters[2].enabled = True

            parameters[3].enabled = True
            parameters[4].enabled = False

            parameters[5].enabled = True

        # =====================================================
        # TAMBAH FASILITAS BARU
        # =====================================================

        elif mode_input == "Tambah Fasilitas Baru":

            parameters[1].enabled = False
            parameters[2].enabled = False

            parameters[3].enabled = True
            parameters[4].enabled = True

            parameters[5].enabled = False

        # =====================================================
        # TAMBAH FASILITAS DARI NBT SEBELUMNYA
        # =====================================================

        elif mode_input == "Tambah Fasilitas dari NBT Sebelumnya":

            parameters[1].enabled = True
            parameters[2].enabled = False

            parameters[3].enabled = True
            parameters[4].enabled = True

            parameters[5].enabled = True

        return

    def updateMessages(self, parameters):

        nama_fasilitas = parameters[4].valueAsText

        if nama_fasilitas:

            if len(nama_fasilitas) > 8:

                parameters[4].setErrorMessage(
                    "Nama fasilitas maksimal 8 huruf"
                )

        return

    # =====================================================
    # HELPER
    # =====================================================

    def copy_fasilitas(
        self,
        fasilitas_path,
        dataset_path,
        nama_fasilitas,
        messages
    ):

        output_fc = os.path.join(
            dataset_path,
            nama_fasilitas
        )

        if arcpy.Exists(output_fc):

            messages.addWarningMessage(
                f"{nama_fasilitas} sudah ada, menghapus lama"
            )

            arcpy.management.Delete(output_fc)

        arcpy.conversion.FeatureClassToFeatureClass(
            fasilitas_path,
            dataset_path,
            nama_fasilitas
        )

        return output_fc

    def transfer_centroid(
        self,
        source_fc,
        target_fc,
        source_field,
        target_field,
        messages,
        max_distance=5
    ):

        messages.addMessage(
            f"== Membaca centroid {source_fc} =="
        )

        source_centroids = []

        with arcpy.da.SearchCursor(
            source_fc,
            ["OID@", "SHAPE@", source_field]
        ) as cursor:

            for row in cursor:

                oid = row[0]
                geom = row[1]
                nilai = row[2]

                if not geom:
                    continue

                centroid_geom = arcpy.PointGeometry(
                    geom.centroid,
                    geom.spatialReference
                )

                source_centroids.append({
                    "oid": oid,
                    "centroid": centroid_geom,
                    "nilai": nilai
                })

        messages.addMessage(
            f"== {len(source_centroids)} centroid dibaca =="
        )

        updated = 0
        skipped = 0

        with arcpy.da.UpdateCursor(
            target_fc,
            ["OID@", "SHAPE@", target_field]
        ) as cursor:

            for row in cursor:

                oid_target = row[0]
                geom_target = row[1]

                if not geom_target:

                    skipped += 1
                    continue

                centroid_target = arcpy.PointGeometry(
                    geom_target.centroid,
                    geom_target.spatialReference
                )

                nearest_distance = float("inf")

                nearest_value = None

                for item in source_centroids:

                    dist = centroid_target.distanceTo(
                        item["centroid"]
                    )

                    if dist < nearest_distance:

                        nearest_distance = dist
                        nearest_value = item["nilai"]

                if (
                    nearest_value is not None and
                    nearest_distance <= max_distance
                ):

                    row[2] = nearest_value

                    cursor.updateRow(row)

                    updated += 1

                else:

                    skipped += 1

        messages.addMessage(
            f"== {updated} bidang berhasil diupdate =="
        )

        messages.addMessage(
            f"== {skipped} bidang dilewati =="
        )
    # =====================================================
    # EXECUTE
    # =====================================================

    def execute(self, parameters, messages):

        messages.addMessage(
            "== Proses dimulai =="
        )

        mode_input = parameters[0].valueAsText

        configs = persil.get_config_values()

        persil_path = os.path.join(
            configs["project_config"]["dataset_path"],
            "Persil_Layer"
        )

        dataset_path = configs[
            "fasilitas_config"
        ]["dataset_path"]

        gdb_path = configs[
            "project_config"
        ]["gdb_path"]

        # =====================================================
        # MEMBUAT DATASET FASILITAS
        # =====================================================

        if not arcpy.Exists(dataset_path):

            messages.addMessage(
                "== Membuat dataset fasilitas =="
            )

            spatial_ref = arcpy.Describe(
                persil_path
            ).spatialReference

            arcpy.management.CreateFeatureDataset(
                gdb_path,
                os.path.basename(dataset_path),
                spatial_ref
            )

        # =====================================================
        # MODE FASILITAS WAJIB
        # =====================================================

        if mode_input == "Fasilitas Wajib":

            nbt_sebelumnya_path = parameters[1].valueAsText

            field_existing = parameters[2].valueAsText

            fasilitas_path = parameters[3].valueAsText

            field_jarak = parameters[5].valueAsText

            if not field_existing:

                raise arcpy.ExecuteError(
                    "Field existing belum dipilih"
                )

            if not fasilitas_path:

                raise arcpy.ExecuteError(
                    "Feature class fasilitas tidak valid"
                )

            nama_fasilitas = field_existing[2:]

            # Copy fasilitas
            self.copy_fasilitas(
                fasilitas_path,
                dataset_path,
                nama_fasilitas,
                messages
            )

            # Transfer nilai
            self.transfer_centroid(
                nbt_sebelumnya_path,
                persil_path,
                field_jarak,
                field_existing,
                messages
            )

        # =====================================================
        # MODE TAMBAH FASILITAS BARU
        # =====================================================

        elif mode_input == "Tambah Fasilitas Baru":

            fasilitas_path = parameters[3].valueAsText

            nama_fasilitas = parameters[4].valueAsText

            if not fasilitas_path:

                raise arcpy.ExecuteError(
                    "Feature class fasilitas tidak valid"
                )

            if not nama_fasilitas:

                raise arcpy.ExecuteError(
                    "Nama fasilitas belum diisi"
                )

            nama_fasilitas = nama_fasilitas.upper()

            field_fasilitas = f"JK{nama_fasilitas}"

            # Copy fasilitas
            output_fc = self.copy_fasilitas(
                fasilitas_path,
                dataset_path,
                nama_fasilitas,
                messages
            )

            existing_fields = [
                field.name
                for field in arcpy.ListFields(
                    persil_path
                )
            ]

            if field_fasilitas not in existing_fields:

                arcpy.management.AddField(
                    persil_path,
                    field_fasilitas,
                    "DOUBLE"
                )

            mapping_fasilitas = configs[
                "fasilitas_config"
            ].get(
                "mapping_fasilitas",
                {}
            )

            mapping_fasilitas[field_fasilitas] = {
                "nama_fasilitas": nama_fasilitas,
                "file_path": output_fc
            }

            configs[
                "fasilitas_config"
            ]["mapping_fasilitas"] = mapping_fasilitas

            persil.set_config_values(
                configs
            )

            arcpy.management.MakeFeatureLayer(
                output_fc,
                nama_fasilitas
            )

            arcpy.SetParameter(
                6,
                nama_fasilitas
            )

            messages.addMessage(
                f"== Fasilitas {nama_fasilitas} berhasil ditambahkan =="
            )

        # =====================================================
        # MODE TAMBAH FASILITAS DARI NBT SEBELUMNYA
        # =====================================================

        elif mode_input == "Tambah Fasilitas dari NBT Sebelumnya":

            nbt_sebelumnya_path = parameters[1].valueAsText

            fasilitas_path = parameters[3].valueAsText

            nama_fasilitas = parameters[4].valueAsText

            field_jarak = parameters[5].valueAsText

            if not nbt_sebelumnya_path:

                raise arcpy.ExecuteError(
                    "NBT sebelumnya belum dipilih"
                )

            if not fasilitas_path:

                raise arcpy.ExecuteError(
                    "Feature class fasilitas tidak valid"
                )

            if not nama_fasilitas:

                raise arcpy.ExecuteError(
                    "Nama fasilitas belum diisi"
                )

            nama_fasilitas = nama_fasilitas.upper()

            field_fasilitas = f"JK{nama_fasilitas}"

            # Copy fasilitas
            output_fc = self.copy_fasilitas(
                fasilitas_path,
                dataset_path,
                nama_fasilitas,
                messages
            )

            existing_fields = [
                field.name
                for field in arcpy.ListFields(
                    persil_path
                )
            ]

            if field_fasilitas not in existing_fields:

                arcpy.management.AddField(
                    persil_path,
                    field_fasilitas,
                    "DOUBLE"
                )

            # Transfer nilai lama
            self.transfer_centroid(
                nbt_sebelumnya_path,
                persil_path,
                field_jarak,
                field_fasilitas,
                messages
            )

            mapping_fasilitas = configs[
                "fasilitas_config"
            ].get(
                "mapping_fasilitas",
                {}
            )

            mapping_fasilitas[field_fasilitas] = {
                "nama_fasilitas": nama_fasilitas,
                "file_path": output_fc
            }

            configs[
                "fasilitas_config"
            ]["mapping_fasilitas"] = mapping_fasilitas

            persil.set_config_values(
                configs
            )

            arcpy.management.MakeFeatureLayer(
                output_fc,
                nama_fasilitas
            )

            arcpy.SetParameter(
                6,
                nama_fasilitas
            )

            messages.addMessage(
                f"== Fasilitas {nama_fasilitas} berhasil ditambahkan dari NBT sebelumnya =="
            )

        messages.addMessage(
            "== Proses selesai =="
        )

        return

class Masukkan_Data_Risiko(object):

    def __init__(self):

        self.label = "Masukkan Data Risiko"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):


        mode_input = arcpy.Parameter(
            displayName="Mode Input",
            name="mode_input",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )

        mode_input.filter.type = "ValueList"
        mode_input.filter.list = [
            "Risiko Standar",
            "Risiko Tambahan"
        ]
        mode_input.value = "Risiko Standar"

        nbt_sebelumnya_path = arcpy.Parameter(
            displayName="Data NBT Sebelumnya",
            name="nbt_sebelumnya_path",
            datatype="DEFeatureClass",
            parameterType="Optional",
            direction="Input"
        )

        existing_field = arcpy.Parameter(
            displayName="Field Risiko Standar",
            name="existing_field",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )

        existing_field.filter.type = "ValueList"
        existing_field.filter.list = [
            "BANJIR",
            "LONGSOR",
        ]

        risiko_path = arcpy.Parameter(
            displayName="Data Risiko (Feature Class)",
            name="risiko_path",
            datatype="DEFeatureClass",
            parameterType="Optional",
            direction="Input"
        )


        nama_risiko = arcpy.Parameter(
            displayName="Nama Risiko Tambahan",
            name="nama_risiko",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )


        idbidang_field = arcpy.Parameter(
            displayName="Field IDBidang",
            name="idbidang_field",
            datatype="Field",
            parameterType="Optional",
            direction="Input"
        )
        idbidang_field.parameterDependencies = [nbt_sebelumnya_path.name]


        jarak_field = arcpy.Parameter(
            displayName="Field Penilaian Risiko",
            name="jarak_field",
            datatype="Field",
            parameterType="Optional",
            direction="Input"
        )
        jarak_field.parameterDependencies = [nbt_sebelumnya_path.name]

        output_layer = arcpy.Parameter(
            displayName="Output Risiko",
            name="output_layer",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [
            mode_input,
            nbt_sebelumnya_path,
            existing_field,
            risiko_path,
            nama_risiko,
            idbidang_field,
            jarak_field,
            output_layer
        ]


    def isLicensed(self):
        return True


    def updateParameters(self, parameters):

        mode_input = parameters[0].valueAsText

        if mode_input == "Risiko Standar":

            # nbt sebelumnya
            parameters[1].enabled = True

            # field existing
            parameters[2].enabled = True

            # fasilitas baru
            parameters[3].enabled = True
            parameters[4].enabled = False

            # field nbt
            parameters[5].enabled = True
            parameters[6].enabled = True

        # =================================================
        # MODE TAMBAH FASILITAS BARU
        # =================================================

        elif mode_input == "Risiko Tambahan":

            # nbt sebelumnya
            parameters[1].enabled = False

            # field existing
            parameters[2].enabled = False

            # fasilitas baru
            parameters[3].enabled = True
            parameters[4].enabled = True

            # field nbt
            parameters[5].enabled = False
            parameters[6].enabled = False

        return
    
    def updateMessages(self, parameters):

        mode_input = parameters[0].valueAsText

        nama_fasilitas = parameters[4].valueAsText

        if mode_input == "Risiko Tambahan":

            if nama_fasilitas:

                if len(nama_fasilitas) > 8:

                    parameters[4].setErrorMessage(
                        "Nama fasilitas maksimal 8 huruf"
                    )

        return
    
    def execute(self, parameters, messages):

        messages.addMessage("== Proses dimulai ==")

        mode_input = parameters[0].valueAsText

        configs = persil.get_config_values()

        persil_path = os.path.join(
            configs["project_config"]["dataset_path"],
            "Persil_Layer"
        )

        #  Mode NBT Sebelumnya

        if mode_input == "Risiko Standar":

            nbt_sebelumnya_path = parameters[1].valueAsText

            field_existing = parameters[2].valueAsText

            field_idbidang = parameters[5].valueAsText

            field_jarak = parameters[6].valueAsText

            risiko_path = parameters[3].valueAsText

            if not field_existing:
                raise arcpy.ExecuteError(
                    "Field existing belum dipilih"
                )
            
            if not risiko_path:
                raise arcpy.ExecuteError(
                    "Feature class Risiko tidak valid"
                )


            nama_risiko = field_existing
            gdb_path = configs["project_config"]["gdb_path"]

            dataset_path = os.path.join(gdb_path, 'resiko')
            persil_ds_path = configs["project_config"]["dataset_path"]
            persil_path = os.path.join(persil_ds_path, 'Persil_Layer')

            # Membuat Dataset Risiko

            if not arcpy.Exists(dataset_path):
                messages.addMessage( "== Membuat dataset risiko ==" )
                spatial_ref = arcpy.Describe(persil_path).spatialReference
                arcpy.management.CreateFeatureDataset(
                    gdb_path,
                    os.path.basename(dataset_path),
                    spatial_ref
                )

            output_fc = os.path.join( dataset_path,  nama_risiko )

            if arcpy.Exists(output_fc):
                arcpy.management.Delete(output_fc)

            arcpy.conversion.FeatureClassToFeatureClass(
                risiko_path,
                dataset_path,
                nama_risiko
            )

            messages.addMessage(
                f"== Copy nilai {field_jarak} ke {field_existing} =="
            )

            data_dict = {}

            with arcpy.da.SearchCursor(
                nbt_sebelumnya_path,
                [field_idbidang, field_jarak]
            ) as cursor:

                for row in cursor:

                    data_dict[row[0]] = row[1]

            updated = 0

            with arcpy.da.UpdateCursor(
                persil_path,
                [field_idbidang, field_existing]
            ) as cursor:

                for row in cursor:

                    idbidang = row[0]

                    if idbidang in data_dict:

                        row[1] = data_dict[idbidang]
                        cursor.updateRow(row)

                        updated += 1

            messages.addMessage(
                f"== {updated} bidang berhasil diupdate =="
            )

        # Mode Fasilitas Baru

        elif mode_input == "Risiko Tambahan":

            risiko_path = parameters[3].valueAsText
            nama_risiko = parameters[4].valueAsText

            if not risiko_path:
                raise arcpy.ExecuteError(
                    "Feature class fasilitas tidak valid"
                )

            if not nama_risiko:
                raise arcpy.ExecuteError(
                    "Nama Risiko belum diisi"
                )

            nama_risiko = nama_risiko.upper()

            gdb_path = configs["project_config"]["gdb_path"]
            dataset_path = os.path.join(gdb_path, 'resiko')
            persil_ds_path = configs["project_config"]["dataset_path"]
            persil_path = os.path.join(persil_ds_path, 'Persil_Layer')

            # Membuat Dataset Fasilitas

            if not arcpy.Exists(dataset_path):

                messages.addMessage(
                    "== Membuat dataset fasilitas =="
                )

                spatial_ref = arcpy.Describe(persil_ds_path).spatialReference

                arcpy.management.CreateFeatureDataset(
                    gdb_path,
                    os.path.basename(dataset_path),
                    spatial_ref
                )

            output_fc = os.path.join(
                dataset_path,
                nama_risiko
            )

            if arcpy.Exists(output_fc):
                arcpy.management.Delete(output_fc)

            arcpy.conversion.FeatureClassToFeatureClass(
                risiko_path,
                dataset_path,
                nama_risiko
            )

            existing_fields = [
                field.name
                for field in arcpy.ListFields(persil_path)
            ]

            if nama_risiko not in existing_fields:

                arcpy.management.AddField(
                    persil_path,
                    nama_risiko,
                    "DOUBLE"
                )

            mapping_fasilitas = configs["resiko_config"].get("mapping_fasilitas", {})

            mapping_fasilitas[nama_risiko] = {
                "nama_fasilitas": nama_risiko,
                "file_path": output_fc
            }

            configs[
                "fasilitas_config"
            ]["mapping_fasilitas"] = mapping_fasilitas

            persil.set_config_values(configs)

            arcpy.management.MakeFeatureLayer(
                output_fc,
                nama_risiko
            )

            arcpy.SetParameter( 7, nama_risiko )

        messages.addMessage("== Proses selesai ==")

        return


# ===========================

class Buat_Workspace_Pembaruan_NBT_OLD(object):
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
    
class Masukkan_Data_NBT_Sebelumnya_OLD(object):

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