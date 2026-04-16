import arcpy, os,sys
from datetime import datetime
# Tambahkan parent directory ke sys.path
script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

arcpy.env.outputZFlag = "Disabled"
arcpy.env.outputMFlag = "Disabled"

arcpy.env.overwriteOutput = True
arcpy.env.addOutputsToMap = True

from zntutils import zona_layer as zonalayer


class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [Penyesuaian_Nomor_Zona_Pembuatan,
                      Hitung_Nilai_ZNT_Pembuatan]


class Penyesuaian_Nomor_Zona_Pembuatan:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Penyesuaian Nomor Zona Pembuatan"
        self.description = ""

    def getParameterInfo(self):
        """Define the tool parameters."""
        penjelasan = arcpy.Parameter(
            displayName="Sesuaikan Nomor Zona Pembuatan",
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
            "-----------------------------------------------\n"
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
            "dan pemetaan.\n"
            "\n"
            "Direktorat Penilaian Tanah & Ekonomi Pertanahan\n"
            "Kementerian ATR/BPN\n"
            "Tahun: {}".format(datetime.now().year))
        

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
        zl_path = os.path.join(dataset_path, "Zona_Layer")
        sim_path = os.path.join(symbology_folder, "Simbologi_Jenis_Penggunaan_Pada_Zona.lyrx")
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
        Jika ada duplikasi, zona dengan luas (Luas_M2) terbesar mempertahankan nomor zonanya.
        Zona lainnya akan dihapus Nomor Zonanya.
        Nomor Zona akan diisi ulang secara otomatis.
        Penomoran menggunakan nilai maksimum NOZN + 1.
        Proses ini menjamin setiap zona memiliki
        Nomor Zona yang unik dan konsisten.
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
        del cursor, row
        
        

