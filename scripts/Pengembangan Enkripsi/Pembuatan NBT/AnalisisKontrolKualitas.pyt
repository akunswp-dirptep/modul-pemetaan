import arcpy, os, sys, math, webbrowser, shlex
from datetime import datetime
script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from nbtutils import persil, constant


class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [Klaster_Persil,
                      Hitung_Koefisien_Variasi,
                      Periksa_Klaster_Berdasarkan_CoV,
                      Periksa_Prediksi_Ekstrim_Dalam_Cluster,
                      Outlier_Dalam_Klaster,
                      Periksa_Outlier_Dalam_Klaster]

class Klaster_Persil(object):
    def __init__(self):
        """Definisi tool Klaster Persil."""
        self.label = "Klaster Persil"
        self.description = (
            "Membentuk klaster persil berdasarkan zonasi dan kelas jalan dari Persil_Layer, "
            "serta menghitung No_Cluster dan No_Cluster_Outlier pada Persil_Prediksi."
        )
        self.canRunInBackground = False

        self.info_text = (
            "Tools ini akan mengelompokkan bidang tanah pada layer \n"
            "Persil_Prediksi berdasarkan kesamaan zonasi (ZONASI & S_ZONASI) \n"
            "dan kelas jalan (S_KLSJLN) untuk membentuk atribut No_Cluster \n"
            "dan No_Cluster_Outlier sebagai dasar kontrol kualitas penilaian.\n\n"
            "Direktorat Penilaian Tanah dan Ekonomi Pertanahan,\n"
            "Kementerian ATR/BPN.\n"
            "Tahun: {}".format(datetime.now().year)
        )

    def getParameterInfo(self):
        """Definisi parameter input dan output tool."""
        penjelasan = arcpy.Parameter(
            displayName="Informasi Tools",
            name="petunjuk",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )
        penjelasan.value = self.info_text

        param_persil = arcpy.Parameter(
            displayName="Persil Prediksi",
            name="in_persil_prediksi",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input"
        )

        out_persil = arcpy.Parameter(
            displayName="Persil Prediksi",
            name="out_persil_prediksi",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [penjelasan, param_persil, out_persil]

    def updateParameters(self, parameters):
        """Mengunci teks informasi dan mengisi otomatis path Persil_Prediksi."""
        if parameters[0].altered:
            parameters[0].value = self.info_text

        if not parameters[1].altered:
            try:
                configs = persil.get_config_values()
                dataset_path = configs["project_config"]["dataset_path"]
                parameters[1].value = os.path.join(dataset_path, "Persil_Prediksi")
            except Exception:
                pass
        return

    def _ambil_zonasi_dari_persil(self, persil_layer_path):
        """Mengambil pasangan unik {S_ZONASI: ZONASI} langsung dari Persil_Layer."""
        if not arcpy.Exists(persil_layer_path):
            arcpy.AddError("Feature class Persil_Layer tidak ditemukan: {}".format(persil_layer_path))
            raise arcpy.ExecuteError

        field_nama_zon = self._get_field_name(persil_layer_path, "ZONASI")
        field_skor_zon = self._get_field_name(persil_layer_path, "S_ZONASI")

        if not field_nama_zon or not field_skor_zon:
            arcpy.AddError("Field 'ZONASI' atau 'S_ZONASI' tidak ditemukan pada Persil_Layer.")
            raise arcpy.ExecuteError

        zondict = {}
        with arcpy.da.SearchCursor(persil_layer_path, [field_skor_zon, field_nama_zon]) as cursor:
            for skor_zon, nama_zon in cursor:
                if skor_zon is not None and nama_zon is not None:
                    nama_clean = str(nama_zon).strip()
                    if nama_clean and skor_zon not in zondict:
                        zondict[skor_zon] = nama_clean

        return zondict

    def _get_field_name(self, fc_path, target_name):
        """Mencari nama field asli secara case-insensitive."""
        field_map = {f.name.lower(): f.name for f in arcpy.ListFields(fc_path)}
        return field_map.get(target_name.lower())

    def _hapus_jika_ada(self, path):
        """Menghapus feature class, layer, atau tabel jika sudah ada."""
        if arcpy.Exists(path):
            arcpy.management.Delete(path)

    def _hapus_field_jika_ada(self, fc_path, daftar_field):
        """Menghapus field lama secara case-insensitive agar tidak terjadi duplikasi nama."""
        target_lower = {nama.lower() for nama in daftar_field}
        to_delete = [
            f.name for f in arcpy.ListFields(fc_path)
            if not f.required and f.name.lower() in target_lower
        ]
        if to_delete:
            arcpy.management.DeleteField(fc_path, to_delete)

    def execute(self, parameters, messages):
        """Logika utama yang dijalankan saat tool dieksekusi."""
        arcpy.AddMessage("== Proses dimulai ==")
        arcpy.env.overwriteOutput = True

        configs = persil.get_config_values()
        dataset_path = configs["project_config"]["dataset_path"]

        persil_layer_path = os.path.join(dataset_path, "Persil_Layer")
        persil_prediksi_path = parameters[1].valueAsText
        if not arcpy.Exists(persil_prediksi_path):
            arcpy.AddError("Feature class tidak ditemukan: {}".format(persil_prediksi_path))
            raise arcpy.ExecuteError

        # Validasi field wajib pada Persil_Prediksi
        field_zonasi = self._get_field_name(persil_prediksi_path, "S_ZONASI")
        field_kls_jln = self._get_field_name(persil_prediksi_path, "S_KLSJLN")
        field_id_bidang = self._get_field_name(persil_prediksi_path, "IDBIDANG")

        if not all([field_zonasi, field_kls_jln, field_id_bidang]):
            arcpy.AddError("Field wajib ('S_ZONASI', 'S_KLSJLN', atau 'IDBIDANG') tidak ditemukan pada Persil_Prediksi.")
            raise arcpy.ExecuteError

        arcpy.AddMessage("== Membaca daftar zonasi dari Persil_Layer ==")
        zondict = self._ambil_zonasi_dari_persil(persil_layer_path)
        if not zondict:
            arcpy.AddError("Data atribut 'ZONASI' dan 'S_ZONASI' pada Persil_Layer kosong.")
            raise arcpy.ExecuteError

        # Bersihkan field cluster lama pada Persil_Prediksi
        self._hapus_field_jika_ada(persil_prediksi_path, ["No_Cluster", "No_Cluster_Outlier"])

        arcpy.AddMessage("== Dissolve dan explode ==")
        persil_cluster_diss_path = os.path.join(dataset_path, "Persil_Cluster_Diss")
        persil_cluster_expl_path = os.path.join(dataset_path, "Persil_Cluster_Expl")

        self._hapus_jika_ada(persil_cluster_diss_path)
        self._hapus_jika_ada(persil_cluster_expl_path)

        arcpy.management.Dissolve(persil_prediksi_path, persil_cluster_diss_path, [field_zonasi, field_kls_jln])
        arcpy.management.MultipartToSinglepart(persil_cluster_diss_path, persil_cluster_expl_path)

        arcpy.AddMessage("== Proses masing-masing zonasi ==")
        temp_gdb = r"C:\PenilaianTanah\scripts\Pengembangan Enkripsi\nbtutils\temporary.gdb"
        if not arcpy.Exists(temp_gdb):
            temp_folder = os.path.dirname(temp_gdb)
            if not os.path.exists(temp_folder):
                os.makedirs(temp_folder)
            arcpy.management.CreateFileGDB(temp_folder, os.path.basename(temp_gdb))

        list_to_merge = []
        for s_zon, nama_zon in zondict.items():
            prefix_zon = "".join(ch for ch in nama_zon if ch.isalnum()) + "_"
            arcpy.AddMessage("== Proses zonasi: {} (Skor: {}) ==".format(nama_zon, s_zon))

            zonasi_path = os.path.join(dataset_path, prefix_zon)
            zonasi_aggr_path = os.path.join(temp_gdb, prefix_zon + "aggr")
            zonasi_aggr_tbl_path = os.path.join(temp_gdb, prefix_zon + "aggr_Tbl")

            for item in [zonasi_path, zonasi_aggr_path, zonasi_aggr_tbl_path]:
                self._hapus_jika_ada(item)

            lyr_zon = arcpy.management.MakeFeatureLayer(
                persil_cluster_expl_path,
                "lyr_" + prefix_zon,
                "{} = {}".format(field_zonasi, s_zon)
            ).getOutput(0)

            row_count = int(arcpy.management.GetCount(lyr_zon).getOutput(0))
            arcpy.AddMessage("Jumlah poligon: {}".format(row_count))

            if row_count > 0:
                arcpy.management.CopyFeatures(lyr_zon, zonasi_path)
                arcpy.cartography.AggregatePolygons(zonasi_path, zonasi_aggr_path, "30 Meters")
                list_to_merge.append(zonasi_aggr_path)

            self._hapus_jika_ada(lyr_zon)
            self._hapus_jika_ada(zonasi_path)

        if not list_to_merge:
            arcpy.AddError("Tidak ada poligon zonasi yang memenuhi kriteria untuk digabungkan.")
            raise arcpy.ExecuteError

        arcpy.AddMessage("== Merge hasil agregasi zonasi ==")
        merge_aggr = os.path.join(dataset_path, "zonasi_aggr_merge")
        self._hapus_jika_ada(merge_aggr)
        arcpy.management.Merge(list_to_merge, merge_aggr)

        arcpy.AddMessage("== Tambah No_Cluster ==")
        oid_merge = arcpy.Describe(merge_aggr).OIDFieldName
        arcpy.management.AddField(merge_aggr, "No_Cluster", "LONG")
        arcpy.management.CalculateField(merge_aggr, "No_Cluster", "!{}!".format(oid_merge), "PYTHON3")

        # Buat centroid dalam persil dan sisakan field IDBIDANG
        persil_centroid_path = os.path.join(dataset_path, "Persil_Cluster_Centroid")
        self._hapus_jika_ada(persil_centroid_path)
        arcpy.management.FeatureToPoint(persil_prediksi_path, persil_centroid_path, "INSIDE")

        arcpy.AddMessage("== Hapus field centroid yang tidak dipakai ==")
        unused_fields = [
            f.name for f in arcpy.ListFields(persil_centroid_path)
            if not f.required and f.name.lower() != field_id_bidang.lower() and "shape" not in f.name.lower()
        ]
        if unused_fields:
            arcpy.management.DeleteField(persil_centroid_path, unused_fields)

        temp_identity = os.path.join(dataset_path, "zonasi_merge_identity")
        self._hapus_jika_ada(temp_identity)
        arcpy.analysis.Identity(persil_centroid_path, merge_aggr, temp_identity, "ALL")

        arcpy.AddMessage("== Join No_Cluster ke Persil_Prediksi ==")
        arcpy.management.JoinField(
            persil_prediksi_path, field_id_bidang, temp_identity, field_id_bidang, ["No_Cluster"]
        )

        arcpy.AddMessage("== Proses No_Cluster_Outlier (Multivariate Clustering) ==")
        output_mc = os.path.join(dataset_path, "output_multivariate_clustering")
        self._hapus_jika_ada(output_mc)

        arcpy.stats.MultivariateClustering(
            persil_prediksi_path, output_mc, [field_zonasi, field_kls_jln]
        )

        for target_fc in [persil_prediksi_path, persil_cluster_diss_path]:
            self._hapus_field_jika_ada(target_fc, ["No_Cluster_Outlier", "cluster_id"])
            oid_target = arcpy.Describe(target_fc).OIDFieldName
            arcpy.management.AddField(target_fc, "No_Cluster_Outlier", "LONG")
            arcpy.management.JoinField(target_fc, oid_target, output_mc, "SOURCE_ID", ["CLUSTER_ID"])
            arcpy.management.CalculateField(target_fc, "No_Cluster_Outlier", "!CLUSTER_ID!", "PYTHON3")
            arcpy.management.DeleteField(target_fc, ["CLUSTER_ID"])

        # Hapus feature class perantara yang tidak lagi dibutuhkan
        for temp_fc in [persil_cluster_expl_path, merge_aggr, persil_centroid_path, temp_identity, output_mc]:
            self._hapus_jika_ada(temp_fc)

        arcpy.AddMessage("== Proses finishing ==")
        lyr_output = arcpy.management.MakeFeatureLayer(persil_prediksi_path, "Persil_Prediksi").getOutput(0)
        arcpy.SetParameter(2, lyr_output)

        arcpy.AddMessage("== Proses Selesai ==")

class Hitung_Koefisien_Variasi(object):
    def __init__(self):
        """Definisi tool Hitung Koefisien Variasi."""
        self.label = "Hitung Koefisien Variasi"
        self.description = (
            "Menghitung nilai Koefisien Variasi (CoV), standar deviasi, rata-rata, "
            "dan simpangan prediksi per klaster pada Persil_Prediksi."
        )
        self.canRunInBackground = False

        self.info_text = (
            "Tools ini akan menghitung nilai Koefisien Variasi (Koef_Var), \n"
            "rata-rata (MEAN_Predicted), standar deviasi (STD_Predicted), \n"
            "dan simpangan nilai prediksi (Simpang) berdasarkan No_Cluster \n"
            "pada layer Persil_Prediksi.\n\n"
            "Direktorat Penilaian Tanah dan Ekonomi Pertanahan,\n"
            "Kementerian ATR/BPN.\n"
            "Tahun: {}".format(datetime.now().year)
        )

    def getParameterInfo(self):
        """Definisi parameter input dan output tool."""
        penjelasan = arcpy.Parameter(
            displayName="Informasi Tools",
            name="petunjuk",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )
        penjelasan.value = self.info_text

        param_persil = arcpy.Parameter(
            displayName="Persil Prediksi",
            name="in_persil_prediksi",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input"
        )

        out_persil = arcpy.Parameter(
            displayName="Persil Prediksi",
            name="out_persil_prediksi",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [penjelasan, param_persil, out_persil]

    def updateParameters(self, parameters):
        """Mengunci teks informasi dan mengisi otomatis path Persil_Prediksi."""
        if parameters[0].altered:
            parameters[0].value = self.info_text

        if not parameters[1].altered:
            try:
                configs = persil.get_config_values()
                dataset_path = configs["project_config"]["dataset_path"]
                parameters[1].value = os.path.join(dataset_path, "Persil_Prediksi")
            except Exception:
                pass
        return

    def _get_field_name(self, fc_path, target_name):
        """Mencari nama field asli secara case-insensitive."""
        field_map = {f.name.lower(): f.name for f in arcpy.ListFields(fc_path)}
        return field_map.get(target_name.lower())

    def _hapus_jika_ada(self, path):
        """Menghapus feature class, layer, atau tabel jika sudah ada."""
        if arcpy.Exists(path):
            arcpy.management.Delete(path)

    def _hapus_field_jika_ada(self, fc_path, daftar_field):
        """Menghapus field lama secara case-insensitive agar tidak terjadi duplikasi nama."""
        target_lower = {nama.lower() for nama in daftar_field}
        to_delete = [
            f.name for f in arcpy.ListFields(fc_path)
            if not f.required and f.name.lower() in target_lower
        ]
        if to_delete:
            arcpy.management.DeleteField(fc_path, to_delete)

    def execute(self, parameters, messages):
        """Logika utama yang dijalankan saat tool dieksekusi."""
        arcpy.AddMessage("== Proses dimulai ==")
        arcpy.env.overwriteOutput = True

        configs = persil.get_config_values()
        dataset_path = configs["project_config"]["dataset_path"]

        persil_prediksi_path = parameters[1].valueAsText
        if not arcpy.Exists(persil_prediksi_path):
            arcpy.AddError("Feature class tidak ditemukan: {}".format(persil_prediksi_path))
            raise arcpy.ExecuteError

        # Validasi field wajib pada Persil_Prediksi
        field_no_cluster = self._get_field_name(persil_prediksi_path, "No_Cluster")
        field_predicted = self._get_field_name(persil_prediksi_path, "Predicted")

        if not field_no_cluster or not field_predicted:
            arcpy.AddError(
                "Field wajib ('No_Cluster' atau 'Predicted') tidak ditemukan pada Persil_Prediksi. "
                "Pastikan proses GWR dan Klaster Persil sudah dijalankan."
            )
            raise arcpy.ExecuteError

        arcpy.AddMessage("== Hitung Koefisien Variasi per Klaster ==")
        persil_cluster_diss_path = os.path.join(dataset_path, "PersilClusterDiss")
        self._hapus_jika_ada(persil_cluster_diss_path)

        arcpy.management.Dissolve(
            in_features=persil_prediksi_path,
            out_feature_class=persil_cluster_diss_path,
            dissolve_field=[field_no_cluster],
            statistics_fields=[[field_predicted, "STD"], [field_predicted, "MEAN"]]
        )

        std_field = self._get_field_name(persil_cluster_diss_path, "STD_" + field_predicted)
        mean_field = self._get_field_name(persil_cluster_diss_path, "MEAN_" + field_predicted)

        arcpy.management.AddField(persil_cluster_diss_path, "Koef_Var", "DOUBLE")

        with arcpy.da.UpdateCursor(persil_cluster_diss_path, [std_field, mean_field, "Koef_Var"]) as cursor:
            for row in cursor:
                std_val, mean_val = row[0], row[1]
                if mean_val is not None and mean_val != 0:
                    # Jika klaster hanya terdiri dari 1 bidang, STD bernilai None sehingga CoV = 0
                    std_aman = std_val if std_val is not None else 0.0
                    row[2] = (std_aman / float(mean_val)) * 100.0
                    cursor.updateRow(row)

        arcpy.AddMessage("== Gabungkan hasil CoV dan hitung Simpang ke Persil_Prediksi ==")
        self._hapus_field_jika_ada(
            persil_prediksi_path, ["Koef_Var", "Simpang", std_field, mean_field]
        )

        arcpy.management.JoinField(
            in_data=persil_prediksi_path,
            in_field=field_no_cluster,
            join_table=persil_cluster_diss_path,
            join_field=field_no_cluster,
            fields=["Koef_Var", std_field, mean_field]
        )

        arcpy.management.AddField(persil_prediksi_path, "Simpang", "DOUBLE")

        with arcpy.da.UpdateCursor(persil_prediksi_path, [mean_field, field_predicted, "Simpang"]) as cursor:
            for row in cursor:
                mean_val, pred_val = row[0], row[1]
                if mean_val is not None and pred_val is not None:
                    row[2] = abs(mean_val - pred_val)
                    cursor.updateRow(row)

        arcpy.AddMessage("== Proses finishing ==")
        lyr_output = arcpy.management.MakeFeatureLayer(persil_prediksi_path, "Persil_Prediksi").getOutput(0)
        arcpy.SetParameter(2, lyr_output)

        arcpy.AddMessage("== Proses Selesai ==")

class Periksa_Klaster_Berdasarkan_CoV(object):
    def __init__(self):
        """Definisi tool Periksa Cluster Berdasarkan CoV."""
        self.label = "Periksa Klaster Berdasarkan CoV"
        self.description = (
            "Memeriksa nilai Koefisien Variasi (Koef_Var) pada Persil_Prediksi "
            "dengan batas toleransi <= 30% dan menampilkan layer hasil klasifikasi CoV."
        )
        self.canRunInBackground = False

        self.info_text = (
            "Tools ini akan memeriksa nilai Koefisien Variasi (Koef_Var) \n"
            "pada layer Persil_Prediksi (batas toleransi <= 30%), \n"
            "mengisi status kelayakan pada kolom sim_cov, serta \n"
            "menampilkan layer hasil klasifikasi Persil_Prediksi_CoV.\n\n"
            "Direktorat Penilaian Tanah dan Ekonomi Pertanahan,\n"
            "Kementerian ATR/BPN.\n"
            "Tahun: {}".format(datetime.now().year)
        )

    def getParameterInfo(self):
        """Definisi parameter input dan output tool."""
        penjelasan = arcpy.Parameter(
            displayName="Informasi Tools",
            name="petunjuk",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )
        penjelasan.value = self.info_text

        param_persil = arcpy.Parameter(
            displayName="Persil Prediksi",
            name="in_persil_prediksi",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input"
        )

        out_persil_cov = arcpy.Parameter(
            displayName="Persil Prediksi CoV",
            name="out_persil_prediksi_cov",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [penjelasan, param_persil, out_persil_cov]

    def updateParameters(self, parameters):
        """Mengunci teks informasi dan mengisi otomatis path Persil_Prediksi."""
        if parameters[0].altered:
            parameters[0].value = self.info_text

        if not parameters[1].altered:
            try:
                configs = persil.get_config_values()
                dataset_path = configs["project_config"]["dataset_path"]
                parameters[1].value = os.path.join(dataset_path, "Persil_Prediksi")
            except Exception:
                pass
        return

    def _get_field_name(self, fc_path, target_name):
        """Mencari nama field asli secara case-insensitive."""
        field_map = {f.name.lower(): f.name for f in arcpy.ListFields(fc_path)}
        return field_map.get(target_name.lower())

    def _cari_file_simbologi(self, project_cfg, nama_dasar):
        """Mencari file simbologi (.lyrx atau .lyr) pada direktori konfigurasi sistem."""
        kandidat_folder = [
            project_cfg.get("sys_path"),
            project_cfg.get("appdata"),
            os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
            r"C:\PenilaianTanah\scripts\Pengembangan Enkripsi\nbtutils"
        ]
        for folder in kandidat_folder:
            if not folder:
                continue
            for ekstensi in (".lyrx", ".lyr"):
                path_lyr = os.path.join(folder, nama_dasar + ekstensi)
                if os.path.exists(path_lyr):
                    return path_lyr
        return None

    def execute(self, parameters, messages):
        """Logika utama yang dijalankan saat tool dieksekusi."""
        arcpy.AddMessage("== Proses dimulai ==")
        arcpy.env.overwriteOutput = True

        configs = persil.get_config_values()
        project_cfg = configs["project_config"]

        persil_prediksi_path = parameters[1].valueAsText
        if not arcpy.Exists(persil_prediksi_path):
            arcpy.AddError("Feature class tidak ditemukan: {}".format(persil_prediksi_path))
            raise arcpy.ExecuteError

        # Validasi field Koef_Var pada Persil_Prediksi
        field_koef_var = self._get_field_name(persil_prediksi_path, "Koef_Var")
        if not field_koef_var:
            arcpy.AddError(
                "Field 'Koef_Var' tidak ditemukan pada Persil_Prediksi. "
                "Pastikan proses Hitung Koefisien Variasi sudah dijalankan."
            )
            raise arcpy.ExecuteError

        # Tambahkan field sim_cov jika belum ada
        field_sim_cov = self._get_field_name(persil_prediksi_path, "sim_cov")
        if not field_sim_cov:
            arcpy.management.AddField(persil_prediksi_path, "sim_cov", "TEXT", field_length=10)
            field_sim_cov = "sim_cov"

        arcpy.AddMessage("== Klasifikasi status CoV (Batas <= 30%) ==")
        with arcpy.da.UpdateCursor(persil_prediksi_path, [field_koef_var, field_sim_cov]) as cursor:
            for row in cursor:
                cov_val = row[0]
                row[1] = "0" if (cov_val is not None and cov_val <= 30) else "1"
                cursor.updateRow(row)

        arcpy.AddMessage("== Membuat layer dan menerapkan simbologi CoV ==")
        lyr_output = arcpy.management.MakeFeatureLayer(
            persil_prediksi_path, "Persil_Prediksi_CoV"
        ).getOutput(0)

        simbologi_path = self._cari_file_simbologi(project_cfg, "SimbologiCoV")
        if simbologi_path:
            arcpy.management.ApplySymbologyFromLayer(lyr_output, simbologi_path)
        else:
            arcpy.AddWarning(
                "File simbologi 'SimbologiCoV.lyrx/.lyr' tidak ditemukan; "
                "layer ditampilkan dengan simbologi default."
            )

        arcpy.SetParameter(2, lyr_output)
        arcpy.AddMessage("== Proses Selesai ==")

class Periksa_Prediksi_Ekstrim_Dalam_Cluster(object):
    def __init__(self):
        """Definisi tool Periksa Prediksi Ekstrim Dalam Cluster."""
        self.label = "Periksa Prediksi Ekstrim Dalam Cluster"
        self.description = (
            "Memeriksa rasio simpangan terhadap rata-rata prediksi (Simpang / MEAN_Predicted > 0.3) "
            "pada Persil_Prediksi dan menampilkan layer hasil klasifikasi prediksi ekstrim."
        )
        self.canRunInBackground = False

        self.info_text = (
            "Tools ini akan memeriksa nilai prediksi ekstrim dalam klaster \n"
            "pada layer Persil_Prediksi berdasarkan rasio simpangan \n"
            "terhadap rata-rata klaster (> 30%), mengisi kolom sim_xtrm, \n"
            "serta menampilkan layer Persil_Prediksi_Ekstrim.\n\n"
            "Direktorat Penilaian Tanah dan Ekonomi Pertanahan,\n"
            "Kementerian ATR/BPN.\n"
            "Tahun: {}".format(datetime.now().year)
        )

    def getParameterInfo(self):
        """Definisi parameter input dan output tool."""
        penjelasan = arcpy.Parameter(
            displayName="Informasi Tools",
            name="petunjuk",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )
        penjelasan.value = self.info_text

        param_persil = arcpy.Parameter(
            displayName="Persil Prediksi",
            name="in_persil_prediksi",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input"
        )

        out_persil_ekstrim = arcpy.Parameter(
            displayName="Persil Prediksi Ekstrim",
            name="out_persil_prediksi_ekstrim",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [penjelasan, param_persil, out_persil_ekstrim]

    def updateParameters(self, parameters):
        """Mengunci teks informasi dan mengisi otomatis path Persil_Prediksi."""
        if parameters[0].altered:
            parameters[0].value = self.info_text

        if not parameters[1].altered:
            try:
                configs = persil.get_config_values()
                dataset_path = configs["project_config"]["dataset_path"]
                parameters[1].value = os.path.join(dataset_path, "Persil_Prediksi")
            except Exception:
                pass
        return

    def _get_field_name(self, fc_path, target_name):
        """Mencari nama field asli secara case-insensitive."""
        field_map = {f.name.lower(): f.name for f in arcpy.ListFields(fc_path)}
        return field_map.get(target_name.lower())

    def _cari_file_simbologi(self, project_cfg, nama_dasar):
        """Mencari file simbologi (.lyrx atau .lyr) pada direktori konfigurasi sistem."""
        kandidat_folder = [
            project_cfg.get("sys_path"),
            project_cfg.get("appdata"),
            os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
            r"C:\PenilaianTanah\scripts\Pengembangan Enkripsi\nbtutils"
        ]
        for folder in kandidat_folder:
            if not folder:
                continue
            for ekstensi in (".lyrx", ".lyr"):
                path_lyr = os.path.join(folder, nama_dasar + ekstensi)
                if os.path.exists(path_lyr):
                    return path_lyr
        return None

    def execute(self, parameters, messages):
        """Logika utama yang dijalankan saat tool dieksekusi."""
        arcpy.AddMessage("== Proses dimulai ==")
        arcpy.env.overwriteOutput = True

        configs = persil.get_config_values()
        project_cfg = configs["project_config"]

        persil_prediksi_path = parameters[1].valueAsText
        if not arcpy.Exists(persil_prediksi_path):
            arcpy.AddError("Feature class tidak ditemukan: {}".format(persil_prediksi_path))
            raise arcpy.ExecuteError

        # Validasi field wajib pada Persil_Prediksi
        field_simpang = self._get_field_name(persil_prediksi_path, "Simpang")
        field_mean = self._get_field_name(persil_prediksi_path, "MEAN_Predicted")

        if not field_simpang or not field_mean:
            arcpy.AddError(
                "Field wajib ('Simpang' atau 'MEAN_Predicted') tidak ditemukan pada Persil_Prediksi. "
                "Pastikan proses Hitung Koefisien Variasi sudah dijalankan."
            )
            raise arcpy.ExecuteError

        # Tambahkan field sim_xtrm jika belum ada
        field_sim_xtrm = self._get_field_name(persil_prediksi_path, "sim_xtrm")
        if not field_sim_xtrm:
            arcpy.management.AddField(persil_prediksi_path, "sim_xtrm", "TEXT", field_length=50)
            field_sim_xtrm = "sim_xtrm"

        arcpy.AddMessage("== Klasifikasi prediksi ekstrim dalam klaster ==")
        with arcpy.da.UpdateCursor(persil_prediksi_path, [field_simpang, field_mean, field_sim_xtrm]) as cursor:
            for row in cursor:
                simpang_val, mean_val = row[0], row[1]
                if simpang_val is not None and mean_val is not None and mean_val != 0:
                    rasio = simpang_val / float(mean_val)
                    row[2] = "Prediksi tinggi / rendah" if rasio > 0.3 else "Prediksi rata-rata"
                else:
                    row[2] = "Prediksi rata-rata"
                cursor.updateRow(row)

        arcpy.AddMessage("== Membuat layer dan menerapkan simbologi ekstrim ==")
        lyr_output = arcpy.management.MakeFeatureLayer(
            persil_prediksi_path, "Persil_Prediksi_Ekstrim"
        ).getOutput(0)

        simbologi_path = self._cari_file_simbologi(project_cfg, "SimbologiXtrm")
        if simbologi_path:
            arcpy.management.ApplySymbologyFromLayer(lyr_output, simbologi_path)
        else:
            arcpy.AddWarning(
                "File simbologi 'SimbologiXtrm.lyrx/.lyr' tidak ditemukan; "
                "layer ditampilkan dengan simbologi default."
            )

        arcpy.SetParameter(2, lyr_output)
        arcpy.AddMessage("== Proses Selesai ==")

class Outlier_Dalam_Klaster(object):
    def __init__(self):
        """Definisi tool Outlier Dalam Cluster (Anselin Local Moran's I)."""
        self.label = "Outlier Dalam Klaster"
        self.description = (
            "Mengidentifikasi outlier spasial dalam klaster menggunakan Anselin Local Moran's I "
            "pada Persil_Prediksi dan menyimpan hasilnya ke atribut oLMiIndex, oLMiZScore, oLMiPValue, dan oCOType."
        )
        self.canRunInBackground = False

        self.info_text = (
            "Tools ini akan menganalisis outlier spasial dalam klaster \n"
            "(Anselin Local Moran's I) berdasarkan atribut No_Cluster_Outlier \n"
            "pada layer Persil_Prediksi, menyimpan hasilnya ke kolom \n"
            "oLMiIndex, oLMiZScore, oLMiPValue, dan oCOType, serta \n"
            "menampilkan layer Persil_Prediksi_Outlier.\n\n"
            "Direktorat Penilaian Tanah dan Ekonomi Pertanahan,\n"
            "Kementerian ATR/BPN.\n"
            "Tahun: {}".format(datetime.now().year)
        )

    def getParameterInfo(self):
        """Definisi parameter input dan output tool."""
        penjelasan = arcpy.Parameter(
            displayName="Informasi Tools",
            name="petunjuk",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )
        penjelasan.value = self.info_text

        param_persil = arcpy.Parameter(
            displayName="Persil Prediksi",
            name="in_persil_prediksi",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input"
        )

        out_persil_outlier = arcpy.Parameter(
            displayName="Persil Prediksi Outlier",
            name="out_persil_prediksi_outlier",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [penjelasan, param_persil, out_persil_outlier]

    def updateParameters(self, parameters):
        """Mengunci teks informasi dan mengisi otomatis path Persil_Prediksi."""
        if parameters[0].altered:
            parameters[0].value = self.info_text

        if not parameters[1].altered:
            try:
                configs = persil.get_config_values()
                dataset_path = configs["project_config"]["dataset_path"]
                parameters[1].value = os.path.join(dataset_path, "Persil_Prediksi")
            except Exception:
                pass
        return

    def _get_field_name(self, fc_path, target_name):
        """Mencari nama field asli secara case-insensitive."""
        field_map = {f.name.lower(): f.name for f in arcpy.ListFields(fc_path)}
        return field_map.get(target_name.lower())

    def _hapus_jika_ada(self, path):
        """Menghapus feature class, layer, atau tabel jika sudah ada."""
        if arcpy.Exists(path):
            arcpy.management.Delete(path)

    def _hapus_field_jika_ada(self, fc_path, daftar_field):
        """Menghapus field secara case-insensitive agar tidak terjadi duplikasi nama."""
        target_lower = {nama.lower() for nama in daftar_field}
        to_delete = [
            f.name for f in arcpy.ListFields(fc_path)
            if not f.required and f.name.lower() in target_lower
        ]
        if to_delete:
            arcpy.management.DeleteField(fc_path, to_delete)

    def execute(self, parameters, messages):
        """Logika utama yang dijalankan saat tool dieksekusi."""
        arcpy.AddMessage("== Proses dimulai ==")
        arcpy.env.overwriteOutput = True

        in_fc = parameters[1].valueAsText
        if not arcpy.Exists(in_fc):
            arcpy.AddError("Feature class tidak ditemukan: {}".format(in_fc))
            raise arcpy.ExecuteError

        # Validasi field No_Cluster_Outlier pada Persil_Prediksi
        field_cluster_outlier = self._get_field_name(in_fc, "No_Cluster_Outlier")
        if not field_cluster_outlier:
            arcpy.AddError(
                "Field 'No_Cluster_Outlier' tidak ditemukan pada Persil_Prediksi. "
                "Pastikan proses Klaster Persil sudah dijalankan."
            )
            raise arcpy.ExecuteError

        temp_gdb_path = r"C:\PenilaianTanah\scripts\Pengembangan Enkripsi\nbtutils\temporary.gdb"
        if not arcpy.Exists(temp_gdb_path):
            temp_folder = os.path.dirname(temp_gdb_path)
            if not os.path.exists(temp_folder):
                os.makedirs(temp_folder)
            arcpy.management.CreateFileGDB(temp_folder, os.path.basename(temp_gdb_path))

        out_path = os.path.join(temp_gdb_path, "Persil_Prediksi_CO_MVC")
        self._hapus_jika_ada(out_path)

        arcpy.AddMessage("== Analisis Cluster and Outlier (Anselin Local Moran's I) ==")
        arcpy.stats.ClustersOutliers(
            in_fc,
            field_cluster_outlier,
            out_path,
            "CONTIGUITY_EDGES_CORNERS",
            "EUCLIDEAN_DISTANCE",
            "NONE"
        )

        # Pastikan tidak ada sisa field hasil join maupun field output lama sebelum JoinField
        temp_join_fields = ["LMiIndex", "LMiZScore", "LMiPValue", "COType"]
        target_fields = [
            ("oLMiIndex", "DOUBLE", None),
            ("oLMiZScore", "DOUBLE", None),
            ("oLMiPValue", "DOUBLE", None),
            ("oCOType", "TEXT", 10)
        ]
        self._hapus_field_jika_ada(in_fc, temp_join_fields + [f[0] for f in target_fields])

        oid_field = arcpy.Describe(in_fc).OIDFieldName
        arcpy.management.JoinField(in_fc, oid_field, out_path, "SOURCE_ID", temp_join_fields)

        for nama_field, tipe_field, panjang in target_fields:
            if panjang:
                arcpy.management.AddField(in_fc, nama_field, tipe_field, field_length=panjang)
            else:
                arcpy.management.AddField(in_fc, nama_field, tipe_field)

        arcpy.AddMessage("== Menyimpan hasil statistik outlier ke Persil_Prediksi ==")
        read_fields = temp_join_fields + [f[0] for f in target_fields]
        with arcpy.da.UpdateCursor(in_fc, read_fields) as cursor:
            for row in cursor:
                row[4] = row[0]  # oLMiIndex
                row[5] = row[1]  # oLMiZScore
                row[6] = row[2]  # oLMiPValue
                row[7] = row[3]  # oCOType
                cursor.updateRow(row)

        # Hapus field sementara hasil join dan feature class sementara di temporary.gdb
        self._hapus_field_jika_ada(in_fc, temp_join_fields)
        self._hapus_jika_ada(out_path)

        arcpy.AddMessage("== Menampilkan layer Persil_Prediksi_Outlier ==")
        lyr_output = arcpy.management.MakeFeatureLayer(in_fc, "Persil_Prediksi_Outlier").getOutput(0)
        arcpy.SetParameter(2, lyr_output)

        arcpy.AddMessage("== Proses Selesai ==")

class Periksa_Outlier_Dalam_Klaster(object):
    def __init__(self):
        """Definisi tool Periksa Outlier Dalam Klaster."""
        self.label = "Periksa Outlier Dalam Klaster"
        self.description = (
            "Mengklasifikasikan tipe outlier spasial (oCOType) pada Persil_Prediksi "
            "ke dalam atribut sim_type dan menampilkan layer hasil dengan simbologi outlier."
        )
        self.canRunInBackground = False

        self.info_text = (
            "Tools ini akan mengklasifikasikan kode tipe outlier (oCOType: \n"
            "HH, LL, HL, LH) pada layer Persil_Prediksi ke dalam kolom \n"
            "sim_type (kode 1 - 5), serta menampilkan layer hasil \n"
            "Persil_Prediksi_Outlier beserta simbologinya.\n\n"
            "Direktorat Penilaian Tanah dan Ekonomi Pertanahan,\n"
            "Kementerian ATR/BPN.\n"
            "Tahun: {}".format(datetime.now().year)
        )

    def getParameterInfo(self):
        """Definisi parameter input dan output tool."""
        penjelasan = arcpy.Parameter(
            displayName="Informasi Tools",
            name="petunjuk",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )
        penjelasan.value = self.info_text

        param_persil = arcpy.Parameter(
            displayName="Persil Prediksi",
            name="in_persil_prediksi",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input"
        )

        out_persil_outlier = arcpy.Parameter(
            displayName="Persil Prediksi Outlier",
            name="out_persil_prediksi_outlier",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [penjelasan, param_persil, out_persil_outlier]

    def updateParameters(self, parameters):
        """Mengunci teks informasi dan mengisi otomatis path Persil_Prediksi."""
        if parameters[0].altered:
            parameters[0].value = self.info_text

        if not parameters[1].altered:
            try:
                configs = persil.get_config_values()
                dataset_path = configs["project_config"]["dataset_path"]
                parameters[1].value = os.path.join(dataset_path, "Persil_Prediksi")
            except Exception:
                pass
        return

    def _get_field_name(self, fc_path, target_name):
        """Mencari nama field asli secara case-insensitive."""
        field_map = {f.name.lower(): f.name for f in arcpy.ListFields(fc_path)}
        return field_map.get(target_name.lower())

    def _cari_file_simbologi(self, project_cfg, nama_dasar):
        """Mencari file simbologi (.lyrx atau .lyr) pada direktori konfigurasi sistem."""
        kandidat_folder = [
            project_cfg.get("sys_path"),
            project_cfg.get("appdata"),
            os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
            r"C:\PenilaianTanah\scripts\Pengembangan Enkripsi\nbtutils"
        ]
        for folder in kandidat_folder:
            if not folder:
                continue
            for ekstensi in (".lyrx", ".lyr"):
                path_lyr = os.path.join(folder, nama_dasar + ekstensi)
                if os.path.exists(path_lyr):
                    return path_lyr
        return None

    def execute(self, parameters, messages):
        """Logika utama yang dijalankan saat tool dieksekusi."""
        arcpy.AddMessage("== Proses dimulai ==")
        arcpy.env.overwriteOutput = True

        configs = persil.get_config_values()
        project_cfg = configs["project_config"]

        persil_prediksi_path = parameters[1].valueAsText
        if not arcpy.Exists(persil_prediksi_path):
            arcpy.AddError("Feature class tidak ditemukan: {}".format(persil_prediksi_path))
            raise arcpy.ExecuteError

        # Validasi field oCOType pada Persil_Prediksi
        field_cotype = self._get_field_name(persil_prediksi_path, "oCOType")
        if not field_cotype:
            arcpy.AddError(
                "Field 'oCOType' tidak ditemukan pada Persil_Prediksi. "
                "Pastikan proses Outlier Dalam Cluster sudah dijalankan."
            )
            raise arcpy.ExecuteError

        # Tambahkan field sim_type jika belum ada
        field_sim_type = self._get_field_name(persil_prediksi_path, "sim_type")
        if not field_sim_type:
            arcpy.management.AddField(persil_prediksi_path, "sim_type", "TEXT", field_length=10)
            field_sim_type = "sim_type"

        arcpy.AddMessage("== Klasifikasi tipe outlier (oCOType -> sim_type) ==")
        mapping_cotype = {
            "HH": "1",
            "LL": "2",
            "HL": "3",
            "LH": "4"
        }

        with arcpy.da.UpdateCursor(persil_prediksi_path, [field_cotype, field_sim_type]) as cursor:
            for row in cursor:
                cotype_val = str(row[0]).strip().upper() if row[0] is not None else ""
                row[1] = mapping_cotype.get(cotype_val, "5")
                cursor.updateRow(row)

        arcpy.AddMessage("== Membuat layer dan menerapkan simbologi outlier ==")
        lyr_output = arcpy.management.MakeFeatureLayer(
            persil_prediksi_path, "Persil_Prediksi_Outlier"
        ).getOutput(0)

        simbologi_path = self._cari_file_simbologi(project_cfg, "SimbologiOutlier")
        if simbologi_path:
            arcpy.management.ApplySymbologyFromLayer(lyr_output, simbologi_path)
        else:
            arcpy.AddWarning(
                "File simbologi 'SimbologiOutlier.lyrx/.lyr' tidak ditemukan; "
                "layer ditampilkan dengan simbologi default."
            )

        arcpy.SetParameter(2, lyr_output)
        arcpy.AddMessage("== Proses Selesai ==")