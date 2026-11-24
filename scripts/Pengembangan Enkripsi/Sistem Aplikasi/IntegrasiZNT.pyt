import os, sys
import math, uuid
import arcpy
import re
import json
import tempfile
from datetime import datetime
import requests

script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from zntutils.system_utils import get_user_data, clear_user_data
from zntutils.constant import CREDENTIAL_KEY, PREFERRED_SERVER_KEY, AUTH_KEY
arcpy.env.outputZFlag = "Disabled"
arcpy.env.outputMFlag = "Disabled"

class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the .pyt file)."""
        self.label = "Toolbox"
        self.alias = "toolbox"
        # List of tool classes associated with this toolbox
        self.tools = [Penggabungan_ZNT_Manual, Unduh_Data_Integrasi_Dari_Sipenta]


class Penggabungan_ZNT_Manual(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Penggabungan ZNT"
        self.description = "Tool untuk menggabungkan Zona Nilai Tanah (ZNT) lama dengan ZNT baru."
        self.canRunInBackground = False
        self.useOtherLayer = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        # Kategori
        cat_1 = "1. Pengaturan ZNT Pertama"
        cat_2 = "2. Pengaturan ZNT Kedua"
        cat_3 = "3. Referensi Spasial & Output"

        # === 1. Input ZNT Pertama & Mapping Field ===
        znt_pertama = arcpy.Parameter(
            displayName="Pilih ZNT Pertama",
            name="old_znt_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )
        znt_pertama.category = cat_1

        nomorzone = arcpy.Parameter(
            displayName="Pilih Field Nomor Zona",
            name="nomorzone_field",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        nomorzone.parameterDependencies = [znt_pertama.name]
        nomorzone.category = cat_1

        nilai = arcpy.Parameter(
            displayName="Pilih Field Nilai",
            name="nilai_field",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        nilai.parameterDependencies = [znt_pertama.name]
        nilai.category = cat_1

        tahun = arcpy.Parameter(
            displayName="Pilih Field Tahun Pembuatan",
            name="tahun_field",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        tahun.parameterDependencies = [znt_pertama.name]
        tahun.category = cat_1

        bulandibuat = arcpy.Parameter(
            displayName="Pilih Field Bulan Pembuatan",
            name="bulandibuat_field",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        bulandibuat.parameterDependencies = [znt_pertama.name]
        bulandibuat.category = cat_1

        # === 2. Input ZNT Kedua & Mapping Field ===
        znt_kedua = arcpy.Parameter(
            displayName="Pilih ZNT Kedua",
            name="another_znt_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )
        znt_kedua.category = cat_2

        nomorzone_znt_kedua = arcpy.Parameter(
            displayName="Pilih Field Nomor Zona",
            name="nomorzone_field_znt_kedua",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        nomorzone_znt_kedua.parameterDependencies = [znt_kedua.name]
        nomorzone_znt_kedua.category = cat_2

        nilai_znt_kedua = arcpy.Parameter(
            displayName="Pilih Field Nilai",
            name="nilai_field_znt_kedua",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        nilai_znt_kedua.parameterDependencies = [znt_kedua.name]
        nilai_znt_kedua.category = cat_2

        tahun_znt_kedua = arcpy.Parameter(
            displayName="Pilih Field Tahun Pembuatan",
            name="tahun_field_znt_kedua",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        tahun_znt_kedua.parameterDependencies = [znt_kedua.name]
        tahun_znt_kedua.category = cat_2

        bulandibuat_znt_kedua = arcpy.Parameter(
            displayName="Pilih Field Bulan Pembuatan",
            name="bulandibuat_field_znt_kedua",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        bulandibuat_znt_kedua.parameterDependencies = [znt_kedua.name]
        bulandibuat_znt_kedua.category = cat_2

        # === 3. Referensi dan Output ===
        znt_spatial_reference = arcpy.Parameter(
            displayName="Pilih ZNT untuk referensi spasial",
            name="reference_znt_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )
        znt_spatial_reference.category = cat_3

        znt_nozone_reference = arcpy.Parameter(
            displayName="Pilih ZNT untuk referensi Nomor Zona",
            name="nozone_reference_znt_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )
        znt_nozone_reference.category = cat_3

        znt_shp_output = arcpy.Parameter(
            displayName="Pilih Tempat Penyimpanan Shapefile ZNT Gabungan",
            name="znt_shp_output",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output"
        )
        znt_shp_output.category = cat_3
        
        penjelasan = arcpy.Parameter(
            displayName="Maaf, Anda tidak memiliki akses untuk menjalankan tools ini.",
            name="penjelasan",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )
        penjelasan.value = "Tools ini hanya untuk Operator GIS Internal\n\n"

        params = [
            znt_pertama, nomorzone, nilai, tahun, bulandibuat,
            znt_kedua, nomorzone_znt_kedua, nilai_znt_kedua, tahun_znt_kedua, bulandibuat_znt_kedua,
            znt_spatial_reference, znt_nozone_reference, znt_shp_output
        ]

        
        credential = get_user_data(CREDENTIAL_KEY)
        self.operatorGIS = (credential.get('instansi_id') == '980FECFC746D8C80E0400B0A9214065D')
        if self.operatorGIS:
            return params
        else:
            return [penjelasan]


    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal validation is performed."""
        
        # Mapping nama field target (diubah jadi UPPERCASE untuk mempermudah perbandingan)
        field_mapping = {
            'nomorzone': ['NOZONE', 'NOZN'],
            'nilai': ['NILAIZN', 'MEAN'],
            'tahun': ['TAHUN', 'THNNILAI'],
            'bulan': ['BULANDIBUAT', 'BULAN']
        }
        
        def autofill_fields(layer_idx, nozone_idx, nilai_idx, tahun_idx, bulan_idx):
            layer_param = parameters[layer_idx]
            
            # Memicu auto-fill hanya jika pengguna baru saja memilih/mengganti layer (belum divalidasi)
            if layer_param.value and not layer_param.hasBeenValidated:
                try:
                    # Ambil daftar field dari layer yang dipilih
                    fields = arcpy.ListFields(layer_param.value)
                    
                    # Buat dictionary: { "NAMA_FIELD_UPPERCASE": "NamaFieldAsli" } 
                    # Ini berguna agar matching tidak sensitif huruf besar/kecil (case-insensitive)
                    field_dict = {f.name.upper(): f.name for f in fields}
                    
                    # Hubungkan parameter dengan kunci (key) pemetaannya
                    target_params = [
                        (parameters[nozone_idx], 'nomorzone'),
                        (parameters[nilai_idx], 'nilai'),
                        (parameters[tahun_idx], 'tahun'),
                        (parameters[bulan_idx], 'bulan')
                    ]
                    
                    # Iterasi setiap parameter field
                    for param, map_key in target_params:
                        for possible_name in field_mapping[map_key]:
                            if possible_name in field_dict:
                                param.value = field_dict[possible_name]
                                break  
                                
                except Exception:
                    pass

        autofill_fields(0, 1, 2, 3, 4)
        autofill_fields(5, 6, 7, 8, 9)

        return

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool parameter."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        credential = get_user_data(CREDENTIAL_KEY)
        self.operatorGIS = (credential.get('instansi_id') == '980FECFC746D8C80E0400B0A9214065D')
        if not self.operatorGIS:
            arcpy.AddError("Anda tidak memiliki akses untuk menjalankan tools ini.")
            return
        
        # Ekstrak nilai parameter
        self.znt_pertama = parameters[0].valueAsText
        self.output_shapefile = parameters[12].valueAsText
        
        znt_kedua = parameters[5].valueAsText
        znt_spatial_reference = parameters[10].valueAsText
        self.znt_nozone_reference = parameters[11].valueAsText

        # Mapping fields ZNT Pertama
        self.mapping_fields = {
            'nomorzone': parameters[1].valueAsText,
            'nilai': parameters[2].valueAsText,
            'tahun': parameters[3].valueAsText,
            'bulan': parameters[4].valueAsText,
        }

        # Mapping fields ZNT Kedua
        self.mapping_fields_znt_kedua = {
            'nomorzone': parameters[6].valueAsText,
            'nilai': parameters[7].valueAsText,
            'tahun': parameters[8].valueAsText,
            'bulan': parameters[9].valueAsText,
        }

        # Eksekusi proses utama
        self.setup_path_and_configuration(reference_layer=znt_spatial_reference)
        
        self.check_field_compatibility(self.znt_pertama, self.mapping_fields)
        self.check_field_compatibility(znt_kedua, self.mapping_fields_znt_kedua)

        self.check_and_prepare_nomor_zona(self.znt_pertama, self.mapping_fields)
        self.check_and_prepare_nomor_zona(znt_kedua, self.mapping_fields_znt_kedua)
        
        # Layer yang diolah dijadikan sebagai referensi nomor zona diproses lebih awal
        if self.znt_nozone_reference == self.znt_pertama:
            self.penggabungan_geometri_dan_atribut(self.znt_pertama, self.mapping_fields)
            self.penggabungan_geometri_dan_atribut(znt_kedua, self.mapping_fields_znt_kedua)
        else:
            self.penggabungan_geometri_dan_atribut(znt_kedua, self.mapping_fields_znt_kedua)
            self.penggabungan_geometri_dan_atribut(self.znt_pertama, self.mapping_fields)
        
        # self.penentuan_kelas_dan_range()
        self.penyimpanan_hasil()
        self.validasi_topologi_dan_tampilkan_ke_map()

        return
    
    def setup_path_and_configuration(self, reference_layer):
        # Menyusun path menuju folder temp
        appdata = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))
        self.folder_temp_path = os.path.join(appdata, "temp")
        self.spatial_ref = arcpy.Describe(reference_layer).spatialReference
        self.merge_zl = os.path.join(self.folder_temp_path, 'Layer_ZNT_Gabungan.shp')

        if not arcpy.Exists(self.folder_temp_path):
            raise Exception("Dataset (folder temp) tidak ditemukan!")

        if arcpy.Exists(self.merge_zl):
            arcpy.management.Delete(self.merge_zl)

        self.merge_zl_fields = [
            ("nomorzone", "LONG"),
            ("nilai", "DOUBLE"),
            ("tahun", "TEXT"),
            ("bulan", "TEXT"),
            ("luasbatas", "DOUBLE"),
            ("kelas", "SHORT")
        ]

        arcpy.management.CreateFeatureclass(
            out_path=self.folder_temp_path,
            out_name="Layer_ZNT_Gabungan",
            geometry_type="POLYGON",
            spatial_reference=self.spatial_ref
        )
        
        for name, ftype in self.merge_zl_fields:
            arcpy.management.AddField(self.merge_zl, name, ftype)

    def check_field_compatibility(self, layer, mapping_fields):
        """Cek apakah field-field yang dipilih sesuai dengan tipe data yang diharapkan dan tidak ada nilai null."""
        field_info = arcpy.ListFields(layer)
        field_dict = {field.name: field for field in field_info}

        expected_field_types = {
            'nomorzone': ('Field Nomor Zona', ['Double', 'Integer', 'String']),
            'nilai': ('Field Nilai ZNT', ['Double', 'Integer', 'String']),
            'tahun': ('Field Tahun Dibuat', ['SmallInteger','Integer', 'String', 'Double']),
            'bulan': ('Field Bulan Dibuat', ['SmallInteger','Integer', 'String', 'Double']),
        }

        for key, field_name in mapping_fields.items():
            if field_name not in field_dict:
                raise ValueError(f"Field '{field_name}' tidak ditemukan pada layer.")
            
            actual_type = field_dict[field_name].type
            expected_type = expected_field_types[key][1]
            
            if actual_type not in expected_type:
                raise TypeError(f"Field '{field_name}' harus bertipe '{expected_type}' agar dapat digunakan untuk mengisi {expected_field_types[key][0]}, tetapi ditemukan '{actual_type}'.")

        # Validasi tambahan: pastikan nilai string hanya berisi angka
        for key, field_name in mapping_fields.items():
            if key in ('tahun', 'bulan', 'nomorzone') and field_dict[field_name].type == 'String':
                non_numeric_examples = []
                with arcpy.da.SearchCursor(layer, [field_name]) as cursor:
                    for row in cursor:
                        val = row[0]
                        if val is None or isinstance(val, (int, float)):
                            continue
                        s = str(val).strip()
                        if not s.isdigit():
                            if len(non_numeric_examples) < 5:
                                non_numeric_examples.append(s)
                                
                if non_numeric_examples:
                    examples_str = ", ".join(non_numeric_examples)
                    raise ValueError(
                        f"{expected_field_types[key][0]} bertipe 'String' namun berisi nilai non-angka. Contoh: {examples_str}.\n"
                        "Mohon pastikan seluruh nilai berformat string angka (misal '2024', '12')."
                    )
        
        # Cek apakah ada nilai null di field yang diperlukan
        null_counts = {}
        for key, field_name in mapping_fields.items():
            null_count = sum(1 for row in arcpy.da.SearchCursor(layer, [field_name]) if row[0] is None)
            if null_count > 0:
                null_counts[expected_field_types[key][0]] = null_count
        
        if null_counts:
            error_msg = "Ditemukan nilai null pada field berikut:\n"
            for field_desc, count in null_counts.items():
                error_msg += f"  - {field_desc}: {count} baris\n"
            error_msg += "Mohon pastikan semua field memiliki nilai yang valid."
            raise ValueError(error_msg)

    def check_and_prepare_nomor_zona(self, layer, mapping_fields):
        """
        Memastikan tidak ada nomor zona yang null atau terduplikat.
        Jika ada duplikasi, zona dengan nilai tertinggi mempertahankan nomor zonanya.
        """
        nomorzone_field = mapping_fields['nomorzone']
        nilai_field = mapping_fields['nilai']
        zona_data = {}
        
        with arcpy.da.SearchCursor(layer, ['OID@', nomorzone_field, nilai_field]) as cursor:
            for fid, nozone, nilai in cursor:
                if nozone is not None:
                    if nozone not in zona_data:
                        zona_data[nozone] = []
                    zona_data[nozone].append((fid, nilai if nilai is not None else 0))
        
        fids_to_nullify = []
        for nozone, records in zona_data.items():
            if len(records) > 1:
                records_sorted = sorted(records, key=lambda x: x[1], reverse=True)
                for fid, nilai in records_sorted[1:]:
                    fids_to_nullify.append(fid)
        
        if fids_to_nullify:
            with arcpy.da.UpdateCursor(layer, ['OID@', nomorzone_field]) as cursor:
                for row in cursor:
                    if row[0] in fids_to_nullify:
                        row[1] = -1
                        cursor.updateRow(row)
        
        # Cari nomor zona maksimum yang valid
        max_nozone = 0
        with arcpy.da.SearchCursor(layer, [nomorzone_field]) as cursor:
            for row in cursor:
                if row[0] is not None and row[0] > max_nozone:
                    max_nozone = int(row[0])
        
        # Isi ulang nomor zona auto-increment
        current_nozone = max_nozone
        with arcpy.da.UpdateCursor(layer, [nomorzone_field]) as cursor:
            for row in cursor:
                if row[0] == -1:
                    current_nozone += 1
                    row[0] = current_nozone
                    cursor.updateRow(row)

    def penggabungan_geometri_dan_atribut(self, layer, mapping_fields):
        """Fungsi untuk menggabungkan ZNT lama dengan ZNT baru."""
        insert_fields = [f[0] for f in self.merge_zl_fields] + ["SHAPE@"]
        src_fields = [
            mapping_fields['nomorzone'],
            mapping_fields['nilai'],
            mapping_fields['tahun'],
            mapping_fields['bulan'],
            'SHAPE@'
        ]
        
        max_nomorzone = 0
        try:
            nomorzone_list = [row[0] for row in arcpy.da.SearchCursor(self.merge_zl, ["nomorzone"]) if row[0] is not None]
            if nomorzone_list:
                max_nomorzone = max(nomorzone_list)
        except Exception:
            pass
        
        current_nomorzone = max_nomorzone
        
        with arcpy.da.InsertCursor(self.merge_zl, insert_fields) as icur:
            with arcpy.da.SearchCursor(layer, src_fields) as scur:
                for srow in scur:
                    geom = srow[-1]
                    try:
                        luas_m2 = round(geom.getArea('GEODESIC', 'SQUAREMETERS'))
                    except Exception:
                        luas_m2 = round(geom.area) if hasattr(geom, 'area') else None
                    
                    current_nomorzone += 1
                    icur.insertRow([
                        current_nomorzone,
                        float(srow[1]) if srow[1] is not None else None,
                        str(srow[2]) if srow[2] is not None else None,
                        str(srow[3]) if srow[3] is not None else None,
                        float(luas_m2) if luas_m2 is not None else None,
                        1,
                        geom
                    ])

    def penentuan_kelas_dan_range(self):
        """Penentuan kelas rentang nilai ZNT."""
        fields = ["nilai", "rangenilai", "kelas"]
        existing_fields = [f.name for f in arcpy.ListFields(self.merge_zl)]
        
        if "rangenilai" not in existing_fields:
            arcpy.management.AddField(self.merge_zl, "rangenilai", "TEXT")

        raw_values = []
        with arcpy.da.SearchCursor(self.merge_zl, ["nilai"]) as scur:
            for srow in scur:
                if srow[0] is not None:
                    try:
                        raw_values.append(float(srow[0]))
                    except Exception:
                        continue

        if not raw_values:
            arcpy.AddWarning("Tidak ada nilai numeric untuk dibagi kelas.")
            return

        max_raw = max(raw_values)
        nilai_list = []
        
        for v in raw_values:
            try:
                if v == max_raw:
                    rounded = int(math.ceil(v / 1000.0) * 1000)
                else:
                    rounded = int(round(v, -3))
                nilai_list.append(rounded)
            except Exception:
                continue

        nilai_sorted = sorted(nilai_list)
        n = len(nilai_sorted)
        batas_kelas = []
        
        for i in range(9):
            if i == 0:
                batas_kelas.append(nilai_sorted[0])
            elif i == 8:
                batas_kelas.append(nilai_sorted[-1])
            else:
                idx = max(0, min(int(math.ceil(i * n / 8.0)) - 1, n - 1))
                batas_kelas.append(nilai_sorted[idx])

        batas_kelas = [int(round(x)) for x in batas_kelas]

        def tentukan_kelas(v):
            for i in range(1, 9):
                if batas_kelas[i - 1] <= v <= batas_kelas[i]:
                    return i
            return 8 if v >= batas_kelas[-1] else 1

        with arcpy.da.UpdateCursor(self.merge_zl, fields) as cursor:
            for row in cursor:
                if row[0] is None:
                    continue
                try:
                    v = float(row[0])
                except Exception:
                    continue
                    
                kelas = tentukan_kelas(v)
                if kelas == 1:
                    range_str = f"{batas_kelas[0]} - {batas_kelas[1]}"
                else:
                    range_str = f"{batas_kelas[kelas - 1] + 1} - {batas_kelas[kelas]}"
                    
                row[1] = range_str
                row[2] = kelas
                cursor.updateRow(row)

    def penyimpanan_hasil(self):
        """Simpan hasil penggabungan ke shapefile."""
        arcpy.AddMessage(self.output_shapefile)
        arcpy.conversion.FeatureClassToFeatureClass(
            in_features=self.merge_zl,
            out_path=os.path.dirname(self.output_shapefile),
            out_name=os.path.basename(self.output_shapefile)
        )

    def validasi_topologi_dan_tampilkan_ke_map(self):
        """Validasi topologi (Must Not Have Gaps, Must Not Overlap) dan tampilkan ke map."""
        try:
            aprx = arcpy.mp.ArcGISProject('CURRENT')
            active_map = aprx.activeMap
            
            arcpy.AddMessage("Memulai validasi topologi layer ZNT Gabungan...")
            top_gdb_path = os.path.join(self.folder_temp_path, 'topo_validation.gdb')
            
            if arcpy.Exists(top_gdb_path):
                arcpy.management.Delete(top_gdb_path)
            
            arcpy.management.CreateFileGDB(self.folder_temp_path, 'topo_validation.gdb')
            dataset_name = 'topo_ds'
            
            topo_dataset_path = os.path.join(top_gdb_path, dataset_name)
            arcpy.CreateFeatureDataset_management(top_gdb_path, dataset_name, self.spatial_ref)
            
            topo_layer_name = 'Zona_Gabungan_Topo'
            arcpy.conversion.FeatureClassToFeatureClass(
                in_features=self.merge_zl,
                out_path=topo_dataset_path,
                out_name=topo_layer_name
            )
            
            topo_layer_path = os.path.join(topo_dataset_path, topo_layer_name)
            topo_name = 'Validasi_ZNT_Topologi'
            topo_path = os.path.join(topo_dataset_path, topo_name)
            
            arcpy.CreateTopology_management(topo_dataset_path, topo_name)
            arcpy.AddFeatureClassToTopology_management(topo_path, topo_layer_path, 1, 1)
            
            # Tambah Aturan Topologi
            arcpy.management.AddRuleToTopology(topo_path, "Must Not Have Gaps (Area)", topo_layer_path)
            arcpy.management.AddRuleToTopology(topo_path, "Must Not Overlap (Area)", topo_layer_path)
            
            arcpy.ValidateTopology_management(in_topology=topo_path)
            arcpy.AddMessage("Validasi topologi selesai.")
            
            self.tampilkan_ke_active_map(topo_path, topo_dataset_path, active_map)
            
        except Exception as e:
            arcpy.AddError(f"Error dalam validasi topologi: {str(e)}")
            try:
                aprx = arcpy.mp.ArcGISProject('CURRENT')
                self.tampilkan_ke_active_map(self.output_shapefile, None, aprx.activeMap)
            except Exception:
                arcpy.AddWarning("Gagal menampilkan layer ke map.")
    
    def tampilkan_ke_active_map(self, layer_path, workspace_path=None, map_object=None):
        """Tampilkan layer ke active map di ArcGIS."""
        try:
            if map_object is None:
                aprx = arcpy.mp.ArcGISProject('CURRENT')
                map_object = aprx.activeMap
            
            layer_name = os.path.basename(layer_path)
            for existing_layer in map_object.listLayers(layer_name):
                map_object.removeLayer(existing_layer)
            
            map_object.addDataFromPath(layer_path)
            arcpy.AddMessage(f"Layer '{layer_name}' berhasil ditampilkan di map aktif.")
            
        except Exception as e:
            arcpy.AddWarning(f"Gagal menampilkan layer ke map: {str(e)}")

