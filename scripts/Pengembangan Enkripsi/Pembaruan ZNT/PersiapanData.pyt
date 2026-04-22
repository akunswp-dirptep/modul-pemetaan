from datetime import datetime
import sys
import arcpy, os

arcpy.env.outputZFlag = "Disabled"
arcpy.env.outputMFlag = "Disabled"

# Tambahkan parent directory ke sys.path
script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from zntutils.document import validate_document_type, get_credentials
from zntutils.upload_utils import main_upload_shapefile, main_upload
from zntutils.system_utils import get_user_data, renew_user_data
from zntutils.zona_layer import get_config_values

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
        self.is_gis_internal = is_internal()
        preferred_server = get_user_data('preferred_server')
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
            displayName="Shapefile Rencana Area Kerja (.shp)",
            name="shapefile_path",
            datatype="DEFile",  
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

        if preferred_server:
            param4.value = preferred_server

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
        username = str(parameters[0].valueAsText).replace(" ", "")
        project_id = str(parameters[1].valueAsText).replace(" ", "")
        tahun = parameters[2].valueAsText
        shapefile_path = parameters[3].valueAsText
        server = parameters[4].valueAsText if len(parameters) > 4 else None
        use_production = True if server == "Produksi" or server == None else False


        validate_document_type(project_id, target='Pembaruan ZNT')
        main_upload_shapefile(project_id, username, "pembaruan_znt_peta_rencana_area_kerja", "Persiapan", "Zona_Layer", tahun, "ZNT", shapefile_path, use_production)
        
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

class Upload_Peta_Area_Kerja_Pembaruan_ZNT(object):
    def __init__(self):
        self.label = "Upload Peta Area Kerja Disepakati"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        preferred_server = get_user_data('preferred_server')
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
            displayName="Shapefile Area Kerja (.shp)",
            name="shapefile_path",
            datatype="DEFile",  
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
        
        if preferred_server:
            param4.value = preferred_server

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
        username = str(parameters[0].valueAsText).replace(" ", "")
        project_id = str(parameters[1].valueAsText).replace(" ", "")
        tahun = parameters[2].valueAsText
        shapefile_path = parameters[3].valueAsText
        server = parameters[4].valueAsText if len(parameters) > 4 else None
        use_production = True if server == "Produksi" or server == None else False
        
        validate_document_type(project_id, target='Pembaruan ZNT')
        main_upload_shapefile(project_id, username, "pembaruan_znt_peta_area_kerja_yang_disepakati", "Persiapan", "Zona_Layer", tahun, "ZNT", shapefile_path, use_production)
        
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

