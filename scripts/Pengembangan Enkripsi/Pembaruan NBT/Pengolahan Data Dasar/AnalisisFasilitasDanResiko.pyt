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
        self.tools = [Hapus_Fasilitas_dan_Resiko,
                      Tambah_Fasilitas,
                      Tambah_Resiko,
                      Hitung_Jarak_Fasilitas,
                      Hitung_Resiko_Persil,
                      ]


class Hapus_Fasilitas_dan_Resiko(object):

    def __init__(self):

        self.label = "Hapus Fasilitas dan Resiko"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):

        return []

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    # =====================================================
    # HELPER
    # =====================================================

    def delete_if_exists(self, path):

        if arcpy.Exists(path):

            try:

                arcpy.management.Delete(
                    path
                )

            except Exception:

                pass

    def delete_feature_classes(
        self,
        dataset_path,
        label,
        messages
    ):

        if not arcpy.Exists(
            dataset_path
        ):

            messages.addWarningMessage(
                f"== Dataset {label} tidak ditemukan =="
            )

            return

        arcpy.env.workspace = (
            dataset_path
        )

        list_fc = arcpy.ListFeatureClasses(
            "*"
        )

        if not list_fc:

            messages.addWarningMessage(
                f"== Tidak ada feature class pada dataset {label} =="
            )

            return

        messages.addMessage(
            f"== Hapus {label} =="
        )

        for fc in list_fc:

            fc_path = os.path.join(
                dataset_path,
                fc
            )

            self.delete_if_exists(
                fc
            )

            self.delete_if_exists(
                fc_path
            )

            messages.addMessage(
                f"{label} {fc} dihapus"
            )

    # =====================================================
    # EXECUTE
    # =====================================================

    def execute(self, parameters, messages):

        import os
        import arcpy

        arcpy.env.overwriteOutput = True

        messages.addMessage(
            "== Proses mulai =="
        )

        # =================================================
        # LOAD CONFIG
        # =================================================

        configs = persil.get_config_values()

        datasetfasilitas_path = (
            configs["fasilitas_config"]["dataset_path"]
        )

        datasetresiko_path = (
            configs["resiko_config"]["dataset_path"]
        )

        # =================================================
        # HAPUS FASILITAS
        # =================================================

        self.delete_feature_classes(
            datasetfasilitas_path,
            "Fasilitas",
            messages
        )

        # =================================================
        # HAPUS RESIKO
        # =================================================

        self.delete_feature_classes(
            datasetresiko_path,
            "Resiko",
            messages
        )

        # =================================================
        # RESET WORKSPACE
        # =================================================

        arcpy.env.workspace = None

        # =================================================
        # SELESAI
        # =================================================

        messages.addMessage(
            "== Proses selesai =="
        )

        return