class Hitung_Nilai_ZNT_Pembuatan:
    def __init__(self):

        self.label = "Hitung Nilai ZNT"
        self.description = "Tools untuk menghitung nilai ZNT Pembuatan"
    
    def getParameterInfo(self):
        pembulatan = arcpy.Parameter(
            displayName = "Pembulatan",
            name = "pembulatan",
            datatype = "GPLong",
            parameterType = "Required",
            direction = "Input"
        )

        ts_output = arcpy.Parameter(
            name = 'ts_output_layer',
            datatype = "GPFeatureLayer",
            parameterType = "Derived",
            direction = "Output"
        )

        zl_output = arcpy.Parameter(
            name = 'zl_output_layer',
            datatype = "GPFeatureLayer",
            parameterType = "Derived",
            direction = "Output"
        )

        pembulatan.value = 1_000

        return [pembulatan, ts_output, zl_output]

    def isLicensed(self):
        return True
    
    def updateParameters(self, parameters):
        return
    
    def execute(self, parameters, messages):
        user_input = parameters[0].valueAsText
        pembulatan = int(user_input)

        config_dan_paths = zonalayer.get_config_values()
        zl_path = config_dan_paths['zl_path']
        ws_dir = config_dan_paths['ws_dir']

        dataset_path = config_dan_paths['dataset_path']  # Path ke geodatabase
        tahun = config_dan_paths['tahun']  # Tahun penilaian
        lokasi = config_dan_paths['provinsi']   # Kode lokasi
        coor = config_dan_paths['coor']      # Sistem koordinat
        gdb_path = config_dan_paths['gdb_path']  # Path lengkap GDB
        identity_output = os.path.join(dataset_path, "IdentitySampel")
        titik_sampel = os.path.join(dataset_path, "Titik_Sampel")

        if not arcpy.Exists(titik_sampel):
            arcpy.AddError("Layer Titik Sampel tidak ditemukan")
        arcpy.analysis.Identity(titik_sampel, zl_path, identity_output)
        dissolve_output = os.path.join(dataset_path, "DissolveSampel")
        field_statistik = [
            ["nilai", "SUM"],
            ["nilai", "MEAN"],
            ["nilai", "MIN"],
            ["nilai", "MAX"],
            ["nilai", "STD"],
            ["nilai", "COUNT"],
            ["nilai", "RANGE"]
        ]

        arcpy.management.Dissolve(identity_output, dissolve_output, "FID_Zona_Layer", field_statistik)

        arcpy.management.JoinField(zl_path, "OBJECTID", dissolve_output, "FID_Zona_Layer",["SUM_nilai", "MEAN_nilai", "MIN_nilai", "MAX_nilai", "STD_nilai", "COUNT_nilai", "RANGE_nilai"])

        fields_to_round = {
            "MIN_nilai": "NILMIN",
            "MAX_nilai": "NILMAKS",
            "COUNT_nilai": "JMLSMPL",
            "MEAN_nilai": "NILAIZN",
            "STD_nilai": "SMPBAKU"
        }

        for input_field, output_field in fields_to_round.items():
            if output_field not in [f.name for f in arcpy.ListFields(zl_path)]:
                arcpy.management.AddField(zl_path, output_field, "DOUBLE")
            arcpy.management.CalculateField(
                zl_path,
                output_field,
                f"None if !{input_field}! is None else round(!{input_field}!)",
                "PYTHON3"
            )
        
        if "SMPBKREL" not in [f.name for f in arcpy.ListFields(zl_path)]:
            arcpy.management.AddField(zl_path, "SMPBKREL", "DOUBLE")
        arcpy.management.CalculateField(
            zl_path, "SMPBKREL",
            "(!SMPBAKU! / !NILAIZN!) * 100 if !NILAIZN! else None", "PYTHON3"
        )
        if "JMLNILAI" not in [f.name for f in arcpy.ListFields(zl_path)]:
            arcpy.management.AddField(zl_path, "JMLNILAI", "DOUBLE")
        arcpy.management.CalculateField(zl_path, "JMLNILAI", "!SUM_nilai!", "PYTHON3")
        arcpy.management.DeleteField(zl_path,
            ["SUM_nilai", "MEAN_nilai", "MIN_nilai", "MAX_nilai", "STD_nilai", "COUNT_nilai", "RANGE_nilai"]
        )

        if "NILBULAT" not in [f.name for f in arcpy.ListFields(zl_path)]:
            arcpy.management.AddField(zl_path, "NILBULAT", "TEXT", field_length=50)

        # Blok kode Python untuk fungsi pembulatan dan formatting
        code_block = f"""def doSomething(mean_val, pembulatan):
            if mean_val:
                # Membulatkan ke kelipatan terdekat dari nilai pembulatan
                rounded = round(mean_val / pembulatan) * pembulatan
                # Memformat nilai dengan separator ribuan
                return "Rp{{:,}}".format(int(rounded)).replace(",", ".")
            else:
                return ""
        """

        # Menghitung field NILBULAT dengan fungsi kustom
        arcpy.management.CalculateField(
            zl_path,
            "NILBULAT",
            f"doSomething(!NILAIZN!, {pembulatan})",
            "PYTHON3",
            code_block
        )

        arcpy.AddMessage("Memeriksa kualitas zona...")
        nilaizn_null_or_zero_zones = []
        less_than_3_samples_zones = []
        with arcpy.da.SearchCursor(zl_path, ["NOZN", "NILAIZN", "JMLSMPL"]) as cursor:
            for row in cursor:
                zone_id = row[0]
                nilaizn = row[1]
                jmlsmpl = row[2]
                
                if nilaizn is None or nilaizn == 0:
                    nilaizn_null_or_zero_zones.append(zone_id)
                if jmlsmpl is None or jmlsmpl < 3:
                    less_than_3_samples_zones.append((zone_id, jmlsmpl if jmlsmpl is not None else 0))

        if nilaizn_null_or_zero_zones:
            arcpy.AddWarning(f"Terdapat zona dengan NILAIZN 0 atau NULL: {', '.join(map(str, nilaizn_null_or_zero_zones))}")
        if less_than_3_samples_zones:
            lines = "\n".join(
                f"{zone_id} (Terdapat {int(jmlsmpl)} Titik Sampel)"
                for zone_id, jmlsmpl in less_than_3_samples_zones
            )

            arcpy.AddWarning(
                f"Terdapat zona dengan jumlah sampel kurang dari 3:\n{lines}"
            )
        if not nilaizn_null_or_zero_zones and not less_than_3_samples_zones:
            arcpy.AddMessage("Semua zona memenuhi kriteria kualitas data.")


        arcpy.management.Delete(dissolve_output)
        arcpy.management.Delete(identity_output)




    
