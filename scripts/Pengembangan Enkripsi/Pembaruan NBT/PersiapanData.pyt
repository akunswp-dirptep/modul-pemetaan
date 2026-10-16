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
            penjelasan.value = (
                "Pastikan data sudah benar sebelum diupload.\n\n"
                "Direktorat Penilaian Tanah dan Ekonomi Pertanahan,\n"
                "Kementerian ATR/BPN.\n"
                "Tahun: {}\n".format(datetime.now().year))
        
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
            penjelasan.value = (
                "Pastikan data sudah benar sebelum diupload.\n\n"
                "Direktorat Penilaian Tanah dan Ekonomi Pertanahan,\n"
                "Kementerian ATR/BPN.\n"
                "Tahun: {}\n".format(datetime.now().year))
        
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

class Masukkan_Data_NBT_Sebelumnya(object):

    DEFAULT_VARIABEL = [
        ["Kelurahan", "WADMKD", ["KELURAHAN", "KEL", "WADMKD"]],
        ["Kecamatan", "WADMKC", ["KECAMATAN", "KEC", "WADMKC"]],
        ["Tipe Hak", "TIPEHAK", ["TIPEHAK"]],
        ["Lebar Depan", "LBRDPN", ["LBRDPN", "LB_DPN"]],
        ["Luas Tanah", "LUASM2", ["LUASM2", "LS_TNH"]],
        ["Skoring Zonasi", "S_ZONASI", ["S_ZONASI"]],
        ["Skoring Bentuk Persil", "S_BENTUK", ["S_BENTUK"]],
        ["Skoring Letak", "S_LETAK", ["S_LETAK"]],
        ["Skoring Elevasi", "S_ELEVASI", ["S_ELEVASI", "S_ELVASI"]],
        ["Lebar Jalan", "LBRJLN", ["LBRJLN", "LB_JLN"]],
        ["Skoring Kelas Jalan", "S_KLSJLN", ["S_KLS_JLN", "S_KLSJLN"]],
        ["Jarak Arteri Primer", "JKATRP", ["JKATRP", "JK_ATRP"]],
        ["Jarak Arteri Sekunder", "JKATRS", ["JKATRS", "JK_ATRS"]],
        ["Jarak Kolektor Primer", "JKKOLP", ["JKKOLP", "JK_KOLP"]],
        ["Jarak Kolektor Sekunder", "JKKOLS", ["JKKOLS", "JK_KOLS"]],
        ["Nilai Bidang Tanah", "NILAIBD", ["PREDICTED", "NILAIBD"]],
        ["NIB", "NIB", ["NIB"]],
        ["ID", "IDKKP", ["ID", "IDKKP"]]
    ]

    AUTO_CREATE_FIELDS = [
        ("BENTUK", "TEXT", 50), ("LETAK", "TEXT", 50), ("ELEVASI", "TEXT", 50),
        ("KLSJLN", "TEXT", 50), ("ZONASI", "TEXT", 50),
        ("JKCBD", "DOUBLE", None), ("JKKES", "DOUBLE", None), ("JKPDDKN", "DOUBLE", None),
        ("JKTRANSP", "DOUBLE", None), ("JKPMRNTH", "DOUBLE", None),
        ("IDBIDANG", "LONG", None), ("BANJIR", "SHORT", None), ("LONGSOR", "SHORT", None)
    ]

    def __init__(self):
        self.label = "Masukkan Data NBT Sebelumnya"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        nbt_awal = arcpy.Parameter(displayName="Pilih Data NBT", name="old_nbt_layer", datatype="GPFeatureLayer", parameterType="Required", direction="Input")
        daftar_variabel = arcpy.Parameter(displayName="Sesuaikan Field", name="define_variable", datatype="GPValueTable", parameterType="Required", direction="Input")
        daftar_variabel.columns = [["GPString", "Nama Variabel"], ["Field", "Field Dataset"]]
        daftar_variabel.parameterDependencies = [nbt_awal.name]
        
        gunakan_data_perubahan = arcpy.Parameter(displayName="Data Memiliki Informasi Perubahan", name="gunakan_data_perubahan", datatype="GPBoolean", parameterType="Optional", direction="Input")
        gunakan_data_perubahan.value = False
        
        field_perubahan = arcpy.Parameter(displayName="Field Status Perubahan", name="field_perubahan", datatype="Field", parameterType="Optional", direction="Input")
        field_perubahan.parameterDependencies = [nbt_awal.name]
        field_perubahan.enabled = False

        field_id_perubahan = arcpy.Parameter(displayName="Field ID", name="field_id_perubahan", datatype="Field", parameterType="Optional", direction="Input")
        field_id_perubahan.parameterDependencies = [nbt_awal.name]
        field_id_perubahan.enabled = False
        
        field_kelompok_perubahan = arcpy.Parameter(displayName="Field Kelompok Perubahan", name="field_kelompok_perubahan", datatype="Field", parameterType="Optional", direction="Input")
        field_kelompok_perubahan.parameterDependencies = [nbt_awal.name]
        field_kelompok_perubahan.enabled = False

        output_lama = arcpy.Parameter(displayName="Output Peta Lama", name="output_lama", datatype="GPFeatureLayer", parameterType="Derived", direction="Output")

        return [nbt_awal, daftar_variabel, gunakan_data_perubahan, field_perubahan, field_id_perubahan, field_kelompok_perubahan, output_lama]

    def updateParameters(self, parameters):
        gunakan_data_perubahan = parameters[2]
        is_perubahan_active = bool(gunakan_data_perubahan.value)
        
        for param in parameters[3:6]:
            param.enabled = is_perubahan_active
            if not is_perubahan_active:
                param.value = None

        nbt_layer = parameters[0].valueAsText
        daftar_variabel = parameters[1]

        if not nbt_layer:
            return

        if parameters[0].altered and not parameters[0].hasBeenValidated:
            daftar_variabel.value = None

        field_names = [f.name.upper() for f in arcpy.ListFields(nbt_layer)]

        if daftar_variabel.value is None:
            daftar_variabel.value = [[nama, self.cari_field(field_names, kandidat)] for nama, _, kandidat in self.DEFAULT_VARIABEL]

        missing_fields = [nama for nama, _, kandidat in self.DEFAULT_VARIABEL if not self.cari_field(field_names, kandidat)]
        if missing_fields:
            daftar_variabel.setErrorMessage("Field berikut belum tersedia:\n- " + "\n- ".join(missing_fields))

        spatial_ref = arcpy.Describe(nbt_layer).spatialReference
        if "DGN_1995_Indonesia_TM-3_Zone" not in spatial_ref.name:
            parameters[0].setErrorMessage("Koordinat Persil harus DGN_1995_Indonesia_TM-3")

    def execute(self, parameters, messages):
        peta_lama_input = parameters[0].valueAsText
        daftar_variabel = parameters[1].value
        field_perubahan = parameters[3].valueAsText
        field_id_perubahan = parameters[4].valueAsText
        field_kelompok_perubahan = parameters[5].valueAsText
        
        configs = persil.get_config_values()
        dataset_path = configs["project_config"]["dataset_path"]
        konfigurasi_variabel_path = configs["project_config"]["daftar_variabel_path"]

        dest_temp_path = r"in_memory\Persil_Lama"
        persil_layer = os.path.join(dataset_path, constant.LAYER_PERSIL)

        self.delete_if_exists(dest_temp_path)
        self.delete_if_exists(persil_layer)

        arcpy.management.CopyFeatures(peta_lama_input, dest_temp_path)

        mapping_field = {row[0]: row[1] for row in self.DEFAULT_VARIABEL}
        rename_fields = {}
        daftar_variabel_python = []

        for row in daftar_variabel or []:
            if len(row) >= 2 and row[1]:
                nama_var, field_ds = str(row[0]).strip(), str(row[1]).strip()
                daftar_variabel_python.append([nama_var, field_ds])
                if nama_var in mapping_field:
                    rename_fields[field_ds] = mapping_field[nama_var]

        with open(konfigurasi_variabel_path, "w") as conf_file:
            json.dump({"daftar_variabel": daftar_variabel_python}, conf_file, indent=4)

        existing_fields_upper = {f.name.upper(): f.name for f in arcpy.ListFields(dest_temp_path)}
        for old_field, new_field in rename_fields.items():
            old_upper, new_upper = old_field.upper(), new_field.upper()
            if old_upper != new_upper and old_upper in existing_fields_upper and new_upper not in existing_fields_upper:
                arcpy.management.AlterField(dest_temp_path, existing_fields_upper[old_upper], new_field, new_field)
                existing_fields_upper[new_upper] = new_field # Update tracker

        arcpy.management.AddField(dest_temp_path, "NILAIBD_LAMA", "DOUBLE", field_alias="NILAIBD LAMA")
        if "NILAIBD" in existing_fields_upper.values():
            arcpy.management.CalculateField(dest_temp_path, "NILAIBD_LAMA", "!NILAIBD!", "PYTHON3")
            arcpy.management.CalculateField(dest_temp_path, "NILAIBD", "None", "PYTHON3")

        # TAMBAHAN: Konversi semua field skoring (S_) menjadi Long (Integer) jika belum
        skoring_fields = [f.name for f in arcpy.ListFields(dest_temp_path) if f.name.upper().startswith("S_")]
        for sf in skoring_fields:
            f_obj = arcpy.ListFields(dest_temp_path, sf)[0]
            if f_obj.type.upper() not in ['INTEGER', 'SMALLINTEGER']:
                temp_sf = sf + "_TMP"
                arcpy.management.AddField(dest_temp_path, temp_sf, "LONG")
                expression = f"int(!{sf}!) if !{sf}! is not None else None"
                arcpy.management.CalculateField(dest_temp_path, temp_sf, expression, "PYTHON3")
                arcpy.management.DeleteField(dest_temp_path, sf)
                arcpy.management.AddField(dest_temp_path, sf, "LONG", field_alias=f_obj.aliasName or sf)
                arcpy.management.CalculateField(dest_temp_path, sf, f"!{temp_sf}!", "PYTHON3")
                arcpy.management.DeleteField(dest_temp_path, temp_sf)

        # UPDATE: Tambahkan NILAIBD_LAMA ke protected_fields
        protected_fields = {"FID", "OBJECTID", "SHAPE", "WADMKD", "WADMKC", "TIPEHAK", "LBRDPN", "LUASM2", "S_ZONASI", "S_BENTUK", "S_LETAK", "S_ELEVASI", "LBRJLN", "S_KLSJLN", "JKATRP", "JKATRS", "JKKOLP", "JKKOLS", "NILAIBD", "NILAIBD_LAMA", "NIB", "IDBIDANG", "IDKKP"}
        for f in [field_perubahan, field_id_perubahan, field_kelompok_perubahan]:
            if f: protected_fields.add(f.upper())
            
        # TAMBAHAN: Definisi field sistem default geodatabase yang harus dilindungi secara eksplisit
        system_shape_fields = {"SHAPE", "SHAPE_LENGTH", "SHAPE_AREA"}
            
        # PERBAIKAN: Ganti aturan ("SHAPE" not in f.name.upper()) menjadi proteksi spesifik
        fields_to_delete = [
            f.name for f in arcpy.ListFields(dest_temp_path) 
            if f.type not in ["Geometry", "OID"] 
            and f.name.upper() not in protected_fields 
            and f.name.upper() not in system_shape_fields
        ]
        
        if fields_to_delete:
            try: arcpy.management.DeleteField(dest_temp_path, fields_to_delete)
            except Exception as e: arcpy.AddWarning(str(e))

        existing_field_names = [f.name.upper() for f in arcpy.ListFields(dest_temp_path)]
        for f_name, f_type, f_len in self.AUTO_CREATE_FIELDS:
            if f_name.upper() not in existing_field_names:
                arcpy.management.AddField(dest_temp_path, f_name, f_type, field_length=f_len, field_alias=f_name)
                if f_type.upper() in ["SHORT", "LONG", "DOUBLE", "FLOAT"]:
                    arcpy.management.CalculateField(dest_temp_path, f_name, 0, "PYTHON3")

        field_from_project = [
            ['WADMPR', 'TEXT', configs['project_config']['provinsi'], 'WADMPR'],
            ['WADMKK', 'TEXT', configs['project_config']['kab_kota'], 'WADMKK'],
            ['THNNILAI', 'SHORT', configs['project_config']['tahun_penilaian'], 'THNNILAI'],
            ['KLSTRZ', 'SHORT', 1, 'KLASTER ZONASI']
        ]
        for f_name, f_type, f_val, f_alias in field_from_project:
            if f_name.upper() not in existing_field_names:
                arcpy.management.AddField(dest_temp_path, f_name, f_type, field_alias=f_alias)
            arcpy.management.CalculateField(dest_temp_path, f_name, repr(f_val), "PYTHON3")

        if "PERUBAHAN" not in existing_field_names:
            arcpy.management.AddField(dest_temp_path, "perubahan", "TEXT", field_length=20, field_alias="PERUBAHAN")
        if "KELOMPOK_PERUBAHAN" not in existing_field_names:
            arcpy.management.AddField(dest_temp_path, "kelompok_perubahan", "LONG", field_length=50, field_alias="KELOMPOK PERUBAHAN")

        if field_perubahan:
            with arcpy.da.UpdateCursor(dest_temp_path, [field_perubahan, "perubahan"]) as cursor:
                for row in cursor:
                    val = str(row[0]).strip().lower() if row[0] else ""
                    row[1] = "update" if val == "berubah" else "tetap"
                    cursor.updateRow(row)

        if field_kelompok_perubahan:
            mapping_kelompok, counter = {}, 1
            with arcpy.da.UpdateCursor(dest_temp_path, [field_kelompok_perubahan, "kelompok_perubahan", "KLSTRZ"]) as cursor:
                for row in cursor:
                    nilai = row[0]
                    if not nilai:
                        row[1] = None
                    else:
                        if nilai not in mapping_kelompok:
                            mapping_kelompok[nilai] = counter
                            counter += 1
                        row[1] = mapping_kelompok[nilai]
                        row[2] = None
                    cursor.updateRow(row)
                    
        if field_id_perubahan:
            with arcpy.da.UpdateCursor(dest_temp_path, [field_id_perubahan, "IDKKP"]) as cursor:
                for row in cursor:
                    row[1] = str(row[0]) if row[0] is not None else None
                    cursor.updateRow(row)

        validation_checks = [
            ("S_ELEVASI", constant.SKORING_ELEVASI, "Skoring Elevasi"),
            ("S_ZONASI", constant.SKORING_ZONASI, "Skoring Zonasi"),
            ("S_LETAK", constant.SKORING_LETAK, "Skoring Letak"),
            ("S_BENTUK", constant.SKORING_BENTUK_PERSIL, "Skoring Bentuk Persil"),
            ("S_KLSJLN", constant.SKORING_KELAS_JALAN["kelas_jalan"], "Skoring Kelas Jalan")
        ]
        
        validation_errors = []
        for f_name, f_dict, f_label in validation_checks:
            validation_errors.extend(self.validate_skoring(dest_temp_path, f_name, f_dict, f_label))
            
        if validation_errors:
            raise Exception("\n".join(validation_errors))

        rev_maps = {
            "S_BENTUK": {v: k for k, v in constant.SKORING_BENTUK_PERSIL.items()},
            "S_LETAK": {v: k for k, v in constant.SKORING_LETAK.items()},
            "S_ELEVASI": {v: k for k, v in constant.SKORING_ELEVASI.items()},
            "S_KLSJLN": {v: k for k, v in constant.SKORING_KELAS_JALAN["kelas_jalan"].items()},
            "S_ZONASI": {v: k for k, v in constant.SKORING_ZONASI.items()}
        }

        with arcpy.da.UpdateCursor(dest_temp_path, ["S_BENTUK", "BENTUK", "S_LETAK", "LETAK", "S_ELEVASI", "ELEVASI", "S_KLSJLN", "KLSJLN", "S_ZONASI", "ZONASI"]) as cursor:
            for row in cursor:
                row[1] = rev_maps["S_BENTUK"].get(row[0])
                row[3] = rev_maps["S_LETAK"].get(row[2])
                row[5] = rev_maps["S_ELEVASI"].get(row[4])
                row[7] = rev_maps["S_KLSJLN"].get(row[6])
                row[9] = rev_maps["S_ZONASI"].get(row[8])
                cursor.updateRow(row)

        # UPDATE: Tambahkan NILAIBD_LAMA ke ordered_fields
        ordered_fields = [
            "IDKKP", "NIB", "IDBIDANG", "perubahan", "kelompok_perubahan",
            "WADMPR", "WADMKK", "WADMKC", "WADMKD", "TIPEHAK",
            "LUASM2", "LBRDPN", "ZONASI", "KLSTRZ", "S_ZONASI",
            "KLSJLN", "S_KLSJLN", "LETAK", "S_LETAK", "BENTUK", "S_BENTUK", 
            "ELEVASI", "S_ELEVASI", "LBRJLN", "JKATRP", "JKATRS", "JKKOLP", 
            "JKKOLS", "JKCBD", "JKKES", "JKPDDKN", "JKTRANSP", "JKPMRNTH",
            "BANJIR", "LONGSOR", "NILAIBD", "NILAIBD_LAMA", "THNNILAI"
        ]

        self.reorder_fields(dest_temp_path, persil_layer, ordered_fields)

        with arcpy.da.UpdateCursor(persil_layer, ["OBJECTID", "IDBIDANG"], sql_clause=(None, "ORDER BY OBJECTID")) as cursor:
            for nomor, row in enumerate(cursor, start=1):
                row[1] = nomor
                cursor.updateRow(row)

        arcpy.SetParameter(6, persil_layer)
        return
    
    def validate_skoring(self, layer_path, field_name, skor_dict, field_label):
        if not field_name: return []
        errors = []
        nilai_maksimum, nilai_minimum = max(skor_dict.values()), min(skor_dict.values())

        with arcpy.da.SearchCursor(layer_path, [field_name]) as cursor:
            for idx, row in enumerate(cursor, start=1):
                value = row[0]
                if value is None:
                    errors.append(f"{field_label} baris {idx} NULL")
                    continue
                if not isinstance(value, (int, float)):
                    errors.append(f"{field_label} baris {idx} bukan angka")
                    continue
                if isinstance(value, float) and not value.is_integer():
                    errors.append(f"{field_label} baris {idx} harus berupa bilangan bulat")
                    continue
                
                value = int(value)
                if not (nilai_minimum <= value <= nilai_maksimum):
                    errors.append(f"{field_label} baris {idx} nilainya tidak dalam rentang {nilai_minimum} - {nilai_maksimum}")
        return errors

    def cari_field(self, field_names, kandidat):
        for nama in kandidat:
            if nama.upper() in field_names: return nama
        return None

    def delete_if_exists(self, path):
        if arcpy.Exists(path):
            try: arcpy.management.Delete(path)
            except Exception as e: arcpy.AddWarning(f"Gagal menghapus {path}: {e}")
                
    def reorder_fields(self, input_fc, output_fc, ordered_fields):
        existing_fields = arcpy.ListFields(input_fc)
        keep_fields_name = {'perubahan' : 'PERUBAHAN', 'kelompok_perubahan' : 'KELOMPOK PERUBAHAN'}

        existing_field_names_dict = {f.name.upper(): f.name for f in existing_fields if f.type not in ["OID", "Geometry"]}
        ordered_upper = [f.upper() for f in ordered_fields]
        
        ordered_existing = [existing_field_names_dict[f] for f in ordered_upper if f in existing_field_names_dict]
        remaining_fields = [f.name for f in existing_fields if f.type not in ["OID", "Geometry"] and f.name.upper() not in ordered_upper]

        final_fields = ordered_existing + remaining_fields
        field_mappings = arcpy.FieldMappings()

        for field_name in final_fields:
            field_map = arcpy.FieldMap()
            field_map.addInputField(input_fc, field_name)
            output_field = field_map.outputField
            
            if field_name.lower() in keep_fields_name:
                output_field.name = field_name
                output_field.aliasName = keep_fields_name[field_name.lower()]
            else:
                output_field.name = field_name.upper()
                output_field.aliasName = field_name.upper()

            field_map.outputField = output_field
            field_mappings.addFieldMap(field_map)

        arcpy.conversion.FeatureClassToFeatureClass(input_fc, os.path.dirname(output_fc), os.path.basename(output_fc), field_mapping=field_mappings)

