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
        self.tools = [Persiapan_Persil_Individual,
                      Hitung_Persil_Individual,
                      Reset_Persil_Individual,
                      Generate_Titik_Indeks,
                      Deteksi_Outlier_Indeks,
                      Set_Cluster_Persil,
                      Periksa_Titik_Sampel_Kelompok_Perubahan,
                      Hitung_Statistik_Cluster,
                      Hitung_Individual_Cluster,
                      Pengembalian_Cluster]


class Persiapan_Persil_Individual(object):

    def __init__(self):

        self.label = "Persiapan Persil Individual"
        self.description = ""
        self.canRunInBackground = False

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

    def execute(self, parameters, messages):

        messages.addMessage( "== Proses dimulai ==" )
        configs = persil.get_config_values()

        dataset_path = configs["project_config"]["dataset_path"]
        persil_nama = "Persil_Layer"
        persil_path = os.path.join( dataset_path, persil_nama )

        self.add_field_if_not_exists(
            persil_path,
            "perubahan",
            "TEXT"
        )

        self.add_field_if_not_exists(
            persil_path,
            "lb_dpn_i",
            "SHORT"
        )

        self.add_field_if_not_exists(
            persil_path,
            "ls_tnh_i",
            "SHORT"
        )

        self.add_field_if_not_exists(
            persil_path,
            "NILAI_LAMA",
            "DOUBLE"
        )

        messages.addMessage("== Update perubahan persil ==" )

        with arcpy.da.UpdateCursor(
            persil_path,  ["status_per", "kelompok_perubahan",  "perubahan" ]
        ) as rows:
            for row in rows:

                if row[0] == "update":
                    if row[1] is not None or 0:
                        row[2] = "mengelompok"

                    else:
                        row[2] = "menyebar"
                rows.updateRow( row )

        messages.addMessage( "== Update klasifikasi persil ==" )

        with arcpy.da.UpdateCursor(persil_path, ["LUASM2", "LBRDPN", "ls_tnh_i", "lb_dpn_i"]) as rows:

            for row in rows:

                value_ls_tnh = row[0]
                value_lb_dpn = row[1]

                # Klasifikasi luas tanah
                if value_ls_tnh is None:
                    row[2] = 0

                elif value_ls_tnh < 50:
                    row[2] = 1

                elif value_ls_tnh > 1000:
                    row[2] = 2

                elif (
                    value_ls_tnh >= 200
                    and value_ls_tnh <= 1000
                ):
                    row[2] = 3

                elif (
                    value_ls_tnh >= 50
                    and value_ls_tnh < 100
                ):
                    row[2] = 4

                elif (
                    value_ls_tnh >= 100
                    and value_ls_tnh <= 200
                ):
                    row[2] = 5

                # Klasifikasi lebar depan
                if value_lb_dpn is None:
                    row[3] = 0

                elif value_lb_dpn <= 0:
                    row[3] = 0

                elif value_lb_dpn < 6:
                    row[3] = 1

                elif (
                    value_lb_dpn > 6
                    and value_lb_dpn <= 10
                ):
                    row[3] = 2

                elif (
                    value_lb_dpn > 10
                    and value_lb_dpn <= 15
                ):
                    row[3] = 3

                elif value_lb_dpn > 15:
                    row[3] = 4

                rows.updateRow(row)

        messages.addMessage(
            "== Update nilai prediksi =="
        )
        field_names = [f.name for f in arcpy.ListFields(persil_path)]

        if "NILAIBD_LAMA" not in field_names:

            arcpy.management.AddField(
                persil_path,
                "NILAIBD_LAMA",
                "LONG"
            )
        arcpy.management.CalculateField(
            persil_path,
            "NILAIBD_LAMA",
            "!NILAIBD!",
            "PYTHON3"
        )

        arcpy.management.CalculateField(
            persil_path,
            "NILAIBD",
            "None",
            "PYTHON3"
        )

        arcpy.SetParameter(0, persil_nama)


        messages.addMessage( "== Proses selesai ==" )

        return

    def add_field_if_not_exists( self,  feature_class, field_name, field_type ):

        field_names = [ field.name  for field in arcpy.ListFields( feature_class)]
        if field_name not in field_names:
            arcpy.management.AddField(
                feature_class,
                field_name,
                field_type
            )

    def delete_if_exists(self, path):

        if arcpy.Exists(path):
            try:
                arcpy.management.Delete( path )
            except Exception:
                pass
    
