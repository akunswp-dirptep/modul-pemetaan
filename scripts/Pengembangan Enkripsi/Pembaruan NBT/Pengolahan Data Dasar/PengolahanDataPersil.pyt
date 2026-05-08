from datetime import datetime
import json
import sys
import arcpy, os, math

# Tambahkan parent directory ke sys.path
script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from nbtutils import constant, persil
from zntutils.document import validate_document_type, get_credentials
from zntutils.system_utils import get_user_data, renew_user_data, get_all_berkas_id, setup_user_data
from zntutils.constant import PREFERRED_BERKAS_ID, CREDENTIAL_KEY, PREFERRED_SERVER_KEY, AUTH_KEY, NAMA_PROVINSI, KAB_KOTA
from zntutils.upload_utils import upload_shapefile_to_sipenta
from zntutils import zona_layer

class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [Indikator_Perubahan_Persil]


class Indikator_Perubahan_Persil(object):

    def __init__(self):
        self.label = "Identifikasi Perubahan Persil"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):

        persil_lama = arcpy.Parameter(
            displayName="Persil Lama (Tahun Sebelumnya)",
            name="persil_lama",
            datatype="GPFeatureLayer",
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

        return [persil_lama, output_layer]

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

        messages.addMessage("== Proses dimulai ==")

        # =====================================================
        # LOAD CONFIG
        # =====================================================

        configs = persil.get_config_values()

        dataset_path = (
            configs["project_config"]["dataset_path"]
        )

        persil_path = (
            configs["persil_config"]["path"]["Persil"]
        )

        appdata = os.path.dirname(
            os.path.dirname(
                os.path.realpath(__file__)
            )
        )

        # =====================================================
        # PARAMETER
        # =====================================================

        peta_lama_input = parameters[0].valueAsText

        # =====================================================
        # PATH DATA
        # =====================================================

        peta_baru = "PersilPetaBaru"
        peta_lama = "PersilPetaLama"
        peta_indikator = "Indikator_Perubahan_Persil"

        peta_baru_path = os.path.join(
            dataset_path,
            peta_baru
        )

        peta_lama_path = os.path.join(
            dataset_path,
            peta_lama
        )

        peta_indikator_path = os.path.join(
            dataset_path,
            peta_indikator
        )

        # =====================================================
        # PERSIAPAN DATA
        # =====================================================

        messages.addMessage(
            "== Menyiapkan data persil =="
        )

        if arcpy.Exists(peta_baru_path):
            arcpy.Delete_management(
                peta_baru_path
            )

        if arcpy.Exists(peta_lama_path):
            arcpy.Delete_management(
                peta_lama_path
            )

        arcpy.CopyFeatures_management(
            persil_path,
            peta_baru_path
        )

        arcpy.CopyFeatures_management(
            peta_lama_input,
            peta_lama_path
        )

        # =====================================================
        # MEMBUAT INDIKATOR AWAL
        # =====================================================

        if arcpy.Exists(peta_indikator_path):
            arcpy.Delete_management(
                peta_indikator_path
            )

        arcpy.CopyFeatures_management(
            peta_baru_path,
            peta_indikator_path
        )

        field_names = [
            f.name for f in arcpy.ListFields(
                peta_indikator_path
            )
        ]

        if "status_per" not in field_names:
            arcpy.AddField_management(
                peta_indikator_path,
                "status_per",
                "TEXT"
            )

        if "selisih_luas" not in field_names:
            arcpy.AddField_management(
                peta_indikator_path,
                "selisih_luas",
                "DOUBLE"
            )

        # =====================================================
        # JOIN DENGAN PERSIL LAMA
        # =====================================================

        messages.addMessage(
            "== Membandingkan persil lama dan baru =="
        )

        join_output = os.path.join(
            dataset_path,
            "Join_Perubahan_Persil"
        )

        if arcpy.Exists(join_output):
            arcpy.Delete_management(
                join_output
            )

        arcpy.SpatialJoin_analysis(
            peta_indikator_path,
            peta_lama_path,
            join_output,
            "JOIN_ONE_TO_ONE",
            "KEEP_ALL",
            match_option="INTERSECT"
        )

        # =====================================================
        # HITUNG SELISIH
        # =====================================================

        field_names = [
            f.name for f in arcpy.ListFields(
                join_output
            )
        ]

        if "ls_lama" not in field_names:
            arcpy.AddField_management(
                join_output,
                "ls_lama",
                "DOUBLE"
            )

        if "ls_baru" not in field_names:
            arcpy.AddField_management(
                join_output,
                "ls_baru",
                "DOUBLE"
            )

        arcpy.CalculateField_management(
            join_output,
            "ls_baru",
            "!ls_tnh!",
            "PYTHON3"
        )

        arcpy.CalculateField_management(
            join_output,
            "ls_lama",
            "!ls_tnh_1!",
            "PYTHON3"
        )

        exp = "hitung(!ls_baru!, !ls_lama!)"

        code_block = """
import math

def hitung(baru, lama):

    if baru is None:
        baru = 0

    if lama is None:
        lama = 0

    return math.fabs(baru - lama)
"""

        arcpy.CalculateField_management(
            join_output,
            "selisih_luas",
            exp,
            "PYTHON3",
            code_block
        )

        exp = "status(!selisih_luas!)"

        code_block = """
def status(nilai):

    if nilai > 1:
        return 'update'
    else:
        return 'tetap'
"""

        arcpy.CalculateField_management(
            join_output,
            "status_per",
            exp,
            "PYTHON3",
            code_block
        )

        # =====================================================
        # FINAL OUTPUT
        # =====================================================

        if arcpy.Exists(peta_indikator_path):
            arcpy.Delete_management(
                peta_indikator_path
            )

        arcpy.CopyFeatures_management(
            join_output,
            peta_indikator_path
        )
        appdata = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))))
        symbology_folder = os.path.join(appdata, 'symbology', 'Nilai Bidang Tanah')
        arcpy.AddMessage(appdata)
        sim_indikator = os.path.join(
            symbology_folder,
            "Simbologi_Persil_Updating_Final.lyr"
        )

        if arcpy.Exists(
            "Indikator_Perubahan_Persil"
        ):
            arcpy.Delete_management(
                "Indikator_Perubahan_Persil"
            )

        arcpy.MakeFeatureLayer_management(
            peta_indikator_path,
            "Indikator_Perubahan_Persil"
        )

        if os.path.exists(sim_indikator):

            arcpy.ApplySymbologyFromLayer_management(
                "Indikator_Perubahan_Persil",
                sim_indikator
            )

        parameters[1].value = (
            "Indikator_Perubahan_Persil"
        )

        messages.addMessage(
            "== Proses selesai =="
        )

        return