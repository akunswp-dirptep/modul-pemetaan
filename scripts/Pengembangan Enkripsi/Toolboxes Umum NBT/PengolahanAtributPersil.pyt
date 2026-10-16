import arcpy, os, sys, math
from collections import Counter

script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from nbtutils import persil, constant

class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [Build_Network_Dataset_Jaringan_Jalan,
                      Menentukan_Perubahan_Mengelompok,
                      Menghitung_Luas_Bidang,
                      Pengisian_Bentuk_Persil_Otomatis,
                      Pengisian_Bentuk_Persil_Manual,
                      Pengisian_WADMKC_WADMKD_Otomatis,
                      Pengisian_WADMKC_WADMKD_Manual,
                      Pengisian_Kelas_dan_Lebar_Jalan_Otomatis,
                      Pengisian_Kelas_dan_Lebar_Jalan_Manual,
                      Pengisian_Letak_Otomatis,
                      Pengisian_Letak_Manual,
                      Pengisian_Lebar_Depan_Otomatis,
                      Pengisian_Jarak_Ke_Jalan_Utama_Otomatis,
                      Pengisian_Zonasi_Manual,
                      Pengisian_Zonasi_Otomatis,
                      FilterPersilJalan
                      ]



class Build_Network_Dataset_Jaringan_Jalan(object):

    def __init__(self):
        self.label = "Build Network Dataset Jaringan Jalan"
        self.description = "Tool untuk memproses dan membangun ulang Network Dataset Jaringan Jalan."
        self.canRunInBackground = False

    def getParameterInfo(self):
        output_nd = arcpy.Parameter(
            displayName="Output Network Dataset",
            name="output_nd",
            datatype="DENetworkDataset",
            parameterType="Derived",
            direction="Output"
        )

        output_jalan_nd = arcpy.Parameter(
            displayName="Output Jaringan Jalan ND",
            name="output_jalan_nd",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        output_junction = arcpy.Parameter(
            displayName="Output Junction ND",
            name="output_junction",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [output_nd, output_jalan_nd, output_junction]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        messages.addMessage("== Proses dimulai ==")
        
        # 1. SETUP VARIABEL DAN PATH
        configs = persil.get_config_values()
        dataset_path = configs["project_config"]["dataset_path"]
        gdb_path = configs["project_config"]["gdb_path"]
        
        jaringan_jalan = 'Jaringan_Jalan'
        fd_template_path = os.path.join(gdb_path, constant.FD_TEMPLATE_JARINGAN_JALAN)
        jaringanjalan_path = os.path.join(dataset_path, jaringan_jalan)
        
        nd_path = os.path.join(fd_template_path, constant.TEMPLATE_LAYER_NETWORK_DATASET_JARINGAN_JALAN)
        template_fc_jarjal = os.path.join(fd_template_path, constant.TEMPLATE_LAYER_FEATURE_CLASS_JARINGAN_JALAN)
        
        junction_path = os.path.join(dataset_path, "Junction")
        junction_nd_path = os.path.join(fd_template_path, "JaringanJalan_ND_Junctions")
        junction_diss_path = os.path.join(dataset_path, "junction_diss")
        junction_final_path = os.path.join(dataset_path, "JunctionFinal")

        # 2. BERSIH-BERSIH LOCK DI MAP
        messages.addMessage("== Bersih-bersih network dataset ==")
        try:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            current_map = aprx.activeMap
            
            if current_map:
                nama_jalan_nd_fc = os.path.basename(template_fc_jarjal)
                nama_junction_nd_fc = os.path.basename(junction_nd_path)
                
                target_layers = [
                    "JaringanJalan_ND", 
                    "JaringanJalanForND", 
                    "JaringanJalan_ND_Junctions",
                    nama_jalan_nd_fc,
                    nama_junction_nd_fc
                ]
                
                for lyr in current_map.listLayers():
                    if lyr.name in target_layers:
                        current_map.removeLayer(lyr)
                        messages.addMessage(f"Membuka lock: Layer '{lyr.name}' berhasil dihapus dari Map.")
        except Exception as e:
            messages.addMessage("Info: Berjalan di luar Pro atau gagal membersihkan map lock.")

        # 3. KOSONGKAN TEMPLATE
        try:
            arcpy.management.TruncateTable(template_fc_jarjal)
            messages.addMessage("Data lama berhasil dikosongkan menggunakan Truncate.")
        except Exception:
            try:
                arcpy.management.DeleteRows(template_fc_jarjal)
                messages.addMessage("Data lama dikosongkan menggunakan DeleteRows.")
            except Exception as e:
                messages.addErrorMessage(f"Gagal mengosongkan template FC: {str(e)}")

        # 4. VALIDASI KELAS JALAN & PERSIAPAN FIELD
        messages.addMessage("== Validasi kelas jalan ==")
        lyr_temp_jalan = "lyr_temp_jalan"

        if arcpy.Exists(lyr_temp_jalan):
            arcpy.management.Delete(lyr_temp_jalan)

        kls_jln = arcpy.AddFieldDelimiters(jaringanjalan_path, "kls_jln")
        s_klsjln = arcpy.AddFieldDelimiters(jaringanjalan_path, "s_klsjln")
        where_clause = f"{kls_jln} IS NULL OR {s_klsjln} IS NULL"

        # Set default untuk jalan yang Null
        arcpy.management.MakeFeatureLayer(jaringanjalan_path, lyr_temp_jalan, where_clause)
        arcpy.management.CalculateField(lyr_temp_jalan, "kls_jln", '"Setapak"', "PYTHON3")
        arcpy.management.CalculateField(lyr_temp_jalan, "s_klsjln", "1", "PYTHON3")
        
        if arcpy.Exists(lyr_temp_jalan):
            arcpy.management.Delete(lyr_temp_jalan)

        # Cek dan Tambah Field
        field_names = [field.name for field in arcpy.ListFields(jaringanjalan_path)]
        if "IdJalan" not in field_names:
            arcpy.management.AddField(jaringanjalan_path, "IdJalan", "LONG")
        if "P_Jalan" not in field_names:
            arcpy.management.AddField(jaringanjalan_path, "P_Jalan", "DOUBLE")

        # Kalkulasi Panjang & ID
        arcpy.management.CalculateField(jaringanjalan_path, "P_Jalan", "!SHAPE.length!", "PYTHON3")
        
        oid_field_name = arcpy.Describe(jaringanjalan_path).OIDFieldName
        arcpy.management.CalculateField(jaringanjalan_path, "IdJalan", f"!{oid_field_name}!", "PYTHON3")

        field_names_nd = [field.name for field in arcpy.ListFields(template_fc_jarjal)]
        if "IdJalan" not in field_names_nd:
            arcpy.management.AddField(template_fc_jarjal, "IdJalan", "LONG")

        # 5. APPEND DATA & BUILD NETWORK
        messages.addMessage("== Append data jaringan jalan ke ND ==")
        arcpy.management.Append([jaringanjalan_path], template_fc_jarjal, "NO_TEST")

        messages.addMessage("== Build network dataset ==")
        arcpy.na.BuildNetwork(nd_path)

        # Bersihkan layer sisa Build Network di memori
        delete_layers = ["JaringanJalan_ND", "JaringanJalanForND", "JaringanJalan_ND_Junctions"]
        for lyr in delete_layers:
            if arcpy.Exists(lyr):
                arcpy.management.Delete(lyr)

        # 6. OLAH JUNCTION (SIMPANG)
        messages.addMessage("== Olah junction ==")
        for item in [junction_path, junction_diss_path]:
            if arcpy.Exists(item):
                arcpy.management.Delete(item)

        # Bikin titik-titik persimpangan (intersect antara jalan dan junction ND)
        arcpy.analysis.Intersect([jaringanjalan_path, junction_nd_path], junction_path, "ALL", "", "INPUT")

        # Cek berapa ruas jalan yang terhubung ke satu titik (Dissolve Count)
        arcpy.management.Dissolve(
            junction_path,
            junction_diss_path,
            ["FID_JaringanJalan_ND_Junctions"],
            [["FID_Jaringan_Jalan", "COUNT"]],
            "MULTI_PART",
            "DISSOLVE_LINES"
        )

        # Hapus dangle (titik jalan buntu / COUNT = 1)
        lyr_junc_diss = "lyr_junc_diss"
        lyr_junc_source = "lyr_junc_source"
        
        arcpy.management.MakeFeatureLayer(junction_diss_path, lyr_junc_diss, "COUNT_FID_Jaringan_Jalan = 1")
        arcpy.management.MakeFeatureLayer(junction_path, lyr_junc_source)

        arcpy.management.SelectLayerByLocation(lyr_junc_source, "INTERSECT", lyr_junc_diss, selection_type="NEW_SELECTION")
        
        # Hapus FITUR dari dalam junction_path
        arcpy.management.DeleteFeatures(lyr_junc_source) 
        
        # Hapus referensi layer memori
        arcpy.management.Delete(lyr_junc_diss)
        arcpy.management.Delete(lyr_junc_source)

        # 7. JUNCTION FINAL (Ambil kelas jalan terbesar/MAX)
        if arcpy.Exists(junction_final_path):
            arcpy.management.Delete(junction_final_path)

        arcpy.management.Dissolve(
            junction_path,
            junction_final_path,
            ["FID_JaringanJalan_ND_Junctions"],
            [["s_klsjln", "MAX"], ["lb_jln", "MAX"]],
            "MULTI_PART",
            "DISSOLVE_LINES"
        )

        # 8. DATASET KELAS JALAN & EXPORT PER KELAS
        messages.addMessage("== Bagi junction berdasarkan kelas jalan ==")
        ds_kelas_jalan = os.path.join(gdb_path, "kelas_jalan")

        if not arcpy.Exists(ds_kelas_jalan):
            arcpy.management.CreateFeatureDataset(
                gdb_path, 
                "kelas_jalan", 
                arcpy.Describe(jaringanjalan_path).spatialReference
            )

        kelas_configs = [
            (7, "JunctionKls7"), (6, "JunctionKls6"), (5, "JunctionKls5"),
            (4, "JunctionKls4"), (3, "JunctionKls3"), (2, "JunctionKls2"),
            (1, "JunctionKls1")
        ]

        for nilai, nama_fc in kelas_configs:
            out_fc = os.path.join(ds_kelas_jalan, nama_fc)
            if arcpy.Exists(out_fc):
                arcpy.management.Delete(out_fc)

            lyr_kelas = "lyr_" + nama_fc
            where_clause_kls = f"MAX_s_klsjln = {nilai}"

            arcpy.management.MakeFeatureLayer(junction_final_path, lyr_kelas, where_clause_kls)
            arcpy.management.CopyFeatures(lyr_kelas, out_fc)
            arcpy.management.Delete(lyr_kelas)

        # 9. OUTPUT & VISUALISASI MAP (Dengan penanganan exception)
        arcpy.na.MakeNetworkDatasetLayer(nd_path, "JaringanJalan_ND")

        try:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            current_map = aprx.activeMap
            if current_map:
                current_map.addDataFromPath(template_fc_jarjal)
                current_map.addDataFromPath(junction_nd_path)
        except Exception:
            # Mengabaikan error ini jika tool di-run dari background (di luar ArcGIS Pro window)
            messages.addMessage("Info: Layer output tidak ditambahkan ke map karena berjalan di luar sesi Map aktif.")

        parameters[0].value = nd_path
        parameters[1].value = template_fc_jarjal
        parameters[2].value = junction_nd_path

        messages.addMessage("== Proses selesai ==")
        return

class Menentukan_Perubahan_Mengelompok(object):

    def __init__(self):
        self.label = "Menentukan Perubahan Mengelompok"
        self.description = "Update kelompok perubahan dan buat simbologi dinamis."
        self.canRunInBackground = False

    def getParameterInfo(self):
        param_cluster = arcpy.Parameter(
            displayName="Nomor Kelompok",
            name="cluster_update",
            datatype="GPLong",
            parameterType="Required",
            direction="Input"
        )

        output_layer = arcpy.Parameter(
            displayName="Output Persil",
            name="output_layer",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [param_cluster, output_layer]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def delete_if_exists(self, path):
        if arcpy.Exists(path):
            try:
                arcpy.management.Delete(path)
            except Exception:
                pass

    def add_field_if_not_exists(self, feature_class, field_name, field_type, field_alias=None):
        field_names = [field.name for field in arcpy.ListFields(feature_class)]
        if field_name not in field_names:
            arcpy.management.AddField(feature_class, field_name, field_type, field_alias=field_alias)

    def execute(self, parameters, messages):
        messages.addMessage("== Proses dimulai ==")
        cluster_update = int(parameters[0].value)
        
        configs = persil.get_config_values()
        dataset_path = configs["project_config"]["dataset_path"]

        persil_name = "Persil_Layer"
        persil_path = os.path.join(dataset_path, persil_name)

        if not arcpy.Exists(persil_path):
            messages.addErrorMessage("Feature class Persil_Layer tidak ditemukan")
            raise arcpy.ExecuteError

        # PERBAIKAN BUG: FIDSet mengembalikan string (misal "1;2;5"). 
        # Harus di-split dulu untuk menghitung jumlah fiturnya.
        fid_set = arcpy.Describe(persil_name).FIDSet
        selected_count = len(fid_set.split(";")) if fid_set else 0

        if selected_count <= 0:
            messages.addWarningMessage("Tidak ada fitur yang dipilih di Peta.")
            return

        self.add_field_if_not_exists(
            persil_path,
            'kelompok_perubahan',
            "LONG", 
            'Kelompok Perubahan'
        )

        messages.addMessage(f"== Update Kelompok Perubahan {cluster_update} ==")

        updated_count = 0
        

        with arcpy.da.UpdateCursor(persil_name, ["kelompok_perubahan", "perubahan"]) as cursor:
            for row in cursor:
                row[0] = cluster_update
                row[1] = "mengelompok"
                cursor.updateRow(row)
                updated_count += 1

        messages.addMessage(f"{updated_count} fitur berhasil diupdate")
        
        arcpy.SetParameter(1, persil_name)
        messages.addMessage("== Proses selesai ==")
        return

class Menghitung_Luas_Bidang(object):

    def __init__(self):
        self.label = "Perhitungan Luas Bidang"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        output_layer = arcpy.Parameter(
            displayName="Output Peta Akhir",
            name="output_peta_akhir",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )
        return [output_layer]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def delete_if_exists(self, path):
        if arcpy.Exists(path):
            try:
                arcpy.management.Delete(path)
            except Exception:
                pass

    def add_field_if_not_exists(self, feature_class, field_name, field_type):
        fields = [field.name.lower() for field in arcpy.ListFields(feature_class)]
        
        if field_name.lower() not in fields:
            arcpy.management.AddField(
                in_table=feature_class,
                field_name=field_name,
                field_type=field_type
            )

    def execute(self, parameters, messages):
        arcpy.env.overwriteOutput = True

        messages.addMessage("== Proses dimulai ==")

        configs = persil.get_config_values()
        dataset_path = configs["project_config"]["dataset_path"]
        
        peta_persil_name = "Persil_Layer"
        peta_persil_path = os.path.join(dataset_path, peta_persil_name)

        self.add_field_if_not_exists(peta_persil_path, "LUASM2", "DOUBLE")

        messages.addMessage("== Hitung luas tanah ==")
        arcpy.management.CalculateField(
            in_table=peta_persil_path,
            field="LUASM2",
            expression="!shape.area@SQUAREMETERS!",
            expression_type="PYTHON3"
        )

        self.delete_if_exists(peta_persil_name)

        arcpy.management.MakeFeatureLayer(peta_persil_path, peta_persil_name)
        parameters[0].value = peta_persil_name

        messages.addMessage("== Proses selesai ==")
        
        return
    
class Pengisian_Bentuk_Persil_Otomatis(object):

    def __init__(self):
        self.label = "Pengisian Bentuk Persil Otomatis"
        self.description = "Alat analisis bentuk persil dengan Generalisasi (menggabungkan garis terputus akibat vertex tetangga)."
        self.canRunInBackground = False

    def getParameterInfo(self):
        update_only = arcpy.Parameter(
            displayName="Hanya Persil Perubahan",
            name="update_only",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )
        update_only.value = True

        null_only = arcpy.Parameter(
            displayName="Hanya Nilai Bentuk Masih Null/Kosong",
            name="null_only",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )
        null_only.value = True

        min_length = arcpy.Parameter(
            displayName="Toleransi Panjang Sisi Minimum (Meter)",
            name="min_length",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input"
        )
        min_length.value = 1.0

        # --- MODIFIKASI: Parameter Toleransi Generalisasi ---
        toleransi_lurus = arcpy.Parameter(
            displayName="Toleransi Kelurusan Sisi / Generalize (Meter)",
            name="toleransi_lurus",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input"
        )
        # Angka 0.1 meter (10 cm) cukup untuk mendeteksi garis lurus 
        # namun tidak merusak sudut asli bidang tanah
        toleransi_lurus.value = 0.1 

        batas_sisi = arcpy.Parameter(
            displayName="Batas Jumlah Sisi untuk Segi Banyak",
            name="batas_sisi",
            datatype="GPLong",
            parameterType="Required",
            direction="Input"
        )
        batas_sisi.value = 5 

        out_lines = arcpy.Parameter(
            displayName="Simpan Garis Tepi Ke (Opsional)",
            name="out_lines",
            datatype="DEFeatureClass",
            parameterType="Optional",
            direction="Output"
        )

        output_layer = arcpy.Parameter(
            displayName="Output Persil Update",
            name="output_persil",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        # Mengembalikan 7 parameter
        return [update_only, null_only, min_length, toleransi_lurus, batas_sisi, out_lines, output_layer]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        update_only = parameters[0].value
        null_only = parameters[1].value
        min_length_threshold = parameters[2].value
        toleransi_lurus_val = parameters[3].value     # Mengambil parameter Generalize
        batas_sisi_banyak = parameters[4].value
        out_lines_path = parameters[5].valueAsText

        try:
            configs = persil.get_config_values()
            dataset_path = configs['project_config']['dataset_path']
        except Exception as e:
            messages.addWarningMessage(f"Modul konfigurasi gagal. Error: {str(e)}")
            dataset_path = arcpy.env.workspace

        input_fc = os.path.join(dataset_path, 'Persil_Layer')

        temp_line = r"memory\temp_line"
        temp_split = r"memory\temp_split"
        temp_dissolve = r"memory\temp_dissolve"
        temp_polygon = r"memory\temp_polygon"

        cleanup_items = [temp_line, temp_split, temp_dissolve, temp_polygon]
        for item in cleanup_items:
            self.delete_if_exists(item)

        messages.addMessage("== Mempersiapkan data ==")
        input_layer = "input_layer"

        conditions = []
        if update_only:
            conditions.append("(perubahan IS NOT NULL)")
        if null_only:
            conditions.append("(BENTUK IS NULL OR BENTUK = '' OR BENTUK = ' ')")
        where_clause = " AND ".join(conditions) if conditions else None
        
        arcpy.management.MakeFeatureLayer(input_fc, input_layer, where_clause)
        count = int(arcpy.management.GetCount(input_layer)[0])
        
        if count == 0:
            messages.addMessage("== Tidak ada bidang yang memenuhi kriteria. ==")
            return

        arcpy.management.CopyFeatures(input_layer, temp_polygon)

        messages.addMessage("== Konversi Polygon to Line ==")
        arcpy.management.PolygonToLine(temp_polygon, temp_line, "IGNORE_NEIGHBORS")
        
        # --- MODIFIKASI UTAMA: Proses Generalisasi sebelum di-Split ---
        if toleransi_lurus_val and toleransi_lurus_val > 0:
            messages.addMessage(f"== Melakukan Generalisasi (Menghapus vertex sebidang dengan toleransi {toleransi_lurus_val}m) ==")
            arcpy.edit.Generalize(temp_line, f"{toleransi_lurus_val} Meters")
        # --------------------------------------------------------------

        # Sekarang saat SplitLine dijalankan, garis tidak akan terputus di persimpangan
        arcpy.management.SplitLine(temp_line, temp_split)

        field_definitions = [
            ("LebarSisi", "DOUBLE"), ("XStart", "DOUBLE"),
            ("XEnd", "DOUBLE"), ("YStart", "DOUBLE"),
            ("YEnd", "DOUBLE"), ("Azimuth", "DOUBLE"),
            ("ATrans", "DOUBLE")
        ]

        for field_name, field_type in field_definitions:
            self.add_field_if_not_exists(temp_split, field_name, field_type)

        arcpy.management.CalculateField(temp_split, "LebarSisi", "!SHAPE.length!", "PYTHON3")

        messages.addMessage(f"== Menghitung Azimuth & ATrans ==")
        with arcpy.da.UpdateCursor(temp_split, ["SHAPE@", "XStart", "XEnd", "YStart", "YEnd", "Azimuth", "ATrans", "LebarSisi"]) as rows:
            for row in rows:
                geometry = row[0]
                if not geometry: 
                    continue

                x_start = geometry.firstPoint.X
                y_start = geometry.firstPoint.Y
                x_end = geometry.lastPoint.X
                y_end = geometry.lastPoint.Y
                
                lebar_sisi = row[7]

                azimuth, atrans = self.calculate_azimuth(x_start, y_start, x_end, y_end)

                row[1] = x_start
                row[2] = x_end
                row[3] = y_start
                row[4] = y_end
                
                if lebar_sisi >= min_length_threshold:
                    row[5] = azimuth
                    row[6] = atrans
                else:
                    row[5] = None
                    row[6] = None

                rows.updateRow(row)

        split_fields = [f.name.upper() for f in arcpy.ListFields(temp_split)]
        if "IDBIDANG" not in split_fields:
            messages.addErrorMessage("Field IDBIDANG tidak ditemukan.")
            raise arcpy.ExecuteError

        if out_lines_path:
            messages.addMessage(f"== Menyimpan Feature Class Garis Tepi ==")
            try:
                arcpy.management.CopyFeatures(temp_split, out_lines_path)
            except Exception as e:
                messages.addWarningMessage(f"Gagal menyimpan garis tepi: {str(e)}")

        messages.addMessage("== Proses Dissolve & Hitung Range ATrans ==")
        arcpy.management.Dissolve(
            temp_split, 
            temp_dissolve, 
            ['IDBIDANG'], 
            [["ATrans", "RANGE"], ["ATrans", "COUNT"]], 
            "MULTI_PART", 
            "DISSOLVE_LINES"
        )

        self.add_field_if_not_exists(temp_polygon, "BENTUK", "TEXT", 100)
        self.add_field_if_not_exists(temp_polygon, "S_BENTUK", "DOUBLE")

        polygon_fields_lower = [f.name.lower() for f in arcpy.ListFields(temp_polygon)]
        for f_name in ["range_atrans", "count_atrans"]:
            if f_name in polygon_fields_lower:
                actual_field_name = arcpy.ListFields(temp_polygon, f_name)[0].name
                arcpy.management.DeleteField(temp_polygon, actual_field_name)

        arcpy.management.JoinField(temp_polygon, 'IDBIDANG', temp_dissolve, 'IDBIDANG', ["RANGE_ATrans", "COUNT_ATrans"])

        messages.addMessage(f"== Klasifikasi Bentuk ==")
        with arcpy.da.UpdateCursor(temp_polygon, ["RANGE_ATrans", "COUNT_ATrans", "BENTUK", "S_BENTUK"]) as rows:
            for row in rows:
                rentang = row[0]
                jml_sisi_valid = row[1]
                
                if rentang is None or jml_sisi_valid is None or jml_sisi_valid == 0:
                    continue

                if jml_sisi_valid == 3:
                    row[2] = "Segi Tiga"
                    row[3] = 1
                elif jml_sisi_valid >= batas_sisi_banyak:
                    row[2] = "Segi Banyak Tidak Beraturan"
                    row[3] = 2
                else:
                    if rentang < 16.3:
                        row[2] = "Segi Empat Beraturan"
                        row[3] = 4
                    elif 16.3 <= rentang <= 58:
                        row[2] = "Segi Empat Tidak Beraturan"
                        row[3] = 3
                    else:
                        row[2] = "Segi Banyak Tidak Beraturan"
                        row[3] = 2
                        
                rows.updateRow(row)

        hasil_bentuk = {}
        with arcpy.da.SearchCursor(temp_polygon, ["IDBIDANG", "BENTUK", "S_BENTUK"]) as rows:
            for row in rows:
                hasil_bentuk[row[0]] = (row[1], row[2])

        messages.addMessage("== Menyimpan hasil ke database persil ==")
        with arcpy.da.UpdateCursor(input_fc, ["IDBIDANG", "BENTUK", "S_BENTUK"], where_clause) as rows:
            for row in rows:
                id_bidang = row[0]
                if id_bidang in hasil_bentuk:
                    bentuk, skor = hasil_bentuk[id_bidang]
                    row[1] = bentuk
                    row[2] = skor
                    rows.updateRow(row)

        for item in cleanup_items:
            self.delete_if_exists(item)

        messages.addMessage("== Memperbarui Simbologi Peta ==")
        sim_path = r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Simbologi_Bentuk_Persil.lyrx"
        
        try:
            arcpy.management.MakeFeatureLayer(input_fc, "Persil_Layer")
            arcpy.management.ApplySymbologyFromLayer("Persil_Layer", sim_path)
        except Exception:
            messages.addWarningMessage(f"Simbologi gagal dimuat.")

        # Parameter output bergeser ke indeks 6
        arcpy.SetParameter(6, "Persil_Layer")
        messages.addMessage("== Proses selesai ==")
        return

    def delete_if_exists(self, path):
        if arcpy.Exists(path):
            try: arcpy.management.Delete(path)
            except Exception: pass

    def add_field_if_not_exists(self, feature_class, field_name, field_type, length=None):
        field_names = [field.name.lower() for field in arcpy.ListFields(feature_class)]
        if field_name.lower() not in field_names:
            if length and field_type.upper() == "TEXT":
                arcpy.management.AddField(feature_class, field_name, field_type, field_length=length)
            else:
                arcpy.management.AddField(feature_class, field_name, field_type)

    def calculate_azimuth(self, x_start, y_start, x_end, y_end):
        delta_y = y_end - y_start
        delta_x = x_end - x_start

        if delta_y == 0:
            if delta_x >= 0: azimuth = 90
            else: azimuth = -90
        else:
            azimuth = math.atan(delta_x / delta_y) * (180 / math.pi)

        if azimuth < -45: atrans = azimuth + 180
        elif -45 <= azimuth <= 45: atrans = azimuth + 90
        else: atrans = azimuth

        return azimuth, atrans

class Pengisian_Bentuk_Persil_Manual(object):

    def __init__(self):
        self.label = "Pengisian Bentuk Persil Manual"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        param_bentuk = arcpy.Parameter(
            displayName="Bentuk Persil",
            name="bentuk",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )

        param_bentuk.filter.list = [
            "Segi Tiga",
            "Segi Banyak Tidak Beraturan",
            "Segi Empat Tidak Beraturan",
            "Segi Empat Beraturan"
        ]

        output_layer = arcpy.Parameter(
            displayName="Output Persil",
            name="output_persil",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [param_bentuk, output_layer]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def get_skor_bentuk(self, bentuk):
        mapping = {
            "Segi Banyak Tidak Beraturan": 2,
            "Segi Tiga": 1,
            "Segi Empat Tidak Beraturan": 3,
            "Segi Empat Beraturan": 4
        }
        return mapping.get(bentuk, 1)

    def delete_if_exists(self, path):
        if arcpy.Exists(path):
            try:
                arcpy.management.Delete(path)
            except Exception:
                pass

    def execute(self, parameters, messages):
        arcpy.env.overwriteOutput = True

        messages.addMessage("== Proses dimulai ==")

        bentuk = parameters[0].valueAsText
        configs = persil.get_config_values()
        skor_bentuk = self.get_skor_bentuk(bentuk)
        
        persil_update = "Persil_layer"

        fields = [field.name.lower() for field in arcpy.ListFields(persil_update)]
        required_fields = ["BENTUK", "S_BENTUK"]
        missing_fields = [field for field in required_fields if field.lower() not in fields]

        if missing_fields:
            messages.addErrorMessage(f"Field berikut tidak ditemukan: {', '.join(missing_fields)}")
            raise arcpy.ExecuteError

        selected_count = len(arcpy.Describe(persil_update).FIDSet)
        if selected_count <= 0:
            messages.addWarningMessage("Tidak ada fitur yang dipilih")
            return

        updated_count = 0
        with arcpy.da.UpdateCursor(persil_update, required_fields) as rows:
            for row in rows:
                row[0] = bentuk
                row[1] = float(skor_bentuk)
                rows.updateRow(row)
                updated_count += 1

        messages.addMessage(f"{updated_count} fitur berhasil diupdate")

        persil_path = os.path.join(configs['project_config']['dataset_path'], 'Persil_Layer')
        sim_path = r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Simbologi_Bentuk_Persil.lyrx"
        
        arcpy.management.MakeFeatureLayer(persil_path, "Persil_Layer")
        arcpy.management.ApplySymbologyFromLayer("Persil_Layer", sim_path)

        arcpy.SetParameter(1, "Persil_Layer")

        return
          
class Pengisian_WADMKC_WADMKD_Otomatis(object):
    def __init__(self):
        self.label = "Isi WADMKC & WADMKD Secara Otomatis"
        self.description = "Mengisi atribut WADMKC dan WADMKD yang Null berdasarkan 3 bidang terdekat, dan perubahan."
        self.canRunInBackground = False

    def getParameterInfo(self):
        

        output_data = arcpy.Parameter(
            name="output_layer",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [output_data]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        messages.addMessage("== Memulai proses otomatisasi WADMKC & WADMKD ==")

        persil_layer = 'Persil_Layer'
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        peta_aktif = aprx.activeMap
        if peta_aktif is None:
            arcpy.AddError('Tidak ditemukan peta aktif pada project ini')
            return

        daftar_layer = peta_aktif.listLayers(persil_layer)

        if len(daftar_layer)  == 0:
            arcpy.AddError(f'Layer {persil_layer} tidak ditemukan.')
            return

        elif len(daftar_layer) > 1:
            jumlah_layer = len(daftar_layer)
            arcpy.AddError(f'Ditemukan {jumlah_layer} Layer {persil_layer}. Hanya boleh ada 1 {persil_layer}')
            return
        layer_diinginkan = daftar_layer[0]
        if layer_diinginkan.isBroken:
            arcpy.AddError(f"Peringatan: Layer '{persil_layer}' ditemukan, tetapi sumber datanya terputus (broken)!")
            return

        input_layer = layer_diinginkan                                              
        required_fields = ["WADMKC", "WADMKD"]
        existing_fields = {f.name.upper(): f.name for f in arcpy.ListFields(input_layer)}
        missing_fields = [f for f in required_fields if f.upper() not in existing_fields]

        if missing_fields:
            messages.addErrorMessage(f"Field berikut tidak ditemukan pada layer: {', '.join(missing_fields)}")
            raise arcpy.ExecuteError

        has_perubahan = "PERUBAHAN" in existing_fields
        

        perubahan_field_name = existing_fields.get("PERUBAHAN", "")

        target_fields = ["WADMKC", "WADMKD"]
        
        for target_field in target_fields:
            messages.addMessage(f"== Memproses field {target_field} ==")
            
            valid_layer = f"memory_valid_{target_field}"
            null_layer = f"memory_null_{target_field}"
            
            where_valid = f"{target_field} IS NOT NULL AND {target_field} <> '' AND {target_field} <> ' '"
            where_null = f"{target_field} IS NULL OR {target_field} = '' OR {target_field} = ' '"
            
            arcpy.management.MakeFeatureLayer(input_layer, valid_layer, where_valid)
            arcpy.management.MakeFeatureLayer(input_layer, null_layer, where_null)
            
            count_valid = int(arcpy.management.GetCount(valid_layer)[0])
            count_null = int(arcpy.management.GetCount(null_layer)[0])
            
            if count_null == 0:
                messages.addMessage(f"Tidak ada bidang yang {target_field}-nya kosong. Lanjut ke proses berikutnya.")
                arcpy.management.Delete(valid_layer)
                arcpy.management.Delete(null_layer)
                continue
                
            if count_valid == 0:
                messages.addErrorMessage(f"Tidak ada satupun bidang dengan {target_field} valid untuk referensi")
                arcpy.management.Delete(valid_layer)
                arcpy.management.Delete(null_layer)
                continue
                
            messages.addMessage(f"Ditemukan {count_null} bidang kosong dan {count_valid} bidang referensi untuk {target_field}")
            
            near_table = r"memory\near_table_result"
            if arcpy.Exists(near_table):
                arcpy.management.Delete(near_table)
                
            arcpy.analysis.GenerateNearTable(
                in_features=null_layer, 
                near_features=valid_layer, 
                out_table=near_table, 
                closest="ALL", 
                closest_count=3, 
                method="PLANAR"
            )
            
            valid_dict = {}
            with arcpy.da.SearchCursor(valid_layer, ["OID@", target_field]) as sc:
                for row in sc:
                    valid_dict[row[0]] = row[1]
                    
            null_neighbors = {}
            with arcpy.da.SearchCursor(near_table, ["IN_FID", "NEAR_FID"]) as sc:
                for row in sc:
                    in_fid = row[0]   
                    near_fid = row[1] 
                    
                    val = valid_dict.get(near_fid)
                    if val is not None:
                        if in_fid not in null_neighbors:
                            null_neighbors[in_fid] = []
                        null_neighbors[in_fid].append(val)
                        
            messages.addMessage(f"== Memperbarui bidang kosong untuk {target_field}... ==")
            
            # Menyusun field yang akan diupdate secara dinamis
            update_fields = ["OID@", target_field]
            if has_perubahan: update_fields.append(perubahan_field_name)
            
            updated_count = 0
            with arcpy.da.UpdateCursor(null_layer, update_fields) as uc:
                for row in uc:
                    oid = row[0]
                    if oid in null_neighbors:
                        val_list = null_neighbors[oid]
                        
                        if val_list:
                           
                            most_common_val = Counter(val_list).most_common(1)[0][0]
                            row[1] = most_common_val
                            
                            if has_perubahan:
                                row[update_fields.index(perubahan_field_name)] = "menyebar"
                                
                            uc.updateRow(row)
                            updated_count += 1
                            
            messages.addMessage(f"Selesai. Berhasil memperbarui {updated_count} bidang untuk {target_field}.")
            
            arcpy.management.Delete(valid_layer)
            arcpy.management.Delete(null_layer)
            arcpy.management.Delete(near_table)
            
        
        arcpy.SetParameter(0, input_layer)
        return

class Pengisian_WADMKC_WADMKD_Manual(object):
    def __init__(self):
        self.label = "Isi WADMKC & WADMKD Secara Manual"
        self.description = "Mengisi atribut WADMKC dan WADMKD secara manual HANYA pada bidang (feature) yang sedang terpilih (selected) pada Persil_Layer."
        self.canRunInBackground = False

    def getParameterInfo(self):
        param_wadmkc = arcpy.Parameter(
            name="wadmkc_value",
            displayName="Nilai WADMKC (Kecamatan)",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )
        
        param_wadmkd = arcpy.Parameter(
            name="wadmkd_value",
            displayName="Nilai WADMKD (Desa/Kelurahan)",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )

        return [param_wadmkc, param_wadmkd]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        messages.addMessage("== Memulai proses update manual WADMKC & WADMKD ==")

        wadmkc_val = parameters[0].valueAsText
        wadmkd_val = parameters[1].valueAsText

        if not wadmkc_val and not wadmkd_val:
            arcpy.AddError("Anda harus memasukkan minimal satu nilai (WADMKC atau WADMKD).")
            return

        input_layer = persil.is_persil_layer_comply()
        layer_name = 'Persil_Layer'

        desc = arcpy.Describe(layer_name)
        if not desc.FIDSet:
            arcpy.AddError('Tidak ada feature yang dipilih di Persil_Layer. Silakan Select fitur terlebih dahulu.')
            return 
        
        selected_features_count = len(desc.FIDSet.split(";"))
        messages.addMessage(f"Ditemukan {selected_features_count} bidang yang terpilih dan akan di-update.")
        existing_fields = {f.name.upper(): f.name for f in arcpy.ListFields(input_layer)}
        
        update_fields = []
        if wadmkc_val:
            if "WADMKC" not in existing_fields:
                arcpy.AddError("Field WADMKC tidak ditemukan pada layer.")
                return
            update_fields.append("WADMKC")
            
        if wadmkd_val:
            if "WADMKD" not in existing_fields:
                arcpy.AddError("Field WADMKD tidak ditemukan pada layer.")
                return
            update_fields.append("WADMKD")

        has_perubahan = "PERUBAHAN" in existing_fields
        
        perubahan_field_name = existing_fields.get("PERUBAHAN", "")

        if has_perubahan: update_fields.append(perubahan_field_name)

        updated_count = 0
        
        with arcpy.da.UpdateCursor(layer_name, update_fields) as uc:
            for row in uc:
                
                if wadmkc_val:
                    row[update_fields.index("WADMKC")] = wadmkc_val
                if wadmkd_val:
                    row[update_fields.index("WADMKD")] = wadmkd_val
                
                if has_perubahan:
                    row[update_fields.index(perubahan_field_name)] = "menyebar"
                    
                uc.updateRow(row)
                updated_count += 1

        messages.addMessage(f"Selesai! Berhasil meng-update {updated_count} bidang pada Persil_Layer")
        return

class Pengisian_Kelas_dan_Lebar_Jalan_Otomatis(object):

    def __init__(self):
        self.label = "Pengisian Kelas dan Lebar Jalan Otomatis"
        self.description = "Memperbaharui atribut kelas jalan dan lebar jalan pada persil sekaligus"
        self.canRunInBackground = False

    def getParameterInfo(self):
        hanya_kosong = arcpy.Parameter(
            displayName="Hanya Nilai Kelas/Lebar Jalan Masih Null/Kosong",
            name="hanya_kosong",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )
        hanya_kosong.value = False

        hanya_update = arcpy.Parameter(
            displayName="Hanya Persil Perubahan",
            name="hanya_update",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )
        hanya_update.value = True

        simpan_temp = arcpy.Parameter(
            displayName="Simpan ke Layer Sementara",
            name="simpan_temp",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )
        simpan_temp.value = False

        radius = arcpy.Parameter(
            displayName="Jarak Pencarian (meter)",
            name="search_radius",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input"
        )
        radius.value = 30

        
        output = arcpy.Parameter(
            displayName="Output Persil",
            name="output_persil",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )
        simbologi = r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Simbologi_Kelas_Jalan_Pada_Persil.lyrx"
        output.symbology = simbologi

        # Urutan parameter mengikuti format Pengisian Kelas Jalan Otomatis
        return [hanya_kosong, hanya_update, simpan_temp, radius, output]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def delete_if_exists(self, path):
        if arcpy.Exists(path):
            try:
                arcpy.management.Delete(path)
            except Exception:
                pass

    def add_field_if_not_exists(self, fc, name, typ):
        fields = [f.name.lower() for f in arcpy.ListFields(fc)]
        if name.lower() not in fields:
            arcpy.management.AddField(fc, name, typ)

    def remove_field_if_exists(self, fc, name):
        fields = [f.name.lower() for f in arcpy.ListFields(fc)]
        if name.lower() in fields:
            try:
                arcpy.management.DeleteField(fc, name)
            except Exception:
                pass

    def execute(self, parameters, messages):
        arcpy.env.overwriteOutput = True
        messages.addMessage("== Proses Sinkronisasi Kelas dan Lebar Jalan Dimulai ==")

        # Note: Pastikan module persil sudah diimport di level atas script Anda
        configs = persil.get_config_values()
        dataset_path = configs['project_config']['dataset_path']

        # Mengambil parameter berdasarkan urutan getParameterInfo
        hanya_kosong = parameters[0].value
        hanya_update = parameters[1].value
        simpan_temp = parameters[2].value
        near_radius = parameters[3].valueAsText or "30"          

        gdb_temp = arcpy.env.scratchGDB
        field_id = 'IDBIDANG'
        field_kelas_sumber = 'kls_jln'
        field_lebar_sumber = 'lb_jln'
        
        # Field target yang disesuaikan
        field_target_kelas_nilai = 'S_KLSJLN'
        field_target_kelas_nama = 'KLSJLN'
        field_target_lebar = 'LBRJLN'

        persil_fc = os.path.join(dataset_path, 'Persil_Layer')
        jalan = os.path.join(dataset_path, "Jaringan_Jalan")
        temp_output_name = "Analisis_Atribut_Jalan_Temp"        
        temp_output_fc = os.path.join(dataset_path, temp_output_name)
        
        line = os.path.join("in_memory", "persil_line_attr")
        split = os.path.join("in_memory", "persil_split_attr")
        midpoint = os.path.join(gdb_temp, "midpoint_attr")

        if simpan_temp:
            self.delete_if_exists(temp_output_fc)
            messages.addMessage("== Membuat temporary layer ==")
            arcpy.management.CopyFeatures(persil_fc, temp_output_fc)
            update_fc = temp_output_fc
        else:
            update_fc = persil_fc

        persil_layer = "persil_input_atribut"
        self.delete_if_exists(persil_layer)
        arcpy.management.MakeFeatureLayer(update_fc, persil_layer)

        if hanya_update:
            arcpy.management.SelectLayerByAttribute(
                persil_layer, "NEW_SELECTION", "UPPER(perubahan) IS NOT NULL"
            )

        if hanya_kosong:
            messages.addMessage("== Seleksi persil yang belum tersinkronisasi atribut jalannya ==")
            selection_type = "SUBSET_SELECTION" if hanya_update else "NEW_SELECTION"
            
            # Filter untuk memproses jika Kelas Jalan ATAU Lebar Jalan masih kosong/0
            where_clause = f"({field_target_kelas_nama} IS NULL OR {field_target_kelas_nama} = '' OR " \
                           f"{field_target_kelas_nilai} IS NULL OR {field_target_kelas_nilai} = 0 OR " \
                           f"{field_target_lebar} IS NULL OR {field_target_lebar} = 0)"
            
            arcpy.management.SelectLayerByAttribute(persil_layer, selection_type, where_clause)

        jumlah = int(arcpy.management.GetCount(persil_layer)[0])
        if jumlah == 0:
            messages.addWarningMessage("== Tidak ada feature yang diproses ==")
            return

        messages.addMessage("== Memproses geometri ==")
        self.add_field_if_not_exists(jalan, "IdJalan", "LONG")
        oid_jalan = arcpy.Describe(jalan).OIDFieldName
        arcpy.management.CalculateField(jalan, "IdJalan", f"!{oid_jalan}!", "PYTHON3")

        self.delete_if_exists(line)
        arcpy.management.PolygonToLine(persil_layer, line, "IGNORE_NEIGHBORS")
        self.delete_if_exists(split)
        arcpy.management.SplitLine(line, split)

        self.delete_if_exists(midpoint)
        arcpy.management.FeatureToPoint(split, midpoint, "INSIDE")

        messages.addMessage("== Analisis Jalan Terdekat ==")
        arcpy.analysis.Near(midpoint, jalan, f"{near_radius} Meters", "LOCATION", "ANGLE")

        self.add_field_if_not_exists(midpoint, "IdJoin", "LONG")
        oid_mid = arcpy.Describe(midpoint).OIDFieldName
        arcpy.management.CalculateField(midpoint, "IdJoin", f"!{oid_mid}!", "PYTHON3")

        for fld in [field_kelas_sumber, field_lebar_sumber]:
            self.remove_field_if_exists(midpoint, fld)

        arcpy.management.JoinField(
            midpoint, "NEAR_FID", jalan, oid_jalan, [field_kelas_sumber, field_lebar_sumber]
        )

        messages.addMessage("== Seleksi frontage terbaik ==")
        mapping_kelas_jalan_ke_skoring = {
            "Arteri Primer": 7, "Arteri Sekunder": 6, "Kolektor Primer": 5,
            "Kolektor Sekunder": 4, "Lokal Primer": 3, "Lokal Sekunder": 2, "Setapak": 1
        }
        
        kandidat_dict = {}
        with arcpy.da.SearchCursor(midpoint, [field_id, field_kelas_sumber, field_lebar_sumber, "NEAR_DIST", "NEAR_FID"]) as rows:
            for row in rows:
                idbid, kelas, lb_jln, near, near_fid = row
                if near_fid == -1 or near is None:
                    continue

                skor_kelas = mapping_kelas_jalan_ke_skoring.get(kelas, 0) if kelas else 0
                try: 
                    lb_jln = float(lb_jln)
                except Exception: 
                    lb_jln = 0

                # Logika skoring frontage utama
                score = (skor_kelas * 1000000) + (lb_jln * 1000) - near
                
                # Simpan skor_kelas dan lb_jln sekaligus untuk update nantinya
                kandidat = [score, skor_kelas, lb_jln]

                if idbid not in kandidat_dict or kandidat[0] > kandidat_dict[idbid][0]:
                    kandidat_dict[idbid] = kandidat

        messages.addMessage("== Perbaharui Kelas dan Lebar Jalan ==")
        mapping_kelas_jalan = {v: k for k, v in mapping_kelas_jalan_ke_skoring.items()}
        
        # Update 3 atribut sekaligus: KLSJLN, S_KLSJLN, dan LBRJLN
        update_fields = [field_id, field_target_kelas_nama, field_target_kelas_nilai, field_target_lebar]
        with arcpy.da.UpdateCursor(persil_layer, update_fields) as rows:
            for row in rows:
                idbid = row[0]
                if idbid in kandidat_dict:
                    skoring_kelas = kandidat_dict[idbid][1]
                    lebar_jalan_val = kandidat_dict[idbid][2]
                    klsjln = mapping_kelas_jalan.get(skoring_kelas, "Tidak Diketahui")
                    
                    row[1] = klsjln
                    row[2] = skoring_kelas
                    row[3] = lebar_jalan_val
                    rows.updateRow(row)

        output_name = temp_output_name if simpan_temp else "Persil_Layer"
        self.delete_if_exists(output_name)
        arcpy.management.MakeFeatureLayer(update_fc, output_name)
        parameters[4].value = output_name

        messages.addMessage("== Proses selesai ==")
        return

class Pengisian_Kelas_dan_Lebar_Jalan_Manual(object):

    def __init__(self):
        self.label = "Pengisian Kelas dan Lebar Jalan Manual"
        self.description = "Memperbaharui atribut kelas dan lebar jalan pada persil terpilih berdasarkan satu segmen jalan yang dipilih secara manual di peta."
        self.canRunInBackground = False

    def getParameterInfo(self):
        return []

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        # Mendefinisikan nama layer langsung sesuai yang ada di panel Contents (Peta)
        layer_persil = "Persil_Layer"
        layer_jalan = "Jaringan_Jalan"

        # Memastikan layer tersebut benar-benar ada di peta
        if not arcpy.Exists(layer_persil):
            messages.addErrorMessage(f"Layer '{layer_persil}' tidak ditemukan di panel Contents (Peta aktif).")
            raise arcpy.ExecuteError
        
        if not arcpy.Exists(layer_jalan):
            messages.addErrorMessage(f"Layer '{layer_jalan}' tidak ditemukan di panel Contents (Peta aktif).")
            raise arcpy.ExecuteError

        # 1. Validasi Seleksi Layer Jalan (Harus tepat 1)
        desc_jalan = arcpy.Describe(layer_jalan)
        if not desc_jalan.FIDSet:
            messages.addErrorMessage("Tidak ada fitur jalan yang dipilih. Silakan select tepat 1 fitur pada layer 'Jaringan_Jalan'.")
            raise arcpy.ExecuteError
        
        jumlah_jalan = len(desc_jalan.FIDSet.split(";"))
        if jumlah_jalan > 1:
            messages.addErrorMessage(f"Anda memilih {jumlah_jalan} fitur jalan. Silakan select HANYA 1 fitur jaringan jalan.")
            raise arcpy.ExecuteError

        # 2. Validasi Seleksi Layer Persil (Minimal 1)
        desc_persil = arcpy.Describe(layer_persil)
        if not desc_persil.FIDSet:
            messages.addErrorMessage("Tidak ada fitur persil yang dipilih. Silakan select 1 atau beberapa fitur pada layer 'Persil_Layer' yang ingin diupdate.")
            raise arcpy.ExecuteError
            
        jumlah_persil = len(desc_persil.FIDSet.split(";"))

        messages.addMessage(f"== Memproses {jumlah_persil} fitur persil berdasarkan 1 fitur jalan terpilih ==")

        # Field sumber dari jalan
        field_kelas_sumber = 'kls_jln'
        field_lebar_sumber = 'lb_jln'
        
        # Field target di persil
        field_target_kelas_nama = 'KLSJLN'
        field_target_kelas_nilai = 'S_KLSJLN'
        field_target_lebar = 'LBRJLN'

        mapping_kelas_jalan_ke_skoring = {
            "Arteri Primer": 7, "Arteri Sekunder": 6, "Kolektor Primer": 5,
            "Kolektor Sekunder": 4, "Lokal Primer": 3, "Lokal Sekunder": 2, "Setapak": 1
        }
        mapping_kelas_jalan = {v: k for k, v in mapping_kelas_jalan_ke_skoring.items()}

        # 3. Baca atribut dari fitur jalan yang dipilih
        kelas_jalan_val = None
        lebar_jalan_val = 0.0

        with arcpy.da.SearchCursor(layer_jalan, [field_kelas_sumber, field_lebar_sumber]) as cursor:
            for row in cursor:
                kelas_jalan_val = row[0]
                try:
                    lebar_jalan_val = float(row[1]) if row[1] is not None else 0.0
                except ValueError:
                    lebar_jalan_val = 0.0
                break # Mengambil nilai dari baris pertama

        # Kalkulasi Skoring
        skor_kelas = mapping_kelas_jalan_ke_skoring.get(kelas_jalan_val, 0) if kelas_jalan_val else 0
        nama_kelas = mapping_kelas_jalan.get(skor_kelas, "Tidak Diketahui")

        messages.addMessage("Data Jalan yang disalin:")
        messages.addMessage(f" - Kelas Jalan : {nama_kelas}")
        messages.addMessage(f" - Skor Kelas  : {skor_kelas}")
        messages.addMessage(f" - Lebar Jalan : {lebar_jalan_val} m")

        # 4. Update fitur persil yang dipilih
        update_fields = [field_target_kelas_nama, field_target_kelas_nilai, field_target_lebar]
        
        sukses_update = 0
        with arcpy.da.UpdateCursor(layer_persil, update_fields) as cursor:
            for row in cursor:
                row[0] = nama_kelas
                row[1] = skor_kelas
                row[2] = lebar_jalan_val
                cursor.updateRow(row)
                sukses_update += 1

        messages.addMessage(f"== Berhasil memperbaharui {sukses_update} bidang persil ==")
        return

class Pengisian_Letak_Otomatis(object):

    def __init__(self):
        self.label = "Pengisian Letak Persil Otomatis"
        self.description = "Menganalisis kedekatan persil dengan jalan dan junction untuk menentukan tipe letak dengan performa yang dioptimalkan."
        self.canRunInBackground = False

    def getParameterInfo(self):
        radius = arcpy.Parameter(
            displayName="Radius Pencarian (Meter)",
            name="near_radius",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input"
        )
        radius.value = 30

        simpan_temp = arcpy.Parameter(
            displayName="Simpan ke Layer Sementara",
            name="simpan_temp",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )
        simpan_temp.value = False

        hanya_update = arcpy.Parameter(
            displayName="Hanya Persil Perubahan",
            name="hanya_update",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )
        hanya_update.value = True

        null_only = arcpy.Parameter(
            displayName="Hanya Analisis Letak Masih Null/Kosong",
            name="null_only",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )
        null_only.value = True

        output = arcpy.Parameter(
            displayName="Output Persil",
            name="output_persil",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )
        sim_path =  r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Simbologi_Letak_Persil.lyrx"
        output.symbology = sim_path

        return [simpan_temp, hanya_update, null_only, radius, output]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def delete_if_exists(self, path):
        if arcpy.Exists(path):
            try:
                arcpy.management.Delete(path)
            except Exception:
                pass

    def add_field_if_not_exists(self, fc, name, typ):
        fields = [f.name.upper() for f in arcpy.ListFields(fc)]
        if name.upper() not in fields:
            arcpy.management.AddField(fc, name, typ)

    def get_addfield_type(self, arcpy_type):
        """Mapping tipe data sistem ke tipe data AddField yang diizinkan"""
        mapping = {
            'Integer': 'LONG', 'String': 'TEXT', 'SmallInteger': 'SHORT',
            'Double': 'DOUBLE', 'Single': 'FLOAT', 'OID': 'LONG', 'Geometry': 'BLOB'
        }
        return mapping.get(arcpy_type, 'TEXT')

    def execute(self, parameters, messages):
        messages.addMessage("== Memulai Analisis Letak Persil ==")
        
        
        simpan_temp = parameters[0].value
        hanya_update = parameters[1].value
        null_only = parameters[2].value
        near_radius = parameters[3].valueAsText or "200"

        # 1. Pengecekan Konfigurasi
        try:
            configs = persil.get_config_values()
            dataset_path = configs['project_config']['dataset_path']
            gdb_path = configs['project_config']['gdb_path']
            network_analysis_template_folder = os.path.join(gdb_path, constant.FD_TEMPLATE_JARINGAN_JALAN)
        except Exception:
            messages.addErrorMessage("== File config persil tidak ditemukan. Proses dihentikan ==")
            raise arcpy.ExecuteError

        persil_path = os.path.join(dataset_path, 'Persil_Layer')
        temp_output_name = "Analisis_Persil_Dengan_Jalan_Temp"
        temp_output_path = os.path.join(dataset_path, temp_output_name)

        if simpan_temp:
            self.delete_if_exists(temp_output_path)
            messages.addMessage("== Membuat temporary layer ==")
            arcpy.management.CopyFeatures(persil_path, temp_output_path)
            update_fc = temp_output_path
        else:
            update_fc = persil_path

        persil_input = "persil_input"
        self.delete_if_exists(persil_input)

        # 2. Menyusun Kueri Filter Secara Dinamis
        conditions = []
        if hanya_update:
            conditions.append("UPPER(perubahan) IS NOT NULL")
        if null_only:
            conditions.append("(LETAK IS NULL OR LETAK = '' OR LETAK = ' ')")
        
        where_clause = " AND ".join(conditions) if conditions else None
        messages.addMessage(f"== Filter: {where_clause if where_clause else 'Semua Data'} ==")

        arcpy.management.MakeFeatureLayer(update_fc, persil_input, where_clause)

        count_persil = int(arcpy.management.GetCount(persil_input)[0])
        if count_persil == 0:
            messages.addMessage("== Tidak ada persil yang memenuhi kriteria filter. Proses selesai. ==")
            return
            
        messages.addMessage(f"== Menghitung letak untuk {count_persil} bidang target... ==")

        jalan = os.path.join(dataset_path, 'Jaringan_Jalan')
        junction = os.path.join(network_analysis_template_folder, 'JaringanJalan_ND_Junctions')
        
        if not arcpy.Exists(jalan) or not arcpy.Exists(junction):
            messages.addErrorMessage("== Jaringan_Jalan atau Junction tidak ditemukan. Proses dihentikan. ==")
            raise arcpy.ExecuteError

        field_id = 'IdBidang'
        field_letak = 'LETAK'
        field_s_letak = 'S_LETAK'
        field_lb_jln = 'LBRJLN'
        field_s_kls_jln = 'S_KLSJLN'
        field_lb_dpn = 'LBRDPN'

        # Standarisasi Layer Virtual ke Memory Workspace
        mem_split = r"memory\split"
        mem_midpoint = r"memory\midpoint_sisi"
        mem_line = r"memory\line"
        mem_join = r"memory\join"
        mem_erase = r"memory\erase"
        mem_normal = r"memory\normal"
        mem_normal_mid = r"memory\normal_mid"
        mem_normal_diss = r"memory\normal_diss"

        cleanup_items = [
            mem_split, mem_midpoint, mem_line, mem_join, mem_erase, 
            mem_normal, mem_normal_mid, mem_normal_diss
        ]
        for item in cleanup_items:
            self.delete_if_exists(item)

        messages.addMessage("== Mempersiapkan IdJalan ==")
        self.add_field_if_not_exists(jalan, "IdJalan", "LONG")
        oid_jalan = arcpy.Describe(jalan).OIDFieldName
        arcpy.management.CalculateField(jalan, "IdJalan", f"!{oid_jalan}!", "PYTHON3")

        messages.addMessage("== Konversi Polygon Ke Batas Garis Bidang ==")
        arcpy.management.PolygonToLine(persil_input, mem_line, "IGNORE_NEIGHBORS")
        arcpy.management.SplitLine(mem_line, mem_split)

        self.add_field_if_not_exists(mem_split, "LebarSisi", "DOUBLE")
        arcpy.management.CalculateField(mem_split, "LebarSisi", "!shape.length!", "PYTHON3")

        messages.addMessage("== Menentukan Titik Tengah Garis (Midpoint) ==")
        arcpy.management.FeatureToPoint(mem_split, mem_midpoint, "INSIDE")

        self.add_field_if_not_exists(mem_midpoint, "X", "DOUBLE")
        self.add_field_if_not_exists(mem_midpoint, "Y", "DOUBLE")
        arcpy.management.CalculateField(mem_midpoint, "X", "!Shape.firstPoint.X!", "PYTHON3")
        arcpy.management.CalculateField(mem_midpoint, "Y", "!Shape.firstPoint.Y!", "PYTHON3")

        messages.addMessage("== Kalkulasi Jarak Terdekat Ke Jaringan Jalan (Dioptimalkan) ==")
        arcpy.analysis.Near(mem_midpoint, jalan, f"{near_radius} Meters", "LOCATION", "ANGLE")

        jalan_dict = {}
        with arcpy.da.SearchCursor(jalan, ["IdJalan", field_s_kls_jln]) as j_cur:
            for j_row in j_cur:
                jalan_dict[j_row[0]] = j_row[1]

        self.add_field_if_not_exists(mem_midpoint, "IdJoin", "LONG")
        oid_mid = arcpy.Describe(mem_midpoint).OIDFieldName
        
        id_field_obj = [f for f in arcpy.ListFields(mem_midpoint) if f.name.upper() == field_id.upper()][0]
        kls_field_obj = [f for f in arcpy.ListFields(jalan) if f.name.upper() == field_s_kls_jln.upper()][0]

        id_field_type = self.get_addfield_type(id_field_obj.type)
        kls_field_type = self.get_addfield_type(kls_field_obj.type)

        # Update IdJoin & Buang fitur yang tidak menemukan jalan (-1) agar tidak error XYToLine
        midpoint_dict = {}
        with arcpy.da.UpdateCursor(mem_midpoint, [oid_mid, "IdJoin", field_id, "LebarSisi", "NEAR_FID", "NEAR_DIST"]) as cur:
            for row in cur:
                near_fid = row[4]
                if near_fid == -1 or near_fid is None:
                    cur.deleteRow()
                    continue

                row[1] = row[0]
                cur.updateRow(row)
                s_kls = jalan_dict.get(near_fid, None)
                midpoint_dict[row[0]] = (row[2], row[3], near_fid, row[5], s_kls)

        sr = arcpy.Describe(mem_midpoint).spatialReference
        
        arcpy.management.XYToLine(mem_midpoint, mem_join, "X", "Y", "NEAR_X", "NEAR_Y", "GEODESIC", "IdJoin", sr)
        
        self.add_field_if_not_exists(mem_join, field_id, id_field_type)
        self.add_field_if_not_exists(mem_join, "LebarSisi", "DOUBLE")
        self.add_field_if_not_exists(mem_join, "IdJalan", "LONG")
        self.add_field_if_not_exists(mem_join, "PanjangNearLine", "DOUBLE")
        self.add_field_if_not_exists(mem_join, field_s_kls_jln, kls_field_type)

        with arcpy.da.UpdateCursor(mem_join, ["IdJoin", field_id, "LebarSisi", "IdJalan", "PanjangNearLine", field_s_kls_jln]) as cur:
            for row in cur:
                val = midpoint_dict.get(row[0])
                if val:
                    row[1] = val[0]
                    row[2] = val[1]
                    row[3] = val[2]
                    row[4] = val[3]
                    row[5] = val[4]
                    cur.updateRow(row)

        messages.addMessage("== Kalkulasi Pairwise Erase untuk identifikasi Lain-lain ==")
        arcpy.analysis.PairwiseErase(mem_join, persil_path, mem_erase)

        self.add_field_if_not_exists(mem_erase, "PanjangErase", "DOUBLE")
        self.add_field_if_not_exists(mem_erase, "Pengurangan", "DOUBLE")
        self.add_field_if_not_exists(mem_erase, "letak_tmp", "TEXT")

        arcpy.management.CalculateField(mem_erase, "PanjangErase", "!shape.length!", "PYTHON3")
        arcpy.management.CalculateField(mem_erase, "Pengurangan", "!PanjangErase! - !PanjangNearLine!", "PYTHON3")

        code_letak = """
def get_letak(v):
    if v is None:
        return 'Pinggir Jalan'
    if v < -0.1:
        return 'Lain-lain'
    return 'Pinggir Jalan'
"""
        arcpy.management.CalculateField(mem_erase, "letak_tmp", "get_letak(!Pengurangan!)", "PYTHON3", code_letak)

        messages.addMessage("== Agregasi Data Hasil Lintasan Jalan ==")
        
        join_dict = {}
        with arcpy.da.SearchCursor(mem_erase, [field_id, "letak_tmp"]) as rows:
            for row in rows:
                if row[0] is not None:
                    join_dict[row[0]] = row[1]

        pair_dict = {} 
        with arcpy.da.SearchCursor(mem_join, [field_id, "IdJalan", "LebarSisi", field_s_kls_jln]) as rows:
            for row in rows:
                fid, id_jln, lebar, kls = row
                if fid is None or id_jln is None:
                    continue
                
                pair_key = (fid, id_jln)
                if pair_key not in pair_dict:
                    # Inisialisasi awal harus memasukkan lebar segmen pertama
                    pair_dict[pair_key] = [(lebar or 0.0), kls]
                else:
                    pair_dict[pair_key][0] += (lebar or 0.0)
                    if kls is not None:
                        if pair_dict[pair_key][1] is None or kls > pair_dict[pair_key][1]:
                            pair_dict[pair_key][1] = kls

        jalan_agregat_dict = {}
        for (fid, id_jln), (sum_lebar, max_kls) in pair_dict.items():
            if fid not in jalan_agregat_dict:
                jalan_agregat_dict[fid] = {
                    "count_jalan": 0,
                    "lb_dpn": 0.0,
                    "s_klsjln": None
                }
            
            jalan_agregat_dict[fid]["count_jalan"] += 1
            jalan_agregat_dict[fid]["lb_dpn"] += sum_lebar
            if max_kls is not None:
                if jalan_agregat_dict[fid]["s_klsjln"] is None or max_kls > jalan_agregat_dict[fid]["s_klsjln"]:
                    jalan_agregat_dict[fid]["s_klsjln"] = max_kls

        messages.addMessage("== Memperbarui Atribut Letak Utama ==")
        with arcpy.da.UpdateCursor(persil_input, [field_id, field_letak, field_s_letak, field_lb_dpn]) as rows:
            for row in rows:
                idbid = row[0]
                letak = "Pinggir Jalan"
                skor = 0
                lb_dpn = 0

                if idbid in jalan_agregat_dict:
                    lb_dpn = jalan_agregat_dict[idbid].get("lb_dpn", 0.0)

                # Prioritas 1: Jika tersentuh garis erase, ambil hasilnya.
                if idbid in join_dict:
                    letak = join_dict[idbid]
                # Prioritas 2: Jika pernah punya rute ke jalan, tapi terhapus 100% di hasil erase (terhalang penuh)
                elif idbid in jalan_agregat_dict and idbid not in join_dict:
                    letak = "Lain-lain"

                # Kalkulasi Final
                if letak == "Lain-lain":
                    skor = 1
                elif idbid in jalan_agregat_dict:
                    count_jln = jalan_agregat_dict[idbid].get("count_jalan", 0)
                    if count_jln > 1:
                        letak = "Hook"
                        skor = 4
                    else:
                        letak = "Normal"
                        skor = 3

                row[1] = letak
                row[2] = skor
                row[3] = lb_dpn
                rows.updateRow(row)

        messages.addMessage("== Analisis Spasial Tusuk Sate ==")
        arcpy.management.MakeFeatureLayer(persil_input, "normal_lyr", f"{field_letak}='Normal'")
        
        count_normal = int(arcpy.management.GetCount("normal_lyr")[0])
        if count_normal > 0:
            arcpy.management.CopyFeatures("normal_lyr", mem_normal)
            arcpy.management.FeatureToPoint(mem_normal, mem_normal_mid, "INSIDE")

            arcpy.analysis.Near(mem_normal_mid, junction, "100 Meters", "LOCATION")
            self.add_field_if_not_exists(mem_normal_mid, "P_Line", "DOUBLE")
            arcpy.management.CalculateField(mem_normal_mid, "P_Line", "!NEAR_DIST!", "PYTHON3")

            arcpy.analysis.SpatialJoin(mem_normal_mid, mem_split, mem_normal_diss, "JOIN_ONE_TO_ONE", "KEEP_ALL", match_option="INTERSECT")

            tusuk_dict = {}
            with arcpy.da.SearchCursor(mem_normal_diss, [field_id, "P_Line", "LebarSisi"]) as rows:
                for row in rows:
                    if row[1] is None or row[2] is None:
                        continue
                    if row[1] < row[2]:
                        tusuk_dict[row[0]] = "Tusuk Sate"

            if tusuk_dict:
                with arcpy.da.UpdateCursor(persil_input, [field_id, field_letak, field_s_letak], f"{field_letak}='Normal'") as rows:
                    for row in rows:
                        idbid = row[0]
                        if idbid in tusuk_dict:
                            row[1] = "Tusuk Sate"
                            row[2] = 2
                            rows.updateRow(row)

        messages.addMessage("== Finalisasi Dan Pembersihan Memori Layer ==")
        for item in cleanup_items:
            self.delete_if_exists(item)

        if simpan_temp:
            output_name = temp_output_name
        else:
            output_name = "Persil_Layer"

        self.delete_if_exists(output_name)
        arcpy.management.MakeFeatureLayer(update_fc, output_name)
        parameters[4].value = output_name

        messages.addMessage("== Seluruh Proses Selesai dengan Berhasil ==")
        return

class Pengisian_Letak_Manual(object):

    def __init__(self):
        self.label = "Pengisian Letak Persil Manual"
        self.description = "Memperbaharui atribut LETAK dan S_LETAK pada persil terpilih berdasarkan input manual dari pengguna."
        self.canRunInBackground = False

    def getParameterInfo(self):
        # Hanya ada satu parameter input yaitu pilihan letak dari dropdown
        jenis_letak = arcpy.Parameter(
            displayName="Jenis Letak Persil",
            name="jenis_letak",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        # Daftar pilihan jenis letak persil
        jenis_letak.filter.list = ["Normal", "Hook", "Tusuk Sate", "Lain-lain"]
        jenis_letak.value = "Normal"

        return [jenis_letak]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        # Mengambil nilai pilihan dari pengguna
        pilihan_letak = parameters[0].valueAsText

        # Mendefinisikan nama layer langsung sesuai yang ada di panel Contents (Peta)
        layer_persil = "Persil_Layer"

        # Memastikan layer tersebut benar-benar ada di peta
        if not arcpy.Exists(layer_persil):
            messages.addErrorMessage(f"Layer '{layer_persil}' tidak ditemukan di panel Contents (Peta aktif).")
            raise arcpy.ExecuteError

        # Validasi Seleksi Layer Persil (Minimal 1 fitur harus dipilih)
        desc_persil = arcpy.Describe(layer_persil)
        if not desc_persil.FIDSet:
            messages.addErrorMessage("Tidak ada fitur persil yang dipilih. Silakan select 1 atau beberapa fitur pada layer 'Persil_Layer' di peta terlebih dahulu.")
            raise arcpy.ExecuteError
            
        jumlah_persil = len(desc_persil.FIDSet.split(";"))
        messages.addMessage(f"== Memproses {jumlah_persil} fitur persil yang dipilih ==")

        # Field target di persil
        field_letak = 'LETAK'
        field_s_letak = 'S_LETAK'

        # Mapping skoring otomatis berdasarkan pilihan
        mapping_skor = {
            "Hook": 4,
            "Normal": 3,
            "Tusuk Sate": 2,
            "Lain-lain": 1
        }
        
        skor_letak = mapping_skor.get(pilihan_letak, 0)

        messages.addMessage(f"Data Letak yang akan disalin:")
        messages.addMessage(f" - Letak Persil : {pilihan_letak}")
        messages.addMessage(f" - Skor Letak   : {skor_letak}")

        # Update fitur persil yang dipilih
        update_fields = [field_letak, field_s_letak]
        
        sukses_update = 0
        with arcpy.da.UpdateCursor(layer_persil, update_fields) as cursor:
            for row in cursor:
                row[0] = pilihan_letak
                row[1] = skor_letak
                cursor.updateRow(row)
                sukses_update += 1

        messages.addMessage(f"== Berhasil memperbaharui {sukses_update} bidang persil ==")
        return

class Pengisian_Lebar_Depan_Otomatis(object):

    def __init__(self):
        self.label = "Pengisian Lebar Depan Otomaris"
        self.description = "Menganalisis panjang sisi bidang yang menghadap jalan (frontage) untuk menentukan Lebar Depan Persil."
        self.canRunInBackground = False

    def getParameterInfo(self):
        radius = arcpy.Parameter(
            displayName="Radius Near (Meter)",
            name="near_radius",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input"
        )
        radius.value = 30

        simpan_temp = arcpy.Parameter(
            displayName="Simpan ke Layer Temporary",
            name="simpan_temp",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )
        simpan_temp.value = False

        hanya_kosong = arcpy.Parameter(
            displayName="Perbaharui yang bernilai 0 atau Kosong saja",
            name="hanya_kosong",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )
        hanya_kosong.value = False

        hanya_update = arcpy.Parameter(
            displayName="Sinkronisasi Data Persil Terbaru (Status Update)",
            name="hanya_update",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )
        hanya_update.value = True

        output = arcpy.Parameter(
            displayName="Output Persil",
            name="output_persil",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [radius, simpan_temp, hanya_kosong, hanya_update, output]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def delete_if_exists(self, path):
        if arcpy.Exists(path):
            try:
                arcpy.management.Delete(path)
            except Exception:
                pass

    def add_field_if_not_exists(self, fc, name, typ):
        fields = [f.name.lower() for f in arcpy.ListFields(fc)]
        if name.lower() not in fields:
            arcpy.management.AddField(fc, name, typ)

    def remove_field_if_exists(self, fc, name):
        fields = [f.name.lower() for f in arcpy.ListFields(fc)]
        if name.lower() in fields:
            try:
                arcpy.management.DeleteField(fc, name)
            except Exception:
                pass

    def execute(self, parameters, messages):
        arcpy.env.overwriteOutput = True
        messages.addMessage("== Proses dimulai ==")

        # 1. Mengambil Konfigurasi dari config file
        try:
            configs = persil.get_config_values()
            dataset_path = configs['project_config']['dataset_path']
        except Exception:
            messages.addErrorMessage("File konfigurasi persil tidak ditemukan. Proses dibatalkan.")
            raise arcpy.ExecuteError

        # 2. Mengambil nilai parameter
        near_radius = parameters[0].valueAsText       
        simpan_temp = parameters[1].value
        hanya_kosong = parameters[2].value
        hanya_update = parameters[3].value

        field_id = 'IDBIDANG'
        field_kelas = 's_klsjln'
        field_lebar = 'lb_jln'
        field_lb_dpn = 'LBRDPN'

        persil_fc = os.path.join(dataset_path, 'Persil_Layer')
        jalan = os.path.join(dataset_path, "Jaringan_Jalan")
        
        if not arcpy.Exists(jalan):
            messages.addErrorMessage(f"Layer jalan tidak ditemukan di: {jalan}")
            raise arcpy.ExecuteError

        temp_output_name = "Analisis_Lebar_Depan_Temp"       
        temp_output_fc = os.path.join(dataset_path, temp_output_name)
        
        # 3. Optimasi Workspace: Menggunakan memory\ untuk layer virtual
        line = r"memory\persil_line"
        split = r"memory\persil_split"
        midpoint = r"memory\midpoint"

        # 4. Membuat layer sementara jika opsi simpan_temp diaktifkan
        if simpan_temp:
            self.delete_if_exists(temp_output_fc)
            messages.addMessage("== Membuat temporary layer ==")
            arcpy.management.CopyFeatures(persil_fc, temp_output_fc)
            update_fc = temp_output_fc
        else:
            update_fc = persil_fc

        # 5. Mempersiapkan feature layer yang akan diolah
        persil_layer = "persil_input"
        self.delete_if_exists(persil_layer)
        arcpy.management.MakeFeatureLayer(update_fc, persil_layer)

        # Seleksi berdasarkan parameter
        if hanya_update:
            messages.addMessage("== Seleksi Persil Perubahan ==")
            arcpy.management.SelectLayerByAttribute(
                persil_layer, "NEW_SELECTION", "UPPER(PERUBAHAN) IS NOT NULL"
            )
        
        if hanya_kosong:
            messages.addMessage("== Seleksi persil yang belum tersinkronisasi (LBRDPN Null/0) ==")
            selection_type = "SUBSET_SELECTION" if hanya_update else "NEW_SELECTION"
            arcpy.management.SelectLayerByAttribute(
                persil_layer, selection_type, f"({field_lb_dpn} IS NULL OR {field_lb_dpn} = 0)"
            )

        # 6. Validasi jumlah data
        jumlah = int(arcpy.management.GetCount(persil_layer)[0])
        if jumlah == 0:
            messages.addWarningMessage("== Tidak ada feature persil yang perlu diproses ==")
            return

        # 7. Mempersiapkan IdJalan
        self.add_field_if_not_exists(jalan, "IdJalan", "LONG")
        oid_jalan = arcpy.Describe(jalan).OIDFieldName
        arcpy.management.CalculateField(jalan, "IdJalan", f"!{oid_jalan}!", "PYTHON3")

        # 8. Konversi polygon -> garis batas -> sisi terpisah
        messages.addMessage("== Ekstraksi sisi batas persil ==")
        self.delete_if_exists(line)
        arcpy.management.PolygonToLine(persil_layer, line, "IGNORE_NEIGHBORS")
        
        self.delete_if_exists(split)
        arcpy.management.SplitLine(line, split)
        
        self.add_field_if_not_exists(split, "LebarSisi", "DOUBLE")
        arcpy.management.CalculateField(split, "LebarSisi", "!shape.length!", "PYTHON3")

        # 9. Titik tengah setiap sisi
        messages.addMessage("== Membuat titik tengah (Midpoint) sisi ==")
        self.delete_if_exists(midpoint)
        arcpy.management.FeatureToPoint(split, midpoint, "INSIDE")

        self.add_field_if_not_exists(midpoint, "X", "DOUBLE")
        self.add_field_if_not_exists(midpoint, "Y", "DOUBLE")
        arcpy.management.CalculateField(midpoint, "X", "!Shape.firstPoint.X!", "PYTHON3")
        arcpy.management.CalculateField(midpoint, "Y", "!Shape.firstPoint.Y!", "PYTHON3")

        # 10. Analisis Kedekatan dengan Jaringan Jalan
        messages.addMessage("== Analisis Jarak Terdekat ke Jalan ==")
        arcpy.analysis.Near(midpoint, jalan, f"{near_radius} Meters", "LOCATION", "ANGLE")

        self.add_field_if_not_exists(midpoint, "IdJoin", "LONG")
        oid_mid = arcpy.Describe(midpoint).OIDFieldName
        arcpy.management.CalculateField(midpoint, "IdJoin", f"!{oid_mid}!", "PYTHON3")
        
        # 11. Join informasi kelas jalan dan lebar jalan
        for fld in [field_kelas, field_lebar]:
            self.remove_field_if_exists(midpoint, fld)

        arcpy.management.JoinField(
            midpoint, "NEAR_FID", jalan, oid_jalan, [field_kelas, field_lebar]
        )

        # 12. Filter jalan terbaik (Frontage Selection)
        messages.addMessage("== Menentukan sisi frontage terbaik ==")
        kandidat_dict = {}

        fields_to_read = [field_id, field_kelas, field_lebar, "LebarSisi", "NEAR_DIST", "NEAR_FID"]
        with arcpy.da.SearchCursor(midpoint, fields_to_read) as rows:
            for row in rows:
                idbid, kelas, lb_jln, lb_sisi, near, near_fid = row

                # Lewati jika tidak ada jalan terdekat dalam radius
                if near_fid == -1 or near is None:
                    continue

                # Casting dan handling tipe data yang aman (menghindari error ValueError/NoneType)
                try: kelas = float(kelas) if kelas is not None else 0.0
                except ValueError: kelas = 0.0

                try: lb_jln = float(lb_jln) if lb_jln is not None else 0.0
                except ValueError: lb_jln = 0.0

                try: lb_sisi = float(lb_sisi) if lb_sisi is not None else 0.0
                except ValueError: lb_sisi = 0.0

                # Logika Scoring: Prioritas pada jalan yang lebih besar/tinggi kelasnya, lalu jarak terdekat
                score = (kelas * 1000000) + (lb_jln * 1000) - near
                kandidat = [score, kelas, lb_jln, near, lb_sisi]

                # Memilih sisi dengan skor tertinggi per bidang persil
                if idbid not in kandidat_dict or kandidat[0] > kandidat_dict[idbid][0]:
                    kandidat_dict[idbid] = kandidat

        # (Opsional) Menampilkan 10 hasil teratas untuk log
        count = 0
        for idbid, kandidat in kandidat_dict.items():
            if count < 10:
                count += 1
                messages.addMessage(f"IdBidang: {idbid} | Skor: {kandidat[0]:.2f} | Sisi: {kandidat[4]:.2f}m")
            else:
                break

        # 13. Update field lebar depan
        messages.addMessage("== Memperbaharui atribut Lebar Depan ==")
        
        with arcpy.da.UpdateCursor(persil_layer, [field_id, field_lb_dpn]) as rows:
            for row in rows:
                idbid = row[0]
                if idbid in kandidat_dict:
                    lb_dpn = kandidat_dict[idbid][4] # Index 4 adalah lb_sisi
                    row[1] = lb_dpn
                    rows.updateRow(row)

        # 14. Output & Cleanup memori
        if simpan_temp:
            output_name = temp_output_name
        else:
            output_name = "Persil_Layer"

        self.delete_if_exists(output_name)
        arcpy.management.MakeFeatureLayer(update_fc, output_name)
        parameters[4].value = output_name

        # Membersihkan layer temporary virtual dari memori RAM
        for item in [line, split, midpoint]:
            self.delete_if_exists(item)

        messages.addMessage("== Proses selesai ==")
        return

class Pengisian_Jarak_Ke_Jalan_Utama_Otomatis(object):

    def __init__(self):
        self.label = "Pengisian Jarak ke Jalan Utama Otomatis"
        self.description = "Menghitung jarak jaringan (Network Distance) dari bidang persil ke berbagai kelas jalan utama."
        self.canRunInBackground = False

    def getParameterInfo(self):
        simpan_temp = arcpy.Parameter(
            displayName="Simpan ke Layer Sementara",
            name="simpan_temp",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )
        simpan_temp.value = False

        hanya_update = arcpy.Parameter(
            displayName="Hanya Persil Perubahan",
            name="hanya_update",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )
        hanya_update.value = True

        pilihan_kelas_jalan = arcpy.Parameter(
            displayName="Pilih Kelas Jalan yang Dihitung",
            name="pilihan_kelas_jalan",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
            multiValue=True
        )
        pilihan_kelas_jalan.filter.type = "ValueList"
        pilihan_kelas_jalan.filter.list = [
            "Semuanya",
            "Arteri Primer",
            "Arteri Sekunder",
            "Kolektor Primer",
            "Kolektor Sekunder"
        ]
        pilihan_kelas_jalan.value = ["Semuanya"]

        hanya_yang_null = arcpy.Parameter(
            displayName="Hanya Nilai Jarak Masih Null/Kosong",
            name="hanya_yang_null",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )
        hanya_yang_null.value = True

        output_persil = arcpy.Parameter(
            displayName="Output Persil",
            name="output_persil",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [simpan_temp, hanya_update, hanya_yang_null,  pilihan_kelas_jalan,  output_persil]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def delete_if_exists(self, path):
        if arcpy.Exists(path):
            try:
                arcpy.management.Delete(path)
            except Exception:
                pass

    def add_field_if_not_exists(self, feature_class, field_name, field_type):
        field_names = [field.name.upper() for field in arcpy.ListFields(feature_class)]
        if field_name.upper() not in field_names:
            arcpy.management.AddField(feature_class, field_name, field_type)

    def execute(self, parameters, messages):
        arcpy.env.overwriteOutput = True
        messages.addMessage("== Proses mulai ==")


        try:
            configs = persil.get_config_values()
            gdb_path = configs["project_config"]["gdb_path"]
            dataset_path = configs["project_config"]["dataset_path"]
            jarjal_ds_path = os.path.join(gdb_path, constant.FD_TEMPLATE_JARINGAN_JALAN)
            jaringan_jalan = 'Jaringan_Jalan'
            jaringanjalan_path = os.path.join(dataset_path, jaringan_jalan)
            nd_path = os.path.join(jarjal_ds_path, constant.TEMPLATE_LAYER_NETWORK_DATASET_JARINGAN_JALAN)
        except Exception:
            messages.addErrorMessage("File konfigurasi persil tidak ditemukan. Proses dibatalkan.")
            raise arcpy.ExecuteError

        # 2. Mengambil nilai parameter
        simpan_temp = parameters[0].value
        hanya_update = parameters[1].value
        hanya_yang_null = parameters[2].value
        
        pilihan_kelas_text = parameters[3].valueAsText
        if pilihan_kelas_text:
            pilihan_list = [p.strip("'") for p in pilihan_kelas_text.split(";")]
        else:
            pilihan_list = ["Semuanya"]

        

        # Mapping pilihan UI ke nama Junction Layer dan Target Field
        mapping_pilihan = {
            "Kolektor Sekunder": "JunctionKls4",
            "Kolektor Primer": "JunctionKls5",
            "Arteri Sekunder": "JunctionKls6",
            "Arteri Primer": "JunctionKls7"
        }
        
        reverse_mapping = {v: k for k, v in mapping_pilihan.items()}
        
        namafield = {
            4: 'JKKOLS',
            5: 'JKKOLP',
            6: 'JKATRS',
            7: 'JKATRP'
        }

        requested_fc = []
        if "Semuanya" in pilihan_list:
            requested_fc = list(mapping_pilihan.values())
        else:
            for p in pilihan_list:
                if p in mapping_pilihan:
                    requested_fc.append(mapping_pilihan[p])

        # Mendapatkan daftar field tujuan yang akan dihitung (untuk kueri Null)
        target_fields = []
        for req_fc in requested_fc:
            kls = int(req_fc.replace("JunctionKls", ""))
            target_fields.append(namafield[kls])

        # 3. Mempersiapkan path untuk dataset dan output sementara
        persil_fc = os.path.join(dataset_path, "Persil_Layer")
        temp_output_name = "Analisis_Jarak_Jalan_Temp"
        temp_output_fc = os.path.join(dataset_path, temp_output_name)

        if simpan_temp:
            self.delete_if_exists(temp_output_fc)
            messages.addMessage("== Membuat layer sementara ==")
            arcpy.management.CopyFeatures(persil_fc, temp_output_fc)
            update_fc = temp_output_fc
        else:
            update_fc = persil_fc

        # 4. Menentukan layer untuk analisis
        persil_layer = "persil_input"
        self.delete_if_exists(persil_layer)
        arcpy.management.MakeFeatureLayer(update_fc, persil_layer)

        # 5. Logika Filter Multiple (Update & Null)
        where_clauses = []
        
        if hanya_update:
            where_clauses.append("UPPER(perubahan) IS NOT NULL")
        
        if hanya_yang_null and target_fields:
            # Contoh hasil: (JKKOLS IS NULL OR JKKOLS = 0 OR JKKOLP IS NULL OR JKKOLP = 0 ...)
            null_queries = [f"({fld} IS NULL OR {fld} = 0)" for fld in target_fields]
            null_where = " OR ".join(null_queries)
            where_clauses.append(f"({null_where})")
        
        if where_clauses:
            final_where = " AND ".join(where_clauses)
            messages.addMessage(f"== Menerapkan Filter: {final_where} ==")
            arcpy.management.SelectLayerByAttribute(persil_layer, "NEW_SELECTION", final_where)

        jumlah = int(arcpy.management.GetCount(persil_layer)[0])
        if jumlah == 0:
            messages.addMessage("== Tidak ada feature persil yang perlu diproses ==")
            return

        # 6. Membuat centroid dari persil
        messages.addMessage(f"== Membuat centroid untuk {jumlah} bidang persil ==")
        gdb_temp = arcpy.env.scratchGDB
        persilcentroid_path = os.path.join(gdb_temp, "Centroid_Persil")
        self.delete_if_exists(persilcentroid_path)
        
        arcpy.management.FeatureToPoint(persil_layer, persilcentroid_path, "INSIDE")
        
        oid_to_idbidang = {}
        oid_field = arcpy.Describe(persilcentroid_path).OIDFieldName

        with arcpy.da.SearchCursor(persilcentroid_path, [oid_field, "IDBIDANG"]) as rows:
            for oid, idbidang in rows:
                # Disimpan ke dictionary untuk lookup balik nanti dari hasil Network Analyst
                # Convert oid ke string karena arcpy NA mengembalikan nama incident (berbasis string OID)
                oid_to_idbidang[str(oid)] = idbidang

        # 7. Persiapan field pada jaringan jalan
        messages.addMessage("== Persiapan field impedansi jalan ==")
        self.add_field_if_not_exists(jaringanjalan_path, "P_Jalan", "DOUBLE")
        arcpy.management.CalculateField(jaringanjalan_path, "P_Jalan", "!shape.length!", "PYTHON3")

        outNALayerName = "NA_Closest_Facility"
        impedance_attribute = "P_Jalan"
        
        dataset_kelas_jalan_path = os.path.join(os.path.dirname(dataset_path), "kelas_jalan")

        # 8. Filter Feature Class Kelas Jalan yang Tersedia
        arcpy.env.workspace = dataset_kelas_jalan_path
        list_fc = arcpy.ListFeatureClasses("*") or []

        list_kelas_jalan = []
        for req_fc in requested_fc:
            nama_jalan_human = reverse_mapping.get(req_fc, req_fc)
            if req_fc in list_fc:
                temp_path = os.path.join(dataset_kelas_jalan_path, req_fc)
                jumlah_fc = int(arcpy.management.GetCount(temp_path)[0])
                if jumlah_fc > 0:
                    list_kelas_jalan.append(req_fc)
                else:
                    messages.addWarningMessage(f"Fasilitas {nama_jalan_human} kosong/tidak ada junction jalan yang terdata.")
            else:
                messages.addWarningMessage(f"Peringatan: Feature Class {req_fc} ({nama_jalan_human}) tidak ditemukan di geodatabase.")

        if not list_kelas_jalan:
            messages.addErrorMessage("Tidak ada satupun kelas jalan (Facilities) yang valid untuk dihitung. Proses dibatalkan.")
            return

        messages.addMessage(f"== Target Kelas Jalan NA: {list_kelas_jalan} ==")

        # 9. Setup Network Analysis (Closest Facility)
        # Checkout extension
        if arcpy.CheckExtension("Network") == "Available":
            arcpy.CheckOutExtension("Network")
        else:
            messages.addErrorMessage("Lisensi Network Analyst tidak tersedia.")
            raise arcpy.ExecuteError

        hasilNAObject = arcpy.na.MakeClosestFacilityLayer(
            in_network_dataset=nd_path,
            out_network_analysis_layer=outNALayerName,
            impedance_attribute=impedance_attribute,
            travel_from_to="TRAVEL_TO",
            default_cutoff=500000,
            default_number_facilities_to_find=1
        )
        outNALayer = hasilNAObject.getOutput(0)

        # Memasukkan titik centroid ke Incidents
        arcpy.na.AddLocations(
            in_network_analysis_layer=outNALayer,
            sub_layer="Incidents",
            in_table=persilcentroid_path,
            field_mappings=f"Name {oid_field} #", # Penting! Mapping nama incident menjadi OID sumber
            append="CLEAR"
        )
        
        jarak_dict = {}
        for kelas_jalan in list_kelas_jalan:
            messages.addMessage(f"== Menghitung rute NA untuk: {kelas_jalan} ==")

            kelas_jalan_path = os.path.join(dataset_kelas_jalan_path, kelas_jalan)
            kls = int(kelas_jalan.replace("JunctionKls", ""))
            nama_field_target = namafield[kls]

            # Memasukkan target junction ke Facilities
            arcpy.na.AddLocations(
                in_network_analysis_layer=outNALayer,
                sub_layer="Facilities",
                in_table=kelas_jalan_path,
                append="CLEAR"
            )

            solve_result = arcpy.na.Solve(outNALayer)
            if solve_result.getMessages(1):
                messages.addWarningMessage(f"NA Solve Warning ({kelas_jalan}): {solve_result.getMessages(1)}")

            # Optimasi RAM: Gunakan memory workspace untuk ekstrak output rute NA
            incident_mem = r"memory\NA_Incidents"
            route_mem = r"memory\NA_Routes"

            self.delete_if_exists(incident_mem)
            self.delete_if_exists(route_mem)

            for lyr in outNALayer.listLayers():
                if lyr.isGroupLayer:
                    continue
                if lyr.name == "Incidents":
                    arcpy.management.CopyFeatures(lyr, incident_mem)
                elif lyr.name == "Routes":
                    arcpy.management.CopyFeatures(lyr, route_mem)

            # 10. Membaca panjang rute dari NA_Routes
            # Field "IncidentID" di NA_Routes mengacu pada "ObjectID" dari NA_Incidents
            # Sedangkan "Name" di NA_Incidents menyimpan nilai OID dari persil centroid asli.
            
            # Mapping ObjectID (NA) -> Name (OID asli Centroid)
            na_inc_to_name = {}
            with arcpy.da.SearchCursor(incident_mem, ["OBJECTID", "Name"]) as rows:
                for oid, name_val in rows:
                    na_inc_to_name[oid] = name_val

            # Membaca jarak dari Routes
            with arcpy.da.SearchCursor(route_mem, ["IncidentID", "Total_P_Jalan"]) as rows:
                for inc_id, jarak in rows:
                    # Ambil "Name" (OID Centroid Asli)
                    asli_oid_str = na_inc_to_name.get(inc_id)
                    if not asli_oid_str:
                        continue
                    
                    # Ambil ID Bidang berdasarkan OID Centroid
                    idbidang = oid_to_idbidang.get(asli_oid_str)
                    
                    if idbidang is not None:
                        if idbidang not in jarak_dict:
                            jarak_dict[idbidang] = {}
                        jarak_dict[idbidang][nama_field_target] = jarak

        # Kembalikan Lisensi NA
        arcpy.CheckInExtension("Network")

        # 11. Update Atribut Jarak Jaringan ke layer Persil
        messages.addMessage("== Memperbarui atribut persil ==")
        
        update_fields = ["IDBIDANG", "JKKOLS", "JKKOLP", "JKATRS", "JKATRP"]
        with arcpy.da.UpdateCursor(persil_layer, update_fields) as rows:
            for row in rows:
                data_jarak = jarak_dict.get(row[0])
                if not data_jarak:
                    continue # Lewati jika persil ini gagal di-solve NA nya (misal tidak terkoneksi jaringan)
                
                # Hanya update field yang nilainya ditemukan
                if "JKKOLS" in data_jarak: row[1] = data_jarak["JKKOLS"]
                if "JKKOLP" in data_jarak: row[2] = data_jarak["JKKOLP"]
                if "JKATRS" in data_jarak: row[3] = data_jarak["JKATRS"]
                if "JKATRP" in data_jarak: row[4] = data_jarak["JKATRP"]

                rows.updateRow(row)

        # 12. Menampilkan output & Cleanup
        if simpan_temp:
            output_name = temp_output_name
        else:
            output_name = "Persil_Layer"

        self.delete_if_exists(output_name)
        arcpy.management.MakeFeatureLayer(update_fc, output_name)
        
        # Hapus temporary file dari memory RAM
        for item in [r"memory\NA_Incidents", r"memory\NA_Routes", persilcentroid_path]:
            self.delete_if_exists(item)

        parameters[4].value = output_name
        messages.addMessage("== Proses selesai dengan sukses ==")
        return


class Pengisian_Zonasi_Manual(object):

    def __init__(self):
        self.label = "Pengisian Zonasi Manual"
        self.description = "Update zonasi pada layer persil berdasarkan data eksisting atau input baru."
        self.canRunInBackground = False

    def getParameterInfo(self):
        # 0. Dropdown Zonasi Eksisting
        pilih_zona = arcpy.Parameter(
            displayName="Pilih Zonasi",
            name="pilih_zona",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )

        # 1. Checkbox Tambah Zonasi Baru
        tambah_zonasi_lain = arcpy.Parameter(
            displayName="Tambahkan Zonasi Lain",
            name="tambah_zonasi_lain",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )
        tambah_zonasi_lain.value = False

        # 2. Input Nama Zonasi Baru
        nama_zonasi_baru = arcpy.Parameter(
            displayName="Nama Zonasi Baru",
            name="nama_zonasi_baru",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )
        nama_zonasi_baru.enabled = False # Default mati sebelum dicentang

        # 3. Input Skor Zonasi Baru (Integer)
        skor_zonasi_baru = arcpy.Parameter(
            displayName="Skor Zonasi Baru",
            name="skor_zonasi_baru",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input"
        )
        skor_zonasi_baru.enabled = False # Default mati sebelum dicentang

        # 4. Checkbox Simpan Perubahan
        simpan_sebagai_perubahan = arcpy.Parameter(
            displayName="Simpan Sebagai Perubahan",
            name="simpan_sebagai_perubahan",
            datatype="GPBoolean",
            parameterType="Required",
            direction="Input"
        )
        simpan_sebagai_perubahan.value = True

        # 5. Output Derived Layer
        output_data = arcpy.Parameter(
            name="persil_layer",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [
            pilih_zona, 
            tambah_zonasi_lain, 
            nama_zonasi_baru, 
            skor_zonasi_baru, 
            simpan_sebagai_perubahan, 
            output_data
        ]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        # Mengisi Dropdown berdasarkan kolom ZONASI langsung dari Feature Class fisik
        if not parameters[0].altered:
            try:
                # 1. Panggil konfigurasi untuk mendapatkan path asli dataset
                configs = persil.get_config_values()
                dataset_path = configs["project_config"]["dataset_path"]
                
                # 2. Gabungkan path dataset dengan nama feature class
                persil_fc_path = os.path.join(dataset_path, "Persil_Layer")

                # 3. Cek eksistensi menggunakan path fisik, bukan nama layer
                if arcpy.Exists(persil_fc_path):
                    with arcpy.da.SearchCursor(persil_fc_path, ["ZONASI"]) as cursor:
                        # Ambil nilai unik dan abaikan Null/None
                        zonasi_list = sorted(list(set([row[0] for row in cursor if row[0]])))
                    parameters[0].filter.list = zonasi_list
            except Exception:
                pass

        # Logika centang: Buka parameter baru dan matikan dropdown jika dicentang
        if parameters[1].value: 
            parameters[2].enabled = True
            parameters[3].enabled = True
            parameters[0].enabled = False
        else:
            parameters[2].enabled = False
            parameters[3].enabled = False
            parameters[0].enabled = True
            
        return


    def updateMessages(self, parameters):
        return

    def add_field_if_not_exists(self, feature_class, field_name, field_type):
        field_names = [field.name for field in arcpy.ListFields(feature_class)]
        if field_name not in field_names:
            arcpy.management.AddField(feature_class, field_name, field_type)

    def execute(self, parameters, messages):
        messages.addMessage("== Proses dimulai ==")

        pilih_zona = parameters[0].valueAsText
        tambah_zonasi_lain = parameters[1].value
        nama_zonasi_baru = parameters[2].valueAsText
        skor_zonasi_baru = parameters[3].value
        simpan_sebagai_data_baru = parameters[4].value
        if tambah_zonasi_lain:
            if not nama_zonasi_baru:
                messages.addErrorMessage("== Nama zonasi baru wajib diisi ==")
                raise arcpy.ExecuteError
            if skor_zonasi_baru is None:
                messages.addErrorMessage("== Skor zonasi baru wajib diisi ==")
                raise arcpy.ExecuteError
        else:
            if not pilih_zona:
                messages.addErrorMessage("== Silakan pilih zonasi dari daftar ==")
                raise arcpy.ExecuteError
        configs = persil.get_config_values()
        dataset_path = configs["project_config"]["dataset_path"]
        
        persil_edit = "Persil_Layer"
        persil_edit_path = os.path.join(dataset_path, persil_edit)

        # ---------------------------------------------------------
        # Menentukan Nilai Zonasi & Skor yang akan diupdate
        # ---------------------------------------------------------
        if tambah_zonasi_lain:
            zonasi_final = nama_zonasi_baru
            s_zonasi_final = skor_zonasi_baru
            min_lb_jln_final = 1.5 # Default fallback
        else:
            zonasi_final = pilih_zona
            s_zonasi_final = 0
            min_lb_jln_final = 1.5
            
            with arcpy.da.SearchCursor(persil_edit, ["ZONASI", "S_ZONASI", "min_lb_jln"]) as cursor:
                for row in cursor:
                    if row[0] == zonasi_final:
                        s_zonasi_final = row[1] if row[1] is not None else 0
                        min_lb_jln_final = row[2] if row[2] is not None else 1.5
                        break

        # Pastikan field min_lb_jln ada
        self.add_field_if_not_exists(persil_edit_path, "min_lb_jln", "DOUBLE")

        # Pengecekan field wajib
        required_fields = ["ZONASI", "S_ZONASI", "min_lb_jln", "perubahan"]
        persil_fields = [f.name for f in arcpy.ListFields(persil_edit_path)]
        missing_fields = [f for f in required_fields if f not in persil_fields]

        if missing_fields:
            messages.addErrorMessage(f"== Field berikut tidak ditemukan: {', '.join(missing_fields)} ==")
            raise arcpy.ExecuteError

        # Cek apakah ada fitur yang di-select
        ada_seleksi = len(arcpy.Describe(persil_edit).FIDSet)
        if ada_seleksi == 0:
            messages.addWarningMessage("== Tidak ada persil yang dipilih. Silakan seleksi persil terlebih dahulu. ==")
            return

        messages.addMessage(f"== Mengupdate zonasi menjadi: {zonasi_final} (Skor: {s_zonasi_final}) ==")

        # Update data persil
        with arcpy.da.UpdateCursor(persil_edit, ["ZONASI", "S_ZONASI", "min_lb_jln", "perubahan"]) as rows:
            for row in rows:
                row[0] = zonasi_final
                row[1] = s_zonasi_final
                row[2] = min_lb_jln_final

                if simpan_sebagai_data_baru:
                    row[3] = "menyebar"
                
                rows.updateRow(row)

        messages.addMessage("== Proses update atribut selesai ==")

        simbology_path = r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Simbologi_Zonasi_Persil_Layer.lyrx"
        try:
            arcpy.management.MakeFeatureLayer(persil_edit_path, "Persil_Layer")
            arcpy.management.ApplySymbologyFromLayer("Persil_Layer", simbology_path)
        except Exception as e:
            messages.addWarningMessage(f"== Gagal mengaplikasikan simbologi: {e} ==")

        arcpy.SetParameter(5, "Persil_Layer")
        return
                     
class FilterPersilJalan(object):
    def __init__(self):
        self.label = "Filter Persil Jaringan Jalan"
        self.description = "Mendeteksi dan memisahkan persil jaringan jalan berdasarkan bentuk geometri memanjang (Rasio Keliling² / Luas)."
        self.canRunInBackground = False

    def getParameterInfo(self):
        # 0. Parameter Input Feature
        in_features = arcpy.Parameter(
            displayName="Data Persil Input",
            name="in_features",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        in_features.filter.list = ["Polygon"]

        # 1. Parameter Output Persil Bersih
        out_persil = arcpy.Parameter(
            displayName="Output Persil Utama (Tanpa Jalan)",
            name="out_persil",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output")

        # 2. Parameter Output Persil Jalan
        out_jalan = arcpy.Parameter(
            displayName="Output Persil Jaringan Jalan",
            name="out_jalan",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output")

        # 3. Parameter Ambang Batas (Threshold)
        threshold = arcpy.Parameter(
            displayName="Ambang Batas Kepanjangan (Default: 80)",
            name="threshold",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input")
        threshold.value = 80.0 

        return [in_features, out_persil, out_jalan, threshold]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        in_features = parameters[0].valueAsText
        out_persil = parameters[1].valueAsText
        out_jalan = parameters[2].valueAsText
        threshold = parameters[3].value

        # Salin fitur ke output pertama (yang nantinya akan dihapus bagian jalannya)
        arcpy.AddMessage("Menyalin data ke output persil utama...")
        arcpy.management.CopyFeatures(in_features, out_persil)

        # Tambahkan field sementara untuk kalkulasi rasio kepanjangan
        arcpy.AddMessage("Menghitung indeks kepanjangan geometri...")
        temp_field = "Ratio_Jalan_Tmp"
        arcpy.management.AddField(out_persil, temp_field, "DOUBLE")
        
        # Kalkulasi (Shape_Length * Shape_Length) / Shape_Area
        # Menggunakan code block untuk mencegah error pembagian dengan nol pada poligon sliver
        code_block = """def get_ratio(length, area):
            if area == 0 or area is None:
                return 0
            return (length * length) / area"""
            
        calc_expression = "get_ratio(!Shape_Length!, !Shape_Area!)"
        arcpy.management.CalculateField(out_persil, temp_field, calc_expression, "PYTHON3", code_block)

        # Buat Layer sementara untuk seleksi
        lyr_name = "persil_lyr"
        arcpy.management.MakeFeatureLayer(out_persil, lyr_name)

        # Lakukan seleksi berdasarkan threshold
        query = f"{temp_field} >= {threshold}"
        arcpy.AddMessage(f"Memilih persil dengan rasio kepanjangan >= {threshold}...")
        arcpy.management.SelectLayerByAttribute(lyr_name, "NEW_SELECTION", query)

        # Hitung jumlah jalan yang terdeteksi
        match_count = int(arcpy.management.GetCount(lyr_name).getOutput(0))
        arcpy.AddMessage(f"Ditemukan {match_count} persil jaringan jalan.")

        if match_count > 0:
            # Simpan hasil seleksi sebagai output persil jalan
            arcpy.AddMessage("Menyimpan data persil jaringan jalan...")
            arcpy.management.CopyFeatures(lyr_name, out_jalan)
            
            # Hapus persil jalan dari data persil utama
            arcpy.AddMessage("Menghapus geometri jalan dari persil utama...")
            arcpy.management.DeleteFeatures(lyr_name)
        else:
            # Jika tidak ada yang memenuhi syarat, buat output jalan kosong
            arcpy.AddMessage("Tidak ada persil jalan yang terdeteksi. Membuat output jalan kosong...")
            arcpy.management.CopyFeatures(lyr_name, out_jalan) 

        # Bersihkan field sementara dari kedua output
        arcpy.AddMessage("Membersihkan field sementara...")
        arcpy.management.DeleteField(out_persil, temp_field)
        if match_count > 0:
            arcpy.management.DeleteField(out_jalan, temp_field)

        arcpy.AddMessage("Proses selesai.")
        return

class Pengisian_Zonasi_Otomatis(object):

    def __init__(self):
        self.label = "Pengisian Zonasi Otomatis"
        self.description = "Mengisi zonasi Null berdasarkan 3 bidang terdekat, mengupdate S_ZONASI, dan perubahan."
        self.canRunInBackground = False

    def getParameterInfo(self):
        
        
        output_data = arcpy.Parameter(
            name="output_layer",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [output_data]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        messages.addMessage("== Memulai proses otomatisasi zonasi ==")
        config = persil.get_config_values()
        ds_path = config['project_config']['dataset_path']


        input_layer = os.path.join(ds_path, 'Persil_layer')

        # 1. Pengecekan Field yang Dibutuhkan
        required_fields = ["ZONASI", "S_ZONASI", "perubahan"]
        existing_fields = [f.name for f in arcpy.ListFields(input_layer)]
        missing_fields = [f for f in required_fields if f not in existing_fields]

        if missing_fields:
            messages.addErrorMessage(f"== Field berikut tidak ditemukan pada layer: {', '.join(missing_fields)} ==")
            raise arcpy.ExecuteError

        # 2. Kumpulkan Data Bidang Valid & Bangun Kamus Skor Dinamis
        valid_features = []
        zonasi_score_dict = {} # Dictionary untuk menyimpan pasangan Zonasi & Skornya
        
        where_valid = "ZONASI IS NOT NULL AND ZONASI <> '' AND ZONASI <> ' '"
        
        messages.addMessage("== Membaca referensi zonasi dan skor dari layer... ==")
        
        # Tambahkan S_ZONASI ke dalam SearchCursor
        with arcpy.da.SearchCursor(input_layer, ["SHAPE@", "ZONASI", "S_ZONASI"], where_valid) as cursor:
            for row in cursor:
                geom = row[0]
                zonasi = row[1]
                skor = row[2] if row[2] is not None else 0
                
                valid_features.append((geom, zonasi))
                
                # Membangun dictionary dinamis dari data yang ada di layer
                if zonasi not in zonasi_score_dict:
                    zonasi_score_dict[zonasi] = skor
                else:
                    # Jika zonasi sudah ada, cek apakah skornya sama
                    if zonasi_score_dict[zonasi] != skor:
                        messages.addErrorMessage(
                            f"== Proses Dihentikan: Terdapat inkonsistensi skor pada zonasi '{zonasi}'. "
                            f"Ditemukan skor {zonasi_score_dict[zonasi]} dan {skor} di dalam layer. "
                            f"Harap perbaiki dan seragamkan skor pada atribut layer terlebih dahulu. =="
                        )
                        return
                
        if not valid_features:
            messages.addErrorMessage("== Tidak ada satupun bidang dengan zonasi yang valid untuk dijadikan referensi ==")
            raise arcpy.ExecuteError

        # 3. Proses Bidang yang ZONASI-nya Null/Kosong
        where_null = "ZONASI IS NULL OR ZONASI = '' OR ZONASI = ' '"
        update_fields = ["SHAPE@", "ZONASI", "S_ZONASI", "perubahan"]
        
        updated_count = 0
        messages.addMessage("== Memproses bidang dengan Zonasi Null... ==")
        
        with arcpy.da.UpdateCursor(input_layer, update_fields, where_null) as cursor:
            for row in cursor:
                null_geom = row[0]
                
                # Lewati jika geometrinya bermasalah
                if null_geom is None:
                    continue

                # Hitung jarak dari bidang null ini ke semua bidang valid
                distances = []
                for valid_geom, v_zonasi in valid_features:
                    # distanceTo menghitung jarak terpendek antar geometri
                    dist = null_geom.distanceTo(valid_geom)
                    distances.append((dist, v_zonasi))

                # Urutkan berdasarkan jarak terdekat dan ambil 3 teratas
                distances.sort(key=lambda x: x[0])
                top_3 = distances[:3]
                
                # Ambil daftar ZONASI dari 3 bidang terdekat tersebut
                top_3_zonasi = [item[1] for item in top_3]

                if top_3_zonasi:
                    # Gunakan collections.Counter untuk mencari ZONASI yang paling banyak muncul (Mayoritas)
                    most_common_zonasi = Counter(top_3_zonasi).most_common(1)[0][0]
                    
                    # Dapatkan S_ZONASI langsung dari kamus dinamis yang kita buat dari layer
                    s_zonasi_value = zonasi_score_dict.get(most_common_zonasi, 0)

                    # Update Row (Index disesuaikan dengan update_fields)
                    row[1] = most_common_zonasi        # ZONASI
                    row[2] = s_zonasi_value            # S_ZONASI
                    row[3] = "menyebar"                
                    
                    cursor.updateRow(row)
                    updated_count += 1

        messages.addMessage(f"== Proses selesai. Berhasil memperbarui {updated_count} bidang ==")
        
        # Set parameter output agar memicu refresh di map
        arcpy.SetParameter(1, input_layer)
        return