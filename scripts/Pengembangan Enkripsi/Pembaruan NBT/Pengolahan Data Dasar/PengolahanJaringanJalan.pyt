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
        self.tools = [Persiapan_Jaringan_Jalan_Update,
                      Set_Atribut_Jaringan_Jalan,
                      Hapus_Jaringan_Jalan_Terpilih,
                      Validasi_Topologi_Jaringan_Jalan,
                      Update_Simbologi_Kelas_Jalan,
                      Set_Lebar_Jalan,
                      Deteksi_Outlier_Jaringan_Jalan,
                      Set_Outlier_Lebar_Jalan,
                      Update_Simbologi_Kelas_Jalan,
                      Set_Kelas_Jalan,
                      ]


class Persiapan_Jaringan_Jalan_Update(object):

    def __init__(self):
        self.label = "Persiapan Jaringan Jalan Update"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):

        in_jaringan_jalan = arcpy.Parameter(
            displayName="Input Jaringan Jalan",
            name="in_jaringan_jalan",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )

        output_jaringan_jalan = arcpy.Parameter(
            displayName="Output Jaringan Jalan",
            name="output_jaringan_jalan",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        output_peta_baru = arcpy.Parameter(
            displayName="Output Peta Baru",
            name="output_peta_baru",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [
            in_jaringan_jalan,
            output_jaringan_jalan,
            output_peta_baru
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

        arcpy.env.overwriteOutput = True

        messages.addMessage(
            "== Proses dimulai =="
        )

        # =====================================================
        # PARAMETER
        # =====================================================

        in_jaringan_jalan = (
            parameters[0].valueAsText
        )

        # =====================================================
        # LOAD CONFIG
        # =====================================================

        configs = persil.get_config_values()

        dataset_path = (
            configs["project_config"]["dataset_path"]
        )

        jaringan_jalan_path = (
            configs["jaringan_jalan_config"]["path"]["Jaringan_Jalan"]
        )

        appdata = os.path.dirname(
            os.path.dirname(
                os.path.realpath(__file__)
            )
        )

        # =====================================================
        # DATASET
        # =====================================================

        jaringan_jalan = (
            "Jaringan_Jalan"
        )

        peta_baru = (
            "Persil_Baru"
        )

        peta_baru_path = os.path.join(
            dataset_path,
            peta_baru
        )

        JaringanJalanTopoUpdate = (
            "Topo_Jaringan_Jalan_Update"
        )

        JaringanJalanTopoAwal = (
            "TopologiJaringanJalan"
        )

        JaringanJalanTopoTaru = (
            "Topo_Jaringan_Jalan_Taru"
        )

        JaringanJalanTopoKonsol = (
            "Topo_Jaringan_Jalan_Konsolidasi"
        )

        jarjaltop_update_path = os.path.join(
            dataset_path,
            JaringanJalanTopoUpdate
        )

        jarjaltop_awal_path = os.path.join(
            dataset_path,
            JaringanJalanTopoAwal
        )

        jarjaltop_taru_path = os.path.join(
            dataset_path,
            JaringanJalanTopoTaru
        )

        jarjaltop_konsol_path = os.path.join(
            dataset_path,
            JaringanJalanTopoKonsol
        )

        # =====================================================
        # SYMBOLOGY
        # =====================================================

        sim_jaringan_jalan = os.path.join(
            appdata,
            "SimbologiJaringanJalanUpdate.lyr"
        )

        sim_persil = os.path.join(
            appdata,
            "SimbologiPetaPersil.lyr"
        )

        # =====================================================
        # SIMPAN KE GDB
        # =====================================================

        messages.addMessage(
            "== Simpan input jaringan jalan ke geodatabase =="
        )

        if (
            os.path.normpath(
                jaringan_jalan_path
            )
            !=
            os.path.normpath(
                in_jaringan_jalan
            )
        ):

            delete_list = [
                jarjaltop_update_path,
                jarjaltop_awal_path,
                jarjaltop_taru_path,
                jarjaltop_konsol_path,
                jaringan_jalan_path
            ]

            for item in delete_list:

                if arcpy.Exists(item):

                    try:
                        arcpy.management.Delete(
                            item
                        )
                    except:
                        pass

            arcpy.conversion.FeatureClassToFeatureClass(
                in_jaringan_jalan,
                dataset_path,
                jaringan_jalan
            )

        # =====================================================
        # TAMBAH FIELD STATUS
        # =====================================================

        messages.addMessage(
            "== Tambah field status_jal =="
        )

        list_names = [
            f.name
            for f in arcpy.ListFields(
                jaringan_jalan_path
            )
        ]

        if "status_jal" not in list_names:

            arcpy.management.AddField(
                jaringan_jalan_path,
                "status_jal",
                "TEXT"
            )

        arcpy.management.CalculateField(
            jaringan_jalan_path,
            "status_jal",
            '"Tetap"',
            "PYTHON3"
        )

        # =====================================================
        # LAYER JARINGAN JALAN
        # =====================================================

        if arcpy.Exists(
            jaringan_jalan
        ):

            try:
                arcpy.management.Delete(
                    jaringan_jalan
                )
            except:
                pass

        arcpy.management.MakeFeatureLayer(
            jaringan_jalan_path,
            jaringan_jalan
        )

        if os.path.exists(
            sim_jaringan_jalan
        ):

            arcpy.management.ApplySymbologyFromLayer(
                jaringan_jalan,
                sim_jaringan_jalan
            )

        # =====================================================
        # LAYER PERSIL BARU
        # =====================================================

        if arcpy.Exists(
            peta_baru
        ):

            try:
                arcpy.management.Delete(
                    peta_baru
                )
            except:
                pass

        arcpy.management.MakeFeatureLayer(
            peta_baru_path,
            peta_baru
        )

        if os.path.exists(
            sim_persil
        ):

            arcpy.management.ApplySymbologyFromLayer(
                peta_baru,
                sim_persil
            )

        # =====================================================
        # OUTPUT PARAMETER
        # =====================================================

        parameters[1].value = (
            jaringan_jalan
        )

        parameters[2].value = (
            peta_baru
        )

        messages.addMessage(
            "== Proses selesai =="
        )

        return

class Set_Atribut_Jaringan_Jalan(object):

    def __init__(self):
        self.label = "Set Atribut Jaringan Jalan"
        self.description = ""
        self.canRunInBackground = False

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
            "Lokal Setapak"
        ]

        lb_jalan = arcpy.Parameter(
            displayName="Lebar Jalan",
            name="lb_jalan",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input"
        )

        sts_jalan = arcpy.Parameter(
            displayName="Status Jalan",
            name="sts_jalan",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )

        sts_jalan.filter.list = [
            "Tetap",
            "Update",
            "Hapus"
        ]

        return [
            kls_jln,
            lb_jalan,
            sts_jalan
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

        arcpy.env.overwriteOutput = True

        messages.addMessage(
            "== Proses dimulai =="
        )

        # =====================================================
        # PARAMETER
        # =====================================================

        kls_jln = (
            parameters[0].valueAsText
        )

        lb_jalan = (
            parameters[1].value
        )

        sts_jalan = (
            parameters[2].valueAsText
        )

        # =====================================================
        # LOAD CONFIG
        # =====================================================

        configs = persil.get_config_values()

        jaringan_jalan = (
            configs["jaringan_jalan_config"]["path"]["Jaringan_Jalan"]
        )

        kelas_jalan_config = (
            configs["jaringan_jalan_config"]["skoring"]["kelas_jalan"]
        )

        # =====================================================
        # SKOR KELAS JALAN
        # =====================================================

        s_kls_jln = kelas_jalan_config.get(
            kls_jln,
            0
        )

        # =====================================================
        # KATEGORI LEBAR JALAN
        # =====================================================

        if lb_jalan == 0:

            SimLJln2 = "0"

        elif lb_jalan > 0 and lb_jalan <= 1.5:

            SimLJln2 = "1.5"

        elif lb_jalan > 1.5 and lb_jalan <= 3:

            SimLJln2 = "3"

        elif lb_jalan > 3 and lb_jalan <= 5:

            SimLJln2 = "5"

        elif lb_jalan > 5 and lb_jalan <= 8:

            SimLJln2 = "8"

        else:

            SimLJln2 = "8+"

        # =====================================================
        # VALIDASI SELEKSI
        # =====================================================

        ada_seleksi = len(
            arcpy.Describe(
                jaringan_jalan
            ).FIDSet
        )

        if ada_seleksi == 0:

            messages.addWarningMessage(
                "== Tidak ada fitur jaringan jalan yang dipilih =="
            )

            return

        # =====================================================
        # VALIDASI FIELD
        # =====================================================

        sampel_fields = [
            f.name
            for f in arcpy.ListFields(
                jaringan_jalan
            )
        ]

        required_fields = [
            "status_jal",
            "kls_jln",
            "lb_jln",
            "s_kls_jln"
        ]

        missing_fields = []

        for field_name in required_fields:

            if field_name not in sampel_fields:

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
        # ADD FIELD SIMLJLN2
        # =====================================================

        if "SimLJln2" not in sampel_fields:

            arcpy.management.AddField(
                jaringan_jalan,
                "SimLJln2",
                "TEXT"
            )

        # =====================================================
        # UPDATE ATRIBUT
        # =====================================================

        messages.addMessage(
            "== Mengupdate atribut jaringan jalan =="
        )

        fields = [
            "kls_jln",
            "lb_jln",
            "SimLJln2",
            "s_kls_jln",
            "status_jal"
        ]

        with arcpy.da.UpdateCursor(
            jaringan_jalan,
            fields
        ) as cursor:

            for row in cursor:

                row[0] = kls_jln
                row[1] = lb_jalan
                row[2] = SimLJln2
                row[3] = s_kls_jln
                row[4] = sts_jalan

                cursor.updateRow(row)

        messages.addMessage(
            "== Atribut jaringan jalan berhasil diperbarui =="
        )

        messages.addMessage(
            "== Proses selesai =="
        )

        return
    
class Hapus_Jaringan_Jalan_Terpilih(object):

    def __init__(self):
        self.label = "Hapus Jaringan Jalan Terpilih"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):

        jaringan_jalan = arcpy.Parameter(
            displayName="Layer Jaringan Jalan",
            name="jaringan_jalan",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )

        return [jaringan_jalan]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):

        import arcpy

        arcpy.env.overwriteOutput = True

        messages.addMessage(
            "== Proses dimulai =="
        )

        # =====================================================
        # PARAMETER
        # =====================================================

        jaringanjalan = (
            parameters[0].valueAsText
        )

        jaringanjalan_temp = (
            "Jaringan_Jalan_Temp"
        )

        # =====================================================
        # VALIDASI SELEKSI
        # =====================================================

        ada_seleksi = len(
            arcpy.Describe(
                jaringanjalan
            ).FIDSet
        )

        if ada_seleksi == 0:

            messages.addWarningMessage(
                "== Tidak ada fitur jaringan jalan yang dipilih =="
            )

            return

        # =====================================================
        # HAPUS FEATURE TERPILIH
        # =====================================================

        messages.addMessage(
            "== Menghapus jaringan jalan terpilih =="
        )

        if arcpy.Exists(
            jaringanjalan_temp
        ):

            try:
                arcpy.management.Delete(
                    jaringanjalan_temp
                )
            except:
                pass

        arcpy.management.MakeFeatureLayer(
            jaringanjalan,
            jaringanjalan_temp
        )

        arcpy.management.DeleteFeatures(
            jaringanjalan_temp
        )

        # =====================================================
        # DELETE TEMP LAYER
        # =====================================================

        if arcpy.Exists(
            jaringanjalan_temp
        ):

            try:
                arcpy.management.Delete(
                    jaringanjalan_temp
                )
            except:
                pass

        messages.addMessage(
            "== Jaringan jalan berhasil dihapus =="
        )

        messages.addMessage(
            "== Proses selesai =="
        )

        return

class Validasi_Topologi_Jaringan_Jalan(object):

    def __init__(self):
        self.label = "Validasi Topologi Jaringan Jalan"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):

        output_topology = arcpy.Parameter(
            displayName="Output Topology",
            name="output_topology",
            datatype="DETopology",
            parameterType="Derived",
            direction="Output"
        )

        return [output_topology]

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
        # LOAD CONFIG
        # =====================================================

        configs = persil.get_config_values()

        dataset_path = (
            configs["project_config"]["dataset_path"]
        )

        jaringan_jalan_path = (
            configs["jaringan_jalan_config"]["path"]["Jaringan_Jalan"]
        )

        # =====================================================
        # DATASET
        # =====================================================

        JaringanJalanTopo = (
            "Topo_Jaringan_Jalan_Update"
        )

        JaringanJalanTopoAwal = (
            "TopologiJaringanJalan"
        )

        JaringanJalanTopoTaru = (
            "Topo_Jaringan_Jalan_Taru"
        )

        JaringanJalanTopoKonsol = (
            "Topo_Jaringan_Jalan_Konsolidasi"
        )

        jarjaltop_path = os.path.join(
            dataset_path,
            JaringanJalanTopo
        )

        jarjaltop_awal_path = os.path.join(
            dataset_path,
            JaringanJalanTopoAwal
        )

        jarjaltop_taru_path = os.path.join(
            dataset_path,
            JaringanJalanTopoTaru
        )

        jarjaltop_konsol_path = os.path.join(
            dataset_path,
            JaringanJalanTopoKonsol
        )

        # =====================================================
        # DELETE EXISTING TOPOLOGY
        # =====================================================

        delete_list = [
            jarjaltop_path,
            jarjaltop_awal_path,
            jarjaltop_taru_path,
            jarjaltop_konsol_path,
            JaringanJalanTopo,
            JaringanJalanTopoAwal,
            JaringanJalanTopoTaru,
            JaringanJalanTopoKonsol
        ]

        for item in delete_list:

            if arcpy.Exists(item):

                try:
                    arcpy.management.Delete(
                        item
                    )
                except:
                    pass

        # =====================================================
        # CREATE TOPOLOGY
        # =====================================================

        messages.addMessage(
            "== Membuat topologi jaringan jalan =="
        )

        arcpy.management.CreateTopology(
            dataset_path,
            JaringanJalanTopo
        )

        # =====================================================
        # ADD FEATURE CLASS
        # =====================================================

        messages.addMessage(
            "== Menambahkan feature class ke topologi =="
        )

        arcpy.management.AddFeatureClassToTopology(
            jarjaltop_path,
            jaringan_jalan_path,
            1,
            1
        )

        # =====================================================
        # ADD TOPOLOGY RULE
        # =====================================================

        messages.addMessage(
            "== Menambahkan rule topologi =="
        )

        arcpy.management.AddRuleToTopology(
            jarjaltop_path,
            "Must Not Overlap (Line)",
            jaringan_jalan_path
        )

        arcpy.management.AddRuleToTopology(
            jarjaltop_path,
            "Must Not Have Dangles (Line)",
            jaringan_jalan_path
        )

        arcpy.management.AddRuleToTopology(
            jarjaltop_path,
            "Must Not Have Pseudo-Nodes (Line)",
            jaringan_jalan_path
        )

        # =====================================================
        # VALIDATE TOPOLOGY
        # =====================================================

        messages.addMessage(
            "== Validasi topologi =="
        )

        arcpy.management.ValidateTopology(
            jarjaltop_path
        )

        # =====================================================
        # OUTPUT PARAMETER
        # =====================================================

        parameters[0].value = (
            jarjaltop_path
        )

        messages.addMessage(
            "== Proses selesai =="
        )

        return
    
