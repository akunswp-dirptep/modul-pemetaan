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
        self.tools = [Hitung_Indeks_Rata_Rata, Hitung_Nilai_Prediksi, Hitung_Harga_Menyebar]


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
            "INDEKS_RATA",
            "KELOMPOK_PERUBAHAN"

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
            [ "KLSTRZ", "NILAIBD", "NILAIBD_LAMA", "INDEKS_RATA", "KELOMPOK_PERUBAHAN"]
        ) as rows:
            for row in rows:

                cluster = row[0]
                nilai_lama = row[2]
                indeks_rata = row[3]
                kelompok_perubahan = row[4]

                if kelompok_perubahan is None:

                    if (cluster not in (None, 0)
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
    
class Hitung_Harga_Menyebar(object):

    def __init__(self):
        self.label = "Hitung Harga Menyebar"
        self.description = "Mengubah zonasi dan kelas jalan pada persil terseleksi, sekaligus menghitung ulang NILAIBD_LAMA menggunakan perbandingan dinamis."
        self.canRunInBackground = False

    def getParameterInfo(self):

        pilih_zona = arcpy.Parameter(
            displayName="Pilih Zonasi",
            name="pilih_zona",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )

        edit_kelas_jalan = arcpy.Parameter(
            displayName="Edit Kelas Jalan",
            name="edit_kelas_jalan",
            datatype="GPBoolean",
            parameterType="Required",
            direction="Input"
        )
        edit_kelas_jalan.value = False

        pilih_kelas_jalan = arcpy.Parameter(
            displayName="Pilih Kelas Jalan",
            name="pilih_kelas_jalan",
            datatype="GPString",
            parameterType="Optional", 
            direction="Input"
        )
        pilih_kelas_jalan.filter.type = "ValueList"
        pilih_kelas_jalan.filter.list = [
            "Arteri Primer", "Arteri Sekunder", "Kolektor Primer",
            "Kolektor Sekunder", "Lokal Primer", "Lokal Sekunder", "Setapak"
        ]

        # Parameter Baru: Jarak Maksimal
        max_jarak = arcpy.Parameter(
            displayName="Jarak Maksimal Pencarian Pembanding (Meter)",
            name="max_jarak",
            datatype="GPLong",
            parameterType="Required",
            direction="Input"
        )
        max_jarak.value = 200

        simpan_sebagai_perubahan = arcpy.Parameter(
            displayName="Simpan Sebagai Perubahan",
            name="simpan_sebagai_perubahan",
            datatype="GPBoolean",
            parameterType="Required",
            direction="Input"
        )
        simpan_sebagai_perubahan.value = True

        output_data = arcpy.Parameter(
            name="persil_layer",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [pilih_zona, edit_kelas_jalan, pilih_kelas_jalan, max_jarak, simpan_sebagai_perubahan, output_data]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        if parameters[1].value:
            parameters[2].enabled = True
        else:
            parameters[2].enabled = False

        if parameters[0].altered:
            return

        try:
            configs = persil.get_config_values()
            zonasi_config_path = os.path.join(configs["project_config"]["ws_path"], "zonasiupdate.json")
            if not os.path.exists(zonasi_config_path):
                return

            with open(zonasi_config_path, "r", encoding="utf-8") as f:
                zonasi_json = json.load(f)
            
            parameters[0].filter.type = "ValueList"
            parameters[0].filter.list = list(zonasi_json.keys())
        except:
            pass
        return

    def updateMessages(self, parameters):
        if parameters[1].value and not parameters[2].valueAsText:
            parameters[2].setErrorMessage("Pilih Kelas Jalan harus diisi jika Edit Kelas Jalan dicentang.")
        else:
            parameters[2].clearMessage()
        return

    def add_field_if_not_exists(self, feature_class, field_name, field_type):
        field_names = [field.name for field in arcpy.ListFields(feature_class)]
        if field_name not in field_names:
            arcpy.management.AddField(feature_class, field_name, field_type)

    def delete_if_exists(self, path):
        if arcpy.Exists(path):
            try:
                arcpy.management.Delete(path)
            except Exception:
                pass

    def calculate_penyesuaian(self, objek, pembanding):
        ls_tnh = (objek["ls_tnh_i"] - pembanding["ls_tnh_i"]) * 0.5
        lb_dpn = (objek["lb_dpn_i"] - pembanding["lb_dpn_i"]) * 1.5
        bentuk = (objek["s_bentuk"] - pembanding["s_bentuk"]) * 1.5
        letak = (objek["s_letak"] - pembanding["s_letak"]) * 1
        kls_jln = (objek["s_kls_jln"] - pembanding["s_kls_jln"]) * 3

        persentase = (ls_tnh + lb_dpn + bentuk + letak + kls_jln)
        nilai = pembanding["nilai"] * (100 + persentase) / 100

        komponen = [ls_tnh, lb_dpn, bentuk, letak, kls_jln]
        nilai_nol = komponen.count(0)

        return {
            "persentase": abs(persentase),
            "nilai": nilai,
            "nilai_nol": nilai_nol
        }

    def execute(self, parameters, messages):
        messages.addMessage("== Proses dimulai ==")

        zonasi = parameters[0].valueAsText
        is_edit_kls_jln = parameters[1].value
        kls_jln = parameters[2].valueAsText
        max_jarak = parameters[3].value
        simpan_sebagai_data_baru = parameters[4].value
        interval = 20 

        configs = persil.get_config_values()

        # Ambil config zonasi
        zonasi_config_path = os.path.join(configs["project_config"]["ws_path"], "zonasiupdate.json")
        if not os.path.exists(zonasi_config_path):
            messages.addErrorMessage("== File konfigurasi zonasi tidak ditemukan ==")
            raise arcpy.ExecuteError

        with open(zonasi_config_path, "r", encoding="utf-8") as f:
            zonasi_json = json.load(f)

        if zonasi not in zonasi_json:
            messages.addErrorMessage(f"== Zonasi '{zonasi}' tidak ditemukan ==")
            raise arcpy.ExecuteError

        s_zonasi = zonasi_json[zonasi].get("s_zonasi",  0)
        min_lb_jln = zonasi_json[zonasi].get("min_lb_jln", 1.5)

        # Ambil config kelas jalan
        s_kls_jln = 0
        if is_edit_kls_jln:
            if not kls_jln:
                messages.addErrorMessage("== Kelas Jalan belum dipilih ==")
                raise arcpy.ExecuteError
            try:
                kelas_jalan_config = configs["jaringan_jalan_config"]["skoring"]["kelas_jalan"]
                s_kls_jln = kelas_jalan_config.get(kls_jln, 0)
            except KeyError:
                messages.addErrorMessage("== Key konfigurasi kelas jalan tidak ditemukan ==")
                raise arcpy.ExecuteError

        dataset_path = configs["project_config"]["dataset_path"]
        persil_edit = "Persil_Layer"
        persil_edit_path = os.path.join(dataset_path, persil_edit)

        # Siapkan Field
        self.add_field_if_not_exists(persil_edit_path, "min_lb_jln", "DOUBLE")
        self.add_field_if_not_exists(persil_edit_path, "data_pembanding", "TEXT")
        self.add_field_if_not_exists(persil_edit_path, "perubahan", "TEXT")

        required_fields = [
            "OBJECTID", "ZONASI", "S_ZONASI", "min_lb_jln", "status_per", "KLSJLN", "S_KLS_JLN",
            "NILAIBD_LAMA", "ls_tnh_i", "lb_dpn_i", "S_BENTUK", "S_LETAK", "IDBIDANG",
            "perubahan", "data_pembanding"
        ]

        persil_fields = [f.name for f in arcpy.ListFields(persil_edit_path)]
        missing_fields = [f for f in required_fields if f not in persil_fields]
        if missing_fields:
            messages.addErrorMessage(f"== Field berikut tidak ditemukan: {', '.join(missing_fields)} ==")
            raise arcpy.ExecuteError

        ada_seleksi = len(arcpy.Describe(persil_edit).FIDSet)
        if ada_seleksi == 0:
            messages.addErrorMessage("== Error: Tidak ada fitur persil yang terseleksi di Persil_Layer ==")
            raise arcpy.ExecuteError

        # =========================================================
        # 1. BACA DATA TARGET DAN KANDIDAT PEMBANDING KE MEMORI
        # =========================================================
        target_dict = {}
        target_oids = []
        
        messages.addMessage("Membaca target fitur yang terseleksi...")
        # SearchCursor pada persil_edit (layer di Peta) otomatis hanya mengambil yang terseleksi
        with arcpy.da.SearchCursor(persil_edit, ["OBJECTID", "ls_tnh_i", "lb_dpn_i", "S_BENTUK", "S_LETAK", "IDBIDANG", "S_KLS_JLN"]) as rows:
            for row in rows:
                target_oids.append(row[0])
                target_dict[row[0]] = {
                    "OBJECTID": row[0],
                    "s_zonasi": s_zonasi, # Memakai nilai parameter user
                    "s_kls_jln": s_kls_jln if is_edit_kls_jln else (row[6] or 0), 
                    "ls_tnh_i": row[1] or 0,
                    "lb_dpn_i": row[2] or 0,
                    "s_bentuk": row[3] or 0,
                    "s_letak": row[4] or 0,
                    "IDBIDANG": row[5]
                }

        pembanding_dict = {}
        arcpy.AddMessage(pembanding_dict)
        messages.addMessage("Membaca data referensi pembanding...")
        # SearchCursor pada persil_edit_path (jalur GDB) mengambil seluruh data untuk pembanding
        fields_kandidat = ["OBJECTID", "S_ZONASI", "S_KLS_JLN", "NILAIBD_LAMA", "ls_tnh_i", "lb_dpn_i", "S_BENTUK", "S_LETAK", "IDBIDANG"]
        with arcpy.da.SearchCursor(persil_edit_path, fields_kandidat, "perubahan IS NULL AND NILAIBD_LAMA > 0") as rows:
            for row in rows:
                if row[0] not in target_oids:
                    pembanding_dict[row[0]] = {
                        "OBJECTID": row[0],
                        "s_zonasi": row[1],
                        "s_kls_jln": row[2] or 0,
                        "nilai": row[3],
                        "ls_tnh_i": row[4] or 0,
                        "lb_dpn_i": row[5] or 0,
                        "s_bentuk": row[6] or 0,
                        "s_letak": row[7] or 0,
                        "IDBIDANG": row[8]
                    }

        if not pembanding_dict:
            messages.addWarningMessage("Tidak ada kandidat pembanding valid di dalam database.")

        # =========================================================
        # 2. PROSES NEAR TABLE DINAMIS
        # =========================================================
        target_layer = "target_layer_temp"
        kandidat_layer = "kandidat_layer_temp"
        near_table = "memory\\bulk_near_table" 

        self.delete_if_exists(kandidat_layer)
        arcpy.management.MakeFeatureLayer(persil_edit_path, kandidat_layer, "perubahan IS NULL AND NILAIBD_LAMA IS NOT NULL AND NILAIBD_LAMA > 0")

        unresolved_targets = set(target_oids)
        dict_hasil_hitung = {}
        jumlah_pembanding = 3

        interval_list = list(range(interval, max_jarak + interval, interval))
        if interval_list[-1] > max_jarak:
            interval_list[-1] = max_jarak
        
        messages.addMessage("Melakukan perhitungan nilai dengan pencarian jarak dinamis...")

        for jarak_sekarang in interval_list:
            if not unresolved_targets:
                break 

            messages.addMessage(f"Mencari kandidat pada radius {jarak_sekarang} meter... (Sisa Target: {len(unresolved_targets)})")

            target_oids_str = ",".join(map(str, unresolved_targets))
            target_where = f"OBJECTID IN ({target_oids_str})"
            
            self.delete_if_exists(target_layer)
            self.delete_if_exists(near_table)
            arcpy.management.MakeFeatureLayer(persil_edit_path, target_layer, target_where)

            arcpy.analysis.GenerateNearTable(
                in_features=target_layer,
                near_features=kandidat_layer,
                out_table=near_table,
                search_radius=f"{jarak_sekarang} Meters",
                location="NO_LOCATION",
                angle="NO_ANGLE",
                closest="ALL"
            )

            near_results = {}
            if arcpy.Exists(near_table):
                with arcpy.da.SearchCursor(near_table, ["IN_FID", "NEAR_FID", "NEAR_DIST"]) as rows:
                    for in_fid, near_fid, near_dist in rows:
                        if in_fid not in near_results:
                            near_results[in_fid] = []
                        near_results[in_fid].append((near_fid, near_dist))

            max_jarak_safe = max_jarak if max_jarak > 0 else 1

            for target_oid in list(unresolved_targets):
                objek = target_dict[target_oid]
                kandidat_list = near_results.get(target_oid, [])
                hasil_rekomendasi = []

                for near_fid, jarak in kandidat_list:
                    if near_fid in pembanding_dict:
                        pembanding = pembanding_dict[near_fid]
                        if objek['s_zonasi'] == pembanding['s_zonasi']:
                            hasil = self.calculate_penyesuaian(objek, pembanding)
                            
                            if abs(hasil["persentase"]) > 10:
                                continue 
                            
                            skor_jarak = (jarak / max_jarak_safe) * 100 
                            skor_persentase = abs(hasil["persentase"])
                            skor_pemilihan = (skor_jarak * 0.70) + (skor_persentase * 0.30)
                            
                            hasil_rekomendasi.append({
                                "OBJECTID": near_fid,
                                "jarak": round(jarak, 2),
                                "skor_pemilihan": skor_pemilihan, 
                                "nilai_nol": hasil["nilai_nol"],
                                "data_hasil": hasil 
                            })

                hasil_rekomendasi.sort(key=lambda x: (x["skor_pemilihan"], -x["nilai_nol"], x["jarak"]))
                is_last_interval = (jarak_sekarang == interval_list[-1])
                
                if len(hasil_rekomendasi) >= jumlah_pembanding:
                    rekomendasi_final = hasil_rekomendasi[:jumlah_pembanding]
                    validasi_berhasil = True
                    hasil_list = []
                    id_pembanding_list = []

                    for rec in rekomendasi_final:
                        hasil = rec["data_hasil"]
                        if hasil["persentase"] > 10:
                            validasi_berhasil = False
                            break
                        hasil_list.append(hasil)
                        id_pembanding_list.append(str(rec['OBJECTID']))

                    if validasi_berhasil:
                        total_nol = sum(h["nilai_nol"] for h in hasil_list)
                        nilai_akhir = 0

                        if total_nol > 0:
                            for h in hasil_list:
                                bobot = (h["nilai_nol"] / total_nol) 
                                nilai_akhir += h["nilai"] * bobot
                        else:
                            bobot_rata = 1.0 / len(hasil_list)
                            for h in hasil_list:
                                nilai_akhir += h["nilai"] * bobot_rata

                        dict_hasil_hitung[target_oid] = {
                            "data_pembanding": " ; ".join(id_pembanding_list),
                            "nilai_akhir": nilai_akhir
                        }
                        unresolved_targets.remove(target_oid)
                else:
                    if is_last_interval:
                        arcpy.AddWarning(f"IDBIDANG {objek['IDBIDANG']} dilewati (Pembanding valid kurang dari {jumlah_pembanding}). Nilai persil ini tidak akan dihitung.")

        self.delete_if_exists(target_layer)
        self.delete_if_exists(kandidat_layer)
        self.delete_if_exists(near_table)

        # =========================================================
        # 3. UPDATE SELURUH ATRIBUT KE PERSIL_LAYER
        # =========================================================
        messages.addMessage("== Menyimpan seluruh pembaruan zonasi, jalan, dan hasil perhitungan ke layer ==")

        update_fields = [
            "OBJECTID", "ZONASI", "S_ZONASI", "min_lb_jln", "status_per", 
            "NILAIBD_LAMA", "data_pembanding", "perubahan"
        ]
        
        if is_edit_kls_jln:
            update_fields.extend(["KLSJLN", "S_KLS_JLN"])

        # Update Cursor hanya memengaruhi data terseleksi
        with arcpy.da.UpdateCursor(persil_edit, update_fields) as rows:
            for row in rows:
                oid = row[0]

                # Update Parameter Zonasi
                row[1] = zonasi
                row[2] = s_zonasi
                row[3] = min_lb_jln

                if simpan_sebagai_data_baru:
                    row[4] = "update"
                    row[7] = "individual"

                # Masukkan hasil hitung jika oid ditemukan di dictionary hasil
                if oid in dict_hasil_hitung:
                    row[5] = dict_hasil_hitung[oid]["nilai_akhir"]
                    row[6] = dict_hasil_hitung[oid]["data_pembanding"]

                # Update Parameter Kelas Jalan
                if is_edit_kls_jln:
                    row[8] = kls_jln
                    row[9] = s_kls_jln
                
                rows.updateRow(row)

        messages.addMessage("== Proses selesai ==")
        
        simbology_path = r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Simbologi_Zonasi_Persil_Layer.lyrx"
        arcpy.management.MakeFeatureLayer(persil_edit_path, "Persil_Layer")
        try:
            arcpy.management.ApplySymbologyFromLayer("Persil_Layer", simbology_path)
        except Exception as e:
            messages.addWarningMessage(f"== Peringatan Simbologi: {str(e)} ==")

        # Indeks set parameter adalah 5 (sesuai urutan output_data)
        arcpy.SetParameter(5, "Persil_Layer")
        
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
