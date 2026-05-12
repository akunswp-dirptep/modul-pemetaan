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
        self.tools = [Identifikasi_Perubahan_Persil, 
                      Hapus_Indikator_Perubahan_Persil,
                      Update_Indikator_Perubahan_Persil,
                      Set_Status_Perubahan_Persil,
                      Persil_Cluster,
                      Reset_Persil_Cluster,
                      Generate_Peta_Persil_Cluster,
                      Generate_Peta_Akhir,
                      Update_Luas_Tanah,
                      Analisis_Bentuk_Persil,
                      Edit_Bentuk_Persil,
                      Simpan_Bentuk_Persil]


class Identifikasi_Perubahan_Persil(object):
    def __init__(self):
        self.label = "Identifikasi Perubahan Persil"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):

        peta_lama = arcpy.Parameter(
            displayName="Persil Lama (Tahun Sebelumnya)",
            name="peta_lama",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )

        output_lama = arcpy.Parameter(
            displayName="Output Peta Lama",
            name="output_lama",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        output_baru = arcpy.Parameter(
            displayName="Output Peta Baru",
            name="output_baru",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        output_indikator = arcpy.Parameter(
            displayName="Output Indikator",
            name="output_indikator",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [
            peta_lama,
            output_lama,
            output_baru,
            output_indikator
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

        dataset_path = (
            configs["project_config"]["dataset_path"]
        )

        persil_path = (
            configs["persil_config"]["path"]["Persil"]
        )

        konfigurasi_variabel_path = (
            configs["project_config"]["daftar_variabel_path"]
        )

        appdata = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.dirname(
                os.path.realpath(__file__)
            )))))

        peta_lama_input = parameters[0].valueAsText
        fields_dont_delete = []

        if os.path.exists(konfigurasi_variabel_path):

            with open(konfigurasi_variabel_path, "r" ) as conf_file:
                json_variabel = json.load(conf_file)

            daftar_variabel = json_variabel.get("daftar_variabel", [])

            for row in daftar_variabel:
                if len(row) < 2:
                    continue
                akronim = row[1]
                fields_dont_delete.append(akronim)
                fields_dont_delete.append("s_" + akronim)

        # =====================================================
        # MEMORY WORKSPACE
        # =====================================================

        dest_lama_path = r"in_memory\PersilPetaLama"
        dest_baru_path = r"in_memory\PersilPetaBaru"

        temp_lama_path = r"in_memory\Peta_Temp_Lama"
        temp_baru_path = r"in_memory\Peta_Temp_Baru"

        peta_indikator_temp = r"in_memory\Indikator_Perubahan"
        peta_indikator = r"Indikator_Perubahan_Persil"

        peta_indikator_path = os.path.join(
            dataset_path,
            peta_indikator
        )

        memory_layers = [
            dest_lama_path,
            dest_baru_path,
            temp_lama_path,
            temp_baru_path,
            peta_indikator_temp
        ]

        for lyr in memory_layers:
            if arcpy.Exists(lyr):
                try:
                    arcpy.management.Delete(lyr)
                except Exception as e:
                    arcpy.AddWarning(str(e))

        arcpy.management.CopyFeatures(
            peta_lama_input,
            dest_lama_path
        )

        arcpy.management.CopyFeatures(
            persil_path,
            dest_baru_path
        )

        def bersihkan_field(fc):
            fields = arcpy.ListFields(fc)
            for f in fields:
                if not (
                    f.type == "Geometry"
                    or f.type == "OID"
                    or "shape" in f.name.lower()
                    or f.name in fields_dont_delete
                    or f.name == "FID"
                ):
                    try:
                        arcpy.management.DeleteField(fc, f.name)
                    except Exception as e:
                        arcpy.AddWarning(str(e))

        bersihkan_field(dest_lama_path)
        bersihkan_field(dest_baru_path)

        for fc in [ dest_lama_path, dest_baru_path ]:

            field_names = [
                f.name
                for f in arcpy.ListFields(fc)
            ]

            if "ls_asal" not in field_names:

                arcpy.management.AddField(
                    fc,
                    "ls_asal",
                    "DOUBLE"
                )

            arcpy.management.CalculateField(
                fc,
                "ls_asal",
                "!shape.area!",
                "PYTHON3"
            )

        arcpy.management.MakeFeatureLayer(
            dest_lama_path,
            "PetaLamaLayer_Temp"
        )

        arcpy.management.SelectLayerByLocation(
            "PetaLamaLayer_Temp",
            "CONTAINS",
            dest_baru_path,
            selection_type="NEW_SELECTION",
            invert_spatial_relationship="INVERT"
        )

        arcpy.management.CopyFeatures(
            "PetaLamaLayer_Temp",
            temp_lama_path
        )

        arcpy.management.MakeFeatureLayer(
            dest_baru_path,
            "PetaBaruLayer_Temp"
        )

        arcpy.management.SelectLayerByLocation(
            "PetaBaruLayer_Temp",
            "CONTAINS",
            dest_lama_path,
            selection_type="NEW_SELECTION",
            invert_spatial_relationship="INVERT"
        )

        arcpy.management.CopyFeatures(
            "PetaBaruLayer_Temp",
            temp_baru_path
        )

        arcpy.management.Merge([temp_baru_path, temp_lama_path], peta_indikator_temp)

        field_names = [f.name  for f in arcpy.ListFields(peta_indikator_temp)]

        if "indikator_perubahan" not in field_names:
            arcpy.management.AddField(
                peta_indikator_temp,
                "indikator_perubahan",
                "TEXT"
            )

        with arcpy.da.UpdateCursor( peta_indikator_temp, ["indikator_perubahan"] ) as cursor:
            for row in cursor:
                row[0] = "Indikator Periksa"
                cursor.updateRow(row)

        if arcpy.Exists(peta_indikator_path):
            try:
                arcpy.management.Delete(peta_indikator_path)
            except:
                pass

        arcpy.management.CopyFeatures(
            peta_indikator_temp,
            peta_indikator_path
        )

        messages.addMessage("== Menerapkan Simbologi ==")
        
        simbology_folder = os.path.join(
            appdata,
            'ui',
            'symbology',
            'Nilai Bidang Tanah'
        )


        # 1. Peta Indikator
        lyr_indikator = arcpy.management.MakeFeatureLayer(
            peta_indikator_path,
            "Indikator_Perubahan_Persil"
        )[0] # Ambil objek layer dari Result object



        # 2. Peta Lama

        saved_old_layer = os.path.join(dataset_path, "Persil_Lama")
        arcpy.management.CopyFeatures(
            dest_lama_path,
            saved_old_layer
        )

        lyr_lama = arcpy.management.MakeFeatureLayer(
            saved_old_layer,
            "Persil_Lama"
        )[0]



        # 3. Peta Baru
        saved_new_layer = os.path.join(dataset_path, "Persil_Baru")
        arcpy.management.CopyFeatures(
            dest_baru_path,
            saved_new_layer
        )
        lyr_baru = arcpy.management.MakeFeatureLayer(
            saved_new_layer,
            "Persil_Baru"
        )[0]


        # =====================================================
        # OUTPUT PARAMETER
        # =====================================================
        # Gunakan objek layer secara langsung agar simbologi yang sudah di-apply terbawa
        
        parameters[1].value = lyr_lama
        parameters[2].value = lyr_baru
        parameters[3].value = lyr_indikator

        messages.addMessage(
            "== Proses selesai =="
        )

        return

class Hapus_Indikator_Perubahan_Persil(object):

    def __init__(self):
        self.label = "Hapus Indikator Perubahan Persil"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):

        indikator_layer = arcpy.Parameter(
            displayName="Layer Indikator Perubahan Persil",
            name="indikator_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )

        return [indikator_layer]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):

        messages.addMessage(
            "== Proses dimulai =="
        )

        # =====================================================
        # PARAMETER
        # =====================================================

        peta_indikator = (
            parameters[0].valueAsText
        )

        peta_indikator_temp = (
            "Indikator_Perubahan_Persil_temp"
        )

        # =====================================================
        # CEK SELEKSI
        # =====================================================

        ada_seleksi = len(
            arcpy.Describe(
                peta_indikator
            ).FIDSet
        )

        # =====================================================
        # HAPUS FEATURE TERPILIH
        # =====================================================

        if ada_seleksi > 0:

            messages.addMessage(
                "== Menghapus feature terpilih =="
            )

            if arcpy.Exists(
                peta_indikator_temp
            ):

                try:
                    arcpy.management.Delete(
                        peta_indikator_temp
                    )
                except:
                    pass

            arcpy.management.MakeFeatureLayer(
                peta_indikator,
                peta_indikator_temp
            )

            arcpy.management.DeleteFeatures(
                peta_indikator_temp
            )

            try:

                arcpy.management.Delete(
                    peta_indikator_temp
                )

            except:
                pass

            messages.addMessage(
                "== Feature berhasil dihapus =="
            )

        else:

            messages.addWarningMessage(
                "== Tidak ada feature yang terseleksi =="
            )

        messages.addMessage(
            "== Proses selesai =="
        )

        return