class Hitung_Persil_Individual(object):

    def __init__(self):

        self.label = "Hitung Individual"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):

        penilaian = arcpy.Parameter(
            displayName="ID Bidang Penilaian",
            name="penilaian",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )

        penilaian.filter.type = "ValueList"

        return [penilaian]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):

        penilaian = parameters[0]

        try:

            configs = persil.get_config_values()

            dataset_path = configs["project_config"]["dataset_path"]

            persil_path = os.path.join(dataset_path, "Persil_Layer")

            list_tsi = []

            with arcpy.da.SearchCursor(persil_path, ["IdBidang"], "perubahan = 'menyebar'") as rows:

                for row in rows:
                    list_tsi.append(str(row[0]))

            list_tsi.sort()

            penilaian.filter.list = list_tsi

        except Exception:
            pass

        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):

        messages.addMessage("== Proses dimulai ==")

        penilaian = parameters[0].valueAsText
        configs = persil.get_config_values()
        dataset_path = configs["project_config"]["dataset_path"]
        persil_name = "Persil_Layer"

        persil_path = os.path.join(dataset_path, persil_name)
        ada_seleksi = len(arcpy.Describe(persil_name).FIDSet)

        if ada_seleksi <= 0:
            messages.addErrorMessage( "== Tidak ada data pembanding dipilih ==")
            raise arcpy.ExecuteError

        pembanding_layers = self.get_selected_pembanding(
            persil_name,
            persil_path,
            messages
        )

        objek_layer = "objek"
        self.delete_if_exists(objek_layer)

        arcpy.management.MakeFeatureLayer(
            persil_path,
            objek_layer,
            f"IdBidang = {penilaian}"
        )

        objek = self.get_data_row(objek_layer)

        pembanding1 = self.get_data_row(pembanding_layers[0])
        pembanding2 = self.get_data_row(pembanding_layers[1])
        pembanding3 = self.get_data_row(pembanding_layers[2])

        pembanding_list = [
            pembanding1,
            pembanding2,
            pembanding3
        ]

        for i, pembanding in enumerate(pembanding_list, start=1):

            if objek["s_zonasi"] != pembanding["s_zonasi"]:

                messages.addErrorMessage(
                    f"== Pembanding {i} memiliki zonasi berbeda =="
                )

                raise arcpy.ExecuteError

        hasil1 = self.calculate_penyesuaian(objek, pembanding1)
        hasil2 = self.calculate_penyesuaian(objek, pembanding2)
        hasil3 = self.calculate_penyesuaian(objek, pembanding3)

        hasil_list = [
            hasil1,
            hasil2,
            hasil3
        ]

        for i, hasil in enumerate(hasil_list, start=1):

            if hasil["persentase"] > 10:

                messages.addErrorMessage(
                    f"== Pembanding {i} memiliki persentase lebih dari 10% =="
                )

                raise arcpy.ExecuteError

        total_nol = (
            hasil1["nilai_nol"]
            + hasil2["nilai_nol"]
            + hasil3["nilai_nol"]
        )

        bobot1 = (hasil1["nilai_nol"] / total_nol) * 100
        bobot2 = (hasil2["nilai_nol"] / total_nol) * 100
        bobot3 = (hasil3["nilai_nol"] / total_nol) * 100

        nilai_akhir = (
            (hasil1["nilai"] * bobot1 / 100)
            + (hasil2["nilai"] * bobot2 / 100)
            + (hasil3["nilai"] * bobot3 / 100)
        )

        self.add_field_if_not_exists(
            persil_path,
            "data_pembanding",
            "TEXT"
        )

        list_data_pembanding = (
            f"{pembanding1['OBJECTID']} ; "
            f"{pembanding2['OBJECTID']} ; "
            f"{pembanding3['OBJECTID']}"
        )

        with arcpy.da.UpdateCursor(
            persil_path,
            [
                "IdBidang",
                "data_pembanding",
                "NILAIBD_LAMA",
                "perubahan"
            ],
            f"IdBidang = {penilaian}"
        ) as rows:

            for row in rows:

                row[1] = list_data_pembanding
                row[2] = nilai_akhir
                row[3] = "individual"

                rows.updateRow(row)

        messages.addMessage(
            f"Data yang akan dinilai memiliki zonasi: {objek['zonasi']}"
        )

        for i, pembanding in enumerate(pembanding_list, start=1):

            hasil = hasil_list[i - 1]

            messages.addMessage(
                (
                    f"Pembanding {i}: "
                    f"zonasi={pembanding['zonasi']} | "
                    f"persentase={hasil['persentase']}% | "
                    f"OBJECTID={pembanding['OBJECTID']}"
                )
            )

        arcpy.management.CalculateField(
            persil_path,
            "IdBidang",
            "!OBJECTID!",
            "PYTHON3"
        )

        self.delete_if_exists(objek_layer)

        for layer in pembanding_layers:
            self.delete_if_exists(layer)

        messages.addMessage("== Proses selesai ==")

        return

    def delete_if_exists(self, path):

        if arcpy.Exists(path):

            try:
                arcpy.management.Delete(path)

            except Exception:
                pass

    def add_field_if_not_exists(self, feature_class, field_name, field_type):

        field_names = [
            field.name
            for field in arcpy.ListFields(feature_class)
        ]

        if field_name not in field_names:

            arcpy.management.AddField(
                feature_class,
                field_name,
                field_type
            )

    def get_selected_pembanding(self, persil_layer, persil_path, messages):

        list_pembanding = []

        with arcpy.da.SearchCursor(
            persil_layer,
            ["IdBidang", "OBJECTID"]
        ) as rows:

            for row in rows:

                list_pembanding.append({
                    "IdBidang": row[0],
                    "OBJECTID": row[1]
                })

        if len(list_pembanding) != 3:

            messages.addErrorMessage(
                "== Jumlah data pembanding harus tepat 3 =="
            )

            raise arcpy.ExecuteError

        pembanding_layers = []

        for i, item in enumerate(list_pembanding, start=1):

            layer_name = f"pembanding_{i}"

            self.delete_if_exists(layer_name)

            where_clause = f"OBJECTID = {item['OBJECTID']}"

            arcpy.management.MakeFeatureLayer(
                persil_path,
                layer_name,
                where_clause
            )

            pembanding_layers.append(layer_name)

        return pembanding_layers

    def get_data_row(self, layer_name):

        fields = [
            "OBJECTID",
            "LUASM2",
            "LBRDPN",
            "s_bentuk",
            "s_letak",
            "s_kls_jln",
            "ls_tnh_i",
            "lb_dpn_i",
            "s_zonasi",
            "ZONASI",
            "NILAIBD_LAMA"
        ]

        with arcpy.da.SearchCursor(layer_name, fields) as rows:

            for row in rows:

                return {
                    "OBJECTID": row[0],
                    "ls_tnh": row[1],
                    "lb_dpn": row[2],
                    "s_bentuk": row[3],
                    "s_letak": row[4],
                    "s_kls_jln": row[5],
                    "ls_tnh_i": row[6],
                    "lb_dpn_i": row[7],
                    "s_zonasi": row[8],
                    "zonasi": row[9],
                    "nilai": row[10]
                }

        return None

    def calculate_penyesuaian(self, objek, pembanding):

        ls_tnh = (
            (objek["ls_tnh_i"] - pembanding["ls_tnh_i"])
            * 0.5
        )

        lb_dpn = (
            (objek["lb_dpn_i"] - pembanding["lb_dpn_i"])
            * 1.5
        )

        bentuk = (
            (objek["s_bentuk"] - pembanding["s_bentuk"])
            * 1.5
        )

        letak = (
            (objek["s_letak"] - pembanding["s_letak"])
            * 1
        )

        kls_jln = (
            (objek["s_kls_jln"] - pembanding["s_kls_jln"])
            * 3
        )

        persentase = (
            ls_tnh
            + lb_dpn
            + bentuk
            + letak
            + kls_jln
        )

        nilai = (
            pembanding["nilai"]
            * (100 + persentase)
        ) / 100

        komponen = [
            ls_tnh,
            lb_dpn,
            bentuk,
            letak,
            kls_jln
        ]

        nilai_nol = komponen.count(0)

        return {
            "persentase": persentase,
            "nilai": nilai,
            "nilai_nol": nilai_nol
        }
    
