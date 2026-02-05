import arcpy, os, math
from ogisinternalutils.document import get_credentials as _get_creds_for_flag


class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = " Pemberian Kelas Nilai"
        self.alias = ""

        # List of tool classes associated with this toolbox
        self.tools = [Pemberian_Kelas_Nilai]


class Pemberian_Kelas_Nilai(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Pemberian Kelas Nilai"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        pilih_znt = arcpy.Parameter(
            displayName="Pilih Shapefile",
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

        nomorzone.parameterDependencies = [pilih_znt.name]

        nilai = arcpy.Parameter(
            displayName="Pilih Field Nilai",
            name="nilai_field",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        nilai.parameterDependencies = [pilih_znt.name]

        tahun = arcpy.Parameter(
            displayName="Pilih Field Tahun Pembuatan",
            name="tahun_field",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        tahun.parameterDependencies = [pilih_znt.name]

        bulandibuat = arcpy.Parameter(
            displayName="Pilih Field Bulan Pembuatan",
            name="bulandibuat_field",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )

        bulandibuat.parameterDependencies = [pilih_znt.name]

        znt_shp_output = arcpy.Parameter(
            displayName="Pilih Tempat Penyimpanan Shapefile ZNT",
            name="znt_shp_output",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output"
        )

        penjelasan = arcpy.Parameter(
            displayName="Maaf, Anda tidak memiliki akses untuk menjalankan tools ini.",
            name="penjelasan",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )
        penjelasan.value = (
            "Tools ini hanya untuk Operator GIS Internal\n"
            "\n"
        )
        self.operatorGIS = bool(_get_creds_for_flag(credential_type="OperatorGISInternal", use_for_tools_validity=True))
        if self.operatorGIS:
            return [pilih_znt, nomorzone, nilai, tahun, bulandibuat, znt_shp_output]
        else:
            return [penjelasan]
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
        """The source code of the tool."""
        self.operatorgis = bool(_get_creds_for_flag(credential_type="OperatorGISInternal", use_for_tools_validity=True))
        if self.operatorgis:
            pilih_znt = parameters[0].valueAsText
            nomorzone = parameters[1].valueAsText
            nilai = parameters[2].valueAsText
            tahun = parameters[3].valueAsText
            bulandibuat = parameters[4].valueAsText
            znt_shp_output = parameters[5].valueAsText

            self.output_shapefile = znt_shp_output

            self.mapping_fields = {
            'nomorzone': nomorzone,
            'nilai': nilai,
            'tahun': tahun,
            'bulan': bulandibuat,
            }

            self.setup_path_and_configuration(pilih_znt)
            self.check_field_compatibility(pilih_znt, self.mapping_fields)
            self.check_and_prepare_nomor_zona(pilih_znt, self.mapping_fields)
            self.penggabungan_geometri_dan_atribut(pilih_znt, self.mapping_fields)
            self.penentuan_kelas_dan_range()
            self.penyimpanan_hasil()
            
            # Jalankan validasi topologi dan tampilkan ke map
            self.validasi_topologi_dan_tampilkan_ke_map()

            arcpy.AddMessage("Proses pemberian kelas dan range nilai selesai.")
        else:
            arcpy.AddError("Anda tidak memiliki akses untuk menjalankan tools ini.")
        return
    
    def setup_path_and_configuration(self, reference_layer):

        appdata = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))
        
        folder_temp_path = os.path.join(appdata, "temp")
        self.folder_temp_path = folder_temp_path

        self.spatial_ref = arcpy.Describe(reference_layer).spatialReference


        self.merge_zl = os.path.join(folder_temp_path, 'Layer_ZNT_Gabungan.shp')


        if not arcpy.Exists(folder_temp_path):
            raise Exception("Dataset tidak ditemukan!")

        if arcpy.Exists(self.merge_zl):
            arcpy.management.Delete(self.merge_zl)

        

        fields = [("nomorzone", "LONG"),
                ("nilai", "DOUBLE"),
                ("tahun", "TEXT"),
                ("bulan", "TEXT"),
                ("luasbatas", "DOUBLE"),
                ("kelas", "SHORT")]
        
        self.merge_zl_fields = fields

        arcpy.management.CreateFeatureclass(
            out_path=folder_temp_path,
            out_name="Layer_ZNT_Gabungan",
            geometry_type="POLYGON",
            spatial_reference=arcpy.Describe(reference_layer).spatialReference
        )
        
        for name, ftype in fields:
            arcpy.management.AddField(self.merge_zl, name, ftype)

    def check_field_compatibility(self, layer, mapping_fields):
        """Cek apakah field-field yang dipilih sesuai dengan tipe data yang diharapkan dan tidak ada nilai null."""
        field_info = arcpy.ListFields(layer)
        field_dict = {field.name: field for field in field_info}

        expected_field_types = {
            'nomorzone': ('Field Nomor Zona', [  'Double', 'Integer' ]),
            'nilai': ('Field Nilai ZNT', [  'Double', 'Integer' ]),
            'tahun': ('Field Tahun Dibuat', [ 'Integer', 'String' ]),
            'bulan': ('Field Bulan Dibuat', [ 'Integer', 'String' ]),
        }

        for key, field_name in mapping_fields.items():
            if field_name not in field_dict:
                raise ValueError(f"Field '{field_name}' tidak ditemukan pada layer.")
            actual_type = field_dict[field_name].type
            expected_type = expected_field_types[key][1]
            if actual_type not in expected_type:
                raise TypeError(f"Field '{field_name}' harus bertipe '{expected_type}' agar dapat digunakan untuk mengisi {expected_field_types[key][0]}, tetapi ditemukan '{actual_type}'.")

        # Validasi tambahan: jika tahun/bulan berupa String, pastikan nilainya string angka (digit-only)
        for key, field_name in mapping_fields.items():
            if key in ('tahun', 'bulan') and field_dict[field_name].type == 'String':
                non_numeric_examples = []
                count_non_numeric = 0
                with arcpy.da.SearchCursor(layer, [field_name]) as cursor:
                    for row in cursor:
                        val = row[0]
                        if val is None:
                            continue  # null akan ditangani oleh pengecekan null di bawah
                        if isinstance(val, (int, float)):
                            continue
                        s = str(val).strip()
                        if not s.isdigit():
                            count_non_numeric += 1
                            if len(non_numeric_examples) < 5:
                                non_numeric_examples.append(s)
                if count_non_numeric > 0:
                    examples_str = ", ".join(non_numeric_examples)
                    raise ValueError(
                        f"{expected_field_types[key][0]} bertipe 'String' namun berisi nilai non-angka sebanyak {count_non_numeric} baris. Contoh: {examples_str}.\n"
                        "Mohon pastikan seluruh nilai berformat string angka (misal '2024', '12')."
                    )
        
        # Cek apakah ada nilai null di field yang diperlukan
        null_counts = {}
        for key, field_name in mapping_fields.items():
            null_count = 0
            with arcpy.da.SearchCursor(layer, [field_name]) as cursor:
                for row in cursor:
                    if row[0] is None:
                        null_count += 1
            if null_count > 0:
                null_counts[expected_field_types[key][0]] = null_count
        
        if null_counts:
            error_msg = "Ditemukan nilai null pada field berikut:\n"
            for field_desc, count in null_counts.items():
                error_msg += f"  - {field_desc}: {count} baris\n"
            error_msg += "Mohon pastikan semua field memiliki nilai yang valid."
            raise ValueError(error_msg)

        return
    
    def check_and_prepare_nomor_zona(self, layer, mapping_fields):
        """
        Memastikan tidak ada nomor zona yang null atau terduplikat.
        Jika ada duplikasi, zona dengan nilai tertinggi mempertahankan nomor zonanya,
        yang lain di-null-kan kemudian diisi ulang dengan max(nozone) + 1.
        """
        nomorzone_field = mapping_fields['nomorzone']
        nilai_field = mapping_fields['nilai']

        # Kumpulkan data zona: {nomorzone: [(FID, nilai), ...]}
        zona_data = {}
        
        with arcpy.da.SearchCursor(layer, ['OID@', nomorzone_field, nilai_field]) as cursor:
            for row in cursor:
                fid, nozone, nilai = row
                if nozone is not None:
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
        
        # Cari nomor zona maksimum yang valid
        max_nozone = 0
        with arcpy.da.SearchCursor(layer, [nomorzone_field]) as cursor:
            for row in cursor:
                if row[0] is not None and row[0] > max_nozone:
                    max_nozone = int(row[0])
        
        # Isi ulang nomor zona yang sudah ditandai dengan auto-increment
        current_nozone = max_nozone
        with arcpy.da.UpdateCursor(layer, [nomorzone_field]) as cursor:
            for row in cursor:
                if row[0] == -1:
                    current_nozone += 1
                    row[0] = current_nozone
                    cursor.updateRow(row)

    def penggabungan_geometri_dan_atribut(self, layer, mapping_fields):
        """Fungsi untuk menggabungkan ZNT lama dengan ZNT baru berdasarkan field mapping yang diberikan."""

        insert_fields = [f[0] for f in self.merge_zl_fields] + ["SHAPE@"]

        src_fields = [
            mapping_fields['nomorzone'],
            mapping_fields['nilai'],
            mapping_fields['tahun'],
            mapping_fields['bulan'],
            'SHAPE@'
        ]
        
        # Ambil nomor zona tertinggi dari self.merge_zl
        max_nomorzone = 0
        try:
            nomorzone_list = [row[0] for row in arcpy.da.SearchCursor(self.merge_zl, ["nomorzone"]) if row[0] is not None]
            if nomorzone_list:
                max_nomorzone = max(nomorzone_list)
        except Exception:
            max_nomorzone = 0
        
        current_nomorzone = max_nomorzone
        with arcpy.da.InsertCursor(self.merge_zl, insert_fields) as icur:
            with arcpy.da.SearchCursor(layer, src_fields) as scur:
                for srow in scur:

                    geom = srow[-1]
                    try:
                        luas_m2 = round(geom.getArea('GEODESIC', 'SQUAREMETERS'))
                    except Exception:
                        # fallback ke planar area jika perlu
                        luas_m2 = round(geom.area) if hasattr(geom, 'area') else None
                    
                    # Increment nomor zona
                    current_nomorzone += 1
            
                    icur.insertRow([
                            current_nomorzone,                                # nomorzone (auto increment)
                            float(srow[1]) if srow[1] is not None else None, # nilai
                            str(srow[2]) if srow[2] is not None else None,   # tahun
                            str(srow[3]) if srow[3] is not None else None,   # bulandibuat
                            float(luas_m2) if luas_m2 is not None else None, # luasbatas (m2)
                            1,                                             # kelas (kosong)
                            geom                                              # SHAPE@
                        ])
                    
    def penentuan_kelas_dan_range(self):
        fields = ["nilai", "rangenilai", "kelas"]

        # Tambah field rangenilai bila belum ada
        existing_fields = [f.name for f in arcpy.ListFields(self.merge_zl)]
        if "rangenilai" not in existing_fields:
            arcpy.management.AddField(self.merge_zl, "rangenilai", "TEXT")

        # Kumpulkan semua nilai, urutkan, lalu bagi menjadi 8 kelas dengan frekuensi sama
        # Kumpulkan nilai asli terlebih dahulu untuk bisa mendeteksi nilai maksimum
        raw_values = []
        with arcpy.da.SearchCursor(self.merge_zl, ["nilai"]) as scur:
            for srow in scur:
                v = srow[0]
                if v is None:
                    continue
                try:
                    raw_values.append(float(v))
                except Exception:
                    continue

        if not raw_values:
            arcpy.AddWarning("Tidak ada nilai numeric untuk dibagi kelas.")
            return

        # Tentukan nilai maksimum asli
        max_raw = max(raw_values)

        # Bulatkan nilai: kebanyakan dibulatkan ke ribuan (round),
        # namun jika nilai adalah nilai maksimum, lakukan pembulatan ke atas (ceiling) ke ribuan.
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

        if not nilai_list:
            arcpy.AddWarning("Tidak ada nilai numeric untuk dibagi kelas.")
            return

        nilai_sorted = sorted(nilai_list)
        n = len(nilai_sorted)

        # Bangun batas kelas (batas_kelas) sebanyak 9 nilai (8 kelas)
        batas_kelas = []
        for i in range(9):
            if i == 0:
                batas_kelas.append(nilai_sorted[0])
            elif i == 8:
                batas_kelas.append(nilai_sorted[-1])
            else:
                idx = int(math.ceil(i * n / 8.0)) - 1
                idx = max(0, min(idx, n - 1))
                batas_kelas.append(nilai_sorted[idx])

        # Bulatkan batas ke integer dan pastikan tidak tumpang tindih.
        # Jika batas atas kelas sebelumnya = X, maka batas bawah kelas berikutnya = X + 1.
        batas_kelas_int = [int(round(x)) for x in batas_kelas]

        # Gunakan batas_kelas_int selanjutnya
        batas_kelas = batas_kelas_int

        def tentukan_kelas(v):
            # Kembalikan kelas 1..8 berdasarkan batas_kelas (integer)
            for i in range(1, 9):
                low = batas_kelas[i - 1]
                high = batas_kelas[i]
                if low <= v <= high:
                    return i
            return 8 if v >= batas_kelas[-1] else 1

        def format_range(low, high):
            # Format range sebagai integer (sudah dibulatkan)
            return f"{int(low)} - {int(high)}"

        # Update field rangenilai dan kelas
        with arcpy.da.UpdateCursor(self.merge_zl, fields) as cursor:
            for row in cursor:
                nilai = row[0]
                if nilai is None:
                    continue
                try:
                    v = float(nilai)
                except Exception:
                    continue
                kelas = tentukan_kelas(v)
                if kelas == 1:
                    range_str = format_range(batas_kelas[0], batas_kelas[1])
                else:
                    range_str = format_range(batas_kelas[kelas - 1] + 1, batas_kelas[kelas] )
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
        return
    
    def validasi_topologi_dan_tampilkan_ke_map(self):
        """
        Validasi topologi layer hasil penggabungan dengan aturan:
        1. Must Not Have Gaps (Area)
        2. Must Not Overlap (Area)
        Kemudian tampilkan hasilnya ke map aktif.
        """
        try:
            # Ambil active map
            aprx = arcpy.mp.ArcGISProject('CURRENT')
            active_map = aprx.activeMap
            
            arcpy.AddMessage("Memulai validasi topologi layer ZNT Gabungan...")
            
            # Buat temporary dataset untuk topology
            top_gdb_path = os.path.join(self.folder_temp_path, 'topo_validation.gdb')
            
            # Hapus GDB lama jika ada
            if arcpy.Exists(top_gdb_path):
                arcpy.management.Delete(top_gdb_path)
            
            # Buat file GDB baru
            arcpy.management.CreateFileGDB(self.folder_temp_path, 'topo_validation.gdb')
            dataset_name = 'topo_ds'
            coord = arcpy.Describe(self.merge_zl).spatialReference
            topo_dataset_path = os.path.join(top_gdb_path, dataset_name)
            arcpy.CreateFeatureDataset_management(top_gdb_path, dataset_name, coord)
            arcpy.AddMessage("File GDB untuk validasi topologi berhasil dibuat.")
            # Copy layer ke dalam GDB untuk validasi topologi
            topo_layer_name = 'Zona_Gabungan_Topo'
            arcpy.conversion.FeatureClassToFeatureClass(
                in_features=self.merge_zl,
                out_path=topo_dataset_path,
                out_name=topo_layer_name
            )
            
            topo_layer_path = os.path.join(topo_dataset_path, topo_layer_name)
            arcpy.AddMessage("Layer ZNT Gabungan berhasil disalin ke dalam GDB untuk validasi topologi.")
            # Buat topology
            topo_name = 'Validasi_ZNT_Topologi'
            arcpy.CreateTopology_management(
                topo_dataset_path,
                topo_name,
            )
            arcpy.AddMessage("Topology berhasil dibuat.")
            topo_path = os.path.join(topo_dataset_path, topo_name)
            
            # Tambahkan layer ke topology
            arcpy.AddFeatureClassToTopology_management(
                topo_path,
                topo_layer_path,
                1,
                1
            )
            
            # Tambahkan topology rules
            # Rule 1: Must Not Have Gaps (Area)
            arcpy.management.AddRuleToTopology(
                topo_path,
                "Must Not Have Gaps (Area)",
                topo_layer_path,

            )
            
            # Rule 2: Must Not Overlap (Area)
            arcpy.management.AddRuleToTopology(
                topo_path,
                "Must Not Overlap (Area)",
                topo_layer_path,

            )
            
            arcpy.AddMessage("Topology rules berhasil ditambahkan.")
            
            # Validasi topology
            arcpy.ValidateTopology_management(in_topology=topo_path)
            arcpy.AddMessage("Validasi topologi selesai.")
            
            # Tampilkan hasil ke map aktif
            self.tampilkan_ke_active_map(topo_path, topo_dataset_path, active_map)
            
            arcpy.AddMessage("Layer ZNT Gabungan berhasil ditampilkan di map aktif dengan validasi topologi.")
            
        except Exception as e:
            arcpy.AddError(f"Error dalam validasi topologi: {str(e)}")
            # Fallback: Tampilkan tanpa topologi
            try:
                aprx = arcpy.mp.ArcGISProject('CURRENT')
                active_map = aprx.activeMap
                self.tampilkan_ke_active_map(self.output_shapefile, None, active_map)
            except:
                arcpy.AddWarning("Gagal menampilkan layer ke map.")
    
    def tampilkan_ke_active_map(self, layer_path, workspace_path=None, map_object=None):
        """
        Tampilkan layer ke active map.
        
        Parameters:
            layer_path (str): Path ke layer/feature class yang akan ditampilkan
            workspace_path (str): Path ke workspace (untuk layer dalam GDB)
            map_object: ArcGIS Map object
        """
        try:
            if map_object is None:
                aprx = arcpy.mp.ArcGISProject('CURRENT')
                map_object = aprx.activeMap
            
            # Cek apakah layer sudah ada di map
            layer_name = os.path.basename(layer_path)
            existing_layers = map_object.listLayers(layer_name)
            
            for existing_layer in existing_layers:
                map_object.removeLayer(existing_layer)
            
            # Tambahkan layer baru
            map_object.addDataFromPath(layer_path)
            arcpy.AddMessage(f"Layer '{layer_name}' berhasil ditampilkan di map aktif.")
            
        except Exception as e:
            arcpy.AddWarning(f"Gagal menampilkan layer ke map: {str(e)}")

