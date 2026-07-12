import sys
import arcpy, os, math
import statistics

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
                      Rekomendasi_Pembanding,
                      Hitung_Persil_Individual,
                      Reset_Persil_Individual,
                      Generate_Titik_Indeks,
                      Deteksi_Outlier_Indeks,
                      Set_Cluster_Persil,
                      Periksa_Titik_Sampel_Kelompok_Perubahan,
                      Mencari_Nilai_Outlier,
                      Hitung_Individual_Cluster,
                      Pengembalian_Cluster,
                      Hitung_Persil_Individual_Otomatis,
                      Simpan_Sebagai_Perubahan_Menyebar,
                      Hitung_Statistik_Kelompok_Perubahan,
                      ]


class Persiapan_Persil_Individual(object):

    def __init__(self):
        self.label = "Persiapan Persil Individual"
        self.description = "Mempersiapkan layer persil dengan perlindungan data (aman dijalankan berulang) dan fitur filter data kosong."
        self.canRunInBackground = False

    def getParameterInfo(self):

        output_persil = arcpy.Parameter(
            displayName="Output Persil",
            name="output_persil",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        cek_kosong = arcpy.Parameter(
            displayName="Hanya proses persil yang ls_tnh_i atau lb_dpn_i masih kosong / 0",
            name="cek_kosong",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )
        cek_kosong.value = False

        return [output_persil, cek_kosong]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):

        messages.addMessage("== Proses dimulai ==")
        
        # Mengambil parameter checkbox
        hanya_yang_kosong = parameters[1].value 

        configs = persil.get_config_values()

        dataset_path = configs["project_config"]["dataset_path"]
        persil_nama = "Persil_Layer"
        persil_path = os.path.join(dataset_path, persil_nama)

        # 1. Pastikan semua field sudah tersedia sebelum Cursor dimulai
        self.add_field_if_not_exists(persil_path, "perubahan", "TEXT")
        self.add_field_if_not_exists(persil_path, "lb_dpn_i", "SHORT")
        self.add_field_if_not_exists(persil_path, "ls_tnh_i", "SHORT")
        self.add_field_if_not_exists(persil_path, "NILAIBD_LAMA", "LONG")

        messages.addMessage("== Memproses klasifikasi, perubahan, dan pembaruan nilai ==")

        fields = [
            "status_per",          # 0
            "kelompok_perubahan",  # 1
            "perubahan",           # 2
            "LUASM2",              # 3
            "LBRDPN",              # 4
            "ls_tnh_i",            # 5
            "lb_dpn_i",            # 6
            "NILAIBD",             # 7
            "NILAIBD_LAMA"         # 8
        ]

        # Menggunakan 1 UpdateCursor untuk seluruh proses (Lebih Cepat & Aman)
        with arcpy.da.UpdateCursor(persil_path, fields) as rows:
            for row in rows:

                # --- FITUR: Lewati jika ls_tnh_i dan lb_dpn_i sudah terisi ---
                is_kosong = (row[5] in [None, 0]) or (row[6] in [None, 0])
                if hanya_yang_kosong and not is_kosong:
                    continue  # Lewati baris ini dan lanjut ke data berikutnya

                # --- A. Update Perubahan ---
                if row[0] == "update":
                    # Perbaikan logika Python yang sebelumnya buggy
                    if row[1] not in [None, 0, ""]: 
                        row[2] = "mengelompok"
                    else:
                        row[2] = "menyebar"

                # --- B. Klasifikasi Luas Tanah ---
                value_ls_tnh = row[3]
                if value_ls_tnh is None:
                    row[5] = 0
                elif value_ls_tnh < 50:
                    row[5] = 1
                elif value_ls_tnh > 1000:
                    row[5] = 2
                elif 200 <= value_ls_tnh <= 1000:
                    row[5] = 3
                elif 50 <= value_ls_tnh < 100:
                    row[5] = 4
                elif 100 <= value_ls_tnh <= 200:
                    row[5] = 5

                # --- C. Klasifikasi Lebar Depan ---
                value_lb_dpn = row[4]
                if value_lb_dpn is None or value_lb_dpn <= 0:
                    row[6] = 0
                elif value_lb_dpn < 6:
                    row[6] = 1
                elif 6 < value_lb_dpn <= 10:
                    row[6] = 2
                elif 10 < value_lb_dpn <= 15:
                    row[6] = 3
                elif value_lb_dpn > 15:
                    row[6] = 4

                # --- D. Update Nilai Prediksi (Aman Dijalankan Berulang) ---
                # Hanya pindahkan NILAIBD ke NILAIBD_LAMA jika NILAIBD memiliki nilai
                if row[7] is not None:
                    row[8] = row[7]   # Pindahkan nilai ke NILAIBD_LAMA
                    row[7] = None     # Kosongkan NILAIBD

                # Simpan perubahan baris
                rows.updateRow(row)

        arcpy.SetParameter(0, persil_nama)
        messages.addMessage("== Proses selesai ==")

        return

    def add_field_if_not_exists(self, feature_class, field_name, field_type):
        field_names = [field.name for field in arcpy.ListFields(feature_class)]
        if field_name not in field_names:
            arcpy.management.AddField(
                feature_class,
                field_name,
                field_type
            )

    def delete_if_exists(self, path):
        if arcpy.Exists(path):
            try:
                arcpy.management.Delete(path)
            except Exception:
                pass