class Reset_Persil_Individual(object):

    def __init__(self):

        self.label = "Reset Persil Individual"
        self.description = ""
        self.canRunInBackground = False

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

    def execute(self, parameters, messages):

        messages.addMessage("== Proses dimulai ==")

        configs = persil.get_config_values()

        dataset_path =  configs["project_config"]["dataset_path"]
        

        appdata = os.path.dirname(
            os.path.dirname(
                os.path.realpath(__file__)
            )
        )

        persil_name = "Persil_Layer"

        persil_path = os.path.join(
            dataset_path,
            persil_name
        )

        ada_seleksi = len( arcpy.Describe( persil_name).FIDSet)

        if ada_seleksi <= 0:

            messages.addWarningMessage(
                "== Tidak ada persil dipilih =="
            )

            return

        messages.addMessage(
            "== Reset nilai individual =="
        )

        with arcpy.da.UpdateCursor(
            persil_name,
            [
                "NILAI_LAMA",
                "perubahan"
            ]
        ) as rows:

            for row in rows:

                row[0] = None
                row[1] = "menyebar"

                rows.updateRow(row)

        self.delete_if_exists(persil)

        arcpy.management.MakeFeatureLayer(
            persil_path,
            persil_name
        )

        simbologi_path = os.path.join(
            appdata,
            "Simbologi_PersilIndividual.lyrx"
        )

        if os.path.exists(simbologi_path):

            arcpy.management.ApplySymbologyFromLayer(
                persil_name,
                simbologi_path
            )

        parameters[0].value = persil_name

        messages.addMessage(
            "== Proses selesai =="
        )

        return

    def delete_if_exists(self, path):

        if arcpy.Exists(path):

            try:
                arcpy.management.Delete(path)

            except Exception:
                pass

class Generate_Titik_Indeks(object):

    def __init__(self):

        self.label = "Generate Titik Indeks"
        self.description = ""
        self.canRunInBackground = False

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

    def execute(self, parameters, messages):

        messages.addMessage("== Proses dimulai ==")

        configs = persil.get_config_values()

        dataset_path = (
            configs["project_config"]["dataset_path"]
        )

        appdata = os.path.dirname(
            os.path.dirname(
                os.path.realpath(__file__)
            )
        )

        persil_path = os.path.join(
            dataset_path,
            "Persil_Layer"
        )

        sampel_path = os.path.join(
            dataset_path,
            "Titik_Sampel"
        )

        indeks_path = os.path.join(
            dataset_path,
            "Titik_Indeks"
        )

        identity_output = os.path.join(
            dataset_path,
            "temp_identity"
        )

        self.delete_if_exists(identity_output)
        self.delete_if_exists(indeks_path)
        self.delete_if_exists("Titik_Indeks")
        self.delete_if_exists("Titik_Sampel_Update")

        messages.addMessage("== Proses identity ==")

        arcpy.analysis.Identity(
            sampel_path,
            persil_path,
            identity_output
        )

        self.add_field_if_not_exists(
            identity_output,
            "indeks",
            "DOUBLE"
        )

        messages.addMessage("== Hitung indeks ==")

        code_block = """
def doSomething(a, b):

    if a and b:
        return round(100 * (a / b), 2)

    return None
"""

        arcpy.management.CalculateField(
            identity_output,
            "indeks",
            "doSomething(!nilai!, !NILAIBD_LAMA!)",
            "PYTHON3",
            code_block
        )

        messages.addMessage("== Sorting indeks ==")

        arcpy.management.Sort(
            identity_output,
            indeks_path,
            [
                ["s_zonasi", "ASCENDING"],
                ["indeks", "ASCENDING"]
            ]
        )

        messages.addMessage("== Hapus data cluster ==")

        with arcpy.da.UpdateCursor(indeks_path, ["kelompok_perubahan"]) as cursor:
            for row in cursor:
                if row[0]:
                    cursor.deleteRow()

        delete_fields = [
            "FID_Titik_Sampel",
            "FID_Persil_Layer",
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
            for field in arcpy.ListFields(indeks_path)
        ]

        valid_delete_fields = [
            field
            for field in delete_fields
            if field in existing_fields
        ]

        if valid_delete_fields:

            messages.addMessage(
                "== Hapus field tidak digunakan =="
            )

            arcpy.management.DeleteField(
                indeks_path,
                valid_delete_fields
            )

        arcpy.management.MakeFeatureLayer(
            indeks_path,
            "Titik_Indeks"
        )

        arcpy.management.MakeFeatureLayer(
            sampel_path,
            "Titik_Sampel"
        )

        simbologi_path = os.path.join(
            appdata,
            "Simbologi_Titik_Indeks.lyrx"
        )

        if os.path.exists(simbologi_path):

            arcpy.management.ApplySymbologyFromLayer(
                "Titik_Indeks",
                simbologi_path
            )

        parameters[0].value = "Titik_Indeks"
        parameters[1].value = "Titik_Sampel"

        self.delete_if_exists(identity_output)

        messages.addMessage("== Proses selesai ==")

        return

    def delete_if_exists(self, path):

        if arcpy.Exists(path):

            try:
                arcpy.management.Delete(path)

            except Exception:
                pass

    def add_field_if_not_exists(self, feature_class, field_name, field_type):

        field_names = [
            field.name
            for field in arcpy.ListFields(feature_class)
        ]

        if field_name not in field_names:

            arcpy.management.AddField(
                feature_class,
                field_name,
                field_type
            )

