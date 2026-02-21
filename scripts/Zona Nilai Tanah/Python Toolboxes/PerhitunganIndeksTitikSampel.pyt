import os, arcpy, json, sys
from penilaiantanahutils import zonalayer, samplepoint

arcpy.env.outputZFlag = "Disabled"
arcpy.env.outputMFlag = "Disabled"


class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Perhitungan Indeks Titik Sampel"
        self.alias = "perhitungan_indeks_titik_sampel"

        # List of tool classes associated with this toolbox
        self.tools = [Perhitungan_Indeks_Titik_Sampel_Keseluruhan, Perhitungan_Indeks_Titik_Sampel_Terpilih]


class Perhitungan_Indeks_Titik_Sampel_Keseluruhan:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Perhitungan Indeks Titik Sampel Keseluruhan"
        self.description = ""

    def getParameterInfo(self):
        """Define the tool parameters."""
        penjelasan = arcpy.Parameter(
            displayName="Hitung Indeks Titik Sampel Keseluruhan",
            name="penjelasan",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )

        penjelasan.value = (
            "Tools ini melakukan overlay Identity antara layer\n"
            "Titik Sampel dan Zona untuk menghasilkan data baru, \n"
            "lalu menghitung indeks_sampel berdasarkan jenis zona \n"
            "dengan rumus tertentu dan faktor pembulatan yang telah \n"
            "ditentukan.\n\n"

            "!-!-! CATATAN PENTING !-!-!\n" 
            "Jika sudah terdapat titik zona, menggunakan tools ini akan\n"
            "menghapus semua data pada layer titik zona tersebut, jika hanya\n"
            "ingin mengubah beberapa titik sampel menjadi titik zona gunakan\n"
            "tools hitung indeks sampel untuk titik terpilih\n"
        )

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
        """The source code of the tool."""
        self.get_config_values()
        self.main_processing()
        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return
    
    def get_config_values(self):
        # Konfigurasi Path Aplikasi
        self.appdata = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))

        # Konfigurasi Path Project
        zl_path = zonalayer.is_zona_layer_comply()
        ws_dir = os.path.dirname(os.path.dirname(os.path.dirname(zl_path)))
        config_path = os.path.join(ws_dir, "config.json")
        configs = None
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                configs = json.load(f)

        self.gdb_path = configs['gdb_path']
        self.dataset_path = configs['dataset_path']
        zonalayer.check_if_there_selected_field()
        return
        
    def main_processing(self):

        bulat1 = "100"  # Faktor pembulatan untuk jenis zona 1
        bulat2 = "100"  # Faktor pembulatan untuk jenis zona 2

        # Mendefinisikan path untuk feature classes yang akan digunakan
        zl = os.path.join(self.dataset_path, "Zona_Layer")      
        ts = os.path.join(self.dataset_path, "Titik_Sampel")    
        hi = os.path.join(self.dataset_path, "Hitung_Indeks")    
        tzt = os.path.join(self.dataset_path, "Titik_Zona_Temp") 

        if arcpy.Exists(hi):
            arcpy.management.Delete(os.path.join(self.gdb_path, "Hitung_Indeks"))
            arcpy.management.Delete(hi)
            
        arcpy.analysis.Identity(in_features = ts, 
                                identity_features = zl, 
                                out_feature_class = hi)

        arcpy.management.AddField(hi, "indeks_sampel", "DOUBLE", field_alias="INDEKS SAMPEL")
        # Code block Python untuk menghitung nilai indeks berdasarkan jenis zona
        code_block = """def doSomething(nila,men,jeniszona,bulat1,bulat2):
            if jeniszona == 1:
                return round(bulat1 * ( nila/men ),2)  # Hitung indeks untuk zona jenis 1
            elif jeniszona == 2:
                return round(bulat2 * ( nila/men ),2)  # Hitung indeks untuk zona jenis 2"""

        # Menghitung nilai indeks sampel menggunakan fungsi Python di atas
        arcpy.management.CalculateField(hi, "indeks_sampel", "doSomething(int(!nilai!),float(!NILAIZN_LAMA!),!JNSZN!," + bulat1 + "," + bulat2 + ")", "PYTHON3", code_block)

        # Mengurutkan data berdasarkan jenis zona dan indeks sampel (ascending)
        arcpy.management.Sort(hi, tzt, [["JNSZN", "ASCENDING"], ["indeks_sampel", "ASCENDING"]])

        list_field = [field.name for field in arcpy.ListFields(tzt)]
        fields_to_delete = ["ORIG_FID", "indeks_nilai_tanah", "Keterangan_1"]
        for field in fields_to_delete:
            if field in list_field:
                arcpy.management.DeleteField(tzt, field)
        
        field_delimited = arcpy.AddFieldDelimiters(self.dataset_path, "Jenis_Data")
        filter_clause = "{} <> 'Individual'".format(field_delimited)
        arcpy.AddMessage(filter_clause)
        titik_zona_path = arcpy.conversion.FeatureClassToFeatureClass(tzt, self.dataset_path, "Titik_Zona", filter_clause)[0]
        aprx = arcpy.mp.ArcGISProject('CURRENT')

        current_map = aprx.activeMap
        existing_layers = current_map.listLayers("Titik_Sampel")
        for layer in existing_layers:
            current_map.removeLayer(layer)

        current_map.addDataFromPath(ts)
        current_map.addDataFromPath(titik_zona_path)
        # Refresh view
        aprx.save()
        del aprx

        # Use UpdateCursor within a 'with' statement for proper resource management
        try:
            with arcpy.da.UpdateCursor(ts, ['Jenis_Data']) as cursor:
                for row in cursor:
                    # Check if the row meets the criteria for deletion
                    if row[0] != 'Individual':
                        cursor.deleteRow()
                del cursor


        except Exception as e:
            arcpy.AddError(f"Terdapat error: {e}")

        arcpy.AddMessage(f"Fitur dihapus dari {ts} berdasarkan kriteria.")

        arcpy.management.Delete(tzt)
        arcpy.management.Delete(hi)

        

