from datetime import datetime
import json
import sys
import arcpy, os, math

# Tambahkan parent directory ke sys.path
script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
gp_dir = os.path.dirname(parent_dir)
if gp_dir not in sys.path:
    sys.path.insert(0, gp_dir)

from nbtutils import constant, persil



class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [Build_Network_Dataset_Jaringan_Jalan,
                      Set_Lebar_Jalan_Persil,
                      Set_Kelas_Jalan_Persil,
                      Tampilkan_Simbologi_Persil,
                      ]


#  Terpilih
class Build_Network_Dataset_Jaringan_Jalan(object):

    def __init__(self):
        self.label = "Optimasi Build Network Dataset Jaringan Jalan"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):

        output_nd = arcpy.Parameter(
            displayName="Output Network Dataset",
            name="output_nd",
            datatype="DENetworkDataset",
            parameterType="Derived",
            direction="Output"
        )

        output_jalan_nd = arcpy.Parameter(
            displayName="Output Jaringan Jalan ND",
            name="output_jalan_nd",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        output_junction = arcpy.Parameter(
            displayName="Output Junction ND",
            name="output_junction",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [
            output_nd,
            output_jalan_nd,
            output_junction
        ]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):

            messages.addMessage("== Proses dimulai ==")
            configs = persil.get_config_values()
            dataset_path = configs["project_config"]["dataset_path"]

            gdb_path = configs["project_config"]["gdb_path"]
            jaringan_jalan = 'Jaringan_Jalan'

            jaringanjalan_path = configs["jaringan_jalan_config"]["path"]["Jaringan_Jalan"]
            nd_path = configs["jaringan_jalan_config"]["path"]["JaringanJalan_ND"]
            jaringanjalan_nd_path = configs["jaringan_jalan_config"]["path"]["JaringanJalanForND"]
            
            junction_path = os.path.join(dataset_path, "Junction")
            junction_nd_path = os.path.join(os.path.dirname(jaringanjalan_nd_path), "JaringanJalan_ND_Junctions")
            junction_diss_path = os.path.join(dataset_path, "junction_diss")
            junction_final_path = os.path.join(dataset_path, "JunctionFinal")

            messages.addMessage("== Bersih-bersih network dataset ==")

            # =====================================================
            # HAPUS LAYER DARI MAP TERLEBIH DAHULU (Mencegah File Lock)
            # =====================================================
            try:
                aprx = arcpy.mp.ArcGISProject("CURRENT")
                current_map = aprx.activeMap
                
                if current_map:
                    # Dapatkan nama layer dari path untuk pencocokan jika namanya dinamis
                    nama_jalan_nd_fc = os.path.basename(jaringanjalan_nd_path)
                    nama_junction_nd_fc = os.path.basename(junction_nd_path)
                    
                    # Daftar nama layer atau nama feature class yang ingin dibersihkan dari Map
                    target_layers = [
                        "JaringanJalan_ND", 
                        "JaringanJalanForND", 
                        "JaringanJalan_ND_Junctions",
                        nama_jalan_nd_fc,
                        nama_junction_nd_fc
                    ]
                    
                    # Iterasi dan hapus jika layer tersebut ada di map saat ini
                    for lyr in current_map.listLayers():
                        if lyr.name in target_layers:
                            current_map.removeLayer(lyr)
                            messages.addMessage(f"Membuka lock: Layer '{lyr.name}' berhasil dihapus dari Map.")
            except Exception as e:
                messages.addMessage(f"Peringatan bersih-bersih map gagal: {str(e)}")

            # =====================================================
            # KOSONGKAN DATA (Menggunakan TruncateTable agar instan)
            # =====================================================
            try:
                # Truncate jauh lebih cepat daripada DeleteRows untuk mengosongkan feature class
                arcpy.management.TruncateTable(jaringanjalan_nd_path)
                messages.addMessage("Data lama berhasil dikosongkan menggunakan Truncate.")
            except:
                try:
                    arcpy.management.DeleteRows(jaringanjalan_nd_path)
                    messages.addMessage("Data lama dikosongkan menggunakan DeleteRows.")
                except:
                    pass

            # =====================================================
            # VALIDASI KELAS JALAN
            # =====================================================
            messages.addMessage("== Validasi kelas jalan ==")
            temp_jalan = "temp_jalan"

            if arcpy.Exists(temp_jalan):
                try:
                    arcpy.management.Delete(temp_jalan)
                except:
                    pass

            kls_jln = arcpy.AddFieldDelimiters(jaringanjalan_path, "kls_jln")
            s_kls_jln = arcpy.AddFieldDelimiters(jaringanjalan_path, "s_kls_jln")
            where_clause = f"{kls_jln} IS NULL OR {s_kls_jln} IS NULL"

            arcpy.management.MakeFeatureLayer(
                jaringanjalan_path,
                temp_jalan,
                where_clause
            )

            arcpy.management.CalculateField(
                temp_jalan,
                "kls_jln",
                '"Setapak"',
                "PYTHON3"
            )

            arcpy.management.CalculateField(
                temp_jalan,
                "s_kls_jln",
                "1",
                "PYTHON3"
            )

            if arcpy.Exists(temp_jalan):
                arcpy.management.Delete(temp_jalan)

            oid_field_name = arcpy.Describe(jaringanjalan_path).OIDFieldName
            field_names = [field.name for field in arcpy.ListFields(jaringanjalan_path)]

            if "IdJalan" not in field_names:
                arcpy.management.AddField(jaringanjalan_path, "IdJalan", "LONG")

            if "P_Jalan" not in field_names:
                arcpy.management.AddField(jaringanjalan_path, "P_Jalan", "DOUBLE")

            arcpy.management.CalculateField(
                jaringanjalan_path,
                "P_Jalan",
                "!shape.length!",
                "PYTHON3"
            )

            arcpy.management.CalculateField(
                jaringanjalan_path,
                "IdJalan",
                "!" + oid_field_name + "!",
                "PYTHON3"
            )

            field_names_nd = [field.name for field in arcpy.ListFields(jaringanjalan_nd_path)]

            if "IdJalan" not in field_names_nd:
                arcpy.management.AddField(jaringanjalan_nd_path, "IdJalan", "LONG")

            # =====================================================
            # APPEND DATA & BUILD
            # =====================================================
            messages.addMessage("== Append data jaringan jalan ke ND ==")
            arcpy.management.Append(
                [jaringanjalan_path],
                jaringanjalan_nd_path,
                "NO_TEST"
            )

            messages.addMessage("== Build network dataset ==")
            arcpy.na.BuildNetwork(nd_path)

            # Bersihkan sisa layer temporary di memori jika ada
            delete_layers = ["JaringanJalan_ND", "JaringanJalanForND", "JaringanJalan_ND_Junctions"]
            for lyr in delete_layers:
                if arcpy.Exists(lyr):
                    try:
                        arcpy.management.Delete(lyr)
                    except:
                        pass

            # =====================================================
            # OLAH JUNCTION
            # =====================================================
            messages.addMessage("== Olah junction ==")
            delete_items = [junction_path, junction_diss_path]
            for item in delete_items:
                if arcpy.Exists(item):
                    try:
                        arcpy.management.Delete(item)
                    except:
                        pass

            arcpy.analysis.Intersect(
                [jaringanjalan_path, junction_nd_path],
                junction_path,
                "ALL",
                "",
                "INPUT"
            )

            arcpy.management.Dissolve(
                junction_path,
                junction_diss_path,
                ["FID_JaringanJalan_ND_Junctions"],
                [["FID_Jaringan_Jalan", "COUNT"]],
                "MULTI_PART",
                "DISSOLVE_LINES"
            )

            arcpy.management.MakeFeatureLayer(
                junction_diss_path,
                "temp_jalan",
                "COUNT_FID_Jaringan_Jalan = 1"
            )

            arcpy.management.MakeFeatureLayer(
                junction_path,
                "temp_jalan2"
            )

            arcpy.management.SelectLayerByLocation(
                "temp_jalan2",
                "INTERSECT",
                "temp_jalan",
                selection_type="NEW_SELECTION"
            )

            arcpy.management.DeleteFeatures("temp_jalan2")
            arcpy.management.Delete("temp_jalan")
            arcpy.management.Delete("temp_jalan2")

            # =====================================================
            # JUNCTION FINAL
            # =====================================================
            if arcpy.Exists(junction_final_path):
                try:
                    arcpy.management.Delete(junction_final_path)
                except:
                    pass

            arcpy.management.Dissolve(
                junction_path,
                junction_final_path,
                ["FID_JaringanJalan_ND_Junctions"],
                [
                    ["s_kls_jln", "MAX"],
                    ["lb_jln", "MAX"]
                ],
                "MULTI_PART",
                "DISSOLVE_LINES"
            )

            # =====================================================
            # DATASET KELAS JALAN
            # =====================================================
            messages.addMessage("== Bagi junction berdasarkan kelas jalan ==")
            ds_kelas_jalan = os.path.join(gdb_path, "kelas_jalan")

            if not arcpy.Exists(ds_kelas_jalan):
                arcpy.management.CreateFeatureDataset(
                    gdb_path,
                    "kelas_jalan",
                    arcpy.Describe(jaringanjalan_path).spatialReference
                )

            # =====================================================
            # EXPORT PER KELAS
            # =====================================================
            kelas_configs = [
                (7, "JunctionKls7"),
                (6, "JunctionKls6"),
                (5, "JunctionKls5"),
                (4, "JunctionKls4"),
                (3, "JunctionKls3"),
                (2, "JunctionKls2"),
                (1, "JunctionKls1")
            ]

            for nilai, nama_fc in kelas_configs:
                out_fc = os.path.join(ds_kelas_jalan, nama_fc)
                if arcpy.Exists(out_fc):
                    try:
                        arcpy.management.Delete(out_fc)
                    except:
                        pass

                temp_layer = "temp_" + nama_fc
                where_clause = f"MAX_s_kls_jln = {nilai}"

                arcpy.management.MakeFeatureLayer(
                    junction_final_path,
                    temp_layer,
                    where_clause
                )

                arcpy.management.CopyFeatures(temp_layer, out_fc)
                arcpy.management.Delete(temp_layer)

            # =====================================================
            # CREATE ND LAYER & ADD TO MAP (Di akhir proses)
            # =====================================================
            arcpy.na.MakeNetworkDatasetLayer(nd_path, "JaringanJalan_ND")

            aprx = arcpy.mp.ArcGISProject("CURRENT")
            current_map = aprx.activeMap

            if current_map:
                current_map.addDataFromPath(jaringanjalan_nd_path)
                current_map.addDataFromPath(junction_nd_path)

            # =====================================================
            # OUTPUT PARAMETER
            # =====================================================
            parameters[0].value = nd_path
            parameters[1].value = jaringanjalan_nd_path
            parameters[2].value = junction_nd_path

            messages.addMessage("== Proses selesai ==")
            return

class Tampilkan_Simbologi_Persil(object):

    def __init__(self):

        self.label = "Tampilkan Simbologi Persil"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):

        jenis_simbologi = arcpy.Parameter(
            displayName="Jenis Simbologi",
            name="jenis_simbologi",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )

        jenis_simbologi.filter.list = [
            "Lebar Jalan",
            "Kelas Jalan"
        ]

        jenis_simbologi.value = "Lebar Jalan"

        output_persil = arcpy.Parameter(
            displayName="Output Persil",
            name="output_persil",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        output_jalan = arcpy.Parameter(
            displayName="Output Jaringan Jalan",
            name="output_jalan",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [
            jenis_simbologi,
            output_persil,
            output_jalan
        ]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):

        messages.addMessage("== Proses dimulai ==")

        configs = persil.get_config_values()

        dataset_path = configs["project_config"]["dataset_path"]

        appdata = os.path.dirname(
            os.path.dirname(
                os.path.realpath(__file__)
            )
        )

        jenis_simbologi = parameters[0].valueAsText

        persil_name = "Persil_Layer"
        persil_path = os.path.join(
            dataset_path,
            persil_name
        )

        jalan_name = "Jaringan_Jalan"

        jalan_path = os.path.join(
            dataset_path,
            jalan_name
        )

        # =====================================================
        # PILIH FILE SIMBOLOGI
        # =====================================================

        if jenis_simbologi == "Lebar Jalan":

            sim_persil = os.path.join(
                appdata,
                "SimbologiLebarJalanUpdate2_i3.lyr"
            )

            sim_jalan = r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Simbologi_Lebar_Jaringan_Jalan.lyrx"

            self.update_simbol_lebar_jalan(
                persil_path
            )

            self.update_simbol_lebar_jalan(
                jalan_path
            )

        else:

            sim_persil = os.path.join(
                appdata,
                "SimbologiKelasJalanPersilUpdate.lyrx"
            )

            sim_jalan = os.path.join(
                appdata,
                "SimbologiKelasJalan.lyr"
            )

        # =====================================================
        # REFRESH PERSIL
        # =====================================================

        if arcpy.Exists(persil_name):

            try:
                arcpy.management.Delete(
                    persil_name
                )

            except:
                pass

        arcpy.management.MakeFeatureLayer(
            persil_path,
            persil_name
        )

        if os.path.exists(sim_persil):

            arcpy.management.ApplySymbologyFromLayer(
                persil_name,
                sim_persil
            )

        # =====================================================
        # REFRESH JALAN
        # =====================================================

        if arcpy.Exists(jalan_name):

            try:
                arcpy.management.Delete(
                    jalan_name
                )

            except:
                pass

        arcpy.management.MakeFeatureLayer(
            jalan_path,
            jalan_name
        )

        if os.path.exists(sim_jalan):

            arcpy.management.ApplySymbologyFromLayer(
                jalan_name,
                sim_jalan
            )

        # =====================================================
        # HIDE ND LAYER
        # =====================================================

        try:

            aprx = arcpy.mp.ArcGISProject(
                "CURRENT"
            )

            current_map = aprx.activeMap

            for layer in current_map.listLayers():

                if layer.name == "JaringanJalanForND":
                    layer.visible = False

        except:
            pass

        parameters[1].value = persil_name
        parameters[2].value = jalan_name

        messages.addMessage("== Proses selesai ==")

    # =====================================================
    # FUNCTION
    # =====================================================

    def update_simbol_lebar_jalan(
        self,
        feature_class
    ):

        field_names = [
            field.name
            for field in arcpy.ListFields(feature_class)
        ]

        if "simbologi_jalan" not in field_names:

            arcpy.management.AddField(
                feature_class,
                "simbologi_jalan",
                "TEXT"
            )

        with arcpy.da.UpdateCursor(
            feature_class,
            ["LBRJLN", "simbologi_jalan"]
        ) as rows:

            for row in rows:

                lb_jln = row[0]

                if not lb_jln:
                    row[0] = 0
                    row[1] = "0"

                elif lb_jln > 30:
                    row[0] = 30
                    row[1] = "8+"

                elif lb_jln <= 1.5:
                    row[1] = "1.5"

                elif lb_jln <= 3:
                    row[1] = "3"

                elif lb_jln <= 5:
                    row[1] = "5"

                elif lb_jln <= 8:
                    row[1] = "8"

                else:
                    row[1] = "8+"

                rows.updateRow(row)

class Set_Lebar_Jalan_Persil(object):

    def __init__(self):

        self.label = "Set Lebar Jalan Persil"
        self.description = ""
        self.canRunInBackground = False

    # =====================================================
    # PARAMETER
    # =====================================================

    def getParameterInfo(self):

        lb_jln = arcpy.Parameter(
            displayName="Lebar Jalan",
            name="lb_jln",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input"
        )

        return [lb_jln]

    # =====================================================
    # LICENSE
    # =====================================================

    def isLicensed(self):
        return True

    # =====================================================
    # UPDATE
    # =====================================================

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    # =====================================================
    # HELPER
    # =====================================================

    def get_simbol_lebar_jalan(self, lb_jln):

        if lb_jln is None:
            return "0"

        if lb_jln == 0:
            return "0"

        elif lb_jln <= 1.5:
            return "1.5"

        elif lb_jln <= 3:
            return "3"

        elif lb_jln <= 5:
            return "5"

        elif lb_jln <= 8:
            return "8"

        else:
            return "8+"

    # =====================================================
    # EXECUTE
    # =====================================================

    def execute(self, parameters, messages):

        messages.addMessage("== Proses dimulai ==")

        # =====================================================
        # INPUT
        # =====================================================

        lb_jln = parameters[0].value

        configs = persil.get_config_values()

        dataset_path = configs[
            "project_config"
        ]["dataset_path"]

        persil_layer = "Persil_Layer"

        persil_path = os.path.join(
            dataset_path,
            persil_layer
        )

        # =====================================================
        # VALIDASI FIELD
        # =====================================================

        field_names = [
            f.name
            for f in arcpy.ListFields(
                persil_path
            )
        ]

        if "LBRJLN" not in field_names:

            messages.addErrorMessage(
                "== Field LBRJLN tidak ditemukan =="
            )

            raise arcpy.ExecuteError

        if "simbologi_jalan" not in field_names:

            arcpy.management.AddField(
                persil_path,
                "simbologi_jalan",
                "TEXT"
            )

        # =====================================================
        # VALIDASI SELEKSI
        # =====================================================

        jumlah_terpilih = int(
            arcpy.management.GetCount(
                persil_layer
            )[0]
        )

        if jumlah_terpilih == 0:

            messages.addWarningMessage(
                "== Tidak ada persil yang dipilih =="
            )

            return

        # =====================================================
        # SIMBOLOGI
        # =====================================================

        simbologi_jalan = (
            self.get_simbol_lebar_jalan(
                lb_jln
            )
        )

        # =====================================================
        # UPDATE FEATURE TERPILIH
        # =====================================================

        messages.addMessage(
            "== Update lebar jalan persil =="
        )

        jumlah_update = 0

        with arcpy.da.UpdateCursor(
            persil_layer,
            [
                "LBRJLN",
                "simbologi_jalan"
            ]
        ) as rows:

            for row in rows:

                row[0] = lb_jln
                row[1] = simbologi_jalan

                rows.updateRow(row)

                jumlah_update += 1

        # =====================================================
        # MESSAGE
        # =====================================================

        messages.addMessage(
            "== {} persil berhasil diperbaharui ==".format(
                jumlah_update
            )
        )

        messages.addMessage(
            "== Proses selesai =="
        )

        return
      
class Set_Kelas_Jalan_Persil(object):

    def __init__(self):

        self.label = "Set Kelas Jalan Persil"
        self.description = ""
        self.canRunInBackground = False

    # =====================================================
    # PARAMETER
    # =====================================================

    def getParameterInfo(self):

        kls_jln = arcpy.Parameter(
            displayName="Kelas Jalan",
            name="kls_jln",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )

        kls_jln.filter.list = [
            "Arteri Primer",
            "Arteri Sekunder",
            "Kolektor Primer",
            "Kolektor Sekunder",
            "Lokal Primer",
            "Lokal Sekunder",
            "Setapak"
        ]

        return [kls_jln]

    # =====================================================
    # LICENSE
    # =====================================================

    def isLicensed(self):
        return True

    # =====================================================
    # UPDATE
    # =====================================================

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    # =====================================================
    # EXECUTE
    # =====================================================

    def execute(self, parameters, messages):

        messages.addMessage(
            "== Proses dimulai =="
        )

        # =====================================================
        # INPUT
        # =====================================================

        kls_jln = parameters[0].valueAsText

        configs = persil.get_config_values()

        dataset_path = configs[
            "project_config"
        ]["dataset_path"]

        persil_layer = "Persil_Layer"

        persil_path = os.path.join(
            dataset_path,
            persil_layer
        )

        # =====================================================
        # KELAS JALAN
        # =====================================================

        kelas_jalan_dict = {
            "Arteri Primer": 7,
            "Arteri Sekunder": 6,
            "Kolektor Primer": 5,
            "Kolektor Sekunder": 4,
            "Lokal Primer": 3,
            "Lokal Sekunder": 2,
            "Setapak": 1
        }

        s_kls_jln = kelas_jalan_dict.get(
            kls_jln,
            1
        )

        # =====================================================
        # VALIDASI FIELD
        # =====================================================

        field_names = [
            f.name
            for f in arcpy.ListFields(
                persil_path
            )
        ]

        required_fields = [
            "KLSJLN",
            "S_KLS_JLN"
        ]

        missing_fields = []

        for field_name in required_fields:

            if field_name not in field_names:
                missing_fields.append(
                    field_name
                )

        if len(missing_fields) > 0:

            messages.addErrorMessage(
                "== Field berikut tidak ditemukan: {} ==".format(
                    ", ".join(missing_fields)
                )
            )

            raise arcpy.ExecuteError

        # =====================================================
        # VALIDASI SELEKSI
        # =====================================================

        jumlah_terpilih = int(
            arcpy.management.GetCount(
                persil_layer
            )[0]
        )

        if jumlah_terpilih == 0:

            messages.addWarningMessage(
                "== Tidak ada persil yang dipilih =="
            )

            return

        # =====================================================
        # UPDATE FEATURE TERPILIH
        # =====================================================

        messages.addMessage(
            "== Update kelas jalan persil =="
        )

        jumlah_update = 0

        with arcpy.da.UpdateCursor(
            persil_layer,
            [
                "KLSJLN",
                "S_KLS_JLN"
            ]
        ) as rows:

            for row in rows:

                row[0] = kls_jln
                row[1] = s_kls_jln

                rows.updateRow(row)

                jumlah_update += 1

        # =====================================================
        # MESSAGE
        # =====================================================

        messages.addMessage(
            "== {} persil berhasil diperbaharui ==".format(
                jumlah_update
            )
        )

        messages.addMessage(
            "== Proses selesai =="
        )

        return  
  
