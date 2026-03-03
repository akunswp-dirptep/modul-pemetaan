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
                arcpy.CalculateField_management(zl_path, "HISTZONE", "!temp3!", "PYTHON3")
                
                # Membersihkan semua field sementara
                arcpy.DeleteField_management(zl_path, "temp2")
                arcpy.DeleteField_management(zl_path, "temp")
                arcpy.DeleteField_management(zl_path, "temp1")
                arcpy.DeleteField_management(zl_path, "temp3")
        except Exception as e:
            arcpy.AddWarning(f'Gagal memperbarui HISTZONE: {e}')   

class Periksa_Kesesuaian_Titik_Dan_Zona_Pembaruan:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Periksa Kesesuaian Titik dan Zona Pembaruan"
        self.description = ""

    def getParameterInfo(self):
        """Define the tool parameters."""
        penjelasan = arcpy.Parameter(
            displayName="Periksa Kesesuaian Titik dan Zona Pembaruan",
            name="penjelasan",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )

        penjelasan.value = (
            "!-!-! CATATAN PENTING !-!-!\n" 
            "Gunakan tool ini hingga tidak ditemukan peringatan lagi\n"
            "Tool ini berfungsi melakukan pemeriksaan kesesuaian\n"
            "antara Titik dan Zona Pembaruan\n\n"
            "Dilakukan beberapa validasi sebelum melakukan\n"
            "perhitungan indeks nilai tanah:\n\n"
            "1. Memastikan setiap zona memiliki Nomor Zona \n"
            "yang unik dan tidak terduplikasi sebagai dasar \n"
            "konsistensi identitas zona.\n\n"
            "2.Mengidentifikasi dan mencegah kondisi di mana \n"
            "satu zona secara bersamaan berisi Titik Zona dan \n"
            "Titik Sampel (Pencilan/Outlier) yang dapat memengaruhi keakuratan \n"
            "analisis.\n\n"
            "3. Memastikan setiap zona yang diklasifikasikan \n"
            "berdasarkan Titik Sampel (Pencilan/Outlier) memiliki jumlah sampel\n"
            "minimal tiga titik untuk menjamin reliabilitas\n"
            "hasil analisis.\n\n"
            "4. Memastikan setiap klaster zona memiliki\n"
            "setidaknya satu Titik Zona untuk menjaga\n"
            "integritas klaster."
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
        config_dan_paths= zonalayer.get_config_values()
        zonalayer.check_if_there_selected_field()
        dataset_path = config_dan_paths['dataset_path']
        zl_path = os.path.join(dataset_path, 'Zona_Layer')
       
        tz_selected_ids = samplepoint.get_selected_oids('Titik_Zona')
        if len(tz_selected_ids) > 0:
            arcpy.AddWarning("Matikan terlebih dahulu fitur editing pada layer Titik Zona sebelum menjalankan validasi ini.")
            sys.exit(1)
        
        ts_selected_ids = samplepoint.get_selected_oids('Titik_Sampel')
        if len(ts_selected_ids) > 0:
            arcpy.AddWarning("Matikan terlebih dahulu fitur editing pada layer Titik Sampel sebelum menjalankan validasi ini.")
            sys.exit(1)
        # ----- Validasi: NOZN unik di Zona_Layer -----
        try:
            if arcpy.Exists(zl_path):
                nozn_map = {}
                with arcpy.da.SearchCursor(zl_path, ["OBJECTID", "NOZN"]) as sc:
                    for oid, nozn in sc:
                        if nozn is None:
                            continue
                        key = str(nozn).strip()
                        if key == "":
                            continue
                        nozn_map.setdefault(key, []).append(oid)

                dup_keys = [k for k, v in nozn_map.items() if len(v) > 1]
                if dup_keys:
                    dup_info = {k: nozn_map[k] for k in dup_keys}
                    arcpy.AddWarning(f'Duplikasi NOZN terdeteksi di Zona_Layer: {dup_info}')
                    raise Exception('Validasi NOZN gagal: ditemukan duplikasi nomor zona.')
                else:
                    arcpy.AddMessage('Validasi NOZN: tidak ada duplikat ditemukan.')
            else:
                arcpy.AddWarning('Layer Zona_Layer tidak ditemukan, melewati validasi NOZN.')
        except Exception as e:
            arcpy.AddWarning(f'{e}')

        try:
            # ----- Validasi: Titik Outlier dan Titik Zona -----
            tz_path = "Titik_Zona"
            to_path = "Titik_Sampel"
            zl_path = "Zona_Layer"
            zout_path = os.path.join(dataset_path, "Jenis_Zona")
            sout_path = os.path.join(dataset_path, "Jenis_Sampel")

            if arcpy.Exists(zout_path):
                arcpy.management.Delete(zout_path)
            if arcpy.Exists(sout_path):
                arcpy.management.Delete(sout_path)

            arcpy.analysis.SpatialJoin(zl_path, tz_path, zout_path, 'Join one to many')
            arcpy.analysis.SpatialJoin(zl_path, to_path, sout_path, 'Join one to many')

            AdaZona = []
            z_rows = arcpy.SearchCursor(zout_path)
            for z_row in z_rows:
                if z_row.getValue("Join_Count") > 0:
                    AdaZona.append(z_row.getValue("TARGET_FID"))

            AdaZona = list(dict.fromkeys(AdaZona))

            ### ----- cek jenis zona titik outlier -----
            outlier_point_is_exist = []
            s_rows = arcpy.SearchCursor(sout_path)
            for s_row in s_rows:
                if s_row.getValue("Join_Count") > 0:
                    if s_row.getValue("TARGET_FID") in AdaZona:
                        outlier_point_is_exist.append(s_row.getValue("TARGET_FID"))

            ### ----- message -----
            outlier_point_is_exist = list(dict.fromkeys(outlier_point_is_exist))

            zona_dict = {}

            with arcpy.da.SearchCursor(zl_path, ["OBJECTID", "NOZN"]) as cursor:
                for oid, nozn in cursor:
                    zona_dict[oid] = nozn

            AdaZona = set()

            with arcpy.da.SearchCursor(zout_path, ["Join_Count", "TARGET_FID"]) as cursor:
                for join_count, target_fid in cursor:
                    if join_count > 0:
                        AdaZona.add(target_fid)
            outlier_nozn = set()

            with arcpy.da.SearchCursor(sout_path, ["Join_Count", "TARGET_FID"]) as cursor:
                for join_count, target_fid in cursor:
                    if join_count > 0 and target_fid in AdaZona:
                        nozn = zona_dict.get(target_fid)
                        if nozn is not None:
                            outlier_nozn.add(nozn)

            
            arcpy.AddMessage(f"Zona dengan Titik Outlier: {outlier_nozn}")
            if outlier_nozn:
                daftar_zona = ", ".join(map(str, sorted(outlier_nozn)))
                arcpy.AddWarning(
                    f"Terdapat Titik Sampel (Pencilan/Outlier) dan Titik Zona di dalam satu zona pada NOZN: {daftar_zona}"
                )
                raise Exception("Validasi Titik Zona dan Outlier gagal.")

            else:
                arcpy.AddMessage("Tidak ada zona yang berisi titik zona dan titik sampel (outlier) bersamaan.")
                zona_hanya_outlier = {}

                with arcpy.da.SearchCursor(sout_path, ["TARGET_FID", "Join_Count"]) as s_cursor:
                    for target_fid, join_count in s_cursor:
                        if join_count > 0 and target_fid not in AdaZona:
                            if target_fid not in zona_hanya_outlier:
                                zona_hanya_outlier[target_fid] = join_count
                            else:
                                zona_hanya_outlier[target_fid] += join_count
                            

                arcpy.AddMessage(zona_hanya_outlier)
                zona_invalid = []
                for fid, count in zona_hanya_outlier.items():
                    if count < 3:
                        nozn = zona_dict.get(fid, "N/A")
                        zona_invalid.append(f"NOZN {nozn} (memiliki {count} titik)")

                if zona_invalid:
                    pesan_error = "Zona outlier berikut tidak memiliki 3 titik: " + ", ".join(zona_invalid)
                    arcpy.AddWarning(pesan_error)
                    raise Exception("Validasi Titik Zona dan Outlier gagal.")

                hanya_outlier_zona_fids = list(zona_hanya_outlier.keys())

                if len(hanya_outlier_zona_fids) > 0:
                    # Update kolom cluster jadi NULL pada zona yang hanya berisi outlier
                    with arcpy.da.UpdateCursor(zl_path, ["OBJECTID", "cluster"]) as cursor:
                        for oid, cluster_val in cursor:
                            if oid in hanya_outlier_zona_fids:
                                cursor.updateRow((oid, None))
                    arcpy.AddMessage(f"Kolom 'cluster' telah diset NULL untuk zona outlier berikut: {hanya_outlier_zona_fids}")
                else:
                    arcpy.AddMessage("Tidak ada zona outlier tunggal yang perlu diubah kolom 'cluster'-nya.")

            # ----- Validasi: Setiap cluster harus memiliki setidaknya satu titik zona -----
            
            clusters = {'1': {},
                        '2': {}}


            oid_jnszn_map = {}
            for oid, jnszn in arcpy.da.SearchCursor(zl_path, ["OBJECTID", "JNSZN"]):
                oid_jnszn_map[oid] = jnszn

            with arcpy.da.SearchCursor(zl_path, ["OBJECTID", "cluster", "JNSZN"]) as cursor:
                for oid, cluster_val, jnszn in cursor:
                    if cluster_val is not None:
                        if cluster_val not in clusters[str(jnszn)]:
                            clusters[str(jnszn)][cluster_val] = []
                        clusters[str(jnszn)][cluster_val].append(oid)

            invalid_clusters_info = []

            
        
            for jnszn, cluster_dict in clusters.items():
                for cluster_val, oids in cluster_dict.items():
                    has_point = any(oid in AdaZona for oid in oids)
                    if not has_point:
                        # Ambil JNSZN dari OID pertama di klaster (asumsi JNSZN sama dalam satu klaster)
                        first_oid = oids[0]
                        jnszn = oid_jnszn_map.get(first_oid, "N/A")
                        invalid_clusters_info.append(f"Jenis Zona {'Pertanian' if jnszn == 2 else 'Non-Pertanian'} - Cluster {cluster_val}\n")
            
            if invalid_clusters_info:
                pesan_error = f"Klaster berikut tidak memiliki Titik Zona:\n{''.join(invalid_clusters_info)}"
                arcpy.AddWarning(pesan_error)
                return
            else:
                arcpy.AddMessage("Validasi klaster: Setiap klaster memiliki setidaknya satu Titik Zona.")

        except Exception as e:
            arcpy.management.Delete(zout_path)
            arcpy.management.Delete(sout_path)
            arcpy.AddWarning(f'{e}')
        
        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return
