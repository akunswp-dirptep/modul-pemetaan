import os
import math
import errno
import arcpy
from datetime import datetime
import sys
import json

arcpy.env.outputZFlag = "Disabled"
arcpy.env.outputMFlag = "Disabled"

# Tambahkan parent directory ke sys.path
script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from nbtutils.constant import PROJECT_CONFIG_FILE_NAME
from nbtutils.persil import get_config_values


class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [Perbaharui_Layer_Jalan,
                      Topologi_Sisi_Jalan,
                      Bangun_Jaringan_Jalan,
                      Perbaharui_Jaringan_Jalan,
                      Topologi_Jaringan_Jalan,
                      Hitung_Lebar_Jalan,
                      Set_Lebar_Jalan,
                      Simbologi_Kelas_Lebar_Jalan,
                      Menentukan_Kelas_Jalan,
                      Outlier_Kelas_Jalan,
                      Set_Lebar_Jalan_Semua_Kelas]


class Perbaharui_Layer_Jalan(object):
    def __init__(self):
        self.label = "Perbaharui Layer Jalan"
        self.description = "Mengganti data sisi jalan lama dengan data baru"
        self.canRunInBackground = False

    def getParameterInfo(self):
        output_layer = arcpy.Parameter(
            displayName="Output Sisi Jalan",
            name="output_sisi_jalan",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        input_sisi_jalan = arcpy.Parameter(
            displayName="Sisi Jalan Baru",
            name="input_sisi_jalan",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input"
        )


        return [output_layer, input_sisi_jalan]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        messages.addMessage("== Proses dimulai ==")

        sisi_jalan_baru_path = parameters[1].valueAsText
        configs = get_config_values()

        dataset_path = configs["main"]["dataset"]
        sisijalan = configs["jalan"]["sisijalan"]["nama"]
        sisijalan_path = configs["jalan"]["sisijalan"]["path"]
        topologi_file_name = configs['jalan']['topologi_sisijalan']['nama']
        topologi_layer_sisi_jalan_path = configs['jalan']['topologi_sisijalan']['path']

        if not sisi_jalan_baru_path:
            raise arcpy.ExecuteError("Input sisi jalan baru kosong")

        messages.addMessage("Menghapus topologi lama")

        if arcpy.Exists(topologi_layer_sisi_jalan_path):
            arcpy.management.Delete(topologi_layer_sisi_jalan_path)

        messages.addMessage("Menghapus layer lama")

        if arcpy.Exists(sisijalan_path):
            arcpy.management.Delete(sisijalan_path)

        messages.addMessage("Menyalin layer baru")

        arcpy.conversion.FeatureClassToFeatureClass(
            sisi_jalan_baru_path,
            dataset_path,
            sisijalan
        )

        arcpy.management.MakeFeatureLayer(
            os.path.join(dataset_path, sisijalan),
            sisijalan
        )

        arcpy.management.CreateTopology(dataset_path, topologi_file_name)
        arcpy.management.AddFeatureClassToTopology(topologi_layer_sisi_jalan_path, sisijalan_path, 1, 1)
        arcpy.management.AddRuleToTopology(topologi_layer_sisi_jalan_path, "Must Not Overlap (Line)", sisijalan_path)
        arcpy.management.AddRuleToTopology(topologi_layer_sisi_jalan_path, "Must Not Have Dangles (Line)", sisijalan_path)
        arcpy.management.ValidateTopology(topologi_layer_sisi_jalan_path)

        arcpy.SetParameter(0, 'SisiJalan')
        aprx = arcpy.mp.ArcGISProject('CURRENT')
        current_map = aprx.activeMap
        current_map.addDataFromPath(topologi_layer_sisi_jalan_path)

        messages.addMessage("== Layer jalan berhasil diperbaharui ==")

class Topologi_Sisi_Jalan(object):

    def __init__(self):
        self.label = "Topologi Sisi Jalan"
        self.description = "Mengganti data sisi jalan lama dengan data baru"
        self.canRunInBackground = False

    def getParameterInfo(self):

        penjelasan = arcpy.Parameter(
            displayName="Informasi Tools",
            name="penjelasan",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )

        penjelasan.value = (
            "Tools ini akan menampilkan pengecekan Topologi\n"
            "Untuk Layer Sisi Jalan\n\n"
            "Direktorat Penilaian Tanah dan Ekonomi Pertanahan,\n"
            "Kementerian ATR/BPN.\n"
            "Tahun: {}\n".format(datetime.now().year)
        )
        return [penjelasan]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        configs = get_config_values()

        dataset_path = configs["main"]["dataset"]
        sisijalan_path = configs["jalan"]["sisijalan"]["path"]
        topologi_file_name = configs['jalan']['topologi_sisijalan']['nama']
        topologi_layer_sisi_jalan_path = configs['jalan']['topologi_sisijalan']['path']

        if arcpy.Exists(topologi_layer_sisi_jalan_path):
            arcpy.management.Delete(topologi_layer_sisi_jalan_path)

        arcpy.management.CreateTopology(dataset_path, topologi_file_name)
        arcpy.management.AddFeatureClassToTopology(topologi_layer_sisi_jalan_path, sisijalan_path, 1, 1)
        arcpy.management.AddRuleToTopology(topologi_layer_sisi_jalan_path, "Must Not Overlap (Line)", sisijalan_path)
        arcpy.management.AddRuleToTopology(topologi_layer_sisi_jalan_path, "Must Not Have Dangles (Line)", sisijalan_path)
        arcpy.management.ValidateTopology(topologi_layer_sisi_jalan_path)

        aprx = arcpy.mp.ArcGISProject('CURRENT')
        current_map = aprx.activeMap
        current_map.addDataFromPath(topologi_layer_sisi_jalan_path)

        messages.addMessage("Topologi sudah diterapkan.")

class Bangun_Jaringan_Jalan(object):
    def __init__(self):
        self.label = "Bangun Jaringan Jalan"
        self.description = "Membangun layer jaringan jalan dari layer sisi jalan tanpa backup"
        self.canRunInBackground = False

    def getParameterInfo(self):

        param_output = arcpy.Parameter(
            displayName="Output Jaringan Jalan",
            name="output_jaringan",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [param_output]

    def execute(self, parameters, messages):
        arcpy.AddMessage("== Proses dimulai ==")

        configs = get_config_values()
        dataset_path = configs['main']['dataset']
        sisijalan_path = configs['jalan']['sisijalan']['path']

        topologi = "TopologiSisiJalan"
        topologi_path = os.path.join(dataset_path, topologi)

        awal = "JaringanAwal"
        awal_path = os.path.join(dataset_path, awal)

        awal_path_poly = os.path.join(dataset_path, "JaringanAwal_poly")

        jaringanjalan = "JaringanJalan"
        jaringanjalan_path = os.path.join(dataset_path, jaringanjalan)

        problemjalan = "JaringanProblem"
        problemjalan_path = os.path.join(dataset_path, problemjalan)

        problempoint = "ProblemPoint"
        problempoint_path = os.path.join(dataset_path, problempoint)

        temp = "temp"

        # =============================
        # Bersihkan data lama
        # =============================
        arcpy.AddMessage("== Bersihkan data sementara ==")

        cleanup_items = [
            topologi_path,
            awal_path,
            awal_path_poly,
            jaringanjalan_path,
            problemjalan_path,
            problempoint_path,
            temp
        ]

        for item in cleanup_items:
            if arcpy.Exists(item):
                arcpy.management.Delete(item)

        # =============================
        # Validasi topologi
        # =============================
        arcpy.AddMessage("== Validasi topologi sisi jalan ==")

        arcpy.management.CreateTopology(dataset_path, topologi)
        arcpy.management.AddFeatureClassToTopology(topologi_path, sisijalan_path, 1, 1)

        arcpy.management.AddRuleToTopology(
            topologi_path,
            "Must Not Overlap (Line)",
            sisijalan_path
        )

        arcpy.management.AddRuleToTopology(
            topologi_path,
            "Must Not Have Dangles (Line)",
            sisijalan_path
        )

        arcpy.management.ValidateTopology(topologi_path)

        err_name = "Error_Topology"
        arcpy.management.ExportTopologyErrors(
            topologi_path,
            dataset_path,
            err_name
        )

        top_error = os.path.join(dataset_path, err_name)

        count_p = int(arcpy.management.GetCount(top_error + "_point")[0])
        count_l = int(arcpy.management.GetCount(top_error + "_line")[0])
        count_pol = int(arcpy.management.GetCount(top_error + "_poly")[0])

        if count_p > 0 or count_l > 0 or count_pol > 0:
            arcpy.AddError("Masih ada error topologi pada layer sisi jalan")
            sys.exit(1)

        arcpy.AddMessage("Topologi valid")

        # =============================
        # Bangun jaringan jalan
        # =============================
        arcpy.AddMessage("== Bangun jaringan jalan ==")

        arcpy.management.FeatureToPolygon(
            sisijalan_path,
            awal_path_poly
        )

        arcpy.topographic.PolygonToCenterline(
            awal_path_poly,
            awal_path
        )

        arcpy.analysis.Near(
            awal_path,
            sisijalan_path,
            100,
            "NO_LOCATION",
            "NO_ANGLE"
        )

        # =============================
        # Tambah field awal
        # =============================
        arcpy.AddMessage("== Menyiapkan field ==")

        field_names = [f.name for f in arcpy.ListFields(awal_path)]

        if 'by_sys' not in field_names:
            arcpy.management.AddField(awal_path, 'by_sys', 'TEXT')

        arcpy.management.CalculateField(
            awal_path,
            'by_sys',
            "'0'",
            "PYTHON3"
        )

        if 'helper_id' not in field_names:
            arcpy.management.AddField(awal_path, 'helper_id', 'LONG')

        arcpy.management.CalculateField(
            awal_path,
            'helper_id',
            "!OBJECTID!",
            "PYTHON3"
        )

        arcpy.AddMessage("== Deteksi problem jalan ==")

        arcpy.management.MakeFeatureLayer(
            awal_path,
            problemjalan,
            "NEAR_DIST = 0"
        )

        arcpy.management.CopyFeatures(
            problemjalan,
            problemjalan_path
        )

        arcpy.management.FeatureToPoint(
            problemjalan_path,
            problempoint_path,
            "CENTROID"
        )


        arcpy.AddMessage("== Dissolve jaringan ==")

        arcpy.management.Dissolve(
            awal_path,
            jaringanjalan_path,
            ["helper_id"],
            "",
            "MULTI_PART",
            "DISSOLVE_LINES"
        )
        # path persil
        persil_path = configs['persil']['persil']['path']

        temp_jaringan = os.path.join(dataset_path, "temp_jaringan_bersih")

        arcpy.AddMessage("== Menghapus jaringan jalan yang overlap dengan persil ==")

        # Hapus bagian garis yang berada di dalam persil
        arcpy.analysis.Erase(
            jaringanjalan_path,
            persil_path,
            temp_jaringan
        )

        # Replace hasil akhir
        arcpy.management.Delete(jaringanjalan_path)

        arcpy.management.CopyFeatures(
            temp_jaringan,
            jaringanjalan_path
        )

        # cleanup
        if arcpy.Exists(temp_jaringan):
            arcpy.management.Delete(temp_jaringan)
        # =============================
        # Tambah atribut jaringan
        # =============================
        arcpy.AddMessage("== Menambah atribut jaringan ==")

        field_names = [f.name for f in arcpy.ListFields(jaringanjalan_path)]

        field_defs = [
            ("P_Jalan", "DOUBLE"),
            ("lb_jln", "DOUBLE"),
            ("Sim_LJln", "TEXT"),
            ("kls_jln", "TEXT"),
            ("s_kls_jln", "DOUBLE")
        ]

        for field_name, field_type in field_defs:
            if field_name not in field_names:
                arcpy.AddField_management(
                    jaringanjalan_path,
                    field_name,
                    field_type
                )

        arcpy.management.CalculateField(
            jaringanjalan_path,
            'kls_jln',
            "'Lokal Setapak'",
            "PYTHON3"
        )

        arcpy.management.CalculateField(
            jaringanjalan_path,
            's_kls_jln',
            "1",
            "PYTHON3"
        )

        # =============================
        # Output
        # =============================
        arcpy.management.MakeFeatureLayer(
            jaringanjalan_path,
            jaringanjalan
        )

        parameters[0].value = jaringanjalan

        arcpy.AddMessage(
            "== Proses selesai. Jaringan jalan berhasil dibuat =="
        )

class Perbaharui_Jaringan_Jalan(object):

    def __init__(self):
        self.label = "Update Jaringan Jalan"
        self.description = "Mengganti data jaringan jalan lama dengan data baru"
        self.canRunInBackground = False

    def getParameterInfo(self):

        in_jaringan_jalan = arcpy.Parameter(
            displayName="Input Jaringan Jalan",
            name="in_jaringan_jalan",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )

        out_layer = arcpy.Parameter(
            displayName="Output Layer",
            name="out_layer",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        field_lebar_jalan = arcpy.Parameter(
            displayName="Field Lebar Jalan",
            name="field_lebar_jalan",
            datatype="Field",
            parameterType="Optional",
            direction="Input"
        )
        field_lebar_jalan.parameterDependencies = [in_jaringan_jalan.name]

        field_kelas_jalan = arcpy.Parameter(
            displayName="Field Kelas Jalan",
            name="field_kelas_jalan",
            datatype="Field",
            parameterType="Optional",
            direction="Input"
        )
        field_kelas_jalan.parameterDependencies = [in_jaringan_jalan.name]

        return [
            in_jaringan_jalan,
            out_layer,
            field_lebar_jalan,
            field_kelas_jalan
        ]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):

        messages.addMessage("== Proses dimulai ==")

        configs = get_config_values()

        # =========================
        # CONFIG PATH
        # =========================
        dataset_path = configs["main"]["dataset"]
        out_path = configs["jalan"]["jaringanjalan"]["path"]

        # =========================
        # INPUT PARAMETER
        # =========================
        in_jaringan_jalan = parameters[0].valueAsText
        field_lebar_jalan = parameters[2].valueAsText
        field_kelas_jalan = parameters[3].valueAsText

        jaringan_jalan_layer = "Jaringan_Jalan"

        # =========================
        # DELETE TOPOLOGY
        # =========================
        topologi_path = os.path.join(dataset_path, "TopologiJaringanJalan")

        if arcpy.Exists(topologi_path):
            messages.addMessage("Menghapus topology lama...")
            arcpy.management.Delete(topologi_path)

        # =========================
        # DELETE OLD FEATURE CLASS
        # =========================
        if arcpy.Exists(out_path):
            messages.addMessage("Menghapus jaringan jalan lama...")
            arcpy.management.Delete(out_path)

        # =========================
        # COPY DATA
        # =========================
        messages.addMessage("Menyalin data jaringan jalan...")
        arcpy.management.CopyFeatures(in_jaringan_jalan, out_path)

        # =========================
        # ADD REQUIRED FIELDS
        # =========================
        list_names = [f.name for f in arcpy.ListFields(out_path)]

        if 'P_Jalan' not in list_names:
            arcpy.management.AddField(out_path, "P_Jalan", "DOUBLE")

        if 'lb_jln' not in list_names:
            arcpy.management.AddField(out_path, "lb_jln", "DOUBLE")

        if 'kls_jln' not in list_names:
            arcpy.management.AddField(out_path, "kls_jln", "TEXT")

        if 's_kls_jln' not in list_names:
            arcpy.management.AddField(out_path, "s_kls_jln", "DOUBLE")

        # =========================
        # CALCULATE LENGTH
        # =========================
        messages.addMessage("Menghitung panjang jalan...")
        arcpy.management.CalculateField(
            out_path,
            "P_Jalan",
            "!shape.length!",
            "PYTHON3"
        )

        # =========================
        # CALCULATE LEBAR JALAN
        # =========================
        if field_lebar_jalan and field_lebar_jalan != "lb_jln":

            messages.addMessage("Mengisi field lebar jalan...")

            arcpy.management.CalculateField(
                out_path,
                "lb_jln",
                f"!{field_lebar_jalan}!",
                "PYTHON3"
            )

        # =========================
        # CALCULATE KELAS JALAN
        # =========================
        if field_kelas_jalan and field_kelas_jalan != "kls_jln":

            messages.addMessage("Mengisi field kelas jalan...")

            exp = f"get(!{field_kelas_jalan}!)"

            code_block = """def get(b):
    if b == 'Arteri Primer':
        return 'Arteri Primer'
    elif b == 'Arteri Sekunder':
        return 'Arteri Sekunder'
    elif b == 'Kolektor Primer':
        return 'Kolektor Primer'
    elif b == 'Kolektor Sekunder':
        return 'Kolektor Sekunder'
    elif b == 'Lokal Primer':
        return 'Lokal Primer'
    elif b == 'Lokal Sekunder':
        return 'Lokal Sekunder'
    elif b == 'Lokal Setapak':
        return 'Lokal Setapak'
    else:
        return 'Lokal Setapak'
"""

            arcpy.management.CalculateField(
                out_path,
                "kls_jln",
                exp,
                "PYTHON3",
                code_block
            )

        # =========================
        # SCORE KELAS JALAN
        # =========================
        messages.addMessage("Menghitung skor kelas jalan...")

        exp = "get(!kls_jln!)"

        code_block = """def get(b):
    if b == 'Arteri Primer':
        return 7
    elif b == 'Arteri Sekunder':
        return 6
    elif b == 'Kolektor Primer':
        return 5
    elif b == 'Kolektor Sekunder':
        return 4
    elif b == 'Lokal Primer':
        return 3
    elif b == 'Lokal Sekunder':
        return 2
    elif b == 'Lokal Setapak':
        return 1
    else:
        return 1
"""

        arcpy.management.CalculateField(
            out_path,
            "s_kls_jln",
            exp,
            "PYTHON3",
            code_block
        )

        # =========================
        # MAKE LAYER
        # =========================
        if arcpy.Exists(jaringan_jalan_layer):
            arcpy.management.Delete(jaringan_jalan_layer)

        arcpy.management.MakeFeatureLayer(
            out_path,
            jaringan_jalan_layer
        )


        # =========================
        # SET OUTPUT
        # =========================
        parameters[1].value = jaringan_jalan_layer

        messages.addMessage("== Proses selesai ==")

class Topologi_Jaringan_Jalan(object):

    def __init__(self):
        self.label = "Topologi Jaringan Jalan"
        self.description = "Mengganti data sisi jalan lama dengan data baru"
        self.canRunInBackground = False

    def getParameterInfo(self):

        penjelasan = arcpy.Parameter(
            displayName="Informasi Tools",
            name="penjelasan",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )

        penjelasan.value = (
            "Tools ini akan menampilkan pengecekan Topologi\n"
            "Untuk Layer Sisi Jalan\n\n"
            "Direktorat Penilaian Tanah dan Ekonomi Pertanahan,\n"
            "Kementerian ATR/BPN.\n"
            "Tahun: {}\n".format(datetime.now().year)
        )
        return [penjelasan]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        configs = get_config_values()

        dataset_path = configs["main"]["dataset"]
        jaringan_jalan = configs["jalan"]["jaringanjalan"]["path"]
        topologi_file_name = configs['jalan']['topologi_jaringanjalan']['nama']
        topologi_layer_jaringan_jalan = configs['jalan']['topologi_jaringanjalan']['path']

        if arcpy.Exists(topologi_layer_jaringan_jalan):
            arcpy.management.Delete(topologi_layer_jaringan_jalan)

        arcpy.management.CreateTopology(dataset_path, topologi_file_name)
        arcpy.management.AddFeatureClassToTopology(topologi_layer_jaringan_jalan, jaringan_jalan, 1, 1)
        arcpy.management.AddRuleToTopology(topologi_layer_jaringan_jalan, "Must Not Overlap (Line)", jaringan_jalan)
        arcpy.management.AddRuleToTopology(topologi_layer_jaringan_jalan, "Must Not Have Dangles (Line)", jaringan_jalan)
        arcpy.management.AddRuleToTopology(topologi_layer_jaringan_jalan, "Must Not Have Pseudo-Nodes (Line)", jaringan_jalan)
        arcpy.management.ValidateTopology(topologi_layer_jaringan_jalan)

        aprx = arcpy.mp.ArcGISProject('CURRENT')
        current_map = aprx.activeMap
        current_map.addDataFromPath(topologi_layer_jaringan_jalan)

        messages.addMessage("Topologi sudah diterapkan.")

class Hitung_Lebar_Jalan(object):

    def __init__(self):
        self.label = "Hitung Lebar Jalan"
        self.description = "Menghitung lebar jalan berdasarkan sisi jalan"
        self.canRunInBackground = False

    def getParameterInfo(self):

        penjelasan = arcpy.Parameter(
            displayName="Informasi Tools",
            name="penjelasan",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )

        penjelasan.value = (
            "Tools ini digunakan untuk menghitung lebar jalan\n"
            "berdasarkan jarak midpoint jaringan jalan\n"
            "ke sisi jalan.\n\n"
            "Direktorat Penilaian Tanah dan Ekonomi Pertanahan,\n"
            "Kementerian ATR/BPN.\n"
            "Tahun: {}\n".format(datetime.now().year)
        )

        return [penjelasan]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):

        messages.addMessage("== Proses dimulai ==")

        configs = get_config_values()

        dataset_path = configs["main"]["dataset"]

        jaringanjalan_path = configs["jalan"]["jaringanjalan"]["path"]
        sisijalan_path = configs["jalan"]["sisijalan"]["path"]
        midpointjaringanjalan_path = configs["jalan"]["midpointjaringanjalan"]["path"]

        topologi_layer_jaringan_jalan = configs['jalan']['topologi_jaringanjalan']['path']

        if arcpy.Exists(topologi_layer_jaringan_jalan):
            arcpy.management.Delete(topologi_layer_jaringan_jalan)

        if arcpy.Exists(midpointjaringanjalan_path):
            messages.addMessage("Menghapus midpoint lama...")
            arcpy.management.Delete(midpointjaringanjalan_path)

        messages.addMessage("== Hitung Lebar Jalan ==")

        field_names = [field.name for field in arcpy.ListFields(jaringanjalan_path)]

        if 'SimLJln2' not in field_names:
            arcpy.management.AddField(jaringanjalan_path, 'SimLJln2', 'TEXT')

        if 'lb_jln' not in field_names:
            arcpy.management.AddField(jaringanjalan_path, 'lb_jln', 'DOUBLE')

        if 'P_Jalan' not in field_names:
            arcpy.management.AddField(jaringanjalan_path, 'P_Jalan', 'DOUBLE')

        messages.addMessage("Menghitung panjang jalan...")

        arcpy.management.CalculateField(
            jaringanjalan_path,
            "P_Jalan",
            "!shape.length!",
            "PYTHON3"
        )

        messages.addMessage("Membuat midpoint jaringan jalan...")

        arcpy.management.FeatureToPoint(
            jaringanjalan_path,
            midpointjaringanjalan_path,
            "INSIDE"
        )

        messages.addMessage("Melakukan analisis jarak sisi jalan...")

        arcpy.analysis.Near(
            midpointjaringanjalan_path,
            sisijalan_path,
            100,
            "LOCATION",
            "NO_ANGLE"
        )

        field_names = [field.name for field in arcpy.ListFields(midpointjaringanjalan_path)]

        if 'lb_jln' not in field_names:
            arcpy.management.AddField(
                midpointjaringanjalan_path,
                'lb_jln',
                'DOUBLE'
            )

        messages.addMessage("Menghitung lebar jalan dari NEAR_DIST...")

        arcpy.management.CalculateField(
            midpointjaringanjalan_path,
            "lb_jln",
            "2 * !NEAR_DIST!",
            "PYTHON3"
        )

        messages.addMessage("Memperbarui atribut jaringan jalan...")

        midpoint_dict = {}

        with arcpy.da.SearchCursor(
            midpointjaringanjalan_path,
            ["ORIG_FID", "lb_jln"]
        ) as cursor:

            for row in cursor:
                midpoint_dict[row[0]] = row[1]

        with arcpy.da.UpdateCursor(
            jaringanjalan_path,
            ["OBJECTID", "lb_jln", "SimLJln2"]
        ) as cursor:

            for row in cursor:

                oid = row[0]

                if oid in midpoint_dict:

                    lb_jln = midpoint_dict[oid]

                    # Batasi nilai
                    if lb_jln > 30:
                        lb_jln = 30

                    if lb_jln < 0:
                        lb_jln = 0

                    row[1] = lb_jln

                    # Klasifikasi SimLJln2
                    if lb_jln <= 0:
                        row[2] = "0"

                    elif lb_jln <= 1.5:
                        row[2] = "1.5"

                    elif lb_jln <= 3:
                        row[2] = "3"

                    elif lb_jln <= 5:
                        row[2] = "5"

                    elif lb_jln <= 8:
                        row[2] = "8"

                    else:
                        row[2] = "8+"

                    cursor.updateRow(row)

        aprx = arcpy.mp.ArcGISProject("CURRENT")
        current_map = aprx.activeMap

        current_map.addDataFromPath(midpointjaringanjalan_path)

        messages.addMessage("== Selesai Hitung Lebar Jalan ==")

class Set_Lebar_Jalan(object):

    def __init__(self):
        self.label = "Set Lebar Jalan"
        self.description = "Mengatur lebar jalan untuk jaringan jalan yang terseleksi"
        self.canRunInBackground = False

    def getParameterInfo(self):

        lebarjalan = arcpy.Parameter(
            displayName="Lebar Jalan",
            name="lebarjalan",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input"
        )

        return [lebarjalan]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):

        messages.addMessage("== Proses dimulai ==")

        # =========================
        # CONFIG
        # =========================
        configs = get_config_values()

        jaringanjalan = configs["jalan"]["jaringanjalan"]["nama"]
        jaringanjalan_path = configs["jalan"]["jaringanjalan"]["path"]

        # =========================
        # PARAMETER
        # =========================
        lebarjalan = parameters[0].value

        # =========================
        # ADD REQUIRED FIELDS
        # =========================
        field_names = [field.name for field in arcpy.ListFields(jaringanjalan_path)]

        if 'lb_jln' not in field_names:
            arcpy.management.AddField(
                jaringanjalan_path,
                'lb_jln',
                'DOUBLE'
            )

        if 'Sim_LJln' not in field_names:
            arcpy.management.AddField(
                jaringanjalan_path,
                'Sim_LJln',
                'TEXT'
            )

        if 'SimLJln2' not in field_names:
            arcpy.management.AddField(
                jaringanjalan_path,
                'SimLJln2',
                'TEXT'
            )

        # =========================
        # CHECK SELECTION
        # =========================
        ada_seleksi = len(arcpy.Describe(jaringanjalan).FIDSet)

        if ada_seleksi <= 0:
            messages.addWarningMessage(
                "Tidak ada jaringan jalan yang dipilih."
            )
            return

        messages.addMessage(
            "Jumlah fitur terseleksi: {}".format(ada_seleksi)
        )

        # =========================
        # UPDATE SELECTION
        # =========================
        messages.addMessage("Memperbarui lebar jalan...")

        with arcpy.da.UpdateCursor(
            jaringanjalan,
            ["lb_jln", "SimLJln2"]
        ) as cursor:

            for row in cursor:

                row[0] = lebarjalan

                # Klasifikasi SimLJln2
                if lebarjalan == 0:
                    row[1] = "0"

                elif lebarjalan <= 1.5:
                    row[1] = "1.5"

                elif lebarjalan <= 3:
                    row[1] = "3"

                elif lebarjalan <= 5:
                    row[1] = "5"

                elif lebarjalan <= 8:
                    row[1] = "8"

                else:
                    row[1] = "8+"

                cursor.updateRow(row)

        # =========================
        # CALCULATE FIELD
        # =========================
        arcpy.management.CalculateField(
            jaringanjalan,
            "lb_jln",
            lebarjalan,
            "PYTHON3"
        )

        messages.addMessage("== Proses selesai ==")