class Update_Indikator_Perubahan_Persil(object):

    def __init__(self):
        self.label = "Update Indikator Perubahan Persil"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):

        radius = arcpy.Parameter(
            displayName="Radius Toleransi",
            name="radius",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input"
        )

        output_layer = arcpy.Parameter(
            displayName="Output Layer",
            name="output_layer",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [
            radius,
            output_layer
        ]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):

        import arcpy
        import os
        import math

        arcpy.env.overwriteOutput = True

        messages.addMessage(
            "== Proses dimulai =="
        )

        # =====================================================
        # LOAD CONFIG
        # =====================================================

        configs = persil.get_config_values()

        dataset_path = (
            configs["project_config"]["dataset_path"]
        )

        appdata = os.path.dirname(
            os.path.dirname(
                os.path.realpath(__file__)
            )
        )

        # =====================================================
        # PARAMETER
        # =====================================================

        radius = parameters[0].value

        toleransi_m2 = (
            math.pi * (radius ** 2)
        )

        # =====================================================
        # DATASET
        # =====================================================

        peta_baru = "Persil_Baru"
        peta_lama = "Persil_Lama"
        peta_indikator = (
            "Indikator_Perubahan_Persil"
        )

        peta_indikator_path = os.path.join(
            dataset_path,
            peta_indikator
        )

        # =====================================================
        # MEMORY WORKSPACE
        # =====================================================

        peta_indikator_update_path = (
            r"in_memory\Peta_Indikator_Update"
        )

        peta_indikator_lama_path = (
            r"in_memory\Peta_Indikator_Lama"
        )

        peta_indikator_akhir_path = (
            r"in_memory\Indikator_Akhir"
        )

        peta_update_path = os.path.join(
            dataset_path,
            peta_baru
        )

        peta_lama_path = os.path.join(
            dataset_path,
            peta_lama
        )

        # =====================================================
        # DELETE MEMORY
        # =====================================================

        memory_layers = [
            peta_indikator_update_path,
            peta_indikator_lama_path,
            peta_indikator_akhir_path
        ]

        for lyr in memory_layers:

            if arcpy.Exists(lyr):

                try:
                    arcpy.management.Delete(
                        lyr
                    )
                except:
                    pass

        # =====================================================
        # JOIN DENGAN PERSIL UPDATE
        # =====================================================

        messages.addMessage(
            "== Join dengan Persil Update =="
        )

        arcpy.analysis.SpatialJoin(
            peta_indikator_path, 
            peta_update_path, 
            peta_indikator_update_path, 
                           "JOIN_ONE_TO_ONE", "KEEP_ALL", 
                           "OBJECTID \"OBJECTID\" true true false 9 Long 0 9 ,First,#," + 
                           peta_indikator_path + ",OBJECTID,-1,-1;NIB \"NIB\" true true false 5 Long 0 0 ,First,#," + 
                           peta_indikator_path + ",NIB,-1,-1;IdBidang \"IdBidang\" true true false 9 Long 0 9 ,First,#," + 
                           peta_indikator_path + ",IdBidang,-1,-1;Predicted \"Predicted\" true true false 19 Double 0 0 ,First,#," + 
                           peta_indikator_path + ",Predicted,-1,-1;Shape_Area \"Shape_Area\" true true false 19 Double 0 0 ,First,#," + 
                           peta_indikator_path + ",Shape_Area,-1,-1;ls_asal \"ls_asal\" true true false 19 Double 0 0 ,First,#," + 
                           peta_indikator_path + ",ls_asal,-1,-1;ls_tnh \"ls_tnh\" true true false 19 Double 0 0 ,First,#," + 
                           peta_indikator_path + ",ls_tnh,-1,-1;sim_sts_2b \"sim_sts_2b\" true true false 254 Text 0 0 ,First,#," + 
                           peta_indikator_path + ",sim_sts_2b,-1,-1;ls_dr_baru \"ls_dr_baru\" true true false 50 Double 0 0 ,First,#," + 
                           peta_update_path + ",ls_asal,-1,-1; cluster \"cluster\" true true false 2 Short 0 0,First,#," + 
                           #peta_indikator_update_path + ",cluster,-1,-1", "WITHIN", "", "")
                           peta_indikator_update_path + ",cluster,-1,-1", "INTERSECT", "", "")

        list_field_update = [
            f.name
            for f in arcpy.ListFields(
                peta_indikator_update_path
            )
        ]

        if "sts_persil" not in list_field_update:

            arcpy.management.AddField(
                peta_indikator_update_path,
                "sts_persil",
                "TEXT"
            )

        if "selisih_ba" not in list_field_update:

            arcpy.management.AddField(
                peta_indikator_update_path,
                "selisih_ba",
                "DOUBLE"
            )

        exp = (
            "myabs(!ls_asal!, !ls_dr_baru!)"
        )

        code_block = """
import math

def myabs(asal, baru):

    if asal is None:
        asal = 0

    if baru is None:
        baru = 0

    return math.fabs(asal - baru)
"""

        arcpy.management.CalculateField(
            peta_indikator_update_path,
            "selisih_ba",
            exp,
            "PYTHON3",
            code_block
        )

        exp = (
            f"get(!selisih_ba!, {toleransi_m2})"
        )

        code_block = """
def get(b, toleransi):

    if b > toleransi:
        return 'update'
    else:
        return 'tetap'
"""

        arcpy.management.CalculateField(
            peta_indikator_update_path,
            "sts_persil",
            exp,
            "PYTHON3",
            code_block
        )

        # =====================================================
        # JOIN DENGAN PERSIL LAMA
        # =====================================================

        messages.addMessage(
            "== Join dengan Persil Lama =="
        )

        arcpy.analysis.SpatialJoin(
            peta_indikator_path, 
            peta_lama_path, 
            peta_indikator_lama_path,
                           "JOIN_ONE_TO_ONE", "KEEP_ALL", "OBJECTID \"OBJECTID\" true true false 9 Long 0 9 ,First,#," +
                           peta_indikator_path + ",OBJECTID,-1,-1;NIB \"NIB\" true true false 5 Long 0 0 ,First,#," +
                           peta_indikator_path + ",NIB,-1,-1;IdBidang \"IdBidang\" true true false 9 Long 0 9 ,First,#," +
                           peta_indikator_path + ",IdBidang,-1,-1;Predicted \"Predicted\" true true false 19 Double 0 0 ,First,#," +
                           peta_indikator_path + ",Predicted,-1,-1;Shape_Area \"Shape_Area\" true true false 19 Double 0 0 ,First,#," +
                           peta_indikator_path + ",Shape_Area,-1,-1;ls_asal \"ls_asal\" true true false 19 Double 0 0 ,First,#," +
                           peta_indikator_path + ",ls_asal,-1,-1;ls_tnh \"ls_tnh\" true true false 19 Double 0 0 ,First,#," +
                           peta_indikator_path + ",ls_tnh,-1,-1;sim_sts_2b \"sim_sts_2b\" true true false 254 Text 0 0 ,First,#," +
                           peta_indikator_path + ",sim_sts_2b,-1,-1;ls_dr_lama \"ls_dr_lama\" true true false 50 Double 0 0 ,First,#," +
                           #peta_lama_path + ",ls_asal,-1,-1", "WITHIN", "", "")
                           peta_lama_path + ",ls_asal,-1,-1", "INTERSECT", "", "")

        list_field_lama = [
            f.name
            for f in arcpy.ListFields(
                peta_indikator_lama_path
            )
        ]

        if "sts_persil" not in list_field_lama:

            arcpy.management.AddField(
                peta_indikator_lama_path,
                "sts_persil",
                "TEXT"
            )

        if "selisih_ba" not in list_field_lama:

            arcpy.management.AddField(
                peta_indikator_lama_path,
                "selisih_ba",
                "DOUBLE"
            )

        exp = (
            "myabs(!ls_asal!, !ls_dr_lama!)"
        )

        code_block = """
import math

def myabs(asal, lama):

    if asal is None:
        asal = 0

    if lama is None:
        lama = asal

    return math.fabs(asal - lama)
"""

        arcpy.management.CalculateField(
            peta_indikator_lama_path,
            "selisih_ba",
            exp,
            "PYTHON3",
            code_block
        )

        exp = (
            f"get(!selisih_ba!, {toleransi_m2})"
        )

        code_block = """
def get(b, toleransi):

    if b > toleransi:
        return 'update'
    else:
        return 'tetap'
"""

        arcpy.management.CalculateField(
            peta_indikator_lama_path,
            "sts_persil",
            exp,
            "PYTHON3",
            code_block
        )

        # =====================================================
        # JOIN FINAL
        # =====================================================

        messages.addMessage(
            "== Join dengan Persil Lama dan Update =="
        )

        fields = arcpy.ListFields(
            peta_indikator_lama_path,
            "cluster",
            "SHORT"
        )

        if len(fields) == 0:

            arcpy.management.AddField(
                peta_indikator_lama_path,
                "cluster",
                "SHORT"
            )

        arcpy.analysis.SpatialJoin(peta_indikator_lama_path, 
                                   peta_indikator_update_path, 
                           peta_indikator_akhir_path, "JOIN_ONE_TO_ONE", "KEEP_COMMON", 
                           "NIB \"NIB\" true true false 5 Long 0 0 ,First,#," + 
                           peta_indikator_lama_path + ",NIB,-1,-1;IdBidang \"IdBidang\" true true false 9 Long 0 9 ,First,#," + 
                           peta_indikator_lama_path + ",IdBidang,-1,-1;ls_asal \"ls_asal\" true true false 19 Double 0 0 ,First,#," + 
                           peta_indikator_lama_path + ",ls_asal,-1,-1;sim_sts_2b \"sim_sts_2b\" true true false 254 Text 0 0 ,First,#," + 
                           peta_indikator_lama_path + ",sim_sts_2b,-1,-1;ls_dr_lama \"ls_dr_lama\" true true false 19 Double 0 0 ,First,#," + 
                           peta_lama_path + ",ls_asal,-1,-1;sts_per_la \"sts_per_la\" true true false 254 Text 0 0 ,First,#," + 
                           peta_indikator_lama_path + ",sts_persil,-1,-1;selisih_la \"selisih_la\" true true false 19 Double 0 0 ,First,#," + 
                           peta_indikator_lama_path + ",selisih_ba,-1,-1;ls_dr_baru \"ls_dr_baru\" true true false 50 Double 0 0 ,First,#," + 
                           peta_indikator_update_path + ",ls_dr_baru,-1,-1;sts_per_ba \"sts_per_ba\" true true false 50 Text 0 0 ,First,#," + 
                           peta_indikator_update_path + ",sts_persil,-1,-1;selisih_up \"selisih_up\" true true false 50 Double 0 0 ,First,#," + 
                           peta_indikator_update_path + ",selisih_ba,-1,-1;cluster \"cluster\" true true false 2 Short 0 0,First,#," + 
                           peta_indikator_update_path + ",cluster,-1,-1", "WITHIN", "", "")
                           #peta_indikator_update_path + ",cluster,-1,-1", "INTERSECT", "", "")


        list_field_akhir = [
            f.name
            for f in arcpy.ListFields(
                peta_indikator_akhir_path
            )
        ]

        if "status_per" not in list_field_akhir:

            arcpy.management.AddField(
                peta_indikator_akhir_path,
                "status_per",
                "TEXT"
            )

        exp = (
            "get(!sts_per_la!, !sts_per_ba!)"
        )

        code_block = """
def get(a, b):

    if a == 'tetap' and b == 'tetap':
        return 'tetap'
    else:
        return 'update'
"""

        arcpy.management.CalculateField(
            peta_indikator_akhir_path,
            "status_per",
            exp,
            "PYTHON3",
            code_block
        )

        # =====================================================
        # DELETE FIELD
        # =====================================================

        arcpy.management.DeleteField(
            peta_indikator_akhir_path,
            [
                "ls_dr_lama",
                "sts_per_la",
                "selisih_la",
                "ls_dr_baru",
                "sts_per_ba",
                "selisih_up",
                "cluster"
            ]
        )

        # =====================================================
        # OUTPUT FINAL
        # =====================================================

        if arcpy.Exists(
            peta_indikator_path
        ):

            try:
                arcpy.management.Delete(
                    peta_indikator_path
                )
            except:
                pass

        arcpy.management.CopyFeatures(
            peta_indikator_akhir_path,
            peta_indikator_path
        )

        # =====================================================
        # SYMBOLOGY
        # =====================================================

        sim_indikator_akhir = os.path.join(
            appdata,
            "Simbologi_Persil_Updating_Final.lyr"
        )

        if arcpy.Exists(
            "Indikator_Perubahan_Persil"
        ):

            try:
                arcpy.management.Delete(
                    "Indikator_Perubahan_Persil"
                )
            except:
                pass

        arcpy.management.MakeFeatureLayer(
            peta_indikator_path,
            "Indikator_Perubahan_Persil"
        )

        if os.path.exists(
            sim_indikator_akhir
        ):

            arcpy.management.ApplySymbologyFromLayer(
                "Indikator_Perubahan_Persil",
                sim_indikator_akhir
            )

        # =====================================================
        # OUTPUT PARAMETER
        # =====================================================

        parameters[1].value = (
            "Indikator_Perubahan_Persil"
        )

        messages.addMessage(
            "== Proses selesai =="
        )

        return

