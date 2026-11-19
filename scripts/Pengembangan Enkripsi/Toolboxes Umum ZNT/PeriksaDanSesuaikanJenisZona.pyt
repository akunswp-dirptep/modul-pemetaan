import arcpy, os, sys
from datetime import datetime

arcpy.env.outputZFlag = "Disabled"
arcpy.env.outputMFlag = "Disabled"

script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
    
from zntutils.zona_layer import get_config_values, delete_bad_file, reorder_fields, delete_topology_file
from zntutils import sample_point as samplepoint

arcpy.env.outputZFlag = "Disabled"  
arcpy.env.outputMFlag = "Disabled"  

class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox Sesuaikan Jenis Zona"
        self.alias = "toolbox_sesuaikan_jenis_zona"

        # List of tool classes associated with this toolbox
        self.tools = [Periksa_Jenis_Zona,
                      Sesuaikan_Jenis_Zona,
                      Sesuaikan_Jenis_Zona_Lanjutan]

class Periksa_Jenis_Zona(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Periksa Jenis Zona"
        self.description = "Tool ini digunakan untuk memeriksa kesesuaian jenis zona antara Zona Layer dan Titik Sampel."

    def getParameterInfo(self):
        """Define the tool parameters."""
        penjelasan = arcpy.Parameter(
            displayName="Apa yang dilakukan tool ini?",
            name="penjelasan",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        penjelasan.value = (
            "Tool ini digunakan untuk memeriksa kesesuaian jenis zona\n"
            "antara Zona Layer dan Titik Sampel.\n"
            "\n"
            "Direktorat Penilaian Tanah & Ekonomi Pertanahan\n"
            "Kementerian ATR/BPN\n"
            "Tahun: {}".format(datetime.now().year))
        
        output_zl = arcpy.Parameter(
            name="output_zl",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        output_ts = arcpy.Parameter(
            name="output_ts",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )
        
        output_tz = arcpy.Parameter(
            name="output_tz",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [penjelasan, output_zl, output_ts, output_tz]

    def isLicensed(self):
        """Set whether the tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        self.config_dan_paths = get_config_values()
        workspace = self.config_dan_paths['gdb_path']
        
        ts_path = os.path.join(self.config_dan_paths['dataset_path'], "Titik_Sampel")
        tz_path = os.path.join(self.config_dan_paths['dataset_path'], "Titik_Zona")
        zl_path = os.path.join(self.config_dan_paths['dataset_path'], "Zona_Layer")
        sim_path = os.path.join(self.config_dan_paths['symbology_folder'], "Simbologi_Periksa_Jenis_Zona.lyrx")

        sim_ts_path = os.path.join(self.config_dan_paths['symbology_folder'], "Titik_Sampel.lyrx")
        sim_tz_path = os.path.join(self.config_dan_paths['symbology_folder'], "Titik_Zona.lyrx") 

        zl_topology_path = os.path.join(self.config_dan_paths['dataset_path'], "Zona_Layer_Topology")
        if arcpy.Exists(zl_topology_path):
            arcpy.management.Delete(zl_topology_path)

        identity_layers = []

        # Identity Titik Zona (jika ada)
        if arcpy.Exists(tz_path):
            arcpy.analysis.Identity(tz_path, zl_path, "identity_tz")
            identity_layers.append("identity_tz")

        # Identity Titik Sampel
        arcpy.analysis.Identity(ts_path, zl_path, "identity_ts")
        identity_layers.append("identity_ts")

        # Dictionary penyimpanan
        listzona = {}
        listsampel = {}
        jumlah_sampel = {}

        for identity_fc in identity_layers:
            with arcpy.da.Editor(workspace) as edit:
                with arcpy.da.SearchCursor(
                    identity_fc,
                    ["NOZN", "JNSZN", "Zoning"]
                ) as cursor:
                    for nozona, jenis, zoning in cursor:
                        if nozona is None or str(nozona).strip() == "":
                            continue

                        if nozona not in listzona:
                            listzona[nozona] = set()
                        if jenis is not None:
                            listzona[nozona].add(jenis)

                        if nozona not in listsampel:
                            listsampel[nozona] = set()
                        if zoning is not None:
                            listsampel[nozona].add(zoning)

                        # Hitung jumlah titik sampel per zona (hanya dari Titik_Sampel)
                        if identity_fc == "identity_ts":
                            jumlah_sampel[nozona] = jumlah_sampel.get(nozona, 0) + 1

        # Hapus field lama jika ada
        field_names = [f.name for f in arcpy.ListFields(zl_path)]
        field_names_upper = [f.upper() for f in field_names]

        if "JENISSAMPEL" in field_names_upper:
            arcpy.management.DeleteField(zl_path, "JENISSAMPEL")
        if "BEDA_ZONA" in field_names_upper:
            arcpy.management.DeleteField(zl_path, "BEDA_ZONA")

        # Tambah field baru
        arcpy.management.AddField(zl_path, "JENISSAMPEL", "TEXT", field_alias="JENIS SAMPEL")
        arcpy.management.AddField(zl_path, "BEDA_ZONA", "TEXT", field_alias="BEDA ZONA")
        if "JMLSMPL" not in field_names_upper:
            arcpy.management.AddField(zl_path, "JMLSMPL", "LONG", field_alias="JUMLAH SAMPEL")

        with arcpy.da.Editor(workspace) as edit:
            with arcpy.da.UpdateCursor(
                zl_path,
                ["NOZN", "BEDA_ZONA", "JENISSAMPEL", "JMLSMPL"]
            ) as cursor:
                for row in cursor:
                    nozona = row[0]
                    zl_type = set(listzona.get(nozona, []))
                    titiksampel = set(listsampel.get(nozona, []))

                    if zl_type == titiksampel:
                        row[1] = "Zona Sama"
                    else:
                        row[1] = "Zona Beda"

                    if titiksampel:
                        row[2] = ", ".join(map(str, sorted(titiksampel)))
                    else:
                        row[2] = "Tidak ada Jenis Zona Titik Sampel"

                    # Isi jumlah sampel untuk zona tersebut (0 jika tidak ada sampel)
                    row[3] = jumlah_sampel.get(nozona, 0)

                    cursor.updateRow(row)

        if "NILAIZN_LAMA" in field_names:
            urutan_field_baru = [
                "WADMPR", "WADMKK", "SKALA", "THNNILAI", "NOZN", "cluster", "JNSZN", 
                "PENGGUNAAN", "HISTZONE", "JMLSMPL", "JENISSAMPEL", "BEDA_ZONA", 
                "Keterangan", "NILAIZN_LAMA", "NILBULAT_LAMA", "NILMIN", "NILMAKS", 
                "JMLNILAI", "SMPBKREL", "SMPBAKU", "NILAIZN", "NILBULAT", 
                "indeks_nilai_tanah", "Luas_M2"
            ]
        else:
            urutan_field_baru = [
                "WADMPR", "WADMKK", "SKALA", "THNNILAI", "cluster", "NOZN", "JNSZN", 
                "PENGGUNAAN", "HISTZONE", "JMLSMPL", "JENISSAMPEL", "BEDA_ZONA", 
                "NILMIN", "NILMAKS", "JMLNILAI", "SMPBKREL", "SMPBAKU", 
                "NILAIZN", "NILBULAT", "Luas_M2"
            ]
        
        reorder_fields(zl_path, urutan_field_baru)

        if arcpy.Exists(ts_path):
            arcpy.management.MakeFeatureLayer(ts_path, "Titik_Sampel")
            if arcpy.Exists(sim_ts_path):
                arcpy.management.ApplySymbologyFromLayer("Titik_Sampel", sim_ts_path)
            arcpy.management.SelectLayerByLocation("Titik_Sampel", "INTERSECT", zl_path, invert_spatial_relationship=True)
            
            count_ts = int(arcpy.management.GetCount("Titik_Sampel")[0])
            if count_ts > 0:
                ts_fields = {f.name.lower(): f.name for f in arcpy.ListFields(ts_path)}
                sampel_field = (
                    ts_fields.get("no_sampel")
                    or ts_fields.get("nomor_entry")
                    or "OID@"
                )

                nomor_sampel_luar = []
                with arcpy.da.SearchCursor("Titik_Sampel", [sampel_field, "OID@"]) as s_cursor:
                    for no_sampel, oid in s_cursor:
                        if no_sampel is not None and str(no_sampel).strip() != "":
                            nomor_sampel_luar.append(str(no_sampel).strip())
                        else:
                            nomor_sampel_luar.append(f"OID-{oid}")

                nomor_sampel_luar.sort(key=lambda x: (0, int(x)) if x.isdigit() else (1, x))
                daftar_nomor_str = ", ".join(nomor_sampel_luar)

                arcpy.AddWarning(
                    f"PERINGATAN: Terdapat {count_ts} Titik Sampel di LUAR Zona Layer "
                    f"(Nomor Titik Sampel: {daftar_nomor_str}). Lihat titik terpilih di Peta!"
                )
            
            arcpy.SetParameter(2, "Titik_Sampel")

        if arcpy.Exists(tz_path):
            arcpy.management.MakeFeatureLayer(tz_path, "Titik_Zona")
            if arcpy.Exists(sim_tz_path):
                arcpy.management.ApplySymbologyFromLayer("Titik_Zona", sim_tz_path)
            arcpy.management.SelectLayerByLocation("Titik_Zona", "INTERSECT", zl_path, invert_spatial_relationship=True)
            
            count_tz = int(arcpy.management.GetCount("Titik_Zona")[0])
            if count_tz > 0:
                arcpy.AddError(f"PERINGATAN: Terdapat {count_tz} Titik Zona yang berada di LUAR Zona Layer. Lihat titik Terpilih di Peta!")
            
            arcpy.SetParameter(3, "Titik_Zona")
            
        arcpy.management.MakeFeatureLayer(zl_path, "Zona_Layer")
        if arcpy.Exists(sim_path):
            arcpy.management.ApplySymbologyFromLayer("Zona_Layer", sim_path)
            
        arcpy.SetParameter(1, "Zona_Layer")

        # Cleanup temporary identity
        for fc in identity_layers:
            if arcpy.Exists(fc):
                arcpy.management.Delete(fc)

        return

    def postExecute(self, parameters):
        return
    
class Sesuaikan_Jenis_Zona(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Sesuaikan Atribut Jenis Zona"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        jenis_zona = arcpy.Parameter(
            displayName="Jenis Zona",
            name="jenis_zona",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        jenis_zona.filter.type = "ValueList"
        jenis_zona.filter.list = ["Pertanian", "Non-Pertanian"]


        output_zl = arcpy.Parameter(
            name="output_zl",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [jenis_zona, output_zl]


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
        delete_bad_file()
        jenis_zona = parameters[0].valueAsText

        config_dan_paths = get_config_values()
        workspace = config_dan_paths['gdb_path']
        kode_zona = 1
        if jenis_zona == "Non-Pertanian":
            kode_zona = 1
        elif jenis_zona == "Pertanian":
            kode_zona = 2

        zl = "Zona_Layer"
        if not arcpy.Exists(zl):
            arcpy.AddError("ERROR: Masukkan data dasar terlebih dahulu.")
        else:
            ada_seleksi = len(arcpy.Describe(zl).FIDSet)  
            if ada_seleksi > 0:

                try:
                    with arcpy.da.Editor(workspace) as edit:
                        with arcpy.da.UpdateCursor(zl, ["JNSZN", "PENGGUNAAN"]) as cursor:
                            for row in cursor:
                                row[0] = kode_zona  
                                row[1] = jenis_zona  
                                cursor.updateRow(row)
                
                except Exception as e:
                    if str(e) == 'Cannot acquire a lock.':
                        arcpy.AddError(f'Tutup tabel atribut pada layer Zona_Layer sebelum menjalankan tool ini.')
                        sys.exit(1)
                    else:
                        arcpy.AddError(f"ERROR: Terjadi kesalahan saat mengupdate atribut jenis zona. {e}")
                        sys.exit(1)
                arcpy.CalculateField_management(
                    zl, 
                    "PENGGUNAAN", 
                    f'"{jenis_zona}"', 
                    "PYTHON3", 
                    ""
                )
                sim_path = os.path.join(config_dan_paths['symbology_folder'], "Simbologi_Sesuaikan_Jenis_Zona.lyrx")
                
                arcpy.management.MakeFeatureLayer(config_dan_paths['zl_path'], "Zona_Layer")
                arcpy.management.ApplySymbologyFromLayer("Zona_Layer", sim_path)
                arcpy.SetParameter(1, "Zona_Layer")

            elif ada_seleksi == 0:
                arcpy.AddWarning("Tidak ada fitur yang dipilih pada layer Zona_Layer.")
        return

class Sesuaikan_Jenis_Zona_Lanjutan(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Sesuaikan Atribut Jenis Zona Lanjutan"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        jenis_zona = arcpy.Parameter(
            displayName="Jenis Zona",
            name="jenis_zona",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        jenis_zona.filter.type = "ValueList"
        jenis_zona.filter.list = ["Pertanian", "Non-Pertanian"]

        # 1. Parameter Checkbox untuk menjalankan Periksa Jenis Zona
        jalankan_periksa = arcpy.Parameter(
            displayName="Jalankan Periksa Jenis Zona otomatis",
            name="jalankan_periksa",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input")
        jalankan_periksa.value = True  # Default dicentang (True)

        output_zl = arcpy.Parameter(
            name="output_zl",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )
        
        # 2. Output tambahan jika Periksa Jenis Zona dijalankan
        output_ts = arcpy.Parameter(
            name="output_ts",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )
        
        output_tz = arcpy.Parameter(
            name="output_tz",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        # Susunan urutan: 0=jenis_zona, 1=jalankan_periksa, 2=output_zl, 3=output_ts, 4=output_tz
        return [jenis_zona, jalankan_periksa, output_zl, output_ts, output_tz]

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        return
        
    def updateMessages(self, parameters):
        return   

    def execute(self, parameters, messages):
        """The source code of the tool."""
        jenis_zona = parameters[0].valueAsText
        jalankan_periksa = parameters[1].value  # Nilainya True atau False

        config_dan_paths = get_config_values()
        workspace = config_dan_paths['gdb_path']
        sampel = os.path.join(config_dan_paths['dataset_path'], "Titik_Sampel")

        selected_ids = samplepoint.get_selected_oids('Titik_Sampel')
        if len(selected_ids) > 0:
            arcpy.AddError("ERROR: Fitur Editing masih menyala pada Titik_Sampel. Matikan terlebih dahulu sebelum melanjutkan proses.")
            sys.exit(1)

        zl = "Zona_Layer"
        JNSZN = 1  # Default value untuk Non-Pertanian
        if jenis_zona == "Non-Pertanian":
            JNSZN = 1
        elif jenis_zona == "Pertanian":
            JNSZN = 2
        
        # Daftar field yang wajib ada
        required_fields = ["JNSZN", "JENISSAMPEL", "PENGGUNAAN"]

        # Dapatkan daftar field yang ada di layer
        field_names = [field.name for field in arcpy.ListFields(zl)]

        # Validasi field yang dibutuhkan
        missing_fields = [field for field in required_fields if field not in field_names]

        if missing_fields:
            error_message = "ERROR: Field berikut dibutuhkan tetapi tidak ditemukan: " + ", ".join(missing_fields)
            arcpy.AddError(error_message)
            raise ValueError(error_message)
        
        ada_seleksi = len(arcpy.Describe(zl).FIDSet)  # Memeriksa apakah ada fitur yang dipilih

        if ada_seleksi > 0:
            try:
                with arcpy.da.Editor(workspace):
                    with arcpy.da.UpdateCursor(zl, ["JNSZN", "JENISSAMPEL", "PENGGUNAAN"]) as cursor1:
                        for row in cursor1:
                            row[0] = JNSZN            # JNSZN
                            row[1] = str(JNSZN)       # JENISSAMPEL
                            row[2] = jenis_zona       # PENGGUNAAN
                            cursor1.updateRow(row)

                    with arcpy.da.UpdateCursor(zl, ["JNSZN", "JENISSAMPEL", "BEDA_ZONA"]) as cursor2:
                        for row in cursor2:
                            JNSZN_str = str(row[0]) if row[0] is not None else ""
                            jenissampel_list = []
                            
                            if row[1] is not None:
                                jenissampel_list = [str(x).strip() for x in str(row[1]).split(",")]
                                
                            if JNSZN_str and JNSZN_str in jenissampel_list:
                                row[2] = "Zona Sama"  # Menandai kesesuaian zona
                            elif row[1] is not None: 
                                row[2] = "Zona Beda"  # Menandai ketidaksesuaian zona
                            else: 
                                row[2] = "Tidak ada Jenis Zona Titik Sampel"  # Default value
                                
                            cursor2.updateRow(row)
                            
            except Exception as e:
                error_msg = str(e).lower()
                # Ambil riwayat error asli (stack trace) dari Python
                if getattr(e, '__cause__', None):
                    error_msg += f" {str(e.__cause__).lower()}"
                if getattr(e, '__context__', None):
                    error_msg += f" {str(e.__context__).lower()}"
                
                # Cek apakah ada kata kunci lock di riwayat error
                if 'lock' in error_msg or 'in use' in error_msg or 'exclusive' in error_msg:
                    arcpy.AddError('ERROR: Layer "Zona_Layer" sedang terkunci (Lock).')
                    arcpy.AddError('SOLUSI: Tutup tabel atribut, pastikan Anda tidak sedang dalam mode Editing aktif (Save Edits & matikan Edit), lalu coba jalankan kembali.')
                else:
                    arcpy.AddError(f"ERROR GAGAL MENGUPDATE ATRIBUT: {e}")
                return

            self.sinkronisasi_zoning(sampel, "Titik_Sampel_temp", workspace)

        # 3. Logika Pemilihan Aksi Berdasarkan Checkbox
        if jalankan_periksa:
            arcpy.AddMessage("Menjalankan Periksa Jenis Zona secara otomatis...")
            self._jalankan_periksa_jenis_zona(config_dan_paths, workspace)
            
            # Set Output Parameter sesuai eksekusi penuh
            arcpy.SetParameter(2, "Zona_Layer")
            if arcpy.Exists("Titik_Sampel"):
                arcpy.SetParameter(3, "Titik_Sampel")
            if arcpy.Exists("Titik_Zona"):
                arcpy.SetParameter(4, "Titik_Zona")
        else:
            # Jika tidak dicentang, hanya setel Simbologi biasa
            sim_path = os.path.join(config_dan_paths['symbology_folder'], "Simbologi_Sesuaikan_Jenis_Zona.lyrx")
            arcpy.management.MakeFeatureLayer(os.path.join(config_dan_paths['dataset_path'], "Zona_Layer"), "Zona_Layer")
            
            if arcpy.Exists(sim_path):
                arcpy.management.ApplySymbologyFromLayer("Zona_Layer", sim_path)
            
            # Set Output Parameter 
            arcpy.SetParameter(2, "Zona_Layer")

        return
    
    def sinkronisasi_zoning(self, layer_path, temp_name, workspace):
        if not arcpy.Exists(layer_path):
            return
            
        zl = "Zona_Layer"
        out_temp_fc = fr"in_memory\{temp_name}"

        arcpy.analysis.SpatialJoin(
            layer_path,
            zl,
            out_temp_fc,
            "JOIN_ONE_TO_MANY",
            "KEEP_ALL",
            'sync_id "sync_id" true true false 100 Text 0 0,First,#,'
            f'{layer_path},sync_id,0,100;'
            'JNSZN "JNSZN" true true false 2 Short 0 0,First,#,zl,JNSZN,-1,-1',
            "INTERSECT"
        )

        arcpy.management.JoinField(
            layer_path,
            "OBJECTID",
            out_temp_fc,
            "TARGET_FID",
            ["JNSZN"]
        )

        with arcpy.da.Editor(workspace):
            with arcpy.da.UpdateCursor(layer_path, ["JNSZN", "Zoning"]) as cursor:
                for row in cursor:
                    if row[0] is not None and row[1] != row[0]:
                        row[1] = row[0]
                        cursor.updateRow(row)

        arcpy.management.DeleteField(layer_path, "JNSZN")
        arcpy.management.Delete(out_temp_fc) 

    def _jalankan_periksa_jenis_zona(self, config_dan_paths, workspace):
        """Helper method yang memuat logika utuh dari tool Periksa_Jenis_Zona"""
        ts_path = os.path.join(config_dan_paths['dataset_path'], "Titik_Sampel")
        tz_path = os.path.join(config_dan_paths['dataset_path'], "Titik_Zona")
        zl_path = os.path.join(config_dan_paths['dataset_path'], "Zona_Layer")
        
        sim_path = os.path.join(config_dan_paths['symbology_folder'], "Simbologi_Periksa_Jenis_Zona.lyrx")
        sim_ts_path = os.path.join(config_dan_paths['symbology_folder'], "Titik_Sampel.lyrx")
        sim_tz_path = os.path.join(config_dan_paths['symbology_folder'], "Titik_Zona.lyrx") 

        zl_topology_path = os.path.join(config_dan_paths['dataset_path'], "Zona_Layer_Topology")
        if arcpy.Exists(zl_topology_path):
            arcpy.management.Delete(zl_topology_path)

        identity_layers = []

        # Identity Titik Zona (jika ada)
        if arcpy.Exists(tz_path):
            arcpy.analysis.Identity(tz_path, zl_path, "identity_tz")
            identity_layers.append("identity_tz")

        # Identity Titik Sampel
        if arcpy.Exists(ts_path):
            arcpy.analysis.Identity(ts_path, zl_path, "identity_ts")
            identity_layers.append("identity_ts")

        # Dictionary penyimpanan
        listzona = {}
        listsampel = {}

        for identity_fc in identity_layers:
            with arcpy.da.SearchCursor(identity_fc, ["NOZN", "JNSZN", "Zoning"]) as cursor:
                for nozona, jenis, zoning in cursor:
                    if nozona is None or str(nozona).strip() == "":
                        continue

                    if nozona not in listzona:
                        listzona[nozona] = set()
                    if jenis is not None:
                        listzona[nozona].add(jenis)

                    if nozona not in listsampel:
                        listsampel[nozona] = set()
                    if zoning is not None:
                        listsampel[nozona].add(zoning)

        # Hapus field lama jika ada
        field_names = [f.name for f in arcpy.ListFields(zl_path)]
        if "JENISSAMPEL" in field_names:
            arcpy.management.DeleteField(zl_path, "JENISSAMPEL")
        if "BEDA_ZONA" in field_names:
            arcpy.management.DeleteField(zl_path, "BEDA_ZONA")

        # Tambah field baru
        arcpy.management.AddField(zl_path, "JENISSAMPEL", "TEXT", field_alias="JENIS SAMPEL")
        arcpy.management.AddField(zl_path, "BEDA_ZONA", "TEXT", field_alias="BEDA ZONA")

        try:
            with arcpy.da.Editor(workspace):
                with arcpy.da.UpdateCursor(zl_path, ["NOZN", "BEDA_ZONA", "JENISSAMPEL"]) as cursor:
                    for row in cursor:
                        nozona = row[0]
                        zl_type = set(listzona.get(nozona, []))
                        titiksampel = set(listsampel.get(nozona, []))

                        if zl_type == titiksampel:
                            row[1] = "Zona Sama"
                        else:
                            row[1] = "Zona Beda"

                        if titiksampel:
                            row[2] = ", ".join(map(str, sorted(titiksampel)))
                        else:
                            row[2] = "Tidak ada Jenis Zona Titik Sampel"

                        cursor.updateRow(row)
        except Exception as e:
            # Error catch robust seperti pada Sesuaikan
            error_msg = str(e).lower()
            if getattr(e, '__cause__', None):
                error_msg += f" {str(e.__cause__).lower()}"
            if getattr(e, '__context__', None):
                error_msg += f" {str(e.__context__).lower()}"
            
            if 'lock' in error_msg or 'in use' in error_msg or 'exclusive' in error_msg:
                arcpy.AddError('ERROR: Layer "Zona_Layer" sedang terkunci saat menjalankan Periksa Jenis Zona.')
                return
            else:
                arcpy.AddError(f"ERROR GAGAL MENGUPDATE ATRIBUT (Periksa): {e}")
                return

        # Proses reorder field
        field_names_updated = [f.name for f in arcpy.ListFields(zl_path)]
        if "NILAIZN_LAMA" in field_names_updated:
            urutan_field_baru = [
                "WADMPR", "WADMKK", "SKALA", "THNNILAI", "NOZN", "cluster", "JNSZN", 
                "PENGGUNAAN", "HISTZONE", "JMLSMPL", "JENISSAMPEL", "BEDA_ZONA", 
                "Keterangan", "NILAIZN_LAMA", "NILBULAT_LAMA", "NILMIN", "NILMAKS", 
                "JMLNILAI", "SMPBKREL", "SMPBAKU", "NILAIZN", "NILBULAT", 
                "indeks_nilai_tanah", "Luas_M2"
            ]
        else:
            urutan_field_baru = [
                "WADMPR", "WADMKK", "SKALA", "THNNILAI", "cluster", "NOZN", "JNSZN", 
                "PENGGUNAAN", "HISTZONE","JMLSMPL", "JENISSAMPEL", "BEDA_ZONA", 
                "NILMIN", "NILMAKS", "JMLNILAI", "SMPBKREL", "SMPBAKU", 
                "NILAIZN", "NILBULAT", "Luas_M2"
            ]
        
        reorder_fields(zl_path, urutan_field_baru)

        # Terapkan layer dan simbologi Titik Sampel & Zona
        if arcpy.Exists(ts_path):
            arcpy.management.MakeFeatureLayer(ts_path, "Titik_Sampel")
            if arcpy.Exists(sim_ts_path):
                arcpy.management.ApplySymbologyFromLayer("Titik_Sampel", sim_ts_path)
            arcpy.management.SelectLayerByLocation("Titik_Sampel", "INTERSECT", zl_path, invert_spatial_relationship=True)
            
            count_ts = int(arcpy.management.GetCount("Titik_Sampel")[0])
            if count_ts > 0:
                arcpy.AddError(f"PERINGATAN: Terdapat {count_ts} Titik Sampel yang berada di LUAR Zona Layer. Lihat titik Terpilih di Peta!")

        if arcpy.Exists(tz_path):
            arcpy.management.MakeFeatureLayer(tz_path, "Titik_Zona")
            if arcpy.Exists(sim_tz_path):
                arcpy.management.ApplySymbologyFromLayer("Titik_Zona", sim_tz_path)
            arcpy.management.SelectLayerByLocation("Titik_Zona", "INTERSECT", zl_path, invert_spatial_relationship=True)
            
            count_tz = int(arcpy.management.GetCount("Titik_Zona")[0])
            if count_tz > 0:
                arcpy.AddError(f"PERINGATAN: Terdapat {count_tz} Titik Zona yang berada di LUAR Zona Layer. Lihat titik Terpilih di Peta!")
            
        arcpy.management.MakeFeatureLayer(zl_path, "Zona_Layer")
        if arcpy.Exists(sim_path):
            arcpy.management.ApplySymbologyFromLayer("Zona_Layer", sim_path)
            
        # Cleanup temporary identity
        for fc in identity_layers:
            if arcpy.Exists(fc):
                arcpy.management.Delete(fc)
