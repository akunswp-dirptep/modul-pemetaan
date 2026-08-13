import os, arcpy, json, sys, datetime, gc, time

arcpy.env.outputZFlag = "Disabled"
arcpy.env.outputMFlag = "Disabled"

# Tambahkan parent directory ke sys.path
script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from zntutils import zona_layer as zonalayer
from zntutils import sample_point as samplepoint


class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox Perhitungan ZNT"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [Hitung_Indeks_Nilai_Tanah, Hitung_Nilai_ZNT_Pencilan_Atau_Outlier, Hitung_Nilai_ZNT_Pembaruan]


class Hitung_Indeks_Nilai_Tanah:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Hitung Indeks Nilai Tanah"
        self.description = ""

    def getParameterInfo(self):
        """Define the tool parameters."""
        penjelasan = arcpy.Parameter(
            displayName="Apa yang dilakukan tool ini?",
            name="penjelasan",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")
        penjelasan.value = (
            "Tool ini menghitung indeks nilai tanah\n"
            "untuk setiap zona berdasarkan rata-rata\n"
            "indeks sampel dari titik zona yang berada\n"
            "dalam zona tersebut. Indeks nilai tanah\n"
            "hanya akan dihitung untuk zona untuk pembaruan.\n\n"
            "Direktorat Penilaian Tanah & Ekonomi Pertanahan\n"
            "Kementerian ATR/BPN\n"
            "Tahun: {}".format(datetime.datetime.now().year))
        params = [penjelasan]
        return params

    def isLicensed(self):
        """Set whether the tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter. This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
 
        arcpy.env.overwriteOutput = True

        titik_zona = "Titik_Zona"
        zona_layer = "Zona_Layer"

        mean_table = "in_memory/indeks_nilai_tanah_table"
        zout_path = "in_memory/jenis_zona_join"   

        mean_field_name = "indeks_nilai_tanah"
        join_key_field = "Keterangan"

        zonalayer.check_if_there_selected_field()
        zonalayer.delete_bad_file()

        config_dan_paths = zonalayer.get_config_values()
        zl_path = os.path.join(config_dan_paths['dataset_path'], 'Zona_Layer')
        tz_path = os.path.join(config_dan_paths['dataset_path'], 'Titik_Zona')

        arcpy.analysis.SpatialJoin(zl_path, tz_path, zout_path, 'JOIN_ONE_TO_MANY')
        AdaZona = set()

        with arcpy.da.SearchCursor(zout_path, ["Join_Count", "TARGET_FID"]) as cursor:
            for join_count, target_fid in cursor:
                if join_count > 0:
                    AdaZona.add(target_fid)

        del cursor
        gc.collect()

        clusters = {'1': {}, '2': {}}
        oid_jnszn_map = {}

        with arcpy.da.SearchCursor(zl_path, ["OBJECTID", "JNSZN"]) as cursor:
            for oid, jnszn in cursor:
                oid_jnszn_map[oid] = jnszn

        del cursor
        gc.collect()

        with arcpy.da.SearchCursor(zl_path, ["OBJECTID", "cluster", "JNSZN"]) as cursor:
            for oid, cluster_val, jnszn in cursor:
                if cluster_val is not None:
                    clusters[str(jnszn)].setdefault(cluster_val, []).append(oid)

        del cursor
        gc.collect()

        invalid_clusters_info = []

        for jnszn, cluster_dict in clusters.items():
            for cluster_val, oids in cluster_dict.items():
                if not any(oid in AdaZona for oid in oids):
                    first_oid = oids[0]
                    jnszn_val = oid_jnszn_map.get(first_oid, "N/A")

                    invalid_clusters_info.append(
                        f"Jenis Zona {'Pertanian' if jnszn_val == 2 else 'Non-Pertanian'} - Cluster {cluster_val}"
                    )

        if invalid_clusters_info:
            arcpy.AddWarning(
                "Terdapat Klaster tanpa Titik Zona:\n" + "\n".join(invalid_clusters_info)
            )
            sys.exit(1)

        arcpy.AddMessage("✅ Validasi klaster OK")

        # ===============================
        # FIELD TITIK_ZONA
        # ===============================
        if join_key_field not in [f.name for f in arcpy.ListFields(titik_zona)]:
            arcpy.management.AddField(titik_zona, join_key_field, "TEXT")

        arcpy.management.CalculateField(
            titik_zona,
            join_key_field,
            "'Jenis Zona: ' + str(!JNSZN!) + ' dan Cluster: ' + str(!cluster!)",
            "PYTHON3"
        )

        arcpy.analysis.Statistics(
            titik_zona,
            mean_table,
            [["indeks_sampel", "MEAN"]],
            ["cluster", "JNSZN"]
        )

        if join_key_field not in [f.name for f in arcpy.ListFields(mean_table)]:
            arcpy.management.AddField(mean_table, join_key_field, "TEXT")

        arcpy.management.CalculateField(
            mean_table,
            join_key_field,
            "'Jenis Zona: ' + str(!JNSZN!) + ' dan Cluster: ' + str(!cluster!)",
            "PYTHON3"
        )

        # ===============================
        # JOIN KE TITIK_ZONA
        # ===============================
        if mean_field_name not in [f.name for f in arcpy.ListFields(titik_zona)]:
            arcpy.management.AddField(titik_zona, mean_field_name, "DOUBLE")

        arcpy.management.JoinField(
            titik_zona,
            join_key_field,
            mean_table,
            join_key_field,
            ["MEAN_indeks_sampel"]
        )

        arcpy.management.CalculateField(
            titik_zona,
            mean_field_name,
            "!MEAN_indeks_sampel!",
            "PYTHON3"
        )

        arcpy.management.DeleteField(titik_zona, ["MEAN_indeks_sampel"])

        # ===============================
        # ZONA_LAYER
        # ===============================
        if join_key_field not in [f.name for f in arcpy.ListFields(zona_layer)]:
            arcpy.management.AddField(zona_layer, join_key_field, "TEXT")

        arcpy.management.CalculateField(
            zona_layer,
            join_key_field,
            "('Jenis Zona: ' + str(!JNSZN!) + ' dan Cluster: ' + str(!cluster!)) if !cluster! not in [None, '', 'NULL'] else 'Zona outlier'",
            "PYTHON3"
        )

        if mean_field_name not in [f.name for f in arcpy.ListFields(zona_layer)]:
            arcpy.management.AddField(zona_layer, mean_field_name, "DOUBLE")

        arcpy.management.JoinField(
            zona_layer,
            join_key_field,
            mean_table,
            join_key_field,
            ["MEAN_indeks_sampel"]
        )

        with arcpy.da.UpdateCursor(zona_layer, ["cluster", "MEAN_indeks_sampel", mean_field_name]) as cursor:
            for cluster_val, mean_val, _ in cursor:
                if cluster_val not in [None, "", "NULL"]:
                    cursor.updateRow((cluster_val, mean_val, mean_val))
                else:
                    cursor.updateRow((cluster_val, mean_val, None))

        del cursor
        gc.collect()

        arcpy.management.DeleteField(zona_layer, ["MEAN_indeks_sampel"])

        # ===============================
        # CLEANUP AMAN
        # ===============================
        def safe_delete(path):
            for i in range(5):
                try:
                    if arcpy.Exists(path):
                        arcpy.Delete_management(path)
                    return
                except:
                    time.sleep(1)
                    arcpy.ClearWorkspaceCache_management()

        time.sleep(1)
        arcpy.ClearWorkspaceCache_management()
        gc.collect()

        safe_delete(zout_path)
        safe_delete(mean_table)

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return

class Hitung_Nilai_ZNT_Pencilan_Atau_Outlier:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Hitung Nilai ZNT Pencilan Atau Outlier"
        self.description = "Menghitung nilai ZNT untuk zona pencilan/outlier dan mengosongkan nilai clusternya."

    def getParameterInfo(self):
        """Define the tool parameters."""
        pembulatan = arcpy.Parameter(
            displayName="Pembulatan Nilai ZNT Pencilan",
            name="pembulatan",
            datatype="GPLong",
            parameterType="Required",
            direction="Input"
        )
        pembulatan.value = 1000
        
        penjelasan = arcpy.Parameter(
            displayName="Apa yang dilakukan tool ini?",
            name="penjelasan",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )
        penjelasan.value = (
            "Tool ini menghitung nilai ZNT untuk zona yang\n"
            "merupakan pencilan atau outlier\n"
            "Nilai ZNT dihitung berdasarkan rata-rata nilai\n"
            "tanah (m2) dari titik sampel yang berada dalam zona tersebut\n"
            "Tool ini hanya memproses zona yang memiliki cluster\n"
            "null atau tidak memiliki cluster sama sekali.\n\n"
            "Direktorat Penilaian Tanah & Ekonomi Pertanahan\n"
            "Kementerian ATR/BPN\n"
            f"Tahun: {datetime.datetime.now().year}"
        )
        
        return [pembulatan, penjelasan]

    def isLicensed(self):
        """Set whether the tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal validation is performed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool parameter."""
        return

    def execute(self, parameters, messages):
        # Asumsi 'zonalayer' adalah modul/objek global yang sudah di-import sebelumnya
        zonalayer.check_if_there_selected_field()
        zonalayer.delete_bad_file()

        pembulatan = int(parameters[0].valueAsText)
        arcpy.env.overwriteOutput = True

        aprx = arcpy.mp.ArcGISProject("CURRENT")
        m = aprx.activeMap

        def get_layer_by_name(name):
            for lyr in m.listLayers():
                if lyr.name == name:
                    return lyr
            return None

        titik_sampel = get_layer_by_name("Titik_Sampel")
        zona_layer = get_layer_by_name("Zona_Layer")

        if not titik_sampel or not zona_layer:
            arcpy.AddError("❌ Layer 'Titik_Sampel' dan 'Zona_Layer' harus ada.")
            sys.exit(1)

        count = int(arcpy.management.GetCount(titik_sampel)[0])
        if count == 0:
            arcpy.AddWarning("Tidak ditemukan titik sampel")
            return

        identity_output = "in_memory/identity_result"
        dissolved_output = "in_memory/dissolved_stats"

        arcpy.analysis.Identity(titik_sampel, zona_layer, identity_output)
        arcpy.AddMessage("✅ Identity selesai")

        zone_id_field = f"FID_{zona_layer.name}"

        stat_fields = [
            ["Nilai", "SUM"], ["Nilai", "MEAN"], ["Nilai", "MIN"],
            ["Nilai", "MAX"], ["Nilai", "STD"], ["Nilai", "COUNT"], ["Nilai", "RANGE"]
        ]

        arcpy.management.Dissolve(
            in_features=identity_output,
            out_feature_class=dissolved_output,
            dissolve_field=zone_id_field,
            statistics_fields=stat_fields
        )

        arcpy.AddMessage("Memvalidasi jumlah titik...")

        zona_invalid = []
        with arcpy.da.SearchCursor(dissolved_output, [zone_id_field, "COUNT_Nilai"]) as cursor:
            for zone_fid, count_nilai in cursor:
                if count_nilai < 3:
                    with arcpy.da.SearchCursor(zona_layer, ["NOZN"], f"OBJECTID = {zone_fid}") as z_cursor:
                        for z_row in z_cursor:
                            zona_invalid.append(f"NOZN {z_row[0]} (hanya {count_nilai} titik)")
                            break

        del cursor
        gc.collect()

        if zona_invalid:
            arcpy.AddError(f"Proses dihentikan. Zona berikut < 3 titik: {', '.join(zona_invalid)}")
            sys.exit(1)

        arcpy.AddMessage("✅ Validasi OK")

        # Melakukan Join data hasil dissolve ke zona_layer
        arcpy.management.JoinField(
            in_data=zona_layer,
            in_field="OBJECTID",
            join_table=dissolved_output,
            join_field=zone_id_field
        )

        field_map = {
            "NILAIZN": "DOUBLE",
            "JMLSMPL": "LONG",
            "JMLNILAI": "DOUBLE",
            "NILMIN": "DOUBLE",
            "NILMAKS": "DOUBLE",
            "SMPBAKU": "DOUBLE",
            "SMPBKREL": "DOUBLE",
            "NILBULAT": "TEXT"
        }

        existing_fields = [f.name for f in arcpy.ListFields(zona_layer)]

        # Menambahkan field jika belum ada
        for field, ftype in field_map.items():
            if field not in existing_fields:
                arcpy.management.AddField(zona_layer, field, ftype)

        # Cek dan tambahkan field 'cluster' jika tidak sengaja belum ada
        cluster_field = "cluster"
        existing_fields_lower = [f.lower() for f in existing_fields]
        
        if cluster_field.lower() not in existing_fields_lower:
            arcpy.management.AddField(zona_layer, cluster_field, "TEXT", field_length=50)
        else:
            # Ambil nama field cluster sesuai case aslinya di tabel
            cluster_field = existing_fields[existing_fields_lower.index(cluster_field.lower())]

        arcpy.AddMessage("Menghitung nilai atribut...")

        # Kalkulasi atribut
        arcpy.management.CalculateField(zona_layer, "JMLNILAI", "round(!SUM_Nilai!) if !SUM_Nilai! is not None else None", "PYTHON3")
        arcpy.management.CalculateField(zona_layer, "NILAIZN", "round(!MEAN_Nilai!) if !MEAN_Nilai! is not None else None", "PYTHON3")
        arcpy.management.CalculateField(zona_layer, "NILMIN", "!MIN_Nilai!", "PYTHON3")
        arcpy.management.CalculateField(zona_layer, "NILMAKS", "!MAX_Nilai!", "PYTHON3")
        arcpy.management.CalculateField(zona_layer, "SMPBAKU", "!STD_Nilai!", "PYTHON3")
        arcpy.management.CalculateField(zona_layer, "JMLSMPL", "!COUNT_Nilai!", "PYTHON3")
        arcpy.management.CalculateField(zona_layer, "SMPBKREL", "(!SMPBAKU! / !NILAIZN!) * 100 if !NILAIZN! else None", "PYTHON3")

        # Perbaikan indentasi pada code_block python
        code_block = f"""def format_rp(value):
    if value:
        bulat = round(value / {pembulatan}) * {pembulatan}
        return "Rp. " + format(int(bulat), ",").replace(",", ".")
    return "Rp. 0"
"""
        arcpy.management.CalculateField(zona_layer, "NILBULAT", "format_rp(!NILAIZN!)", "PYTHON3", code_block)

        # === TAMBAHAN KODE: Set field cluster menjadi Null (None) untuk zona yang dihitung nilainya ===
        # Logika: Jika field COUNT_Nilai (hasil join) ada isinya, berarti zona tersebut ikut dihitung, maka cluster = None
        arcpy.management.CalculateField(
            zona_layer, 
            cluster_field, 
            f"None if !COUNT_Nilai! is not None else !{cluster_field}!", 
            "PYTHON3"
        )
        arcpy.AddMessage("✅ Nilai Cluster dikosongkan (Null) untuk zona outlier.")
        # ==============================================================================================

        # Membersihkan field hasil join statistik
        stat_keywords = ["sum_nilai", "mean_nilai", "min_nilai", "max_nilai", "std_nilai", "count_nilai", "range_nilai"]
        delete_fields = [
            f.name for f in arcpy.ListFields(zona_layer)
            if any(k in f.name.lower() for k in stat_keywords) or f.name.lower().startswith("fid_")
        ]

        if delete_fields:
            arcpy.management.DeleteField(zona_layer, delete_fields)

        def safe_delete(path):
            for i in range(5):
                try:
                    if arcpy.Exists(path):
                        arcpy.management.Delete(path)
                    return
                except Exception:
                    time.sleep(1)
                    arcpy.management.ClearWorkspaceCache()

        time.sleep(1)
        arcpy.management.ClearWorkspaceCache()
        gc.collect()

        safe_delete(identity_output)
        safe_delete(dissolved_output)
        
        arcpy.AddMessage("✅ Proses selesai.")

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and added to the display."""
        return
    
class Hitung_Nilai_ZNT_Pembaruan:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Hitung Nilai ZNT Pembaruan"
        self.description = ""

    def getParameterInfo(self):
        """Define the tool parameters."""
        pembulatan = arcpy.Parameter(
            displayName="Pembulatan Nilai ZNT Pembaruan",
            name="pembulatan",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        pembulatan.value = 1000
        penjelasan = arcpy.Parameter(
            displayName="Apa yang dilakukan tool ini?",
            name="penjelasan",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")
        penjelasan.value = (
            "Tool ini menghitung nilai ZNT baru dengan\n"
            "mengkalikan nilai lama dengan indeks nilai\n"
            "tanah yang sudah dihitung sebelumnya.\n"
            "Tool ini hanya memproses zona yang memiliki\n"
            "cluster valid (tidak null) dan memiliki nilai\n"
            "indeks nilai tanah.\n\n"
            "Direktorat Penilaian Tanah & Ekonomi Pertanahan\n"
            "Kementerian ATR/BPN\n"
            "Tahun: {}".format(datetime.datetime.now().year))
        params = [pembulatan, penjelasan]
        return params

    def isLicensed(self):
        """Set whether the tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter. This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        zonalayer.check_if_there_selected_field()
        zonalayer.delete_bad_file()

        pembulatan = int(parameters[0].valueAsText)
        workspace = arcpy.env.scratchGDB
        arcpy.env.workspace = workspace

        aprx = arcpy.mp.ArcGISProject("CURRENT")
        m = aprx.activeMap

        def get_layer_by_name(name):
            for lyr in m.listLayers():
                if lyr.name == name:
                    return lyr
            return None

        zona_layer = get_layer_by_name("Zona_Layer")


        if not zona_layer:
            arcpy.AddError("❌ Layer yang diperlukan tidak ditemukan di peta. Pastikan layer 'Zona_Layer' ada.")
            sys.exit(1)

        def ensure_fields_exist(layer, required_fields):
            existing_fields = {field.name.upper() for field in arcpy.ListFields(layer)}
            missing_fields = [field_name for field_name in required_fields if field_name.upper() not in existing_fields]

            if missing_fields:

                for field_name in missing_fields:
                    if  field_name == 'indeks_nilai_tanah':
                        arcpy.AddError("Data Indeks Nilai Tanah tidak ditemukan. Pastikan sudah menjalankan tool Hitung Indeks Nilai Tanah terlebih dahulu.")
                        
                    else:
                        arcpy.AddError(
                        f"Field berikut tidak ditemukan pada Zona_Layer: {field_name}"
                    )
                sys.exit(1)

        fields = ['cluster', 'NILAIZN', 'NILAIZN_LAMA', 'indeks_nilai_tanah']
        ensure_fields_exist(zona_layer, fields)

        with arcpy.da.UpdateCursor(zona_layer, fields) as cursor:
            for row in cursor:
                # === Proses hanya jika cluster tidak null ===
                if row[0] not in [None, "", "NULL"] and row[3] is not None and row[2] is not None:
                    try:
                        nilai_lama = float(row[2])
                        row[1] = round(nilai_lama * float(row[3]/100))
                    except (TypeError, ValueError):
                        row[1] = None
                cursor.updateRow(row)

        arcpy.AddMessage("✅ Data Nilai zona berhasil dihitung untuk zona dengan cluster valid.")

        if "NILBULAT" not in [f.name for f in arcpy.ListFields(zona_layer)]:
            arcpy.management.AddField(zona_layer, "NILBULAT", "TEXT", field_length=50)


        # Blok kode Python untuk fungsi pembulatan dan formatting
        code_block = f"""def doSomething(mean_val, pembulatan):
            if mean_val:
                # Membulatkan ke kelipatan terdekat dari nilai pembulatan
                rounded = round(mean_val / pembulatan) * pembulatan
                # Memformat nilai dengan separator ribuan
                return "Rp. {{:,}}".format(int(rounded)).replace(",", ".")
            else:
                return ""
        """

        # Menghitung field NILBULAT dengan fungsi kustom
        arcpy.management.CalculateField(
            zona_layer,
            "NILBULAT",
            f"doSomething(int(!NILAIZN!), {pembulatan})",
            "PYTHON3",
            code_block
        )

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return