class Masukkan_Data_Jaringan_Jalan(object):

    def __init__(self):
        self.label = "Masukkan Data Jaringan Jalan"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):

        jaringan_jalan=arcpy.Parameter(
            displayName="Jaringan Jalan (Feature Layer)",
            name="jaringan_jalan",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )

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
        jaringan_jalan_path=os.path.join(dataset_path, 'Jaringan_Jalan')
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

        if arcpy.Exists(topologi_jaringan_jalan_path):
            arcpy.management.Delete(topologi_jaringan_jalan_path)
        
        # 1. Copy data ke in_memory (sementara) agar mudah diolah
        temp_jaringan = r"in_memory\temp_jaringan_jalan"
        if arcpy.Exists(temp_jaringan):
            arcpy.management.Delete(temp_jaringan)

        arcpy.conversion.FeatureClassToFeatureClass(
            in_jaringan_jalan,
            "in_memory",
            "temp_jaringan_jalan"
        )

        # 2. Lakukan pengubahan field pada file sementara
        arcpy.management.AlterField(
            temp_jaringan,
            field_skor_jalan,
            "s_klsjln", # Di kode Anda namanya s_klsjln
            "Skor Kelas Jalan"
        )

        arcpy.management.AlterField(
            temp_jaringan,
            field_lebar_jalan,
            "lb_jln",
            "Lebar Jalan"
        )
        
        arcpy.management.AddField(
            temp_jaringan,
            "kls_jln",
            "TEXT",
            field_alias="Kelas Jalan"
        )
        
        kelas_mapping = {
            1: "Setapak", 2: "Lokal Sekunder", 3: "Lokal Primer",
            4: "Kolektor Sekunder", 5: "Kolektor Primer",
            6: "Arteri Sekunder", 7: "Arteri Primer"
        }
        
        with arcpy.da.UpdateCursor(temp_jaringan, ["s_klsjln", "kls_jln"]) as cursor:
            for row in cursor:
                skor = row[0]
                row[1] = kelas_mapping.get(skor, "Kelas Tidak Diketahui")
                cursor.updateRow(row)

        # Paksa alias kls_jln muncul
        arcpy.management.AlterField(temp_jaringan, "kls_jln", "kls_jln", "Kelas Jalan")

        # 3. Hapus field yang tidak diperlukan (termasuk status_jal sudah dihilangkan)
        required_fields = {
            "OBJECTID", "Shape", "Shape_Length", "Shape_Area",
            "s_klsjln", "lb_jln", "kls_jln"
        }

        delete_fields = [
            field.name for field in arcpy.ListFields(temp_jaringan)
            if field.type not in ["OID", "Geometry"] and field.name not in required_fields
        ]

        if delete_fields:
            arcpy.management.DeleteField(temp_jaringan, delete_fields)

        # 4. REORDER dan pindahkan ke Geodatabase utama
        if arcpy.Exists(jaringan_jalan_path):
            arcpy.management.Delete(jaringan_jalan_path)

        # Susun urutan kolom di sini
        self.reorder_fields(
            temp_jaringan, 
            jaringan_jalan_path, 
            ["kls_jln", "s_klsjln", "lb_jln"]
        )

        # Bersihkan memori
        arcpy.management.Delete(temp_jaringan)
        
        # -- PERUBAHAN SELESAI SAMPAI DI SINI --
        
        # Lanjut ke proses simbologi ...
        simbologi_path=r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Simbologi_Kelas_Jaringan_Jalan.lyrx"
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

    def reorder_fields(self, input_fc, output_fc, ordered_fields):
        existing_fields = {
            f.name.lower(): f.name 
            for f in arcpy.ListFields(input_fc) 
            if f.type not in ["OID", "Geometry"]
        }
        
        field_mappings = arcpy.FieldMappings()
        
        for field in ordered_fields:
            field_lower = field.lower()
            if field_lower in existing_fields:
                field_map = arcpy.FieldMap()
                field_map.addInputField(input_fc, existing_fields[field_lower])
                field_mappings.addFieldMap(field_map)
                
        ordered_lower = [f.lower() for f in ordered_fields]
        for field_lower, field_real in existing_fields.items():
            if field_lower not in ordered_lower:
                field_map = arcpy.FieldMap()
                field_map.addInputField(input_fc, field_real)
                field_mappings.addFieldMap(field_map)
                
        arcpy.conversion.FeatureClassToFeatureClass(
            input_fc,
            os.path.dirname(output_fc),
            os.path.basename(output_fc),
            field_mapping=field_mappings
        )

