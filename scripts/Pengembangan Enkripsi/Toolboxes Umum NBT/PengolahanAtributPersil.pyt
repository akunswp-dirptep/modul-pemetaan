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
                      Pengisian_Bentuk_Persil_Otomatis,
                      Pengisian_WADMKC_WADMKD_Otomatis,
                      Pengisian_WADMKC_WADMKD_Manual
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
      
class Pengisian_WADMKC_WADMKD_Otomatis(object):
    def __init__(self):
        self.label = "Isi WADMKC & WADMKD Secara Otomatis"
        self.description = "Mengisi atribut WADMKC dan WADMKD yang Null berdasarkan 3 bidang terdekat, mengupdate status_per, dan perubahan."
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

        has_status = "STATUS_PER" in existing_fields or "STATUS_PERUBAHAN" in existing_fields
        has_perubahan = "PERUBAHAN" in existing_fields
        
        status_field_name = existing_fields.get("STATUS_PER", existing_fields.get("STATUS_PERUBAHAN", ""))
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
            if has_status: update_fields.append(status_field_name)
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
                            
                            if has_status:
                                row[update_fields.index(status_field_name)] = "update"
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

        has_status = "STATUS_PER" in existing_fields or "STATUS_PERUBAHAN" in existing_fields
        has_perubahan = "PERUBAHAN" in existing_fields
        
        status_field_name = existing_fields.get("STATUS_PER", existing_fields.get("STATUS_PERUBAHAN", ""))
        perubahan_field_name = existing_fields.get("PERUBAHAN", "")

        if has_status: update_fields.append(status_field_name)
        if has_perubahan: update_fields.append(perubahan_field_name)

        updated_count = 0
        
        with arcpy.da.UpdateCursor(layer_name, update_fields) as uc:
            for row in uc:
                
                if wadmkc_val:
                    row[update_fields.index("WADMKC")] = wadmkc_val
                if wadmkd_val:
                    row[update_fields.index("WADMKD")] = wadmkd_val
                
                if has_status:
                    row[update_fields.index(status_field_name)] = "update"
                if has_perubahan:
                    row[update_fields.index(perubahan_field_name)] = "menyebar"
                    
                uc.updateRow(row)
                updated_count += 1

        messages.addMessage(f"Selesai! Berhasil meng-update {updated_count} bidang pada Persil_Layer")
        return