class Deteksi_Outlier_Indeks(object):

    def __init__(self):

        self.label = "Deteksi Outlier Indeks"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):

        output_indeks = arcpy.Parameter(
            displayName="Output Titik Indeks",
            name="output_indeks",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [output_indeks]

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

        appdata = os.path.dirname(
            os.path.dirname(
                os.path.realpath(__file__)
            )
        )

        titik_indeks = os.path.join(
            dataset_path,
            "Titik_Indeks"
        )

        if not arcpy.Exists(titik_indeks):

            messages.addErrorMessage(
                "Feature class Titik_Indeks tidak ditemukan"
            )

            raise arcpy.ExecuteError

        self.add_field_if_not_exists(
            titik_indeks,
            "outlier",
            "TEXT"
        )

        arcpy.management.CalculateField(
            titik_indeks,
            "outlier",
            "None",
            "PYTHON3"
        )

        messages.addMessage("== Membaca zonasi ==")

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

                    zonasi_dict[
                        int(s_zonasi)
                    ] = nama_zonasi

        list_zonasi = sorted(
            zonasi_dict.keys()
        )

        for s_zonasi in list_zonasi:

            nama_zonasi = zonasi_dict[s_zonasi]

            messages.addMessage(
                f"== Proses zonasi: {nama_zonasi} =="
            )

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
                        data.append(row[0])

            data_sorted = sorted(data)

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
                    f"{round(lower_bound, 2)} | "
                    f"Upper Bound: "
                    f"{round(upper_bound, 2)}"
                )
            )

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

                        row[1] = "Indeks Outlier"

                    else:
                        row[1] = None

                    rows.updateRow(row)

        if arcpy.Exists("Titik_Indeks"):

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

        simbologi_path = os.path.join(
            appdata,
            "Simbologi_Titik_Indeks_Outlier.lyrx"
        )

        if os.path.exists(simbologi_path):

            arcpy.management.ApplySymbologyFromLayer(
                "Titik_Indeks",
                simbologi_path
            )

        parameters[0].value = "Titik_Indeks"

        messages.addMessage("== Proses selesai ==")

        return

    def add_field_if_not_exists(self, feature_class, field_name, field_type):

        fields = [
            field.name
            for field in arcpy.ListFields(feature_class)
        ]

        if field_name not in fields:

            arcpy.management.AddField(
                feature_class,
                field_name,
                field_type
            )

    def delete_field_if_exists(self, feature_class, field_name):

        fields = [
            field.name
            for field in arcpy.ListFields(feature_class)
        ]

        if field_name in fields:

            arcpy.management.DeleteField(
                feature_class,
                field_name
            )

    def calculate_boxplot_values(self, data_list):

        import numpy

        q1 = numpy.percentile(data_list, 25)
        median = numpy.percentile(data_list, 50)
        q3 = numpy.percentile(data_list, 75)

        iqr = q3 - q1

        lower_bound = q1 - (1.5 * iqr)
        upper_bound = q3 + (1.5 * iqr)

        return (
            q1,
            median,
            q3,
            lower_bound,
            upper_bound
        )


# Mengelompokkan

class Set_Cluster_Persil(object):

    def __init__(self):

        self.label = "Set Cluster Persil"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):

        cluster_update = arcpy.Parameter(
            displayName="Nilai Cluster",
            name="cluster_update",
            datatype="GPShort",
            parameterType="Required",
            direction="Input"
        )

        return [cluster_update]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):

        messages.addMessage("== Proses dimulai ==")

        cluster_update = parameters[0].value

        persil_nama = "Persil_Layer"

        if not arcpy.Exists(persil_nama):

            messages.addErrorMessage(
                "Feature layer Persil_nama tidak ditemukan"
            )

            raise arcpy.ExecuteError

        ada_seleksi = len(
            arcpy.Describe(
                persil_nama
            ).FIDSet
        )

        if ada_seleksi <= 0:

            messages.addWarningMessage(
                "== Tidak ada persil dipilih =="
            )

            return

        self.add_field_if_not_exists(
            persil_nama,
            "kelompok_perubahan",
            "SHORT"
        )

        self.add_field_if_not_exists(
            persil_nama,
            "status_per",
            "TEXT"
        )

        self.add_field_if_not_exists(
            persil_nama,
            "perubahan",
            "TEXT"
        )

        messages.addMessage(
            "== Update cluster persil =="
        )

        with arcpy.da.UpdateCursor(
            persil,
            [
                "status_per",
                "kelompok_perubahan",
                "perubahan"
            ]
        ) as rows:

            for row in rows:

                row[0] = "update"
                row[1] = cluster_update
                row[2] = "mengelompok"

                rows.updateRow(row)

        arcpy.management.CalculateField(
            persil,
            "kelompok_perubahan",
            cluster_update,
            "PYTHON3"
        )

        messages.addMessage(
            "== Proses selesai =="
        )

        return

    def add_field_if_not_exists(self, feature_class, field_name, field_type):

        field_names = [
            field.name
            for field in arcpy.ListFields(feature_class)
        ]

        if field_name not in field_names:

            arcpy.management.AddField(
                feature_class,
                field_name,
                field_type
            )

