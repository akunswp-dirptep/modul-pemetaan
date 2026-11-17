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
        self.tools = [Prediksi_Nilai_Tanah_GWR_Populasi,
                      Klaster_Persil,
                      Hitung_Koefisien_Variasi,
                      Periksa_Klaster_Berdasarkan_CoV,
                      Periksa_Prediksi_Ekstrim_Dalam_Cluster,
                      Outlier_Dalam_Klaster,
                      Periksa_Outlier_Dalam_Klaster]


class Prediksi_Nilai_Tanah_GWR_Populasi(object):
    def __init__(self):
        """Definisi tool Prediksi Nilai Tanah (GWR & Interpolasi Koefisien)."""
        self.label = "Prediksi Nilai Tanah (GWR & EBK)"
        self.description = (
            "Menjalankan pemodelan GWR pada Persil_Sampel dan Persil_Layer, "
            "menginterpolasi koefisien lokal dengan Empirical Bayesian Kriging, "
            "serta menghasilkan Persil_Prediksi dan Sampel_Prediksi."
        )
        self.canRunInBackground = False

        self.info_text = (
            "Tools ini akan menjalankan pemodelan GWR pada Persil_Sampel \n"
            "dan Persil_Layer, melakukan interpolasi koefisien lokal (C_*) \n"
            "menggunakan Empirical Bayesian Kriging, serta menyimpan \n"
            "hasilnya ke dalam Persil_Prediksi dan Sampel_Prediksi.\n\n"
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

        param_sample = arcpy.Parameter(
            displayName="Persil Sampel",
            name="sample",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input"
        )

        param_population = arcpy.Parameter(
            displayName="Persil Layer",
            name="population",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input"
        )

        param_exp_var = arcpy.Parameter(
            displayName="Variabel Prediksi",
            name="explanatory_fields",
            datatype="Field",
            parameterType="Required",
            direction="Input",
            multiValue=True
        )
        param_exp_var.parameterDependencies = [param_sample.name]

        param_match_var = arcpy.Parameter(
            displayName="Pasangan Variabel Persil (Opsional jika nama field sama)",
            name="explanatory_variables_to_match",
            datatype="GPValueTable",
            parameterType="Optional",
            direction="Input"
        )
        param_match_var.columns = [["GPString", "Variabel Sampel"], ["GPString", "Variabel Persil"]]

        param_nb_type = arcpy.Parameter(
            displayName="Tipe Ketetanggaan (Neighborhood Type)",
            name="neighborhood_type",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        param_nb_type.filter.type = "ValueList"
        param_nb_type.filter.list = ["NUMBER_OF_NEIGHBORS", "DISTANCE_BAND"]
        param_nb_type.value = "NUMBER_OF_NEIGHBORS"

        param_nb_method = arcpy.Parameter(
            displayName="Metode Pemilihan Ketetanggaan",
            name="neighborhood_selection_method",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        param_nb_method.filter.type = "ValueList"
        param_nb_method.filter.list = ["GOLDEN_SEARCH", "MANUAL_INTERVALS", "USER_DEFINED"]
        param_nb_method.value = "GOLDEN_SEARCH"

        param_min_nb = arcpy.Parameter(
            displayName="Minimum Jumlah Tetangga",
            name="minimum_number_of_neighbors",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input"
        )

        param_max_nb = arcpy.Parameter(
            displayName="Maksimum Jumlah Tetangga",
            name="maximum_number_of_neighbors",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input"
        )

        param_min_dist = arcpy.Parameter(
            displayName="Minimum Jarak Pencarian",
            name="minimum_search_distance",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input"
        )

        param_max_dist = arcpy.Parameter(
            displayName="Maksimum Jarak Pencarian",
            name="maximum_search_distance",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input"
        )

        param_nb_inc = arcpy.Parameter(
            displayName="Increment Jumlah Tetangga",
            name="number_of_neighbors_increment",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input"
        )

        param_dist_inc = arcpy.Parameter(
            displayName="Increment Jarak Pencarian",
            name="search_distance_increment",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input"
        )

        param_num_inc = arcpy.Parameter(
            displayName="Jumlah Increment",
            name="number_of_increments",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input"
        )

        param_num_nb = arcpy.Parameter(
            displayName="Jumlah Tetangga (User Defined)",
            name="number_of_neighbors",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input"
        )

        param_dist_band = arcpy.Parameter(
            displayName="Jarak Band (User Defined)",
            name="distance_band",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input"
        )

        param_weight = arcpy.Parameter(
            displayName="Skema Pembobotan Lokal",
            name="local_weighting_scheme",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )
        param_weight.filter.type = "ValueList"
        param_weight.filter.list = ["GAUSSIAN", "BISQUARE"]
        param_weight.value = "GAUSSIAN"

        out_persil_prediksi = arcpy.Parameter(
            displayName="Persil Prediksi",
            name="out_persil_prediksi",
            datatype="DEFeatureClass",
            parameterType="Derived",
            direction="Output"
        )

        out_sampel_prediksi = arcpy.Parameter(
            displayName="Sampel Prediksi",
            name="out_sampel_prediksi",
            datatype="DEFeatureClass",
            parameterType="Derived",
            direction="Output"
        )

        return [
            penjelasan,
            param_sample,
            param_population,
            param_exp_var,
            param_match_var,
            param_nb_type,
            param_nb_method,
            param_min_nb,
            param_max_nb,
            param_min_dist,
            param_max_dist,
            param_nb_inc,
            param_dist_inc,
            param_num_inc,
            param_num_nb,
            param_dist_band,
            param_weight,
            out_persil_prediksi,
            out_sampel_prediksi
        ]

    def updateParameters(self, parameters):
        """Mengunci teks informasi, mengisi path default, variabel otomatis, dan visibilitas parameter."""
        if parameters[0].altered:
            parameters[0].value = self.info_text

        try:
            configs = persil.get_config_values()
            project_cfg = configs["project_config"]
            dataset_path = project_cfg["dataset_path"]
            gdb_path = project_cfg.get("gdb_path") or os.path.dirname(dataset_path)

            if not parameters[1].altered:
                parameters[1].value = os.path.join(dataset_path, "Persil_Sampel")

            if not parameters[2].altered:
                parameters[2].value = os.path.join(dataset_path, "Persil_Layer")

            # Otomatis isi variabel prediksi dari tabel VariabelReady jika tersedia
            if not parameters[3].altered and parameters[1].value:
                vready_path = os.path.join(gdb_path, "VariabelReady")
                if arcpy.Exists(vready_path) and arcpy.Exists(parameters[1].valueAsText):
                    sample_fields = {f.name.lower(): f.name for f in arcpy.ListFields(parameters[1].valueAsText)}
                    vars_ready = []
                    with arcpy.da.SearchCursor(vready_path, ["variable"]) as cursor:
                        for row in cursor:
                            if row[0] and row[0].lower() in sample_fields:
                                vars_ready.append(sample_fields[row[0].lower()])
                    if vars_ready:
                        parameters[3].values = vars_ready
        except Exception:
            pass

        # Atur visibilitas parameter ketetanggaan sesuai pilihan
        nb_type = parameters[5].valueAsText
        nb_method = parameters[6].valueAsText

        is_num = (nb_type == "NUMBER_OF_NEIGHBORS")
        is_dist = (nb_type == "DISTANCE_BAND")
        is_golden = (nb_method == "GOLDEN_SEARCH")
        is_manual = (nb_method == "MANUAL_INTERVALS")
        is_user = (nb_method == "USER_DEFINED")

        parameters[7].enabled = is_num and (is_golden or is_manual)    # minimum_number_of_neighbors
        parameters[8].enabled = is_num and is_golden                    # maximum_number_of_neighbors
        parameters[9].enabled = is_dist and (is_golden or is_manual)   # minimum_search_distance
        parameters[10].enabled = is_dist and is_golden                  # maximum_search_distance
        parameters[11].enabled = is_num and is_manual                   # number_of_neighbors_increment
        parameters[12].enabled = is_dist and is_manual                  # search_distance_increment
        parameters[13].enabled = is_manual                              # number_of_increments
        parameters[14].enabled = is_num and is_user                     # number_of_neighbors
        parameters[15].enabled = is_dist and is_user                    # distance_band
        return

    def _get_field_name(self, fc_path, target_name):
        """Mencari nama field asli secara case-insensitive."""
        field_map = {f.name.lower(): f.name for f in arcpy.ListFields(fc_path)}
        return field_map.get(target_name.lower())

    def _hapus_jika_ada(self, path):
        """Menghapus feature class atau raster jika sudah ada."""
        if arcpy.Exists(path):
            arcpy.management.Delete(path)

    def _hapus_field_lama(self, fc_path, daftar_target, prefix=None):
        """Menghapus field lama sebelum JoinField agar tidak terjadi duplikasi nama (_1)."""
        existing = arcpy.ListFields(fc_path)
        target_lower = {t.lower() for t in daftar_target}
        to_delete = []
        for f in existing:
            if f.required:
                continue
            if f.name.lower() in target_lower:
                to_delete.append(f.name)
            elif prefix and f.name.lower().startswith(prefix.lower()):
                to_delete.append(f.name)
        if to_delete:
            arcpy.management.DeleteField(fc_path, to_delete)

    def execute(self, parameters, messages):
        """Logika utama yang dijalankan saat tool dieksekusi."""
        arcpy.AddMessage("== Proses dimulai ==")
        arcpy.env.overwriteOutput = True

        # Cek ketersediaan lisensi Geostatistical Analyst & Spatial Analyst
        for ext, nama_ext in [("GeoStats", "Geostatistical Analyst"), ("Spatial", "Spatial Analyst")]:
            if arcpy.CheckExtension(ext) == "Available":
                arcpy.CheckOutExtension(ext)
            else:
                arcpy.AddError("Ekstensi {} tidak tersedia atau belum aktif.".format(nama_ext))
                raise arcpy.ExecuteError

        configs = persil.get_config_values()
        project_cfg = configs["project_config"]
        dataset_path = project_cfg["dataset_path"]
        gdb_path = project_cfg.get("gdb_path") or os.path.dirname(dataset_path)

        sample_path = parameters[1].valueAsText
        population_path = parameters[2].valueAsText
        explanatory_fields = parameters[3].valueAsText
        match_table = parameters[4].values
        neighborhood_type = parameters[5].valueAsText
        neighborhood_selection_method = parameters[6].valueAsText

        min_neighbors = parameters[7].value if parameters[7].enabled else None
        max_neighbors = parameters[8].value if parameters[8].enabled else None
        min_distance = parameters[9].value if parameters[9].enabled else None
        max_distance = parameters[10].value if parameters[10].enabled else None
        neighbors_inc = parameters[11].value if parameters[11].enabled else None
        distance_inc = parameters[12].value if parameters[12].enabled else None
        num_inc = parameters[13].value if parameters[13].enabled else None
        num_neighbors = parameters[14].value if parameters[14].enabled else None
        distance_band = parameters[15].value if parameters[15].enabled else None
        local_weighting_scheme = parameters[16].valueAsText or "GAUSSIAN"

        field_nilai = self._get_field_name(sample_path, "nilai")
        if not field_nilai:
            arcpy.AddError("Field 'nilai' tidak ditemukan pada {}.".format(sample_path))
            raise arcpy.ExecuteError

        # Pasangkan variabel prediksi antara Persil_Sampel dan Persil_Layer secara otomatis
        if match_table:
            vars_to_match = match_table
        else:
            vars_to_match = []
            for var_s in [v.strip() for v in explanatory_fields.split(";") if v.strip()]:
                var_p = self._get_field_name(population_path, var_s)
                if not var_p:
                    arcpy.AddError(
                        "Field variabel '{}' tidak ditemukan pada Persil_Layer ({}). "
                        "Pastikan Transformasi Variabel sudah dijalankan pada kedua layer.".format(var_s, population_path)
                    )
                    raise arcpy.ExecuteError
                vars_to_match.append([var_s, var_p])

        # Bersihkan data sementara & raster koefisien lama di GDB
        arcpy.AddMessage("=== Membersihkan data sementara lama ===")
        old_workspace = arcpy.env.workspace
        arcpy.env.workspace = gdb_path
        for raster_lama in (arcpy.ListRasters("C_*") or []):
            self._hapus_jika_ada(os.path.join(gdb_path, raster_lama))
        for fc_lama in (arcpy.ListFeatureClasses("Hasil_GWR_*") or []):
            self._hapus_jika_ada(os.path.join(gdb_path, fc_lama))
        arcpy.env.workspace = old_workspace

        out_sample_gwr = os.path.join(gdb_path, "Hasil_GWR_Sampel")
        out_pred_gwr = os.path.join(gdb_path, "Hasil_GWR_Persil")
        poin_persil = os.path.join(gdb_path, "PoinPersil")
        persil_prediksi = os.path.join(dataset_path, "Persil_Prediksi")
        sampel_prediksi = os.path.join(dataset_path, "Sampel_Prediksi")

        for item in [out_sample_gwr, out_pred_gwr, poin_persil, persil_prediksi, sampel_prediksi]:
            self._hapus_jika_ada(item)

        # 1. Jalankan GWR
        arcpy.AddMessage("=== Menjalankan GWR ===")
        if neighborhood_type == "NUMBER_OF_NEIGHBORS" and neighborhood_selection_method == "GOLDEN_SEARCH":
            if min_neighbors is None:
                min_neighbors = 30
                arcpy.AddMessage("Minimum Jumlah Tetangga kosong, otomatis menggunakan nilai default: 30.")

        try:
            arcpy.stats.GWR(
                in_features=sample_path,
                dependent_variable=field_nilai,
                model_type="CONTINUOUS",
                explanatory_variables=explanatory_fields,
                output_features=out_sample_gwr,
                neighborhood_type=neighborhood_type,
                neighborhood_selection_method=neighborhood_selection_method,
                minimum_number_of_neighbors=min_neighbors,
                maximum_number_of_neighbors=max_neighbors,
                minimum_search_distance=min_distance,
                maximum_search_distance=max_distance,
                number_of_neighbors_increment=neighbors_inc,
                search_distance_increment=distance_inc,
                number_of_increments=num_inc,
                number_of_neighbors=num_neighbors,
                distance_band=distance_band,
                prediction_locations=population_path,
                explanatory_variables_to_match=vars_to_match,
                output_predicted_features=out_pred_gwr,
                robust_prediction="ROBUST",
                local_weighting_scheme=local_weighting_scheme
            )
        except arcpy.ExecuteError:
            err_msg = arcpy.GetMessages(2)
            if "110222" in err_msg:
                arcpy.AddError(
                    "Gagal estimasi model lokal GWR (ERROR 110222 - Multikolinearitas Lokal). "
                    "Perbesar nilai 'Minimum Jumlah Tetangga' atau keluarkan variabel yang homogen di suatu wilayah."
                )
            raise

        # 2. Buat titik dalam persil
        arcpy.AddMessage("=== Membuat Titik dalam Persil ===")
        arcpy.management.FeatureToPoint(population_path, poin_persil, "INSIDE")

        # 3. Interpolasi setiap field koefisien (C_*) dengan Empirical Bayesian Kriging
        arcpy.AddMessage("=== Proses Interpolasi Koefisien (EBK) ===")
        old_extent = arcpy.env.extent
        arcpy.env.extent = population_path

        coef_fields = [f.name for f in arcpy.ListFields(out_sample_gwr, "C_*")]
        rasters_name = []
        for field in coef_fields:
            arcpy.AddMessage("=== Interpolasi {} ===".format(field))
            out_raster = os.path.join(gdb_path, field)
            arcpy.ga.EmpiricalBayesianKriging(out_sample_gwr, field, "", out_raster)
            rasters_name.append(out_raster)

        arcpy.env.extent = old_extent

        # 4. Ekstrak nilai raster koefisien ke PoinPersil
        if rasters_name:
            arcpy.AddMessage("=== Extract Data Raster ke Poin Persil ===")
            arcpy.sa.ExtractMultiValuesToPoints(poin_persil, rasters_name)

        # 5. Gabungkan hasil ke Persil_Prediksi dan Sampel_Prediksi
        arcpy.AddMessage("=== Proses Pembuatan Persil_Prediksi dan Sampel_Prediksi ===")
        oid_persil = arcpy.Describe(population_path).OIDFieldName
        oid_sample = arcpy.Describe(sample_path).OIDFieldName

        arcpy.management.CopyFeatures(population_path, persil_prediksi)
        self._hapus_field_lama(persil_prediksi, ["PREDICTED"], prefix="C_")
        if coef_fields:
            arcpy.management.JoinField(persil_prediksi, oid_persil, poin_persil, "ORIG_FID", coef_fields)
        arcpy.management.JoinField(persil_prediksi, oid_persil, out_pred_gwr, "SOURCE_ID", ["PREDICTED"])

        arcpy.management.CopyFeatures(sample_path, sampel_prediksi)
        self._hapus_field_lama(sampel_prediksi, ["PREDICTED", "RESIDUAL", "STDRESID"])
        arcpy.management.JoinField(
            sampel_prediksi, oid_sample, out_sample_gwr, "SOURCE_ID", ["PREDICTED", "RESIDUAL", "STDRESID"]
        )

        # Hapus feature class sementara di GDB
        for temp_fc in [out_sample_gwr, out_pred_gwr, poin_persil]:
            self._hapus_jika_ada(temp_fc)

        arcpy.SetParameterAsText(17, persil_prediksi)
        arcpy.SetParameterAsText(18, sampel_prediksi)

        aprx = arcpy.mp.ArcGISProject("CURRENT")
        if aprx.activeMap:
            aprx.activeMap.addDataFromPath(persil_prediksi)
            aprx.activeMap.addDataFromPath(sampel_prediksi)

        arcpy.AddMessage("== Proses Selesai ==")

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