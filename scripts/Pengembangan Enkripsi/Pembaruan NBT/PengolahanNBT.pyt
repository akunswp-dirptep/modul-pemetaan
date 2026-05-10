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
        self.tools = [Generate_Titik_Indeks_Non_Cluster]


class Generate_Titik_Indeks_Non_Cluster(object):

    def __init__(self):

        self.label = "Generate Titik Indeks Non Cluster"
        self.description = ""
        self.canRunInBackground = False

    # =====================================================
    # PARAMETER
    # =====================================================

    def getParameterInfo(self):

        output_indeks = arcpy.Parameter(
            displayName="Output Titik Indeks",
            name="output_indeks",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        output_sampel = arcpy.Parameter(
            displayName="Output Titik Sampel",
            name="output_sampel",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [
            output_indeks,
            output_sampel
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

                arcpy.management.Delete(path)

            except Exception:

                pass

    def add_field_if_not_exists(
        self,
        feature_class,
        field_name,
        field_type
    ):

        fields = [
            field.name
            for field in arcpy.ListFields(
                feature_class
            )
        ]

        if field_name not in fields:

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

        appdata = os.path.dirname(
            os.path.dirname(
                os.path.realpath(__file__)
            )
        )

        # =================================================
        # DATASET
        # =================================================

        persil_path = os.path.join(
            dataset_path,
            "Persil_Baru"
        )

        sampel_path = os.path.join(
            dataset_path,
            "Titik_Sampel_Update"
        )

        indeks_path = os.path.join(
            dataset_path,
            "Titik_Indeks"
        )

        temp_identity = os.path.join(
            dataset_path,
            "temp_hi"
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
                    "Persil_Baru "
                    "tidak ditemukan"
                )
            )

            raise arcpy.ExecuteError

        if not arcpy.Exists(
            sampel_path
        ):

            messages.addErrorMessage(
                (
                    "Feature class "
                    "Titik_Sampel_Update "
                    "tidak ditemukan"
                )
            )

            raise arcpy.ExecuteError

        # =================================================
        # CLEAN TEMP
        # =================================================

        self.delete_if_exists(
            temp_identity
        )

        self.delete_if_exists(
            indeks_path
        )

        self.delete_if_exists(
            "Titik_Indeks"
        )

        # =================================================
        # IDENTITY
        # =================================================

        messages.addMessage(
            "== Membuat identity =="
        )

        arcpy.analysis.Identity(
            sampel_path,
            persil_path,
            temp_identity
        )

        # =================================================
        # FIELD INDEKS
        # =================================================

        self.add_field_if_not_exists(
            temp_identity,
            "indeks",
            "DOUBLE"
        )

        # =================================================
        # CALCULATE INDEKS
        # =================================================

        code_block = """
def doSomething(a, b):

    if a and b:

        return round(
            100 * (a / b),
            2
        )

    return None
"""

        arcpy.management.CalculateField(
            temp_identity,
            "indeks",
            "doSomething(!nilai!, !NILAI_LAMA!)",
            "PYTHON3",
            code_block
        )

        # =================================================
        # SORT
        # =================================================

        messages.addMessage(
            "== Sorting indeks =="
        )

        arcpy.management.Sort(
            temp_identity,
            indeks_path,
            [
                ["s_zonasi", "ASCENDING"],
                ["indeks", "ASCENDING"]
            ]
        )

        # =================================================
        # DELETE CLUSTER DATA
        # =================================================

        messages.addMessage(
            "== Hapus data cluster =="
        )

        with arcpy.da.UpdateCursor(
            indeks_path,
            ["clusternew"]
        ) as cursor:

            for row in cursor:

                if row[0]:

                    cursor.deleteRow()

        # =================================================
        # DELETE UNUSED FIELD
        # =================================================

        delete_fields = [
            "FID_Titik_Sampel_Update",
            "FID_Persil_Baru",
            "NIB",
            "ls_asal",
            "ls_tnh",
            "lb_dpn",
            "bentuk",
            "s_bentuk",
            "letak",
            "s_letak",
            "s_kls_jln",
            "lb_jln",
            "kls_jln",
            "jk_atrp",
            "jk_atrs",
            "jk_kolp",
            "jk_kols",
            "Shape_Le_1",
            "tsk_st",
            "SimLbDpn",
            "sim_l_dpn",
            "CBD",
            "Banjir",
            "ls_tnh_i",
            "lb_dpn_i",
            "perubahan",
            "MEAN_nilai",
            "STD_nilai",
            "PTDDEV",
            "indeks_rata"
        ]

        existing_fields = [
            field.name
            for field in arcpy.ListFields(
                indeks_path
            )
        ]

        valid_delete_fields = [
            field
            for field in delete_fields
            if field in existing_fields
        ]

        if valid_delete_fields:

            arcpy.management.DeleteField(
                indeks_path,
                valid_delete_fields
            )

        # =================================================
        # CREATE LAYER
        # =================================================

        arcpy.management.MakeFeatureLayer(
            indeks_path,
            "Titik_Indeks"
        )

        arcpy.management.MakeFeatureLayer(
            sampel_path,
            "Titik_Sampel_Update"
        )

        # =================================================
        # APPLY SYMBOLOGY
        # =================================================

        simbologi_path = os.path.join(
            appdata,
            "Simbologi_Titik_Indeks.lyrx"
        )

        if os.path.exists(
            simbologi_path
        ):

            arcpy.management.ApplySymbologyFromLayer(
                "Titik_Indeks",
                simbologi_path
            )

        # =================================================
        # OUTPUT
        # =================================================

        parameters[0].value = (
            "Titik_Indeks"
        )

        parameters[1].value = (
            "Titik_Sampel_Update"
        )

        # =================================================
        # CLEAN TEMP
        # =================================================

        self.delete_if_exists(
            temp_identity
        )

        # =================================================
        # FINISH
        # =================================================

        messages.addMessage(
            "== Proses selesai =="
        )

        return
    
class Deteksi_Outlier_Indeks(object):

    def __init__(self):

        self.label = "Deteksi Outlier Indeks"
        self.description = ""
        self.canRunInBackground = False

    # =====================================================
    # PARAMETER
    # =====================================================

    def getParameterInfo(self):

        output_layer = arcpy.Parameter(
            displayName="Output Titik Indeks",
            name="output_indeks",
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

    def delete_field_if_exists(
        self,
        feature_class,
        field_name
    ):

        field_names = [
            field.name
            for field in arcpy.ListFields(
                feature_class
            )
        ]

        if field_name in field_names:

            arcpy.management.DeleteField(
                feature_class,
                field_name
            )

    def calculate_boxplot_values(
        self,
        data_list
    ):

        import numpy

        q1 = numpy.percentile(
            data_list,
            25
        )

        median = numpy.percentile(
            data_list,
            50
        )

        q3 = numpy.percentile(
            data_list,
            75
        )

        iqr = q3 - q1

        lower_bound = (
            q1 - (1.5 * iqr)
        )

        upper_bound = (
            q3 + (1.5 * iqr)
        )

        return (
            q1,
            median,
            q3,
            lower_bound,
            upper_bound
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
        import numpy

        arcpy.env.overwriteOutput = True
        arcpy.env.outputZFlag = "Disabled"
        arcpy.env.outputMFlag = "Disabled"

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

        titik_indeks = os.path.join(
            dataset_path,
            "Titik_Indeks"
        )

        # =================================================
        # VALIDASI
        # =================================================

        if not arcpy.Exists(
            titik_indeks
        ):

            messages.addErrorMessage(
                (
                    "Feature class "
                    "Titik_Indeks "
                    "tidak ditemukan"
                )
            )

            raise arcpy.ExecuteError

        # =================================================
        # FIELD OUTLIER
        # =================================================

        self.add_field_if_not_exists(
            titik_indeks,
            "outlier",
            "TEXT"
        )

        # RESET VALUE
        arcpy.management.CalculateField(
            titik_indeks,
            "outlier",
            "None",
            "PYTHON3"
        )

        # =================================================
        # GET ZONASI
        # =================================================

        list_zonasi = []
        zonasi_dict = {}

        with arcpy.da.SearchCursor(
            titik_indeks,
            [
                "zonasi",
                "s_zonasi"
            ]
        ) as rows:

            for row in rows:

                nama_zonasi = row[0]
                s_zonasi = row[1]

                if (
                    nama_zonasi is not None
                    and s_zonasi is not None
                ):

                    s_zonasi = int(
                        s_zonasi
                    )

                    list_zonasi.append(
                        s_zonasi
                    )

                    zonasi_dict[
                        s_zonasi
                    ] = nama_zonasi

        list_zonasi = sorted(
            list(
                set(list_zonasi)
            )
        )

        # =================================================
        # PROCESS OUTLIER
        # =================================================

        for s_zonasi in list_zonasi:

            nama_zonasi = (
                zonasi_dict[
                    s_zonasi
                ]
            )

            messages.addMessage(
                (
                    f"== Zonasi "
                    f"{nama_zonasi} =="
                )
            )

            # =============================================
            # GET DATA
            # =============================================

            where_clause = (
                f"s_zonasi = {s_zonasi}"
            )

            data = []

            with arcpy.da.SearchCursor(
                titik_indeks,
                ["indeks"],
                where_clause
            ) as rows:

                for row in rows:

                    if row[0] is not None:

                        data.append(
                            row[0]
                        )

            # =============================================
            # VALIDASI SAMPEL
            # =============================================

            if len(data) < 10:

                self.delete_field_if_exists(
                    titik_indeks,
                    "outlier"
                )

                error_message = (
                    "Titik Sampel kurang "
                    f"dari 10 untuk "
                    f"zona {nama_zonasi}"
                )

                messages.addErrorMessage(
                    error_message
                )

                raise arcpy.ExecuteError

            # =============================================
            # SORT DATA
            # =============================================

            data_sorted = sorted(
                data
            )

            # =============================================
            # HITUNG BOXPLOT
            # =============================================

            (
                q1,
                median,
                q3,
                lower_bound,
                upper_bound
            ) = self.calculate_boxplot_values(
                data_sorted
            )

            messages.addMessage(
                (
                    f"(Q1, Median, Q3) "
                    f"{nama_zonasi}: "
                    f"{[q1, median, q3]}"
                )
            )

            messages.addMessage(
                (
                    f"Lower Bound: "
                    f"{round(lower_bound,2)} | "
                    f"Upper Bound: "
                    f"{round(upper_bound,2)}"
                )
            )

            # =============================================
            # UPDATE OUTLIER
            # =============================================

            with arcpy.da.UpdateCursor(
                titik_indeks,
                [
                    "indeks",
                    "outlier"
                ],
                where_clause
            ) as rows:

                for row in rows:

                    indeks = row[0]

                    if indeks is None:

                        continue

                    if (
                        indeks < lower_bound
                        or indeks > upper_bound
                    ):

                        row[1] = (
                            "Indeks Outlier"
                        )

                    else:

                        row[1] = None

                    rows.updateRow(
                        row
                    )

        # =================================================
        # REFRESH LAYER
        # =================================================

        if arcpy.Exists(
            "Titik_Indeks"
        ):

            try:

                arcpy.management.Delete(
                    "Titik_Indeks"
                )

            except Exception:

                pass

        arcpy.management.MakeFeatureLayer(
            titik_indeks,
            "Titik_Indeks"
        )

        # =================================================
        # APPLY SYMBOLOGY
        # =================================================

        simbologi_path = os.path.join(
            appdata,
            "Simbologi_Titik_Indeks_Outlier.lyrx"
        )

        if os.path.exists(
            simbologi_path
        ):

            arcpy.management.ApplySymbologyFromLayer(
                "Titik_Indeks",
                simbologi_path
            )

        # =================================================
        # OUTPUT
        # =================================================

        parameters[0].value = (
            "Titik_Indeks"
        )

        # =================================================
        # FINISH
        # =================================================

        messages.addMessage(
            "== Proses selesai =="
        )

        return

class Hitung_Indeks_Rata_Rata(object):

    def __init__(self):

        self.label = "Hitung Indeks Rata-Rata"
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

        output_indeks = arcpy.Parameter(
            displayName="Output Titik Indeks",
            name="output_indeks",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [
            output_persil,
            output_indeks
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
        # DATASET
        # =================================================

        persil_path = os.path.join(
            dataset_path,
            "Persil_Baru"
        )

        indeks_path = os.path.join(
            dataset_path,
            "Titik_Indeks"
        )

        temp_path = os.path.join(
            dataset_path,
            "temp_indeks_rata"
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
                    "Persil_Baru "
                    "tidak ditemukan"
                )
            )

            raise arcpy.ExecuteError

        if not arcpy.Exists(
            indeks_path
        ):

            messages.addErrorMessage(
                (
                    "Feature class "
                    "Titik_Indeks "
                    "tidak ditemukan"
                )
            )

            raise arcpy.ExecuteError

        # =================================================
        # DELETE TEMP
        # =================================================

        self.delete_if_exists(
            temp_path
        )

        # =================================================
        # SPATIAL JOIN
        # =================================================

        messages.addMessage(
            "== Spatial Join =="
        )

        arcpy.analysis.SpatialJoin(
            indeks_path,
            persil_path,
            temp_path
        )

        # =================================================
        # ADD FIELD
        # =================================================

        self.add_field_if_not_exists(
            temp_path,
            "indeks_rata",
            "DOUBLE",
            2
        )

        self.add_field_if_not_exists(
            persil_path,
            "indeks_rata",
            "DOUBLE",
            2
        )

        self.add_field_if_not_exists(
            indeks_path,
            "indeks_rata",
            "DOUBLE",
            2
        )

        # =================================================
        # GET LIST ZONASI
        # =================================================

        list_zona = []

        with arcpy.da.SearchCursor(
            persil_path,
            ["s_zonasi"],
            "s_zonasi IS NOT NULL"
        ) as rows:

            for row in rows:

                if row[0] is not None:

                    list_zona.append(
                        int(row[0])
                    )

        list_zona = sorted(
            list(
                set(list_zona)
            )
        )

        # =================================================
        # HITUNG RATA-RATA
        # =================================================

        for zona in list_zona:

            messages.addMessage(
                (
                    f"== Zonasi "
                    f"{zona} =="
                )
            )

            total = 0
            jumlah = 0

            where_clause = (
                f"s_zonasi = {zona}"
            )

            with arcpy.da.SearchCursor(
                temp_path,
                [
                    "indeks",
                    "outlier"
                ],
                where_clause
            ) as rows:

                for row in rows:

                    indeks = row[0]
                    outlier = row[1]

                    if (
                        not outlier
                        and indeks is not None
                    ):

                        total += indeks
                        jumlah += 1

            # =============================================
            # SKIP JIKA TIDAK ADA DATA
            # =============================================

            if jumlah == 0:

                messages.addWarningMessage(
                    (
                        f"Tidak ada "
                        f"data valid "
                        f"untuk zonasi "
                        f"{zona}"
                    )
                )

                continue

            rata = round(
                (total / float(jumlah)),
                2
            )

            messages.addMessage(
                (
                    f"Indeks rata-rata: "
                    f"{rata}"
                )
            )

            # =============================================
            # UPDATE TITIK INDEKS
            # =============================================

            with arcpy.da.UpdateCursor(
                indeks_path,
                ["indeks_rata"],
                where_clause
            ) as rows:

                for row in rows:

                    row[0] = rata

                    rows.updateRow(
                        row
                    )

            # =============================================
            # UPDATE PERSIL
            # =============================================

            with arcpy.da.UpdateCursor(
                persil_path,
                ["indeks_rata"],
                where_clause
            ) as rows:

                for row in rows:

                    row[0] = rata

                    rows.updateRow(
                        row
                    )

        # =================================================
        # CLEAR OUTLIER VALUE
        # =================================================

        messages.addMessage(
            "== Membersihkan outlier =="
        )

        indeks_dict = {}

        with arcpy.da.SearchCursor(
            indeks_path,
            [
                "IdBidang",
                "outlier"
            ]
        ) as rows:

            for row in rows:

                indeks_dict[
                    row[0]
                ] = row[1]

        # =================================================
        # UPDATE PERSIL
        # =================================================

        with arcpy.da.UpdateCursor(
            persil_path,
            [
                "IdBidang",
                "indeks_rata"
            ]
        ) as rows:

            for row in rows:

                bidang_id = row[0]

                if (
                    bidang_id in indeks_dict
                    and indeks_dict[bidang_id]
                    == "Indeks Outlier"
                ):

                    row[1] = None

                    rows.updateRow(
                        row
                    )

        # =================================================
        # UPDATE TITIK INDEKS
        # =================================================

        with arcpy.da.UpdateCursor(
            indeks_path,
            [
                "outlier",
                "indeks_rata"
            ]
        ) as rows:

            for row in rows:

                if (
                    row[0]
                    == "Indeks Outlier"
                ):

                    row[1] = None

                    rows.updateRow(
                        row
                    )

        # =================================================
        # REFRESH LAYER
        # =================================================

        self.delete_if_exists(
            "Persil_Baru"
        )

        self.delete_if_exists(
            "Titik_Indeks"
        )

        arcpy.management.MakeFeatureLayer(
            persil_path,
            "Persil_Baru"
        )

        arcpy.management.MakeFeatureLayer(
            indeks_path,
            "Titik_Indeks"
        )

        # =================================================
        # OUTPUT
        # =================================================

        parameters[0].value = (
            "Persil_Baru"
        )

        parameters[1].value = (
            "Titik_Indeks"
        )

        # =================================================
        # DELETE TEMP
        # =================================================

        self.delete_if_exists(
            temp_path
        )

        # =================================================
        # FINISH
        # =================================================

        messages.addMessage(
            "== Proses selesai =="
        )

        return
    

class Hitung_Nilai_Prediksi(object):

    def __init__(self):

        self.label = "Hitung Nilai Prediksi"
        self.description = ""
        self.canRunInBackground = False

    # =====================================================
    # PARAMETER
    # =====================================================

    def getParameterInfo(self):

        output_layer = arcpy.Parameter(
            displayName="Output Persil",
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

        persil_path = os.path.join(
            dataset_path,
            "Persil_Baru"
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
                    "Persil_Baru "
                    "tidak ditemukan"
                )
            )

            raise arcpy.ExecuteError

        required_fields = [
            "indeks_rata",
            "NILAI_LAMA",
            "PREDICTED"
        ]

        existing_fields = [
            field.name
            for field in arcpy.ListFields(
                persil_path
            )
        ]

        missing_fields = [
            field
            for field in required_fields
            if field not in existing_fields
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
        # HITUNG PREDIKSI
        # =================================================

        messages.addMessage(
            "== Menghitung nilai prediksi =="
        )

        total_updated = 0

        with arcpy.da.UpdateCursor(
            persil_path,
            [
                "indeks_rata",
                "NILAI_LAMA",
                "PREDICTED"
            ]
        ) as cursor:

            for row in cursor:

                indeks_rata = row[0]
                nilai_lama = row[1]
                predicted = row[2]

                # =========================================
                # HITUNG JIKA BELUM ADA NILAI
                # =========================================

                if (
                    predicted is None
                    and nilai_lama is not None
                    and indeks_rata is not None
                ):

                    row[2] = (
                        nilai_lama
                        * indeks_rata
                    ) / 100.0

                    cursor.updateRow(
                        row
                    )

                    total_updated += 1

        messages.addMessage(
            (
                f"{total_updated} "
                f"persil berhasil "
                f"dihitung"
            )
        )

        # =================================================
        # REFRESH LAYER
        # =================================================

        self.delete_if_exists(
            "Persil_Baru"
        )

        arcpy.management.MakeFeatureLayer(
            persil_path,
            "Persil_Baru"
        )

        # =================================================
        # APPLY SYMBOLOGY
        # =================================================

        simbologi_path = os.path.join(
            appdata,
            "Simbologi_PetaNBTUpdate.lyrx"
        )

        if os.path.exists(
            simbologi_path
        ):

            arcpy.management.ApplySymbologyFromLayer(
                "Persil_Baru",
                simbologi_path
            )

        # =================================================
        # OUTPUT
        # =================================================

        parameters[0].value = (
            "Persil_Baru"
        )

        # =================================================
        # FINISH
        # =================================================

        messages.addMessage(
            "== Proses selesai =="
        )

        return