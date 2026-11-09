import os
import math
import arcpy

arcpy.env.outputZFlag = "Disabled"
arcpy.env.outputMFlag = "Disabled"

class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the .pyt file)."""
        self.label = "Toolbox"
        self.alias = "toolbox"
        # List of tool classes associated with this toolbox
        self.tools = [Penggabungan_ZNT_Manual]


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
        
        self.operatorGIS = True
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
        self.operatorGIS = True
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
        
        self.penentuan_kelas_dan_range()
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
            'nilai': ('Field Nilai ZNT', ['Double', 'Integer']),
            'tahun': ('Field Tahun Dibuat', ['Integer', 'String']),
            'bulan': ('Field Bulan Dibuat', ['SmallInteger','Integer', 'String']),
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