class Unduh_Data_Integrasi_Dari_Sipenta(object):
    def __init__(self):
        self.label = "Unduh Data Integrasi Dari Sipenta"
        self.description = "Tool untuk mengunduh data pemetaan berdasarkan nomor integrasi."
        self.canRunInBackground = False

        self.NO_DATA_LABEL = "Tidak ada berkas yang dapat dipilih"
        self.GDB_NAME = "IntegrasiNilaiTanah.gdb"
        self.DATASET_NAME = "integrasi_ds"

        self._cached_token = None
        self._label_to_info = {}

    def _get_pemetaan_base_url(self):
        server = get_user_data(PREFERRED_SERVER_KEY)
        if server == "Produksi":
            return "https://sipenta.atrbpn.go.id/tatausaha/api/pemetaan"
        return "https://belajar.atrbpn.go.id/sipenta/tatausaha-2/api/pemetaan"

    def _get_base_url(self):
        return f"{self._get_pemetaan_base_url()}/integrasi"

    def get_no_integrasi(self, token):
        """Mengambil daftar integrasi dengan format tampilan 'no_integrasi - nama_wilayah'."""
        self._label_to_info = {}
        if not token:
            return []

        api_url = f"{self._get_base_url()}/list"
        headers = {"Authorization": f"Bearer {token}"}

        try:
            response = requests.get(api_url, headers=headers, timeout=15)
            response.raise_for_status()
            json_data = response.json()

            if not json_data.get("success"):
                return []

            data_list = json_data.get("data") or []
            integrasi_labels = []

            for item in data_list:
                if not isinstance(item, dict):
                    continue

                no_int = str(item.get("no_integrasi") or "").strip()
                nama_wilayah = str(item.get("nama_wilayah") or "").strip()

                if not no_int:
                    continue

                display_label = f"{no_int} - {nama_wilayah}" if nama_wilayah else no_int
                if display_label not in self._label_to_info:
                    self._label_to_info[display_label] = {
                        "no_integrasi": no_int,
                        "nama_wilayah": nama_wilayah,
                    }
                    integrasi_labels.append(display_label)

            return integrasi_labels

        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 403:
                try:
                    msg = e.response.json().get("message", "")
                    if "expired" in msg.lower():
                        clear_user_data()
                except Exception:
                    pass
            return []
        except Exception:
            return []

    def _extract_integrasi_info(self, selected_label):
        """Mengambil no_integrasi dan nama_wilayah dari teks pilihan dropdown."""
        if not selected_label:
            return "", ""
        if selected_label in self._label_to_info:
            info = self._label_to_info[selected_label]
            return info["no_integrasi"], info["nama_wilayah"]

        parts = selected_label.split(" - ", 1)
        no_int = parts[0].strip()
        wilayah = parts[1].strip() if len(parts) > 1 else ""
        return no_int, wilayah

    def _extract_no_berkas_sipenta(self, nama_sumber):
        """
        Mengekstrak nomor berkas jika nama_sumber memiliki pola 'Berkas Sipenta: XX/YYYY/ZZZZ'.
        """
        if not nama_sumber:
            return None

        text = str(nama_sumber).replace("\\/", "/").strip()
        match = re.search(r"berkas\s+sipenta\s*:\s*([^\s,;]+)", text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None

    def getParameterInfo(self):
        user_data = get_user_data(CREDENTIAL_KEY)
        token = user_data.get(AUTH_KEY) if user_data else None

        integrasi_list = self.get_no_integrasi(token) if token else []
        self._cached_token = token

        no_integrasi_show = integrasi_list if integrasi_list else [self.NO_DATA_LABEL]

        # 1. Parameter Nomor Integrasi
        no_integrasi = arcpy.Parameter(
            displayName="Nomor Integrasi",
            name="no_integrasi",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        no_integrasi.filter.type = "ValueList"
        no_integrasi.filter.list = no_integrasi_show
        if not integrasi_list:
            no_integrasi.value = self.NO_DATA_LABEL

        # 2. Parameter Folder Penyimpanan GDB
        output_folder = arcpy.Parameter(
            displayName="Folder Penyimpanan",
            name="output_folder",
            datatype="DEFolder",
            parameterType="Required",
            direction="Input"
        )
        output_folder.value = os.path.join(os.path.expanduser("~"), "Downloads")

        # 3. Parameter Penjelasan
        penjelasan = arcpy.Parameter(
            displayName="Informasi Tools",
            name="petunjuk",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )
        penjelasan.value = (
            "Login terlebih dahulu untuk mengakses fitur ini.\n\n"
            "Direktorat Penilaian Tanah dan Ekonomi Pertanahan,\n"
            "Kementerian ATR/BPN.\n"
            "Tahun: {}\n".format(datetime.now().year)
        )

        return [no_integrasi, output_folder, penjelasan]

    def updateParameters(self, parameters):
        no_integrasi = parameters[0]
        output_folder = parameters[1]
        penjelasan = parameters[2]

        user_data = get_user_data(CREDENTIAL_KEY)

        if user_data is None:
            no_integrasi.enabled = False
            output_folder.enabled = False
            penjelasan.enabled = True
            self._cached_token = None
            self._label_to_info = {}
        else:
            no_integrasi.enabled = True
            output_folder.enabled = True
            penjelasan.enabled = False

            token = user_data.get(AUTH_KEY)
            if token != self._cached_token:
                integrasi_list = self.get_no_integrasi(token)
                self._cached_token = token

                if integrasi_list:
                    no_integrasi.filter.list = integrasi_list
                    if no_integrasi.valueAsText not in integrasi_list:
                        no_integrasi.value = integrasi_list[0]
                else:
                    no_integrasi.filter.list = [self.NO_DATA_LABEL]
                    no_integrasi.value = self.NO_DATA_LABEL

        return

    def updateMessages(self, parameters):
        no_integrasi = parameters[0]
        user_data = get_user_data(CREDENTIAL_KEY)

        if user_data is not None:
            val = no_integrasi.valueAsText
            if not val or val == self.NO_DATA_LABEL:
                no_integrasi.setWarningMessage(
                    "Tidak ada berkas/nomor integrasi yang dapat dipilih. "
                    "Jika tool tetap dijalankan, proses unduh tidak akan dieksekusi."
                )
        return

    def execute(self, parameters, messages):
        user_data = get_user_data(CREDENTIAL_KEY)
        if not user_data:
            arcpy.AddError("Anda belum login. Silakan login terlebih dahulu.")
            return

        selected_label = parameters[0].valueAsText
        output_folder = parameters[1].valueAsText

        if not selected_label or selected_label == self.NO_DATA_LABEL:
            arcpy.AddWarning(
                "Peringatan: Tidak ada berkas/nomor integrasi yang dipilih atau tersedia. "
                "Proses unduh dibatalkan."
            )
            return

        token = user_data.get(AUTH_KEY, None)
        if not token:
            arcpy.AddError("Token autentikasi tidak ditemukan. Silakan login ulang.")
            return

        no_integrasi, fallback_wilayah = self._extract_integrasi_info(selected_label)
        self.download_from_sipenta(no_integrasi, token, output_folder, fallback_wilayah)
        return

    def _sanitize_fc_name(self, raw_name, used_names, fallback_index=1):
        """
        Menyesuaikan nama Feature Class agar valid untuk File Geodatabase
        (hanya huruf, angka, dan underscore; tanpa spasi; diawali huruf)
        serta menangani duplikasi nama (case-insensitive).
        """
        if raw_name is None or not str(raw_name).strip():
            clean = f"sumber_data_{fallback_index}"
        else:
            clean = str(raw_name).strip()

        clean = re.sub(r"[^A-Za-z0-9_]+", "_", clean)
        clean = re.sub(r"_+", "_", clean).strip("_")

        if not clean:
            clean = f"sumber_data_{fallback_index}"

        if not clean[0].isalpha():
            clean = f"fc_{clean}"

        max_base_len = 80
        base_name = clean[:max_base_len].rstrip("_")

        candidate = base_name
        counter = 1
        while candidate.lower() in used_names:
            suffix = f"_{counter}"
            allowed_len = max_base_len - len(suffix)
            candidate = f"{base_name[:allowed_len].rstrip('_')}{suffix}"
            counter += 1

        used_names.add(candidate.lower())
        return candidate

    def _ensure_gdb_and_dataset(self, output_folder, sample_sr=None):
        """
        Membuat File Geodatabase (IntegrasiNilaiTanah.gdb) dan Feature Dataset (integrasi_ds)
        jika belum tersedia, lalu mengembalikan path Feature Dataset.
        """
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        gdb_path = os.path.join(output_folder, self.GDB_NAME)
        if not arcpy.Exists(gdb_path):
            arcpy.AddMessage(f"Membuat File Geodatabase: {gdb_path} ...")
            arcpy.management.CreateFileGDB(
                out_folder_path=output_folder,
                out_name=self.GDB_NAME
            )

        fd_path = os.path.join(gdb_path, self.DATASET_NAME)
        if not arcpy.Exists(fd_path):
            sr = sample_sr
            if sr is None or getattr(sr, "name", "Unknown") == "Unknown":
                sr = arcpy.SpatialReference(4326)  # Default WGS 1984 (RFC 7946 GeoJSON)

            arcpy.AddMessage(
                f"Membuat Feature Dataset '{self.DATASET_NAME}' (SR: {sr.name}) ..."
            )
            arcpy.management.CreateFeatureDataset(
                out_dataset_path=gdb_path,
                out_name=self.DATASET_NAME,
                spatial_reference=sr
            )

        return fd_path

    def _group_features_by_geometry(self, geojson_obj):
        """
        Mengelompokkan feature berdasarkan keluarga geometri
        (Polygon/MultiPolygon, Point/MultiPoint, LineString/MultiLineString).
        """
        features = geojson_obj.get("features", [])
        groups = {"POLYGON": [], "POINT": [], "POLYLINE": []}

        for feat in features:
            geom = feat.get("geometry") or {}
            gtype = geom.get("type", "")
            if gtype in ("Polygon", "MultiPolygon"):
                groups["POLYGON"].append(feat)
            elif gtype in ("Point", "MultiPoint"):
                groups["POINT"].append(feat)
            elif gtype in ("LineString", "MultiLineString"):
                groups["POLYLINE"].append(feat)

        non_empty = {k: v for k, v in groups.items() if v}

        if len(non_empty) <= 1:
            return [(None, geojson_obj)]

        result = []
        for family, feats in non_empty.items():
            result.append((
                family.lower(),
                {"type": "FeatureCollection", "features": feats}
            ))
        return result

    def _add_sumber_id_field(self, fc_path, sumber_id):
        """Menambahkan field SUMBER_ID (TEXT) pada Feature Class dan mengisinya dengan nilai id."""
        field_name = "SUMBER_ID"
        existing_fields = [f.name.upper() for f in arcpy.ListFields(fc_path)]

        if field_name not in existing_fields:
            arcpy.management.AddField(
                in_table=fc_path,
                field_name=field_name,
                field_type="TEXT",
                field_length=50
            )

        with arcpy.da.UpdateCursor(fc_path, [field_name]) as cursor:
            for row in cursor:
                row[0] = sumber_id
                cursor.updateRow(row)

    def _convert_geojson_to_fc(
        self,
        geojson_data,
        base_label,
        output_folder,
        used_names,
        fallback_index=1,
        sumber_id=None,
        log_title=None
    ):
        """
        Mengonversi objek GeoJSON menjadi satu atau lebih Feature Class di dalam
        IntegrasiNilaiTanah.gdb\\integrasi_ds dan mengembalikan daftar path Feature Class.
        """
        display_title = log_title or base_label

        if isinstance(geojson_data, str):
            try:
                geojson_data = json.loads(geojson_data)
            except Exception:
                arcpy.AddWarning(f"Format string GeoJSON tidak valid pada '{display_title}', dilewati.")
                return []

        if not isinstance(geojson_data, dict) or not geojson_data.get("features"):
            arcpy.AddWarning(f"Data GeoJSON kosong pada '{display_title}', dilewati.")
            return []

        geom_batches = self._group_features_by_geometry(geojson_data)
        created_paths = []

        for geom_suffix, batch_geojson in geom_batches:
            raw_label = f"{base_label}_{geom_suffix}" if geom_suffix else base_label
            fc_name = self._sanitize_fc_name(raw_label, used_names, fallback_index=fallback_index)

            temp_geojson_path = None
            temp_mem_fc = f"memory\\tmp_json_{uuid.uuid4().hex[:10]}"

            try:
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".geojson", encoding="utf-8", delete=False
                ) as tmp_file:
                    json.dump(batch_geojson, tmp_file, ensure_ascii=False)
                    temp_geojson_path = tmp_file.name

                id_info = f" (ID: {sumber_id})" if sumber_id is not None else ""
                arcpy.AddMessage(
                    f"Mengonversi '{display_title}'{id_info} -> {self.GDB_NAME}\\{self.DATASET_NAME}\\{fc_name} ..."
                )

                arcpy.conversion.JSONToFeatures(
                    in_json_file=temp_geojson_path,
                    out_features=temp_mem_fc
                )

                if sumber_id is not None:
                    self._add_sumber_id_field(temp_mem_fc, sumber_id)

                src_sr = arcpy.Describe(temp_mem_fc).spatialReference
                fd_path = self._ensure_gdb_and_dataset(output_folder, sample_sr=src_sr)
                out_fc_path = os.path.join(fd_path, fc_name)

                ds_sr = arcpy.Describe(fd_path).spatialReference

                if arcpy.Exists(out_fc_path):
                    arcpy.management.Delete(out_fc_path)

                if (
                    src_sr
                    and ds_sr
                    and ds_sr.factoryCode != 0
                    and src_sr.factoryCode != ds_sr.factoryCode
                    and src_sr.name != ds_sr.name
                ):
                    arcpy.management.Project(
                        in_dataset=temp_mem_fc,
                        out_dataset=out_fc_path,
                        out_coor_system=ds_sr
                    )
                else:
                    arcpy.conversion.FeatureClassToFeatureClass(
                        in_features=temp_mem_fc,
                        out_path=fd_path,
                        out_name=fc_name
                    )

                created_paths.append(out_fc_path)

            finally:
                if arcpy.Exists(temp_mem_fc):
                    try:
                        arcpy.management.Delete(temp_mem_fc)
                    except Exception:
                        pass
                if temp_geojson_path and os.path.exists(temp_geojson_path):
                    try:
                        os.remove(temp_geojson_path)
                    except OSError:
                        pass

        return created_paths

    def _fetch_and_convert_nearby(self, no_berkas, token, output_folder, used_names):
        """
        Mengambil data nearby dari endpoint /api/pemetaan/nearby berdasarkan no_berkas,
        lalu mengonversi geojson_berkas -> Nearby_Data_Terkini
        dan geojson_dashboard -> Nearby_Data_Lampau ke dalam Feature Dataset.
        """
        arcpy.AddMessage(
            f"Mengambil data nearby untuk nomor berkas '{no_berkas}' "
            f"(mohon tunggu, ukuran data bisa cukup besar)..."
        )

        api_url = f"{self._get_pemetaan_base_url()}/nearby"
        headers = {"Authorization": f"Bearer {token}"}
        params = {"no_berkas": no_berkas}

        try:
            response = requests.get(api_url, headers=headers, params=params, timeout=(30, 300))
            response.raise_for_status()
            json_data = response.json()

            if not json_data.get("success"):
                msg = json_data.get("message", "Gagal mengambil data nearby dari server.")
                arcpy.AddWarning(f"Data nearby untuk berkas '{no_berkas}' gagal diambil: {msg}")
                return []

            nearby_data = json_data.get("data") or {}
            geojson_berkas = nearby_data.get("geojson_berkas") or nearby_data.get("berkas")
            geojson_dashboard = nearby_data.get("geojson_dashboard") or nearby_data.get("dashboard")

            nearby_fc_paths = []

            if geojson_berkas:
                nearby_fc_paths.extend(
                    self._convert_geojson_to_fc(
                        geojson_data=geojson_berkas,
                        base_label="Nearby_Data_Terkini",
                        output_folder=output_folder,
                        used_names=used_names,
                        fallback_index=1,
                        sumber_id=None,
                        log_title=f"Nearby Berkas ({no_berkas})"
                    )
                )
            else:
                arcpy.AddWarning(f"Tidak ditemukan geojson_berkas pada data nearby '{no_berkas}'.")

            if geojson_dashboard:
                nearby_fc_paths.extend(
                    self._convert_geojson_to_fc(
                        geojson_data=geojson_dashboard,
                        base_label="Nearby_Data_Lampau",
                        output_folder=output_folder,
                        used_names=used_names,
                        fallback_index=2,
                        sumber_id=None,
                        log_title=f"Nearby Dashboard ({no_berkas})"
                    )
                )
            else:
                arcpy.AddWarning(f"Tidak ditemukan geojson_dashboard pada data nearby '{no_berkas}'.")

            return nearby_fc_paths

        except requests.exceptions.HTTPError as e:
            resp = e.response
            message = ""
            try:
                message = resp.json().get("message", "")
            except Exception:
                pass
            status_code = resp.status_code if resp is not None else "Unknown"
            arcpy.AddWarning(
                f"Gagal mengambil data nearby untuk berkas '{no_berkas}' "
                f"(HTTP {status_code}): {message or str(e)}"
            )
            return []
        except Exception as e:
            arcpy.AddWarning(
                f"Terjadi kesalahan saat mengunduh/mengonversi data nearby '{no_berkas}': {str(e)}"
            )
            return []

    def _add_folder_connection(self, folder_path):
        """Menambahkan folder penyimpanan ke Folder Connections pada project ArcGIS Pro aktif."""
        if not folder_path or not os.path.exists(folder_path):
            return

        try:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            abs_folder = os.path.abspath(folder_path)
            target_norm = os.path.normcase(abs_folder)

            connections = list(aprx.folderConnections or [])
            already_connected = any(
                os.path.normcase(os.path.abspath(conn.get("connectionString", ""))) == target_norm
                for conn in connections
                if conn.get("connectionString")
            )

            if not already_connected:
                connections.append({
                    "connectionString": abs_folder,
                    "alias": "",
                    "isHomeFolder": False
                })
                aprx.updateFolderConnections(connections)
                arcpy.AddMessage(
                    f"Folder '{abs_folder}' berhasil ditambahkan ke Folder Connections."
                )
            else:
                arcpy.AddMessage(
                    f"Folder '{abs_folder}' sudah terdaftar di Folder Connections."
                )
        except Exception as e:
            arcpy.AddWarning(
                f"Gagal menambahkan folder ke Folder Connections secara otomatis: {str(e)}"
            )

    def _add_feature_classes_to_map(self, fc_paths):
        """Menambahkan seluruh Feature Class hasil konversi ke Map yang sedang aktif."""
        if not fc_paths:
            return

        try:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            active_map = aprx.activeMap

            if active_map is None:
                maps = aprx.listMaps()
                if maps:
                    active_map = maps[0]

            if active_map is None:
                arcpy.AddWarning(
                    "Tidak ditemukan Map yang terbuka di project ArcGIS Pro. "
                    "Feature Class tetap tersimpan di dalam Geodatabase."
                )
                return

            added_count = 0
            for fc_path in fc_paths:
                if arcpy.Exists(fc_path):
                    active_map.addDataFromPath(fc_path)
                    added_count += 1

            if added_count > 0:
                arcpy.AddMessage(
                    f"{added_count} Feature Class berhasil ditambahkan ke Map '{active_map.name}'."
                )
        except Exception as e:
            arcpy.AddWarning(
                f"Feature Class berhasil disimpan, namun gagal ditambahkan otomatis ke Map: {str(e)}"
            )

    def download_from_sipenta(self, no_integrasi, token, output_folder, fallback_wilayah=""):
        arcpy.AddMessage(f"Mengambil detail data integrasi: {no_integrasi}...")

        api_url = f"{self._get_base_url()}/detail"
        headers = {"Authorization": f"Bearer {token}"}
        params = {"no_integrasi": no_integrasi}

        try:
            response = requests.get(api_url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            json_data = response.json()

            if not json_data.get("success"):
                raise Exception(json_data.get("message", "Gagal mengambil detail integrasi dari server."))

            detail_data = json_data.get("data", {})
            raw_wilayah = str(detail_data.get("nama_wilayah") or "").strip()
            if not raw_wilayah or raw_wilayah == "-":
                raw_wilayah = fallback_wilayah

            nama_wilayah_display = raw_wilayah if raw_wilayah else "-"
            jenis_integrasi = detail_data.get("jenis_integrasi", "-")
            tahun = detail_data.get("tahun", "-")
            zona_tm3 = detail_data.get("zona_tm3", "-")

            arcpy.AddMessage(
                f"Info Integrasi -> Jenis: {jenis_integrasi} | Wilayah: {nama_wilayah_display} | "
                f"Tahun: {tahun} | Zona TM-3: {zona_tm3}"
            )

            sumber_data_list = detail_data.get("sumber_data", [])
            if not sumber_data_list:
                arcpy.AddWarning(f"Tidak ditemukan sumber_data pada integrasi {no_integrasi}.")
                return

            prev_overwrite = arcpy.env.overwriteOutput
            arcpy.env.overwriteOutput = True

            used_names = set()
            created_fc_paths = []
            berkas_sipenta_list = []

            try:
                for idx, sumber in enumerate(sumber_data_list, start=1):
                    raw_id = sumber.get("id")
                    sumber_id = str(raw_id).strip() if raw_id is not None else ""
                    nama_sumber = sumber.get("nama_sumber")
                    geojson_data = sumber.get("geojson")

                    # Cek apakah nama_sumber mengandung nomor berkas Sipenta
                    extracted_berkas = self._extract_no_berkas_sipenta(nama_sumber)
                    if extracted_berkas and extracted_berkas not in berkas_sipenta_list:
                        berkas_sipenta_list.append(extracted_berkas)

                    clean_sumber_title = (
                        str(nama_sumber).strip()
                        if (nama_sumber and str(nama_sumber).strip())
                        else f"sumber_data_{idx}"
                    )
                    raw_label = f"{raw_wilayah}_{clean_sumber_title}" if raw_wilayah else clean_sumber_title

                    fc_paths = self._convert_geojson_to_fc(
                        geojson_data=geojson_data,
                        base_label=raw_label,
                        output_folder=output_folder,
                        used_names=used_names,
                        fallback_index=idx,
                        sumber_id=sumber_id,
                        log_title=clean_sumber_title
                    )
                    created_fc_paths.extend(fc_paths)

                # Jika ditemukan nomor berkas Sipenta, tarik dan konversi data nearby-nya
                for no_berkas in berkas_sipenta_list:
                    nearby_paths = self._fetch_and_convert_nearby(
                        no_berkas=no_berkas,
                        token=token,
                        output_folder=output_folder,
                        used_names=used_names
                    )
                    created_fc_paths.extend(nearby_paths)

            finally:
                arcpy.env.overwriteOutput = prev_overwrite

            if created_fc_paths:
                target_ds_path = os.path.join(output_folder, self.GDB_NAME, self.DATASET_NAME)
                arcpy.AddMessage(
                    f"Selesai! {len(created_fc_paths)} Feature Class berhasil disimpan di: {target_ds_path}"
                )
                self._add_folder_connection(output_folder)
                self._add_feature_classes_to_map(created_fc_paths)
            else:
                arcpy.AddWarning("Tidak ada layer GeoJSON yang berhasil dikonversi menjadi Feature Class.")

        except requests.exceptions.HTTPError as e:
            resp = e.response
            message = ""
            try:
                message = resp.json().get("message", "")
            except Exception:
                pass

            if resp is not None and resp.status_code == 403 and "expired" in message.lower():
                clear_user_data()
                arcpy.AddError("Token Anda kadaluarsa, silakan login ulang.")
            elif resp is not None and resp.status_code == 403:
                arcpy.AddError("Akses ditolak (403). Periksa hak akses atau token.")
            elif resp is not None and resp.status_code == 404:
                arcpy.AddError("Data integrasi tidak ditemukan (404) di server.")
            else:
                status_code = resp.status_code if resp is not None else "Unknown"
                arcpy.AddError(f"HTTP Error {status_code}: {message or str(e)}")

        except Exception as e:
            arcpy.AddError(f"Terjadi kesalahan saat proses unduh dan konversi: {str(e)}")