class Periksa_Titik_Sampel_Kelompok_Perubahan(object):

    def __init__(self):

        self.label = "Periksa Titik Sampel Cluster"
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

    def execute(self, parameters, messages):

        messages.addMessage("== Proses dimulai ==")

        configs = persil.get_config_values()

        dataset_path = configs["project_config"]["dataset_path"]
        

        persil_path = os.path.join(
            dataset_path,
            "Persil_Layer"
        )

        sampel_path = os.path.join(
            dataset_path,
            "Titik_Sampel"
        )

        identity_path = os.path.join(
            dataset_path,
            "temp_identity_cluster"
        )

        if not arcpy.Exists(persil_path):

            messages.addErrorMessage(
                "Feature class Persil_Layer tidak ditemukan"
            )

            raise arcpy.ExecuteError

        if not arcpy.Exists(sampel_path):

            messages.addErrorMessage(
                "Feature class Titik_Sampel_Update tidak ditemukan"
            )

            raise arcpy.ExecuteError

        self.delete_if_exists(identity_path)

        messages.addMessage("== Membuat identity ==")

        arcpy.analysis.Identity(
            sampel_path,
            persil_path,
            identity_path
        )

        list_cluster = []

        with arcpy.da.SearchCursor(
            identity_path,
            ["kelompok_perubahan"],
            "perubahan = 'mengelompok'"
        ) as rows:

            for row in rows:

                if row[0] is not None:
                    list_cluster.append(row[0])

        unique_cluster = sorted(
            list(set(list_cluster))
        )

        messages.addMessage(
            "== Periksa jumlah titik sampel =="
        )

        for cluster_id in unique_cluster:

            titik_list = []

            where_clause = (
                f"kelompok_perubahan = {cluster_id}"
            )

            with arcpy.da.SearchCursor(
                identity_path,
                ["OBJECTID"],
                where_clause
            ) as rows:

                for row in rows:
                    titik_list.append(row[0])

            jumlah_titik = len(titik_list)

            if jumlah_titik > 3:

                messages.addWarningMessage(
                    (
                        f"Kelompok [{cluster_id}] "
                        "memiliki titik sampel "
                        "lebih dari 3."
                    )
                )

            elif jumlah_titik < 3:

                messages.addWarningMessage(
                    (
                        f"Kelompok [{cluster_id}] "
                        "memiliki titik sampel "
                        "kurang dari 3."
                    )
                )

            else:

                messages.addMessage(
                    (
                        f"Kelompok [{cluster_id}] "
                        "memiliki 3 titik sampel."
                    )
                )

        self.delete_if_exists(identity_path)

        messages.addMessage(
            "== Proses selesai =="
        )

        return

    def delete_if_exists(self, path):

        if arcpy.Exists(path):

            try:
                arcpy.management.Delete(path)

            except Exception:
                pass
            