class Rekomendasi_Pembanding(object):

    def __init__(self):

        self.label = "Rekomendasi Pembanding"
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

        max_jarak = arcpy.Parameter(
            displayName="Maksimal Jarak (Meter)",
            name="max_jarak",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input"
        )

        max_jarak.value = 500

        jumlah_rekomendasi = arcpy.Parameter(
            displayName="Jumlah Rekomendasi",
            name="jumlah_rekomendasi",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input"
        )

        jumlah_rekomendasi.value = 10

        return [
            penilaian,
            max_jarak,
            jumlah_rekomendasi
        ]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):

        penilaian = parameters[0]

        try:

            configs = persil.get_config_values()

            dataset_path = configs["project_config"]["dataset_path"]

            persil_path = os.path.join(
                dataset_path,
                "Persil_Layer"
            )

            list_tsi = []

            with arcpy.da.SearchCursor(
                persil_path,
                ["IdBidang"],
                "perubahan = 'menyebar'"
            ) as rows:

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

        messages.addMessage(
            "== Proses rekomendasi dimulai =="
        )

        penilaian = parameters[0].valueAsText
        max_jarak = parameters[1].value
        jumlah_rekomendasi = parameters[2].value

        configs = persil.get_config_values()

        dataset_path = configs["project_config"]["dataset_path"]

        persil_path = os.path.join(
            dataset_path,
            "Persil_Layer"
        )

        objek_layer = "objek_penilaian"
        kandidat_layer = "kandidat_pembanding"
        near_table = "in_memory\\near_table"

        self.delete_if_exists(objek_layer)
        self.delete_if_exists(kandidat_layer)
        self.delete_if_exists(near_table)

        arcpy.management.MakeFeatureLayer(
            persil_path,
            objek_layer,
            f"IDBIDANG = {penilaian}"
        )

        objek = self.get_data_row(objek_layer)

        if not objek:

            messages.addErrorMessage(
                "== Data objek tidak ditemukan =="
            )

            raise arcpy.ExecuteError

        messages.addMessage(
            f"Zonasi objek: {objek['zonasi']}"
        )

        where_clause = (
            f"S_ZONASI = {objek['s_zonasi']} "
            f"AND IDBIDANG <> {penilaian}"
        )

        arcpy.management.MakeFeatureLayer(
            persil_path,
            kandidat_layer,
            where_clause
        )

        jumlah_kandidat = int(
            arcpy.management.GetCount(
                kandidat_layer
            )[0]
        )

        if jumlah_kandidat == 0:

            messages.addErrorMessage(
                "== Tidak ada kandidat dengan zonasi sama =="
            )

            raise arcpy.ExecuteError

        arcpy.analysis.GenerateNearTable(
            objek_layer,
            kandidat_layer,
            near_table,
            f"{max_jarak} Meters",
            "NO_LOCATION",
            "NO_ANGLE",
            "ALL"
        )

        hasil_rekomendasi = []

        near_dict = {}

        with arcpy.da.SearchCursor(
            near_table,
            [
                "NEAR_FID",
                "NEAR_DIST"
            ]
        ) as rows:

            for row in rows:

                near_dict[row[0]] = row[1]

        if len(near_dict) == 0:

            messages.addErrorMessage(
                "== Tidak ada pembanding dalam radius pencarian =="
            )

            raise arcpy.ExecuteError

        fields = [
            "OBJECTID",
            "LUASM2",
            "LBRDPN",
            "S_BENTUK",
            "S_LETAK",
            "S_KLS_JLN",
            "ls_tnh_i",
            "lb_dpn_i",
            "S_ZONASI",
            "ZONASI",
            "NILAIBD_LAMA"
        ]

        with arcpy.da.SearchCursor(
            kandidat_layer,
            fields
        ) as rows:

            for row in rows:

                oid = row[0]

                if oid not in near_dict:
                    continue

                pembanding = {
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

                hasil = self.calculate_penyesuaian(
                    objek,
                    pembanding
                )

                hasil_rekomendasi.append({
                    "OBJECTID": oid,
                    "jarak": round(
                        near_dict[oid],
                        2
                    ),
                    "persentase": round(
                        hasil["persentase"],
                        2
                    ),
                    "score": abs(
                        hasil["persentase"]
                    ),
                    "nilai_nol": hasil["nilai_nol"]
                })

        if len(hasil_rekomendasi) == 0:

            messages.addErrorMessage(
                "== Tidak ada rekomendasi ditemukan =="
            )

            raise arcpy.ExecuteError

        hasil_rekomendasi.sort(
            key=lambda x: (
                x["score"],
                -x["nilai_nol"],
                x["jarak"]
            )
        )

        hasil_rekomendasi = (
            hasil_rekomendasi[:jumlah_rekomendasi]
        )

        oid_list = [
            str(item["OBJECTID"])
            for item in hasil_rekomendasi
        ]

        where_output = (
            f"OBJECTID IN ({','.join(oid_list)})"
        )

        output_layer = "Rekomendasi_Pembanding"

        self.delete_if_exists(output_layer)

        arcpy.management.MakeFeatureLayer(
            persil_path,
            output_layer,
            where_output
        )

        arcpy.management.SelectLayerByAttribute(
            output_layer,
            "NEW_SELECTION",
            where_output
        )

        messages.addMessage("")

        messages.addMessage(
            "== HASIL REKOMENDASI =="
        )

        for i, item in enumerate(
            hasil_rekomendasi,
            start=1
        ):

            messages.addMessage(
                (
                    f"{i}. "
                    f"OBJECTID={item['OBJECTID']} | "
                    f"Jarak={item['jarak']} m | "
                    f"Persentase={item['persentase']}% | "
                    f"Score={item['score']} | "
                    f"Komponen Sama={item['nilai_nol']}"
                )
            )

        arcpy.management.AddSpatialIndex(
            persil_path
        )

        self.delete_if_exists(objek_layer)
        self.delete_if_exists(kandidat_layer)
        self.delete_if_exists(near_table)

        messages.addMessage("")
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

    def get_data_row(self, layer_name):

        fields = [
            "OBJECTID",
            "LUASM2",
            "LBRDPN",
            "S_BENTUK",
            "S_LETAK",
            "S_KLS_JLN",
            "ls_tnh_i",
            "lb_dpn_i",
            "S_ZONASI",
            "ZONASI",
            "NILAIBD_LAMA"
        ]

        with arcpy.da.SearchCursor(
            layer_name,
            fields
        ) as rows:

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

    def calculate_penyesuaian(
        self,
        objek,
        pembanding
    ):

        ls_tnh = (
            (objek["ls_tnh_i"]
             - pembanding["ls_tnh_i"])
            * 0.5
        )

        lb_dpn = (
            (objek["lb_dpn_i"]
             - pembanding["lb_dpn_i"])
            * 1.5
        )

        bentuk = (
            (objek["s_bentuk"]
             - pembanding["s_bentuk"])
            * 1.5
        )

        letak = (
            (objek["s_letak"]
             - pembanding["s_letak"])
            * 1
        )

        kls_jln = (
            (objek["s_kls_jln"]
             - pembanding["s_kls_jln"])
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
            f"IDBIDANG = {penilaian}"
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
                arcpy.AddMessage(pembanding)

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
                "IDBIDANG",
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
            "S_BENTUK",
            "S_LETAK",
            "S_KLS_JLN",
            "ls_tnh_i",
            "lb_dpn_i",
            "S_ZONASI",
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

        persentase = abs(
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

class Hitung_Persil_Individual_Otomatis(object):

    def __init__(self):
        self.label = "Hitung Nilai Persil Individual Otomatis"
        self.description = "Menghitung penyesuaian nilai persil secara otomatis dengan interval pencarian dinamis (Minimal 3 pembanding)."
        self.canRunInBackground = False

    def getParameterInfo(self):

        pilih_zonasi = arcpy.Parameter(
            displayName="Pilih Zonasi",
            name="pilih_zonasi",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        pilih_zonasi.filter.type = "ValueList"
        pilih_zonasi.filter.list = [
            "Sempadan dan Lindung", "Pertanian", "Permukiman Sederhana",
            "Permukiman Menengah", "Permukiman Mewah", "Industri",
            "Perdagangan dan Jasa", "Semua Zonasi"
        ]
        pilih_zonasi.value = "Sempadan dan Lindung"

        max_jarak = arcpy.Parameter(
            displayName="Jarak Maksimal Pembanding (Meter)",
            name="max_jarak",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input"
        )
        max_jarak.value = 200

        interval_jarak = arcpy.Parameter(
            displayName="Interval Pencarian Dinamis (Meter)",
            name="interval_jarak",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input"
        )
        interval_jarak.value = 20

        timpa_data = arcpy.Parameter(
            displayName="Ganti Semua Data? (Abaikan jika sudah ada nilai/pembanding)",
            name="timpa_data",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )
        timpa_data.value = False

        return [pilih_zonasi, max_jarak, interval_jarak, timpa_data]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):

        messages.addMessage("== Proses dimulai ==")

        zonasi = parameters[0].valueAsText
        max_jarak = parameters[1].value
        interval = parameters[2].value
        timpa_data = parameters[3].value

        if interval is None or interval <= 0:
            interval = max_jarak if max_jarak > 0 else 20

        if zonasi == "Semua Zonasi":
            main_zonasi = [1, 2, 3, 4, 5, 6, 7]
        else:
            main_zonasi = [constant.SKORING_ZONASI[zonasi]]

        configs = persil.get_config_values()
        dataset_path = configs["project_config"]["dataset_path"]
        persil_path = os.path.join(dataset_path, "Persil_Layer")

        # =========================================================
        # 1. PERSIAPAN FIELD DAN BACA MEMORY
        # =========================================================
        self.add_field_if_not_exists(persil_path, "data_pembanding", "TEXT")

        target_dict = {}
        pembanding_dict = {}

        fields = [
            "OBJECTID", "SHAPE@XY", "S_ZONASI", "S_KLS_JLN", "NILAIBD_LAMA",
            "LUASM2", "LBRDPN", "S_BENTUK", "S_LETAK", "ls_tnh_i",
            "lb_dpn_i", "IDBIDANG", "perubahan", "data_pembanding"
        ]

        messages.addMessage("Membaca atribut persil ke memori...")
        with arcpy.da.SearchCursor(persil_path, fields) as rows:
            for row in rows:
                if row[2] in main_zonasi:
                    data_row = {
                        "OBJECTID": row[0], "x": row[1][0], "y": row[1][1],
                        "s_zonasi": row[2], "s_kls_jln": row[3], "nilai": row[4],
                        "ls_tnh": row[5], "lb_dpn": row[6], "s_bentuk": row[7],
                        "s_letak": row[8], "ls_tnh_i": row[9], "lb_dpn_i": row[10],
                        "IDBIDANG": row[11], "perubahan": row[12], "data_pembanding": row[13]
                    }

                    if row[12] == 'menyebar':
                        nilai_lama = row[4]
                        data_pemb = row[13]

                        if not timpa_data:
                            ada_nilai = (nilai_lama is not None and nilai_lama > 0)
                            ada_pemb = (data_pemb is not None and data_pemb.strip() != "")
                            if ada_nilai or ada_pemb:
                                continue

                        target_dict[row[0]] = data_row

                    elif row[12] is None and (row[4] is not None and row[4] > 0):
                        pembanding_dict[row[0]] = data_row

        if not target_dict:
            messages.addWarningMessage("Tidak ada target persil yang memenuhi kriteria untuk diproses.")
            return

        # =========================================================
        # 2. PROSES NEAR TABLE DINAMIS (INTERVAL LOOP)
        # =========================================================
        messages.addMessage("Melakukan pencarian jarak secara dinamis...")

        target_layer = "target_layer_temp"
        kandidat_layer = "kandidat_layer_temp"
        near_table = "memory\\bulk_near_table" 

        zonasi_str = ",".join(map(str, main_zonasi))
        kandidat_where = f"S_ZONASI IN ({zonasi_str}) AND perubahan IS NULL AND NILAIBD_LAMA IS NOT NULL AND NILAIBD_LAMA > 0"
        
        self.delete_if_exists(kandidat_layer)
        arcpy.management.MakeFeatureLayer(persil_path, kandidat_layer, kandidat_where)

        unresolved_targets = set(target_dict.keys())
        dict_update_massal = {}
        jumlah_pembanding = 3 # <-- Batas minimum yang ditetapkan

        interval_list = list(range(interval, max_jarak, interval))
        if max_jarak not in interval_list:
            interval_list.append(max_jarak)

        for jarak_sekarang in interval_list:
            if not unresolved_targets:
                break 

            messages.addMessage(f"Mencari kandidat pada radius {jarak_sekarang} meter... (Sisa Target: {len(unresolved_targets)})")

            target_oids_str = ",".join(map(str, unresolved_targets))
            target_where = f"OBJECTID IN ({target_oids_str})"
            
            self.delete_if_exists(target_layer)
            self.delete_if_exists(near_table)
            arcpy.management.MakeFeatureLayer(persil_path, target_layer, target_where)

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

            # =========================================================
            # 3. EVALUASI DAN HITUNG REKOMENDASI PADA INTERVAL INI
            # =========================================================
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
                            
                            # Filter Tambahan
                            if abs(hasil["persentase"]) > 10:
                                continue 
                            
                            skor_jarak = (jarak / max_jarak_safe) * 100 
                            skor_persentase = abs(hasil["persentase"])
                            skor_pemilihan = (skor_jarak * 0.70) + (skor_persentase * 0.30)
                            
                            hasil_rekomendasi.append({
                                "OBJECTID": near_fid,
                                "jarak": round(jarak, 2),
                                "persentase": round(hasil["persentase"], 2),
                                "skor_pemilihan": skor_pemilihan, 
                                "nilai_nol": hasil["nilai_nol"],
                                "data_hasil": hasil 
                            })

                hasil_rekomendasi.sort(
                    key=lambda x: (
                        x["skor_pemilihan"],
                        -x["nilai_nol"],
                        x["jarak"]
                    )
                )

                is_last_interval = (jarak_sekarang == max_jarak)
                
                if len(hasil_rekomendasi) >= jumlah_pembanding:
                    # Mengambil 3 pembanding terbaik (sesuai jumlah_pembanding)
                    rekomendasi_final = hasil_rekomendasi[:jumlah_pembanding]

                    validasi_berhasil = True
                    hasil_list = []
                    id_pembanding_list = []

                    for i, rec in enumerate(rekomendasi_final, start=1):
                        hasil = rec["data_hasil"]
                        if hasil["persentase"] > 10:
                            arcpy.AddWarning(f"== Pembanding untuk IDBIDANG {objek['IDBIDANG']} memiliki persentase > 10%. Ditunda ke radius berikutnya ==")
                            validasi_berhasil = False
                            break
                        hasil_list.append(hasil)
                        id_pembanding_list.append(str(rec['OBJECTID']))

                    if validasi_berhasil:
                        total_nol = sum(h["nilai_nol"] for h in hasil_list)
                        nilai_akhir = 0

                        if total_nol > 0:
                            for hasil in hasil_list:
                                bobot = (hasil["nilai_nol"] / total_nol) 
                                nilai_akhir += hasil["nilai"] * bobot
                        else:
                            bobot_rata = 1.0 / len(hasil_list)
                            for hasil in hasil_list:
                                nilai_akhir += hasil["nilai"] * bobot_rata

                        list_data_pembanding = " ; ".join(id_pembanding_list)

                        dict_update_massal[objek["IDBIDANG"]] = {
                            "data_pembanding": list_data_pembanding,
                            "nilai_akhir": nilai_akhir,
                            "perubahan": "individual"
                        }
                    
                        # Hanya hapus dari antrean target JIKA validasi BERHASIL dan syarat >= 3 terpenuhi
                        unresolved_targets.remove(target_oid)

                else:
                    # Jika belum mencapai minimal 3 pembanding
                    if is_last_interval:
                        # Jika sudah mentok di jarak maksimal tapi kandidat tetap kurang dari 3, berikan notifikasi
                        arcpy.AddWarning(f"IDBIDANG {objek['IDBIDANG']} dilewati: Hanya memiliki {len(hasil_rekomendasi)} pembanding valid (Syarat minimal: {jumlah_pembanding}).")

        # Bersihkan Memori Loop
        self.delete_if_exists(target_layer)
        self.delete_if_exists(kandidat_layer)
        self.delete_if_exists(near_table)

        # =========================================================
        # 4. UPDATE DATABASE SECARA MASSAL (BATCH UPDATE)
        # =========================================================
        if dict_update_massal:
            messages.addMessage(f"Menyimpan pembaruan nilai untuk {len(dict_update_massal)} bidang...")
            
            with arcpy.da.UpdateCursor(
                persil_path, 
                ["IDBIDANG", "data_pembanding", "NILAIBD_LAMA", "perubahan"]
            ) as rows:
                for row in rows:
                    idbidang = row[0]
                    if idbidang in dict_update_massal:
                        data_baru = dict_update_massal[idbidang]
                        row[1] = data_baru["data_pembanding"]
                        row[2] = data_baru["nilai_akhir"]
                        row[3] = data_baru["perubahan"]
                        
                        rows.updateRow(row)

            messages.addMessage("== Proses Berhasil Disimpan ==")
        else:
            messages.addWarningMessage("Tidak ada data persil yang valid untuk di-update.")

        return
    
    def calculate_penyesuaian(self, objek, pembanding):
        ls_tnh = (objek["ls_tnh_i"] - pembanding["ls_tnh_i"]) * 0.5
        lb_dpn = (objek["lb_dpn_i"] - pembanding["lb_dpn_i"]) * 1.5
        bentuk = (objek["s_bentuk"]- pembanding["s_bentuk"]) * 1.5
        letak = (objek["s_letak"] - pembanding["s_letak"]) * 1
        kls_jln = (objek["s_kls_jln"] - pembanding["s_kls_jln"]) * 3

        persentase = abs(ls_tnh + lb_dpn + bentuk + letak + kls_jln)
        nilai = pembanding["nilai"] * (100 + persentase) / 100

        komponen = [ls_tnh, lb_dpn, bentuk, letak, kls_jln]
        nilai_nol = komponen.count(0)

        return {
            "persentase": persentase,
            "nilai": nilai,
            "nilai_nol": nilai_nol
        }

    def delete_if_exists(self, path):
        if arcpy.Exists(path):
            try:
                arcpy.management.Delete(path)
            except Exception:
                pass

    def add_field_if_not_exists(self, feature_class, field_name, field_type):
        field_names = [field.name for field in arcpy.ListFields(feature_class)]
        if field_name not in field_names:
            arcpy.management.AddField(feature_class, field_name, field_type)

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

        self.label = "Generate Titik Zona"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):

        output_zona = arcpy.Parameter(
            displayName="Output Titik Zona",
            name="output_zona",
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
            output_zona,
            output_sampel
        ]

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

        zona_path = os.path.join(
            dataset_path,
            "Titik_Zona"
        )

        identity_output = os.path.join(
            dataset_path,
            "temp_identity"
        )

        temp_zona = "temp_zona"

        cleanup_items = [

            identity_output,
            zona_path,
            temp_zona,

            "Titik_Zona",
            "Titik_Sampel_Update"
        ]

        for item in cleanup_items:

            self.delete_if_exists(item)

        # =====================================================
        # Identity
        # =====================================================

        messages.addMessage(
            "== Proses identity =="
        )

        arcpy.analysis.Identity(
            sampel_path,
            persil_path,
            identity_output
        )

        # =====================================================
        # Tambah Field Indeks
        # =====================================================

        self.add_field_if_not_exists(
            identity_output,
            "INDEKS",
            "DOUBLE"
        )

        # =====================================================
        # Hitung Indeks
        # =====================================================

        messages.addMessage(
            "== Hitung indeks =="
        )

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
            identity_output,
            "INDEKS",
            "doSomething(!nilai!, !NILAIBD_LAMA!)",
            "PYTHON3",
            code_block
        )

        # =====================================================
        # Sorting
        # =====================================================

        messages.addMessage(
            "== Sorting indeks =="
        )

        arcpy.management.Sort(
            identity_output,
            zona_path,
            [
                ["S_ZONASI", "ASCENDING"],
                ["INDEKS", "ASCENDING"]
            ]
        )

        # =====================================================
        # Seleksi Titik Zona
        # =====================================================

        messages.addMessage(
            "== Seleksi titik zona =="
        )
        temp_zona_filtered = os.path.join(
            "in_memory",
            "temp_zona_filtered"
        )

        self.delete_if_exists(
            temp_zona_filtered
        )

        arcpy.management.MakeFeatureLayer(
            zona_path,
            temp_zona,
            (
                "kelompok_perubahan IS NULL "
                "OR kelompok_perubahan = 0"
            )
        )

        arcpy.management.CopyFeatures(
            temp_zona,
            temp_zona_filtered
        )

        self.delete_if_exists(
            zona_path
        )

        arcpy.management.CopyFeatures(
            temp_zona_filtered,
            zona_path
        )

        # =====================================================
        # Hapus Titik Zona dari Titik Sampel
        # =====================================================

        messages.addMessage(
            "== Sinkronisasi titik sampel =="
        )

        zona_ids = set()

        with arcpy.da.SearchCursor(
            zona_path,
            ["FID_Titik_Sampel"]
        ) as rows:

            for row in rows:

                if row[0] is not None:

                    zona_ids.add(
                        row[0]
                    )

        with arcpy.da.UpdateCursor(
            sampel_path,
            ["OBJECTID"]
        ) as rows:

            for row in rows:

                if row[0] in zona_ids:

                    rows.deleteRow()

        # =====================================================
        # Hapus Field Tidak Digunakan
        # =====================================================

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
            for field in arcpy.ListFields(
                zona_path
            )
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
                zona_path,
                valid_delete_fields
            )

        # =====================================================
        # Feature Layer
        # =====================================================

        arcpy.management.MakeFeatureLayer(
            zona_path,
            "Titik_Zona"
        )

        arcpy.management.MakeFeatureLayer(
            sampel_path,
            "Titik_Sampel"
        )

        # =====================================================
        # Symbology
        # =====================================================

        simbologi_path = os.path.join(
            appdata,
            "Simbologi_Titik_Zona.lyrx"
        )

        if os.path.exists(
            simbologi_path
        ):

            arcpy.management.ApplySymbologyFromLayer(
                "Titik_Zona",
                simbologi_path
            )

        # =====================================================
        # Output
        # =====================================================

        parameters[0].value = (
            "Titik_Zona"
        )

        parameters[1].value = (
            "Titik_Sampel"
        )

        # =====================================================
        # Cleanup
        # =====================================================

        self.delete_if_exists(
            identity_output
        )

        self.delete_if_exists(
            temp_zona
        )

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

    def add_field_if_not_exists(
        self,
        feature_class,
        field_name,
        field_type
    ):

        field_names = [

            field.name.upper()
            for field in arcpy.ListFields(
                feature_class
            )
        ]

        if field_name.upper() not in field_names:

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
            "Titik_Zona"
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

        if arcpy.Exists("Titik_Zona"):

            try:
                arcpy.management.Delete(
                    "Titik_Zona"
                )

            except Exception:
                pass

        arcpy.management.MakeFeatureLayer(
            titik_indeks,
            "Titik_Zona"
        )

        simbologi_path = os.path.join(
            appdata,
            "Simbologi_Titik_Indeks_Outlier.lyrx"
        )

        if os.path.exists(simbologi_path):

            arcpy.management.ApplySymbologyFromLayer(
                "Titik_Zona",
                simbologi_path
            )

        parameters[0].value = "Titik_Zona"

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

