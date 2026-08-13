# -*- coding: utf-8 -*-

import arcpy, os,sys, datetime
# Tambahkan parent directory ke sys.path
script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

arcpy.env.outputZFlag = "Disabled"
arcpy.env.outputMFlag = "Disabled"

from zntutils import zona_layer as zonalayer
from zntutils import sample_point as samplepoint

class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [Simbologi_Titik_Zona, 
                      Pemilihan_Titik_Sampel_Outlier_Manual,
                      Pemilihan_Titik_Sampel_Outlier_Kuartil,
                      Pengembalian_Titik_Sampel_Outlier_Ke_Titik_Zona,
                      Pemilihan_Zona_Parsial,
                      Rekomendasi_Klaster,
                      Perbaharui_Indeks_Sampel_Pada_Titik_Zona,
                      Penyesuaian_Nomor_Zona_Pembaruan,
                      Periksa_Kesesuaian_Titik_Dan_Zona_Pembaruan]


class Simbologi_Titik_Zona:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Simbologi Titik Zona"
        self.description = ""

    def getParameterInfo(self):
        """Define the tool parameters."""
        tz_output  =arcpy.Parameter(
            name="tz_output",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        penjelasan = arcpy.Parameter(
            displayName="Apa yang dilakukan tool ini?",
            name="penjelasan",
            datatype="GPString",
            parameterType="Optional",
        )

        penjelasan.value = (
            "Tool ini digunakan untuk menampilkan layer\n"
            "Titik Zona dengan simbologi yang sudah ditentukan.\n\n"
            "Direktorat Penilaian Tanah & Ekonomi Pertanahan\n"
            "Kementerian ATR/BPN\n"
            "Tahun: {}".format(datetime.datetime.now().year)
        )
        return [tz_output, penjelasan]

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
        zonalayer.delete_bad_file()
        config_dan_paths = zonalayer.get_config_values()

        tz_path = os.path.join(config_dan_paths['dataset_path'], "Titik_Zona")
        ui_folder = os.path.join(config_dan_paths['appdata'], "ui")
        symbology_folder = os.path.join(ui_folder, "symbology")
        tz_simbology_path = os.path.join(symbology_folder, "Titik_Zona.lyrx")


        arcpy.management.MakeFeatureLayer(tz_path, "Titik_Zona")
        arcpy.management.ApplySymbologyFromLayer("Titik_Zona", tz_simbology_path)

        arcpy.SetParameter(0, "Titik_Zona")
        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return

class Pemilihan_Titik_Sampel_Outlier_Manual:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Pemilihan Titik Sampel Outlier Manual"
        self.description = ""

    def getParameterInfo(self):
        """Define the tool parameters."""
        penjelasan = arcpy.Parameter(
            displayName="Apa yang dilakukan tool ini?",
            name="penjelasan",
            datatype="GPString",
            parameterType="Optional",
        )

        penjelasan.value = (
            "Tool ini digunakan untuk memindahkan titik zona yang\n"
            "Sudah dipilih pada layer Titik Zona ke layer Titik Sampel.\n\n"
            "Direktorat Penilaian Tanah & Ekonomi Pertanahan\n"
            "Kementerian ATR/BPN\n"
            "Tahun: {}".format(datetime.datetime.now().year)
        )
        return [penjelasan]

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
        zonalayer.delete_bad_file()
        # Hardcoded layer names
        titik_zona = "Titik_Zona"
        titik_sampel = "Titik_Sampel"

        zonalayer.check_if_there_selected_field()

        # Get selection
        selected_ids = samplepoint.get_selected_oids(titik_zona)
        if len(selected_ids) <= 0:
            arcpy.AddError("Tidak ada titik yang dipilih di layer Titik_Zona.")
            sys.exit(1)

        # Step 1: Transfer selected features
        where_clause = f"OBJECTID IN ({','.join(map(str, selected_ids))})"
        temp_layer = arcpy.management.MakeFeatureLayer(titik_zona, "temp_selected", where_clause)[0]
        temp_copy = arcpy.management.CopyFeatures(temp_layer, "in_memory\\temp_copy_manual")[0]

        # Step 2: Insert only shared fields + geometry
        common_fields = samplepoint.get_common_fields(temp_copy, titik_sampel)
        insert_fields = common_fields + ["SHAPE@"]

        with arcpy.da.InsertCursor(titik_sampel, insert_fields) as icur:
            with arcpy.da.SearchCursor(temp_copy, insert_fields) as scur:
                for row in scur:
                    icur.insertRow(row)

        # Step 3: Delete moved features from Titik_Zona
        arcpy.management.DeleteFeatures(temp_layer)
        arcpy.AddMessage(f"Memindahkan {len(selected_ids)} titik dari Titik_Zona ke Titik_Sampel")

        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return

class Pemilihan_Titik_Sampel_Outlier_Kuartil:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Pemilihan Titik Sampel Outlier Kuartil"
        self.description = ""

    def getParameterInfo(self):
        """Define the tool parameters."""
        penjelasan = arcpy.Parameter(
            displayName="Apa yang dilakukan tool ini?",
            name="penjelasan",
            datatype="GPString",
            parameterType="Optional",
        )

        penjelasan.value = (
            "Tool ini digunakan untuk memindahkan titik zona yang\n"
            "Sudah dipilih pada layer Titik Zona ke layer Titik\n"
            "Sampel menggunakan metode Kuartil.\n\n"
            "Direktorat Penilaian Tanah & Ekonomi Pertanahan\n"
            "Kementerian ATR/BPN\n"
            "Tahun: {}".format(datetime.datetime.now().year)
        )
        return [penjelasan]

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
        zonalayer.delete_bad_file()
        self.config_dan_paths = zonalayer.get_config_values()
        dataset_path = self.config_dan_paths['dataset_path']
        titik_zona = "Titik_Zona"
        titik_sampel = "Titik_Sampel"
        titik_zona_path = os.path.join(dataset_path, titik_zona)
        titik_sampel_path = os.path.join(dataset_path, titik_sampel)

        # Fungsi ini menghitung Q1 (quartile 1), Q2 (median), dan Q3 (quartile 3) dari sekumpulan nilai
        def quartiles(values):
            values = sorted(values)  # Urutkan nilai secara ascending
            size = len(values)
            
            # Jika jumlah data kurang dari 4, tidak bisa menghitung quartile yang valid
            if size < 4:
                return None
            
            mid = size // 2  # Posisi tengah
            
            # Hitung Q2 (median)
            if size % 2 == 0:
                Q2 = (values[mid - 1] + values[mid]) / 2  # Rata-rata dua nilai tengah untuk data genap
            else:
                Q2 = values[mid]  # Nilai tengah langsung untuk data ganjil
            
            # Hitung Q1 (quartile bawah - median dari separuh data pertama)
            if mid % 2 == 0:
                Q1 = (values[mid // 2 - 1] + values[mid // 2]) / 2
            else:
                Q1 = values[mid // 2]
            
            # Hitung Q3 (quartile atas - median dari separuh data kedua)
            if (size - mid) % 2 == 0:
                Q3 = (values[(mid + size) // 2 - 1] + values[(mid + size) // 2]) / 2
            else:
                Q3 = values[(mid + size) // 2]
            
            return Q1, Q2, Q3


        # ======================
        # IDENTIFIKASI ZONA
        # ======================

        # Mengidentifikasi kombinasi zona unik berdasarkan field JNSZN
        zones_type = set()  # Menggunakan set untuk mendapatkan nilai unik
        with arcpy.da.SearchCursor(titik_zona_path, ["JNSZN"]) as cursor:
            for i, row in enumerate(cursor):
                if len(row) > 0:
                    zones_type.add(row[0])
                else:
                    arcpy.AddMessage("Baris kosong terdeteksi")
        arcpy.AddMessage(f"Mengidentifikasi jenis zona unik berdasarkan field JNSZN...{zones_type}")

        # ======================
        # PROCESS KUARTIL
        # ======================

        # Proses setiap jenis zona secara terpisah
        for jenis_zona in zones_type:
            # Buat query untuk memfilter data berdasarkan zona
            where = f"JNSZN = {jenis_zona}"

            # Ambil semua nilai indeks_sampel untuk zona ini
            values = [r[0] for r in arcpy.da.SearchCursor(titik_zona_path, ["indeks_sampel"], where_clause=where)]
            # jika pada jenis zona kurang dari 4 data  maka di skip (tidak cukup untuk analisis quartile)
            if len(values) < 4:
                arcpy.AddMessage(f"Jenis zona {jenis_zona} dilewati: hanya terdapat ({len(values)} data, kurang dari minimal 4)")
                continue

            # Hitung nilai quartile untuk zona ini
            Q1, Q2, Q3 = quartiles(values)
            arcpy.AddMessage(f"Jenis Zona ({jenis_zona}) : Q1={Q1:.2f}, Q2={Q2:.2f}, Q3={Q3:.2f}")
            jangkauan_kuartil = Q3-Q1

            batas_bawah = Q1 - (1.5*jangkauan_kuartil)
            batas_atas = Q3 + (1.5*jangkauan_kuartil)
            arcpy.AddMessage(f"Jenis Zona ({jenis_zona}) : Batas Bawah={batas_bawah:.2f}, Batas Atas={batas_atas:.2f}")

            

            # Buat query untuk mengidentifikasi outlier: nilai di bawah Q1 atau di atas Q3
            outlier_query = f"JNSZN = {jenis_zona} AND (indeks_sampel < {batas_bawah} OR indeks_sampel > {batas_atas})"

            # Buat feature layer sementara berisi data outlier
            sel_layer = arcpy.management.MakeFeatureLayer(titik_zona, "temp_quartile", outlier_query)[0]
            
            # Copy data outlier ke in_memory workspace untuk processing
            temp_copy = arcpy.management.CopyFeatures(sel_layer, "in_memory\\temp_copy_quartile")[0]

            # Dapatkan field yang common antara source dan target
            common_fields = samplepoint.get_common_fields(temp_copy, titik_sampel_path)
            insert_fields = common_fields + ["SHAPE@"]  # Tambahkan geometry field

            # Transfer data outlier dari Titik_Zona ke titik_sampel
            with arcpy.da.InsertCursor(titik_sampel_path, insert_fields) as icur:
                with arcpy.da.SearchCursor(temp_copy, insert_fields) as scur:
                    for row in scur:
                        icur.insertRow(row)  # Insert setiap baris outlier ke titik_sampel

            # Hapus data outlier dari Titik_Zona (karena sudah dipindahkan ke titik_sampel)
            arcpy.management.DeleteFeatures(sel_layer)
            
            # Cleanup: hapus temporary layer
            arcpy.management.Delete("in_memory\\temp_copy_quartile")

        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return

class Pengembalian_Titik_Sampel_Outlier_Ke_Titik_Zona:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Pengembalian Titik Sampel Outlier Ke Titik Zona"
        self.description = ""

    def getParameterInfo(self):
        """Define the tool parameters."""
        tz_output  =arcpy.Parameter(
            name="tz_output",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )
        ts_output  =arcpy.Parameter(
            name="ts_output",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        penjelasan = arcpy.Parameter(
            displayName="Apa yang dilakukan tool ini?",
            name="penjelasan",
            datatype="GPString",
            parameterType="Optional",
        )

        penjelasan.value = (
            "Tool ini  digunakan untuk memindahkan titik sampel outlier\n"
            "dari layer Titik Sampel ke layer Titik Zona.\n\n"
            "Direktorat Penilaian Tanah & Ekonomi Pertanahan\n"
            "Kementerian ATR/BPN\n"
            "Tahun: {}".format(datetime.datetime.now().year)
        )
        return [tz_output, ts_output, penjelasan]

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
        zonalayer.delete_bad_file()
        config_dan_paths = zonalayer.get_config_values()
        dataset_path = config_dan_paths['dataset_path']
        zl = os.path.join(dataset_path, "Zona_Layer")      # Layer zona
        ts = os.path.join(dataset_path, "Titik_Sampel")
        tz = os.path.join(dataset_path, "Titik_Zona")      # Layer sumber
        tzt = "in_memory\\Titik_Zona_Temp" # Layer tujuan sementara

        # MAIN
        outlier_selected = samplepoint.get_selected_oids('Titik_Sampel')
        zona_selected = samplepoint.get_selected_oids('Titik_Zona')

        if  zona_selected:
            arcpy.AddError("Hanya pilih titik di layer Titik Sampel")
            sys.exit(1)
        elif not outlier_selected and not zona_selected:
            arcpy.AddError("Tidak ada titik yang dipilih. Silakan pilih titik sampel (pencilan/outlier) di layer Titik Sampel.")
            sys.exit(1)

        if outlier_selected:
            if self.check_individual_data(ts, outlier_selected):
                arcpy.AddWarning("Data 'Individual' tidak dapat dipindahkan ke Titik Zona.")
                sys.exit()
            arcpy.AddMessage(f"Memindahkan {len(outlier_selected)} titik dari Titik_Sampel ke Titik_Zona...")
            self.transfer_features(ts, outlier_selected, tz, tzt, zl, dataset_path, config_dan_paths['appdata'])
            arcpy.AddMessage("Pemindahan fitur selesai. Nilai atribut bersama dipertahankan.")

        return

    def get_necessary_fields(self, tz, tzt, zl, dataset_path, feature_1):
        # Mendefinisikan path untuk feature classes yang akan digunakan

        # Buat feature class baru berdasarkan geometri sumber
        spatial_ref = arcpy.Describe(tz).spatialReference
        geometry_type = arcpy.Describe(tz).shapeType

        # Hapus jika sudah ada
        if arcpy.Exists(tzt):
            arcpy.management.Delete(tzt)

        # Buat feature class baru dengan geometri yang sama
        arcpy.management.CreateFeatureclass("in_memory", "Titik_Zona_Temp", geometry_type, spatial_reference=spatial_ref)
        arcpy.analysis.Identity(feature_1, zl, tzt)
        arcpy.management.AddField(tzt, "indeks_sampel", "DOUBLE")

        bulat1 = "100"
        bulat2 = "100"
        code_block = """def doSomething(nila,men,jeniszona,bulat1,bulat2):
                if jeniszona == 1:
                    return round(bulat1 * ( nila/men ),2)
                elif jeniszona == 2:
                    return round(bulat2 * ( nila/men ),2)"""

        arcpy.management.CalculateField(tzt, "indeks_sampel", "doSomething(int(!nilai!),float(!NILAIZN_LAMA!),!JNSZN!," + bulat1 + "," + bulat2 + ")", "PYTHON3", code_block)
        arcpy.management.Append(tzt, tz, "NO_TEST")
        arcpy.management.Delete(tzt)

    def transfer_features(self, source_layer, selected_ids, tz, tzt, zl, dataset_path, appdata):
        where_clause = f"OBJECTID IN ({','.join(map(str, selected_ids))})"
        temp_layer = arcpy.management.MakeFeatureLayer(source_layer, "temp_selected", where_clause)[0]
        temp_copy = arcpy.management.CopyFeatures(temp_layer, "in_memory\\Titik_Sampel")[0]

        self.get_necessary_fields(tz, tzt, zl, dataset_path, temp_copy)

        with arcpy.da.UpdateCursor(source_layer, ["OBJECTID"]) as ucur:
            for row in ucur:
                if row[0] in selected_ids:
                    ucur.deleteRow()

        arcpy.management.DeleteFeatures(temp_layer)
        arcpy.management.Delete("in_memory\\Titik_Sampel")

        ui_folder = os.path.join(appdata, "ui")
        symbology_folder = os.path.join(ui_folder, "symbology")
        tz_simbology_path = os.path.join(symbology_folder, "Titik_Zona.lyrx")
        ts_simbology_path = os.path.join(symbology_folder, "Titik_Sampel.lyrx")

        arcpy.management.MakeFeatureLayer(tz, "Titik_Zona")
        arcpy.management.ApplySymbologyFromLayer("Titik_Zona", tz_simbology_path)

        arcpy.management.MakeFeatureLayer(source_layer, "Titik_Sampel")
        arcpy.management.ApplySymbologyFromLayer("Titik_Sampel", ts_simbology_path)

        arcpy.SetParameter(0, "Titik_Zona")
        arcpy.SetParameter(1, "Titik_Sampel")

    def check_individual_data(self, source_layer, selected_ids):
        """Check if any selected features have 'Jenis_Data' as 'Individual'."""
        individual_found = False
        where_clause = f"OBJECTID IN ({','.join(map(str, selected_ids))})"
        with arcpy.da.SearchCursor(source_layer, ["Jenis_Data"], where_clause) as cursor:
            for row in cursor:
                if row[0] == "Individual":
                    individual_found = True
                    break
        return individual_found

class Pemilihan_Zona_Parsial:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Pemilihan Zona Parsial"
        self.description = ""

    def getParameterInfo(self):
        """Define the tool parameters."""

        cluster  =arcpy.Parameter(
            displayName="Nomor Klaster",
            name="cluster",
            datatype="GPLong",
            parameterType="Required",
            direction="Input"
        )

        penjelasan = arcpy.Parameter(
            displayName="Apa yang dilakukan tool ini?",
            name="penjelasan",
            datatype="GPString",
            parameterType="Optional",
        )

        penjelasan.value = (
            "Tool ini digunakan untuk memperbaharui nilai klaster\n"
            "pada zona terpilih.\n\n"
            "Direktorat Penilaian Tanah & Ekonomi Pertanahan\n"
            "Kementerian ATR/BPN\n"
            "Tahun: {}".format(datetime.datetime.now().year)
        )
        return [cluster, penjelasan]

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
        cluster_update = str(parameters[0].valueAsText)
        zonalayer.delete_bad_file()
        config_dan_paths = zonalayer.get_config_values()

        zl = "Zona_Layer"
        titik_zona = 'Titik_Zona'

        # Cek apakah ada seleksi
        ada_seleksi = len(arcpy.Describe(zl).FIDSet)

        if ada_seleksi <= 0:
            arcpy.AddError('Tidak terdapat feature yang dipilih')
            sys.exit(1)


        oid_field = arcpy.Describe(zl).OIDFieldName
        fid_list = arcpy.Describe(zl).FIDSet.split(';')

        # Buat klausa WHERE agar hanya fitur terpilih yang diupdate
        where_clause = f"{oid_field} IN ({','.join(fid_list)})"
        where_clause_titik_zona = f"FID_Zona_Layer IN ({','.join(fid_list)})"


        count = 0
        with arcpy.da.UpdateCursor(titik_zona, ["cluster", 'no_Sampel', 'OBJECTID'], where_clause_titik_zona) as cursor:
            for row in cursor:
                row[0] = cluster_update
                cursor.updateRow(row)
                count += 1
        if count == 0:
            arcpy.AddWarning('Tidak ada nilai cluster yang diperbarui. Pastikan terdapat titik zona yang terkait dengan zona terpilih.')
            sys.exit(1)
        with arcpy.da.UpdateCursor(zl, ['cluster'], where_clause) as cursor:
            for row in cursor:
                row[0] = cluster_update
                cursor.updateRow(row)

        arcpy.AddMessage(f"{count} titik berhasil diperbarui untuk zona terpilih ({len(fid_list)} zona).")
        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return

class Rekomendasi_Klaster(object):
    def __init__(self):
        self.label = "Rekomendasi Klaster"
        self.description = "Membentuk cluster dari titik dengan perubahan signifikan"
        self.canRunInBackground = False

    def getParameterInfo(self):
        params = []

        eps_pertanian = arcpy.Parameter(
            displayName="Jarak Klaster Pertanian (meter)",
            name="eps_pertanian",
            datatype="Double",
            parameterType="Required",
            direction="Input"
        )
        eps_pertanian.value = 500

        eps_non_pertanian = arcpy.Parameter(
            displayName="Jarak Klaster Non-Pertanian (meter)",
            name="eps_non_pertanian",
            datatype="Double",
            parameterType="Required",
            direction="Input"
        )
        eps_non_pertanian.value = 300

        min_points = arcpy.Parameter(
            displayName="Minimum Titik dalam Klaster",
            name="min_points",
            datatype="Long",
            parameterType="Required",
            direction="Input"
        )
        min_points.value = 3

        out_feature = arcpy.Parameter(
            name="out_feature",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        params.extend([eps_pertanian, eps_non_pertanian, min_points, out_feature])
        return params

    def execute(self, parameters, messages):
        zonalayer.delete_bad_file()
        eps_pertanian = float(parameters[0].value)
        eps_non_pertanian = float(parameters[1].value)
        min_pts = int(parameters[2].value)

        config_dan_paths = zonalayer.get_config_values()
        titik_zona = os.path.join(config_dan_paths['dataset_path'], "Titik_Zona")
        zona_layer = os.path.join(config_dan_paths['dataset_path'], "Zona_Layer")
        out_fc = os.path.join(config_dan_paths['dataset_path'], 'Rekomendasi_Klaster')
        field_indeks = "indeks_sampel"
        field_jnszn = "JNSZN"
        
        arcpy.env.overwriteOutput = True

        for required_field, feature_class in [(field_indeks, titik_zona), (field_jnszn, titik_zona), (field_jnszn, zona_layer)]:
            if required_field not in [field.name for field in arcpy.ListFields(feature_class)]:
                raise Exception(f"Field {required_field} tidak ditemukan pada {os.path.basename(feature_class)}")

        # Workspace sementara
        temp_gdb = arcpy.env.scratchGDB

        naik_layer = os.path.join(temp_gdb, "naik")
        turun_layer = os.path.join(temp_gdb, "turun")

        arcpy.AddMessage("Memfilter titik signifikan...")

        # Filter naik (>120)
        arcpy.analysis.Select(
            titik_zona,
            naik_layer,
            f"{field_indeks} > 120"
        )

        # Filter turun (<85)
        arcpy.analysis.Select(
            titik_zona,
            turun_layer,
            f"{field_indeks} < 85"
        )

        def ensure_field(feature_class, field_name, field_type, field_length=None):
            existing_fields = [field.name for field in arcpy.ListFields(feature_class)]
            if field_name in existing_fields:
                return

            if field_length:
                arcpy.management.AddField(feature_class, field_name, field_type, field_length=field_length)
            else:
                arcpy.management.AddField(feature_class, field_name, field_type)

        def process_cluster(input_layer, arah_perubahan, jenis_zona, label_zona, eps_distance):
            zoned_layer = os.path.join(temp_gdb, f"{arah_perubahan.lower()}_{jenis_zona}_titik")
            arcpy.analysis.Select(
                input_layer,
                zoned_layer,
                f"{field_jnszn} = {jenis_zona}"
            )

            if int(arcpy.management.GetCount(zoned_layer)[0]) == 0:
                arcpy.AddWarning(f"Tidak ada titik {arah_perubahan} untuk zona {label_zona}")
                return None

            buffer_fc = os.path.join(temp_gdb, f"buffer_{arah_perubahan.lower()}_{jenis_zona}")
            dissolve_fc = os.path.join(temp_gdb, f"dissolve_{arah_perubahan.lower()}_{jenis_zona}")
            cluster_fc = os.path.join(temp_gdb, f"cluster_{arah_perubahan.lower()}_{jenis_zona}")
            filtered_fc = os.path.join(temp_gdb, f"filtered_{arah_perubahan.lower()}_{jenis_zona}")

            arcpy.AddMessage(f"Clustering {arah_perubahan} untuk zona {label_zona} dengan jarak {eps_distance} meter...")

            # Buffer
            arcpy.analysis.Buffer(
                zoned_layer,
                buffer_fc,
                f"{eps_distance} Meters",
                dissolve_option="ALL"
            )

            # Multipart to singlepart (pisah cluster)
            arcpy.management.MultipartToSinglepart(buffer_fc, dissolve_fc)

            # Spatial Join (hitung statistik titik pada setiap buffer cluster)
            field_mappings = arcpy.FieldMappings()
            field_mappings.addTable(dissolve_fc)
            field_mappings.addTable(zoned_layer)

            field_map_index = field_mappings.findFieldMapIndex(field_indeks)
            if field_map_index == -1:
                raise Exception(f"Field indeks {field_indeks} tidak ditemukan pada layer input")

            field_map = field_mappings.getFieldMap(field_map_index)
            field_map.mergeRule = "Mean"
            output_field = field_map.outputField
            output_field.name = "AVG_INDEKS"
            output_field.aliasName = "AVG_INDEKS"
            field_map.outputField = output_field
            field_mappings.replaceFieldMap(field_map_index, field_map)

            arcpy.analysis.SpatialJoin(
                dissolve_fc,
                zoned_layer,
                cluster_fc,
                join_operation="JOIN_ONE_TO_ONE",
                field_mapping=field_mappings,
                match_option="INTERSECT"
            )

            arcpy.analysis.Select(
                cluster_fc,
                filtered_fc,
                f"Join_Count >= {min_pts}"
            )

            if int(arcpy.management.GetCount(filtered_fc)[0]) == 0:
                arcpy.AddWarning(f"Tidak ada cluster {arah_perubahan} untuk zona {label_zona} yang memenuhi minimum {min_pts} titik")
                return None

            ensure_field(filtered_fc, "jenis_cluster", "TEXT", field_length=20)
            ensure_field(filtered_fc, "JNSZN_CL", "SHORT")
            ensure_field(filtered_fc, "ZONA_TIPE", "TEXT", field_length=30)
            ensure_field(filtered_fc, "EPS_METER", "DOUBLE")
            ensure_field(filtered_fc, "cluster_rek", "TEXT", field_length=50)

            arcpy.management.CalculateField(filtered_fc, "jenis_cluster", f"'{arah_perubahan}'", "PYTHON3")
            arcpy.management.CalculateField(filtered_fc, "JNSZN_CL", str(jenis_zona), "PYTHON3")
            arcpy.management.CalculateField(filtered_fc, "ZONA_TIPE", f"'{label_zona}'", "PYTHON3")
            arcpy.management.CalculateField(filtered_fc, "EPS_METER", str(float(eps_distance)), "PYTHON3")

            cluster_prefix = "P" if jenis_zona == 2 else "NP"
            with arcpy.da.UpdateCursor(filtered_fc, ["cluster_rek"]) as cursor:
                nomor_cluster = 1
                for row in cursor:
                    row[0] = f"{cluster_prefix}_{arah_perubahan}_{nomor_cluster}"
                    cursor.updateRow(row)
                    nomor_cluster += 1

            return filtered_fc

        cluster_outputs = []
        zone_configs = [
            (1, "Non-Pertanian", eps_non_pertanian),
            (2, "Pertanian", eps_pertanian)
        ]

        for jenis_zona, label_zona, eps_distance in zone_configs:
            cluster_naik = process_cluster(naik_layer, "NAIK", jenis_zona, label_zona, eps_distance)
            if cluster_naik:
                cluster_outputs.append(cluster_naik)

            cluster_turun = process_cluster(turun_layer, "TURUN", jenis_zona, label_zona, eps_distance)
            if cluster_turun:
                cluster_outputs.append(cluster_turun)

        if len(cluster_outputs) == 0:
            raise Exception("Tidak ada cluster yang terbentuk")

        arcpy.AddMessage("Menggabungkan cluster hasil rekomendasi...")

        merged_cluster_fc = os.path.join(temp_gdb, "merged_cluster_rekomendasi")
        if len(cluster_outputs) == 1:
            arcpy.management.CopyFeatures(cluster_outputs[0], merged_cluster_fc)
        else:
            arcpy.management.Merge(cluster_outputs, merged_cluster_fc)

        zona_work = os.path.join(temp_gdb, "zona_layer_rekomendasi")
        arcpy.management.CopyFeatures(zona_layer, zona_work)

        ensure_field(zona_work, "ZONE_OID", "LONG")
        ensure_field(zona_work, "ZONE_AREA", "DOUBLE")

        arcpy.management.CalculateField(zona_work, "ZONE_OID", "!OBJECTID!", "PYTHON3")
        arcpy.management.CalculateGeometryAttributes(zona_work, [["ZONE_AREA", "AREA"]], area_unit="SQUARE_METERS")

        overlay_fc = os.path.join(temp_gdb, "overlay_cluster_zona")
        arcpy.analysis.Intersect([zona_work, merged_cluster_fc], overlay_fc, "ALL", output_type="INPUT")

        ensure_field(overlay_fc, "OVR_AREA", "DOUBLE")
        arcpy.management.CalculateGeometryAttributes(overlay_fc, [["OVR_AREA", "AREA"]], area_unit="SQUARE_METERS")

        rekomendasi_zona = {}
        fields_overlay = ["ZONE_OID", "ZONE_AREA", "OVR_AREA", field_jnszn, "JNSZN_CL", "cluster_rek", "jenis_cluster", "AVG_INDEKS", "EPS_METER"]

        with arcpy.da.SearchCursor(overlay_fc, fields_overlay) as cursor:
            for zone_oid, zone_area, overlap_area, jnszn_zona, jnszn_cluster, cluster_rek, jenis_cluster, avg_indeks, eps_meter in cursor:
                if zone_area in [None, 0] or jnszn_zona != jnszn_cluster:
                    continue

                overlap_ratio = float(overlap_area) / float(zone_area)
                if overlap_ratio <= 0.3:
                    continue

                existing = rekomendasi_zona.get(zone_oid)
                if existing is None or overlap_ratio > existing["overlap_ratio"]:
                    rekomendasi_zona[zone_oid] = {
                        "cluster": cluster_rek,
                        "jenis_cluster": jenis_cluster,
                        "avg_indeks": avg_indeks,
                        "eps_meter": eps_meter,
                        "overlap_ratio": overlap_ratio
                    }

        if len(rekomendasi_zona) == 0:
            raise Exception("Tidak ada zona yang tertimpa cluster lebih dari 30% luasnya")

        where_clause = f"ZONE_OID IN ({','.join(str(oid) for oid in sorted(rekomendasi_zona.keys()))})"
        zona_layer_lyr = arcpy.management.MakeFeatureLayer(zona_work, "zona_layer_rekomendasi_lyr", where_clause)[0]
        rekomendasi_fc = os.path.join(temp_gdb, "zona_rekomendasi_sebelum_dissolve")
        arcpy.management.CopyFeatures(zona_layer_lyr, rekomendasi_fc)

        ensure_field(rekomendasi_fc, "jenis_cluster", "TEXT", field_length=20)
        ensure_field(rekomendasi_fc, "AVG_INDEKS", "DOUBLE")
        ensure_field(rekomendasi_fc, "OVLP_PCT", "DOUBLE")
        ensure_field(rekomendasi_fc, "EPS_METER", "DOUBLE")
        ensure_field(rekomendasi_fc, "ZONE_OID_TXT", "TEXT", field_length=255)

        with arcpy.da.UpdateCursor(rekomendasi_fc, ["ZONE_OID", "ZONE_OID_TXT", "cluster", "jenis_cluster", "AVG_INDEKS", "OVLP_PCT", "EPS_METER"]) as cursor:
            for row in cursor:
                data_rekomendasi = rekomendasi_zona.get(row[0])
                if data_rekomendasi:
                    row[1] = str(row[0])
                    row[2] = data_rekomendasi["cluster"]
                    row[3] = data_rekomendasi["jenis_cluster"]
                    row[4] = round(data_rekomendasi["avg_indeks"], 2)
                    row[5] = round(data_rekomendasi["overlap_ratio"] * 100, 2)
                    row[6] = data_rekomendasi["eps_meter"]
                    cursor.updateRow(row)

        dissolve_stats = [
            ["ZONE_OID_TXT", "CONCATENATE"],
            ["jenis_cluster", "FIRST"],
            ["AVG_INDEKS", "FIRST"],
            ["OVLP_PCT", "MAX"],
            ["EPS_METER", "FIRST"]
        ]

        arcpy.management.Dissolve(
            rekomendasi_fc,
            out_fc,
            ["cluster"],
            dissolve_stats,
            multi_part="MULTI_PART"
        )

        if "CONCATENATE_ZONE_OID_TXT" in [field.name for field in arcpy.ListFields(out_fc)]:
            arcpy.management.AlterField(out_fc, "CONCATENATE_ZONE_OID_TXT", new_field_name="ZONE_OID", new_field_alias="ZONE_OID")

        rename_targets = {
            "FIRST_jenis_cluster": "jenis_cluster",
            "FIRST_AVG_INDEKS": "AVG_INDEKS",
            "MAX_OVLP_PCT": "OVLP_PCT",
            "FIRST_EPS_METER": "EPS_METER"
        }

        existing_out_fields = [field.name for field in arcpy.ListFields(out_fc)]
        for old_name, new_name in rename_targets.items():
            if old_name in existing_out_fields:
                arcpy.management.AlterField(out_fc, old_name, new_field_name=new_name, new_field_alias=new_name)

        arcpy.AddMessage(f"Selesai. {len(rekomendasi_zona)} zona direkomendasikan sebagai cluster.")
        arcpy.management.MakeFeatureLayer(out_fc, "Rekomendasi_Klaster")
        arcpy.management.ApplySymbologyFromLayer("Rekomendasi_Klaster", os.path.join(config_dan_paths['symbology_folder'], "Rekomendasi_Klaster.lyrx"))
        arcpy.SetParameter(3, "Rekomendasi_Klaster")

class Penyesuaian_Nomor_Zona_Pembaruan:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Penyesuaian Nomor Zona Pembaruan"
        self.description = ""

    def getParameterInfo(self):
        """Define the tool parameters."""
        penjelasan = arcpy.Parameter(
            displayName="Sesuaikan Nomor Zona Pembaruan",
            name="penjelasan",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )

        zona_layer_output = arcpy.Parameter(
            name="zona_layer_output",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )
        penjelasan.value = (
            "Tool ini digunakan untuk memvalidasi\n "
            "Field Nomor Zona (NOZN) pada layer zona.\n"
            "Tool memastikan NOZN tidak bernilai null\n"
            "dan tidak terduplikasi.\n\n"
            "Direktorat Penilaian Tanah & Ekonomi Pertanahan\n"
            "Kementerian ATR/BPN\n"
            "Tahun: {}".format(datetime.datetime.now().year)
        )

        return [penjelasan, zona_layer_output]

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
        zonalayer.delete_bad_file()
        config_dan_paths = zonalayer.get_config_values()
        dataset_path = config_dan_paths['dataset_path']
        symbology_folder = config_dan_paths['symbology_folder']
        zl_path = os.path.join(dataset_path, 'Zona_Layer')
        self.check_and_prepare_nomor_zona(zl_path)
        self.recodify_histzone(zl_path)

        zl_path = os.path.join(dataset_path, "Zona_Layer")
        sim_path = os.path.join(symbology_folder, "Simbologi_Jenis_Penggunaan_Pada_Zona.lyrx")
        arcpy.management.MakeFeatureLayer(zl_path, "Zona_Layer")
        arcpy.management.ApplySymbologyFromLayer("Zona_Layer", sim_path)
        arcpy.SetParameter(1, "Zona_Layer")
        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return

    def check_and_prepare_nomor_zona(self, layer):
        """
        Memastikan tidak ada nomor zona yang null atau terduplikat.
        Jika ada duplikasi, zona dengan luas (Luas_M2) terbesar mempertahankan nomor zonanya,
        yang lain di-null-kan kemudian diisi ulang dengan max(nozone) + 1.
        """
        nomorzone_field = 'NOZN'
        luas_field = 'Luas_M2'

        # Hitung ulang Luas_M2
        arcpy.management.CalculateGeometryAttributes(layer, [["Luas_M2", "AREA"]], area_unit="SQUARE_METERS")

        # Kumpulkan data zona: {nomorzone: [(FID, luas), ...]}
        zona_data = {}
        
        with arcpy.da.SearchCursor(layer, ['OID@', nomorzone_field, luas_field]) as cursor:
            for row in cursor:
                fid, nozone, luas = row
                if nozone is not None:
                    if nozone not in zona_data:
                        zona_data[nozone] = []
                    zona_data[nozone].append((fid, luas if luas is not None else 0))
        
        # Tentukan FID mana yang harus di-null-kan (duplikat dengan luas lebih kecil)
        fids_to_nullify = []
        
        for nozone, records in zona_data.items():
            if len(records) > 1:  # Ada duplikasi
                # Urutkan berdasarkan luas (descending), ambil yang terluas
                records_sorted = sorted(records, key=lambda x: x[1], reverse=True)
                # Semua kecuali yang luasnya terbesar akan di-null-kan
                for fid, luas in records_sorted[1:]:
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
                if row[0] is not None and int(row[0]) > max_nozone:
                    max_nozone = int(row[0])
        
        # Isi ulang nomor zona yang sudah ditandai dengan auto-increment
        current_nozone = max_nozone
        with arcpy.da.UpdateCursor(layer, [nomorzone_field]) as cursor:
            for row in cursor:
                if row[0] == -1:
                    current_nozone += 1
                    row[0] = current_nozone
                    cursor.updateRow(row)

    def recodify_histzone(self, zl_path):
        try:
            # Mendapatkan daftar field yang ada dalam layer
            field_names = [field.name for field in arcpy.ListFields(zl_path)]

            # Memeriksa apakah field HISTZONE sudah ada
            if "HISTZONE" not in field_names:
                """
                JIKA HISTZONE BELUM ADA:
                Membuat field HISTZONE baru dengan urutan nomor dan tipe zona
                """

                # Membuat field sementara untuk menyimpan tipe zona
                arcpy.AddField_management(zl_path, "temp", "STRING")

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
                arcpy.management.CalculateField(zl_path, "temp", expression, "PYTHON3", codeblock)
                
                # Menggabungkan NOZN dan temp menjadi HISTZONE (contoh: "1N", "2P")
                arcpy.management.CalculateField(zl_path, "HISTZONE", "str(!NOZN!) + !temp!", "PYTHON3")
                
                # Menghapus field sementara
                arcpy.management.DeleteField(zl_path, "temp")

            else:
                """
                JIKA HISTZONE SUDAH ADA:
                Memperbarui nilai HISTZONE dengan mempertahankan nilai historis
                """
                
                # Menyimpan nilai HISTZONE yang ada ke field sementara
                arcpy.management.AddField(zl_path, "temp1", "STRING")
                arcpy.management.CalculateField(zl_path, "temp1", "!HISTZONE!", "PYTHON3")


                # Membuat field sementara untuk nilai zona baru
                arcpy.management.AddField(zl_path, "temp2", "STRING")
                
                # Mengisi field temp2 dengan 'N' atau 'P' berdasarkan JNSZN
                expression = "abc(!JNSZN!)"
                codeblock = """def abc(JNSZN):
                    if JNSZN == 1:
                        return 'N' 
                    elif JNSZN == 2:
                        return 'P' 
                    else:
                        return ''  
                    """
                arcpy.management.CalculateField(zl_path, "temp2", expression, "PYTHON3", codeblock)
                
                # Membuat field sementara untuk gabungan NOZN + temp2
                arcpy.management.AddField(zl_path, "temp", "STRING")
                arcpy.management.CalculateField(zl_path, "temp", "str(!NOZN!) + !temp2!", "PYTHON3")
                
                # Membuat field sementara untuk hasil akhir
                arcpy.management.AddField(zl_path, "temp3", "STRING")
                """
                MEMPROSES LOGIKA HISTZONE:
                - Membandingkan nilai lama (temp1) dengan nilai baru (temp)
                - Menerapkan logika khusus untuk mempertahankan atau menggabungkan nilai
                """
                with arcpy.da.UpdateCursor(zl_path, ["temp1", "temp", "temp3"]) as rows:
                    for row in rows:
                        # Jika nilai lama pendek (<3 karakter)
                        if len(row[0]) < 3:
                            if row[0] == row[1]:  # Jika nilai lama sama dengan baru
                                row[2] = row[1]   # Gunakan nilai baru
                            elif row[0] != row[1]:  # Jika berbeda
                                row[2] = row[0] + row[1]  # Gabungkan lama + baru
                        
                        # Jika nilai lama panjang (=3 karakter)
                        else:
                            if row[0][-2:] == row[1][-2:]:  # Jika 2 karakter akhir sama
                                row[2] = row[0]  # Pertahankan nilai lama
                            elif row[0][-2:] != row[1][-2:]:  # Jika 2 karakter akhir berbeda
                                row[2] = row[0] + row[1]  # Gabungkan lama + baru
                        
                        rows.updateRow(row)
                del rows, row
                
                # Memindahkan hasil akhir ke field HISTZONE
                arcpy.management.CalculateField(zl_path, "HISTZONE", "!temp3!", "PYTHON3")
                
                # Membersihkan semua field sementara
                arcpy.management.DeleteField(zl_path, "temp2")
                arcpy.management.DeleteField(zl_path, "temp")
                arcpy.management.DeleteField(zl_path, "temp1")
                arcpy.management.DeleteField(zl_path, "temp3")
        except Exception as e:
            arcpy.AddWarning(f'Gagal memperbarui HISTZONE: {e}')   

class Perbaharui_Indeks_Sampel_Pada_Titik_Zona:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Perbaharui Indeks Sampel Pada Titik Zona"
        self.description = ""

    def getParameterInfo(self):
        """Define the tool parameters."""

        penjelasan = arcpy.Parameter(
            displayName="Apa yang dilakukan tool ini?",
            name="penjelasan",
            datatype="GPString",
            parameterType="Optional",
        )

        penjelasan.value = (
            "Tool ini digunakan untuk memperbarui indeks sampel\n"
            "pada Titik Zona.\n\n"
            "Direktorat Penilaian Tanah & Ekonomi Pertanahan\n"
            "Kementerian ATR/BPN\n"
            "Tahun: {}".format(datetime.datetime.now().year)
        )
        return [penjelasan]

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
        config_dan_paths = zonalayer.get_config_values()

        bulat1 = "100"  # Faktor pembulatan untuk jenis zona 1
        bulat2 = "100"  # Faktor pembulatan untuk jenis zona 2
        # Mendefinisikan path untuk feature classes yang akan digunakan
        zl = os.path.join(config_dan_paths['dataset_path'], "Zona_Layer")      # Layer zona
        # Titik Zona
        hi = "in_memory\\HitungIndeksZona"    # Output hitung indeks

        tz = os.path.join(config_dan_paths['dataset_path'], "Titik_Zona")      # Layer sumber
        tzt = "in_memory\\Titik_Zona_Temp" # Layer tujuan

        spatial_ref = arcpy.Describe(tz).spatialReference
        geometry_type = arcpy.Describe(tz).shapeType


        if arcpy.Exists(tzt):
            arcpy.management.Delete(tzt)

        if arcpy.Exists(hi):
            arcpy.management.Delete(hi)

        arcpy.management.CreateFeatureclass("in_memory", "Titik_Zona_Temp", geometry_type, spatial_reference=spatial_ref)

        fields_to_copy = ["no_sampel", "nilai"]

        for field in fields_to_copy:
            arcpy.management.AddField(tzt, field, arcpy.ListFields(tz, field)[0].type)

        with arcpy.da.SearchCursor(tz, ["SHAPE@"] + fields_to_copy) as cursor_in:
            with arcpy.da.InsertCursor(tzt, ["SHAPE@"] + fields_to_copy) as cursor_out:
                for row in cursor_in:
                    cursor_out.insertRow(row)
        arcpy.analysis.Identity(tzt, zl, hi)
        arcpy.management.AddField(hi, "indeks_sampel", "DOUBLE")
        code_block = """def doSomething(nila,men,jeniszona,bulat1,bulat2):
        if jeniszona == 1:
            return round(bulat1 * ( nila/men ),2)  # Hitung indeks untuk zona jenis 1
        elif jeniszona == 2:
            return round(bulat2 * ( nila/men ),2)  # Hitung indeks untuk zona jenis 2"""
        arcpy.management.CalculateField(hi, "indeks_sampel", "doSomething(int(!nilai!),float(!NILAIZN_LAMA!),!JNSZN!," + bulat1 + "," + bulat2 + ")", "PYTHON3", code_block)
        fields_hi = {f.name for f in arcpy.ListFields(hi)}
        fields_tz = {f.name for f in arcpy.ListFields(tz)}
        common_fields = list((fields_hi & fields_tz) - {"OBJECTID", "Shape", "Shape_Length", "Shape_Area", "no_sampel"})
        for field_name in common_fields:
            if field_name not in [f.name for f in arcpy.ListFields(tz)]:
                arcpy.AddMessage(f"Field {field_name} tidak ada di Titik_Zona, menambahkannya...")
                field_template = arcpy.ListFields(hi, field_name)[0]
                arcpy.management.AddField(tz, field_name, field_template.type, field_template.precision, field_template.scale, field_template.length, field_template.aliasName, field_template.isNullable, field_template.required, field_template.domain)
        data_dict = {}
        cursor_fields_hi = ["no_sampel"] + common_fields
        with arcpy.da.SearchCursor(hi, cursor_fields_hi) as cursor:
            for row in cursor:
                nomor_entry = row[0]
                data_dict[nomor_entry] = row[1:]
            del cursor
        arcpy.AddMessage('Memperbarui Titik_Zona dengan data dari hasil Identity...')
        updated_rows = 0
        cursor_fields_tz = ["no_sampel"] + common_fields
        with arcpy.da.UpdateCursor(tz, cursor_fields_tz) as cursor:
            for row in cursor:
                nomor_entry = row[0]
                if nomor_entry in data_dict:
                    # Buat baris baru dengan nomor_entry dan data baru
                    new_row = [nomor_entry] + list(data_dict[nomor_entry])
                    cursor.updateRow(new_row)
                    updated_rows += 1
            del cursor
        arcpy.AddMessage(f'Selesai. {updated_rows} baris di Titik_Zona telah diperbarui.')

        arcpy.management.Delete(tzt)
        arcpy.management.Delete(hi)



        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return

class Periksa_Kesesuaian_Titik_Dan_Zona_Pembaruan:
    def __init__(self):
        self.label = "Periksa Kesesuaian Titik dan Zona Pembaruan"
        self.description = ""

    def getParameterInfo(self):
        penjelasan = arcpy.Parameter(
            displayName="Periksa Kesesuaian Titik dan Zona Pembaruan",
            name="penjelasan",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )

        import datetime
        penjelasan.value = (
            "CATATAN PENTING:\n"
            "Jalankan tool ini berulang hingga tidak ada peringatan.\n\n"

            "Tool ini digunakan untuk memeriksa kesesuaian antara\n"
            "Titik dan Zona Pembaruan sebelum perhitungan indeks \n"
            "nilai tanah.\n\n"

            "Validasi yang dilakukan:\n\n"

            "1. Tidak boleh ada perbedaan antara jenis zona \n"
            "   maupun klaster antara zona dan titik di dalam zona.\n\n"

            "2. Nilai pada field Nilai Tanah (m2) pada Titik Zona \n"
            "   dan Titik Sampel tidak boleh bernilai negatif.\n\n"

            "3. Setiap zona harus memiliki Nomor Zona yang unik\n"
            "   (tidak boleh duplikat).\n\n"

            "4. Satu zona tidak boleh memiliki sekaligus:\n"
            "   - Titik Zona\n"
            "   - Titik Sampel (Pencilan/Outlier)\n\n"

            "5. Zona yang menggunakan Titik Sampel (Outlier)\n"
            "   harus memiliki minimal 3 titik agar hasil\n"
            "   analisis lebih reliabel.\n\n"

            "6. Setiap klaster zona harus memiliki minimal\n"
            "   1 Titik Zona\n\n"


            "Direktorat Penilaian Tanah dan Ekonomi Pertanahan\n"
            "Kementerian ATR/BPN\n"
            f"Tahun: {datetime.datetime.now().year}"
        )
        return [penjelasan]

    def isLicensed(self):
        return True

    # ===============================
    # 🔧 UTIL
    # ===============================
    def _get_field_name(self, layer_path, expected):
        for f in arcpy.ListFields(layer_path):
            if f.name.lower() == expected.lower():
                return f.name
        return None

    def _validate_non_negative_nilai(self, layer_path, label):
        nilai_field = self._get_field_name(layer_path, "nilai")
        if not nilai_field:
            arcpy.AddWarning(f"Field 'nilai' tidak ditemukan pada {label}")
            sys.exit(0)


        invalid = []
        with arcpy.da.SearchCursor(layer_path, ["OID@", nilai_field]) as cur:
            for oid, nilai in cur:
                if nilai is not None and nilai < 0:
                    invalid.append((oid, nilai))

        if invalid:
            arcpy.AddWarning(f"{label} memiliki nilai tanah (m2) negatif")
            sys.exit(0)

    def _safe_delete(self, path):
        import time
        for _ in range(5):
            try:
                if arcpy.Exists(path):
                    arcpy.management.Delete(path)
                return
            except:
                time.sleep(1)
                arcpy.ClearWorkspaceCache_management()

    # ===============================
    # 🔥 MAIN EXECUTE
    # ===============================
    def execute(self, parameters, messages):
        import arcpy, os, sys, gc, time

        arcpy.env.overwriteOutput = True

        zonalayer.delete_bad_file()
        zonalayer.check_if_there_selected_field()
        config = zonalayer.get_config_values()

        dataset_path = config['dataset_path']
        zl_path = os.path.join(dataset_path, 'Zona_Layer')
        tz_path = os.path.join(dataset_path, 'Titik_Zona')
        ts_path = os.path.join(dataset_path, 'Titik_Sampel')

        # ===============================
        # VALIDASI SELECTION
        # ===============================
        if samplepoint.get_selected_oids('Titik_Zona'):
            arcpy.AddWarning("Matikan selection Titik Zona")
            sys.exit(0)

        if samplepoint.get_selected_oids('Titik_Sampel'):
            arcpy.AddWarning("Matikan selection Titik Sampel")
            sys.exit(0)

        perbedaan_zona = zonalayer.validate_kesesuaian_zona(config_dan_paths=zonalayer.get_config_values())
        if perbedaan_zona:
            arcpy.AddError(perbedaan_zona)
            return

        perbedaan_klaster = zonalayer.validasi_klaster_zona(config_dan_paths=zonalayer.get_config_values())
        if perbedaan_klaster:
            for err in perbedaan_klaster:
                arcpy.AddError(f'Terdapat error field klaster antara Titik dan Zona {err}')
            return
        
        # ===============================
        # VALIDASI NILAI
        # ===============================
        self._validate_non_negative_nilai(tz_path, 'Titik_Zona')
        self._validate_non_negative_nilai(ts_path, 'Titik_Sampel')
        arcpy.AddMessage("✅ Tidak ada nilai negatif pada Titik Zona dan Titik Sampel")

        # ===============================
        # VALIDASI NOZN
        # ===============================
        nozn_map = {}
        with arcpy.da.SearchCursor(zl_path, ["OBJECTID", "NOZN"]) as cur:
            for oid, nozn in cur:
                if nozn:
                    nozn_map.setdefault(str(nozn), []).append(oid)

        dup = [k for k, v in nozn_map.items() if len(v) > 1]
        if dup:
            arcpy.AddWarning(f"Terdapat Duplikasi NOZN:\n {dup}")
            sys.exit(0)

        arcpy.AddMessage("✅ Tidak ada duplikasi NOZN pada Zona Layer")

        # ===============================
        # 🔥 SPATIAL JOIN (IN MEMORY)
        # ===============================
        zout = "in_memory/zona_join"
        sout = "in_memory/sampel_join"

        arcpy.analysis.SpatialJoin(zl_path, tz_path, zout, 'JOIN_ONE_TO_MANY')
        arcpy.analysis.SpatialJoin(zl_path, ts_path, sout, 'JOIN_ONE_TO_MANY')

        # ===============================
        # CEK ZONA YANG PUNYA TITIK ZONA
        # ===============================
        ada_zona = set()
        with arcpy.da.SearchCursor(zout, ["Join_Count", "TARGET_FID"]) as cur:
            for jc, fid in cur:
                if jc > 0:
                    ada_zona.add(fid)

        # ===============================
        # CEK OUTLIER CAMPUR
        # ===============================
        zona_dict = {}
        with arcpy.da.SearchCursor(zl_path, ["OBJECTID", "NOZN"]) as cur:
            for oid, nozn in cur:
                zona_dict[oid] = nozn

        outlier_nozn = set()
        with arcpy.da.SearchCursor(sout, ["Join_Count", "TARGET_FID"]) as cur:
            for jc, fid in cur:
                if jc > 0 and fid in ada_zona:
                    nozn = zona_dict.get(fid)
                    if nozn:
                        outlier_nozn.add(nozn)

        if outlier_nozn:
            arcpy.AddWarning(f"Terdapat Zona yang memiliki Titik Zona dan Titik Sampel Sekaligus:\n {sorted(outlier_nozn)}")
            sys.exit(0)

        # ===============================
        # CEK OUTLIER MIN 3
        # ===============================
        zona_outlier = {}
        with arcpy.da.SearchCursor(sout, ["TARGET_FID", "Join_Count"]) as cur:
            for fid, jc in cur:
                if jc > 0 and fid not in ada_zona:
                    zona_outlier[fid] = zona_outlier.get(fid, 0) + jc

        invalid = []
        for fid, count in zona_outlier.items():
            if count < 3:
                invalid.append(f"{zona_dict.get(fid)} ({count})")

        if invalid:
            arcpy.AddWarning(f"Pada Zona Outlier ini titik sampel kurang dari batas minimum (3 buah):\n {invalid}")
            sys.exit(0)

        # ===============================
        # UPDATE CLUSTER
        # ===============================
        if zona_outlier:
            with arcpy.da.UpdateCursor(zl_path, ["OBJECTID", "cluster"]) as cur:
                for oid, cluster in cur:
                    if oid in zona_outlier:
                        cur.updateRow((oid, None))

        # ===============================
        # VALIDASI CLUSTER
        # ===============================
        clusters = {'1': {}, '2': {}}
        oid_jnszn = {}

        with arcpy.da.SearchCursor(zl_path, ["OBJECTID", "JNSZN"]) as cur:
            for oid, jnszn in cur:
                oid_jnszn[oid] = jnszn

        with arcpy.da.SearchCursor(zl_path, ["OBJECTID", "cluster", "JNSZN"]) as cur:
            for oid, cl, jnszn in cur:
                if cl is not None:
                    clusters[str(jnszn)].setdefault(cl, []).append(oid)

        invalid_cluster = []
        for jnszn, cluster_dict in clusters.items():
            for cl, oids in cluster_dict.items():
                if not any(oid in ada_zona for oid in oids):
                    invalid_cluster.append(f"{jnszn}-{cl}")

        if invalid_cluster:
            arcpy.AddWarning(f"Terdapat cluster yang tidak memiliki titik zona:\n {invalid_cluster}")
            sys.exit(0)

        arcpy.AddMessage("🎉 Semua validasi berhasil")

        # ===============================
        # CLEANUP
        # ===============================
        time.sleep(1)
        arcpy.management.ClearWorkspaceCache()
        gc.collect()

        self._safe_delete(zout)
        self._safe_delete(sout)