class Hitung_Statistik_Cluster(object):

    def __init__(self):

        self.label = "Hitung Statistik Cluster"
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

    def execute(self, parameters, messages):

        messages.addMessage(
            "== Proses dimulai =="
        )


        configs = persil.get_config_values()

        dataset_path = configs["project_config"]["dataset_path"]

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
            "Persil_Layer"
        )

        sampel_path = os.path.join(
            dataset_path,
            "Titik_Sampel"
        )

        identity_path = os.path.join(
            dataset_path,
            "temp_identity_cluster"
        )

        temp_intersect = os.path.join(
            dataset_path,
            "temp_intersect_cluster"
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
            sampel_path
        ):

            messages.addErrorMessage(
                (
                    "Feature class "
                    "Titik_Sampel "
                    "tidak ditemukan"
                )
            )

            raise arcpy.ExecuteError

        # =================================================
        # CLEAN TEMP
        # =================================================

        self.delete_if_exists(
            identity_path
        )

        self.delete_if_exists(
            temp_intersect
        )

        # =================================================
        # FIELD
        # =================================================

        delete_fields = [
            "MEAN_nilai",
            "STD_nilai",
            "PTDDEV"
        ]

        existing_fields = [
            field.name
            for field in arcpy.ListFields(
                persil_path
            )
        ]

        valid_delete = [
            field
            for field in delete_fields
            if field in existing_fields
        ]

        if valid_delete:

            arcpy.management.DeleteField(
                persil_path,
                valid_delete
            )

        self.add_field_if_not_exists(
            persil_path,
            "MEAN_nilai",
            "DOUBLE"
        )

        self.add_field_if_not_exists(
            persil_path,
            "STD_nilai",
            "DOUBLE"
        )

        self.add_field_if_not_exists(
            persil_path,
            "PTDDEV",
            "DOUBLE"
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
            identity_path
        )

        # =================================================
        # GET CLUSTER
        # =================================================

        list_cluster = []

        with arcpy.da.SearchCursor(
            identity_path,
            ["kelompok_perubahan"],
            "perubahan = 'mengelompok'"
        ) as rows:

            for row in rows:

                if row[0] not in (
                    None,
                    0
                ):

                    list_cluster.append(
                        row[0]
                    )

        unique_cluster = sorted(
            list(
                set(list_cluster)
            )
        )

        # =================================================
        # INTERSECT
        # =================================================

        arcpy.analysis.Intersect(
            [
                persil_path,
                sampel_path
            ],
            temp_intersect,
            "ALL"
        )

        # =================================================
        # LOOP CLUSTER
        # =================================================

        counter = 0

        for cluster_id in unique_cluster:

            counter += 1

            messages.addMessage(
                (
                    f"== Proses Kelompok Perubahan"
                    f"{cluster_id} =="
                )
            )

            cluster_layer = (
                f"cKelompok Perubahan_{counter}"
            )

            dissolve_output = os.path.join(
                dataset_path,
                f"dissolve_{counter}"
            )

            self.delete_if_exists(
                cluster_layer
            )

            self.delete_if_exists(
                dissolve_output
            )

            # =============================================
            # MAKE LAYER
            # =============================================

            arcpy.management.MakeFeatureLayer(
                identity_path,
                cluster_layer,
                f"kelompok_perubahan = {cluster_id}"
            )

            # =============================================
            # DISSOLVE
            # =============================================

            statistic_fields = [
                ["nilai", "SUM"],
                ["nilai", "MEAN"],
                ["nilai", "MIN"],
                ["nilai", "MAX"],
                ["nilai", "STD"],
                ["nilai", "COUNT"],
                ["nilai", "RANGE"]
            ]

            arcpy.management.Dissolve(
                cluster_layer,
                dissolve_output,
                ["kelompok_perubahan"],
                statistic_fields,
                "MULTI_PART",
                "DISSOLVE_LINES"
            )

            # =============================================
            # DELETE INVALID ROW
            # =============================================

            with arcpy.da.UpdateCursor(
                dissolve_output,
                ["kelompok_perubahan"]
            ) as cursor:

                for row in cursor:

                    if row[0] in (
                        None,
                        0
                    ):

                        cursor.deleteRow()

            # =============================================
            # UPDATE PREDICTED
            # =============================================

            where_intersect = (
                f"kelompok_perubahan = {cluster_id}"
            )

            with arcpy.da.SearchCursor(
                temp_intersect,
                [
                    "FID_Persil_Layer",
                    "nilai"
                ],
                where_intersect
            ) as rows:

                for row in rows:

                    fid_persil = row[0]
                    nilai = row[1]

                    where_update = (
                        f"OBJECTID = {fid_persil}"
                    )

                    with arcpy.da.UpdateCursor(
                        persil_path,
                        ["NILAIBD"],
                        where_update
                    ) as update_rows:

                        for update_row in update_rows:

                            update_row[0] = nilai

                            update_rows.updateRow(
                                update_row
                            )

            # =============================================
            # GET STATISTIC
            # =============================================

            mean_nilai = None
            std_nilai = None

            with arcpy.da.SearchCursor(
                dissolve_output,
                [
                    "MEAN_nilai",
                    "STD_nilai",
                    "kelompok_perubahan"
                ]
            ) as rows:

                for row in rows:

                    mean_nilai = row[0]
                    std_nilai = row[1]

            # =============================================
            # UPDATE STATISTIC
            # =============================================

            if mean_nilai is not None:

                with arcpy.da.UpdateCursor(
                    persil_path,
                    [
                        "kelompok_perubahan",
                        "NILAIBD",
                        "MEAN_nilai",
                        "STD_nilai"
                    ],
                    f"kelompok_perubahan = {cluster_id}"
                ) as rows:

                    for row in rows:

                        if row[1] is not None:

                            row[2] = mean_nilai
                            row[3] = std_nilai

                            rows.updateRow(
                                row
                            )

            # =============================================
            # CLEAN TEMP
            # =============================================

            self.delete_if_exists(
                cluster_layer
            )

            self.delete_if_exists(
                dissolve_output
            )

        # =================================================
        # CALCULATE PTDDEV
        # =================================================

        messages.addMessage(
            "== Hitung PTDDEV =="
        )

        codeblock = """
def doSomething(a, b):

    if a and b:

        return round(
            (a / b) * 100,
            2
        )

    return None
"""

        arcpy.management.CalculateField(
            persil_path,
            "PTDDEV",
            "doSomething(!STD_nilai!, !MEAN_nilai!)",
            "PYTHON3",
            codeblock
        )

        # =================================================
        # RESET PREDICTED
        # =================================================

        messages.addMessage(
            "== Reset predicted non-individual =="
        )

        with arcpy.da.UpdateCursor(
            persil_path,
            [
                "perubahan",
                "NILAIBD"
            ]
        ) as cursor:

            for row in cursor:

                if row[0] != "individual":

                    row[1] = None

                    cursor.updateRow(
                        row
                    )

        # =================================================
        # REFRESH LAYER
        # =================================================

        if arcpy.Exists(
            "Persil_Layer"
        ):

            try:

                arcpy.management.Delete(
                    "Persil_Layer"
                )

            except Exception:

                pass

        arcpy.management.MakeFeatureLayer(
            persil_path,
            "Persil_Layer"
        )

        # =================================================
        # APPLY SYMBOLOGY
        # =================================================

        simbologi_path = os.path.join(
            appdata,
            "Simbologi_Outlier_Persil_Baru.lyrx"
        )

        if os.path.exists(
            simbologi_path
        ):

            arcpy.management.ApplySymbologyFromLayer(
                "Persil_Layer",
                simbologi_path
            )

        # =================================================
        # OUTPUT
        # =================================================

        parameters[0].value = (
            "Persil_Layer"
        )

        # =================================================
        # SHOW SAMPLE
        # =================================================

        try:

            aprx = arcpy.mp.ArcGISProject(
                "CURRENT"
            )

            current_map = (
                aprx.activeMap
            )

            for layer in current_map.listLayers():

                if (
                    layer.name
                    == "Titik_Sampel"
                ):

                    layer.visible = True

        except Exception:

            pass

        # =================================================
        # CLEAN TEMP
        # =================================================

        self.delete_if_exists(
            identity_path
        )

        self.delete_if_exists(
            temp_intersect
        )

        # =================================================
        # FINISH
        # =================================================

        messages.addMessage( "== Proses selesai ==")

        return