class Set_Status_Perubahan_Persil(object):

    def __init__(self):
        self.label = "Set Status Perubahan Persil"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):

        status_perubahan = arcpy.Parameter(
            displayName="Status Perubahan",
            name="status_perubahan",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )

        status_perubahan.filter.list = [
            "tetap",
            "update"
        ]

        return [status_perubahan]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):

        arcpy.env.overwriteOutput = True

        messages.addMessage(
            "== Proses dimulai =="
        )

        val = parameters[0].valueAsText

        configs = persil.get_config_values()

        dataset_path = (
            configs["project_config"]["dataset_path"]
        )

        status_per = os.path.join(
            dataset_path,
            "Indikator_Perubahan_Persil"
        )

        if not arcpy.Exists(
            status_per
        ):

            messages.addErrorMessage(
                "== Layer Indikator_Perubahan_Persil tidak ditemukan =="
            )

            raise arcpy.ExecuteError


        sampel_fields = [
            f.name
            for f in arcpy.ListFields(
                status_per
            )
        ]

        if "status_per" not in sampel_fields:

            messages.addErrorMessage(
                "== Field status_per tidak ditemukan =="
            )

            raise arcpy.ExecuteError

        messages.addMessage(
            "== Mengupdate status perubahan persil =="
        )

        arcpy.management.CalculateField(
            status_per,
            "status_per",
            f'"{val}"',
            "PYTHON3"
        )

        messages.addMessage(
            "== Status berhasil diperbarui =="
        )

        messages.addMessage(
            "== Proses selesai =="
        )

        return

