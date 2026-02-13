import arcpy, os
from penilaiantanahutils import zonalayer
# ======================
# ENVIRONMENT SETTINGS
# ======================
# Menonaktifkan output Z dan M values untuk optimisasi performa
arcpy.env.outputZFlag = "Disabled"  # Nonaktifkan nilai Z (elevasi)
arcpy.env.outputMFlag = "Disabled"  # Nonaktifkan nilai M (measure)
arcpy.env.overwriteOutput = True  # Mengizinkan overwrite output

class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Masukkan Data ZNT Sebelumnya"
        self.alias = "MasukkanDataZNTSebelumnya"

        # List of tool classes associated with this toolbox
        self.tools = [Masukkan_Data_ZNT_Sebelumnya]


class Masukkan_Data_ZNT_Sebelumnya:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Masukkan Data ZNT Sebelumnya"
        self.description = ""

    def getParameterInfo(self):
        """Define the tool parameters."""
                # 1. Input layer ZNT Lama
        znt_awal = arcpy.Parameter(
            displayName="Pilih Data ZNT",
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

        nomorzone.parameterDependencies = [znt_awal.name]

        nilai = arcpy.Parameter(
            displayName="Pilih Field Nilai",
            name="nilai_field",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        nilai.parameterDependencies = [znt_awal.name]

        jeniszona = arcpy.Parameter(
            displayName="Pilih Field Jenis Zona",
            name="jeniszona_field",
            datatype="Field",
            parameterType="Optional",
            direction="Input"
        )
        jeniszona.parameterDependencies = [znt_awal.name]


        return [znt_awal, nomorzone, nilai, jeniszona]
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
        znt_lama = parameters[0].valueAsText
        nomorzone = parameters[1].valueAsText
        nilai = parameters[2].valueAsText
        jeniszona = parameters[3].valueAsText if parameters[3].valueAsText else None

        dataset_path, tahun, provinsi, kota, coor, gdb_path = zonalayer.get_config_values()

        # --- Validasi: pastikan field nomorzone dan nilai tidak NULL dan bernilai numerik
        fields = [nomorzone, nilai, jeniszona] if jeniszona else [nomorzone, nilai]

        if not znt_lama:
            messages.addErrorMessage("Input ZNT belum ditentukan.")
            return

        try:
            with arcpy.da.SearchCursor(znt_lama, fields) as cursor:
                rownum = 0
                for row in cursor:
                    rownum += 1
                    for i, val in enumerate(row):
                        field_name = fields[i]
                        # Null atau empty string dianggap tidak valid
                        if val is None:
                            messages.addErrorMessage(f"Field '{field_name}' mengandung nilai NULL pada record {rownum}. Semua nilai harus terisi dan numeric atau dapat dikonversi ke angka.")
                            return
                        if isinstance(val, str):
                            s = val.strip()
                            if s == "":
                                messages.addErrorMessage(f"Field '{field_name}' mengandung string kosong pada record {rownum}.")
                                return
                            try:
                                float(s)
                            except Exception:
                                messages.addErrorMessage(f"Field '{field_name}' value '{s}' pada record {rownum} bukan angka dan tidak dapat dikonversi ke angka.")
                                return
                        elif isinstance(val, (int, float)):
                            # sudah numeric, lanjut
                            continue
                        else:
                            # coba konversi ke float sebagai upaya terakhir
                            try:
                                float(val)
                            except Exception:
                                messages.addErrorMessage(f"Field '{field_name}' value '{val}' pada record {rownum} bukan angka dan tidak dapat dikonversi ke angka.")
                                return
        except arcpy.ExecuteError:
            messages.addErrorMessage(f"Gagal membaca layer: {arcpy.GetMessages(2)}")
            return

        messages.addMessage("Validasi field nomor zona dan nilai: OK.")
        # --- Proses memasukkan data ZNT sebelumnya ke layer ZNT saat ini
        zona_layer_path = os.path.join(dataset_path, "Zona_Layer")
        zona_layer_temp_path = os.path.join(dataset_path, "Zona_Layer_Temp")
        # Hapus topology dan layer zona jika sudah ada
        topo = os.path.join(dataset_path, "Zona_Layer_Topology")
        if arcpy.Exists(topo):
            arcpy.management.Delete(topo)

        if arcpy.Exists(zona_layer_path):
            arcpy.management.Delete(zona_layer_path)

        if arcpy.Exists(zona_layer_temp_path):
            arcpy.management.Delete(zona_layer_temp_path)

        field_mappings = arcpy.FieldMappings()
        field_mappings.addTable(znt_lama)

        # Hapus field OBJECTID dari field mappings
        for field_map in field_mappings.fieldMappings:
            if field_map.outputField.name.upper() == "OBJECTID":
                field_mappings.removeFieldMap(field_mappings.findFieldMapIndex(field_map.outputField.name))

        # ======================
        # KONVERSI FITUR
        # ======================
        arcpy.conversion.FeatureClassToFeatureClass(
            znt_lama,
            dataset_path,
            "Zona_Layer_Temp",
            field_mapping=field_mappings
        )

        # ======================
        # FIELD CALCULATIONS
        # ======================

        """
        Simpan data lama dahulu
        """

        old_value_fields = [{'name': "NILAIZN_LAMA", 'data_type': "LONG"},
                        {'name': "NILBULAT_LAMA", 'data_type': "TEXT"}]
        input_features_fields = [f.name for f in arcpy.ListFields(znt_lama)]

        for field in old_value_fields:
            if field['name'] in input_features_fields:
                arcpy.management.CalculateField(zona_layer_temp_path, field['name'], "None", "PYTHON3") 
            else:
                arcpy.management.AddField(zona_layer_temp_path, field['name'], field['data_type'])

        # Fungsi untuk pembulatan nilai zona
        code_block = """def get(a):
            if a:
                return round(a) 
            else:
                return a  # Pertahankan nilai null"""

        # Fungsi untuk format nilai mata uang dengan pembulatan
        code_block2 = """def get(a, b):
            if a:
                # Bulatkan nilai berdasarkan parameter, format ke Rupiah
                valu = round((int(a)/int(b)), 0)*int(b)
                return 'Rp. ' + (f'{int(float(valu)):,}').replace(',', '.')  # Format dengan titik sebagai pemisah ribuan
            else:
                return a  # Pertahankan nilai null"""
        
        kode_jenis_zona = """def get_jenis_zona(a):
            if a == 1:
                return 'Non-Pertanian'
            elif a == 2:
                return 'Pertanian'"""

        # Perhitungan field untuk berbagai kolom:
        arcpy.management.CalculateField(zona_layer_temp_path, "NILAIZN_LAMA", f"get(!{nilai}!)", "PYTHON3", code_block)  # Salin nilai asli
        arcpy.management.CalculateField(zona_layer_temp_path, "NILBULAT_LAMA", f"get(!{nilai}!, '1000')", "PYTHON3", code_block2)  # Salin nilai bulat
        arcpy.management.DeleteField(zona_layer_temp_path, nilai)  # Hapus field nilai asli jika berbeda
        
        arcpy.management.AddField(zona_layer_temp_path, "NOZN", "LONG")
        arcpy.management.CalculateField(zona_layer_temp_path, 'NOZN', f"int(!{nomorzone}!)", "PYTHON3")
        arcpy.management.DeleteField(zona_layer_temp_path, nomorzone)  # Hapus field nomorzone asli jika berbeda

        if jeniszona:
            if jeniszona != "JNSZN":
                arcpy.management.AddField(zona_layer_temp_path, "JNSZN", "SHORT")
                arcpy.management.CalculateField(zona_layer_temp_path, 'JNSZN', f"!{jeniszona}!", "PYTHON3")
                arcpy.management.CalculateField(zona_layer_temp_path, 'PENGGUNAAN', f"get_jenis_zona(!{jeniszona}!)", "PYTHON3", kode_jenis_zona)
                arcpy.management.DeleteField(zona_layer_temp_path, jeniszona)
        else:
                arcpy.management.AddField(zona_layer_temp_path, "JNSZN", "SHORT")
                arcpy.management.CalculateField(zona_layer_temp_path, "JNSZN", "1", "PYTHON3")  # Set default ke 1
                arcpy.management.AddField(zona_layer_temp_path, "PENGGUNAAN", "TEXT")
                arcpy.management.CalculateField(zona_layer_temp_path, "PENGGUNAAN", "'Non-Pertanian'", "PYTHON3")  # Set default

        self.check_and_prepare_nomor_zona(zona_layer_temp_path)

        # --- Hapus field yang tidak diinginkan ---
        all_fields = [f.name for f in arcpy.ListFields(zona_layer_temp_path)]
        
        # Dapatkan nama field geometri dan ObjectID
        desc = arcpy.Describe(zona_layer_temp_path)
        shape_field_name = desc.shapeFieldName
        oid_field_name = desc.OIDFieldName

        # Field yang ingin dipertahankan
        desired_fields = ["NOZN", "NILAIZN", "JNSZN", "PENGGUNAAN", "NILAIZN_LAMA", "NILBULAT", "NILBULAT_LAMA", "HISTZONE", shape_field_name, oid_field_name]
        
        # Tambahkan field yang diperlukan sistem (seperti Shape_Length, Shape_Area) ke daftar yang dipertahankan
        for field in desc.fields:
            if not field.editable:
                if field.name not in desired_fields:
                    desired_fields.append(field.name)

        fields_to_delete = [f for f in all_fields if f not in desired_fields]

        if fields_to_delete:
            arcpy.management.DeleteField(zona_layer_temp_path, fields_to_delete)

        required_fields = [
                            {'name': "SMPBKREL", 'data_type': "DOUBLE"},
                            {'name': "SMPBAKU", 'data_type': "DOUBLE"},
                            {'name': "NILAIZN", 'data_type': "LONG"},
                            {'name': "JMLSMPL", 'data_type': "SHORT"},
                            {'name': "NILBULAT", 'data_type': "TEXT"},
                            {'name': "NILMIN", 'data_type': "LONG"},
                            {'name': "NILMAKS", 'data_type': "LONG"},
                            {'name': "cluster", 'data_type': "TEXT"},
                            {'name': "WADMKK", 'data_type': "TEXT"},
                            {'name':"WADMPR", 'data_type': "TEXT"},
                            {'name': "THNNILAI", 'data_type': "SHORT"}]

        for field in required_fields:
            if field['name'] in input_features_fields:
                arcpy.management.CalculateField(zona_layer_temp_path, field['name'], "None", "PYTHON3") 
            else:
                arcpy.management.AddField(zona_layer_temp_path, field['name'], field['data_type'])

        # Set nilai default
        arcpy.management.CalculateField(zona_layer_temp_path, "WADMKK", "'"+str(kota)+"'", "PYTHON3")  # Set kode kabupaten/kota
        arcpy.management.CalculateField(zona_layer_temp_path, "WADMPR", "'"+str(provinsi)+"'", "PYTHON3")  # Set kode provinsi
        arcpy.management.CalculateField(zona_layer_temp_path, "THNNILAI", tahun, "PYTHON3")  # Set tahun nilai
        arcpy.management.CalculateField(zona_layer_temp_path, "cluster", "1", "PYTHON3")  # Set cluster default

        zona_layer_fields = [f.name for f in arcpy.ListFields(zona_layer_temp_path)]
        # Tambah field JNSZN (jenis zona) jika belum ada

        if "HISTZONE" not in zona_layer_fields:
            """
            JIKA HISTZONE BELUM ADA:
            Membuat field HISTZONE baru dengan urutan nomor dan tipe zona
            """
            

            # Membuat field sementara untuk menyimpan tipe zona
            arcpy.management.AddField(zona_layer_temp_path, "temp", "STRING")

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
            arcpy.management.CalculateField(zona_layer_temp_path, "temp", expression, "PYTHON3", codeblock)
            
            # Menggabungkan NOZN dan temp menjadi HISTZONE (contoh: "1N", "2P")
            arcpy.management.CalculateField(zona_layer_temp_path, "HISTZONE", "str(!NOZN!) + !temp!", "PYTHON3")
            
            # Menghapus field sementara
            arcpy.management.DeleteField(zona_layer_temp_path, "temp")

        # Update penggunaan lahan berdasarkan jenis zona
        with arcpy.da.UpdateCursor(zona_layer_temp_path, ["JNSZN", "PENGGUNAAN"]) as rows:
            for row in rows:
                if row[0] == 1:  # Jika jenis zona = 1
                    row[1] = "Non-Pertanian"
                elif row[0] == 2:  # Jika jenis zona = 2
                    row[1] = "Pertanian"
                rows.updateRow(row)  # Update record
        del row, rows  # Bersihkan cursor

        zona_layer_lyr = "zona_layer_lyr_tmp"
        arcpy.management.MakeFeatureLayer(zona_layer_temp_path, zona_layer_lyr)
        
        existing_fields = [f.name for f in arcpy.ListFields(zona_layer_lyr)]
        ordered_fields = [
            "NOZN",
            "cluster",
            "WADMKK",
            "WADMPR",
            "JNSZN",
            "PENGGUNAAN",
            "HISTZONE",
            "SMPBKREL",
            "SMPBAKU",
            "NILAIZN",
            "JMLSMPL",
            "NILMIN",
            "NILMAKS",
            "NILBULAT",
            "THNNILAI",
            "NILAIZN_LAMA",
            "NILBULAT_LAMA",
        ]

        fms = arcpy.FieldMappings()

        for fld in ordered_fields:
            if fld not in existing_fields:
                arcpy.AddWarning(f"Field '{fld}' tidak ditemukan, dilewati")
                continue

            fm = arcpy.FieldMap()
            fm.addInputField(zona_layer_lyr, fld)
            fms.addFieldMap(fm)

        arcpy.conversion.FeatureClassToFeatureClass(
            zona_layer_temp_path,
            dataset_path,
            'Zona_Layer',
            field_mapping=fms
        )

        arcpy.management.Delete(zona_layer_temp_path)  # Hapus layer sementara      

        # BUG ERROR (Arcgis 3.6): Baca Lebih rinci di : https://www.notion.so/ZNT-002-2e42170c49e3807c9119ef76beb74a46?source=copy_link

        if arcpy.Exists(zona_layer_path):
            p = arcpy.mp.ArcGISProject("CURRENT")
            m = p.activeMap
            
            # Tambahkan layer yang baru diproses
            m.addDataFromPath(zona_layer_path)
        
        # End Of Bug 

        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""

        return
    
    def check_and_prepare_nomor_zona(self, layer):
        """
        Memastikan tidak ada nomor zona yang null atau terduplikat.
        Jika ada duplikasi, zona dengan nilai tertinggi mempertahankan nomor zonanya,
        yang lain di-null-kan kemudian diisi ulang dengan max(nozone) + 1.
        """
        nomorzone_field = 'NOZN'
        nilai_field = 'NILAIZN_LAMA'

        # Kumpulkan data zona: {nomorzone: [(FID, nilai), ...]}
        zona_data = {}
        max_nozone = 0
        with arcpy.da.SearchCursor(layer, ['OID@', nomorzone_field, nilai_field]) as cursor:
            for row in cursor:
                fid, nozone, nilai = row
                if nozone is not None:
                    if nozone > max_nozone:
                        max_nozone = nozone
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
        
        # Isi ulang nomor zona yang sudah ditandai dengan auto-increment
        current_nozone = max_nozone
        with arcpy.da.UpdateCursor(layer, [nomorzone_field]) as cursor:
            for row in cursor:
                if row[0] == -1:
                    current_nozone += 1
                    row[0] = current_nozone
                    cursor.updateRow(row)
        
        