class Hitung_Individual_Cluster(object):

    def __init__(self):

        self.label = "Hitung Individual Cluster"
        self.description = ""
        self.canRunInBackground = False

    # =====================================================
    # PARAMETER
    # =====================================================

    def getParameterInfo(self):

        configs = persil.get_config_values()

        dataset_path = (
            configs["project_config"]["dataset_path"]
        )

        persil_path = os.path.join(
            dataset_path,
            "Persil_Baru"
        )

        cluster_list = []

        if arcpy.Exists(persil_path):

            with arcpy.da.SearchCursor(
                persil_path,
                ["clusternew"],
                "perubahan = 'mengelompok'"
            ) as rows:

                for row in rows:

                    if row[0] not in (
                        None,
                        0
                    ):

                        cluster_list.append(
                            str(row[0])
                        )

        cluster_list = sorted(
            list(set(cluster_list))
        )

        param_cluster = arcpy.Parameter(
            displayName="Nomor Cluster",
            name="cluster",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )

        param_cluster.filter.type = (
            "ValueList"
        )

        param_cluster.filter.list = (
            cluster_list
        )

        output_layer = arcpy.Parameter(
            displayName="Output Persil",
            name="output_persil",
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

    def get_row_value(
        self,
        feature_class,
        where_clause
    ):

        fields = [
            "ls_tnh_i",
            "lb_dpn_i",
            "s_bentuk",
            "s_letak",
            "s_kls_jln",
            "ls_tnh",
            "nilai"
        ]

        with arcpy.da.SearchCursor(
            feature_class,
            fields,
            where_clause
        ) as rows:

            for row in rows:

                return {
                    "ls_tnh_i": row[0],
                    "lb_dpn_i": row[1],
                    "s_bentuk": row[2],
                    "s_letak": row[3],
                    "s_kls_jln": row[4],
                    "ls_tnh": row[5],
                    "nilai": row[6]
                }

        return None

    def calculate_adjustment(
        self,
        objek,
        pembanding
    ):

        ls_tnh = (
            (
                objek["ls_tnh_i"]
                - pembanding["ls_tnh_i"]
            ) * 0.5
        )

        lb_dpn = (
            (
                objek["lb_dpn_i"]
                - pembanding["lb_dpn_i"]
            ) * 1.5
        )

        bentuk = (
            (
                objek["s_bentuk"]
                - pembanding["s_bentuk"]
            ) * 1.5
        )

        letak = (
            (
                objek["s_letak"]
                - pembanding["s_letak"]
            ) * 1
        )

        kelas = (
            (
                objek["s_kls_jln"]
                - pembanding["s_kls_jln"]
            ) * 3
        )

        persentase = (
            ls_tnh
            + lb_dpn
            + bentuk
            + letak
            + kelas
        )

        nilai = (
            pembanding["nilai"]
            * (100 + persentase)
        ) / 100

        skor = [
            ls_tnh,
            lb_dpn,
            bentuk,
            letak,
            kelas
        ]

        nilai_nol = skor.count(0)

        return nilai, nilai_nol

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

        cluster = int(
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

        temp_intersect = os.path.join(
            dataset_path,
            "temp_intersect"
        )

        sampel_join = os.path.join(
            dataset_path,
            "Titik_Sampel_Join"
        )

        # =================================================
        # CLEAN TEMP
        # =================================================

        self.delete_if_exists(
            temp_intersect
        )

        self.delete_if_exists(
            sampel_join
        )

        # =================================================
        # INTERSECT
        # =================================================

        messages.addMessage(
            "== Membuat intersect =="
        )

        arcpy.analysis.Intersect(
            [
                persil_path,
                sampel_path
            ],
            temp_intersect,
            "ALL"
        )

        # =================================================
        # GET SAMPEL PEMBANDING
        # =================================================

        arcpy.management.MakeFeatureLayer(
            temp_intersect,
            "temp_layer",
            f"clusternew = {cluster}"
        )

        arcpy.management.CopyFeatures(
            "temp_layer",
            sampel_join
        )

        pembanding_ids = []

        with arcpy.da.SearchCursor(
            sampel_join,
            ["IdBidang"]
        ) as rows:

            for row in rows:

                pembanding_ids.append(
                    row[0]
                )

        pembanding_ids = list(
            dict.fromkeys(
                pembanding_ids
            )
        )

        # =================================================
        # VALIDASI PEMBANDING
        # =================================================

        if len(
            pembanding_ids
        ) < 3:

            messages.addErrorMessage(
                (
                    "Data pembanding "
                    "kurang dari 3"
                )
            )

            raise arcpy.ExecuteError

        if len(
            pembanding_ids
        ) > 3:

            messages.addErrorMessage(
                (
                    "Data pembanding "
                    "lebih dari 3"
                )
            )

            raise arcpy.ExecuteError

        # =================================================
        # GET DATA PEMBANDING
        # =================================================

        pembanding_data = []

        for pembanding_id in pembanding_ids:

            data = self.get_row_value(
                sampel_join,
                f"IdBidang = {pembanding_id}"
            )

            pembanding_data.append(
                data
            )

        # =================================================
        # GET PENILAIAN
        # =================================================

        penilaian_ids = []

        with arcpy.da.SearchCursor(
            persil_path,
            ["IdBidang"],
            (
                "perubahan = "
                "'mengelompok' "
                f"AND clusternew = {cluster}"
            )
        ) as rows:

            for row in rows:

                penilaian_ids.append(
                    row[0]
                )

        penilaian_ids = [
            value
            for value in penilaian_ids
            if value not in pembanding_ids
        ]

        # =================================================
        # UPDATE SAMPEL
        # =================================================

        with arcpy.da.SearchCursor(
            sampel_join,
            [
                "FID_Persil_Baru",
                "nilai"
            ]
        ) as rows:

            for row in rows:

                fid = row[0]
                nilai = row[1]

                with arcpy.da.UpdateCursor(
                    persil_path,
                    [
                        "PREDICTED",
                        "perubahan"
                    ],
                    f"OBJECTID = {fid}"
                ) as update_rows:

                    for update_row in update_rows:

                        update_row[0] = nilai
                        update_row[1] = (
                            "individual"
                        )

                        update_rows.updateRow(
                            update_row
                        )

        # =================================================
        # LOOP PENILAIAN
        # =================================================

        for bidang_id in penilaian_ids:

            objek = self.get_row_value(
                persil_path,
                f"IdBidang = {bidang_id}"
            )

            hasil = []

            bobot = []

            for pembanding in pembanding_data:

                nilai, nilai_nol = (
                    self.calculate_adjustment(
                        objek,
                        pembanding
                    )
                )

                hasil.append(
                    nilai
                )

                bobot.append(
                    nilai_nol
                )

            total_bobot = sum(
                bobot
            )

            if total_bobot == 0:

                continue

            nilai_pasar = 0

            for i in range(3):

                persen = (
                    bobot[i]
                    / total_bobot
                ) * 100

                nilai_pasar += (
                    hasil[i]
                    * persen
                ) / 100

            nilai_baru = (
                nilai_pasar
            )

            # =============================================
            # UPDATE
            # =============================================

            with arcpy.da.UpdateCursor(
                persil_path,
                [
                    "PREDICTED",
                    "perubahan"
                ],
                f"IdBidang = {bidang_id}"
            ) as rows:

                for row in rows:

                    row[0] = (
                        nilai_baru
                    )

                    row[1] = (
                        "individual"
                    )

                    rows.updateRow(
                        row
                    )

            messages.addMessage(
                (
                    f"IdBidang "
                    f"{bidang_id} : "
                    f"{round(nilai_baru,2)}"
                )
            )

        # =================================================
        # REFRESH LAYER
        # =================================================

        if arcpy.Exists(
            "Persil_Baru"
        ):

            self.delete_if_exists(
                "Persil_Baru"
            )

        arcpy.management.MakeFeatureLayer(
            persil_path,
            "Persil_Baru"
        )

        # =================================================
        # SYMBOLOGY
        # =================================================

        simbologi_path = os.path.join(
            appdata,
            "Simbologi_PersilIndividualCluster.lyrx"
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

        parameters[1].value = (
            "Persil_Baru"
        )

        # =================================================
        # CLEAN TEMP
        # =================================================

        self.delete_if_exists(
            temp_intersect
        )

        self.delete_if_exists(
            sampel_join
        )

        self.delete_if_exists(
            "temp_layer"
        )

        # =================================================
        # FINISH
        # =================================================

        messages.addMessage(
            "== Proses selesai =="
        )

        return

class Pengembalian_Cluster(object):

    def __init__(self):

        self.label = (
            "Pengembalian Persil "
            "Cluster Individual"
        )

        self.description = ""
        self.canRunInBackground = False

    # =====================================================
    # PARAMETER
    # =====================================================

    def getParameterInfo(self):

        import arcpy
        import os

        cluster_list = []

        try:

            configs = (
                persil.get_config_values()
            )

            dataset_path = (
                configs["project_config"]["dataset_path"]
            )

            persil_path = os.path.join(
                dataset_path,
                "Persil_Baru"
            )

            if arcpy.Exists(
                persil_path
            ):

                with arcpy.da.SearchCursor(
                    persil_path,
                    ["clusternew"],
                    "clusternew IS NOT NULL"
                ) as rows:

                    for row in rows:

                        if row[0] not in (
                            None,
                            0
                        ):

                            cluster_list.append(
                                str(row[0])
                            )

        except Exception:

            pass

        cluster_list = sorted(
            list(set(cluster_list))
        )

        # =================================================
        # PARAMETER CLUSTER
        # =================================================

        param_cluster = arcpy.Parameter(
            displayName="Nomor Cluster",
            name="cluster",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )

        param_cluster.filter.type = (
            "ValueList"
        )

        param_cluster.filter.list = (
            cluster_list
        )

        # =================================================
        # OUTPUT
        # =================================================

        output_layer = arcpy.Parameter(
            displayName="Output Persil",
            name="output_persil",
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

        cluster = int(
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

        # =================================================
        # GET PENILAIAN
        # =================================================

        penilaian_ids = []

        where_clause = (
            "perubahan = 'individual' "
            f"AND clusternew = {cluster}"
        )

        with arcpy.da.SearchCursor(
            persil_path,
            ["IdBidang"],
            where_clause
        ) as rows:

            for row in rows:

                penilaian_ids.append(
                    row[0]
                )

        # =================================================
        # VALIDASI DATA
        # =================================================

        if not penilaian_ids:

            messages.addWarningMessage(
                (
                    f"Tidak ada persil "
                    f"individual pada "
                    f"cluster {cluster}"
                )
            )

            return

        # =================================================
        # UPDATE DATA
        # =================================================

        messages.addMessage(
            (
                f"== Pengembalian "
                f"cluster {cluster} =="
            )
        )

        for bidang_id in penilaian_ids:

            with arcpy.da.UpdateCursor(
                persil_path,
                [
                    "PREDICTED",
                    "perubahan"
                ],
                f"IdBidang = {bidang_id}"
            ) as rows:

                for row in rows:

                    row[0] = None
                    row[1] = "mengelompok"

                    rows.updateRow(
                        row
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
        # SYMBOLOGY
        # =================================================

        simbologi_path = os.path.join(
            appdata,
            "Simbologi_PersilIndividualCluster.lyrx"
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

        parameters[1].value = (
            "Persil_Baru"
        )

        # =================================================
        # FINISH
        # =================================================

        messages.addMessage(
            "== Proses selesai =="
        )

        return