class Tambah_Fasilitas(object):

    def __init__(self):

        self.label = "Tambah Fasilitas"
        self.description = ""
        self.canRunInBackground = False

    # =====================================================
    # PARAMETER
    # =====================================================

    def getParameterInfo(self):

        fasilitas_path = arcpy.Parameter(
            displayName="Feature Class Fasilitas",
            name="fasilitas_path",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )

        jenis_fasilitas = arcpy.Parameter(
            displayName="Jenis Fasilitas",
            name="jenis_fasilitas",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )

        jenis_fasilitas.filter.list = [
            "Central Business District",
            "Fasilitas Kesehatan",
            "Fasilitas Pendidikan",
            "Fasilitas Pemerintah",
            "Fasilitas Transportasi",
            "Fasilitas Khusus 1",
            "Fasilitas Khusus 2"
        ]

        output_layer = arcpy.Parameter(
            displayName="Output Fasilitas",
            name="output_layer",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [
            fasilitas_path,
            jenis_fasilitas,
            output_layer
        ]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    # =====================================================
    # HELPER
    # =====================================================

    def delete_if_exists(self, path):

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

    def execute(self, parameters, messages):

        import os
        import arcpy

        arcpy.env.overwriteOutput = True

        messages.addMessage(
            "== Proses dimulai =="
        )

        # =================================================
        # PARAMETER
        # =================================================

        fasilitas_path = (
            parameters[0].valueAsText
        )

        jenis_fasilitas = (
            parameters[1].valueAsText
        )

        # =================================================
        # LOAD CONFIG
        # =================================================

        configs = persil.get_config_values()

        dataset_path = (
            configs["fasilitas_config"]["dataset_path"]
        )

        gdb_path = (
            configs["project_config"]["gdb_path"]
        )

        jalan_path = (
            configs["jaringan_jalan_config"]["path"]["Jaringan_Jalan"]
        )

        # =================================================
        # MAPPING FASILITAS
        # =================================================

        fasilitas_mapping = {
            "Central Business District": "jk_cbd",
            "Fasilitas Kesehatan": "jk_kes",
            "Fasilitas Pendidikan": "jk_edu",
            "Fasilitas Pemerintah": "jk_pem",
            "Fasilitas Transportasi": "jk_trans",
            "Fasilitas Khusus 1": "jk_fas1",
            "Fasilitas Khusus 2": "jk_fas2"
        }

        fasilitas = fasilitas_mapping.get(
            jenis_fasilitas
        )

        if fasilitas is None:

            messages.addErrorMessage(
                "== Jenis fasilitas tidak valid =="
            )

            raise arcpy.ExecuteError

        # =================================================
        # CREATE DATASET
        # =================================================

        if not arcpy.Exists(
            dataset_path
        ):

            messages.addMessage(
                "== Membuat dataset fasilitas =="
            )

            arcpy.management.CreateFeatureDataset(
                gdb_path,
                "fasilitas",
                jalan_path
            )

        # =================================================
        # OUTPUT PATH
        # =================================================

        output_fc = os.path.join(
            dataset_path,
            fasilitas
        )

        # =================================================
        # CLEAN EXISTING
        # =================================================

        self.delete_if_exists(
            output_fc
        )

        self.delete_if_exists(
            fasilitas
        )

        # =================================================
        # COPY FEATURE
        # =================================================

        messages.addMessage(
            f"== Menambahkan fasilitas {jenis_fasilitas} =="
        )

        arcpy.conversion.FeatureClassToFeatureClass(
            fasilitas_path,
            dataset_path,
            fasilitas
        )

        # =================================================
        # CREATE LAYER
        # =================================================

        arcpy.management.MakeFeatureLayer(
            output_fc,
            fasilitas
        )

        # =================================================
        # OUTPUT
        # =================================================

        parameters[2].value = (
            fasilitas
        )

        # =================================================
        # FINISH
        # =================================================

        messages.addMessage(
            "== Proses selesai =="
        )

        return

class Tambah_Resiko(object):

    def __init__(self):

        self.label = "Tambah Resiko"
        self.description = ""
        self.canRunInBackground = False

    # =====================================================
    # PARAMETER
    # =====================================================

    def getParameterInfo(self):

        resiko_path = arcpy.Parameter(
            displayName="Feature Class Resiko",
            name="resiko_path",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )

        jenis_resiko = arcpy.Parameter(
            displayName="Jenis Resiko",
            name="jenis_resiko",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )

        jenis_resiko.filter.list = [
            "Banjir",
            "Longsor",
            "Risiko 1",
            "Risiko 2"
        ]

        output_layer = arcpy.Parameter(
            displayName="Output Resiko",
            name="output_layer",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [
            resiko_path,
            jenis_resiko,
            output_layer
        ]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    # =====================================================
    # HELPER
    # =====================================================

    def delete_if_exists(self, path):

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

    def execute(self, parameters, messages):

        import os
        import arcpy

        arcpy.env.overwriteOutput = True

        messages.addMessage(
            "== Proses dimulai =="
        )

        # =================================================
        # PARAMETER
        # =================================================

        resiko_path = (
            parameters[0].valueAsText
        )

        jenis_resiko = (
            parameters[1].valueAsText
        )

        # =================================================
        # LOAD CONFIG
        # =================================================

        configs = persil.get_config_values()

        dataset_path = (
            configs["resiko_config"]["dataset_path"]
        )

        gdb_path = (
            configs["project_config"]["gdb_path"]
        )

        jalan_path = (
            configs["jaringan_jalan_config"]["path"]["Jaringan_Jalan"]
        )

        # =================================================
        # MAPPING RESIKO
        # =================================================

        resiko_mapping = {
            "Banjir": "banjir",
            "Longsor": "longsor",
            "Risiko 1": "risiko_1",
            "Risiko 2": "risiko_2"
        }

        resiko = resiko_mapping.get(
            jenis_resiko
        )

        if resiko is None:

            messages.addErrorMessage(
                "== Jenis resiko tidak valid =="
            )

            raise arcpy.ExecuteError

        # =================================================
        # CREATE DATASET
        # =================================================

        if not arcpy.Exists(
            dataset_path
        ):

            messages.addMessage(
                "== Membuat dataset resiko =="
            )

            arcpy.management.CreateFeatureDataset(
                gdb_path,
                "resiko",
                jalan_path
            )

        # =================================================
        # OUTPUT PATH
        # =================================================

        output_fc = os.path.join(
            dataset_path,
            resiko
        )

        # =================================================
        # CLEAN EXISTING
        # =================================================

        self.delete_if_exists(
            output_fc
        )

        self.delete_if_exists(
            resiko
        )

        # =================================================
        # COPY FEATURE
        # =================================================

        messages.addMessage(
            f"== Menambahkan resiko {jenis_resiko} =="
        )

        arcpy.conversion.FeatureClassToFeatureClass(
            resiko_path,
            dataset_path,
            resiko
        )

        # =================================================
        # CREATE LAYER
        # =================================================

        arcpy.management.MakeFeatureLayer(
            output_fc,
            resiko
        )

        # =================================================
        # OUTPUT
        # =================================================

        parameters[2].value = (
            resiko
        )

        # =================================================
        # FINISH
        # =================================================

        messages.addMessage(
            "== Proses selesai =="
        )

        return

class Hitung_Jarak_Fasilitas(object):

    def __init__(self):

        self.label = "Hitung Jarak Fasilitas"
        self.description = ""
        self.canRunInBackground = False

    # =====================================================
    # PARAMETER
    # =====================================================

    def getParameterInfo(self):

        output_persil = arcpy.Parameter(
            displayName="Output Persil",
            name="output_persil",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [output_persil]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    # =====================================================
    # HELPER
    # =====================================================

    def delete_if_exists(self, path):

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

    def execute(self, parameters, messages):

        import os
        import arcpy

        arcpy.env.overwriteOutput = True

        messages.addMessage(
            "== Proses mulai =="
        )

        # =================================================
        # LOAD CONFIG
        # =================================================

        configs = persil.get_config_values()

        dataset_path = (
            configs["project_config"]["dataset_path"]
        )

        datasetfasilitas_path = (
            configs["fasilitas_config"]["dataset_path"]
        )

        jaringanjalan_nd_path = (
            configs["jaringan_jalan_config"]["path"]["JaringanJalanForND"]
        )

        nd_path = (
            configs["jaringan_jalan_config"]["path"]["JaringanJalan_ND"]
        )

        # =================================================
        # DATASET
        # =================================================

        persil = (
            "Persil_Baru"
        )

        persil_path = os.path.join(
            dataset_path,
            persil
        )

        persilcentroid = (
            "PersilCentroidUpdate"
        )

        persilcentroid_path = os.path.join(
            dataset_path,
            persilcentroid
        )

        dataset_template_path = os.path.dirname(
            jaringanjalan_nd_path
        )

        # =================================================
        # CLEAN TEMP
        # =================================================

        self.delete_if_exists(
            persilcentroid
        )

        self.delete_if_exists(
            persilcentroid_path
        )

        # =================================================
        # CREATE CENTROID
        # =================================================

        messages.addMessage(
            "== Membuat centroid persil =="
        )

        arcpy.management.FeatureToPoint(
            persil_path,
            persilcentroid_path,
            "INSIDE"
        )

        # =================================================
        # NETWORK ANALYST CONFIG
        # =================================================

        messages.addMessage(
            "== Persiapan network analyst =="
        )

        outNALayerName = (
            "hasil_na"
        )

        impedance_attribute = (
            "P_Jalan"
        )

        # =================================================
        # LIST FASILITAS
        # =================================================

        arcpy.env.workspace = (
            datasetfasilitas_path
        )

        list_fc = arcpy.ListFeatureClasses(
            "*"
        )

        if not list_fc:

            messages.addWarningMessage(
                "== Tidak ada fasilitas ditemukan =="
            )

            return

        # =================================================
        # LOOP FASILITAS
        # =================================================

        for fc in list_fc:

            fasilitas = fc

            fasilitas_path = os.path.join(
                datasetfasilitas_path,
                fasilitas
            )

            namafield = (
                fc.replace(" ", "")[:7]
            )

            messages.addMessage(
                f"== Hitung jarak fasilitas: {fasilitas} =="
            )

            # =============================================
            # CREATE CLOSEST FACILITY
            # =============================================

            hasilNAObject = arcpy.na.MakeClosestFacilityLayer(
                nd_path,
                outNALayerName,
                impedance_attribute,
                "TRAVEL_FROM",
                default_number_facilities_to_find=1
            )

            outNALayer = (
                hasilNAObject.getOutput(0)
            )

            # =============================================
            # ADD LOCATIONS
            # =============================================

            arcpy.na.AddLocations(
                outNALayer,
                "Incidents",
                persilcentroid_path
            )

            arcpy.na.AddLocations(
                outNALayer,
                "Facilities",
                fasilitas_path
            )

            # =============================================
            # SOLVE
            # =============================================

            arcpy.na.Solve(
                outNALayer
            )

            # =============================================
            # OUTPUT TEMP
            # =============================================

            incident_path = os.path.join(
                dataset_template_path,
                f"incident_{fasilitas}"
            )

            route_path = os.path.join(
                dataset_template_path,
                f"route_{fasilitas}"
            )

            temp_join = os.path.join(
                dataset_template_path,
                "temp_join1"
            )

            self.delete_if_exists(
                incident_path
            )

            self.delete_if_exists(
                route_path
            )

            self.delete_if_exists(
                temp_join
            )

            # =============================================
            # EXPORT LAYER
            # =============================================

            messages.addMessage(
                "== Export hasil network analyst =="
            )

            for lyr in outNALayer.listLayers():

                if lyr.isGroupLayer:

                    continue

                if lyr.name == "Incidents":

                    arcpy.management.CopyFeatures(
                        lyr,
                        incident_path
                    )

                elif lyr.name == "Routes":

                    arcpy.management.CopyFeatures(
                        lyr,
                        route_path
                    )

            # =============================================
            # JOIN ROUTE
            # =============================================

            messages.addMessage(
                "== Join route =="
            )

            arcpy.management.JoinField(
                incident_path,
                "OBJECTID",
                route_path,
                "IncidentID",
                ["Total_P_Jalan"]
            )

            # =============================================
            # SPATIAL JOIN
            # =============================================

            messages.addMessage(
                "== Spatial join =="
            )

            field_mapping = (
                f'IdBidang "IdBidang" true true false 4 Long 0 0 ,First,#,{persil_path},IdBidang,-1,-1;'
                f'Total_P_Jalan "Total_P_Jalan" true true false 8 Double 0 0 ,First,#,{incident_path},Total_P_Jalan,-1,-1'
            )

            arcpy.analysis.SpatialJoin(
                persil_path,
                incident_path,
                temp_join,
                "JOIN_ONE_TO_ONE",
                "KEEP_ALL",
                field_mapping,
                "INTERSECT"
            )

            # =============================================
            # VALIDASI FIELD
            # =============================================

            self.add_field_if_not_exists(
                persil_path,
                namafield,
                "DOUBLE"
            )

            # =============================================
            # JOIN KE PERSIL
            # =============================================

            arcpy.management.JoinField(
                persil_path,
                "IdBidang",
                temp_join,
                "IdBidang",
                ["Total_P_Jalan"]
            )

            arcpy.management.CalculateField(
                persil_path,
                namafield,
                "!Total_P_Jalan!",
                "PYTHON3"
            )

            try:

                arcpy.management.DeleteField(
                    persil_path,
                    "Total_P_Jalan"
                )

            except:

                pass

        # =================================================
        # REFRESH OUTPUT
        # =================================================

        self.delete_if_exists(
            persil
        )

        arcpy.management.MakeFeatureLayer(
            persil_path,
            persil
        )

        # =================================================
        # OUTPUT
        # =================================================

        parameters[0].value = (
            persil
        )

        # =================================================
        # FINISH
        # =================================================

        messages.addMessage(
            "== Proses selesai =="
        )

        return

class Hitung_Resiko_Persil(object):

    def __init__(self):

        self.label = "Hitung Resiko Persil"
        self.description = ""
        self.canRunInBackground = False

    # =====================================================
    # PARAMETER
    # =====================================================

    def getParameterInfo(self):

        output_persil = arcpy.Parameter(
            displayName="Output Persil",
            name="output_persil",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [output_persil]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    # =====================================================
    # HELPER
    # =====================================================

    def delete_if_exists(self, path):

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
        field_type="SHORT"
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

    def execute(self, parameters, messages):

        import os
        import arcpy

        arcpy.env.overwriteOutput = True

        messages.addMessage(
            "== Proses mulai =="
        )

        # =================================================
        # LOAD CONFIG
        # =================================================

        configs = persil.get_config_values()

        dataset_path = (
            configs["project_config"]["dataset_path"]
        )

        datasetresiko_path = (
            configs["resiko_config"]["dataset_path"]
        )

        # =================================================
        # DATASET
        # =================================================

        persil = (
            "Persil_Baru"
        )

        persil_path = os.path.join(
            dataset_path,
            persil
        )

        persilcentroid = (
            "PersilCentroidUpdate"
        )

        persilcentroid_path = os.path.join(
            dataset_path,
            persilcentroid
        )

        # =================================================
        # PERSIAPAN
        # =================================================

        messages.addMessage(
            "== Persiapan =="
        )

        self.delete_if_exists(
            persilcentroid
        )

        self.delete_if_exists(
            persilcentroid_path
        )

        # =================================================
        # CREATE CENTROID
        # =================================================

        arcpy.management.FeatureToPoint(
            persil_path,
            persilcentroid_path,
            "INSIDE"
        )

        # =================================================
        # LIST RESIKO
        # =================================================

        arcpy.env.workspace = (
            datasetresiko_path
        )

        list_fc = arcpy.ListFeatureClasses(
            "*"
        )

        if not list_fc:

            messages.addWarningMessage(
                "== Tidak ada layer resiko ditemukan =="
            )

            return

        # =================================================
        # LOOP RESIKO
        # =================================================

        for fc in list_fc:

            resiko = fc

            resiko_path = os.path.join(
                datasetresiko_path,
                resiko
            )

            namafield = (
                fc.replace(" ", "")[:7]
            )

            messages.addMessage(
                f"== Cari persil dalam resiko: {resiko} =="
            )

            # =============================================
            # VALIDASI FIELD
            # =============================================

            self.add_field_if_not_exists(
                persil_path,
                namafield,
                "SHORT"
            )

            # =============================================
            # RESET VALUE
            # =============================================

            arcpy.management.CalculateField(
                persil_path,
                namafield,
                "0",
                "PYTHON3"
            )

            # =============================================
            # TEMP LAYER
            # =============================================

            temp_lyr = "temp"

            self.delete_if_exists(
                temp_lyr
            )

            arcpy.management.MakeFeatureLayer(
                persil_path,
                temp_lyr
            )

            # =============================================
            # SELECT BY LOCATION
            # =============================================

            arcpy.management.SelectLayerByLocation(
                temp_lyr,
                "INTERSECT",
                resiko_path
            )

            # =============================================
            # UPDATE VALUE
            # =============================================

            arcpy.management.CalculateField(
                temp_lyr,
                namafield,
                "1",
                "PYTHON3"
            )

            # =============================================
            # CLEAN TEMP
            # =============================================

            self.delete_if_exists(
                temp_lyr
            )

        # =================================================
        # REFRESH OUTPUT
        # =================================================

        self.delete_if_exists(
            persil
        )

        arcpy.management.MakeFeatureLayer(
            persil_path,
            persil
        )

        # =================================================
        # OUTPUT
        # =================================================

        parameters[0].value = (
            persil
        )

        # =================================================
        # FINISH
        # =================================================

        messages.addMessage(
            "== Proses selesai =="
        )

        return