class Update_Simbologi_Lebar_Jalan(object):

    def __init__(self):
        self.label = "Update Simbologi Lebar Jalan"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):

        output_layer = arcpy.Parameter(
            displayName="Output Layer",
            name="output_layer",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [output_layer]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):

        import os
        import arcpy

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

        jaringanjalan = (
            "Jaringan_Jalan"
        )

        jaringanjalan_path = (
            configs["jaringan_jalan_config"]["path"]["Jaringan_Jalan"]
        )

        # =====================================================
        # APPDATA
        # =====================================================

        appdata = os.path.dirname(
            os.path.dirname(
                os.path.realpath(__file__)
            )
        )

        simbologi_path = os.path.join(
            appdata,
            "SimbologiLebarJalanUpdate.lyr"
        )

        # =====================================================
        # VALIDASI FIELD
        # =====================================================

        sampel_fields = [
            f.name
            for f in arcpy.ListFields(
                jaringanjalan_path
            )
        ]

        if "SimLJln2" not in sampel_fields:

            arcpy.management.AddField(
                jaringanjalan_path,
                "SimLJln2",
                "TEXT"
            )

        # =====================================================
        # START EDIT SESSION
        # =====================================================

        messages.addMessage(
            "== Update kategori lebar jalan =="
        )

        edit = arcpy.da.Editor(
            os.path.dirname(
                dataset_path
            )
        )

        edit.startEditing(
            False,
            False
        )

        edit.startOperation()

        # =====================================================
        # UPDATE FIELD
        # =====================================================

        with arcpy.da.UpdateCursor(
            jaringanjalan_path,
            ["lb_jln", "SimLJln2"]
        ) as rows:

            for row in rows:

                if not row[0]:

                    row[0] = 0
                    row[1] = "0"

                else:

                    if row[0] > 30:

                        row[0] = 30
                        row[1] = "8+"

                    else:

                        if row[0] == 0:

                            row[1] = "0"

                        elif (
                            row[0] > 0
                            and row[0] <= 1.5
                        ):

                            row[1] = "1.5"

                        elif (
                            row[0] > 1.5
                            and row[0] <= 3
                        ):

                            row[1] = "3"

                        elif (
                            row[0] > 3
                            and row[0] <= 5
                        ):

                            row[1] = "5"

                        elif (
                            row[0] > 5
                            and row[0] <= 8
                        ):

                            row[1] = "8"

                        elif row[0] > 8:

                            row[1] = "8+"

                rows.updateRow(row)

        # =====================================================
        # STOP EDIT SESSION
        # =====================================================

        edit.stopOperation()

        edit.stopEditing(True)

        # =====================================================
        # REFRESH LAYER
        # =====================================================

        if arcpy.Exists(
            jaringanjalan
        ):

            try:
                arcpy.management.Delete(
                    jaringanjalan
                )
            except:
                pass

        arcpy.management.MakeFeatureLayer(
            jaringanjalan_path,
            jaringanjalan
        )

        # =====================================================
        # APPLY SYMBOLOGY
        # =====================================================

        if os.path.exists(
            simbologi_path
        ):

            arcpy.management.ApplySymbologyFromLayer(
                jaringanjalan,
                simbologi_path
            )

        # =====================================================
        # OUTPUT PARAMETER
        # =====================================================

        parameters[0].value = (
            jaringanjalan
        )

        messages.addMessage(
            "== Proses selesai =="
        )

        return