class Simbologi_Kelas_Lebar_Jalan(object):

    def __init__(self):
        self.label = "Simbologi Kelas Lebar Jalan"
        self.description = "Menerapkan simbologi kelas jalan pada jaringan jalan"
        self.canRunInBackground = False

    def getParameterInfo(self):

        out_layer = arcpy.Parameter(
            displayName="Output Layer",
            name="out_layer",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [out_layer]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):

        messages.addMessage("== Proses dimulai ==")

        # =========================
        # CONFIG
        # =========================
        configs = get_config_values()

        jaringanjalan = configs["jalan"]["jaringanjalan"]["nama"]
        jaringanjalan_path = configs["jalan"]["jaringanjalan"]["path"]
        simbologi_path = r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Simbologi_Lebar_Jalan.lyrx"

        temp_layer = "temp"

        # =========================
        # DELETE TEMP LAYER
        # =========================
        if arcpy.Exists(temp_layer):
            arcpy.management.Delete(temp_layer)

        if arcpy.Exists(jaringanjalan):
            arcpy.management.Delete(jaringanjalan)

        # =========================
        # UPDATE NULL VALUE
        # =========================
        messages.addMessage(
            "Mengisi nilai kelas jalan yang kosong..."
        )

        arcpy.management.MakeFeatureLayer(
            jaringanjalan_path,
            temp_layer
        )

        arcpy.management.SelectLayerByAttribute(
            temp_layer,
            "NEW_SELECTION",
            "kls_jln IS NULL"
        )

        arcpy.management.CalculateField(
            temp_layer,
            "kls_jln",
            "'Lokal'",
            "PYTHON3"
        )

        arcpy.management.CalculateField(
            temp_layer,
            "s_kls_jln",
            "1",
            "PYTHON3"
        )

        # =========================
        # DELETE TEMP LAYER
        # =========================
        if arcpy.Exists(temp_layer):
            arcpy.management.Delete(temp_layer)

        # =========================
        # CREATE OUTPUT LAYER
        # =========================
        messages.addMessage(
            "Membuat layer jaringan jalan..."
        )

        arcpy.management.MakeFeatureLayer(
            jaringanjalan_path,
            jaringanjalan
        )

        # =========================
        # APPLY SYMBOLOGY
        # =========================
        messages.addMessage(
            "Menerapkan simbologi kelas jalan..."
        )

        arcpy.management.ApplySymbologyFromLayer(
            jaringanjalan,
            simbologi_path
        )

        # =========================
        # ADD TO CURRENT MAP
        # =========================
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        current_map = aprx.activeMap

        current_map.addDataFromPath(jaringanjalan_path)

        # =========================
        # SET OUTPUT
        # =========================
        parameters[0].value = jaringanjalan

        messages.addMessage("== Proses selesai ==")

