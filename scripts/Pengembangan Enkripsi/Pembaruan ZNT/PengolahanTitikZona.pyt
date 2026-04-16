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
        zonalayer.delete_bad_file()
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
            "field Nomor Zona (NOZN) pada layer zona.\n"
            "Tool memastikan NOZN tidak bernilai null\n"
            "dan tidak terduplikasi.\n"
            "--------------------------------------------------\n"
            "Jika ditemukan NOZN yang sama pada lebih\n"
            "dari satu zona, maka akan dilakukan seleksi.\n"
            "Zona dengan luas terbesar (Luas_M2)\n"
            "akan mempertahankan Nomor Zonanya.\n"
            "Zona lainnya akan dihapus Nomor Zonanya.\n"
            "Nomor Zona akan diisi ulang secara otomatis.\n"
            "Penomoran menggunakan nilai maksimum NOZN + 1.\n"
            "Proses ini menjamin setiap zona memiliki\n "
            "Nomor Zona yang unik dan konsisten.\n"
            "Hasil siap digunakan untuk analisis\n"
            "dan pemetaan."
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

            "1. Nilai pada field Nilai Tanah (m2) pada Titik Zona \n"
            "   dan Titik Sampel tidak boleh bernilai negatif.\n\n"

            "2. Setiap zona harus memiliki Nomor Zona yang unik\n"
            "   (tidak boleh duplikat).\n\n"

            "3. Satu zona tidak boleh memiliki sekaligus:\n"
            "   - Titik Zona\n"
            "   - Titik Sampel (Pencilan/Outlier)\n\n"

            "4. Zona yang menggunakan Titik Sampel (Outlier)\n"
            "   harus memiliki minimal 3 titik agar hasil\n"
            "   analisis lebih reliabel.\n\n"

            "5. Setiap klaster zona harus memiliki minimal\n"
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