class Masukkan_Data_ZNT_Sebelumnya(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Masukkan Data ZNT Sebelumnya"
        self.description = ""

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

        # === 2. Parameter mapping field (dengan filter Field) ===
        nomorzone = arcpy.Parameter(
            displayName="Pilih Field Nomor Zona",
            name="nomorzone_field",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )       

        nomorzone.parameterDependencies = [znt_awal.name]

        penjelasan_nomorzone = arcpy.Parameter(
            displayName="Penjelasan Field Nomor Zona",
            name="penjelasan_nomorzone",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )

        penjelasan_nomorzone.value = (
            "Field nomor zona adalah field\n"
            "yang berisi nomor identifikasi zona.\n"
            "Field ini harus berisi nilai unik\n"
            "untuk setiap zona, dan bentuknya\n"
            "berupa angka bulat. (1, 2, 3, dst.)"
        )

        nilai = arcpy.Parameter(
            displayName="Pilih Field Nilai",
            name="nilai_field",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        nilai.parameterDependencies = [znt_awal.name]

        penjelasan_nilai = arcpy.Parameter(
            displayName="Penjelasan Field Nilai",
            name="penjelasan_nilai",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )

        penjelasan_nilai.value = (
            "Field nilai adalah field yang \n"
            "berisi nilai ZNT Sebelumnya \n"
            "untuk setiap zona. Nilai ini \n"
            "harus berupa angka, dan akan \n"
            "digunakan sebagai dasar perhitungan \n"
            "nilai tanah pada ZNT baru.\n"
            "Field Nilai tidak boleh bernilai\n"
            "null atau 0.")

        jeniszona = arcpy.Parameter(
            displayName="Pilih Field Jenis Zona",
            name="jeniszona_field",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        jeniszona.parameterDependencies = [znt_awal.name]


        penjelasan_jeniszona = arcpy.Parameter(
            displayName="Penjelasan Field Jenis Zona",
            name="penjelasan_jeniszona",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )
        penjelasan_jeniszona.value = (
            "Field jenis zona adalah field \n"
            "yang berisi angka 1 atau 2 \n"
            "yang menunjukkan jenis zona: \n"
            " - 1 untuk Non-Pertanian, \n"
            " - 2 untuk Pertanian.\n"
            "Field ini tidak boleh null \n"
            "atau 0 ataupun bernilai selain 1 atau 2."
        )


        return [znt_awal, nomorzone, penjelasan_nomorzone, nilai, penjelasan_nilai, jeniszona, penjelasan_jeniszona]
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
                rownum = 0
                for row in cursor:
                    rownum += 1
                    for i, val in enumerate(row):
                        field_name = fields[i]
                        # Null atau empty string dianggap tidak valid
                        if val is None:
                            arcpy.AddError(f"Field '{field_name}' mengandung nilai NULL pada record {rownum}. Semua nilai harus terisi dan numeric atau dapat dikonversi ke angka.")
                            return
                        if val == 0 or val == '0':
                                arcpy.AddError(f"Field '{field_name}' mengandung nilai 0 pada record {rownum}.")
                                return
                        if field_name == jeniszona:
                            if val not in [1, 2, '1', '2']:
                                arcpy.AddError(f"Field '{field_name}' pada record {rownum} memiliki nilai '{val}' yang tidak valid. Nilai harus 1 (Non-Pertanian) atau 2 (Pertanian).")
                                return

                        if isinstance(val, str):
                            s = val.strip()
                            if s == "":
                                arcpy.AddError(f"Field '{field_name}' mengandung string kosong pada record {rownum}.")
                                return
                            try:
                                float(s)
                            except Exception:
                                arcpy.AddError(f"Field '{field_name}' value '{s}' pada record {rownum} bukan angka dan tidak dapat dikonversi ke angka.")
                                return
                        elif isinstance(val, (int, float)):
                            # sudah numeric, lanjut
                            continue
                        else:
                            # coba konversi ke float sebagai upaya terakhir
                            try:
                                float(val)
                            except Exception:
                                arcpy.AddError(f"Field '{field_name}' value '{val}' pada record {rownum} bukan angka dan tidak dapat dikonversi ke angka.")
                                return
        except arcpy.ExecuteError:
            arcpy.AddError(f"Gagal membaca layer: {arcpy.GetMessages(2)}")
            return

        arcpy.AddMessage("Validasi field nomor zona dan nilai: OK.")

        # --- Proses memasukkan data ZNT sebelumnya ke layer ZNT saat ini
        zona_layer_path = os.path.join(dataset_path, "Zona_Layer")
        zona_layer_temp_path = os.path.join(dataset_path, "Zona_Layer_Temp")

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

        # ======================
        # KONVERSI FITUR
        # ======================
        arcpy.conversion.FeatureClassToFeatureClass(
            znt_lama,
            dataset_path,
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
        self.is_gis_internal = is_internal()
        preferred_server = get_user_data('preferred_server')
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

        if preferred_server:
            param4.value = preferred_server
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
        
        validate_document_type(project_id, target='Pembaruan ZNT')
        main_upload(project_id, username, "pembaruan_znt_delineasi_perubahan_batas_zona_baru", "Analisis & Delineasi Zona yang Mengalami Perubahan", "Zona_Layer", tahun, "ZNT", feature_class, use_production)
              
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