class Menentukan_Kelas_Jalan(object):

    def __init__(self):
        self.label = "Menentukan Kelas Jalan"
        self.description = "Menentukan Kelas Jalan"
        self.canRunInBackground = False

    def getParameterInfo(self):

        kelas_jalan = arcpy.Parameter(
            displayName ='Pilih Kelas',
            name='kelas_jalan',
            datatype='GPString',
            parameterType="Required",
            direction="Input"

        )
        kelas_jalan.filter.list = [
            'Arteri Primer',
            'Arteri Sekunder',
            'Kolektor Primer',
            'Kolektor Sekunder',
            'Lokal Primer',
            'Lokal Sekunder',
            'Lokal Setapak'
        ]
        out_layer = arcpy.Parameter(
            displayName="Output Layer",
            name="out_layer",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [kelas_jalan, out_layer]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):

        kelas_jalan = parameters[0].valueAsText

        mapping_kelas = {
            "Arteri Primer": 7,
            "Arteri Sekunder": 6,
            "Kolektor Primer": 5,
            "Kolektor Sekunder": 4,
            "Lokal Primer": 3,
            "Lokal Sekunder": 2,
            "Lokal Setapak": 1
        }

        # Validasi input
        if kelas_jalan not in mapping_kelas:
            arcpy.AddError("Kelas jalan tidak valid.")
            sys.exit()

        skor_kelas = mapping_kelas[kelas_jalan] 

        configs = get_config_values()

        jaringanjalan = configs["jalan"]["jaringanjalan"]["nama"]
        jaringanjalan_path = configs["jalan"]["jaringanjalan"]["path"]
        simbologi_path = r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Simbologi_Kelas_Jalan.lyrx"

        # =========================
        # ADD REQUIRED FIELDS
        # =========================
        field_names = [field.name for field in arcpy.ListFields(jaringanjalan_path)]

        if 'kls_jln' not in field_names:
            arcpy.management.AddField(
                jaringanjalan_path,
                'kls_jln',
                'TEXT'
            )

        if 's_kls_jln' not in field_names:
            arcpy.management.AddField(
                jaringanjalan_path,
                's_kls_jln',
                'DOUBLE'
            )

        # =========================
        # CHECK SELECTION
        # =========================
        ada_seleksi = len(arcpy.Describe(jaringanjalan).FIDSet)

        if ada_seleksi <= 0:
            messages.addWarningMessage(
                "Tidak ada jaringan jalan yang dipilih."
            )
            return

        messages.addMessage(
            "Jumlah fitur terseleksi: {}".format(ada_seleksi)
        )

        # =========================
        # UPDATE CLASS
        # =========================
        messages.addMessage(
            "Mengubah kelas jalan menjadi {}".format(kelas_jalan)
        )

        with arcpy.da.UpdateCursor(
            jaringanjalan,
            ["kls_jln", "s_kls_jln"]
        ) as cursor:

            for row in cursor:

                row[0] = kelas_jalan
                row[1] = skor_kelas

                cursor.updateRow(row)

        # =========================
        # APPLY SYMBOLOGY
        # =========================
        if arcpy.Exists(jaringanjalan):

            messages.addMessage(
                "Menerapkan simbologi kelas jalan..."
            )

            arcpy.management.ApplySymbologyFromLayer(
                jaringanjalan,
                simbologi_path
            )