class Persil_Cluster(object):

    def __init__(self):

        self.label = "Persil Cluster"
        self.description = ""
        self.canRunInBackground = False

    # =====================================================
    # PARAMETER
    # =====================================================

    def getParameterInfo(self):

        param_cluster = arcpy.Parameter(
            displayName="Nomor Cluster",
            name="cluster_update",
            datatype="GPLong",
            parameterType="Required",
            direction="Input"
        )

        output_layer = arcpy.Parameter(
            displayName="Output Persil",
            name="output_layer",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [
            param_cluster,
            output_layer
        ]

    def isLicensed(self):
        return True

    def updateParameters(
        self,
        parameters
    ):
        return

    def updateMessages(
        self,
        parameters
    ):
        return

    # =====================================================
    # HELPER
    # =====================================================

    def delete_if_exists(
        self,
        path
    ):

        if arcpy.Exists(path):

            try:

                arcpy.management.Delete(
                    path
                )

            except Exception:

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

    # =====================================================
    # EXECUTE
    # =====================================================

    def execute(
        self,
        parameters,
        messages
    ):

        import os
        import arcpy

        arcpy.env.overwriteOutput = True

        messages.addMessage(
            "== Proses dimulai =="
        )

        # =================================================
        # PARAMETER
        # =================================================

        cluster_update = int(
            parameters[0].value
        )

        # =================================================
        # CONFIG
        # =================================================

        configs = (
            persil.get_config_values()
        )

        dataset_path = (
            configs["project_config"]["dataset_path"]
        )

        # =================================================
        # APPDATA
        # =================================================

        appdata = os.path.dirname(
            os.path.dirname(
                os.path.realpath(__file__)
            )
        )

        # =================================================
        # DATASET
        # =================================================

        persil_name = (
            "Indikator_Perubahan_Persil"
        )

        persil_path = os.path.join(
            dataset_path,
            persil_name
        )

        # =================================================
        # VALIDASI
        # =================================================

        if not arcpy.Exists(
            persil_path
        ):

            messages.addErrorMessage(
                (
                    "Feature class "
                    "Indikator_Perubahan_Persil "
                    "tidak ditemukan"
                )
            )

            raise arcpy.ExecuteError

        # =================================================
        # VALIDASI SELEKSI
        # =================================================

        selected_count = len(
            arcpy.Describe(
                persil_name
            ).FIDSet
        )

        if selected_count <= 0:

            messages.addWarningMessage(
                (
                    "Tidak ada "
                    "fitur yang dipilih"
                )
            )

            return

        # =================================================
        # FIELD CLUSTER
        # =================================================

        self.add_field_if_not_exists(
            persil_path,
            "clusternew",
            "SHORT"
        )

        # =================================================
        # UPDATE CLUSTER
        # =================================================

        messages.addMessage(
            (
                f"== Update cluster "
                f"{cluster_update} =="
            )
        )

        updated_count = 0

        with arcpy.da.UpdateCursor(
            persil_name,
            ["clusternew"]
        ) as cursor:

            for row in cursor:

                row[0] = (
                    cluster_update
                )

                cursor.updateRow(
                    row
                )

                updated_count += 1

        messages.addMessage(
            (
                f"{updated_count} "
                f"fitur berhasil "
                f"diupdate"
            )
        )

        # =================================================
        # REFRESH LAYER
        # =================================================

        self.delete_if_exists(
            persil_name
        )

        arcpy.management.MakeFeatureLayer(
            persil_path,
            persil_name
        )

        # =================================================
        # APPLY SYMBOLOGY
        # =================================================

        simbologi_path = os.path.join(
            appdata,
            "Indikator_Perubahan_Persil.lyrx"
        )

        if os.path.exists(
            simbologi_path
        ):

            arcpy.management.ApplySymbologyFromLayer(
                persil_name,
                simbologi_path
            )

        # =================================================
        # OUTPUT
        # =================================================

        parameters[1].value = (
            persil_name
        )

        # =================================================
        # FINISH
        # =================================================

        messages.addMessage(
            "== Proses selesai =="
        )

        return

class Reset_Persil_Cluster(object):

    def __init__(self):

        self.label = (
            "Reset Persil Cluster"
        )

        self.description = ""
        self.canRunInBackground = False

    # =====================================================
    # PARAMETER
    # =====================================================

    def getParameterInfo(self):

        output_layer = arcpy.Parameter(
            displayName="Output Persil",
            name="output_layer",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [output_layer]

    def isLicensed(self):
        return True

    def updateParameters(
        self,
        parameters
    ):
        return

    def updateMessages(
        self,
        parameters
    ):
        return

    # =====================================================
    # HELPER
    # =====================================================

    def delete_if_exists(
        self,
        path
    ):

        if arcpy.Exists(path):

            try:

                arcpy.management.Delete(
                    path
                )

            except Exception:

                pass

    # =====================================================
    # EXECUTE
    # =====================================================

    def execute(
        self,
        parameters,
        messages
    ):

        import os
        import arcpy

        arcpy.env.overwriteOutput = True

        messages.addMessage(
            "== Proses dimulai =="
        )

        # =================================================
        # CONFIG
        # =================================================

        configs = (
            persil.get_config_values()
        )

        dataset_path = (
            configs["project_config"]["dataset_path"]
        )

        # =================================================
        # APPDATA
        # =================================================

        appdata = os.path.dirname(
            os.path.dirname(
                os.path.realpath(__file__)
            )
        )

        # =================================================
        # DATASET
        # =================================================

        persil_name = (
            "Indikator_Perubahan_Persil"
        )

        persil_path = os.path.join(
            dataset_path,
            persil_name
        )

        # =================================================
        # VALIDASI
        # =================================================

        if not arcpy.Exists(
            persil_path
        ):

            messages.addErrorMessage(
                (
                    "Feature class "
                    "Indikator_Perubahan_Persil "
                    "tidak ditemukan"
                )
            )

            raise arcpy.ExecuteError

        # =================================================
        # VALIDASI SELEKSI
        # =================================================

        selected_count = len(
            arcpy.Describe(
                persil_name
            ).FIDSet
        )

        if selected_count <= 0:

            messages.addWarningMessage(
                (
                    "Tidak ada "
                    "fitur yang dipilih"
                )
            )

            return

        # =================================================
        # VALIDASI FIELD
        # =================================================

        field_names = [
            field.name
            for field in arcpy.ListFields(
                persil_path
            )
        ]

        if "clusternew" not in field_names:

            messages.addWarningMessage(
                (
                    "Field clusternew "
                    "tidak ditemukan"
                )
            )

            return

        # =================================================
        # RESET CLUSTER
        # =================================================

        messages.addMessage(
            "== Reset cluster =="
        )

        updated_count = 0

        with arcpy.da.UpdateCursor(
            persil_name,
            ["clusternew"]
        ) as cursor:

            for row in cursor:

                row[0] = None

                cursor.updateRow(
                    row
                )

                updated_count += 1

        messages.addMessage(
            (
                f"{updated_count} "
                f"fitur berhasil "
                f"direset"
            )
        )

        # =================================================
        # REFRESH LAYER
        # =================================================

        self.delete_if_exists(
            persil_name
        )

        arcpy.management.MakeFeatureLayer(
            persil_path,
            persil_name
        )

        # =================================================
        # APPLY SYMBOLOGY
        # =================================================

        simbologi_path = os.path.join(
            appdata,
            "Indikator_Perubahan_Persil.lyrx"
        )

        if os.path.exists(
            simbologi_path
        ):

            arcpy.management.ApplySymbologyFromLayer(
                persil_name,
                simbologi_path
            )

        # =================================================
        # OUTPUT
        # =================================================

        parameters[0].value = (
            persil_name
        )

        # =================================================
        # FINISH
        # =================================================

        messages.addMessage(
            "== Proses selesai =="
        )

        return

class Generate_Peta_Persil_Cluster(object):

    def __init__(self):

        self.label = (
            "Generate Peta Persil Cluster"
        )

        self.description = ""
        self.canRunInBackground = False

    # =====================================================
    # PARAMETER
    # =====================================================

    def getParameterInfo(self):

        output_layer = arcpy.Parameter(
            displayName="Output Peta Persil",
            name="output_persil",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [output_layer]

    def isLicensed(self):
        return True

    def updateParameters(
        self,
        parameters
    ):
        return

    def updateMessages(
        self,
        parameters
    ):
        return

    def delete_if_exists(
        self,
        path
    ):

        if arcpy.Exists(path):

            try:

                arcpy.management.Delete(
                    path
                )

            except Exception:

                pass

    def add_field_if_not_exists(
        self,
        feature_class,
        field_name,
        field_type,
        precision=None
    ):

        fields = [
            field.name
            for field in arcpy.ListFields(
                feature_class
            )
        ]

        if field_name not in fields:

            if precision:

                arcpy.management.AddField(
                    feature_class,
                    field_name,
                    field_type,
                    field_precision=precision
                )

            else:

                arcpy.management.AddField(
                    feature_class,
                    field_name,
                    field_type
                )

    def execute(
        self,
        parameters,
        messages
    ):

        import os
        import arcpy

        arcpy.env.overwriteOutput = True

        messages.addMessage(
            "== Proses dimulai =="
        )


        configs = (
            persil.get_config_values()
        )

        dataset_path = (
            configs["project_config"]["dataset_path"]
        )

        appdata = os.path.dirname(
            os.path.dirname(
                os.path.realpath(__file__)
            )
        )

        # =================================================
        # DATASET
        # =================================================

        peta_baru_path = os.path.join(
            dataset_path,
            "Persil_Baru"
        )

        indikator_path = os.path.join(
            dataset_path,
            "Indikator_Perubahan_Persil"
        )

        peta_persil_path = os.path.join(
            dataset_path,
            "Peta_Persil"
        )

        peta_persil = (
            "Peta_Persil"
        )


        required_fc = [
            peta_baru_path,
            indikator_path
        ]

        for fc in required_fc:

            if not arcpy.Exists(fc):

                messages.addErrorMessage(
                    (
                        f"Feature class "
                        f"{os.path.basename(fc)} "
                        f"tidak ditemukan"
                    )
                )

                raise arcpy.ExecuteError


        self.delete_if_exists(
            peta_persil_path
        )

        self.delete_if_exists(
            peta_persil
        )


        messages.addMessage(
            (
                "== Spatial Join "
                "Persil =="
            )
        )

        field_mapping = (
            f'NIB "NIB" true true false '
            f'5 Long 0 0,First,#,'
            f'{peta_baru_path},NIB,-1,-1;'

            f'IdBidang "IdBidang" '
            f'true true false 9 Long '
            f'0 9,First,#,'
            f'{peta_baru_path},'
            f'IdBidang,-1,-1;'

            f'ls_asal "ls_asal" '
            f'true true false 19 Double '
            f'0 0,First,#,'
            f'{peta_baru_path},'
            f'ls_asal,-1,-1;'

            f'status_per "status_per" '
            f'true true false 50 Text '
            f'0 0,First,#,'
            f'{indikator_path},'
            f'status_per,-1,-1;'

            f'clusternew "clusternew" '
            f'true true false 2 Short '
            f'0 0,First,#,'
            f'{indikator_path},'
            f'clusternew,-1,-1'
        )

        arcpy.analysis.SpatialJoin(
            peta_baru_path,
            indikator_path,
            peta_persil_path,
            "JOIN_ONE_TO_ONE",
            "KEEP_ALL",
            field_mapping,
            "CONTAINS"
        )

        self.add_field_if_not_exists(
            peta_persil_path,
            "PREDICTED",
            "DOUBLE",
            2
        )

        # =================================================
        # COPY PREDICTED
        # =================================================

        messages.addMessage(
            (
                "== Copy field "
                "PREDICTED =="
            )
        )

        predicted_dict = {}

        with arcpy.da.SearchCursor(
            peta_baru_path,
            [
                "IdBidang",
                "PREDICTED"
            ]
        ) as rows:

            for row in rows:

                predicted_dict[
                    row[0]
                ] = row[1]

        with arcpy.da.UpdateCursor(
            peta_persil_path,
            [
                "IdBidang",
                "PREDICTED",
                "status_per"
            ]
        ) as rows:

            for row in rows:

                bidang_id = row[0]

                if bidang_id in predicted_dict:

                    row[1] = (
                        predicted_dict[
                            bidang_id
                        ]
                    )

                if row[2] == "update":

                    row[1] = None

                rows.updateRow(
                    row
                )

        # =================================================
        # DEFAULT STATUS
        # =================================================

        messages.addMessage(
            (
                "== Update status "
                "default =="
            )
        )

        with arcpy.da.UpdateCursor(
            peta_persil_path,
            [
                "status_per",
                "IdBidang",
                "OBJECTID"
            ]
        ) as rows:

            for row in rows:

                if not row[0]:

                    row[0] = "tetap"
                    row[1] = row[2]

                    rows.updateRow(
                        row
                    )

        # =================================================
        # REFRESH LAYER
        # =================================================

        self.delete_if_exists(
            peta_persil
        )

        arcpy.management.MakeFeatureLayer(
            peta_persil_path,
            peta_persil
        )

        # =================================================
        # APPLY SYMBOLOGY
        # =================================================

        simbologi_path = os.path.join(
            appdata,
            "SimbologiPetaPersil.lyr"
        )

        if os.path.exists(
            simbologi_path
        ):

            arcpy.management.ApplySymbologyFromLayer(
                peta_persil,
                simbologi_path
            )

        # =================================================
        # OUTPUT
        # =================================================

        parameters[0].value = (
            peta_persil
        )

        # =================================================
        # HIDE LAYER
        # =================================================

        try:

            aprx = arcpy.mp.ArcGISProject(
                "CURRENT"
            )

            current_map = (
                aprx.activeMap
            )

            hidden_layers = [
                "Indikator_Perubahan_Persil",
                "Peta_Baru",
                "Peta_Lama",
                "Persil"
            ]

            for layer in current_map.listLayers():

                if layer.name in hidden_layers:

                    layer.visible = False

        except Exception:

            pass

        # =================================================
        # FINISH
        # =================================================

        messages.addMessage(
            "== Proses selesai =="
        )

        return

class Generate_Peta_Akhir(object):

    def __init__(self):

        self.label = "Generate Peta Akhir"
        self.description = ""
        self.canRunInBackground = False

    # =====================================================
    # PARAMETER
    # =====================================================

    def getParameterInfo(self):

        output_layer = arcpy.Parameter(
            displayName="Output Peta Akhir",
            name="output_peta_akhir",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [output_layer]

    def isLicensed(self):
        return True

    def updateParameters(
        self,
        parameters
    ):
        return

    def updateMessages(
        self,
        parameters
    ):
        return

    # =====================================================
    # HELPER
    # =====================================================

    def delete_if_exists(
        self,
        path
    ):

        if arcpy.Exists(path):

            try:

                arcpy.management.Delete(
                    path
                )

            except Exception:

                pass

    def add_field_if_not_exists(
        self,
        feature_class,
        field_name,
        field_type
    ):

        fields = [
            field.name.lower()
            for field in arcpy.ListFields(
                feature_class
            )
        ]

        if field_name.lower() not in fields:

            arcpy.management.AddField(
                feature_class,
                field_name,
                field_type
            )

    # =====================================================
    # EXECUTE
    # =====================================================

    def execute(
        self,
        parameters,
        messages
    ):

        import os
        import arcpy

        arcpy.env.overwriteOutput = True

        messages.addMessage(
            "== Proses dimulai =="
        )

        # =================================================
        # CONFIG
        # =================================================

        configs = (
            persil.get_config_values()
        )

        dataset_path = (
            configs["project_config"]["dataset_path"]
        )

        daftar_variabel_path = (
            configs["project_config"]["daftar_variabel_path"]
        )

        # =================================================
        # APPDATA
        # =================================================

        appdata = os.path.dirname(
            os.path.dirname(
                os.path.realpath(__file__)
            )
        )

        # =================================================
        # VARIABLE CONFIG
        # =================================================

        with open(daftar_variabel_path, "r") as f:

            json_conf = (
                json.load(f)
            )
            variable_config = json_conf['daftar_variabel']

        field_str_type = [
            "bentuk",
            "letak",
            "kls_jln",
            "elvasi",
            "zonasi"
        ]

        fields_dont_delete = []

        for item in variable_config:

            # Extract field_name from list format [display_name, field_name]
            field_name = (
                item[1]
                if isinstance(item, list) and len(item) > 1
                else None
            )

            if not field_name:
                continue

            fields_dont_delete.append(
                field_name
            )

            if (
                field_name.lower()
                in field_str_type
            ):

                fields_dont_delete.append(
                    f"s_{field_name}"
                )

        # =================================================
        # DATASET
        # =================================================

        peta_persil_path = os.path.join(
            dataset_path,
            "Peta_Persil"
        )

        peta_lama_path = os.path.join(
            dataset_path,
            "Persil_Lama"
        )

        centroid_path = os.path.join(
            dataset_path,
            "Persil_Lama_Centroid"
        )

        erase_path = os.path.join(
            dataset_path,
            "Peta_Erase"
        )

        peta_akhir_path = os.path.join(
            dataset_path,
            "Peta_Akhir"
        )

        peta_akhir_layer = (
            "Peta_Akhir"
        )

        # =================================================
        # VALIDASI
        # =================================================

        required_fc = [
            peta_persil_path,
            peta_lama_path
        ]

        for fc in required_fc:

            if not arcpy.Exists(fc):

                messages.addErrorMessage(
                    (
                        f"Feature class "
                        f"{os.path.basename(fc)} "
                        f"tidak ditemukan"
                    )
                )

                raise arcpy.ExecuteError

        # =================================================
        # CLEANUP
        # =================================================

        cleanup_items = [
            centroid_path,
            erase_path,
            peta_akhir_path,
            peta_akhir_layer
        ]

        for item in cleanup_items:

            self.delete_if_exists(
                item
            )

        # =================================================
        # CENTROID
        # =================================================

        messages.addMessage(
            (
                "== Generate centroid "
                "persil lama =="
            )
        )

        arcpy.management.FeatureToPoint(
            peta_lama_path,
            centroid_path,
            "INSIDE"
        )

        # =================================================
        # SELECT UPDATE
        # =================================================

        messages.addMessage(
            (
                "== Seleksi persil "
                "update =="
            )
        )

        temp_persil = (
            "temp_persil"
        )

        self.delete_if_exists(
            temp_persil
        )

        arcpy.management.MakeFeatureLayer(
            peta_persil_path,
            temp_persil
        )

        arcpy.management.SelectLayerByAttribute(
            temp_persil,
            "NEW_SELECTION",
            "status_per = 'update'"
        )

        # =================================================
        # ERASE
        # =================================================

        messages.addMessage(
            "== Erase centroid =="
        )

        arcpy.analysis.Erase(
            centroid_path,
            temp_persil,
            erase_path
        )

        # =================================================
        # DELETE UNUSED FIELD
        # =================================================

        messages.addMessage(
            (
                "== Hapus field "
                "tidak digunakan =="
            )
        )

        erase_fields = (
            arcpy.ListFields(
                erase_path
            )
        )

        delete_fields = []

        for field in erase_fields:

            if (
                field.type
                in ["Geometry", "OID"]
            ):

                continue

            if (
                "shape"
                in field.name.lower()
            ):

                continue

            if (
                field.name
                in fields_dont_delete
            ):

                continue

            if (
                field.name == "FID"
            ):

                continue

            delete_fields.append(
                field.name
            )

        if delete_fields:

            arcpy.management.DeleteField(
                erase_path,
                delete_fields
            )

        # =================================================
        # SPATIAL JOIN
        # =================================================

        messages.addMessage(
            "== Spatial Join =="
        )

        arcpy.analysis.SpatialJoin(
            peta_persil_path,
            erase_path,
            peta_akhir_path,
            "JOIN_ONE_TO_ONE",
            "KEEP_ALL",
            "",
            "INTERSECT"
        )

        # =================================================
        # DELETE JOIN FIELD
        # =================================================

        join_delete_fields = []

        fields = arcpy.ListFields(
            peta_akhir_path
        )

        for field in fields:

            if (
                field.name.lower().startswith(
                    "join_"
                )
                or
                field.name.lower().startswith(
                    "target_"
                )
            ):

                join_delete_fields.append(
                    field.name
                )

        if join_delete_fields:

            arcpy.management.DeleteField(
                peta_akhir_path,
                join_delete_fields
            )

        # =================================================
        # ENSURE REQUIRED FIELD
        # =================================================

        existing_fields = [
            field.name.lower()
            for field in arcpy.ListFields(
                peta_akhir_path
            )
        ]

        for field_name in fields_dont_delete:

            if (
                field_name.lower()
                not in existing_fields
            ):

                field_type = (
                    "TEXT"
                    if field_name.lower()
                    in field_str_type
                    else "DOUBLE"
                )

                arcpy.management.AddField(
                    peta_akhir_path,
                    field_name,
                    field_type
                )

        # =================================================
        # OUTPUT LAYER
        # =================================================

        self.delete_if_exists(
            peta_akhir_layer
        )

        arcpy.management.MakeFeatureLayer(
            peta_akhir_path,
            peta_akhir_layer
        )

        parameters[0].value = (
            peta_akhir_layer
        )

        # =================================================
        # CLEANUP TEMP
        # =================================================

        self.delete_if_exists(
            temp_persil
        )

        # =================================================
        # FINISH
        # =================================================

        messages.addMessage(
            "== Proses selesai =="
        )

        return

class Update_Luas_Tanah(object):

    def __init__(self):

        self.label = (
            "Update Luas Tanah"
        )

        self.description = ""
        self.canRunInBackground = False

    # =====================================================
    # PARAMETER
    # =====================================================

    def getParameterInfo(self):

        output_layer = arcpy.Parameter(
            displayName="Output Peta Akhir",
            name="output_peta_akhir",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [output_layer]

    def isLicensed(self):
        return True

    def updateParameters(
        self,
        parameters
    ):
        return

    def updateMessages(
        self,
        parameters
    ):
        return

    # =====================================================
    # HELPER
    # =====================================================

    def delete_if_exists(
        self,
        path
    ):

        if arcpy.Exists(path):

            try:

                arcpy.management.Delete(
                    path
                )

            except Exception:

                pass

    def add_field_if_not_exists(
        self,
        feature_class,
        field_name,
        field_type
    ):

        fields = [
            field.name.lower()
            for field in arcpy.ListFields(
                feature_class
            )
        ]

        if field_name.lower() not in fields:

            arcpy.management.AddField(
                feature_class,
                field_name,
                field_type
            )

    # =====================================================
    # EXECUTE
    # =====================================================

    def execute(
        self,
        parameters,
        messages
    ):

        import os
        import arcpy

        arcpy.env.overwriteOutput = True

        messages.addMessage(
            "== Proses dimulai =="
        )

        # =================================================
        # CONFIG
        # =================================================

        configs = (
            persil.get_config_values()
        )

        dataset_path = (
            configs["project_config"]["dataset_path"]
        )

        # =================================================
        # DATASET
        # =================================================

        peta_persil_name = (
            "Peta_Akhir"
        )

        peta_persil_path = os.path.join(
            dataset_path,
            peta_persil_name
        )

        # =================================================
        # VALIDASI
        # =================================================

        if not arcpy.Exists(
            peta_persil_path
        ):

            messages.addErrorMessage(
                (
                    "Feature class "
                    "Peta_Akhir "
                    "tidak ditemukan"
                )
            )

            raise arcpy.ExecuteError

        # =================================================
        # ADD FIELD
        # =================================================

        self.add_field_if_not_exists(
            peta_persil_path,
            "ls_tnh",
            "DOUBLE"
        )

        # =================================================
        # CALCULATE AREA
        # =================================================

        messages.addMessage(
            (
                "== Hitung luas "
                "tanah =="
            )
        )

        arcpy.management.CalculateField(
            peta_persil_path,
            "ls_tnh",
            "!shape.area!",
            "PYTHON3"
        )

        # =================================================
        # REFRESH LAYER
        # =================================================

        self.delete_if_exists(
            peta_persil_name
        )

        arcpy.management.MakeFeatureLayer(
            peta_persil_path,
            peta_persil_name
        )

        # =================================================
        # OUTPUT
        # =================================================

        parameters[0].value = (
            peta_persil_name
        )

        # =================================================
        # FINISH
        # =================================================

        messages.addMessage(
            "== Proses selesai =="
        )

        return

class Analisis_Bentuk_Persil(object):

    def __init__(self):

        self.label = (
            "Analisis Bentuk Persil"
        )

        self.description = ""
        self.canRunInBackground = False

    # =====================================================
    # PARAMETER
    # =====================================================

    def getParameterInfo(self):

        output_layer = arcpy.Parameter(
            displayName="Output Persil Update",
            name="output_persil",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [output_layer]

    def isLicensed(self):
        return True

    def updateParameters(
        self,
        parameters
    ):
        return

    def updateMessages(
        self,
        parameters
    ):
        return

    # =====================================================
    # HELPER
    # =====================================================

    def delete_if_exists(
        self,
        path
    ):

        if arcpy.Exists(path):

            try:

                arcpy.management.Delete(
                    path
                )

            except Exception:

                pass

    def add_field_if_not_exists(
        self,
        feature_class,
        field_name,
        field_type
    ):

        field_names = [
            field.name.lower()
            for field in arcpy.ListFields(
                feature_class
            )
        ]

        if field_name.lower() not in field_names:

            arcpy.management.AddField(
                feature_class,
                field_name,
                field_type
            )

    def calculate_azimuth(
        self,
        x_start,
        y_start,
        x_end,
        y_end
    ):

        import math

        delta_y = (
            y_end - y_start
        )

        delta_x = (
            x_end - x_start
        )

        if delta_y == 0:

            if delta_x >= 0:
                azimuth = 90

            else:
                azimuth = -90

        else:

            azimuth = math.atan(
                delta_x / delta_y
            ) * (
                180 / math.pi
            )

        if azimuth < -45:

            atrans = (
                azimuth + 180
            )

        elif (
            azimuth >= -45
            and
            azimuth <= 45
        ):

            atrans = (
                azimuth + 90
            )

        else:

            atrans = azimuth

        return (
            azimuth,
            atrans
        )

    # =====================================================
    # EXECUTE
    # =====================================================

    def execute(
        self,
        parameters,
        messages
    ):

        import os
        import arcpy

        arcpy.env.overwriteOutput = True

        messages.addMessage(
            "== Proses dimulai =="
        )

        # =================================================
        # CONFIG
        # =================================================

        configs = (
            persil.get_config_values()
        )

        dataset_path = (
            configs["project_config"]["dataset_path"]
        )

        # =================================================
        # APPDATA
        # =================================================

        appdata = os.path.dirname(
            os.path.dirname(
                os.path.realpath(__file__)
            )
        )

        simbologi_path = os.path.join(
            appdata,
            "SimbologiBentukPersil.lyr"
        )

        # =================================================
        # DATASET
        # =================================================

        peta_akhir_path = os.path.join(
            dataset_path,
            "Peta_Akhir"
        )

        persil_baru_path = os.path.join(
            dataset_path,
            "Persil_Baru"
        )

        persil_update_path = os.path.join(
            dataset_path,
            "Persil_Update"
        )

        persil_line_path = os.path.join(
            dataset_path,
            "PersilLineUpdate"
        )

        # Jika dataset_path menunjuk ke Feature Dataset di dalam GDB,
        # root GDB bisa saja masih memiliki feature class dengan nama sama.
        gdb_root = dataset_path
        try:
            desc = arcpy.Describe(dataset_path)
            if desc.dataType == "FeatureDataset":
                gdb_root = os.path.dirname(dataset_path)
        except Exception:
            pass

        root_persil_baru_path = os.path.join(
            gdb_root,
            "Persil_Baru"
        )

        persil_split_path = os.path.join(
            dataset_path,
            "PersilSplitUpdate"
        )

        dissolve_path = os.path.join(
            dataset_path,
            "PersilDissolveUpdateBentuk"
        )

        # =================================================
        # VALIDASI
        # =================================================

        if not arcpy.Exists(
            peta_akhir_path
        ):

            messages.addErrorMessage(
                (
                    "Feature class "
                    "Peta_Akhir "
                    "tidak ditemukan"
                )
            )

            raise arcpy.ExecuteError

        # =================================================
        # CLEANUP
        # =================================================

        cleanup_items = [
            persil_baru_path,
            root_persil_baru_path,
            persil_update_path,
            persil_line_path,
            persil_split_path,
            dissolve_path,
            "Persil_Update"
        ]

        for item in cleanup_items:

            self.delete_if_exists(
                item
            )

        # =================================================
        # GENERATE ID BIDANG
        # =================================================

        messages.addMessage(
            (
                "== Generate "
                "IdBidang =="
            )
        )

        max_id_bidang = 0

        with arcpy.da.SearchCursor(
            peta_akhir_path,
            ["IdBidang"]
        ) as rows:

            for row in rows:

                if row[0]:

                    max_id_bidang = max(
                        int(row[0]),
                        max_id_bidang
                    )

        with arcpy.da.UpdateCursor(
            peta_akhir_path,
            ["IdBidang"],
            "IdBidang = 0"
        ) as rows:

            for row in rows:

                max_id_bidang += 1

                row[0] = (
                    max_id_bidang
                )

                rows.updateRow(
                    row
                )

        # =================================================
        # COPY PERSIL BARU
        # =================================================

        messages.addMessage(
            (
                "== Copy persil "
                "baru =="
            )
        )

        arcpy.conversion.FeatureClassToFeatureClass(
            peta_akhir_path,
            dataset_path,
            "Persil_Baru"
        )

        # =================================================
        # COPY UPDATE ONLY
        # =================================================

        temp_update = (
            "temp_persil_update"
        )

        self.delete_if_exists(
            temp_update
        )

        arcpy.management.MakeFeatureLayer(
            persil_baru_path,
            temp_update,
            "status_per = 'update'"
        )

        arcpy.management.CopyFeatures(
            temp_update,
            persil_update_path
        )

        # =================================================
        # POLYGON TO LINE
        # =================================================

        messages.addMessage(
            (
                "== Polygon to line =="
            )
        )

        arcpy.management.PolygonToLine(
            persil_update_path,
            persil_line_path,
            "IGNORE_NEIGHBORS"
        )

        arcpy.management.SplitLine(
            persil_line_path,
            persil_split_path
        )

        # =================================================
        # FIELD
        # =================================================

        field_definitions = [
            ("LebarSisi", "DOUBLE"),
            ("XStart", "DOUBLE"),
            ("XEnd", "DOUBLE"),
            ("YStart", "DOUBLE"),
            ("YEnd", "DOUBLE"),
            ("Azimuth", "DOUBLE"),
            ("ATrans", "DOUBLE")
        ]

        for field_name, field_type in field_definitions:

            self.add_field_if_not_exists(
                persil_split_path,
                field_name,
                field_type
            )

        # =================================================
        # HITUNG LEBAR SISI
        # =================================================

        arcpy.management.CalculateField(
            persil_split_path,
            "LebarSisi",
            "!shape.length!",
            "PYTHON3"
        )

        # =================================================
        # AZIMUTH
        # =================================================

        messages.addMessage(
            (
                "== Hitung azimuth =="
            )
        )

        shape_field = (
            arcpy.Describe(
                persil_split_path
            ).shapeFieldName
        )

        with arcpy.da.UpdateCursor(
            persil_split_path,
            [
                shape_field,
                "XStart",
                "XEnd",
                "YStart",
                "YEnd",
                "Azimuth",
                "ATrans"
            ]
        ) as rows:

            for row in rows:

                geometry = row[0]

                if isinstance(geometry, tuple):
                    if len(geometry) == 1:
                        geometry = geometry[0]
                    elif len(geometry) == 2 and all(
                        isinstance(v, (int, float)) for v in geometry
                    ):
                        geometry = arcpy.PointGeometry(
                            arcpy.Point(
                                geometry[0],
                                geometry[1]
                            )
                        )

                x_start = (
                    geometry.firstPoint.X
                )

                y_start = (
                    geometry.firstPoint.Y
                )

                x_end = (
                    geometry.lastPoint.X
                )

                y_end = (
                    geometry.lastPoint.Y
                )

                azimuth, atrans = (
                    self.calculate_azimuth(
                        x_start,
                        y_start,
                        x_end,
                        y_end
                    )
                )

                row[1] = x_start
                row[2] = x_end
                row[3] = y_start
                row[4] = y_end
                row[5] = azimuth
                row[6] = atrans

                rows.updateRow(
                    row
                )

        # =================================================
        # DISSOLVE
        # =================================================

        messages.addMessage(
            "== Dissolve =="
        )

        arcpy.management.Dissolve(
            persil_split_path,
            dissolve_path,
            ["IdBidang"],
            [["ATrans", "RANGE"]],
            "MULTI_PART",
            "DISSOLVE_LINES"
        )

        # =================================================
        # FIELD PERSIL
        # =================================================

        self.add_field_if_not_exists(
            persil_update_path,
            "bentuk",
            "TEXT"
        )

        self.add_field_if_not_exists(
            persil_update_path,
            "s_bentuk",
            "DOUBLE"
        )

        fields = [
            field.name
            for field in arcpy.ListFields(
                persil_update_path
            )
        ]

        if "Range_ATrans" in fields:

            arcpy.management.DeleteField(
                persil_update_path,
                "Range_ATrans"
            )

        # =================================================
        # JOIN
        # =================================================

        arcpy.management.JoinField(
            persil_update_path,
            "IdBidang",
            dissolve_path,
            "IdBidang",
            ["Range_ATrans"]
        )

        # =================================================
        # HITUNG BENTUK
        # =================================================

        messages.addMessage(
            (
                "== Hitung bentuk "
                "persil =="
            )
        )

        with arcpy.da.UpdateCursor(
            persil_update_path,
            [
                "Range_ATrans",
                "bentuk",
                "s_bentuk"
            ]
        ) as rows:

            for row in rows:

                nilai = row[0]

                if nilai is None:

                    continue

                if nilai < 16.3:

                    row[1] = (
                        "Segi Empat "
                        "Beraturan"
                    )

                    row[2] = 4

                elif (
                    nilai >= 16.3
                    and nilai <= 58
                ):

                    row[1] = (
                        "Segi Empat "
                        "Tidak Beraturan"
                    )

                    row[2] = 3

                else:

                    row[1] = (
                        "Segi Banyak "
                        "Tidak Beraturan"
                    )

                    row[2] = 1

                rows.updateRow(
                    row
                )

        # =================================================
        # POINT COUNT
        # =================================================

        arcpy.management.AddGeometryAttributes(
            persil_update_path,
            "POINT_COUNT"
        )

        with arcpy.da.UpdateCursor(
            persil_update_path,
            [
                "bentuk",
                "s_bentuk",
                "PNT_COUNT"
            ]
        ) as rows:

            for row in rows:

                if (
                    row[2]
                    and
                    int(row[2]) == 4
                ):

                    row[0] = (
                        "Segi Tiga"
                    )

                    row[1] = 2

                    rows.updateRow(
                        row
                    )

        # =================================================
        # DELETE TEMP FIELD
        # =================================================

        fields = [
            field.name
            for field in arcpy.ListFields(
                persil_update_path
            )
        ]

        if "PNT_COUNT" in fields:

            arcpy.management.DeleteField(
                persil_update_path,
                "PNT_COUNT"
            )

        # =================================================
        # OUTPUT
        # =================================================

        self.delete_if_exists(
            "Persil_Update"
        )

        arcpy.management.MakeFeatureLayer(
            persil_update_path,
            "Persil_Update"
        )

        # =================================================
        # SYMBOLOGY
        # =================================================

        if os.path.exists(
            simbologi_path
        ):

            arcpy.management.ApplySymbologyFromLayer(
                "Persil_Update",
                simbologi_path
            )

        parameters[0].value = (
            "Persil_Update"
        )

        # =================================================
        # CLEANUP
        # =================================================

        self.delete_if_exists(
            temp_update
        )

        # =================================================
        # FINISH
        # =================================================

        messages.addMessage(
            "== Proses selesai =="
        )

        return

class Edit_Bentuk_Persil(object):

    def __init__(self):

        self.label = (
            "Edit Bentuk Persil"
        )

        self.description = ""
        self.canRunInBackground = False

    # =====================================================
    # PARAMETER
    # =====================================================

    def getParameterInfo(self):

        param_bentuk = arcpy.Parameter(
            displayName="Bentuk Persil",
            name="bentuk",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )

        param_bentuk.filter.list = [
            "Segi Banyak Tidak Beraturan",
            "Segi Tiga",
            "Segi Empat Tidak Beraturan",
            "Segi Empat Beraturan"
        ]

        output_layer = arcpy.Parameter(
            displayName="Output Persil",
            name="output_persil",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [
            param_bentuk,
            output_layer
        ]

    def isLicensed(self):
        return True

    def updateParameters(
        self,
        parameters
    ):
        return

    def updateMessages(
        self,
        parameters
    ):
        return

    # =====================================================
    # HELPER
    # =====================================================

    def get_skor_bentuk(
        self,
        bentuk
    ):

        mapping = {

            "Segi Banyak Tidak Beraturan": 1,
            "Segi Tiga": 2,
            "Segi Empat Tidak Beraturan": 3,
            "Segi Empat Beraturan": 4

        }

        return mapping.get(
            bentuk,
            1
        )

    def delete_if_exists(
        self,
        path
    ):

        if arcpy.Exists(path):

            try:

                arcpy.management.Delete(
                    path
                )

            except Exception:

                pass

    # =====================================================
    # EXECUTE
    # =====================================================

    def execute(
        self,
        parameters,
        messages
    ):

        import arcpy

        arcpy.env.overwriteOutput = True

        messages.addMessage(
            "== Proses dimulai =="
        )

        # =================================================
        # PARAMETER
        # =================================================

        bentuk = (
            parameters[0].valueAsText
        )

        skor_bentuk = (
            self.get_skor_bentuk(
                bentuk
            )
        )

        # =================================================
        # FEATURE CLASS
        # =================================================

        persil_update = (
            "Persil_Update"
        )

        # =================================================
        # VALIDASI
        # =================================================

        if not arcpy.Exists(
            persil_update
        ):

            messages.addErrorMessage(
                (
                    "Layer "
                    "Persil_Update "
                    "tidak ditemukan"
                )
            )

            raise arcpy.ExecuteError

        fields = [
            field.name.lower()
            for field in arcpy.ListFields(
                persil_update
            )
        ]

        required_fields = [
            "bentuk",
            "s_bentuk"
        ]

        missing_fields = [
            field
            for field in required_fields
            if field.lower() not in fields
        ]

        if missing_fields:

            messages.addErrorMessage(
                (
                    "Field berikut "
                    "tidak ditemukan: "
                    f"{', '.join(missing_fields)}"
                )
            )

            raise arcpy.ExecuteError

        # =================================================
        # VALIDASI SELEKSI
        # =================================================

        selected_count = len(
            arcpy.Describe(
                persil_update
            ).FIDSet
        )

        if selected_count <= 0:

            messages.addWarningMessage(
                (
                    "Tidak ada "
                    "fitur yang dipilih"
                )
            )

            return

        # =================================================
        # UPDATE NILAI
        # =================================================

        messages.addMessage(
            (
                "== Update bentuk "
                "persil =="
            )
        )

        updated_count = 0

        with arcpy.da.UpdateCursor(
            persil_update,
            [
                "bentuk",
                "s_bentuk"
            ]
        ) as rows:

            for row in rows:

                row[0] = bentuk
                row[1] = float(
                    skor_bentuk
                )

                rows.updateRow(
                    row
                )

                updated_count += 1

        messages.addMessage(
            (
                f"{updated_count} "
                f"fitur berhasil "
                f"diupdate"
            )
        )

        # =================================================
        # CALCULATE FIELD
        # =================================================

        arcpy.management.CalculateField(
            persil_update,
            "bentuk",
            f'"{bentuk}"',
            "PYTHON3"
        )

        # =================================================
        # REFRESH LAYER
        # =================================================

        self.delete_if_exists(
            "Persil_Update"
        )

        arcpy.management.MakeFeatureLayer(
            "Persil_Update",
            "Persil_Update"
        )

        # =================================================
        # OUTPUT
        # =================================================

        parameters[1].value = (
            "Persil_Update"
        )

        # =================================================
        # FINISH
        # =================================================

        messages.addMessage(
            "== Proses selesai =="
        )

        return

class Simpan_Bentuk_Persil(object):

    def __init__(self):

        self.label = (
            "Simpan Bentuk Persil"
        )

        self.description = ""
        self.canRunInBackground = False

    # =====================================================
    # PARAMETER
    # =====================================================

    def getParameterInfo(self):

        output_layer = arcpy.Parameter(
            displayName="Output Persil Baru",
            name="output_persil_baru",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [output_layer]

    def isLicensed(self):
        return True

    def updateParameters(
        self,
        parameters
    ):
        return

    def updateMessages(
        self,
        parameters
    ):
        return

    # =====================================================
    # HELPER
    # =====================================================

    def delete_if_exists(
        self,
        path
    ):

        if arcpy.Exists(path):

            try:

                arcpy.management.Delete(
                    path
                )

            except Exception:

                pass

    def add_field_if_not_exists(
        self,
        feature_class,
        field_name,
        field_type,
        field_length=None
    ):

        fields = [
            field.name
            for field in arcpy.ListFields(
                feature_class
            )
        ]

        if field_name not in fields:

            if field_type == "TEXT":
                arcpy.management.AddField(
                    feature_class,
                    field_name,
                    field_type,
                    field_length=field_length or 255
                )
            else:
                arcpy.management.AddField(
                    feature_class,
                    field_name,
                    field_type
                )

    # =====================================================
    # EXECUTE
    # =====================================================

    def execute(
        self,
        parameters,
        messages
    ):

        import os
        import arcpy

        arcpy.env.overwriteOutput = True

        messages.addMessage(
            "== Proses dimulai =="
        )

        # =================================================
        # CONFIG
        # =================================================

        configs = (
            persil.get_config_values()
        )

        dataset_path = (
            configs["project_config"]["dataset_path"]
        )

        # =================================================
        # DATASET
        # =================================================

        source_name = (
            "Persil_Update"
        )

        target_name = (
            "Persil_Baru"
        )

        source_path = os.path.join(
            dataset_path,
            source_name
        )

        target_path = os.path.join(
            dataset_path,
            target_name
        )

        # =================================================
        # VALIDASI
        # =================================================

        required_feature_classes = [
            source_path,
            target_path
        ]

        for fc in required_feature_classes:

            if not arcpy.Exists(fc):

                messages.addErrorMessage(
                    (
                        f"Feature class "
                        f"{os.path.basename(fc)} "
                        f"tidak ditemukan"
                    )
                )

                raise arcpy.ExecuteError

        # =================================================
        # FIELD VALIDATION
        # =================================================

        join_fields = [
            "IdBidang",
            "bentuk",
            "s_bentuk"
        ]

        source_fields = [
            field.name
            for field in arcpy.ListFields(
                source_path
            )
        ]

        target_fields = [
            field.name
            for field in arcpy.ListFields(
                target_path
            )
        ]

        missing_source = [
            field
            for field in join_fields
            if field not in source_fields
        ]

        missing_target = [
            field
            for field in join_fields
            if field not in target_fields
        ]

        if missing_source:

            messages.addErrorMessage(
                (
                    "Field source "
                    "tidak ditemukan: "
                    f"{', '.join(missing_source)}"
                )
            )

            raise arcpy.ExecuteError

        if missing_target:

            messages.addMessage(
                (
                    "Field target tidak lengkap, "
                    "menambahkan field yang hilang pada Persil_Baru"
                )
            )

            field_defs = {
                "IdBidang": "LONG",
                "bentuk": "TEXT",
                "s_bentuk": "DOUBLE"
            }

            for field in missing_target:
                self.add_field_if_not_exists(
                    target_path,
                    field,
                    field_defs.get(field, "TEXT"),
                    255 if field == "bentuk" else None
                )

            target_fields = [
                field.name
                for field in arcpy.ListFields(
                    target_path
                )
            ]

            missing_target = [
                field
                for field in join_fields
                if field not in target_fields
            ]

            if missing_target:
                messages.addErrorMessage(
                    (
                        "Field target "
                        "tidak ditemukan: "
                        f"{', '.join(missing_target)}"
                    )
                )
                raise arcpy.ExecuteError

        # =================================================
        # LOAD SOURCE DATA
        # =================================================

        messages.addMessage(
            (
                "== Membaca data "
                "Persil_Update =="
            )
        )

        join_dictionary = {}

        with arcpy.da.SearchCursor(
            source_path,
            join_fields
        ) as rows:

            for row in rows:

                id_bidang = row[0]

                join_dictionary[
                    id_bidang
                ] = {

                    "bentuk": row[1],
                    "s_bentuk": row[2]

                }

        # =================================================
        # UPDATE TARGET
        # =================================================

        messages.addMessage(
            (
                "== Update bentuk "
                "Persil_Baru =="
            )
        )

        updated_count = 0

        with arcpy.da.UpdateCursor(
            target_path,
            join_fields
        ) as rows:

            for row in rows:

                id_bidang = row[0]

                if (
                    id_bidang
                    in join_dictionary
                ):

                    row[1] = (
                        join_dictionary[
                            id_bidang
                        ]["bentuk"]
                    )

                    row[2] = (
                        join_dictionary[
                            id_bidang
                        ]["s_bentuk"]
                    )

                    rows.updateRow(
                        row
                    )

                    updated_count += 1

        messages.addMessage(
            (
                f"{updated_count} "
                f"fitur berhasil "
                f"diupdate"
            )
        )

        # =================================================
        # REFRESH LAYER
        # =================================================

        self.delete_if_exists(
            target_name
        )

        arcpy.management.MakeFeatureLayer(
            target_path,
            target_name
        )

        # =================================================
        # DELETE FIELD
        # =================================================

        target_field_names = [
            field.name
            for field in arcpy.ListFields(
                target_name
            )
        ]

        if (
            "Shape_Leng"
            in target_field_names
        ):

            try:

                arcpy.management.DeleteField(
                    target_name,
                    "Shape_Leng"
                )

            except Exception:

                pass

        # =================================================
        # MAP CLEANUP
        # =================================================

        try:

            aprx = arcpy.mp.ArcGISProject(
                "CURRENT"
            )

            current_map = (
                aprx.activeMap
            )

            for layer in current_map.listLayers():

                try:

                    if (
                        layer.name
                        != target_name
                    ):

                        current_map.removeLayer(
                            layer
                        )

                except Exception:

                    pass

        except Exception:

            pass

        # =================================================
        # OUTPUT
        # =================================================

        parameters[0].value = (
            target_name
        )

        # =================================================
        # FINISH
        # =================================================

        messages.addMessage(
            "== Proses selesai =="
        )

        return