class Set_Lebar_Jalan(object):

    def __init__(self):
        self.label = "Set Lebar Jalan"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):

        lb_jalan = arcpy.Parameter(
            displayName="Lebar Jalan",
            name="lb_jalan",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input"
        )

        return [lb_jalan]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):

        import os
        import arcpy

        arcpy.env.overwriteOutput = True

        messages.addMessage(
            "== Proses dimulai =="
        )

        # =====================================================
        # PARAMETER
        # =====================================================

        lb_jalan = (
            parameters[0].value
        )

        # =====================================================
        # LOAD CONFIG
        # =====================================================

        configs = persil.get_config_values()

        jaringanjalan = (
            configs["jaringan_jalan_config"]["path"]["Jaringan_Jalan"]
        )

        # =====================================================
        # VALIDASI FIELD
        # =====================================================

        field_names = [
            field.name
            for field in arcpy.ListFields(
                jaringanjalan
            )
        ]

        if "lb_jln" not in field_names:

            arcpy.management.AddField(
                jaringanjalan,
                "lb_jln",
                "DOUBLE"
            )

        if "SimLJln2" not in field_names:

            arcpy.management.AddField(
                jaringanjalan,
                "SimLJln2",
                "TEXT"
            )

        # =====================================================
        # VALIDASI SELEKSI
        # =====================================================

        ada_seleksi = len(
            arcpy.Describe(
                jaringanjalan
            ).FIDSet
        )

        if ada_seleksi == 0:

            messages.addWarningMessage(
                "== Tidak ada jaringan jalan yang dipilih =="
            )

            return

        # =====================================================
        # KATEGORI LEBAR JALAN
        # =====================================================

        if lb_jalan == 0:

            SimLJln2 = "0"

        elif (
            lb_jalan > 0
            and lb_jalan <= 1.5
        ):

            SimLJln2 = "1.5"

        elif (
            lb_jalan > 1.5
            and lb_jalan <= 3
        ):

            SimLJln2 = "3"

        elif (
            lb_jalan > 3
            and lb_jalan <= 5
        ):

            SimLJln2 = "5"

        elif (
            lb_jalan > 5
            and lb_jalan <= 8
        ):

            SimLJln2 = "8"

        else:

            SimLJln2 = "8+"

        # =====================================================
        # UPDATE FIELD
        # =====================================================

        messages.addMessage(
            "== Mengupdate lebar jalan =="
        )

        with arcpy.da.UpdateCursor(
            jaringanjalan,
            [
                "lb_jln",
                "SimLJln2"
            ]
        ) as rows:

            for row in rows:

                row[0] = lb_jalan
                row[1] = SimLJln2

                rows.updateRow(row)

        # =====================================================
        # UPDATE FINAL
        # =====================================================

        arcpy.management.CalculateField(
            jaringanjalan,
            "SimLJln2",
            f'"{SimLJln2}"',
            "PYTHON3"
        )

        messages.addMessage(
            "== Proses selesai =="
        )

        return

