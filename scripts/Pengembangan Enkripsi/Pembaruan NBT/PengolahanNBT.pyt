import os, arcpy, json, sys, datetime, gc, time

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
        self.tools = [Hitung_Indeks_Rata_Rata, Hitung_Nilai_Prediksi]


class Hitung_Indeks_Rata_Rata(object):

    def __init__(self):

        self.label = "Hitung Indeks NBT"
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

        output_titik = arcpy.Parameter(
            displayName="Output Titik Zona",
            name="output_titik",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [
            output_persil,
            output_titik
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

        existing_fields = [

            field.name.upper()
            for field in arcpy.ListFields(
                feature_class
            )
        ]

        if field_name.upper() not in existing_fields:

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
        import gc
        import time
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

        titik_zona = os.path.join(
            dataset_path,
            "Titik_Zona"
        )

        persil_path = os.path.join(
            dataset_path,
            "Persil_Layer"
        )

        mean_table = os.path.join(
            "in_memory",
            "mean_indeks_nbt"
        )

        spatial_join = os.path.join(
            "in_memory",
            "sj_indeks_nbt"
        )

        # =================================================
        # VALIDASI
        # =================================================

        required_fc = [

            titik_zona,
            persil_path

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
        # CLEAN TEMP
        # =================================================

        cleanup_items = [

            mean_table,
            spatial_join

        ]

        for item in cleanup_items:

            self.delete_if_exists(
                item
            )

        # =================================================
        # VALIDASI CLUSTER
        # =================================================

        messages.addMessage(
            "== Validasi cluster =="
        )

        arcpy.analysis.SpatialJoin(
            persil_path,
            titik_zona,
            spatial_join,
            "JOIN_ONE_TO_MANY"
        )

        cluster_has_point = set()

        with arcpy.da.SearchCursor(
            spatial_join,
            [
                "Join_Count",
                "TARGET_FID"
            ]
        ) as rows:

            for row in rows:

                join_count = row[0]
                target_fid = row[1]

                if join_count > 0:

                    cluster_has_point.add(
                        target_fid
                    )

        cluster_dict = {}

        with arcpy.da.SearchCursor(
            persil_path,
            [
                "OBJECTID",
                "S_ZONASI",
                "KLSTRZ"
            ]
        ) as rows:

            for row in rows:

                oid = row[0]
                zonasi = row[1]
                cluster = row[2]

                if cluster not in (
                    None,
                    0
                ):

                    key = (
                        zonasi,
                        cluster
                    )

                    cluster_dict.setdefault(
                        key,
                        []
                    ).append(
                        oid
                    )

        invalid_cluster = []

        for key, oid_list in cluster_dict.items():

            has_titik = any(
                oid in cluster_has_point
                for oid in oid_list
            )

            if not has_titik:

                invalid_cluster.append(
                    (
                        f"Zonasi "
                        f"{key[0]} "
                        f"- Cluster "
                        f"{key[1]}"
                    )
                )

        if invalid_cluster:

            messages.addWarningMessage(
                (
                    "Cluster tanpa Titik Zona:\n"
                    +
                    "\n".join(
                        invalid_cluster
                    )
                )
            )

        else:

            messages.addMessage(
                "✅ Validasi cluster OK"
            )

        # =================================================
        # FIELD JOIN KEY
        # =================================================

        join_field = "JOIN_KEY"

        self.add_field_if_not_exists(
            titik_zona,
            join_field,
            "TEXT"
        )

        self.add_field_if_not_exists(
            persil_path,
            join_field,
            "TEXT"
        )

        # =================================================
        # CALCULATE JOIN KEY
        # =================================================

        messages.addMessage(
            "== Membuat join key =="
        )

        expression = (
            "'SZ_' + "
            "str(!S_ZONASI!) + "
            "'_K_' + "
            "str(!KLSTRZ!)"
        )

        arcpy.management.CalculateField(
            titik_zona,
            join_field,
            expression,
            "PYTHON3"
        )

        arcpy.management.CalculateField(
            persil_path,
            join_field,
            expression,
            "PYTHON3"
        )

        # =================================================
        # STATISTIC
        # =================================================

        messages.addMessage(
            "== Hitung statistik indeks =="
        )

        arcpy.analysis.Statistics(
            titik_zona,
            mean_table,
            [
                ["INDEKS", "MEAN"],
                ["INDEKS", "MIN"],
                ["INDEKS", "MAX"],
                ["INDEKS", "STD"],
                ["INDEKS", "COUNT"]
            ],
            [
                "S_ZONASI",
                "KLSTRZ"
            ]
        )

        # =================================================
        # FIELD OUTPUT
        # =================================================

        output_fields = [

            ("INDEKS_RATA", "DOUBLE"),
            ("INDEKS_MIN", "DOUBLE"),
            ("INDEKS_MAX", "DOUBLE"),
            ("INDEKS_STD", "DOUBLE"),
            ("JUMLAH_TITIK", "LONG")

        ]

        for field_name, field_type in output_fields:

            self.add_field_if_not_exists(
                titik_zona,
                field_name,
                field_type
            )

            self.add_field_if_not_exists(
                persil_path,
                field_name,
                field_type
            )

        # =================================================
        # ADD JOIN FIELD TO MEAN TABLE
        # =================================================

        self.add_field_if_not_exists(
            mean_table,
            join_field,
            "TEXT"
        )

        arcpy.management.CalculateField(
            mean_table,
            join_field,
            expression,
            "PYTHON3"
        )

        # =================================================
        # JOIN TITIK ZONA
        # =================================================

        messages.addMessage(
            "== Update Titik Zona =="
        )

        arcpy.management.JoinField(
            titik_zona,
            join_field,
            mean_table,
            join_field,
            [
                "MEAN_INDEKS",
                "MIN_INDEKS",
                "MAX_INDEKS",
                "STD_INDEKS",
                "COUNT_INDEKS"
            ]
        )

        with arcpy.da.UpdateCursor(
            titik_zona,
            [
                "MEAN_INDEKS",
                "MIN_INDEKS",
                "MAX_INDEKS",
                "STD_INDEKS",
                "COUNT_INDEKS",

                "INDEKS_RATA",
                "INDEKS_MIN",
                "INDEKS_MAX",
                "INDEKS_STD",
                "JUMLAH_TITIK"
            ]
        ) as rows:

            for row in rows:

                row[5] = row[0]
                row[6] = row[1]
                row[7] = row[2]
                row[8] = row[3]
                row[9] = row[4]

                rows.updateRow(
                    row
                )

        # =================================================
        # JOIN PERSIL
        # =================================================

        messages.addMessage(
            "== Update Persil =="
        )

        arcpy.management.JoinField(
            persil_path,
            join_field,
            mean_table,
            join_field,
            [
                "MEAN_INDEKS",
                "MIN_INDEKS",
                "MAX_INDEKS",
                "STD_INDEKS",
                "COUNT_INDEKS"
            ]
        )

        with arcpy.da.UpdateCursor(
            persil_path,
            [
                "KLSTRZ",

                "MEAN_INDEKS",
                "MIN_INDEKS",
                "MAX_INDEKS",
                "STD_INDEKS",
                "COUNT_INDEKS",

                "INDEKS_RATA",
                "INDEKS_MIN",
                "INDEKS_MAX",
                "INDEKS_STD",
                "JUMLAH_TITIK"
            ]
        ) as rows:

            for row in rows:

                cluster = row[0]

                if cluster not in (
                    None,
                    0
                ):

                    row[6] = row[1]
                    row[7] = row[2]
                    row[8] = row[3]
                    row[9] = row[4]
                    row[10] = row[5]

                else:

                    row[6] = None
                    row[7] = None
                    row[8] = None
                    row[9] = None
                    row[10] = None

                rows.updateRow(
                    row
                )

        # =================================================
        # DELETE JOIN FIELD
        # =================================================

        delete_fields = [

            "MEAN_INDEKS",
            "MIN_INDEKS",
            "MAX_INDEKS",
            "STD_INDEKS",
            "COUNT_INDEKS"

        ]

        existing_titik = [

            f.name
            for f in arcpy.ListFields(
                titik_zona
            )
        ]

        existing_persil = [

            f.name
            for f in arcpy.ListFields(
                persil_path
            )
        ]

        delete_titik = [

            f
            for f in delete_fields
            if f in existing_titik
        ]

        delete_persil = [

            f
            for f in delete_fields
            if f in existing_persil
        ]

        if delete_titik:

            arcpy.management.DeleteField(
                titik_zona,
                delete_titik
            )

        if delete_persil:

            arcpy.management.DeleteField(
                persil_path,
                delete_persil
            )

        # =================================================
        # REFRESH LAYER
        # =================================================

        self.delete_if_exists(
            "Persil_Layer"
        )

        self.delete_if_exists(
            "Titik_Zona"
        )

        arcpy.management.MakeFeatureLayer(
            persil_path,
            "Persil_Layer"
        )

        arcpy.management.MakeFeatureLayer(
            titik_zona,
            "Titik_Zona"
        )

        # =================================================
        # OUTPUT
        # =================================================

        parameters[0].value = (
            "Persil_Layer"
        )

        parameters[1].value = (
            "Titik_Zona"
        )

        # =================================================
        # CLEAN TEMP
        # =================================================

        time.sleep(1)

        arcpy.ClearWorkspaceCache_management()

        gc.collect()

        for item in cleanup_items:

            self.delete_if_exists(
                item
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

        self.label = "Hitung Nilai NBT Pembaruan"
        self.description = ""
        self.canRunInBackground = False

    # =====================================================
    # PARAMETER
    # =====================================================

    def getParameterInfo(self):

        pembulatan = arcpy.Parameter(
            displayName="Pembulatan Nilai NBT",
            name="pembulatan",
            datatype="GPLong",
            parameterType="Required",
            direction="Input"
        )

        pembulatan.value = 1000

        penjelasan = arcpy.Parameter(
            displayName="Apa yang dilakukan tool ini?",
            name="penjelasan",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )

        penjelasan.value = (
            "Tool ini menghitung nilai NBT baru\n"
            "berdasarkan indeks rata-rata NBT\n"
            "yang telah dihitung sebelumnya.\n\n"
            "Nilai baru dihitung menggunakan:\n"
            "NILAIBD = NILAIBD_LAMA x "
            "(INDEKS_RATA / 100)\n\n"
            "Tool hanya memproses persil\n"
            "yang memiliki cluster valid\n"
            "dan indeks rata-rata.\n\n"
            "Direktorat Penilaian Tanah "
            "& Ekonomi Pertanahan\n"
            "Kementerian ATR/BPN\n"
            "Tahun: {}".format(
                datetime.datetime.now().year
            )
        )

        output_layer = arcpy.Parameter(
            displayName="Output Persil",
            name="output_persil",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [
            pembulatan,
            penjelasan,
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

    def add_field_if_not_exists(
        self,
        feature_class,
        field_name,
        field_type,
        field_length=None
    ):

        existing_fields = [

            field.name.upper()
            for field in arcpy.ListFields(
                feature_class
            )
        ]

        if field_name.upper() not in existing_fields:

            if field_length:

                arcpy.management.AddField(
                    feature_class,
                    field_name,
                    field_type,
                    field_length=field_length
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
        import sys
        import arcpy
        import datetime

        arcpy.env.overwriteOutput = True

        messages.addMessage(
            "== Proses dimulai =="
        )

        # =================================================
        # PARAMETER
        # =================================================

        pembulatan = int(
            parameters[0].valueAsText
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
            "Persil_Layer"
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
                    "Persil_Layer "
                    "tidak ditemukan"
                )
            )

            raise arcpy.ExecuteError

        required_fields = [

            "KLSTRZ",
            "NILAIBD",
            "NILAIBD_LAMA",
            "INDEKS_RATA"

        ]

        existing_fields = {

            field.name.upper()
            for field in arcpy.ListFields(
                persil_path
            )
        }

        missing_fields = [

            field_name
            for field_name in required_fields
            if field_name.upper()
            not in existing_fields

        ]

        if missing_fields:

            for field_name in missing_fields:

                if (
                    field_name
                    == "INDEKS_RATA"
                ):

                    messages.addErrorMessage(
                        (
                            "Data indeks rata-rata "
                            "NBT belum tersedia.\n"
                            "Jalankan tool "
                            "'Hitung Indeks NBT' "
                            "terlebih dahulu."
                        )
                    )

                else:

                    messages.addErrorMessage(
                        (
                            f"Field tidak ditemukan: "
                            f"{field_name}"
                        )
                    )

            raise arcpy.ExecuteError

        # =================================================
        # FIELD OUTPUT
        # =================================================

        self.add_field_if_not_exists(
            persil_path,
            "NILBULAT",
            "TEXT",
            50
        )

        # =================================================
        # HITUNG NILAIBD
        # =================================================

        messages.addMessage(
            "== Hitung nilai NBT =="
        )

        with arcpy.da.UpdateCursor(
            persil_path,
            [
                "KLSTRZ",
                "NILAIBD",
                "NILAIBD_LAMA",
                "INDEKS_RATA"
            ]
        ) as rows:

            for row in rows:

                cluster = row[0]
                nilai_lama = row[2]
                indeks_rata = row[3]

                if (
                    cluster not in (
                        None,
                        0
                    )
                    and
                    indeks_rata is not None
                    and
                    nilai_lama is not None
                ):

                    try:

                        nilai_baru = (
                            float(nilai_lama)
                            *
                            (
                                float(indeks_rata)
                                / 100.0
                            )
                        )

                        row[1] = round(
                            nilai_baru,
                            2
                        )

                    except Exception:

                        row[1] = None

                else:

                    row[1] = None

                rows.updateRow(
                    row
                )

        messages.addMessage(
            "✅ Nilai NBT berhasil dihitung"
        )

        # =================================================
        # HITUNG NILBULAT
        # =================================================

        messages.addMessage(
            "== Hitung nilai pembulatan =="
        )

        code_block = f"""

def doSomething(
    nilai,
    pembulatan
):

    if nilai:

        rounded = (
            round(
                nilai / pembulatan
            )
            *
            pembulatan
        )

        return (
            "Rp. {{:,}}"
            .format(
                int(rounded)
            )
            .replace(",", ".")
        )

    return ""

"""

        arcpy.management.CalculateField(
            persil_path,
            "NILBULAT",
            (
                f"doSomething("
                f"!NILAIBD!, "
                f"{pembulatan}"
                f")"
            ),
            "PYTHON3",
            code_block
        )

        # =================================================
        # REFRESH LAYER
        # =================================================

        self.delete_if_exists(
            "Persil_Layer"
        )

        arcpy.management.MakeFeatureLayer(
            persil_path,
            "Persil_Layer"
        )

        # =================================================
        # OUTPUT
        # =================================================

        parameters[2].value = (
            "Persil_Layer"
        )

        # =================================================
        # FINISH
        # =================================================

        messages.addMessage(
            "== Proses selesai =="
        )

        return

    def postExecute(
        self,
        parameters
    ):

        return
    

# DUMP
class Hitung_Indeks_Rata_Rata_OLD(object):

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
            "Persil_Layer"
        )

        indeks_path = os.path.join(
            dataset_path,
            "Titik_Zona"
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
                    "Persil_Layer "
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
                    "Titik_Zona "
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
            ["S_ZONASI"],
            "S_ZONASI IS NOT NULL"
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
                f"S_ZONASI = {zona}"
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
                "IDBIDANG",
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
    
class Hitung_Nilai_Prediksi_OLD(object):

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