class Perhitungan_Indeks_Titik_Sampel_Terpilih:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Perhitungan Indeks Titik Sampel Terpilih"
        self.description = ""

    def getParameterInfo(self):
        """Define the tool parameters."""
        penjelasan = arcpy.Parameter(
            displayName="Hitung Indeks Titik Sampel Terpilih",
            name="penjelasan",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )



        penjelasan.value = (
            "Tools ini melakukan overlay Identity antara layer\n"
            "Titik Sampel dan Zona untuk menghasilkan data baru pada, \n"
            "titik sampel yang dipilih\n\n"

        )

        titik_zona = arcpy.Parameter(
            name="titik_zona",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output",
        )

        titik_sampel = arcpy.Parameter(
            name="titik_sampel",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output",
        )

        params = [penjelasan, titik_zona, titik_sampel]
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
        self.get_config_values()
        self.main_processing()
        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return
    
    def get_config_values(self):
        # Konfigurasi Path Aplikasi
        self.appdata = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))

        # Konfigurasi Path Project
        zl_path = zonalayer.is_zona_layer_comply()
        ws_dir = os.path.dirname(os.path.dirname(os.path.dirname(zl_path)))
        config_path = os.path.join(ws_dir, "config.json")
        configs = None
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                configs = json.load(f)

        self.gdb_path = configs['gdb_path']
        self.dataset_path = configs['dataset_path']
        zonalayer.check_if_there_selected_field()
        return
    
    def main_processing(self):
        zl = os.path.join(self.dataset_path, "Zona_Layer")      # Layer zona
        ts = os.path.join(self.dataset_path, "Titik_Sampel")
        tz = os.path.join(self.dataset_path, "Titik_Zona")      # Layer sumber
        tzt = os.path.join(self.dataset_path, "Titik_Zona_Temp") # Layer tujuan

        def get_necessary_fields(feaure_1):
            # Mendefinisikan path untuk feature classes yang akan digunakan

            # Buat feature class baru berdasarkan geometri sumber
            spatial_ref = arcpy.Describe(tz).spatialReference
            geometry_type = arcpy.Describe(tz).shapeType

            # Hapus jika sudah ada
            if arcpy.Exists(tzt):
                arcpy.management.Delete(tzt)

            # Buat feature class baru dengan geometri yang sama
            arcpy.management.CreateFeatureclass(self.dataset_path, "Titik_Zona_Temp", geometry_type, spatial_reference=spatial_ref)
            arcpy.analysis.Identity(feaure_1, zl, tzt)
            # Menambahkan field baru untuk menyimpan nilai indeks sampel
            arcpy.management.AddField(tzt, "indeks_sampel", "DOUBLE")

            bulat1 = "100"  # Faktor pembulatan untuk jenis zona 1
            bulat2 = "100"  # Faktor pembulatan untuk jenis zona 2
            # Code block Python untuk menghitung nilai indeks berdasarkan jenis zona
            code_block = """def doSomething(nila,men,jeniszona,bulat1,bulat2):
                if jeniszona == 1:
                    return round(bulat1 * ( nila/men ),2)  # Hitung indeks untuk zona jenis 1
                elif jeniszona == 2:
                    return round(bulat2 * ( nila/men ),2)  # Hitung indeks untuk zona jenis 2"""

            # Menghitung nilai indeks sampel menggunakan fungsi Python di atas
            arcpy.management.CalculateField(tzt, "indeks_sampel", "doSomething(int(!nilai!),float(!NILAIZN_LAMA!),!JNSZN!," + bulat1 + "," + bulat2 + ")", "PYTHON3", code_block)
            arcpy.management.Append(tzt, tz, "NO_TEST")

            arcpy.management.Delete(tzt)
        
        def transfer_features(source_layer, target_layer, selected_ids):
            where_clause = f"OBJECTID IN ({','.join(map(str, selected_ids))})"
            temp_layer = arcpy.management.MakeFeatureLayer(source_layer, "temp_selected", where_clause)[0]
            temp_copy = arcpy.management.CopyFeatures(temp_layer, "in_memory\\Titik_Sampel")[0]     

            get_necessary_fields(temp_copy)

            with arcpy.da.UpdateCursor(source_layer, ["OBJECTID"]) as ucur:
                for row in ucur:
                    if row[0] in selected_ids:
                        ucur.deleteRow()
            

            arcpy.management.DeleteFeatures(temp_layer)
            arcpy.management.Delete("in_memory\\Titik_Sampel")
            
            ui_folder = os.path.join(self.appdata, "ui")
            symbology_folder = os.path.join(ui_folder, "symbology")
            tz_simbology_path = os.path.join(symbology_folder, "Titik_Zona.lyrx")
            ts_simbology_path = os.path.join(symbology_folder, "Titik_Sampel.lyrx")

            arcpy.management.MakeFeatureLayer(tz, "Titik_Zona")
            arcpy.management.ApplySymbologyFromLayer("Titik_Zona", tz_simbology_path)

            arcpy.management.MakeFeatureLayer(ts, "Titik_Sampel")
            arcpy.management.ApplySymbologyFromLayer("Titik_Sampel", ts_simbology_path)

            arcpy.SetParameter(1, "Titik_Zona")
            arcpy.SetParameter(2, "Titik_Sampel")

        def check_individual_data(source_layer, selected_ids):
            """Check if any selected features have 'Jenis_Data' as 'Individual'."""
            individual_found = False
            where_clause = f"OBJECTID IN ({','.join(map(str, selected_ids))})"
            with arcpy.da.SearchCursor(source_layer, ["Jenis_Data"], where_clause) as cursor:
                for row in cursor:
                    if row[0] == "Individual":
                        individual_found = True
                        break
            return individual_found

        sampel_selected = samplepoint.get_selected_oids('Titik_Sampel')

        if not sampel_selected:
            arcpy.AddError("Tidak ada titik yang dipilih. Silakan pilih titik sampel (pencilan/outlier) di layer Titik Sampel.")
            sys.exit()

        if sampel_selected:
            if check_individual_data(ts, sampel_selected):
                arcpy.AddWarning("Data 'Individual' tidak dapat dipindahkan ke Titik Zona.")
                sys.exit()
            arcpy.AddMessage(f"Memindahkan {len(sampel_selected)} titik dari Titik_Sampel ke Titik_Zona...")
            transfer_features(ts, tz, sampel_selected)
            arcpy.AddMessage("Pemindahan fitur selesai. Nilai atribut bersama dipertahankan.")