class Simpan_Sebagai_Perubahan_Menyebar(object):
    def __init__(self):
        """Mendefinisikan informasi Tool."""
        self.label = "Update Atribut (Menyebar)"
        self.description = "Tools untuk memperbarui field (perubahan, status_per, NILAIBD_LAMA, data_pembanding, kelompok_perubahan) pada feature yang dipilih (selected features)."
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Mendefinisikan parameter input untuk tool."""
        # Parameter 0: Input Feature Layer
        param0 = arcpy.Parameter(
            displayName="Penjelasan",
            name="in_features",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )

        param0.value = 'Tools ujicoba'
        
        return [param0]

    def isLicensed(self):
        """Cek lisensi (biarkan return True agar selalu bisa digunakan)."""
        return True

    def updateParameters(self, parameters):
        """Memodifikasi nilai parameter sebelum divalidasi (tidak diperlukan untuk tools ini)."""
        return

    def updateMessages(self, parameters):
        """Memodifikasi pesan error/warning bawaan (tidak diperlukan untuk tools ini)."""
        return

    def execute(self, parameters, messages):
        """Kode utama yang dieksekusi saat klik RUN."""
        # Mengambil input dari user
        in_features = 'Persil_Layer'
        
        # Daftar field yang akan di-update (urutan harus sama dengan di bawah)
        fields = ['perubahan', 'status_per', 'NILAIBD_LAMA', 'data_pembanding', 'kelompok_perubahan']
        
        try:
            # Membuka UpdateCursor
            # Cursor otomatis hanya mengeksekusi fitur yang sedang terpilih (selected)
            with arcpy.da.UpdateCursor(in_features, fields) as cursor:
                count = 0
                for row in cursor:
                    row[0] = 'menyebar'  # perubahan
                    row[1] = 'update'    # status_per
                    row[2] = 0           # NILAIBD_LAMA
                    row[3] = None        # data_pembanding
                    row[4] = None        # kelompok_perubahan
                    
                    # Terapkan perubahan pada baris tersebut
                    cursor.updateRow(row)
                    count += 1
            
            # Tampilkan pesan sukses di geoprocessing window
            messages.addMessage(f"✅ Selesai! Berhasil memperbarui {count} fitur.")
            
        except Exception as e:
            # Tampilkan pesan error jika ada field yang tidak ditemukan atau tipe data salah
            messages.addErrorMessage(f"❌ Terjadi kesalahan: {str(e)}")
            messages.addErrorMessage("Pastikan Feature Layer memiliki field: perubahan, status_per, NILAIBD_LAMA, data_pembanding, dan kelompok_perubahan dengan tipe data yang sesuai.")
            
        return
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
        self.label = "Periksa Titik Sampel Kelompok Perubahan"
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
        
        persil_path = os.path.join(dataset_path, "Persil_Layer")
        sampel_path = os.path.join(dataset_path, "Titik_Sampel")
        
        # MENGGUNAKAN WORKSPACE MEMORY (in_memory ArcGIS Pro)
        # File sementara akan disimpan langsung di RAM komputer Anda
        dissolve_path = r"memory\temp_dissolve_persil"
        identity_path = r"memory\temp_identity_cluster"

        # PENTING: Sesuaikan nama field nomor/ID sampel dari layer Titik_Sampel Anda di sini
        field_nomor_sampel = "no_sampel" 

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

        # Bersihkan data memory lawas jika ada (mencegah error jika dijalankan berulang kali)
        self.delete_if_exists(dissolve_path)
        self.delete_if_exists(identity_path)

        # 1. PROSES DISSOLVE PERSIL TERLEBIH DAHULU
        messages.addMessage("== Melakukan Dissolve pada Persil Layer (di dalam Memory) ==")
        
        fields = [f.name.lower() for f in arcpy.ListFields(persil_path)]
        if "kelompok_perubahan" not in fields:
            messages.addErrorMessage("Field 'kelompok_perubahan' tidak ditemukan di Persil_Layer")
            raise arcpy.ExecuteError

        arcpy.management.Dissolve(
            in_features=persil_path,
            out_feature_class=dissolve_path,
            dissolve_field="kelompok_perubahan",
            multi_part="MULTI_PART"
        )

        # 2. PROSES IDENTITY MENGGUNAKAN HASIL DISSOLVE
        messages.addMessage("== Membuat identity dengan Persil Ter-dissolve (di dalam Memory) ==")

        arcpy.analysis.Identity(
            sampel_path,
            dissolve_path,
            identity_path
        )

        # Cek apakah field nomor sampel ada di hasil identity
        identity_fields = [f.name.lower() for f in arcpy.ListFields(identity_path)]
        if field_nomor_sampel.lower() not in identity_fields:
            messages.addWarningMessage(
                f"Field '{field_nomor_sampel}' tidak ditemukan di output identity. Menggunakan OBJECTID default."
            )
            field_nomor_sampel = "OBJECTID"

        list_cluster = []

        # Mengambil kelompok_perubahan yang valid
        with arcpy.da.SearchCursor(
            identity_path,
            ["kelompok_perubahan"]
        ) as rows:
            for row in rows:
                if row[0] is not None and str(row[0]).strip() != "":
                    list_cluster.append(row[0])

        unique_cluster = sorted(
            list(set(list_cluster))
        )

        messages.addMessage(
            "== Periksa jumlah titik sampel =="
        )

        for cluster_id in unique_cluster:

            titik_list = []

            # Gunakan penanganan tipe data dinamis untuk klausa WHERE kelompok_perubahan
            # (Mengantisipasi jika field berupa String/Teks atau Short/Long Integer)
            field_type = [f.type for f in arcpy.ListFields(identity_path, "kelompok_perubahan")][0]
            if field_type in ["String", "Guid"]:
                where_clause = f"kelompok_perubahan = '{cluster_id}'"
            else:
                where_clause = f"kelompok_perubahan = {cluster_id}"

            # Mengambil nomor sampel berdasarkan field_nomor_sampel
            with arcpy.da.SearchCursor(
                identity_path,
                [field_nomor_sampel],
                where_clause
            ) as rows:
                for row in rows:
                    if row[0] is not None:
                        titik_list.append(str(row[0]))

            jumlah_titik = len(titik_list)
            str_nomor_sampel = ", ".join(titik_list) if titik_list else "-"

            if jumlah_titik > 3:
                messages.addWarningMessage(
                    f"Kelompok [{cluster_id}] memiliki titik sampel LEBIH dari 3 (Jumlah: {jumlah_titik}). "
                    f"Nomor Sampel: [{str_nomor_sampel}]"
                )

            elif jumlah_titik < 3:
                messages.addWarningMessage(
                    f"Kelompok [{cluster_id}] memiliki titik sampel KURANG dari 3 (Jumlah: {jumlah_titik}). "
                    f"Nomor Sampel: [{str_nomor_sampel}]"
                )

            else:
                messages.addMessage(
                    f"Kelompok [{cluster_id}] memiliki TEPAT 3 titik sampel. "
                    f"Nomor Sampel: [{str_nomor_sampel}]"
                )

        # Bersihkan memory setelah proses selesai agar RAM komputer kembali lega
        self.delete_if_exists(dissolve_path)
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

class Hitung_Statistik_Kelompok_Perubahan(object):

    def __init__(self):
        self.label = "Penyesuaian Hitung Statistik Kelompok Perubahan"
        self.description = ""
        self.canRunInBackground = False

    # =====================================================
    # PARAMETER
    # =====================================================
    def getParameterInfo(self):
        # Parameter baru untuk memilih kelompok (bisa pilih lebih dari satu)
        param_kelompok = arcpy.Parameter(
            displayName="Pilih ID Kelompok Perubahan (Kosongkan untuk proses semua)",
            name="kelompok_pilihan",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input",
            multiValue=True
        )

        output_persil = arcpy.Parameter(
            displayName="Output Persil",
            name="output_persil",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )
        
        return [param_kelompok, output_persil]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        # 1. Cek apakah ada persil layer atau layer dengan sumber data yang valid di map
        # Kita berasumsi nama layer atau path datanya bisa diambil dari config atau default "Persil_Layer"
        # Namun karena fungsi ini berjalan real-time sebelum 'execute', kita bisa mencari layer bernama "Persil_Layer" di map aktif
        
        # Lakukan pengecekan hanya jika daftar pilihan belum terisi (agar tidak terus-menerus membaca data/looping berat)
        if not parameters[0].filter.list:
            try:
                aprx = arcpy.mp.ArcGISProject("CURRENT")
                current_map = aprx.activeMap
                persil_layer = None
                
                # Mencari apakah ada layer bernama "Persil_Layer" di isi Map
                if current_map:
                    for layer in current_map.listLayers():
                        if layer.name == "Persil_Layer":
                            persil_layer = layer
                            break
                
                # Jika tidak ada di Map aktif, coba alternatif mengambil dari konfigurasi path (jika persil ter-import)
                if not persil_layer:
                    # Opsi fallback: jika script 'persil' dan environment project-nya siap
                    configs = persil.get_config_values()
                    dataset_path = configs["project_config"]["dataset_path"]
                    fallback_path = os.path.join(dataset_path, "Persil_Layer")
                    if arcpy.Exists(fallback_path):
                        persil_layer = fallback_path

                # 2. Kalau layer ditemukan, ambil nilai kelompok perubahan yang unik
                if persil_layer and arcpy.Exists(persil_layer):
                    list_kelompok = []
                    fields = [field.name for field in arcpy.ListFields(persil_layer)]
                    
                    # Pastikan field yang dibutuhkan ada sebelum memanggil cursor
                    if "kelompok_perubahan" in fields and "perubahan" in fields:
                        where_clause = "perubahan = 'mengelompok'"
                        with arcpy.da.SearchCursor(persil_layer, ["kelompok_perubahan"], where_clause) as rows:
                            for row in rows:
                                if row[0] not in (None, 0, ""):
                                    list_kelompok.append(int(row[0]))
                        
                        unique_kelompok = sorted(list(set(list_kelompok)))
                        
                        # 3. Ubah parameter 0 menjadi dropdown dengan mengisi nilai filter list
                        if unique_kelompok:
                            parameters[0].filter.type = "ValueList"
                            parameters[0].filter.list = unique_kelompok
            except Exception:
                # Menggunakan pass agar jika ada error pembacaan map saat inisialisasi, tool tidak langsung crash
                pass
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

    def add_field_if_not_exists(self, feature_class, field_name, field_type):
        fields = [field.name.upper() for field in arcpy.ListFields(feature_class)]
        if field_name.upper() not in fields:
            arcpy.management.AddField(feature_class, field_name, field_type)

    def get_data_row(self, persil_path, id_bidang):
        fields = [
            "IdBidang", "OBJECTID", "LUASM2", "LBRDPN", "S_BENTUK", 
            "S_LETAK", "S_KLS_JLN", "ls_tnh_i", "lb_dpn_i", "S_ZONASI", 
            "ZONASI", "NILAIBD_LAMA" 
        ]
        
        with arcpy.da.SearchCursor(persil_path, fields, f"IdBidang = {id_bidang}") as rows:
            for row in rows:
                return {
                    "IdBidang": row[0],
                    "OBJECTID": row[1],
                    "ls_tnh": row[2],
                    "lb_dpn": row[3],
                    "s_bentuk": row[4],
                    "s_letak": row[5],
                    "s_kls_jln": row[6],
                    "ls_tnh_i": row[7],
                    "lb_dpn_i": row[8],
                    "s_zonasi": row[9],
                    "zonasi": row[10],
                    "nilai": row[11] # Nilai ini nantinya akan ditimpa dengan harga sampel untuk Pembanding
                }
        return None

    def calculate_penyesuaian(self, objek, pembanding):
        ls_tnh = ((objek["ls_tnh_i"] - pembanding["ls_tnh_i"]) * 0.5)
        lb_dpn = ((objek["lb_dpn_i"] - pembanding["lb_dpn_i"]) * 1.5)
        bentuk = ((objek["s_bentuk"] - pembanding["s_bentuk"]) * 1.5)
        letak = ((objek["s_letak"] - pembanding["s_letak"]) * 1)
        kls_jln = ((objek["s_kls_jln"] - pembanding["s_kls_jln"]) * 3)

        persentase = abs(ls_tnh + lb_dpn + bentuk + letak + kls_jln)
        nilai = (pembanding["nilai"] * (100 + persentase)) / 100

        komponen = [ls_tnh, lb_dpn, bentuk, letak, kls_jln]
        nilai_nol = komponen.count(0)
        return {
            "persentase": persentase,
            "nilai": nilai,
            "nilai_nol": nilai_nol
        }

    # =====================================================
    # EXECUTE
    # =====================================================

    def execute(self, parameters, messages):
        messages.addMessage("== Proses dimulai ==")

        # Mendapatkan nilai pilihan kelompok dari parameter input pengguna
        pilihan_user = parameters[0].values
        list_pilihan = []
        if pilihan_user:
            list_pilihan = [int(v) for v in pilihan_user]

        configs = persil.get_config_values()
        dataset_path = configs["project_config"]["dataset_path"]

        # =================================================
        # DATASET & MEMORY WORKSPACE
        # =================================================
        persil_path = os.path.join(dataset_path, "Persil_Layer")
        sampel_path = os.path.join(dataset_path, "Titik_Sampel")

        identity_path = r"memory\temp_identity_kelompok"
        temp_intersect = r"memory\temp_intersect_kelompok"
        temp_dissolve_persil = r"memory\temp_dissolve_persil"

        # =================================================
        # VALIDASI
        # =================================================
        required_fc = [persil_path, sampel_path]
        for fc in required_fc:
            if not arcpy.Exists(fc):
                messages.addErrorMessage(f"Feature class {os.path.basename(fc)} tidak ditemukan")
                raise arcpy.ExecuteError

        cleanup_items = [identity_path, temp_intersect, temp_dissolve_persil]
        for item in cleanup_items:
            self.delete_if_exists(item)

        # =================================================
        # FIELD MANAGEMENT
        # =================================================
        self.add_field_if_not_exists(persil_path, "SMPBKREL", "DOUBLE")
        self.add_field_if_not_exists(persil_path, "data_pembanding", "TEXT")

        # =================================================
        # IDENTITY 
        # =================================================
        messages.addMessage("== Membuat identity ==")
        arcpy.analysis.Identity(
            sampel_path,
            persil_path,
            identity_path
        )

        # =================================================
        # GET KELOMPOK LIST
        # =================================================
        list_kelompok = []
        with arcpy.da.SearchCursor(identity_path, ["kelompok_perubahan"], "perubahan = 'mengelompok'") as rows:
            for row in rows:
                if row[0] not in (None, 0, ""):
                    list_kelompok.append(row[0])

        unique_kelompok = sorted(list(set(list_kelompok)))

        # Filter kelompok berdasarkan input pengguna (jika diisi)
        if list_pilihan:
            unique_kelompok = [k for k in unique_kelompok if k in list_pilihan]
            
            # Validasi jika input pengguna tidak ada di dataset
            if not unique_kelompok:
                messages.addWarningMessage(f"Kelompok yang dimasukkan {list_pilihan} tidak ditemukan atau tidak valid. Proses dihentikan.")
                return

        messages.addMessage(f"Kelompok yang akan dihitung: {unique_kelompok}")

        # =================================================
        # LOOP KELOMPOK
        # =================================================
        counter = 0
        for kelompok_id in unique_kelompok:
            counter += 1
            messages.addMessage(f"== Proses Kelompok {kelompok_id} ==")
            
            # --- KONFIGURASI NAMA FIELD HARGA SAMPEL ---
            # UBAH "NILAI_SAMPEL" di bawah ini sesuai dengan nama kolom harga yang ada di Titik Sampel!
            field_harga_sampel = "nilai" 
            # -------------------------------------------
            
            pembanding_dict = {}
            where_clause_kelompok = f"kelompok_perubahan = {kelompok_id}"
            
            try:
                # Mengambil ID dan Harga langsung dari hasil identity (yang membawa atribut sampel)
                with arcpy.da.SearchCursor(identity_path, ["IdBidang", field_harga_sampel], where_clause_kelompok) as rows:
                    for row in rows:
                        if row[0] not in (None, "", 0):
                            if row[0] not in pembanding_dict:
                                pembanding_dict[row[0]] = row[1] 
            except RuntimeError as e:
                messages.addErrorMessage(f"Error membaca '{field_harga_sampel}'. Pastikan field tersebut benar dari sampel. Error: {str(e)}")
                raise arcpy.ExecuteError
            
            pembanding_ids = list(pembanding_dict.keys())

            if len(pembanding_ids) > 3:
                messages.addMessage(f"--> Dilewati: Bidang pembanding > 3 ({len(pembanding_ids)} bidang).")
                continue
            elif len(pembanding_ids) < 3:
                messages.addMessage(f"--> Dilewati: Bidang pembanding < 3 ({len(pembanding_ids)} bidang).")
                continue
            # =============================================
            # PERHITUNGAN STATISTIK (MEAN, STD, PTDDEV)
            # =============================================
            list_nilai_adj = []
            for pid in pembanding_ids:
                harga_sampel = pembanding_dict[pid]
                list_nilai_adj.append(harga_sampel)
            
            mean_val = statistics.mean(list_nilai_adj)
            std_val = statistics.stdev(list_nilai_adj)
                
            # Hitung PTDDEV (Koefisien Variasi dalam bentuk persentase)
            ptddev = (std_val / mean_val * 100) if mean_val != 0 else 0

            if ptddev > 15:
                arcpy.AddWarning(f'kelompok perubahan {kelompok_id} memiliki standar deviasi lebih dari 15%. Penilaian dilewati')
                continue
            
            # =================================================
            # UPDATE ATRIBUT BIDANG PEMBANDING ITU SENDIRI
            # =================================================
            
            for pid in pembanding_ids:
                harga_sampel = pembanding_dict[pid]
                with arcpy.da.UpdateCursor(
                    persil_path,
                    ["NILAIBD", "data_pembanding", "perubahan", "SMPBKREL"],
                    f"IdBidang = {pid}"
                ) as p_cursor:
                    for p_row in p_cursor:
                        p_row[0] = round(harga_sampel)  # NILAIBD dari nilai sampel
                        p_row[1] = None          # Kosongkan data_pembanding
                        p_row[3] = ptddev
                        p_cursor.updateRow(p_row)
                messages.addMessage(f"  - Bidang Pembanding IdBidang= {pid} diperbarui (NILAIBD={round(harga_sampel)}).")

            pembanding_data = []
            for pid in pembanding_ids:
                data = self.get_data_row(persil_path, pid)
                if data:
                    # Menimpa NILAIBD_LAMA yang diambil sebelumnya dengan Harga Sampel (dari tabel identity)
                    data["nilai"] = pembanding_dict[pid] 
                    pembanding_data.append(data)
            
            if len(pembanding_data) != 3:
                continue

            pembanding1, pembanding2, pembanding3 = pembanding_data[0], pembanding_data[1], pembanding_data[2]
            
            # Mendapatkan Objek yang akan dihitung (bidang di kelompok yg bukan pembanding)
            objek_ids = []
            with arcpy.da.SearchCursor(persil_path, ["IdBidang"], where_clause_kelompok) as rows:
                for row in rows:
                    if row[0] not in pembanding_ids:
                        objek_ids.append(row[0])

            # Hitung individual untuk setiap bidang objek
            for obj_id in objek_ids:
                objek = self.get_data_row(persil_path, obj_id)
                if not objek: continue

                zonasi_valid = True
                for p_idx, p in enumerate(pembanding_data, start=1):
                    if objek["s_zonasi"] != p["s_zonasi"]:
                        messages.addMessage(f"  - Objek IdBidang={obj_id} dilewati (Zonasi beda dgn Pembanding {p_idx}).")
                        zonasi_valid = False
                        break
                
                if not zonasi_valid: continue

                # Kalkulasi masing-masing pembanding
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
                        arcpy.AddWarning(
                            f"== bidang {obj_id} tidak bisa dihitung karena memiliki persentase lebih dari 10% =="
                        )
                        continue
                nilai_adj1 = hasil1["nilai"]
                nilai_adj2 = hasil2["nilai"]
                nilai_adj3 = hasil3["nilai"]

                total_nol = hasil1["nilai_nol"] + hasil2["nilai_nol"] + hasil3["nilai_nol"]
                
                # Jika semua nilai_nol adalah 0, bagi bobot sama rata (masing-masing sepertiga)
                if total_nol == 0:
                    bobot1 = 100.0 / 3.0
                    bobot2 = 100.0 / 3.0
                    bobot3 = 100.0 / 3.0
                # Jika ada nilai_nol, hitung bobot secara proporsional seperti biasa
                else:
                    bobot1 = (hasil1["nilai_nol"] / total_nol) * 100
                    bobot2 = (hasil2["nilai_nol"] / total_nol) * 100
                    bobot3 = (hasil3["nilai_nol"] / total_nol) * 100
                
                nilai_akhir = (
                    (nilai_adj1 * bobot1 / 100) +
                    (nilai_adj2 * bobot2 / 100) +
                    (nilai_adj3 * bobot3 / 100)
                )

                list_data_pembanding = f"{pembanding1['OBJECTID']} ; {pembanding2['OBJECTID']} ; {pembanding3['OBJECTID']}"

                # Update ke kolom NILAIBD secara langsung
                with arcpy.da.UpdateCursor(
                    persil_path,
                    ["data_pembanding", "NILAIBD", "perubahan", "SMPBKREL"],
                    f"IdBidang = {obj_id}"
                ) as u_cursor:
                    for u_row in u_cursor:
                        u_row[0] = list_data_pembanding
                        u_row[1] = round(nilai_akhir)
                        u_row[2] = "mengelompok"
                        u_row[3] = ptddev
                        u_cursor.updateRow(u_row)

        # =================================================
        # REFRESH LAYER
        # =================================================
        if arcpy.Exists("Persil_Layer"):
            try:
                arcpy.management.Delete("Persil_Layer")
            except Exception:
                pass

        arcpy.management.MakeFeatureLayer(persil_path, "Persil_Layer")
        
        # PERHATIKAN: Ubah index parameter ke 1, karena sekarang output_persil adalah parameter kedua
        parameters[1].value = "Persil_Layer"

        try:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            current_map = aprx.activeMap
            for layer in current_map.listLayers():
                if layer.name == "Titik_Sampel":
                    layer.visible = True
        except Exception:
            pass

        for item in cleanup_items:
            self.delete_if_exists(item)

        messages.addMessage("== Proses selesai ==")
        return

class Mencari_Nilai_Outlier(object):
    def __init__(self):
        self.label = "Mencari Nilai Outlier"
        self.description = "Mencari bidang anomali berdasarkan pilihan Kelurahan, Zonasi spesifik, dan perbandingan nilai dalam radius tertentu menggunakan Near Table."
        self.canRunInBackground = False

    def getParameterInfo(self):
        # 0. Parameter Input Layer
        param_in_fc = arcpy.Parameter(
            displayName="Input Feature Layer (Bidang)",
            name="in_features",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")

        # 1. Parameter Pilihan Kelurahan (Dropdown Dinamis)
        param_kelurahan = arcpy.Parameter(
            displayName="Pilih Kelurahan (Otomatis dari field WADMKD)",
            name="kelurahan_value",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param_kelurahan.filter.type = "ValueList"

        # 2. Parameter Pilihan Nilai Zonasi (Dropdown Dinamis)
        param_zone_val = arcpy.Parameter(
            displayName="Pilih Zonasi (Otomatis dari field ZONASI)",
            name="zone_value",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param_zone_val.filter.type = "ValueList"

        # 3. Parameter Pilihan Field Target (Nilai)
        param_field = arcpy.Parameter(
            displayName="Field Nilai yang Dicek",
            name="target_field",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param_field.filter.type = "ValueList"
        param_field.filter.list = ["NILAIBD_LAMA", "NILAIBD"]
        param_field.value = "NILAIBD_LAMA"

        # 4. Parameter Radius
        param_radius = arcpy.Parameter(
            displayName="Radius Pencarian",
            name="radius",
            datatype="GPLinearUnit",
            parameterType="Required",
            direction="Input")
        param_radius.value = "100 Meters"

        # 5. Parameter Skip 0
        param_skip_zero = arcpy.Parameter(
            displayName="Abaikan Nilai 0 (Null otomatis diabaikan)",
            name="skip_zero",
            datatype="GPBoolean",
            parameterType="Required",
            direction="Input")
        param_skip_zero.value = True

        # 6. Parameter Batas Anomali
        param_threshold = arcpy.Parameter(
            displayName="Threshold Perbedaan (Berapa Kali Lipat)",
            name="threshold",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input")
        param_threshold.value = 2.0 

        return [param_in_fc, param_kelurahan, param_zone_val, param_field, param_radius, param_skip_zero, param_threshold]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        if parameters[0].value:
            in_fc = parameters[0].valueAsText
            kelurahan_val = parameters[1].valueAsText
            try:
                fields = [f.name.upper() for f in arcpy.ListFields(in_fc)]
                
                # Update List Kelurahan (WADMKD)
                if "WADMKD" in fields:
                    unique_kel = set()
                    with arcpy.da.SearchCursor(in_fc, ["WADMKD"]) as cursor:
                        for row in cursor:
                            if row[0] is not None:
                                unique_kel.add(str(row[0]))
                    if unique_kel:
                        parameters[1].filter.list = sorted(list(unique_kel))
                else:
                    parameters[1].filter.list = []

                # Update List Zonasi
                if "ZONASI" in fields:
                    where_clause = None
                    # Jika Kelurahan sudah dipilih, filter Zonasi yang tampil agar sesuai Kelurahan tersebut
                    if kelurahan_val:
                        kel_delim = arcpy.AddFieldDelimiters(in_fc, "WADMKD")
                        where_clause = f"{kel_delim} = '{kelurahan_val}'"
                        
                    unique_zone = set()
                    with arcpy.da.SearchCursor(in_fc, ["ZONASI"], where_clause=where_clause) as cursor:
                        for row in cursor:
                            if row[0] is not None:
                                unique_zone.add(str(row[0]))
                    
                    if unique_zone:
                        parameters[2].filter.list = sorted(list(unique_zone))
                else:
                    parameters[2].filter.list = []
            except:
                pass
        return

    def updateMessages(self, parameters):
        if parameters[0].value:
            in_fc = parameters[0].valueAsText
            try:
                fields = [f.name.upper() for f in arcpy.ListFields(in_fc)]
                missing_fields = []
                
                if "WADMKD" not in fields:
                    missing_fields.append("'WADMKD'")
                if "ZONASI" not in fields:
                    missing_fields.append("'ZONASI'")
                    
                if missing_fields:
                    param_msg = " dan ".join(missing_fields)
                    parameters[0].setErrorMessage(f"Layer input harus memiliki field {param_msg} agar tool ini bisa berfungsi.")
            except:
                pass
        return

    def execute(self, parameters, messages):
        in_fc = parameters[0].valueAsText
        chosen_kelurahan = parameters[1].valueAsText
        chosen_zone = parameters[2].valueAsText
        target_field = parameters[3].valueAsText
        radius = parameters[4].valueAsText
        skip_zero = parameters[5].value
        threshold = parameters[6].value

        desc = arcpy.Describe(in_fc)
        oid_field = desc.OIDFieldName
        
        # Pengecekan tipe data field untuk formasi SQL yang tepat
        zone_type = "String"
        kel_type = "String"
        for f in desc.fields:
            if f.name.upper() == "ZONASI":
                zone_type = f.type
            elif f.name.upper() == "WADMKD":
                kel_type = f.type
                
        zonasi_delim = arcpy.AddFieldDelimiters(in_fc, "ZONASI")
        kelurahan_delim = arcpy.AddFieldDelimiters(in_fc, "WADMKD")
        
        # Pembuatan Query Kelurahan
        if kel_type in ["String", "Guid", "GlobalID"]:
            kel_query = f"{kelurahan_delim} = '{chosen_kelurahan}'"
        else:
            kel_query = f"{kelurahan_delim} = {chosen_kelurahan}"

        # Pembuatan Query Zonasi
        if zone_type in ["String", "Guid", "GlobalID"]:
            zone_query = f"{zonasi_delim} = '{chosen_zone}'"
        else:
            zone_query = f"{zonasi_delim} = {chosen_zone}"

        # Gabungkan kedua Query
        where_clause = f"{kel_query} AND {zone_query}"

        temp_layer = "filtered_zone_layer"
        arcpy.management.MakeFeatureLayer(in_fc, temp_layer, where_clause)

        count = int(arcpy.management.GetCount(temp_layer)[0])
        if count == 0:
            arcpy.AddError(f"Tidak ada data valid untuk Kelurahan: {chosen_kelurahan} dan Zonasi: {chosen_zone}")
            return

        messages.addMessage(f"Membaca {count} fitur pada area Kelurahan: {chosen_kelurahan}, Zonasi: {chosen_zone}...")
        
        valid_data = {}
        with arcpy.da.SearchCursor(temp_layer, [oid_field, target_field]) as cursor:
            for row in cursor:
                oid = row[0]
                nilai = row[1]

                if nilai is None:
                    continue
                if skip_zero and (nilai == 0 or nilai == 0.0):
                    continue

                valid_data[oid] = float(nilai)

        if not valid_data:
            arcpy.AddError("Proses dibatalkan: Tidak ada nilai bidang yang valid (bukan Null/0) pada filter ini.")
            return

        messages.addMessage(f"Mencari tetangga dalam radius {radius} menggunakan Near Table...")
        temp_near = "memory\\near_temp_outlier"
        
        if arcpy.Exists(temp_near):
            arcpy.management.Delete(temp_near)

        arcpy.analysis.GenerateNearTable(
            in_features=temp_layer,
            near_features=temp_layer,
            out_table=temp_near,
            search_radius=radius,
            closest="ALL",
            closest_count=0
        )

        messages.addMessage("Menganalisis anomali nilai...")
        
        neighbors_dict = {}
        with arcpy.da.SearchCursor(temp_near, ["IN_FID", "NEAR_FID"]) as cursor:
            for row in cursor:
                t_fid = row[0]
                j_fid = row[1]
                if t_fid == j_fid:
                    continue
                if t_fid not in neighbors_dict:
                    neighbors_dict[t_fid] = []
                neighbors_dict[t_fid].append(j_fid)

        arcpy.management.Delete(temp_near)

        # Menggunakan List untuk menampung OID yang anomali
        anomaly_oids = []

        for t_fid, t_nilai in valid_data.items():
            if t_fid not in neighbors_dict:
                continue

            valid_neighbors = []
            for j_fid in neighbors_dict[t_fid]:
                if j_fid in valid_data:
                    valid_neighbors.append(valid_data[j_fid])

            if len(valid_neighbors) > 0:
                avg_nilai = sum(valid_neighbors) / len(valid_neighbors)
                
                if avg_nilai == 0:
                    continue

                max_val = max(t_nilai, avg_nilai)
                min_val = min(t_nilai, avg_nilai)
                
                rasio = (max_val / min_val) if min_val > 0 else float('inf')

                if rasio >= threshold:
                    anomaly_oids.append(t_fid)

        messages.addMessage(f"Ditemukan {len(anomaly_oids)} bidang anomali.")
        
        # Logika Seleksi Layer Asal
        if len(anomaly_oids) == 0:
            arcpy.management.SelectLayerByAttribute(in_fc, "CLEAR_SELECTION")
            messages.addMessage("Tidak ada anomali. Menghapus seleksi (jika ada).")
        else:
            messages.addMessage("Menyeleksi bidang anomali pada layer asal...")
            # Membuat format String untuk SQL IN Statement: misal "1, 5, 10, 15"
            oid_list_str = ",".join(map(str, anomaly_oids))
            selection_query = f"{oid_field} IN ({oid_list_str})"
            
            # Melakukan seleksi ke layer asli pengguna
            arcpy.management.SelectLayerByAttribute(in_fc, "NEW_SELECTION", selection_query)
            messages.addMessage(f"Selesai! Fitur anomali berhasil diseleksi.")

        # Bersihkan layer temp
        if arcpy.Exists(temp_layer):
            arcpy.management.Delete(temp_layer)

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