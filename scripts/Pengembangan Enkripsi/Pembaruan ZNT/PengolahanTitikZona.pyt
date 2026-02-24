# -*- coding: utf-8 -*-

import arcpy, os,sys
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
                      Pemilihan_Titik_Sampel_Outlier_Kuartil]


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
            "Titik Zona dengan simbologi yang sudah ditentukan."
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
            "Tool ini digunakan untuk memindahkan titik  sampel (outlier) yang\n"
            "Sudah dipilih pada layer Titik Zona ke layer Titik Sampel."
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
        # Hardcoded layer names
        titik_zona = "Titik_Zona"
        titik_sampel = "Titik_Sampel"

        # Get selection
        selected_ids = samplepoint.get_selected_oids(titik_zona)
        if len(selected_ids) <= 0:
            arcpy.AddError("No features selected in Titik_Zona.")
            raise arcpy.ExecuteError

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
            "Tool ini digunakan untuk memindahkan titik  sampel (outlier) yang\n"
            "Sudah dipilih pada layer Titik Zona ke layer Titik Sampel menggunakan metode Kuartil."
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

