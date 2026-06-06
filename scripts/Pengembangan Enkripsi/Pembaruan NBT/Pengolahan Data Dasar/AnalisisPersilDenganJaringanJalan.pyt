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
                      Sinkronisasi_Kelas_Dan_Lebar_Jalan_Dengan_Persil,
                      Tampilkan_Simbologi_Persil,
                      Perbaharui_Letak_Persil,
                      Perbaharui_Lebar_Depan_Persil,
                      Perbaharui_Jarak_Kelas_Jalan
                      ]


#  Terpilih
class Build_Network_Dataset_Jaringan_Jalan(object):

    def __init__(self):
        self.label = "Build Network Dataset Jaringan Jalan"
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

        junction_nd_path = os.path.join( os.path.dirname(jaringanjalan_nd_path), "JaringanJalan_ND_Junctions")
        junction_diss_path = os.path.join( dataset_path, "junction_diss")
        junction_final_path = os.path.join( dataset_path, "JunctionFinal")

        messages.addMessage( "== Bersih-bersih network dataset ==")

        try:
            arcpy.management.DeleteRows(jaringanjalan_nd_path)

        except:
            pass

        messages.addMessage( "== Validasi kelas jalan =="  )
        temp_jalan = "temp_jalan"

        if arcpy.Exists(temp_jalan ):
            try:
                arcpy.management.Delete( temp_jalan )
            except:
                pass

        kls_jln=arcpy.AddFieldDelimiters(jaringanjalan_path,"kls_jln")
        s_kls_jln=arcpy.AddFieldDelimiters(jaringanjalan_path,"s_kls_jln")

        where_clause=f"{kls_jln} IS NULL OR {s_kls_jln} IS NULL"

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
            arcpy.management.Delete( temp_jalan)

        oid_field_name = arcpy.Describe(jaringanjalan_path).OIDFieldName

        field_names = [
            field.name
            for field in arcpy.ListFields(
                jaringanjalan_path
            )
        ]

        if "IdJalan" not in field_names:
            arcpy.management.AddField(
                jaringanjalan_path,
                "IdJalan",
                "LONG"
            )

        if "P_Jalan" not in field_names:
            arcpy.management.AddField(
                jaringanjalan_path,
                "P_Jalan",
                "DOUBLE"
            )

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

        field_names_nd = [field.name   for field in arcpy.ListFields(jaringanjalan_nd_path)]

        if "IdJalan" not in field_names_nd:
            arcpy.management.AddField(
                jaringanjalan_nd_path,
                "IdJalan",
                "LONG"
            )

        messages.addMessage( "== Append data jaringan jalan ke ND ==" )

        arcpy.management.Append(
            [jaringanjalan_path],
            jaringanjalan_nd_path,
            "NO_TEST"
        )


        messages.addMessage( "== Build network dataset ==" )
        arcpy.na.BuildNetwork(nd_path )

        delete_layers = [
            "JaringanJalan_ND",
            "JaringanJalanForND",
            "JaringanJalan_ND_Junctions"
        ]

        for lyr in delete_layers:
            if arcpy.Exists(lyr):
                try:
                    arcpy.management.Delete( lyr)
                except:
                    pass

        messages.addMessage( "== Olah junction ==" )

        delete_items = [
            junction_path,
            junction_diss_path
        ]

        for item in delete_items:
            if arcpy.Exists(item):
                try:
                    arcpy.management.Delete(item)
                except:
                    pass

        arcpy.analysis.Intersect([jaringanjalan_path, junction_nd_path],
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

        arcpy.management.DeleteFeatures(
            "temp_jalan2"
        )

        arcpy.management.Delete(
            "temp_jalan"
        )

        arcpy.management.Delete(
            "temp_jalan2"
        )

        # =====================================================
        # JUNCTION FINAL
        # =====================================================

        if arcpy.Exists(
            junction_final_path
        ):

            try:
                arcpy.management.Delete(
                    junction_final_path
                )
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

        messages.addMessage(
            "== Bagi junction berdasarkan kelas jalan =="
        )

        ds_kelas_jalan = os.path.join(
            gdb_path,
            "kelas_jalan"
        )

        if not arcpy.Exists(
            ds_kelas_jalan
        ):

            arcpy.management.CreateFeatureDataset(
                gdb_path,
                "kelas_jalan",
                arcpy.Describe(
                    jaringanjalan_path
                ).spatialReference
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

            out_fc = os.path.join(
                ds_kelas_jalan,
                nama_fc
            )

            if arcpy.Exists(
                out_fc
            ):

                try:
                    arcpy.management.Delete(
                        out_fc
                    )
                except:
                    pass

            temp_layer = (
                "temp_" + nama_fc
            )

            where_clause = (
                "MAX_s_kls_jln = {}".format(
                    nilai
                )
            )

            arcpy.management.MakeFeatureLayer(
                junction_final_path,
                temp_layer,
                where_clause
            )

            arcpy.management.CopyFeatures(
                temp_layer,
                out_fc
            )

            arcpy.management.Delete(
                temp_layer
            )

        # =====================================================
        # CREATE ND LAYER
        # =====================================================

        arcpy.na.MakeNetworkDatasetLayer(
            nd_path,
            "JaringanJalan_ND"
        )

        # =====================================================
        # ADD TO CURRENT MAP
        # =====================================================

        aprx = arcpy.mp.ArcGISProject(
            "CURRENT"
        )

        current_map = aprx.activeMap

        current_map.addDataFromPath(
            jaringanjalan_nd_path
        )

        current_map.addDataFromPath(
            junction_nd_path
        )

        # =====================================================
        # OUTPUT PARAMETER
        # =====================================================

        parameters[0].value = (
            nd_path
        )

        parameters[1].value = (
            jaringanjalan_nd_path
        )

        parameters[2].value = (
            junction_nd_path
        )

        messages.addMessage(
            "== Proses selesai =="
        )

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

class Perbaharui_Letak_Persil(object):

    def __init__(self):
        self.label="Perbaharui Letak Persil"
        self.description=""
        self.canRunInBackground=False

    def getParameterInfo(self):

        radius = arcpy.Parameter(
            displayName="Radius Near",
            name="near_radius",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input"
        )
        radius.value = 200

        simpan_temp = arcpy.Parameter(
            displayName="Simpan ke Temporary Layer",
            name="simpan_temp",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )
        simpan_temp.value = False

        hanya_update = arcpy.Parameter(
            displayName="Sinkronisasi Data Persil Terbaru",
            name="hanya_update",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )
        hanya_update.value = True

        output = arcpy.Parameter(
            displayName="Output Persil",
            name="output_persil",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [
            radius,
            simpan_temp,
            hanya_update,
            output
        ]

    def isLicensed(self):
        return True

    def updateParameters(self,parameters):
        return

    def updateMessages(self,parameters):
        return

    def delete_if_exists(self,path):

        if arcpy.Exists(path):

            try: arcpy.management.Delete(path)
            except: pass

    def add_field_if_not_exists(self,fc,name,typ):

        fields=[f.name for f in arcpy.ListFields(fc)]

        if name not in fields:
            arcpy.management.AddField(fc,name,typ)

    def execute(self,parameters,messages):

        messages.addMessage("== Proses dimulai ==")
        near_radius = parameters[0].valueAsText or "200"

        simpan_temp = parameters[1].value
        hanya_update = parameters[2].value

        configs = persil.get_config_values()
        dataset_path = configs['project_config']['dataset_path']
        gdb_path = configs['project_config']['gdb_path']
        network_analysis_template_folder = os.path.join(gdb_path, 'ds_znt_template')


        persil_path= os.path.join(dataset_path, 'Persil_Layer')
        temp_output_name = "Analisis_Persil_Dengan_Jalan_Temp"

        temp_output_path = os.path.join(
            dataset_path,
            temp_output_name
        )

        if simpan_temp:

            self.delete_if_exists(
                temp_output_path
            )

            messages.addMessage(
                "== Membuat temporary layer =="
            )

            arcpy.management.CopyFeatures(
                persil_path,
                temp_output_path
            )

            update_fc = temp_output_path

        else:

            update_fc = persil_path
        persil_input = "persil_input"

        if arcpy.Exists(persil_input):

            self.delete_if_exists(
                persil_input
            )

        arcpy.management.MakeFeatureLayer(
            update_fc,
            persil_input
        )
        if hanya_update:
            messages.addMessage(
                "== Seleksi status_per='update' =="
            )

            arcpy.management.SelectLayerByAttribute(
                persil_input,
                "NEW_SELECTION",
                "UPPER(status_per) = 'UPDATE'"
            )
        jalan=os.path.join(dataset_path, 'Jaringan_Jalan')
        junction=os.path.join(network_analysis_template_folder, 'JaringanJalan_ND_Junctions')
        field_id='IdBidang'

        field_letak='LETAK'
        field_s_letak='S_LETAK'

        field_lb_jln='LBRJLN'
        field_s_kls_jln='S_KLS_JLN'
        field_lb_dpn='LBRDPN'


        split=os.path.join("in_memory","split")
        midpoint=os.path.join("in_memory","midpoint")
        line=os.path.join("in_memory","line")
        join=os.path.join("in_memory","join")
        erase=os.path.join("in_memory","erase")
        normal=os.path.join("in_memory","normal")
        normal_mid=os.path.join("in_memory","normal_mid")
        normal_diss=os.path.join("in_memory","normal_diss")
        hook=os.path.join("in_memory","hook")

        messages.addMessage("== Persiapan jalan ==")

        self.add_field_if_not_exists(
            jalan,
            "IdJalan",
            "LONG"
        )

        oid=arcpy.Describe(jalan).OIDFieldName

        arcpy.management.CalculateField(
            jalan,
            "IdJalan",
            f"!{oid}!",
            "PYTHON3"
        )

        messages.addMessage("== Split bidang ==")

        arcpy.management.PolygonToLine(
            persil_input,
            line,
            "IGNORE_NEIGHBORS"
        )

        arcpy.management.SplitLine(
            line,
            split
        )

        self.add_field_if_not_exists(
            split,
            "LebarSisi",
            "DOUBLE"
        )

        arcpy.management.CalculateField(
            split,
            "LebarSisi",
            "!shape.length!",
            "PYTHON3"
        )

        messages.addMessage("== Midpoint ==")

        arcpy.management.FeatureToPoint(
            split,
            midpoint,
            "INSIDE"
        )

        self.add_field_if_not_exists(
            midpoint,
            "X",
            "DOUBLE"
        )

        self.add_field_if_not_exists(
            midpoint,
            "Y",
            "DOUBLE"
        )

        arcpy.management.CalculateField(
            midpoint,
            "X",
            "!Shape.firstPoint.X!",
            "PYTHON3"
        )

        arcpy.management.CalculateField(
            midpoint,
            "Y",
            "!Shape.firstPoint.Y!",
            "PYTHON3"
        )

        messages.addMessage("== Near jalan ==")

        arcpy.analysis.Near(
            midpoint,
            jalan,
            f"{near_radius} Meters",
            "LOCATION",
            "ANGLE"
        )

        self.add_field_if_not_exists(
            midpoint,
            "IdJoin",
            "LONG"
        )

        oid_mid=arcpy.Describe(midpoint).OIDFieldName

        arcpy.management.CalculateField(
            midpoint,
            "IdJoin",
            f"!{oid_mid}!",
            "PYTHON3"
        )

        sr=arcpy.Describe(midpoint).spatialReference

        arcpy.management.XYToLine(
            midpoint,
            line,
            "X",
            "Y",
            "NEAR_X",
            "NEAR_Y",
            "GEODESIC",
            "IdJoin",
            sr
        )

        arcpy.management.JoinField(
            line,
            "IdJoin",
            midpoint,
            "IdJoin",
            [field_id,"LebarSisi"]
        )

        arcpy.analysis.SpatialJoin(
            line,
            jalan,
            join,
            "JOIN_ONE_TO_ONE",
            "KEEP_ALL",
            match_option="INTERSECT"
        )

        self.add_field_if_not_exists(
            join,
            "PanjangNearLine",
            "DOUBLE"
        )

        arcpy.management.CalculateField(
            join,
            "PanjangNearLine",
            "!shape.length!",
            "PYTHON3"
        )

        messages.addMessage("== Erase ==")

        arcpy.analysis.Erase(
            join,
            persil_input,
            erase
        )

        self.add_field_if_not_exists(
            erase,
            "PanjangErase",
            "DOUBLE"
        )

        self.add_field_if_not_exists(
            erase,
            "Pengurangan",
            "DOUBLE"
        )

        arcpy.management.CalculateField(
            erase,
            "PanjangErase",
            "!shape.length!",
            "PYTHON3"
        )

        arcpy.management.CalculateField(
            erase,
            "Pengurangan",
            "!PanjangErase! - !PanjangNearLine!",
            "PYTHON3"
        )

        self.add_field_if_not_exists(
            erase,
            "letak_tmp",
            "TEXT"
        )

        exp="""get(!Pengurangan!)"""

        code="""
def get(v):

    if v < -0.1:
        return 'Lain-lain'

    return 'Pinggir Jalan'
"""

        arcpy.management.CalculateField(
            erase,
            "letak_tmp",
            exp,
            "PYTHON3",
            code
        )

        messages.addMessage("== Dissolve jalan ==")

        diss=os.path.join("in_memory","diss")

        arcpy.management.Dissolve(
            join,
            diss,
            [field_id,"IdJalan"],
            [["LebarSisi","SUM"],[field_s_kls_jln,"MAX"]],
            "MULTI_PART",
            "DISSOLVE_LINES"
        )

        diss2=os.path.join("in_memory","diss2")

        arcpy.management.Dissolve(
            diss,
            diss2,
            [field_id],
            [["IdJalan","COUNT"],["SUM_LebarSisi","SUM"],[f"MAX_{field_s_kls_jln}","MAX"]],
            "MULTI_PART",
            "DISSOLVE_LINES"
        )

        join_dict={}

        with arcpy.da.SearchCursor(
            erase,
            [field_id,"letak_tmp"]
        ) as rows:

            for row in rows:
                join_dict[row[0]]=row[1]

        jalan_dict={}

        with arcpy.da.SearchCursor(
            diss2,
            [
                field_id,
                "COUNT_IdJalan",
                "SUM_SUM_LebarSisi",
                f"MAX_MAX_{field_s_kls_jln}"
            ]
        ) as rows:

            for row in rows:

                jalan_dict[row[0]]={
                    "count_jalan":row[1],
                    "lb_dpn":row[2],
                    "s_kls_jln":row[3]
                }

        messages.addMessage("== Update awal ==")

        with arcpy.da.UpdateCursor(
            persil_input,
            [
                field_id,
                field_letak,
                field_s_letak,
                field_lb_dpn
            ]
        ) as rows:

            for row in rows:

                idbid=row[0]

                letak="Pinggir Jalan"
                skor=0
                lb_dpn=0

                if idbid in join_dict:
                    letak=join_dict[idbid]

                if idbid in jalan_dict:
                    lb_dpn=jalan_dict[idbid]["lb_dpn"]

                if letak=="Lain-lain":
                    skor=1

                elif idbid in jalan_dict:

                    if jalan_dict[idbid]["count_jalan"]>1:
                        letak="Hook"
                        skor=4

                    else:
                        letak="Normal"
                        skor=3

                row[1]=letak
                row[2]=skor
                row[3]=lb_dpn

                rows.updateRow(row)

        messages.addMessage("== Analisis tusuk sate ==")

        arcpy.management.MakeFeatureLayer(
            persil_input,
            "normal_lyr",
            f"{field_letak}='Normal'"
        )

        arcpy.management.CopyFeatures(
            "normal_lyr",
            normal
        )

        arcpy.management.FeatureToPoint(
            normal,
            normal_mid,
            "INSIDE"
        )

        arcpy.analysis.Near(
            normal_mid,
            junction,
            "100",
            "LOCATION"
        )

        self.add_field_if_not_exists(
            normal_mid,
            "P_Line",
            "DOUBLE"
        )

        arcpy.management.CalculateField(
            normal_mid,
            "P_Line",
            "!NEAR_DIST!",
            "PYTHON3"
        )

        arcpy.analysis.SpatialJoin(
            normal_mid,
            split,
            normal_diss,
            "JOIN_ONE_TO_ONE",
            "KEEP_ALL",
            match_option="INTERSECT"
        )

        tusuk_dict={}

        with arcpy.da.SearchCursor(
            normal_diss,
            [field_id,"P_Line","LebarSisi"]
        ) as rows:

            for row in rows:

                if row[1] is None or row[2] is None:
                    continue

                if row[1] < row[2]:
                    tusuk_dict[row[0]]="Tusuk Sate"

        with arcpy.da.UpdateCursor(
            persil_input,
            [
                field_id,
                field_letak,
                field_s_letak
            ]
        ) as rows:

            for row in rows:

                idbid=row[0]

                if idbid in tusuk_dict:

                    row[1]="Tusuk Sate"
                    row[2]=2

                    rows.updateRow(row)

        messages.addMessage("== Finalisasi ==")
        if simpan_temp:
            output_name = temp_output_name
        else:
            output_name = "Persil_Layer"

        if arcpy.Exists(output_name):

            try:
                arcpy.management.Delete(
                    output_name
                )

            except:
                pass

        arcpy.management.MakeFeatureLayer(
            update_fc,
            output_name
        )

        parameters[3].value = output_name

        messages.addMessage("== Proses selesai ==")

        return
    
class Perbaharui_Lebar_Depan_Persil(object):

    def __init__(self):

        self.label = "Perbaharui Lebar Depan Persil"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):

        radius = arcpy.Parameter(
            displayName="Radius Near",
            name="near_radius",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input"
        )
        radius.value = 30

        simpan_temp=arcpy.Parameter(
            displayName="Simpan ke Layer Temporary",
            name="simpan_temp",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )
        simpan_temp.value=False

        hanya_kosong=arcpy.Parameter(
            displayName="Perbaharui yang bernilai 0 saja",
            name="hanya_kosong",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )
        hanya_kosong.value=False


        hanya_update=arcpy.Parameter(
            displayName="Sinkronisasi Data Persil Terbaru",
            name="hanya_update",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )
        hanya_update.value=True

        output = arcpy.Parameter(
            displayName="Output Persil",
            name="output_persil",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [
            radius,
            simpan_temp,
            hanya_kosong,
            hanya_update,
            output
        ]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def delete_if_exists(self, path):
        if arcpy.Exists(path):
            try:
                arcpy.management.Delete(path)
            except:
                pass

    def add_field_if_not_exists(
        self,
        fc,
        name,
        typ
    ):

        fields = [
            f.name
            for f in arcpy.ListFields(fc)
        ]

        if name not in fields:

            arcpy.management.AddField(
                fc,
                name,
                typ
            )

    def remove_field_if_exists(
        self,
        fc,
        name
    ):

        fields = [
            f.name
            for f in arcpy.ListFields(fc)
        ]

        if name in fields:

            arcpy.management.DeleteField(
                fc,
                name
            )

    def execute(self, parameters, messages):

        messages.addMessage("== Proses dimulai ==")

        # 1. Mengambil Konfigurasi dari config file

        configs = persil.get_config_values()
        dataset_path = configs['project_config']['dataset_path']

        # 2. Mengambil nilai parameter
        near_radius = parameters[0].valueAsText       
        simpan_temp = parameters[1].value
        hanya_kosong = parameters[2].value
        hanya_update = parameters[3].value

        # 3. Mempersiapkan path untuk dataset dan output sementara
        gdb_path = arcpy.env.scratchGDB

        field_id = 'IDBIDANG'
        field_kelas = 's_kls_jln'
        field_lebar = 'lb_jln'
        field_lb_dpn = 'LBRDPN'

        persil_fc = os.path.join(dataset_path, 'Persil_Layer')
        jalan = os.path.join(dataset_path,"Jaringan_Jalan")

        temp_output_name = "Analisis_Persil_Dengan_Jalan_Temp"
        gdb_path=arcpy.env.scratchGDB        
        temp_output_fc = os.path.join(dataset_path, temp_output_name )
        line = os.path.join("in_memory", "persil_line")
        split = os.path.join("in_memory", "persil_split")
        midpoint = os.path.join( gdb_path, "midpoint")


        # 4. Membuat layer sementara jika opsi simpan_temp diaktifkan, jika tidak maka langsung menggunakan feature class persil_fc untuk diupdate
        if simpan_temp:
            self.delete_if_exists(temp_output_fc)
            messages.addMessage("== Membuat temporary layer ==")
            arcpy.management.CopyFeatures(persil_fc, temp_output_fc )
            update_fc = temp_output_fc
        else:
            update_fc = persil_fc

        #  5. Mempersiapkan feeature layer yang akan diolah, jika opsi hanya_update diaktifkan maka dilakukan seleksi terlebih dahulu untuk mengambil data persil yang berstatus update saja

        persil_layer = "persil_input"
        self.delete_if_exists(persil_layer)
        arcpy.management.MakeFeatureLayer(update_fc, persil_layer )

        if hanya_update:
            messages.addMessage( "== Seleksi status_per='update' ==" )
            arcpy.management.SelectLayerByAttribute(
                persil_layer,
                "NEW_SELECTION",
                "UPPER(status_per) = 'UPDATE'"
            )
        
        if hanya_kosong:
            # Tambahan: hanya proses data yang belum memiliki lebar jalan
            messages.addMessage("== Seleksi persil yang belum tersinkronisasi ==")

            selection_type = (
                "SUBSET_SELECTION"
                if hanya_update
                else "NEW_SELECTION"
            )

            arcpy.management.SelectLayerByAttribute(
                persil_layer,
                selection_type,
                "(LBRDPN IS NULL OR LBRDPN = 0)"
            )

        # 6. Validasi jumlah data yang akan diproses, jika tidak ada maka proses dihentikan

        jumlah = int(arcpy.management.GetCount(persil_layer)[0])
        if jumlah == 0:
            messages.addWarningMessage("== Tidak ada feature yang diproses ==")
            return

        #  7. Mempersiapkan IdJalan

        self.add_field_if_not_exists(jalan, "IdJalan", "LONG")
        oid_jalan = arcpy.Describe(jalan).OIDFieldName
        arcpy.management.CalculateField(
            jalan,
            "IdJalan",
            f"!{oid_jalan}!",
            "PYTHON3"
        )

        # 8. Mengubah polygon persil menjadi garis, kemudian memecah garis menjadi sisi-sisi, dan menghitung panjang sisi
        messages.addMessage("== Polygon to line ==")
        self.delete_if_exists(line)
        arcpy.management.PolygonToLine(
            persil_layer,
            line,
            "IGNORE_NEIGHBORS"
        )
        self.delete_if_exists(split)
        arcpy.management.SplitLine(
            line,
            split
        )
        self.add_field_if_not_exists(
            split,
            "LebarSisi",
            "DOUBLE"
        )
        arcpy.management.CalculateField(
            split,
            "LebarSisi",
            "!shape.length!",
            "PYTHON3"
        )
        # 9. Menghitung titik tengah dari setiap sisi, dan menambahkan field X dan Y untuk menyimpan koordinat titik tengah

        messages.addMessage("== Midpoint sisi ==")
        self.delete_if_exists(midpoint)

        arcpy.management.FeatureToPoint(split, midpoint, "INSIDE")

        self.add_field_if_not_exists(
            midpoint,
            "X",
            "DOUBLE"
        )

        self.add_field_if_not_exists(
            midpoint,
            "Y",
            "DOUBLE"
        )

        arcpy.management.CalculateField(
            midpoint,
            "X",
            "!Shape.firstPoint.X!",
            "PYTHON3"
        )

        arcpy.management.CalculateField(
            midpoint,
            "Y",
            "!Shape.firstPoint.Y!",
            "PYTHON3"
        )


        # 10. Melakukan Analisis Near dari titik tengah sisi ke jaringan jalan dengan radius yang ditentukan, dan menyimpan jarak, FID jalan terdekat, koordinat X dan Y jalan terdekat, serta sudut antara sisi dengan jalan terdekat

        messages.addMessage("== Analisis Jalan Terdekat ==")

        arcpy.analysis.Near(
            midpoint,
            jalan,
            f"{near_radius} Meters",
            "LOCATION",
            "ANGLE"
        )

        self.add_field_if_not_exists(
            midpoint,
            "IdJoin",
            "LONG"
        )

        oid_mid = arcpy.Describe(midpoint).OIDFieldName
        arcpy.management.CalculateField(
            midpoint,
            "IdJoin",
            f"!{oid_mid}!",
            "PYTHON3"
        )

        sr = arcpy.Describe(midpoint).spatialReference
        
        #  11. Melakukan Join_Field untuk menggabungkan informasi kelas jalan dan lebar jalan dari layer jalan ke layer midpoint berdasarkan FID jalan terdekat yang disimpan di field NEAR_FID
        for fld in [field_kelas, field_lebar]:
            self.remove_field_if_exists(midpoint,fld)

        arcpy.management.JoinField(
            midpoint,
            "NEAR_FID",
            jalan,
            oid_jalan,
            [field_kelas, field_lebar]
        )

        # 12. Dilakukan Filter Jalan Terbaik dimana jalan dengan kelas yang lebih tinggi dianggap sebagai jalan depan
        messages.addMessage("== Seleksi frontage terbaik ==")
        kandidat_dict = {}

        with arcpy.da.SearchCursor(
            midpoint,
            [
                field_id,
                field_kelas,
                field_lebar,
                "LebarSisi",
                "NEAR_DIST",
                "NEAR_FID"
            ]
        ) as rows:
            for row in rows:

                idbid = row[0]
                kelas = row[1]
                lb_jln = row[2]
                lb_sisi = row[3]
                near = row[4]
                near_fid = row[5]

                if near_fid == -1:
                    continue

                if near is None:
                    continue

                try:
                    kelas = float(kelas)
                except:
                    kelas = 0

                try:
                    lb_jln = float(lb_jln)
                except:
                    lb_jln = 0

                try:
                    lb_sisi = float(lb_sisi)
                except:
                    lb_sisi = 0

                # NEED REVIEW: Apakah logika scoring sudah benar? Apakah bobot kelas jalan sudah sesuai dengan kebutuhan? Apakah perlu menambahkan faktor lain dalam scoring seperti sudut antara sisi dengan jalan terdekat?
                score = (kelas * 1000000)  + (lb_jln * 1000) - near
                kandidat = [score, kelas,  lb_jln,  near, lb_sisi ]

                if idbid not in kandidat_dict:
                    kandidat_dict[idbid] = kandidat

                else:
                    if kandidat[0] > kandidat_dict[idbid][0]:
                        kandidat_dict[idbid] = kandidat
        count = 0
        for idbid, kandidat in kandidat_dict.items():
            if count < 10:
                count += 1
                messages.addMessage(f"IdBidang: {idbid}, Score: {kandidat[0]}, Kelas: {kandidat[1]}, Lebar Jalan: {kandidat[2]}, Jarak Near: {kandidat[3]}, Lebar Sisi: {kandidat[4]}")
            else:
                break

        # 13. Update field lebar depan di layer persil dengan nilai lebar jalan dari kandidat terbaik yang sudah dipilih
        
        messages.addMessage( "== Perbaharui Lebar Depan ==")

        with arcpy.da.UpdateCursor(
            persil_layer,
            [
                field_id,
                field_lb_dpn,
            ]
        ) as rows:
            for row in rows:
                idbid = row[0]
                lb_dpn = 0
                if idbid in kandidat_dict:
                    lb_dpn = kandidat_dict[idbid][4]
                row[1] = lb_dpn

                rows.updateRow(row)

        # 14. Menampilkan output, jika opsi simpan_temp diaktifkan maka akan menampilkan layer sementara, jika tidak maka akan menampilkan layer persil yang sudah diupdate

        if simpan_temp:
            output_name = temp_output_name
        else:
            output_name = "Persil_Layer"

        self.delete_if_exists(
            output_name
        )

        arcpy.management.MakeFeatureLayer(
            update_fc,
            output_name
        )

        parameters[4].value = output_name

        messages.addMessage(
            "== Proses selesai =="
        )

        return

class Sinkronisasi_Kelas_Dan_Lebar_Jalan_Dengan_Persil(object):

    def __init__(self):
        self.label="Sinkronisasi Kelas dan Lebar Jalan"
        self.description=""
        self.canRunInBackground=False

    def getParameterInfo(self):
        simpan_temp=arcpy.Parameter(
            displayName="Simpan ke Layer Temporary",
            name="simpan_temp",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )
        simpan_temp.value=False

        hanya_lebar=arcpy.Parameter(
            displayName="Perbaharui nilai lebar saja",
            name="hanya_lebar",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )
        hanya_lebar.value=False

        hanya_kosong=arcpy.Parameter(
            displayName="Perbaharui yang bernilai 0 saja",
            name="hanya_kosong",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )
        hanya_kosong.value=False


        hanya_update=arcpy.Parameter(
            displayName="Sinkronisasi Data Persil Terbaru",
            name="hanya_update",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )
        hanya_update.value=True


        radius=arcpy.Parameter(
            displayName="Jarak Pencarian (meter)",
            name="search_radius",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input"
        )
        radius.value=30
    
        output=arcpy.Parameter(
            displayName="Output Persil",
            name="output_persil",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [
            radius,
            simpan_temp,
            hanya_lebar,
            hanya_kosong,
            hanya_update,
            output
        ]

    def isLicensed(self):
        return True

    def updateParameters(self,parameters):
        return

    def updateMessages(self,parameters):
        return

    def execute(self,parameters,messages):

        messages.addMessage("== Proses dimulai ==")
        # 1. Mengambil Konfigurasi dari config file

        configs = persil.get_config_values()
        dataset_path = configs['project_config']['dataset_path']

        # 2. Mengambil nilai parameter
        near_radius = parameters[0].valueAsText or "30"          
        simpan_temp = parameters[1].value
        hanya_lebar = parameters[2].value
        hanya_kosong = parameters[3].value
        hanya_update = parameters[4].value


        # 3. Mempersiapkan path untuk dataset dan output sementara
        gdb_path = arcpy.env.scratchGDB

        field_id = 'IDBIDANG'
        field_kelas_sumber='kls_jln'
        field_lebar_sumber='lb_jln'
        field_skor_kelas_sumber='s_kls_jln'

        field_target_kelas_nilai='S_KLS_JLN'
        field_target_kelas_nama='KLSJLN'
        field_target_lebar='LBRJLN'

        persil_fc = os.path.join(dataset_path, 'Persil_Layer')
        jalan = os.path.join(dataset_path,"Jaringan_Jalan")

        gdb_temp = arcpy.env.scratchGDB

        temp_output_name = "Analisis_Persil_Dengan_Jalan_Temp"        
        temp_output_fc = os.path.join(dataset_path, temp_output_name )
        line = os.path.join("in_memory", "persil_line")
        split = os.path.join("in_memory", "persil_split")
        midpoint = os.path.join( gdb_temp, "midpoint")

        # 4. Membuat layer sementara jika opsi simpan_temp diaktifkan, jika tidak maka langsung menggunakan feature class persil_fc untuk diupdate
        if simpan_temp:
            self.delete_if_exists(temp_output_fc)
            messages.addMessage("== Membuat temporary layer ==")
            arcpy.management.CopyFeatures(persil_fc, temp_output_fc )
            update_fc = temp_output_fc
        else:
            update_fc = persil_fc

        #  5. Mempersiapkan feeature layer yang akan diolah, jika opsi hanya_update diaktifkan maka dilakukan seleksi terlebih dahulu untuk mengambil data persil yang berstatus update saja
        persil_layer = "persil_input"
        self.delete_if_exists(persil_layer)
        arcpy.management.MakeFeatureLayer(update_fc, persil_layer )

        if hanya_update:
            messages.addMessage( "== Seleksi status_per='update' ==" )
            arcpy.management.SelectLayerByAttribute(
                persil_layer,
                "NEW_SELECTION",
                "UPPER(status_per) = 'UPDATE'"
            )

        if hanya_kosong:
            # Tambahan: hanya proses data yang belum memiliki lebar jalan
            messages.addMessage("== Seleksi persil yang belum tersinkronisasi ==")

            selection_type = (
                "SUBSET_SELECTION"
                if hanya_update
                else "NEW_SELECTION"
            )

            arcpy.management.SelectLayerByAttribute(
                persil_layer,
                selection_type,
                "(LBRJLN IS NULL OR LBRJLN = 0)"
            )


        # 6. Validasi jumlah data yang akan diproses, jika tidak ada maka proses dihentikan

        jumlah = int(arcpy.management.GetCount(persil_layer)[0])
        if jumlah == 0:
            messages.addWarningMessage("== Tidak ada feature yang diproses ==")
            return

        messages.addMessage("== Membuat titik tengah persil ==")

        #  7. Mempersiapkan IdJalan

        self.add_field_if_not_exists(jalan, "IdJalan", "LONG")
        oid_jalan = arcpy.Describe(jalan).OIDFieldName
        arcpy.management.CalculateField(
            jalan,
            "IdJalan",
            f"!{oid_jalan}!",
            "PYTHON3"
        )

        # 8. Mengubah polygon persil menjadi garis, kemudian memecah garis menjadi sisi-sisi, dan menghitung panjang sisi
        messages.addMessage("== Polygon to line ==")
        self.delete_if_exists(line)
        arcpy.management.PolygonToLine(
            persil_layer,
            line,
            "IGNORE_NEIGHBORS"
        )
        self.delete_if_exists(split)
        arcpy.management.SplitLine(
            line,
            split
        )

        # 9. Menghitung titik tengah dari setiap sisi, dan menambahkan field X dan Y untuk menyimpan koordinat titik tengah

        messages.addMessage("== Midpoint sisi ==")
        self.delete_if_exists(midpoint)

        arcpy.management.FeatureToPoint(split, midpoint, "INSIDE")

        self.add_field_if_not_exists(
            midpoint,
            "X",
            "DOUBLE"
        )

        self.add_field_if_not_exists(
            midpoint,
            "Y",
            "DOUBLE"
        )

        arcpy.management.CalculateField(
            midpoint,
            "X",
            "!Shape.firstPoint.X!",
            "PYTHON3"
        )

        arcpy.management.CalculateField(
            midpoint,
            "Y",
            "!Shape.firstPoint.Y!",
            "PYTHON3"
        )

        # 10. Melakukan Analisis Near dari titik tengah sisi ke jaringan jalan dengan radius yang ditentukan, dan menyimpan jarak, FID jalan terdekat, koordinat X dan Y jalan terdekat, serta sudut antara sisi dengan jalan terdekat

        messages.addMessage("== Analisis Jalan Terdekat ==")

        arcpy.analysis.Near(
            midpoint,
            jalan,
            f"{near_radius} Meters",
            "LOCATION",
            "ANGLE"
        )

        self.add_field_if_not_exists(
            midpoint,
            "IdJoin",
            "LONG"
        )

        oid_mid = arcpy.Describe(midpoint).OIDFieldName
        arcpy.management.CalculateField(
            midpoint,
            "IdJoin",
            f"!{oid_mid}!",
            "PYTHON3"
        )

        sr = arcpy.Describe(midpoint).spatialReference

        #  11. Melakukan Join_Field untuk menggabungkan informasi kelas jalan dan lebar jalan dari layer jalan ke layer midpoint berdasarkan FID jalan terdekat yang disimpan di field NEAR_FID
        for fld in [field_kelas_sumber, field_lebar_sumber]:
            self.remove_field_if_exists(midpoint,fld)

        arcpy.management.JoinField(
            midpoint,
            "NEAR_FID",
            jalan,
            oid_jalan,
            [field_kelas_sumber, field_lebar_sumber]
        )


        # 12. Dilakukan Filter Jalan Terbaik dimana jalan dengan kelas yang lebih tinggi dianggap sebagai jalan depan
        messages.addMessage("== Seleksi frontage terbaik ==")
        mapping_kelas_jalan_ke_skoring = {
            "Arteri Primer": 7,
            "Arteri Sekunder": 6,
            "Kolektor Primer": 5,
            "Kolektor Sekunder": 4,
            "Lokal Primer": 3,
            "Lokal Sekunder": 2,
            "Setapak": 1
        }
        kandidat_dict = {}

        with arcpy.da.SearchCursor(
            midpoint,
            [
                field_id,
                field_kelas_sumber,
                field_lebar_sumber,
                "NEAR_DIST",
                "NEAR_FID"
            ]
        ) as rows:
            for row in rows:

                idbid = row[0]
                kelas = row[1]

                skor_kelas = mapping_kelas_jalan_ke_skoring.get(kelas, 0) if kelas is not None else 0
                lb_jln = row[2]
                near = row[3]
                near_fid = row[4]

                if near_fid == -1:
                    continue

                if near is None:
                    continue

                try:
                    skor_kelas = float(skor_kelas)
                except:
                    skor_kelas = 0

                try:
                    lb_jln = float(lb_jln)
                except:
                    lb_jln = 0

                # NEED REVIEW: Apakah logika scoring sudah benar? Apakah bobot kelas jalan sudah sesuai dengan kebutuhan? Apakah perlu menambahkan faktor lain dalam scoring seperti sudut antara sisi dengan jalan terdekat?
                score = (skor_kelas * 1000000)  + (lb_jln * 1000) - near
                kandidat = [score, skor_kelas,  lb_jln,  near ]

                if idbid not in kandidat_dict:
                    kandidat_dict[idbid] = kandidat

                else:
                    if kandidat[0] > kandidat_dict[idbid][0]:
                        kandidat_dict[idbid] = kandidat
        count = 0
        for idbid, kandidat in kandidat_dict.items():
            if count < 10:
                count += 1
                messages.addMessage(f"IdBidang: {idbid}, Score: {kandidat[0]}, Skor Kelas: {kandidat[1]}, Lebar Jalan: {kandidat[2]}, Jarak Near: {kandidat[3]}")
            else:
                break

        # 13. Update field lebar jalan dan kelas jalan di layer persil dengan nilai lebar jalan dari kandidat terbaik yang sudah dipilih
        
        messages.addMessage( "== Perbaharui Kelas dan Lebar Jalan ==")

        mapping_kelas_jalan={
            7:"Arteri Primer",
            6:"Arteri Sekunder",
            5:"Kolektor Primer",
            4:"Kolektor Sekunder",
            3:"Lokal Primer",
            2:"Lokal Sekunder",
            1:"Setapak"
        }
        with arcpy.da.UpdateCursor(
            persil_layer,
            [
                field_id,
                field_target_lebar,
                field_target_kelas_nama,
                field_target_kelas_nilai,
            ]
        ) as rows:
            for row in rows:
                idbid = row[0]
                lbrjln = 0
                klsjln = ""
                skoring_kelas = 0
                if idbid in kandidat_dict:
                    lbrjln = kandidat_dict[idbid][2]
                    skoring_kelas = kandidat_dict[idbid][1]
                    klsjln = mapping_kelas_jalan[skoring_kelas] if skoring_kelas in mapping_kelas_jalan else "Tidak Diketahui"
                row[1] = lbrjln
                if not hanya_lebar:
                    row[2] = klsjln
                    row[3] = skoring_kelas

                rows.updateRow(row)

        # 14. Menampilkan output, jika opsi simpan_temp diaktifkan maka akan menampilkan layer sementara, jika tidak maka akan menampilkan layer persil yang sudah diupdate

        if simpan_temp:
            output_name = temp_output_name
        else:
            output_name = "Persil_Layer"

        self.delete_if_exists(
            output_name
        )

        arcpy.management.MakeFeatureLayer(
            update_fc,
            output_name
        )

        parameters[5].value = output_name

        messages.addMessage(
            "== Proses selesai =="
        )

        return
    
    def delete_if_exists(self, path):
        if arcpy.Exists(path):
            try:
                arcpy.management.Delete(path)
            except:
                pass

    def add_field_if_not_exists(
        self,
        fc,
        name,
        typ
    ):

        fields = [
            f.name
            for f in arcpy.ListFields(fc)
        ]

        if name not in fields:

            arcpy.management.AddField(
                fc,
                name,
                typ
            )

    def remove_field_if_exists(
        self,
        fc,
        name
    ):

        fields = [
            f.name
            for f in arcpy.ListFields(fc)
        ]

        if name in fields:

            arcpy.management.DeleteField(
                fc,
                name
            )

class Perbaharui_Jarak_Kelas_Jalan(object):

    def __init__(self):

        self.label = "Optimasi Hitung Jarak Kelas Jalan"
        self.description = ""
        self.canRunInBackground = False


    def getParameterInfo(self):

        simpan_temp = arcpy.Parameter(
            displayName="Simpan ke Temporary Layer",
            name="simpan_temp",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )
        simpan_temp.value = False

        hanya_update = arcpy.Parameter(
            displayName="Sinkronisasi Data Persil Terbaru",
            name="hanya_update",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )
        hanya_update.value = True

        output_persil = arcpy.Parameter(
            displayName="Output Persil",
            name="output_persil",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [
            simpan_temp,
            hanya_update,
            output_persil
        ]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def delete_if_exists(self, path):

        if arcpy.Exists(path):

            try:
                arcpy.management.Delete(path)

            except:
                pass

    def add_field_if_not_exists(
        self,
        feature_class,
        field_name,
        field_type
    ):

        field_names = [
            field.name
            for field in arcpy.ListFields(
                feature_class
            )
        ]

        if field_name not in field_names:

            arcpy.management.AddField(
                feature_class,
                field_name,
                field_type
            )

    def execute(self, parameters, messages):

        messages.addMessage("== Proses mulai ==")

        # 1. Mengambil Konfigurasi dari config file
        configs = persil.get_config_values()
        dataset_path = configs["project_config"]["dataset_path"]
        jaringanjalan_path = configs["jaringan_jalan_config"]["path"]["Jaringan_Jalan"]
        nd_path = configs["jaringan_jalan_config"]["path"]["JaringanJalan_ND"]
        jaringanjalan_nd_path = configs["jaringan_jalan_config"]["path"]["JaringanJalanForND"]

        # 2. Mengambil nilai parameter

        simpan_temp = parameters[0].value
        hanya_update = parameters[1].value

        # 3. Mempersiapkan path untuk dataset dan output sementara

        persil_fc = os.path.join(dataset_path,"Persil_Layer")
        temp_output_name = "Analisis_Persil_Dengan_Jalan_Temp"
        temp_output_fc = os.path.join(dataset_path, temp_output_name)


        if simpan_temp:
            self.delete_if_exists(temp_output_fc)
            messages.addMessage("== Membuat layer sementara ==")
            arcpy.management.CopyFeatures(persil_fc,temp_output_fc)
            update_fc = temp_output_fc

        else:
            update_fc = persil_fc

        # 4. Menentukan layer untuk analisis, jika hanya_update maka lakukan seleksi pada layer persil_input, jika tidak maka gunakan seluruh data persil

        persil_layer = "persil_input"

        self.delete_if_exists(
            persil_layer
        )

        arcpy.management.MakeFeatureLayer(
            update_fc,
            persil_layer
        )

        if hanya_update:
            arcpy.management.SelectLayerByAttribute(
                persil_layer,
                "NEW_SELECTION",
                "UPPER(status_per) = 'UPDATE'"
            )

        # 5. Validasi jumlah feature yang akan diproses

        jumlah = int(arcpy.management.GetCount(persil_layer)[0])

        if jumlah == 0:
            messages.addWarningMessage("== Tidak ada feature yang diproses ==")
            return

        persilcentroid = ("Centroid_Persil")
        gdb_temp = arcpy.env.scratchGDB
        persilcentroid_path = os.path.join(gdb_temp, persilcentroid)

        # 6. Membuat centroid dari persil untuk digunakan sebagai titik awal dalam analisis jaringan dan menyimpan mapping OID dengan IDBIDANG untuk memudahkan update hasil analisis jaringan ke layer persil setelahnya

        messages.addMessage("== Membuat centroid persil ==")

        arcpy.management.FeatureToPoint(
            persil_layer,
            persilcentroid_path,
            "INSIDE"
        )
        oid_to_idbidang = {}

        oid_field = arcpy.Describe(persilcentroid_path).OIDFieldName

        with arcpy.da.SearchCursor(persilcentroid_path, [oid_field, "IDBIDANG"]) as rows:

            for oid, idbidang in rows:
                oid_to_idbidang[oid] = idbidang

        # 7. Persiapan field pada jaringan jalan untuk analisis jaringan

        messages.addMessage("== Persiapan field jalan ==")

        self.add_field_if_not_exists(
            jaringanjalan_path,
            "P_Jalan",
            "DOUBLE"
        )

        arcpy.management.CalculateField(
            jaringanjalan_path,
            "P_Jalan",
            "!shape.length!",
            "PYTHON3"
        )

        outNALayerName = "hasil_kelas"
        impedance_attribute = "P_Jalan"

        namafield = {
            4: 'JKKOLS',
            5: 'JKKOLP',
            6: 'JKATRS',
            7: 'JKATRP'
        }


        dataset_template_path = os.path.dirname(jaringanjalan_nd_path)
        dataset_kelas_jalan_path = os.path.join(os.path.dirname(dataset_path), "kelas_jalan")

        # 7. Melakukan iterasi untuk setiap kelas jalan yang ada di dataset kelas jalan, kemudian melakukan analisis jaringan untuk mencari jarak terdekat dari centroid persil ke kelas jalan tersebut, dan menyimpan hasilnya ke field yang sudah disiapkan

        arcpy.env.workspace = (dataset_kelas_jalan_path)

        list_fc = arcpy.ListFeatureClasses("*")

        list_kelas_jalan = []
        for fc in list_fc:

            if any(kls in fc for kls in ("JunctionKls1", "JunctionKls2", "JunctionKls3")):
                continue

            temp_path = os.path.join( dataset_kelas_jalan_path,    fc )
            jumlah_fc = int(arcpy.management.GetCount(temp_path )[0])

            if jumlah_fc > 0:
                list_kelas_jalan.append(fc)

        arcpy.AddMessage(f"== Kelas jalan yang diproses: {list_kelas_jalan} ==")
        hasilNAObject = arcpy.na.MakeClosestFacilityLayer(
                    nd_path,
                    outNALayerName,
                    impedance_attribute,
                    "TRAVEL_TO",
                    default_cutoff=500000,
                    default_number_facilities_to_find=1
                )
            

        outNALayer = hasilNAObject.getOutput(0)
        arcpy.na.AddLocations(
                outNALayer,
                "Incidents",
                persilcentroid_path
            )
        
        jarak_dict = {}
        for kelas_jalan in list_kelas_jalan:
            # 8. Melakukan analisis jaringan untuk mencari jarak terdekat dari centroid persil ke kelas jalan tersebut, dan menyimpan hasilnya ke field yang sudah disiapkan
            messages.addMessage(f"== Hitung jarak kelas_jalan: {kelas_jalan} ==")

            kelas_jalan_path = os.path.join(dataset_kelas_jalan_path,  kelas_jalan)
            kls = kelas_jalan.replace("JunctionKls","" )
            nama_field_target = namafield[int(kls)]

            arcpy.na.AddLocations(
                outNALayer,
                "Facilities",
                kelas_jalan_path,
                append="CLEAR"
            )

            solve_result = arcpy.na.Solve(outNALayer)
            if solve_result.getMessages(1): # 1 adalah kode untuk Warning
                messages.addWarningMessage(f"Peringatan Solve NA: {solve_result.getMessages(1)}")

            incident_path = os.path.join(dataset_template_path, f"incident_{kelas_jalan}" )
            route_path = os.path.join(dataset_template_path, f"route_{kelas_jalan}")

            self.delete_if_exists(incident_path)
            self.delete_if_exists(route_path)

            for lyr in outNALayer.listLayers():

                if lyr.isGroupLayer:
                    continue
                if lyr.name == "Incidents":
                    arcpy.management.CopyFeatures(lyr,  incident_path)

                elif lyr.name == "Routes":

                    arcpy.management.CopyFeatures(lyr,route_path)

            # 9. Mengambil nilai Total_P_Jalan untuk masing-masing incidentID

            arcpy.management.JoinField(
                incident_path,
                "OBJECTID",
                route_path,
                "IncidentID",
                ["Total_P_Jalan"]
            )

            # 10. Menyimpan data panjang rute dengan mapping ObjectID incident ke IDBIDANG untuk memudahkan update hasil analisis jaringan ke layer persil setelahnya

            with arcpy.da.SearchCursor(
                incident_path,
                ["OBJECTID", "Total_P_Jalan"]
            ) as rows:

                for incident_oid, jarak in rows:

                    idbidang = oid_to_idbidang.get(incident_oid)
                    if idbidang is not None:
                        if idbidang not in jarak_dict:
                            jarak_dict[idbidang] = {}
                        jarak_dict[idbidang][nama_field_target] = jarak
        # 11. Melakukan update data panjang rute ke field yang sudah disiapkan di layer persil dengan mapping IDBIDANG
        with arcpy.da.UpdateCursor(
            persil_layer,
            [
                "IDBIDANG",
                "JKKOLS",
                "JKKOLP",
                "JKATRS",
                "JKATRP"
            ]
        ) as rows:
            for row in rows:

                data = jarak_dict.get(row[0],{})
            
                row[1] = data.get("JKKOLS")
                row[2] = data.get("JKKOLP")
                row[3] = data.get("JKATRS")
                row[4] = data.get("JKATRP")

                rows.updateRow(row)


        # 12. Menampilkan output, jika opsi simpan_temp diaktifkan maka akan menampilkan layer sementara, jika tidak maka akan menampilkan layer persil yang sudah diupdate
        if simpan_temp:
            output_name = temp_output_name
        else:
            output_name = "Persil_Layer"

        self.delete_if_exists(
            output_name
        )

        arcpy.management.MakeFeatureLayer(
            update_fc,
            output_name
        )

        parameters[2].value = output_name

        messages.addMessage(
            "== Proses selesai =="
        )

        return
    