class Masukkan_Data_Fasilitas(object):
    def __init__(self):
        self.label = "Masukkan Data Fasilitas"
        self.description = "Tool untuk memasukkan data fasilitas baru atau yang sudah ada ke dalam Geodatabase NBT."
        self.canRunInBackground = False

    def getParameterInfo(self):

        mode_input = arcpy.Parameter(
            displayName="Pilih Mode Input",
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

        fasilitas_path = arcpy.Parameter(
            displayName="Feature Class Fasilitas (Point)",
            name="fasilitas_path",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input"
        )
        fasilitas_path.category = "Data Utama Fasilitas"


        keterangan = arcpy.Parameter(
            displayName="Field Keterangan Fasilitas",
            name="keterangan",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        keterangan.parameterDependencies = [fasilitas_path.name]
        keterangan.category = "Data Utama Fasilitas"

        nama_fasilitas = arcpy.Parameter(
            displayName="Nama Fasilitas Baru (Maks 8 Huruf)",
            name="nama_fasilitas",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )
        nama_fasilitas.category = "Pengaturan Fasilitas Baru"

        nbt_sebelumnya_path = arcpy.Parameter(
            displayName="Data NBT Sebelumnya",
            name="nbt_sebelumnya_path",
            datatype="DEFeatureClass",
            parameterType="Optional",
            direction="Input"
        )
        nbt_sebelumnya_path.category = "Transfer Atribut NBT Sebelumnya"

        existing_field = arcpy.Parameter(
            displayName="Pilih Fasilitas Wajib (Field Existing)",
            name="existing_field",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )
        existing_field.filter.type = "ValueList"
        existing_field.filter.list = ["JKCBD", "JKKES", "JKPDDKN", "JKTRANSP", "JKPMRNTH"]
        existing_field.category = "Transfer Atribut NBT Sebelumnya"

        jarak_field = arcpy.Parameter(
            displayName="Field Jarak Fasilitas di NBT Sebelumnya",
            name="jarak_field",
            datatype="Field",
            parameterType="Optional",
            direction="Input"
        )
        jarak_field.parameterDependencies = [nbt_sebelumnya_path.name]
        jarak_field.category = "Transfer Atribut NBT Sebelumnya"

        output_layer = arcpy.Parameter(
            displayName="Output Fasilitas Layer",
            name="output_layer",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [
            mode_input,          
            fasilitas_path,      
            keterangan,          
            nama_fasilitas,      
            nbt_sebelumnya_path, 
            existing_field,      
            jarak_field,         
            output_layer         
        ]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        mode_input = parameters[0].valueAsText
        
        if mode_input == "Fasilitas Wajib":
            parameters[3].enabled = False 
            parameters[4].enabled = True  
            parameters[5].enabled = True  
            parameters[6].enabled = True  
            
        elif mode_input == "Tambah Fasilitas Baru":
            parameters[3].enabled = True  
            parameters[4].enabled = False 
            parameters[5].enabled = False 
            parameters[6].enabled = False 
            
        elif mode_input == "Tambah Fasilitas dari NBT Sebelumnya":
            parameters[3].enabled = True  
            parameters[4].enabled = True  
            parameters[5].enabled = False 
            parameters[6].enabled = True  
        return

    def updateMessages(self, parameters):
        mode_input = parameters[0].valueAsText
        
        if mode_input in ["Tambah Fasilitas Baru", "Tambah Fasilitas dari NBT Sebelumnya"]:
            nama_fasilitas = parameters[3].valueAsText
            if nama_fasilitas and len(nama_fasilitas) > 8:
                parameters[3].setErrorMessage("Nama fasilitas maksimal 8 huruf")
        return

    def copy_fasilitas(self, fasilitas_path, dataset_path, nama_fasilitas, keterangan_field, messages):
        arcpy.env.overwriteOutput = True 
        
        output_fc = os.path.join(dataset_path, nama_fasilitas)
        
        if arcpy.Exists(output_fc):
            messages.addWarningMessage(f"Layer '{nama_fasilitas}' sudah ada, mencoba menghapus atau menimpa data yang lama...")
            try:
                arcpy.management.Delete(output_fc)
            except Exception as e:
                messages.addWarningMessage(f"Peringatan: Tidak bisa menghapus '{nama_fasilitas}' karena file sedang dikunci/dibuka di peta. Sistem akan mencoba menimpanya secara otomatis.")

        field_mappings = arcpy.FieldMappings()
        if keterangan_field:
            fm = arcpy.FieldMap()
            fm.addInputField(fasilitas_path, keterangan_field)

            out_field = fm.outputField
            out_field.name = "keterangan"
            out_field.aliasName = "Keterangan"
            fm.outputField = out_field
            
            field_mappings.addFieldMap(fm)

        arcpy.conversion.FeatureClassToFeatureClass(
            fasilitas_path,
            dataset_path,
            nama_fasilitas,
            field_mapping=field_mappings
        )
        return output_fc

    def transfer_centroid(self, source_fc, target_fc, source_field, target_field, messages, max_distance=5):
        scratch_gdb = arcpy.env.scratchGDB
        source_point = os.path.join(scratch_gdb, "tmp_source_centroid")
        target_point = os.path.join(scratch_gdb, "tmp_target_centroid")
        join_result = os.path.join(scratch_gdb, "tmp_spatial_join")

        for fc in [source_point, target_point, join_result]:
            if arcpy.Exists(fc):
                arcpy.management.Delete(fc)

        messages.addMessage("Mempersiapkan Key Penggabungan Berdasarkan Centroid")
        arcpy.management.FeatureToPoint(source_fc, source_point, "INSIDE")
        arcpy.management.FeatureToPoint(target_fc, target_point, "INSIDE")

        messages.addMessage("Mulai Memindahkan data")
        

        field_mappings = arcpy.FieldMappings()
        field_mappings.addTable(target_point)
        
        idx = field_mappings.findFieldMapIndex(target_field)
        if idx != -1:
            field_mappings.removeFieldMap(idx)
            
        field_mappings.addTable(source_point)

        arcpy.analysis.SpatialJoin(
            target_features=target_point,
            join_features=source_point,
            out_feature_class=join_result,
            join_operation="JOIN_ONE_TO_ONE",
            join_type="KEEP_ALL",
            field_mapping=field_mappings,
            match_option="CLOSEST",
            search_radius=f"{max_distance} Meters"
        )

        value_dict = {}
        with arcpy.da.SearchCursor(join_result, ["TARGET_FID", source_field]) as rows:
            for target_oid, nilai in rows:
                if nilai is None:
                    continue
                value_dict[target_oid] = nilai

        messages.addMessage(f"{len(value_dict)} pasangan ditemukan")
        updated = 0
        skipped = 0

        with arcpy.da.UpdateCursor(target_fc, ["OID@", target_field]) as rows:
            for row in rows:
                oid = row[0]
                if oid in value_dict:
                    row[1] = value_dict[oid]
                    rows.updateRow(row)
                    updated += 1
                else:
                    skipped += 1

        messages.addMessage(f"{updated} bidang berhasil diperbaharui")
        messages.addMessage(f"{skipped} bidang dilewati")

        for fc in [source_point, target_point, join_result]:
            if arcpy.Exists(fc):
                arcpy.management.Delete(fc)

    def execute(self, parameters, messages):
        messages.addMessage("Proses dimulai")
        
        mode_input = parameters[0].valueAsText
        fasilitas_path = parameters[1].valueAsText
        keterangan_field = parameters[2].valueAsText
        nama_fasilitas = parameters[3].valueAsText
        nbt_sebelumnya_path = parameters[4].valueAsText
        field_existing = parameters[5].valueAsText
        field_jarak = parameters[6].valueAsText

        configs = persil.get_config_values()
        persil_path = os.path.join(configs["project_config"]["dataset_path"], "Persil_Layer")
        dataset_path = configs["fasilitas_config"]["dataset_path"]
        gdb_path = configs["project_config"]["gdb_path"]

        if not arcpy.Exists(dataset_path):
            messages.addMessage("Membuat dataset fasilitas")
            spatial_ref = arcpy.Describe(persil_path).spatialReference
            arcpy.management.CreateFeatureDataset(gdb_path, os.path.basename(dataset_path), spatial_ref)

        output_fc = None
        layer_name = ""

        if mode_input == "Fasilitas Wajib":
            if not field_existing:
                raise arcpy.ExecuteError("Field existing belum dipilih")
            
            nama_fasilitas = field_existing[2:] 
            output_fc = self.copy_fasilitas(fasilitas_path, dataset_path, nama_fasilitas, keterangan_field, messages)
            self.transfer_centroid(nbt_sebelumnya_path, persil_path, field_jarak, field_existing, messages)
            
            layer_name = f"Fasilitas_{nama_fasilitas}"
            messages.addMessage(f"Fasilitas Wajib {nama_fasilitas} berhasil diproses")

        elif mode_input == "Tambah Fasilitas Baru":
            if not nama_fasilitas:
                raise arcpy.ExecuteError("Nama fasilitas belum diisi")

            nama_fasilitas = nama_fasilitas.upper()
            field_fasilitas = f"JK{nama_fasilitas}"
            output_fc = self.copy_fasilitas(fasilitas_path, dataset_path, nama_fasilitas, keterangan_field, messages)

            existing_fields = [field.name for field in arcpy.ListFields(persil_path)]
            if field_fasilitas not in existing_fields:
                arcpy.management.AddField(persil_path, field_fasilitas, "DOUBLE")

            mapping_fasilitas = configs["fasilitas_config"].get("mapping_fasilitas", {})
            mapping_fasilitas[field_fasilitas] = {
                "nama_fasilitas": nama_fasilitas,
                "file_path": output_fc
            }
            configs["fasilitas_config"]["mapping_fasilitas"] = mapping_fasilitas
            persil.set_config_values(configs)

            layer_name = f"Fasilitas_{nama_fasilitas}"
            messages.addMessage(f"Fasilitas Baru {nama_fasilitas} berhasil ditambahkan")

        elif mode_input == "Tambah Fasilitas dari NBT Sebelumnya":
            if not nbt_sebelumnya_path:
                raise arcpy.ExecuteError("NBT sebelumnya belum dipilih")
            if not nama_fasilitas:
                raise arcpy.ExecuteError("Nama fasilitas belum diisi")

            nama_fasilitas = nama_fasilitas.upper()
            field_fasilitas = f"JK{nama_fasilitas}"
            output_fc = self.copy_fasilitas(fasilitas_path, dataset_path, nama_fasilitas, keterangan_field, messages)

            existing_fields = [field.name for field in arcpy.ListFields(persil_path)]
            if field_fasilitas not in existing_fields:
                arcpy.management.AddField(persil_path, field_fasilitas, "DOUBLE")

            self.transfer_centroid(nbt_sebelumnya_path, persil_path, field_jarak, field_fasilitas, messages)

            mapping_fasilitas = configs["fasilitas_config"].get("mapping_fasilitas", {})
            mapping_fasilitas[field_fasilitas] = {
                "nama_fasilitas": nama_fasilitas,
                "file_path": output_fc
            }
            configs["fasilitas_config"]["mapping_fasilitas"] = mapping_fasilitas
            persil.set_config_values(configs)

            layer_name = f"Fasilitas_{nama_fasilitas}"
            messages.addMessage(f"Fasilitas {nama_fasilitas} berhasil ditambahkan dari NBT sebelumnya")

        if output_fc and arcpy.Exists(output_fc):
            symbology_mapping = {
                'CBD' : r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Fasilitas_CBD.lyrx",
                'KES' : r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Fasilitas_KES.lyrx",
                'PDDKN' : r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Fasilitas_PDDKN.lyrx",
                'PMRNTH' : r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Fasilitas_PMRNTH.lyrx",
                'TRANSP' : r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Fasilitas_TRANSP.lyrx",
            }
            simbology_file = symbology_mapping.get(nama_fasilitas, r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Fasilitas_LAINNYA.lyrx")

            arcpy.management.MakeFeatureLayer(output_fc, layer_name)
            arcpy.management.ApplySymbologyFromLayer(layer_name, simbology_file)
            
            arcpy.SetParameter(7, layer_name)
            messages.addMessage(f"Layer '{layer_name}' ditambahkan ke map")

        messages.addMessage("Proses selesai")
        return
    
class Masukkan_Data_Risiko(object):

    def __init__(self):

        self.label = "Masukkan Data Risiko"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):


        mode_input = arcpy.Parameter(
            displayName="Pilih Mode Input",
            name="mode_input",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        mode_input.filter.type = "ValueList"
        mode_input.filter.list = [
            "Risiko Wajib",
            "Tambah Risiko Baru",
            "Tambah Risiko dari NBT Sebelumnya"
        ]
        mode_input.value = "Risiko Wajib"

        risiko_path = arcpy.Parameter(
            displayName="Feature Class Risiko (Polygon)",
            name="Risiko_path",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input"
        )
        risiko_path.category = "Data Utama Risiko"


        keterangan = arcpy.Parameter(
            displayName="Field Keterangan Fasilitas",
            name="keterangan",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        keterangan.parameterDependencies = [risiko_path.name]
        keterangan.category = "Data Utama Risiko"

        nama_risiko = arcpy.Parameter(
            displayName="Nama Risiko Baru (Maks 10 Huruf)",
            name="nama_Risiko",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )
        nama_risiko.category = "Pengaturan Risiko Baru"

        nbt_sebelumnya_path = arcpy.Parameter(
            displayName="Data NBT Sebelumnya",
            name="nbt_sebelumnya_path",
            datatype="DEFeatureClass",
            parameterType="Optional",
            direction="Input"
        )
        nbt_sebelumnya_path.category = "Transfer Atribut NBT Sebelumnya"

        existing_field = arcpy.Parameter(
            displayName="Pilih Risiko Wajib (Field Existing)",
            name="existing_field",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )
        existing_field.filter.type = "ValueList"
        existing_field.filter.list = ["BANJIR", "LONGSOR"]
        existing_field.category = "Transfer Atribut NBT Sebelumnya"

        skor_risiko = arcpy.Parameter(
            displayName="Field Skor Risiko di NBT Sebelumnya",
            name="skor_Risiko",
            datatype="Field",
            parameterType="Optional",
            direction="Input"
        )
        skor_risiko.parameterDependencies = [nbt_sebelumnya_path.name]
        skor_risiko.category = "Transfer Atribut NBT Sebelumnya"

        output_layer = arcpy.Parameter(
            displayName="Output Risiko Layer",
            name="output_layer",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [
            mode_input,          
            risiko_path,      
            keterangan,          
            nama_risiko,      
            nbt_sebelumnya_path, 
            existing_field,      
            skor_risiko,         
            output_layer         
        ]



    def isLicensed(self):
        return True


    def updateParameters(self, parameters):

        mode_input = parameters[0].valueAsText
        
        if mode_input == "Risiko Wajib":
            parameters[3].enabled = False 
            parameters[4].enabled = True  
            parameters[5].enabled = True  
            parameters[6].enabled = True  
            
        elif mode_input == "Tambah Risiko Baru":
            parameters[3].enabled = True  
            parameters[4].enabled = False 
            parameters[5].enabled = False 
            parameters[6].enabled = False 
            
        elif mode_input == "Tambah Risiko dari NBT Sebelumnya":
            parameters[3].enabled = True  
            parameters[4].enabled = True  
            parameters[5].enabled = False 
            parameters[6].enabled = True  
        return
    
    def updateMessages(self, parameters):

        mode_input = parameters[0].valueAsText
        
        if mode_input in ["Tambah Risiko Baru", "Tambah Risiko dari NBT Sebelumnya"]:
            nama_risiko = parameters[3].valueAsText
            if nama_risiko and len(nama_risiko) > 10:
                parameters[3].setErrorMessage("Nama risiko maksimal 10 huruf")
        return

    def copy_risiko(self, risiko_path, dataset_path, nama_risiko, keterangan_field, messages):
        arcpy.env.overwriteOutput = True 
        
        output_fc = os.path.join(dataset_path, nama_risiko)
        
        if arcpy.Exists(output_fc):
            messages.addWarningMessage(f"Layer '{nama_risiko}' sudah ada, mencoba menghapus atau menimpa data yang lama...")
            try:
                arcpy.management.Delete(output_fc)
            except Exception as e:
                messages.addWarningMessage(f"Peringatan: Tidak bisa menghapus '{nama_risiko}' karena file sedang dikunci/dibuka di peta. Sistem akan mencoba menimpanya secara otomatis.")

        field_mappings = arcpy.FieldMappings()
        if keterangan_field:
            fm = arcpy.FieldMap()
            fm.addInputField(risiko_path, keterangan_field)

            out_field = fm.outputField
            out_field.name = "keterangan"
            out_field.aliasName = "Keterangan"
            fm.outputField = out_field
            
            field_mappings.addFieldMap(fm)

        arcpy.conversion.FeatureClassToFeatureClass(
            risiko_path,
            dataset_path,
            nama_risiko,
            field_mapping=field_mappings
        )
        return output_fc

    def transfer_centroid(self, source_fc, target_fc, source_field, target_field, messages, max_distance=5):
        scratch_gdb = arcpy.env.scratchGDB
        source_point = os.path.join(scratch_gdb, "tmp_source_centroid")
        target_point = os.path.join(scratch_gdb, "tmp_target_centroid")
        join_result = os.path.join(scratch_gdb, "tmp_spatial_join")

        for fc in [source_point, target_point, join_result]:
            if arcpy.Exists(fc):
                arcpy.management.Delete(fc)

        messages.addMessage("Mempersiapkan Key Penggabungan Berdasarkan Centroid")
        arcpy.management.FeatureToPoint(source_fc, source_point, "INSIDE")
        arcpy.management.FeatureToPoint(target_fc, target_point, "INSIDE")

        messages.addMessage("Mulai Memindahkan data")
        

        field_mappings = arcpy.FieldMappings()
        field_mappings.addTable(target_point)
        
        idx = field_mappings.findFieldMapIndex(target_field)
        if idx != -1:
            field_mappings.removeFieldMap(idx)
            
        field_mappings.addTable(source_point)

        arcpy.analysis.SpatialJoin(
            target_features=target_point,
            join_features=source_point,
            out_feature_class=join_result,
            join_operation="JOIN_ONE_TO_ONE",
            join_type="KEEP_ALL",
            field_mapping=field_mappings,
            match_option="CLOSEST",
            search_radius=f"{max_distance} Meters"
        )

        value_dict = {}
        with arcpy.da.SearchCursor(join_result, ["TARGET_FID", source_field]) as rows:
            for target_oid, nilai in rows:
                if nilai is None:
                    continue
                value_dict[target_oid] = nilai

        messages.addMessage(f"{len(value_dict)} pasangan ditemukan")
        updated = 0
        skipped = 0

        with arcpy.da.UpdateCursor(target_fc, ["OID@", target_field]) as rows:
            for row in rows:
                oid = row[0]
                if oid in value_dict:
                    row[1] = value_dict[oid]
                    rows.updateRow(row)
                    updated += 1
                else:
                    skipped += 1

        messages.addMessage(f"{updated} bidang berhasil diperbaharui")
        messages.addMessage(f"{skipped} bidang dilewati")

        for fc in [source_point, target_point, join_result]:
            if arcpy.Exists(fc):
                arcpy.management.Delete(fc)

    def execute(self, parameters, messages):

        mode_input = parameters[0].valueAsText
        risiko_path = parameters[1].valueAsText
        keterangan_field = parameters[2].valueAsText
        nama_risiko = parameters[3].valueAsText
        nbt_sebelumnya_path = parameters[4].valueAsText
        field_existing = parameters[5].valueAsText
        field_skor = parameters[6].valueAsText

        configs = persil.get_config_values()
        persil_path = os.path.join(configs["project_config"]["dataset_path"], "Persil_Layer")
        dataset_path = configs["risiko_config"]["dataset_path"]
        gdb_path = configs["project_config"]["gdb_path"]

        if not arcpy.Exists(dataset_path):
            messages.addMessage("Membuat dataset risiko")
            spatial_ref = arcpy.Describe(persil_path).spatialReference
            arcpy.management.CreateFeatureDataset(gdb_path, os.path.basename(dataset_path), spatial_ref)

        output_fc = None
        layer_name = ""

        if mode_input == "Risiko Wajib":
            if not field_existing:
                raise arcpy.ExecuteError("Field existing belum dipilih")
            
            output_fc = self.copy_risiko(risiko_path, dataset_path, field_existing , keterangan_field, messages)
            self.transfer_centroid(nbt_sebelumnya_path, persil_path, field_skor, field_existing, messages)
            nama_risiko = field_existing
            layer_name = f"Risiko_{field_existing}"
            messages.addMessage(f"Risiko Wajib {field_existing } berhasil diproses")

        elif mode_input == "Tambah Risiko Baru":
            if not nama_risiko:
                raise arcpy.ExecuteError("Nama risiko belum diisi")

            nama_risiko = nama_risiko.upper()
            output_fc = self.copy_risiko(risiko_path, dataset_path, nama_risiko, keterangan_field, messages)

            existing_fields = [field.name for field in arcpy.ListFields(persil_path)]
            if nama_risiko not in existing_fields:
                arcpy.management.AddField(persil_path, nama_risiko, "SHORT")

            mapping_risiko = configs["risiko_config"].get("mapping_risiko", {})
            mapping_risiko[nama_risiko] = {
                "nama_risiko": nama_risiko,
                "file_path": output_fc
            }
            configs["risiko_config"]["mapping_risiko"] = mapping_risiko
            persil.set_config_values(configs)

            layer_name = f"Risiko_{nama_risiko}"
            messages.addMessage(f"Risiko Baru {nama_risiko} berhasil ditambahkan")

        elif mode_input == "Tambah Risiko dari NBT Sebelumnya":
            if not nbt_sebelumnya_path:
                raise arcpy.ExecuteError("NBT sebelumnya belum dipilih")
            if not nama_risiko:
                raise arcpy.ExecuteError("Nama risiko belum diisi")

            nama_risiko = nama_risiko.upper()
            field_risiko = f"{nama_risiko}"
            output_fc = self.copy_risiko(risiko_path, dataset_path, nama_risiko, keterangan_field, messages)

            existing_fields = [field.name for field in arcpy.ListFields(persil_path)]
            if field_risiko not in existing_fields:
                arcpy.management.AddField(persil_path, field_risiko, "SHORT")

            self.transfer_centroid(nbt_sebelumnya_path, persil_path, field_skor, field_risiko, messages)

            mapping_risiko = configs["risiko_config"].get("mapping_risiko", {})
            mapping_risiko[field_risiko] = {
                "nama_risiko": nama_risiko,
                "file_path": output_fc
            }
            configs["risiko_config"]["mapping_risiiko"] = mapping_risiko
            persil.set_config_values(configs)

            layer_name = f"Risiko_{nama_risiko}"
            messages.addMessage(f"Risiko {nama_risiko} berhasil ditambahkan dari NBT sebelumnya")

        if output_fc and arcpy.Exists(output_fc):
            symbology_mapping = {
                'BANJIR' : r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Risiko_BANJIR.lyrx",
                'LONGSOR' : r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Risiko_LONGSOR.lyrx",
            }
            arcpy.AddMessage(nama_risiko)
            simbology_file = symbology_mapping.get(nama_risiko, r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Risiko_LAINNYA.lyrx")

            arcpy.management.MakeFeatureLayer(output_fc, layer_name)
            arcpy.management.ApplySymbologyFromLayer(layer_name, simbology_file)
            
            arcpy.SetParameter(7, layer_name)
            messages.addMessage(f"Layer '{layer_name}' ditambahkan ke map")

        messages.addMessage("Proses selesai")

        return