class Outlier_Kelas_Jalan(object):

    def __init__(self):
        self.label = "Outlier Kelas Jalan"
        self.description = "Mendeteksi outlier lebar jalan berdasarkan kelas jalan"
        self.canRunInBackground = False

    def getParameterInfo(self):

        in_jaringanjalan = arcpy.Parameter(
            displayName="Input Jaringan Jalan",
            name="in_jaringanjalan",
            datatype="GPFeatureLayer",
            parameterType="Optional",
            direction="Input"
        )

        out_kelas_1 = arcpy.Parameter(
            displayName="Outlier Kelas 1",
            name="out_kelas_1",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        out_kelas_2 = arcpy.Parameter(
            displayName="Outlier Kelas 2",
            name="out_kelas_2",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        out_kelas_3 = arcpy.Parameter(
            displayName="Outlier Kelas 3",
            name="out_kelas_3",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        out_kelas_4 = arcpy.Parameter(
            displayName="Outlier Kelas 4",
            name="out_kelas_4",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        out_kelas_5 = arcpy.Parameter(
            displayName="Outlier Kelas 5",
            name="out_kelas_5",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        out_jaringan_jalan = arcpy.Parameter(
            displayName="Jaringan Jalan",
            name="out_jaringan_jalan",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [
            in_jaringanjalan,
            out_kelas_1,
            out_kelas_2,
            out_kelas_3,
            out_kelas_4,
            out_kelas_5,
            out_jaringan_jalan
        ]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        messages.addMessage("== Proses dimulai ==")

        # =========================
        # CONFIG
        # =========================
        configs = get_config_values()

        dataset_path = configs["main"]["dataset"]

        default_jalan_name = configs["jalan"]["jaringanjalan"]["nama"]
        default_jalan_path = configs["jalan"]["jaringanjalan"]["path"]

        temp_gdb_path = arcpy.env.scratchGDB

        sim_path = r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Simbologi_Layer_Outlier_Lebar_Jalan.lyrx"
        no_sim_path = r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Simbologi_Layer_Outlier_Lebar_Jalan.lyrx"

        # =========================
        # INPUT
        # =========================
        jaringanjalan_path = parameters[0].valueAsText

        if not jaringanjalan_path:
            jaringanjalan_path = default_jalan_path

        jaringanjalan = "JaringanJalan"

        # =========================
        # VALIDASI FIELD
        # =========================
        field_names = [field.name for field in arcpy.ListFields(jaringanjalan_path)]

        if 'SkorKelasJalan' not in field_names or 'LebarJalan' not in field_names:

            messages.addWarningMessage(
                "Proses dihentikan, field "
                "'SkorKelasJalan' atau 'LebarJalan' tidak ditemukan."
            )
            return

        list_err = []

        # =========================
        # PROSES OUTLIER
        # =========================
        for i in range(1, 6):

            out_name = "outlier_klsjln_" + str(i)
            out_path = os.path.join(temp_gdb_path, out_name)

            messages.addMessage(
                "== Anselin Local Moran's I: {} ==".format(out_name)
            )

            # Delete old output
            if arcpy.Exists(out_path):
                arcpy.management.Delete(out_path)

            temp_lyr = "temp_lyr"

            if arcpy.Exists(temp_lyr):
                arcpy.management.Delete(temp_lyr)

            # =========================
            # FILTER KELAS JALAN
            # =========================
            arcpy.management.MakeFeatureLayer(
                jaringanjalan_path,
                temp_lyr,
                "SkorKelasJalan = {}".format(i)
            )

            row_count = int(
                arcpy.management.GetCount(temp_lyr)[0]
            )

            messages.addMessage(
                "Jumlah record: {}".format(row_count)
            )

            # =========================
            # VALIDASI MINIMUM FEATURE
            # =========================
            if row_count > 2:

                try:

                    # =========================
                    # CLUSTER OUTLIER
                    # =========================
                    arcpy.stats.ClustersOutliers(
                        temp_lyr,
                        "LebarJalan",
                        out_path,
                        "INVERSE_DISTANCE_SQUARED",
                        "EUCLIDEAN_DISTANCE",
                        "NONE"
                    )

                    lyr = "Outlier_Lebar_Jalan_Kelas_{}".format(i)

                    if arcpy.Exists(lyr):
                        arcpy.management.Delete(lyr)

                    arcpy.management.MakeFeatureLayer(
                        out_path,
                        lyr
                    )

                    # =========================
                    # APPLY SYMBOLOGY
                    # =========================
                    arcpy.management.ApplySymbologyFromLayer(
                        lyr,
                        sim_path
                    )

                    parameters[i].value = lyr

                except arcpy.ExecuteError:

                    err_msg = arcpy.GetMessages()

                    messages.addWarningMessage(
                        "Error pada {}".format(out_name)
                    )

                    list_err.append(
                        "{},{}".format(out_name, err_msg)
                    )

            else:

                messages.addMessage(
                    "Kelas Jalan {} tidak diproses. "
                    "Jumlah record {}, kurang dari 3.".format(
                        i,
                        row_count
                    )
                )

            # =========================
            # DELETE TEMP LAYER
            # =========================
            if arcpy.Exists(temp_lyr):
                arcpy.management.Delete(temp_lyr)

            messages.addMessage("== Ok ==")

        # =========================
        # SAVE ERROR LOG
        # =========================
        appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

        err_outlier_path = os.path.join(
            appdata,
            "err_outlier.err"
        )

        with open(err_outlier_path, "w") as conf_file:
            conf_file.write("\n".join(list_err) + "\n")

        # =========================
        # FINAL LAYER
        # =========================
        lyr = "JaringanJalan"

        if arcpy.Exists(lyr):
            arcpy.management.Delete(lyr)

        arcpy.management.MakeFeatureLayer(
            jaringanjalan_path,
            lyr
        )

        arcpy.management.ApplySymbologyFromLayer(
            lyr,
            no_sim_path
        )

        # =========================
        # ADD TO CURRENT MAP
        # =========================
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        current_map = aprx.activeMap

        current_map.addDataFromPath(jaringanjalan_path)

        # =========================
        # SET OUTPUT
        # =========================
        parameters[6].value = lyr

        messages.addMessage("== Proses selesai ==")

class Set_Lebar_Jalan_Semua_Kelas(object):

    def __init__(self):
        self.label = "Set Lebar Jalan Semua Kelas"
        self.description = (
            "Mengatur lebar jalan pada seluruh layer "
            "kelas jalan yang memiliki seleksi"
        )
        self.canRunInBackground = False

    def getParameterInfo(self):

        lebar_jalan = arcpy.Parameter(
            displayName="Lebar Jalan",
            name="lebar_jalan",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input"
        )

        return [lebar_jalan]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):

        messages.addMessage("== Proses dimulai ==")

        # =========================
        # PARAMETER
        # =========================
        val = parameters[0].value

        field_lebar = "lb_jln"
        field_cotype = "COType"

        # =========================
        # LIST LAYER
        # =========================
        layer_list = [
            "Jalan_Lokal_Setapak",
            "Jalan_Lokal_Sekunder",
            "Jalan_Lokal_Primer",
            "Jalan_Kolektor_Sekunder",
            "Jalan_Kolektor_Primer",
            "Jalan_Arteri_Sekunder",
            "Jalan_Arteri_Primer"
        ]

        # =========================
        # UPDATE PER KELAS
        # =========================
        for layer_name in layer_list:

            ada_seleksi = 0

            if arcpy.Exists(layer_name):
                ada_seleksi = len(
                    arcpy.Describe(layer_name).FIDSet
                )

            if ada_seleksi > 0:

                messages.addMessage(
                    "Memproses layer: {}".format(layer_name)
                )

                with arcpy.da.UpdateCursor(
                    layer_name,
                    [field_lebar, field_cotype]
                ) as cursor:

                    for row in cursor:

                        # Update lebar jalan
                        row[0] = val

                        # Update COType
                        val_temp = row[1]

                        if val_temp is None:
                            val_temp = ""

                        if len(str(val_temp)) > 0:
                            val_temp = str(val_temp)[0]

                        val_temp = str(val_temp) + "E"

                        row[1] = val_temp

                        cursor.updateRow(row)

                messages.addMessage(
                    "Jumlah fitur terseleksi: {}".format(
                        ada_seleksi
                    )
                )

        # =========================
        # UPDATE JARINGAN JALAN
        # =========================
        jaringanjalan = "Jaringan_Jalan"

        ada_seleksi = 0

        if arcpy.Exists(jaringanjalan):
            ada_seleksi = len(
                arcpy.Describe(jaringanjalan).FIDSet
            )

        if ada_seleksi > 0:

            messages.addMessage(
                "Memperbarui layer Jaringan_Jalan..."
            )

            with arcpy.da.UpdateCursor(
                jaringanjalan,
                [field_lebar]
            ) as cursor:

                for row in cursor:

                    row[0] = val
                    cursor.updateRow(row)

            messages.addMessage(
                "Jumlah fitur terseleksi pada "
                "Jaringan_Jalan: {}".format(
                    ada_seleksi
                )
            )

        messages.addMessage("== Proses selesai ==")
