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
        self.tools = [Identifikasi_Perubahan_Persil, 
                      Hapus_Indikator_Perubahan_Persil,
                      Update_Indikator_Perubahan_Persil,
                      Set_Status_Perubahan_Persil]


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

        import arcpy
        import os
        import json

        arcpy.env.overwriteOutput = True

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

        konfigurasi_variabel_path = (
            configs["project_config"]["daftar_variabel_path"]
        )

        appdata = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.dirname(
                os.path.realpath(__file__)
            ))))
        )

        # =====================================================
        # PARAMETER
        # =====================================================

        peta_lama_input = parameters[0].valueAsText

        # =====================================================
        # LOAD VARIABEL JSON
        # =====================================================

        fields_dont_delete = []

        if os.path.exists(
            konfigurasi_variabel_path
        ):

            with open(
                konfigurasi_variabel_path,
                "r"
            ) as conf_file:

                json_variabel = json.load(
                    conf_file
                )

            daftar_variabel = json_variabel.get(
                "daftar_variabel",
                []
            )

            for row in daftar_variabel:

                if len(row) < 2:
                    continue

                akronim = row[1]

                fields_dont_delete.append(
                    akronim
                )

                fields_dont_delete.append(
                    "s_" + akronim
                )

        # =====================================================
        # MEMORY WORKSPACE
        # =====================================================

        dest_lama_path = r"memory\PersilPetaLama"
        dest_baru_path = r"memory\PersilPetaBaru"

        temp_lama_path = r"memory\Peta_Temp_Lama"
        temp_baru_path = r"memory\Peta_Temp_Baru"

        peta_indikator_temp = (
            r"memory\Indikator_Perubahan"
        )

        # =====================================================
        # OUTPUT FINAL
        # =====================================================

        peta_indikator = (
            "Indikator_Perubahan_Persil"
        )

        peta_indikator_path = os.path.join(
            dataset_path,
            peta_indikator
        )

        # =====================================================
        # DELETE MEMORY LAYER
        # =====================================================

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
                    arcpy.management.Delete(
                        lyr
                    )
                except:
                    pass

        # =====================================================
        # COPY DATA
        # =====================================================

        messages.addMessage(
            "== Menyalin data =="
        )

        arcpy.management.CopyFeatures(
            peta_lama_input,
            dest_lama_path
        )

        arcpy.management.CopyFeatures(
            persil_path,
            dest_baru_path
        )

        # =====================================================
        # FUNCTION DELETE FIELD
        # =====================================================

        def bersihkan_field(fc):

            fields = arcpy.ListFields(fc)

            for f in fields:

                if not (
                    f.type == "Geometry"
                    or f.type == "OID"
                    or f.name == "IdBidang"
                    or f.name == "NIB"
                    or "shape" in f.name.lower()
                    or f.name in fields_dont_delete
                    or f.name.lower() == "nilai"
                    or f.name.lower() == "predicted"
                    or f.name == "FID"
                ):

                    try:

                        arcpy.management.DeleteField(
                            fc,
                            f.name
                        )

                    except:
                        pass

        # =====================================================
        # DELETE UNUSED FIELD
        # =====================================================

        messages.addMessage(
            "== Membersihkan field =="
        )

        bersihkan_field(dest_lama_path)
        bersihkan_field(dest_baru_path)

        # =====================================================
        # TAMBAH FIELD LUAS
        # =====================================================

        messages.addMessage(
            "== Menghitung luas =="
        )

        for fc in [
            dest_lama_path,
            dest_baru_path
        ]:

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

        # =====================================================
        # SELECT BY LOCATION
        # =====================================================

        messages.addMessage(
            "== Seleksi perubahan persil =="
        )

        arcpy.management.MakeFeatureLayer(
            dest_lama_path,
            "PetaLamaLayer"
        )

        arcpy.management.SelectLayerByLocation(
            "PetaLamaLayer",
            "CONTAINS",
            dest_baru_path,
            selection_type="NEW_SELECTION",
            invert_spatial_relationship="INVERT"
        )

        arcpy.management.CopyFeatures(
            "PetaLamaLayer",
            temp_lama_path
        )

        arcpy.management.MakeFeatureLayer(
            dest_baru_path,
            "PetaBaruLayer"
        )

        arcpy.management.SelectLayerByLocation(
            "PetaBaruLayer",
            "CONTAINS",
            dest_lama_path,
            selection_type="NEW_SELECTION",
            invert_spatial_relationship="INVERT"
        )

        arcpy.management.CopyFeatures(
            "PetaBaruLayer",
            temp_baru_path
        )

        # =====================================================
        # MERGE
        # =====================================================

        messages.addMessage(
            "== Menggabungkan indikator =="
        )

        arcpy.management.Merge(
            [
                temp_baru_path,
                temp_lama_path
            ],
            peta_indikator_temp
        )

        # =====================================================
        # TAMBAH FIELD STATUS
        # =====================================================

        field_names = [
            f.name
            for f in arcpy.ListFields(
                peta_indikator_temp
            )
        ]

        if "sim_sts_2b" not in field_names:

            arcpy.management.AddField(
                peta_indikator_temp,
                "sim_sts_2b",
                "TEXT"
            )

        with arcpy.da.UpdateCursor(
            peta_indikator_temp,
            ["sim_sts_2b"]
        ) as cursor:

            for row in cursor:

                row[0] = (
                    "Indikator Periksa"
                )

                cursor.updateRow(row)

        # =====================================================
        # DELETE UNUSED FINAL FIELD
        # =====================================================

        fields = arcpy.ListFields(
            peta_indikator_temp
        )

        for f in fields:

            if not (
                f.type == "Geometry"
                or f.type == "OID"
                or f.name == "IdBidang"
                or f.name == "NIB"
                or "shape" in f.name.lower()
                or f.name.lower() == "sim_sts_2b"
                or f.name.lower() == "ls_asal"
                or f.name.lower() == "ls_tnh"
                or f.name.lower() == "nilai"
                or f.name.lower() == "predicted"
                or f.name == "FID"
            ):

                try:

                    arcpy.management.DeleteField(
                        peta_indikator_temp,
                        f.name
                    )

                except:
                    pass

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
            peta_indikator_temp,
            peta_indikator_path
        )

        # =====================================================
        # SYMBOLOGY
        # =====================================================
        simbology_folder = os.path.join(
            appdata,
            'ui',
            'symbology',
            'Nilai Bidang Tanah'
        )

        arcpy.AddMessage(simbology_folder)

        sim_path = r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Simbologi_Layer_2B.lyrx"

        sim_pathbaru = os.path.join(
            simbology_folder,
            "SimbologiPetaUpdate.lyrx"
        )

        sim_pathlama = os.path.join(
            simbology_folder,
            "SimbologiPetaLama.lyrx"
        )

        if arcpy.Exists(
            "Indikator_Perubahan_Persil"
        ):

            arcpy.management.Delete(
                "Indikator_Perubahan_Persil"
            )

        arcpy.management.MakeFeatureLayer(
            peta_indikator_path,
            "Indikator_Perubahan_Persil"
        )

        arcpy.management.ApplySymbologyFromLayer(
                "Indikator_Perubahan_Persil",
                sim_path
            )

        if arcpy.Exists("Peta_Lama"):

            arcpy.management.Delete(
                "Peta_Lama"
            )

        arcpy.management.MakeFeatureLayer(
            dest_lama_path,
            "Peta_Lama"
        )

        if os.path.exists(sim_pathlama):

            arcpy.management.ApplySymbologyFromLayer(
                "Peta_Lama",
                sim_pathlama
            )

        if arcpy.Exists("Peta_Baru"):

            arcpy.management.Delete(
                "Peta_Baru"
            )

        arcpy.management.MakeFeatureLayer(
            dest_baru_path,
            "Peta_Baru"
        )

        if os.path.exists(sim_pathbaru):

            arcpy.management.ApplySymbologyFromLayer(
                "Peta_Baru",
                sim_pathbaru
            )

        # =====================================================
        # OUTPUT PARAMETER
        # =====================================================

        parameters[1].value = "Peta_Lama"
        parameters[2].value = "Peta_Baru"
        arcpy.SetParameter(3, "Indikator_Perubahan_Persil")

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

        import arcpy
        import os

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

        peta_baru = "PersilPetaBaru"
        peta_lama = "PersilPetaLama"
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
            r"memory\Peta_Indikator_Update"
        )

        peta_indikator_lama_path = (
            r"memory\Peta_Indikator_Lama"
        )

        peta_indikator_akhir_path = (
            r"memory\Indikator_Akhir"
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
            "JOIN_ONE_TO_ONE",
            "KEEP_ALL",
            match_option="INTERSECT"
        )

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
            "JOIN_ONE_TO_ONE",
            "KEEP_ALL",
            match_option="INTERSECT"
        )

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

        arcpy.analysis.SpatialJoin(
            peta_indikator_lama_path,
            peta_indikator_update_path,
            peta_indikator_akhir_path,
            "JOIN_ONE_TO_ONE",
            "KEEP_COMMON",
            match_option="WITHIN"
        )

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

        import arcpy
        import os

        arcpy.env.overwriteOutput = True

        messages.addMessage(
            "== Proses dimulai =="
        )

        # =====================================================
        # PARAMETER
        # =====================================================

        val = parameters[0].valueAsText

        # =====================================================
        # LOAD CONFIG
        # =====================================================

        configs = persil.get_config_values()

        dataset_path = (
            configs["project_config"]["dataset_path"]
        )

        # =====================================================
        # DATASET
        # =====================================================

        status_per = os.path.join(
            dataset_path,
            "Indikator_Perubahan_Persil"
        )

        # =====================================================
        # VALIDASI DATASET
        # =====================================================

        if not arcpy.Exists(
            status_per
        ):

            messages.addErrorMessage(
                "== Layer Indikator_Perubahan_Persil tidak ditemukan =="
            )

            raise arcpy.ExecuteError

        # =====================================================
        # VALIDASI FIELD
        # =====================================================

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

        # =====================================================
        # UPDATE FIELD
        # =====================================================

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