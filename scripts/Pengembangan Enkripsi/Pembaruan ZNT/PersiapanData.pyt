from datetime import datetime
import sys
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
from zntutils.system_utils import get_user_data, get_all_berkas_id
from zntutils.zona_layer import get_config_values, validate_zona_layer_before_upload

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
        self.tools = [Upload_Peta_Rencana_Area_Kerja_Pembaruan_ZNT,
                      Upload_Peta_Area_Kerja_Pembaruan_ZNT,
                      Masukkan_Data_ZNT_Sebelumnya,
                      Upload_Delineasi_Zona_Awal_Nilai_Tanah_Pembaruan_ZNT]

class Upload_Peta_Rencana_Area_Kerja_Pembaruan_ZNT(object):
    def __init__(self):
        self.label = "Upload Peta Rencana Area Kerja"
        self.description = ""
        self.canRunInBackground = False


    def getParameterInfo(self):
        berkas_list = get_all_berkas_id(process_type='Pembaruan ZNT')
        berkas_show = []
        if berkas_list is not None:
            for berkas in berkas_list:
                if berkas[1] is True:
                    berkas_show.append(f"{berkas[0]}")
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
            penjelasan.enabled = False
        
        return
    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True
    
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

        berkas_list = get_all_berkas_id(process_type='Pembaruan ZNT')

        if berkas_list is None:
            arcpy.AddWarning("Tidak ada berkas yang tersedia untuk dipilih. Pastikan Anda tidak salah memilih menu atau memiliki berkas yang valid untuk proses Pembaruan ZNT.")
            return
        
        shapefile_path = parameters[0].valueAsText
        berkas_value = parameters[1].valueAsText

        server = get_user_data(PREFERRED_SERVER_KEY)
        use_production = True if server == "Produksi" or server == None else False
        token = user_data.get(AUTH_KEY, None)

        validate_document_type(
            document_id=berkas_value,
            target='Pembaruan ZNT')
        upload_shapefile_to_sipenta(
            nomor_berkas=berkas_value,
            token=token,
            param="pembaruan_znt_peta_rencana_area_kerja",
            in_feature="Zona_Layer",
            shapefile_path=shapefile_path,
            use_production=use_production)

        return