class Deteksi_Outlier_Jaringan_Jalan(object):

    def __init__(self):
        self.label = "Deteksi Outlier Jaringan Jalan"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):

        output_jaringan_jalan = arcpy.Parameter(
            displayName="Output Jaringan Jalan",
            name="output_jaringan_jalan",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        output_lokal_setapak = arcpy.Parameter(
            displayName="Outlier Jalan Lokal Setapak",
            name="output_lokal_setapak",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        output_lokal_sekunder = arcpy.Parameter(
            displayName="Outlier Jalan Lokal Sekunder",
            name="output_lokal_sekunder",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        output_lokal_primer = arcpy.Parameter(
            displayName="Outlier Jalan Lokal Primer",
            name="output_lokal_primer",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        output_kolektor_sekunder = arcpy.Parameter(
            displayName="Outlier Jalan Kolektor Sekunder",
            name="output_kolektor_sekunder",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        output_kolektor_primer = arcpy.Parameter(
            displayName="Outlier Jalan Kolektor Primer",
            name="output_kolektor_primer",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        output_arteri_sekunder = arcpy.Parameter(
            displayName="Outlier Jalan Arteri Sekunder",
            name="output_arteri_sekunder",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        output_arteri_primer = arcpy.Parameter(
            displayName="Outlier Jalan Arteri Primer",
            name="output_arteri_primer",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [
            output_jaringan_jalan,
            output_lokal_setapak,
            output_lokal_sekunder,
            output_lokal_primer,
            output_kolektor_sekunder,
            output_kolektor_primer,
            output_arteri_sekunder,
            output_arteri_primer
        ]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):

        import os
        import arcpy

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

        jaringanjalan = (
            "Jaringan_Jalan"
        )

        jaringanjalan_path = (
            configs["jaringan_jalan_config"]["path"]["Jaringan_Jalan"]
        )

        # =====================================================
        # APPDATA
        # =====================================================

        appdata = os.path.dirname(
            os.path.dirname(
                os.path.realpath(__file__)
            )
        )

        temp_gdb_path = os.path.join(
            appdata,
            "temporary.gdb"
        )

        sim_path = os.path.join(
            appdata,
            "SimbologiOutlierKelasJalan.lyr"
        )

        no_sim_path = os.path.join(
            appdata,
            "NoSimbologiJalan.lyr"
        )

        # =====================================================
        # VALIDASI FIELD
        # =====================================================

        field_names = [
            field.name
            for field in arcpy.ListFields(
                jaringanjalan_path
            )
        ]

        messages.addMessage(
            str(field_names)
        )

        if (
            "s_kls_jln" not in field_names
            or
            "lb_jln" not in field_names
        ):

            messages.addWarningMessage(
                "== Field s_kls_jln atau lb_jln tidak ditemukan =="
            )

            return

        # =====================================================
        # PROSES LOCAL MORAN
        # =====================================================

        list_err = []

        for i in range(1, 8):

            out_name = (
                "outlier_u_klsjln_" + str(i)
            )

            out_path = os.path.join(
                temp_gdb_path,
                out_name
            )

            messages.addMessage(
                "== Anselin Local Moran's I: {} ==".format(
                    out_path
                )
            )

            if arcpy.Exists(out_path):

                try:
                    arcpy.management.Delete(
                        out_path
                    )
                except:
                    pass

            temp_lyr = "temp_lyr"

            if arcpy.Exists(temp_lyr):

                try:
                    arcpy.management.Delete(
                        temp_lyr
                    )
                except:
                    pass

            arcpy.management.MakeFeatureLayer(
                jaringanjalan_path,
                temp_lyr,
                "s_kls_jln = {}".format(i)
            )

            row_count = int(
                arcpy.management.GetCount(
                    temp_lyr
                )[0]
            )

            messages.addMessage(
                "jumlah record: {}".format(
                    row_count
                )
            )

            if row_count > 2:

                try:

                    arcpy.stats.ClustersOutliers(
                        temp_lyr,
                        "lb_jln",
                        out_path,
                        "INVERSE_DISTANCE_SQUARED",
                        "EUCLIDEAN_DISTANCE",
                        "NONE"
                    )

                except arcpy.ExecuteError:

                    messages.addWarningMessage(
                        "Error: {}".format(
                            out_name
                        )
                    )

                    list_err.append(
                        out_name
                        + ","
                        + arcpy.GetMessages()
                    )

            else:

                messages.addMessage(
                    "Kelas Jalan {} tidak diproses. "
                    "Jumlah record {}, kurang dari 3.".format(
                        i,
                        row_count
                    )
                )

            if arcpy.Exists(temp_lyr):

                try:
                    arcpy.management.Delete(
                        temp_lyr
                    )
                except:
                    pass

            messages.addMessage(
                "== Ok =="
            )

        # =====================================================
        # SAVE ERROR LOG
        # =====================================================

        err_outlier_path = os.path.join(
            appdata,
            "err_outlier.err"
        )

        with open(
            err_outlier_path,
            "w"
        ) as conf_file:

            conf_file.write(
                "\n".join(list_err) + "\n"
            )

        # =====================================================
        # DATASET OUTLIER
        # =====================================================

        outlier_layers = [
            (
                "outlier_u_klsjln_1",
                "Jalan_Lokal_Setapak",
                1
            ),
            (
                "outlier_u_klsjln_2",
                "Jalan_Lokal_Sekunder",
                2
            ),
            (
                "outlier_u_klsjln_3",
                "Jalan_Lokal_Primer",
                3
            ),
            (
                "outlier_u_klsjln_4",
                "Jalan_Kolektor_Sekunder",
                4
            ),
            (
                "outlier_u_klsjln_5",
                "Jalan_Kolektor_Primer",
                5
            ),
            (
                "outlier_u_klsjln_6",
                "Jalan_Arteri_Sekunder",
                6
            ),
            (
                "outlier_u_klsjln_7",
                "Jalan_Arteri_Primer",
                7
            )
        ]

        # =====================================================
        # LOAD OUTLIER LAYER
        # =====================================================

        for fc_name, lyr_name, param_idx in outlier_layers:

            fc_path = os.path.join(
                temp_gdb_path,
                fc_name
            )

            if arcpy.Exists(lyr_name):

                try:
                    arcpy.management.Delete(
                        lyr_name
                    )
                except:
                    pass

            if arcpy.Exists(fc_path):

                arcpy.management.MakeFeatureLayer(
                    fc_path,
                    lyr_name
                )

                if os.path.exists(sim_path):

                    arcpy.management.ApplySymbologyFromLayer(
                        lyr_name,
                        sim_path
                    )

                parameters[param_idx].value = (
                    lyr_name
                )

        # =====================================================
        # REFRESH JARINGAN JALAN
        # =====================================================

        if arcpy.Exists(jaringanjalan):

            try:
                arcpy.management.Delete(
                    jaringanjalan
                )
            except:
                pass

        arcpy.management.MakeFeatureLayer(
            jaringanjalan_path,
            jaringanjalan
        )

        if os.path.exists(no_sim_path):

            arcpy.management.ApplySymbologyFromLayer(
                jaringanjalan,
                no_sim_path
            )

        parameters[0].value = (
            jaringanjalan
        )

        messages.addMessage(
            "== Menjalankan proses berhasil dilakukan. "
            "Silahkan lanjutkan proses berikutnya... =="
        )

        return

class Set_Outlier_Lebar_Jalan(object):

    def __init__(self):
        self.label = "Set Outlier Lebar Jalan"
        self.description = ""
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

        import os
        import arcpy

        arcpy.env.overwriteOutput = True

        messages.addMessage(
            "== Proses dimulai =="
        )

        # =====================================================
        # PARAMETER
        # =====================================================

        val = (
            parameters[0].value
        )

        # =====================================================
        # FIELD
        # =====================================================

        field = "lb_jln"
        field2 = "COType"

        # =====================================================
        # DAFTAR LAYER
        # =====================================================

        daftar_layer = [
            "Jalan_Lokal_Setapak",
            "Jalan_Lokal_Sekunder",
            "Jalan_Lokal_Primer",
            "Jalan_Kolektor_Sekunder",
            "Jalan_Kolektor_Primer",
            "Jalan_Arteri_Sekunder",
            "Jalan_Arteri_Primer"
        ]

        # =====================================================
        # UPDATE OUTLIER LAYER
        # =====================================================

        for layer_name in daftar_layer:

            if not arcpy.Exists(
                layer_name
            ):

                continue

            ada_seleksi = len(
                arcpy.Describe(
                    layer_name
                ).FIDSet
            )

            if ada_seleksi == 0:

                continue

            messages.addMessage(
                "== Update layer {} ==".format(
                    layer_name
                )
            )

            fields = [
                field,
                field2
            ]

            with arcpy.da.UpdateCursor(
                layer_name,
                fields
            ) as rows:

                for row in rows:

                    row[0] = val

                    val_temp = row[1]

                    if val_temp is None:

                        val_temp = ""

                    else:

                        val_temp = str(
                            val_temp
                        )

                        if len(val_temp) > 0:

                            val_temp = (
                                val_temp[0]
                            )

                    val_temp = (
                        val_temp + "E"
                    )

                    row[1] = val_temp

                    rows.updateRow(row)

        # =====================================================
        # UPDATE JARINGAN JALAN
        # =====================================================

        jaringanjalan = (
            "Jaringan_Jalan"
        )

        if arcpy.Exists(
            jaringanjalan
        ):

            ada_seleksi = len(
                arcpy.Describe(
                    jaringanjalan
                ).FIDSet
            )

            if ada_seleksi > 0:

                messages.addMessage(
                    "== Update layer Jaringan_Jalan =="
                )

                with arcpy.da.UpdateCursor(
                    jaringanjalan,
                    [field]
                ) as rows:

                    for row in rows:

                        row[0] = val

                        rows.updateRow(row)

        messages.addMessage(
            "== Proses selesai =="
        )

        return

class Update_Simbologi_Kelas_Jalan(object):

    def __init__(self):
        self.label = "Update Simbologi Kelas Jalan"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):

        output_layer = arcpy.Parameter(
            displayName="Output Layer",
            name="output_layer",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [output_layer]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):

        import os
        import arcpy

        arcpy.env.overwriteOutput = True

        messages.addMessage(
            "== Proses dimulai =="
        )

        # =====================================================
        # LOAD CONFIG
        # =====================================================

        configs = persil.get_config_values()

        jaringanjalan = (
            "Jaringan_Jalan"
        )

        jaringanjalan_path = (
            configs["jaringan_jalan_config"]["path"]["Jaringan_Jalan"]
        )

        # =====================================================
        # APPDATA
        # =====================================================

        appdata = os.path.dirname(
            os.path.dirname(
                os.path.realpath(__file__)
            )
        )

        simbologi_path = os.path.join(
            appdata,
            "SimbologiKelasJalan.lyr"
        )

        # =====================================================
        # TEMP LAYER
        # =====================================================

        temp_layer = "temp"

        if arcpy.Exists(
            temp_layer
        ):

            try:
                arcpy.management.Delete(
                    temp_layer
                )
            except:
                pass

        # =====================================================
        # VALIDASI FIELD
        # =====================================================

        field_names = [
            field.name
            for field in arcpy.ListFields(
                jaringanjalan_path
            )
        ]

        if "kls_jln" not in field_names:

            arcpy.management.AddField(
                jaringanjalan_path,
                "kls_jln",
                "TEXT"
            )

        if "s_kls_jln" not in field_names:

            arcpy.management.AddField(
                jaringanjalan_path,
                "s_kls_jln",
                "SHORT"
            )

        # =====================================================
        # UPDATE NULL VALUE
        # =====================================================

        messages.addMessage(
            "== Update kelas jalan kosong =="
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
            '"Lokal"',
            "PYTHON3"
        )

        arcpy.management.CalculateField(
            temp_layer,
            "s_kls_jln",
            "1",
            "PYTHON3"
        )

        # =====================================================
        # DELETE TEMP
        # =====================================================

        if arcpy.Exists(
            temp_layer
        ):

            try:
                arcpy.management.Delete(
                    temp_layer
                )
            except:
                pass

        # =====================================================
        # REFRESH LAYER
        # =====================================================

        if arcpy.Exists(
            jaringanjalan
        ):

            try:
                arcpy.management.Delete(
                    jaringanjalan
                )
            except:
                pass

        arcpy.management.MakeFeatureLayer(
            jaringanjalan_path,
            jaringanjalan
        )

        # =====================================================
        # APPLY SYMBOLOGY
        # =====================================================

        if os.path.exists(
            simbologi_path
        ):

            arcpy.management.ApplySymbologyFromLayer(
                jaringanjalan,
                simbologi_path
            )

        # =====================================================
        # OUTPUT PARAMETER
        # =====================================================

        parameters[0].value = (
            jaringanjalan
        )

        messages.addMessage(
            "== Proses selesai =="
        )

        return

class Set_Kelas_Jalan(object):

    def __init__(self):
        self.label = "Set Kelas Jalan"
        self.description = ""
        self.canRunInBackground = False

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
            "Lokal Setapak"
        ]

        return [kls_jln]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):

        import os
        import arcpy

        arcpy.env.overwriteOutput = True

        messages.addMessage(
            "== Proses dimulai =="
        )

        # =====================================================
        # PARAMETER
        # =====================================================

        kls_jln = (
            parameters[0].valueAsText
        )

        # =====================================================
        # LOAD CONFIG
        # =====================================================

        configs = persil.get_config_values()

        jaringan_jalan = (
            configs["jaringan_jalan_config"]["path"]["Jaringan_Jalan"]
        )

        kelas_jalan_config = (
            configs["jaringan_jalan_config"]["skoring"]["kelas_jalan"]
        )

        # =====================================================
        # SKOR KELAS JALAN
        # =====================================================

        s_kls_jln = kelas_jalan_config.get(
            kls_jln,
            1
        )

        # =====================================================
        # VALIDASI FIELD
        # =====================================================

        jalan_fields = [
            f.name
            for f in arcpy.ListFields(
                jaringan_jalan
            )
        ]

        required_fields = [
            "kls_jln",
            "s_kls_jln"
        ]

        missing_fields = []

        for field_name in required_fields:

            if field_name not in jalan_fields:

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

        ada_seleksi = len(
            arcpy.Describe(
                jaringan_jalan
            ).FIDSet
        )

        if ada_seleksi == 0:

            messages.addWarningMessage(
                "== Tidak ada jaringan jalan yang dipilih =="
            )

            return

        # =====================================================
        # UPDATE FIELD
        # =====================================================

        messages.addMessage(
            "== Mengupdate kelas jalan =="
        )

        with arcpy.da.UpdateCursor(
            jaringan_jalan,
            [
                "kls_jln",
                "s_kls_jln"
            ]
        ) as rows:

            for row in rows:

                row[0] = kls_jln
                row[1] = s_kls_jln

                rows.updateRow(row)

        # =====================================================
        # UPDATE FINAL
        # =====================================================

        arcpy.management.CalculateField(
            jaringan_jalan,
            "kls_jln",
            f'"{kls_jln}"',
            "PYTHON3"
        )

        messages.addMessage(
            "== Proses selesai =="
        )

        return