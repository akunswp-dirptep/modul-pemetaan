import arcpy, os, sys

script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
    
from zntutils.zona_layer import get_config_values

arcpy.env.outputZFlag = "Disabled"  # Menonaktifkan output nilai Z (3D)
arcpy.env.outputMFlag = "Disabled"  # Menonaktifkan output nilai M (measure)

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
        
        penjelasan.value =(
            "Tool ini digunakan untuk memeriksa kesesuaian jenis zona\n"
            "antara Zona Layer dan Titik Sampel. ")
        
        output_zl = arcpy.Parameter(
            name="output_zl",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [penjelasan, output_zl]

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
        self.config_dan_paths = get_config_values()
        ts_path = os.path.join(self.config_dan_paths['dataset_path'], "Titik_Sampel")  # Path layer titik sampel
        zl_path = os.path.join(self.config_dan_paths['dataset_path'], "Zona_Layer")  # Path zona layer
        zl_temp_path = os.path.join(self.config_dan_paths['dataset_path'], "Zona_Layer_Temp")  # Path zona layer temporary
        sim_path = os.path.join(self.config_dan_paths['symbology_folder'], "Simbologi_Periksa_Jenis_Zona.lyrx")  # Path file simbologi
        zl_topology_path = os.path.join(self.config_dan_paths['dataset_path'], "Zona_Layer_Topology")  # Path zona layer topology

        if arcpy.Exists(zl_topology_path):
            arcpy.management.Delete(zl_topology_path) 
        # Membuat salinan temporary zona layer jika belum ada
        if not arcpy.Exists(zl_temp_path):
            arcpy.management.Copy(zl_path, zl_temp_path)

        # Menghapus field BEDA_ZONA jika sudah ada dan menambahkannya kembali
        field_names = [field.name for field in arcpy.ListFields(zl_temp_path)]
        if "BEDA_ZONA" in field_names:
            arcpy.management.DeleteField(zl_temp_path, "BEDA_ZONA")

        arcpy.management.AddField(zl_temp_path, "BEDA_ZONA", "TEXT")

        # Melakukan analisis Identity antara titik sampel dan zona layer
        arcpy.analysis.Identity(ts_path, zl_path, 'identity')

        # Membuat dictionary untuk menyimpan jenis zona per nomor zona
        listzona = {}
        listsampel= {}
        with arcpy.da.SearchCursor('identity', ["NOZN", "JNSZN"]) as cursor:
            for row in cursor:
                nozona = row[0]
                jenis = row[1]
                if nozona not in listzona:
                    listzona[nozona] = set()  # Menggunakan set untuk nilai unik
                listzona[nozona].add(jenis)
        with arcpy.da.SearchCursor('identity', ["NOZN", "Zoning"]) as cursor:
            for row in cursor:
                nozona = row[0]
                zoning = row[1]
                if nozona not in listsampel:
                    listsampel[nozona] = set()  # Menggunakan set untuk nilai unik
                listsampel[nozona].add(zoning)
        field_names = [f.name for f in arcpy.ListFields(zl_path)]
        if "JENISSAMPEL" in field_names:
            arcpy.DeleteField_management(zl_path, "JENISSAMPEL")
        arcpy.AddField_management(zl_path, "JENISSAMPEL", "TEXT")
        if "BEDA_ZONA" in field_names:
            arcpy.DeleteField_management(zl_path, "BEDA_ZONA")
        arcpy.management.AddField(zl_path, "BEDA_ZONA", "TEXT")

        with arcpy.da.UpdateCursor(zl_path, ["NOZN", "BEDA_ZONA", "JENISSAMPEL"]) as cursor:
            for row in cursor:
                nozona = row[0] 
                zl_type = set(listzona.get(nozona, []))  # Jenis zona dari zona layer
                titiksampel = set(listsampel.get(nozona, []))  # Zoning dari titik sampel
                if zl_type == titiksampel:
                    row[1] = 'Zona Sama'  # Menandai jika zona sama
                else:
                    row[1] = 'Zona Beda'  # Menandai jika zona berbeda
                if titiksampel:  
                    row[2] = ", ".join(map(str, titiksampel))  # Menggabungkan nilai zoning
                else:
                    row[2] = "Tidak ada Jenis Zona Titik Sampel"  # Default value jika kosong
                cursor.updateRow(row)
        arcpy.management.MakeFeatureLayer(zl_path, "Zona_Layer")
        arcpy.management.ApplySymbologyFromLayer("Zona_Layer", sim_path)
        arcpy.management.Delete(zl_temp_path)
        arcpy.SetParameter(1, "Zona_Layer")  # Mengatur parameter output
        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return
    
class Sesuaikan_Jenis_Zona(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Sesuaikan Jenis Zona"
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
        jenis_zona = parameters[0].valueAsText

        config_dan_paths = get_config_values()
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
                arcpy.AddMessage(f'{kode_zona} - {jenis_zona}')
                try:
                    with arcpy.da.UpdateCursor(zl, ["JNSZN", "PENGGUNAAN"]) as cursor:
                        for row in cursor:
                            arcpy.AddMessage(f'JNSZN: {row[0]}, PENGGUNAAN: {row[1]}')
                            arcpy.AddMessage(f'JNSZN: {kode_zona}, PENGGUNAAN: {jenis_zona}')
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
        self.label = "Sesuaikan Jenis Zona Lanjutan"
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
        jenis_zona = parameters[0].valueAsText

        config_dan_paths = get_config_values()
        sampel = os.path.join(config_dan_paths['dataset_path'], "Titik_Sampel")  # Path layer titik sampel
        out_temp = os.path.join(config_dan_paths['dataset_path'], "Titik_Sampel_temp")
        zl= "Zona_Layer"
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
            # Jika ada field yang tidak ditemukan
            error_message = "ERROR: Field berikut dibutuhkan tetapi tidak ditemukan: " + ", ".join(missing_fields)
            arcpy.AddError(error_message)
            raise ValueError(error_message)
        
        a = 1
        ada_seleksi = 0
        ada_seleksi = len(arcpy.Describe(zl).FIDSet)  # Memeriksa apakah ada fitur yang dipilih

        if ada_seleksi > 0:
            # Update field-field di Zona Layer untuk fitur yang dipilih
            try:            
                rows = arcpy.UpdateCursor(zl)
                for row in rows:
                    row.setValue("JNSZN", JNSZN)  # Mengatur nilai JNSZN
                    row.setValue("JENISSAMPEL", JNSZN)  # Mengatur nilai JENISSAMPEL
                    row.setValue("PENGGUNAAN", jenis_zona)  # Mengatur nilai PENGGUNAAN
                    rows.updateRow(row)
                del row
                del rows
            except Exception as e:
                    if str(e) == 'Cannot acquire a lock.':
                        arcpy.AddError(f'Tutup tabel atribut pada layer Zona_Layer sebelum menjalankan tool ini.')
                        return
                    else:
                        arcpy.AddError(f"ERROR: Terjadi kesalahan saat mengupdate atribut jenis zona. {e}")
                        return


            cursor = arcpy.da.UpdateCursor(zl, ["JNSZN", "JENISSAMPEL","BEDA_ZONA"])
            for row in cursor:
                JNSZN_str = str(row[0])  # Konversi JNSZN ke string
                jenissampel_list = []
                if row[1] is not None:
                    # Memisahkan nilai JENISSAMPEL yang dipisahkan koma
                    jenissampel_list = [x.strip() for x in row[1].split(",")]
                if JNSZN_str in jenissampel_list:
                    row[2] = "Zona Sama"  # Menandai kesesuaian zona
                elif row[1] is not None: 
                    row[2] = "Zona Beda"  # Menandai ketidaksesuaian zona
                else: 
                    row[2] = "Tidak ada Jenis Zona Titik Sampel"  # Default value
                cursor.updateRow(row)
            del row, cursor

            arcpy.analysis.SpatialJoin(sampel, zl, out_temp, "JOIN_ONE_TO_MANY", "KEEP_ALL", "sync_id \"sync_id\" true true false 100 Text 0 0,First,#,sampel,sync_id,0,100; JNSZN \"JNSZN\" true true false 2 Short 0 0,First,#,zl,JNSZN,-1,-1", "INTERSECT")
            
            # Join field JNSZN dari temporary layer ke Titik_Sampel
            arcpy.management.JoinField(sampel, "OBJECTID", out_temp, "TARGET_FID", ["JNSZN"])
            
            # Update field Zoning di Titik_Sampel berdasarkan nilai JNSZN yang baru
            rows = arcpy.da.UpdateCursor(sampel, ["JNSZN", "Zoning"])
            for row in rows:
                if row[1] != row[0] and row[0] != None:
                    row[1] = row[0]  # Update Zoning dengan nilai JNSZN
                rows.updateRow(row)
            del row, rows
            
            # Membersihkan field JNSZN yang telah di-join
            arcpy.management.DeleteField(sampel, "JNSZN")
            sim_path = os.path.join(config_dan_paths['symbology_folder'], "Simbologi_Sesuaikan_Jenis_Zona.lyrx")
                
            arcpy.management.MakeFeatureLayer(config_dan_paths['zl_path'], "Zona_Layer")
            arcpy.management.ApplySymbologyFromLayer("Zona_Layer", sim_path)
            arcpy.SetParameter(1, "Zona_Layer")
        return

 