class Upload_Peta_Area_Kerja_Pembaruan_ZNT(object):
    def __init__(self):
        self.label = "Upload Peta Area Kerja Disepakati"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):

        berkas_list = get_all_berkas_id(process_type='Pembaruan ZNT')
        berkas_show = []
        if berkas_list is not None:
            for berkas in berkas_list:
                if berkas[1] is True:
                    berkas_show.append(f"{berkas[0]}")
        else:
            berkas_show = ['Tidak ada berkas yang dapat dipilih']

        shapefile = arcpy.Parameter(
            displayName="Shapefile Area Kerja Disepakati (.shp)",
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
            penjelasan.enabled = False
        
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

        berkas_list = get_all_berkas_id(process_type='Pembaruan ZNT')

        if berkas_list is None:
            arcpy.AddWarning("Tidak ada berkas yang tersedia untuk dipilih. Pastikan Anda tidak salah memilih menu atau memiliki berkas yang valid untuk proses Pembaruan ZNT.")
            return
        
        shapefile_path = parameters[0].valueAsText
        berkas_value = parameters[1].valueAsText

        server = get_user_data(PREFERRED_SERVER_KEY)
        use_production = True if server == "Produksi" or server == None else False
        token = user_data.get(AUTH_KEY, None)

        validate_document_type(
            document_id=berkas_value,
            target='Pembaruan ZNT')
        
        upload_shapefile_to_sipenta(
            nomor_berkas=berkas_value,
            token=token,
            param="pembaruan_znt_peta_area_kerja_yang_disepakati",
            in_feature="Zona_Layer",
            shapefile_path=shapefile_path,
            use_production=use_production)


        return        

class Masukkan_Data_ZNT_Sebelumnya(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Masukkan Data ZNT Sebelumnya"
        self.description = "Tools untuk memasukkan data ZNT sebelumnya ke dalam sistem sebagai dasar perhitungan ZNT baru. Pastikan data ZNT lama sudah benar dan lengkap sebelum menggunakan tool ini."

    def getParameterInfo(self):
        """Define the tool parameters."""

        # 1. Input layer ZNT Lama
        znt_awal = arcpy.Parameter(
            displayName="Pilih Data ZNT",
            name="old_znt_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )

        # === 2. Field Nomor Zona ===
        nomorzone = arcpy.Parameter(
            displayName="Pilih Field Nomor Zona",
            name="nomorzone_field",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        nomorzone.parameterDependencies = [znt_awal.name]
        nomorzone.description = "ID unik untuk setiap zona"

        penjelasan_nomorzone = arcpy.Parameter(
            displayName="Info Field Nomor Zona",
            name="penjelasan_nomorzone",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )
        penjelasan_nomorzone.value = (
            "Ketentuan untuk field nomor zona:\n"
            " - Berisi ID unik untuk setiap zona\n"
            " - Harus unik (tidak boleh duplikat)\n"
            " - Format: angka bulat (1, 2, 3, ...)"
        )

        # === 3. Field Nilai ===
        nilai = arcpy.Parameter(
            displayName="Pilih Field Nilai",
            name="nilai_field",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        nilai.parameterDependencies = [znt_awal.name]
        nilai.description = "Nilai ZNT sebelumnya"

        penjelasan_nilai = arcpy.Parameter(
            displayName="Info Field Nilai",
            name="penjelasan_nilai",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )

        penjelasan_nilai.value = (
            "Ketentuan untuk field nilai:\n"
            " - Berisi Nilai ZNT sebelumnya\n"
            " - Format: numerik (angka)\n"
            " - Tidak boleh <null> atau 0"
        )

        # === 4. Field Jenis Zona ===
        jeniszona = arcpy.Parameter(
            displayName="Pilih Field Jenis Zona",
            name="jeniszona_field",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        jeniszona.parameterDependencies = [znt_awal.name]
        jeniszona.description = "Kategori zona"

        penjelasan_jeniszona = arcpy.Parameter(
            displayName="Info Field Jenis Zona",
            name="penjelasan_jeniszona",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )

        penjelasan_jeniszona.value = (
            "Ketentuan untuk field jenis zona:\n"
            " - Berisi kategori zona dengan kode:\n"
            "   - 1 → Non-Pertanian\n"
            "   - 2 → Pertanian\n"
            " - Tidak boleh berisi <null>\n"
            " - Tidak boleh berisi nilai selain 1 atau 2"
        )

        return [
            znt_awal,
            nomorzone, penjelasan_nomorzone,
            nilai, penjelasan_nilai,
            jeniszona, penjelasan_jeniszona
        ]
    def isLicensed(self):
        """Set whether the tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """
        Kondisi yang harus terpebuhi agar parameter field muncul:
        1. Terdapat nilai default 'NOZONE' atau 'NOZN' untuk Parameter Nomor Zona jika tersedia di dalam nama field dari ZNT lama.
        2. Terdapat nilai default 'NILAIZN' atau 'MEAN' untuk Parameter Nilai jika tersedia di dalam nama field dari ZNT lama.
        3. Terdapat nilai default 'JNSZN' atau 'JENIS_ZONA' untuk Parameter Jenis Zona jika tersedia di dalam nama field dari ZNT lama.
        """
        znt_lama = parameters[0].valueAsText
        if not znt_lama:
            return

        try:
            field_names = [field.name for field in arcpy.ListFields(znt_lama)]
        except Exception:
            return

        field_names_upper = {field_name.upper(): field_name for field_name in field_names}

        if not parameters[1].altered:
            if "NOZONE" in field_names_upper:
                parameters[1].value = field_names_upper["NOZONE"]
            elif "NOZN" in field_names_upper:
                parameters[1].value = field_names_upper["NOZN"]

        if not parameters[3].altered:
            if "NILAIZN" in field_names_upper:
                parameters[3].value = field_names_upper["NILAIZN"]
            elif "MEAN" in field_names_upper:
                parameters[3].value = field_names_upper["MEAN"]

        if not parameters[5].altered:
            if "JNSZN" in field_names_upper:
                parameters[5].value = field_names_upper["JNSZN"]
            elif "JENIS_ZONA" in field_names_upper:
                parameters[5].value = field_names_upper["JENIS_ZONA"]

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter. This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        znt_lama = parameters[0].valueAsText
        nomorzone = parameters[1].valueAsText
        nilai = parameters[3].valueAsText
        jeniszona = parameters[5].valueAsText 

        config_and_paths = get_config_values()
        dataset_path = config_and_paths['dataset_path']

        # --- Validasi: pastikan field nomorzone dan nilai tidak NULL dan bernilai numerik
        fields = [nomorzone, nilai, jeniszona]

        if not znt_lama:
            arcpy.AddError("File ZNT lama tidak ditemukan.")
            return

        try:
            with arcpy.da.SearchCursor(znt_lama, fields) as cursor:
                for rownum, row in enumerate(cursor, start=1):
                    for i, val in enumerate(row):
                        field_name = fields[i]

                        if val is None:
                            arcpy.AddError(f"{field_name} NULL di baris {rownum}")
                            return

                        try:
                            if isinstance(val, str):
                                val = float(val.strip())
                            elif isinstance(val, bool):
                                raise ValueError("Boolean tidak valid")
                            else:
                                val = float(val)
                        except:
                            arcpy.AddError(f"{field_name} tidak bisa dikonversi ke angka di baris {rownum}")
                            return

                        if math.isnan(val) or val <= 0:
                            arcpy.AddError(f"Field {field_name} memiliki nilai tidak valid (0, negatif, atau Null) di baris {rownum}")
                            return

                        if field_name == jeniszona:
                            if int(val) not in [1, 2]:
                                arcpy.AddError(f" Field {field_name} memiliki nilai tidak valid ({int(val)}) di baris {rownum}\nJenis Zona hanya boleh berisi angka 1 (Non-Pertanian) atau 2 (Pertanian)")
                                return           

        except arcpy.ExecuteError:
            arcpy.AddError(f"Gagal membaca layer: {arcpy.GetMessages(2)}")
            return

        arcpy.AddMessage("Validasi field nomor zona dan nilai: OK.")

        # --- Proses memasukkan data ZNT sebelumnya ke layer ZNT saat ini
        zona_layer_path = os.path.join(dataset_path, "Zona_Layer")
        zona_layer_temp_path = 'in_memory/Zona_Layer_Temp'

        # Hapus topology dan layer zona jika sudah ada
        topo = os.path.join(dataset_path, "Zona_Layer_Topology")
        if arcpy.Exists(topo):
            arcpy.management.Delete(topo)

        if arcpy.Exists(zona_layer_path):
            arcpy.management.Delete(zona_layer_path)

        if arcpy.Exists(zona_layer_temp_path):
            arcpy.management.Delete(zona_layer_temp_path)

        field_mappings = arcpy.FieldMappings()
        field_mappings.addTable(znt_lama)

        # Hapus field OBJECTID dari field mappings
        for field_map in field_mappings.fieldMappings:
            if field_map.outputField.name.upper() == "OBJECTID":
                field_mappings.removeFieldMap(field_mappings.findFieldMapIndex(field_map.outputField.name))


        arcpy.conversion.FeatureClassToFeatureClass(
            znt_lama,
            'in_memory',
            "Zona_Layer_Temp",
            field_mapping=field_mappings
        )

        # ======================
        # FIELD CALCULATIONS
        # ======================

        """
        Simpan data lama dahulu
        """

        old_value_fields = [{'name': "NILAIZN_LAMA", 'data_type': "LONG"},
                        {'name': "NILBULAT_LAMA", 'data_type': "TEXT"}]
        input_features_fields = [f.name for f in arcpy.ListFields(znt_lama)]

        for field in old_value_fields:
            if field['name'] in input_features_fields:
                arcpy.management.CalculateField(zona_layer_temp_path, field['name'], "None", "PYTHON3") 
            else:
                arcpy.management.AddField(zona_layer_temp_path, field['name'], field['data_type'])

        # Fungsi untuk pembulatan nilai zona
        code_block = """def get(a):
            if a:
                return round(a) 
            else:
                return a  # Pertahankan nilai null"""

        # Fungsi untuk format nilai mata uang dengan pembulatan
        code_block2 = """def get(a, b):
            if a:
                # Bulatkan nilai berdasarkan parameter, format ke Rupiah
                valu = round((int(a)/int(b)), 0)*int(b)
                return 'Rp. ' + (f'{int(float(valu)):,}').replace(',', '.')  # Format dengan titik sebagai pemisah ribuan
            else:
                return a  # Pertahankan nilai null"""
        
        kode_jenis_zona = """def get_jenis_zona(a):
            if a == 1:
                return 'Non-Pertanian'
            elif a == 2:
                return 'Pertanian'"""

        # Perhitungan field untuk berbagai kolom:
        arcpy.management.CalculateField(zona_layer_temp_path, "NILAIZN_LAMA", f"get(!{nilai}!)", "PYTHON3", code_block)  # Salin nilai asli
        arcpy.management.CalculateField(zona_layer_temp_path, "NILBULAT_LAMA", f"get(!{nilai}!, '1000')", "PYTHON3", code_block2)  # Salin nilai bulat
        arcpy.management.DeleteField(zona_layer_temp_path, nilai)  # Hapus field nilai asli jika berbeda
        
        # NOZN tidak terbaca,
        arcpy.management.AddField(zona_layer_temp_path, "NOZN", "LONG")
        arcpy.management.CalculateField(zona_layer_temp_path, 'NOZN', f"int(!{nomorzone}!)", "PYTHON3")
        if nomorzone != "NOZN":
            arcpy.management.DeleteField(zona_layer_temp_path, nomorzone)

        if jeniszona:
            if jeniszona != "JNSZN":
                arcpy.management.AddField(zona_layer_temp_path, "JNSZN", "SHORT")
                arcpy.management.CalculateField(zona_layer_temp_path, 'JNSZN', f"!{jeniszona}!", "PYTHON3")
                arcpy.management.CalculateField(zona_layer_temp_path, 'PENGGUNAAN', f"get_jenis_zona(!{jeniszona}!)", "PYTHON3", kode_jenis_zona)
                arcpy.management.DeleteField(zona_layer_temp_path, jeniszona)
        else:
                arcpy.management.AddField(zona_layer_temp_path, "JNSZN", "SHORT")
                arcpy.management.CalculateField(zona_layer_temp_path, "JNSZN", "1", "PYTHON3")  # Set default ke 1
                arcpy.management.AddField(zona_layer_temp_path, "PENGGUNAAN", "TEXT")
                arcpy.management.CalculateField(zona_layer_temp_path, "PENGGUNAAN", "'Non-Pertanian'", "PYTHON3")  # Set default

        self.check_and_prepare_nomor_zona(zona_layer_temp_path)

        # --- Hapus field yang tidak diinginkan ---
        all_fields = [f.name for f in arcpy.ListFields(zona_layer_temp_path)]
        
        # Dapatkan nama field geometri dan ObjectID
        desc = arcpy.Describe(zona_layer_temp_path)
        shape_field_name = desc.shapeFieldName
        oid_field_name = desc.OIDFieldName

        # Field yang ingin dipertahankan
        desired_fields = ["NOZN", "NILAIZN", "JNSZN", "PENGGUNAAN", "NILAIZN_LAMA", "NILBULAT", "NILBULAT_LAMA", "HISTZONE", shape_field_name, oid_field_name]
        
        # Tambahkan field yang diperlukan sistem (seperti Shape_Length, Shape_Area) ke daftar yang dipertahankan
        for field in desc.fields:
            if not field.editable:
                if field.name not in desired_fields:
                    desired_fields.append(field.name)

        fields_to_delete = [f for f in all_fields if f not in desired_fields]

        if fields_to_delete:
            arcpy.management.DeleteField(zona_layer_temp_path, fields_to_delete)

        required_fields = [
                            {'name': "SMPBKREL", 'data_type': "DOUBLE"},
                            {'name': "SMPBAKU", 'data_type': "DOUBLE"},
                            {'name': "NILAIZN", 'data_type': "DOUBLE"},
                            {'name': "JMLSMPL", 'data_type': "SHORT"},
                            {'name': "NILBULAT", 'data_type': "TEXT"},
                            {'name': "NILMIN", 'data_type': "LONG"},
                            {'name': "NILMAKS", 'data_type': "LONG"},
                            {'name': "cluster", 'data_type': "TEXT"},
                            {'name': "WADMKK", 'data_type': "TEXT"},
                            {'name':"WADMPR", 'data_type': "TEXT"},
                            {'name': "THNNILAI", 'data_type': "SHORT"}]

        existing_fields_details = {f.name: f.type for f in arcpy.ListFields(zona_layer_temp_path)}

        for field_info in required_fields:
            field_name = field_info['name']
            field_type = field_info['data_type']
            
            # Periksa apakah field sudah ada
            if field_name in existing_fields_details:
                # Jika tipe data tidak sesuai, hapus field tersebut
                if existing_fields_details[field_name].upper() != field_type.upper():
                    arcpy.management.DeleteField(zona_layer_temp_path, field_name)
                    arcpy.management.AddField(zona_layer_temp_path, field_name, field_type)
                else:
                    # Jika tipe data sudah benar, kosongkan nilainya
                    arcpy.management.CalculateField(zona_layer_temp_path, field_name, "None", "PYTHON3")
            else:
                # Jika field belum ada, tambahkan
                arcpy.management.AddField(zona_layer_temp_path, field_name, field_type)

        arcpy.management.AlterField(
            in_table=zona_layer_temp_path,
            field="cluster",
            new_field_name="cluster",        # boleh sama (tidak ganti nama)
            new_field_alias="KLASTER"
        )
                # Set nilai default
        arcpy.management.CalculateField(zona_layer_temp_path, "WADMKK", "'"+str(config_and_paths['kota'])+"'", "PYTHON3")  # Set kode kabupaten/kota
        arcpy.management.CalculateField(zona_layer_temp_path, "WADMPR", "'"+str(config_and_paths['provinsi'])+"'", "PYTHON3")  # Set kode provinsi
        arcpy.management.CalculateField(zona_layer_temp_path, "THNNILAI", config_and_paths['tahun'], "PYTHON3")  # Set tahun nilai
        arcpy.management.CalculateField(zona_layer_temp_path, "cluster", "1", "PYTHON3")  # Set cluster default

        zona_layer_fields = [f.name for f in arcpy.ListFields(zona_layer_temp_path)]
        # Tambah field JNSZN (jenis zona) jika belum ada

        if "HISTZONE" not in zona_layer_fields:
            """
            JIKA HISTZONE BELUM ADA:
            Membuat field HISTZONE baru dengan urutan nomor dan tipe zona
            """
            

            # Membuat field sementara untuk menyimpan tipe zona
            arcpy.management.AddField(zona_layer_temp_path, "temp", "STRING")

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
            arcpy.management.CalculateField(zona_layer_temp_path, "temp", expression, "PYTHON3", codeblock)
            
            # Menggabungkan NOZN dan temp menjadi HISTZONE (contoh: "1N", "2P")
            arcpy.management.CalculateField(zona_layer_temp_path, "HISTZONE", "str(!NOZN!) + !temp!", "PYTHON3")
            
            # Menghapus field sementara
            arcpy.management.DeleteField(zona_layer_temp_path, "temp")

        # Update penggunaan lahan berdasarkan jenis zona
        with arcpy.da.UpdateCursor(zona_layer_temp_path, ["JNSZN", "PENGGUNAAN"]) as rows:
            for row in rows:
                if row[0] == 1:  # Jika jenis zona = 1
                    row[1] = "Non-Pertanian"
                elif row[0] == 2:  # Jika jenis zona = 2
                    row[1] = "Pertanian"
                rows.updateRow(row)  # Update record
        del row, rows  # Bersihkan cursor

        zona_layer_lyr = "zona_layer_lyr_tmp"
        arcpy.management.MakeFeatureLayer(zona_layer_temp_path, zona_layer_lyr)
        
        existing_fields = [f.name for f in arcpy.ListFields(zona_layer_lyr)]
        ordered_fields = [
            "NOZN",
            "cluster",
            "WADMKK",
            "WADMPR",
            "JNSZN",
            "PENGGUNAAN",
            "HISTZONE",
            "SMPBKREL",
            "SMPBAKU",
            "NILAIZN",
            "JMLSMPL",
            "NILMIN",
            "NILMAKS",
            "NILBULAT",
            "THNNILAI",
            "NILAIZN_LAMA",
            "NILBULAT_LAMA",
        ]

        fms = arcpy.FieldMappings()

        for fld in ordered_fields:
            if fld not in existing_fields:
                arcpy.AddWarning(f"Field '{fld}' tidak ditemukan, dilewati")
                continue

            fm = arcpy.FieldMap()
            fm.addInputField(zona_layer_lyr, fld)
            fms.addFieldMap(fm)

        arcpy.conversion.FeatureClassToFeatureClass(
            zona_layer_temp_path,
            dataset_path,
            'Zona_Layer',
            field_mapping=fms
        )

        arcpy.management.Delete(zona_layer_temp_path)  # Hapus layer sementara      

        # BUG ERROR (Arcgis 3.6): Baca Lebih rinci di : https://www.notion.so/ZNT-002-2e42170c49e3807c9119ef76beb74a46?source=copy_link

        if arcpy.Exists(zona_layer_path):
            p = arcpy.mp.ArcGISProject("CURRENT")
            m = p.activeMap
            
            # Tambahkan layer yang baru diproses
            m.addDataFromPath(zona_layer_path)
        
        # End Of Bug 

        return

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
 
class Upload_Delineasi_Zona_Awal_Nilai_Tanah_Pembaruan_ZNT(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Upload Delineasi Perubahan Batas Zona Baru"
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
            param="pembaruan_znt_delineasi_perubahan_batas_zona_baru",
            in_feature="Zona_Layer",
            feature_layer=feature_layer,
            use_production=use_production)
        return        
