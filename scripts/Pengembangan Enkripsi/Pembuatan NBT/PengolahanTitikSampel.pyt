import arcpy, os, sys, math, webbrowser
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
        self.tools = [Tempel_Nilai_Tanah_Ke_Persil,
                      Transformasi_Variabel,
                      Pemodelan_Regresi_OLS_Dan_Exploratory,
                      Pemodelan_GWR_Sampel,
                      Evaluasi_Model_GWR_MAPE,
                      Spasial_Autokorelasi_Moran]

class Tempel_Nilai_Tanah_Ke_Persil(object):
    def __init__(self):
        """Definisi tool Proses Sampel Skor."""
        self.label = "Tempel Nilai Tanah Ke Persil"
        self.description = "Melakukan Spatial Join persil dengan Titik_Sampel dan menghapus data bernilai NULL."
        self.canRunInBackground = False

        # Simpan teks informasi sebagai atribut class agar mudah dipanggil ulang
        self.info_text = (
            "Tools ini akan menempelkan atribut nilai dan \n"
            "no_sampel dari Titik_Sampel ke Persil_Layer \n"
            "melalui proses Spatial Join, menghapus persil\n"
            "dengan nilai kosong (NULL), serta menampilkan\n"
            "hasil layer Persil_Sampel.\n\n"
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
        penjelasan.value = (
            "Tools ini akan menempelkan atribut nilai dan \n"
            "no_sampel dari Titik_Sampel ke Persil_Layer \n"
            "melalui proses Spatial Join, menghapus persil\n"
            "dengan nilai kosong (NULL), serta menampilkan\n"
            "hasil layer Persil_Sampel.\n\n"
            "Direktorat Penilaian Tanah dan Ekonomi Pertanahan,\n"
            "Kementerian ATR/BPN.\n"
            "Tahun: {}\n".format(datetime.now().year)
        )

        fl_sampel = arcpy.Parameter(
            displayName="Sampel Skor",
            name="out_sampel_skor",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [penjelasan, fl_sampel]
    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        if parameters[0].altered:
            parameters[0].value = self.info_text
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        """Logika utama yang dijalankan saat tool dieksekusi."""
        arcpy.AddMessage("== Proses dimulai ==")

        configs = persil.get_config_values()
        dataset_path = configs["project_config"]["dataset_path"]

        titiksampel_path = os.path.join(dataset_path, "Titik_Sampel")
        persil_path = os.path.join(dataset_path, "Persil_Layer")
        outjoin = os.path.join(dataset_path, "Persil_Sampel")

        if arcpy.Exists(outjoin):
            arcpy.management.Delete(outjoin)

        field_mapping = arcpy.FieldMappings()
        field_mapping.addTable(persil_path)

        fields_persil = {f.name.lower() for f in arcpy.ListFields(persil_path)}
        daftar_field_sampel = {f.name.lower(): f.name for f in arcpy.ListFields(titiksampel_path)}

        for nama_field in ["nilai", "no_sampel"]:
            nama_asli = daftar_field_sampel.get(nama_field)
            if not nama_asli:
                arcpy.AddError("Field '{}' tidak ditemukan pada Titik_Sampel.".format(nama_field))
                return
            fm = arcpy.FieldMap()
            fm.addInputField(titiksampel_path, nama_asli)
            field_mapping.addFieldMap(fm)

        arcpy.analysis.SpatialJoin(
            target_features=persil_path,
            join_features=titiksampel_path,
            out_feature_class=outjoin,
            join_type="KEEP_COMMON",
            field_mapping=field_mapping
        )

        field_nilai_hasil = "nilai_1" if "nilai" in fields_persil else "nilai"
        where_null = "{} IS NULL".format(field_nilai_hasil)

        with arcpy.da.UpdateCursor(outjoin, [field_nilai_hasil], where_null) as cursor:
            for row in cursor:
                cursor.deleteRow()

        lyr_output = arcpy.management.MakeFeatureLayer(outjoin, "Persil_Sampel").getOutput(0)
        arcpy.SetParameter(1, lyr_output)

        arcpy.AddMessage("== Proses Selesai ==")

class Transformasi_Variabel(object):
    def __init__(self):
        """Definisi tool Transformasi Variabel."""
        self.label = "Transformasi Variabel"
        self.description = "Melakukan transformasi variabel prediksi (Logaritmik dan Inverse) bertipe Double langsung pada Persil_Layer dan Persil_Sampel."
        self.canRunInBackground = False

        self.info_text = (
            "Tools ini akan melakukan transformasi variabel prediksi \n"
            "bertipe Double (Logaritmik atau Inverse) dan menyimpan \n"
            "hasilnya langsung ke dalam Persil_Layer dan Persil_Sampel.\n\n"
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
            displayName="Persil Layer",
            name="persil_skor",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input"
        )

        param_sampel = arcpy.Parameter(
            displayName="Persil Sampel",
            name="sampel_skor",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input"
        )

        param_variabel = arcpy.Parameter(
            displayName="Daftar Variabel Prediksi",
            name="define_variable",
            datatype="GPValueTable",
            parameterType="Required",
            direction="Input"
        )
        param_variabel.parameterDependencies = [param_persil.name]
        param_variabel.columns = [["Field", "Variabel"], ["GPString", "Transformasi"]]
        param_variabel.filters[1].type = "ValueList"
        param_variabel.filters[1].list = ["Logaritmik", "Inverse"]

        return [penjelasan, param_persil, param_sampel, param_variabel]

    def updateParameters(self, parameters):
        """Mengunci teks informasi, mengisi path default, dan menetapkan Logaritmik sebagai pilihan utama."""
        if parameters[0].altered:
            parameters[0].value = self.info_text

        if not parameters[1].altered or not parameters[2].altered:
            try:
                configs = persil.get_config_values()
                dataset_path = configs["project_config"]["dataset_path"]

                if not parameters[1].altered:
                    parameters[1].value = os.path.join(dataset_path, "Persil_Layer")
                if not parameters[2].altered:
                    parameters[2].value = os.path.join(dataset_path, "Persil_Sampel")
            except Exception:
                pass

        # Otomatis isi kolom Transformasi dengan "Logaritmik" saat variabel baru dipilih
        if parameters[3].values:
            updated_rows = []
            changed = False
            for row in parameters[3].values:
                if row[0] and (len(row) < 2 or not row[1]):
                    updated_rows.append([row[0], "Logaritmik"])
                    changed = True
                else:
                    updated_rows.append(row)
            if changed:
                parameters[3].values = updated_rows

        return

    def updateMessages(self, parameters):
        """Memberikan peringatan langsung di UI jika field yang dipilih bukan bertipe Double."""
        if parameters[1].value and parameters[2].value and parameters[3].values:
            try:
                persil_fields = {f.name.lower(): f for f in arcpy.ListFields(parameters[1].valueAsText)}
                sampel_fields = {f.name.lower(): f for f in arcpy.ListFields(parameters[2].valueAsText)}

                non_double = []
                for row in parameters[3].values:
                    if not row[0]:
                        continue
                    nama_var = str(row[0]).strip()
                    if nama_var.lower().startswith("s_"):
                        nama_var = nama_var[2:]

                    f_persil = self._get_source_field(persil_fields, nama_var)
                    f_sampel = self._get_source_field(sampel_fields, nama_var)

                    if (f_persil and f_persil.type != "Double") or (f_sampel and f_sampel.type != "Double"):
                        non_double.append(str(row[0]))

                if non_double:
                    parameters[3].setWarningMessage(
                        "Hanya field bertipe Double yang dapat ditransformasi. Field berikut akan dilewati: {}".format(
                            ", ".join(non_double)
                        )
                    )
            except Exception:
                pass
        return

    def _get_source_field(self, field_map_lower, nama_dasar):
        """Mengembalikan objek arcpy.Field dengan prioritas prefix 's_' lalu nama dasar."""
        kandidat_skor = "s_" + nama_dasar.lower()
        if kandidat_skor in field_map_lower:
            return field_map_lower[kandidat_skor]
        if nama_dasar.lower() in field_map_lower:
            return field_map_lower[nama_dasar.lower()]
        return None

    def _proses_transformasi(self, fc_path, field_map_lower, nama_dasar, jenis_transformasi):
        """Menambahkan field hasil transformasi dan menghitung nilainya langsung di feature class."""
        prefix = "ln_" if jenis_transformasi == "Logaritmik" else "iv_"
        field_hasil = prefix + nama_dasar

        if field_hasil.lower() in field_map_lower:
            arcpy.management.DeleteField(fc_path, field_map_lower[field_hasil.lower()].name)

        arcpy.management.AddField(fc_path, field_hasil, "DOUBLE")
        field_sumber = self._get_source_field(field_map_lower, nama_dasar).name

        with arcpy.da.UpdateCursor(fc_path, [field_hasil, field_sumber]) as cursor:
            for row in cursor:
                nilai = row[1]
                if jenis_transformasi == "Logaritmik":
                    if nilai is not None and nilai > 0:
                        row[0] = math.log(nilai)
                        cursor.updateRow(row)
                elif jenis_transformasi == "Inverse":
                    if nilai is not None and nilai != 0:
                        row[0] = 1.0 / nilai
                        cursor.updateRow(row)

    def execute(self, parameters, messages):
        """Logika utama yang dijalankan saat tool dieksekusi."""
        arcpy.AddMessage("== Proses dimulai ==")

        persil_path = parameters[1].valueAsText
        sampel_path = parameters[2].valueAsText
        list_transform = parameters[3].values or []

        persil_fields = {f.name.lower(): f for f in arcpy.ListFields(persil_path)}
        sampel_fields = {f.name.lower(): f for f in arcpy.ListFields(sampel_path)}

        for row in list_transform:
            nama_variabel = str(row[0]).strip()
            jenis_transformasi = str(row[1]).strip() if len(row) > 1 and row[1] else "Logaritmik"

            if nama_variabel.lower().startswith("s_"):
                nama_variabel = nama_variabel[2:]

            field_persil = self._get_source_field(persil_fields, nama_variabel)
            field_sampel = self._get_source_field(sampel_fields, nama_variabel)

            if not field_persil or not field_sampel:
                arcpy.AddError("NAMA FIELD VARIABEL '{}' TIDAK KONSISTEN ANTARA PERSIL DAN SAMPEL.".format(nama_variabel))
                raise arcpy.ExecuteError

            # Validasi tipe data harus Double pada kedua layer
            if field_persil.type != "Double" or field_sampel.type != "Double":
                arcpy.AddWarning(
                    "Field '{}' dilewati karena tipe data bukan Double (Persil: {}, Sampel: {}).".format(
                        nama_variabel, field_persil.type, field_sampel.type
                    )
                )
                continue

            self._proses_transformasi(persil_path, persil_fields, nama_variabel, jenis_transformasi)
            self._proses_transformasi(sampel_path, sampel_fields, nama_variabel, jenis_transformasi)

        arcpy.AddMessage("== Tampilkan Layer ==")
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        if aprx.activeMap:
            existing_layers = [lyr.name for lyr in aprx.activeMap.listLayers()]
            if os.path.basename(sampel_path) not in existing_layers:
                aprx.activeMap.addDataFromPath(sampel_path)

        arcpy.AddMessage("== Proses Selesai ==")


class Pemodelan_Regresi_OLS_Dan_Exploratory(object):
    def __init__(self):
        """Definisi tool Pemodelan Regresi (OLS & Exploratory Regression)."""
        self.label = "Pemodelan Regresi (OLS / Exploratory Regression)"
        self.description = "Menjalankan analisis Ordinary Least Squares (OLS) atau Exploratory Regression dan menyaring variabel signifikan ke tabel VariabelReady."
        self.canRunInBackground = False

        self.info_text = (
            "Tools ini akan melakukan pemodelan regresi menggunakan \n"
            "metode Ordinary Least Squares (OLS) atau Exploratory \n"
            "Regression pada Persil_Sampel, lalu menyimpan variabel \n"
            "yang signifikan (VIF < 7.5) ke dalam tabel VariabelReady.\n\n"
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
            displayName="Persil Sampel",
            name="in_feature",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input"
        )

        param_variabel = arcpy.Parameter(
            displayName="Variabel Prediksi",
            name="exp_var",
            datatype="Field",
            parameterType="Required",
            direction="Input",
            multiValue=True
        )
        param_variabel.parameterDependencies = [param_persil.name]

        param_metode = arcpy.Parameter(
            displayName="Metode Pemodelan",
            name="metode",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        param_metode.filter.type = "ValueList"
        param_metode.filter.list = ["Ordinary Least Squares (OLS)", "Exploratory Regression"]
        param_metode.value = "Ordinary Least Squares (OLS)"

        param_max_exp = arcpy.Parameter(
            displayName="Maksimum Jumlah Variabel",
            name="max_exp",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input"
        )
        param_max_exp.value = 5

        param_min_exp = arcpy.Parameter(
            displayName="Minimum Jumlah Variabel",
            name="min_exp",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input"
        )
        param_min_exp.value = 1

        param_cutoff = arcpy.Parameter(
            displayName="Batas Minimum Signifikansi (0 - 1)",
            name="cutoff",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input"
        )
        param_cutoff.value = 0.5

        return [
            penjelasan,
            param_persil,
            param_variabel,
            param_metode,
            param_max_exp,
            param_min_exp,
            param_cutoff
        ]

    def updateParameters(self, parameters):
        """Mengunci teks informasi, mengisi path default, dan mengatur tampilan parameter metode."""
        if parameters[0].altered:
            parameters[0].value = self.info_text

        if not parameters[1].altered:
            try:
                configs = persil.get_config_values()
                dataset_path = configs["project_config"]["dataset_path"]
                parameters[1].value = os.path.join(dataset_path, "Persil_Sampel")
            except Exception:
                pass

        # Tampilkan parameter tambahan hanya jika metode Exploratory Regression dipilih
        is_er = (parameters[3].valueAsText == "Exploratory Regression")
        parameters[4].enabled = is_er
        parameters[5].enabled = is_er
        parameters[6].enabled = is_er
        return

    def updateMessages(self, parameters):
        """Validasi kelengkapan parameter khusus Exploratory Regression."""
        if parameters[3].valueAsText == "Exploratory Regression":
            for idx, label in [(4, "Maksimum Jumlah Variabel"), (5, "Minimum Jumlah Variabel"), (6, "Batas Minimum Signifikansi")]:
                if parameters[idx].value is None:
                    parameters[idx].setErrorMessage("{} wajib diisi untuk metode Exploratory Regression.".format(label))
        return

    def _get_field_name(self, fc_path, target_name, fallback=None):
        """Mencari nama field asli secara case-insensitive."""
        field_map = {f.name.lower(): f.name for f in arcpy.ListFields(fc_path)}
        return field_map.get(target_name.lower(), fallback)

    def _hapus_jika_ada(self, path):
        """Menghapus feature class, tabel, atau file jika sudah ada."""
        if arcpy.Exists(path):
            arcpy.management.Delete(path)
        elif os.path.exists(path):
            os.remove(path)

    def _parse_hasil_ols(self, report_txt_path, var_real):
        """Membaca ringkasan variabel signifikan dan VIF < 7.5 dari log OLS."""
        with open(report_txt_path, "r") as fp:
            lines = [line.strip() for line in fp.readlines()]

        num_start, num_stop = 0, 0
        for idx, line in enumerate(lines):
            if "Intercept" in line:
                num_start = idx
            elif "OLS Diagnostics" in line:
                num_stop = idx

        hasil = []
        for line in lines[(num_start + 1):max(num_start + 1, num_stop - 2)]:
            kolom = list(filter(None, line.split(" ")))
            if len(kolom) not in (8, 9):
                continue

            nama_var = var_real.get(kolom[0].lower(), kolom[0])
            prob_str = kolom[4]
            if "*" not in prob_str:
                continue

            if len(kolom) == 9:
                vif_val = float(kolom[8].replace(",", "."))
                if vif_val < 7.5:
                    hasil.append([nama_var, prob_str[:-1], kolom[8]])
            elif len(kolom) == 8:
                hasil.append([nama_var, prob_str[:-1], ""])

        return hasil

    def _parse_hasil_er(self, report_txt_path, var_real, cutoff):
        """Membaca ringkasan signifikansi dan multikolinearitas dari log Exploratory Regression."""
        with open(report_txt_path, "r") as fp:
            lines = [line.strip() for line in fp.readlines()]

        num_start, num_stop, num_stop_vif = 0, 0, 0
        for idx, line in enumerate(lines):
            if "Summary of Variable Significance" in line:
                num_start = idx
            elif "Summary of Multicollinearity" in line:
                num_stop = idx
            elif "Summary of Residual Normality (JB)" in line:
                num_stop_vif = idx

        # Ambil nilai VIF per variabel
        vif_map = {}
        for line in lines[(num_stop + 2):max(num_stop + 2, num_stop_vif - 3)]:
            kolom = list(filter(None, line.split(" ")))
            if len(kolom) >= 2:
                vif_map[kolom[0]] = "" if kolom[1] == "--------" else kolom[1]

        # Saring variabel berdasarkan cutoff dan VIF < 7.5
        hasil = []
        batas_persen = float(cutoff) * 100.0
        for line in lines[(num_start + 2):max(num_start + 2, num_stop - 3)]:
            kolom = list(filter(None, line.split(" ")))
            if len(kolom) < 2:
                continue

            sig_val = float(kolom[1].replace(",", "."))
            if sig_val < batas_persen:
                continue

            nama_raw = kolom[0]
            nama_var = var_real.get(nama_raw.lower(), nama_raw)
            vif_str = vif_map.get(nama_raw, "")

            if vif_str:
                if float(vif_str.replace(",", ".")) < 7.5:
                    hasil.append([nama_var, kolom[1], vif_str])
            else:
                hasil.append([nama_var, kolom[1], ""])

        return hasil

    def execute(self, parameters, messages):
        """Logika utama yang dijalankan saat tool dieksekusi."""
        arcpy.AddMessage("== Proses dimulai ==")
        arcpy.env.overwriteOutput = True

        configs = persil.get_config_values()
        project_cfg = configs["project_config"]
        dataset_path = project_cfg["dataset_path"]
        gdb_path = project_cfg.get("gdb_path") or os.path.dirname(dataset_path)
        ws_path = project_cfg.get("ws_path") or os.path.dirname(gdb_path)

        in_feature = parameters[1].valueAsText
        exp_var = parameters[2].valueAsText
        metode = parameters[3].valueAsText
        max_exp = parameters[4].value
        min_exp = parameters[5].value
        cutoff = parameters[6].value

        # Validasi field wajib ('nilai' dan 'IdBidang' / OID)
        field_nilai = self._get_field_name(in_feature, "nilai")
        if not field_nilai:
            arcpy.AddError("Field 'nilai' tidak ditemukan pada {}.".format(in_feature))
            raise arcpy.ExecuteError

        oid_field = arcpy.Describe(in_feature).OIDFieldName
        field_id = self._get_field_name(in_feature, "IdBidang", fallback=oid_field)

        # Simpan nama asli variabel (case-sensitive)
        var_real = {v.strip().lower(): v.strip() for v in exp_var.split(";") if v.strip()}
        list_hasilakhir = []

        aprx = arcpy.mp.ArcGISProject("CURRENT")
        current_map = aprx.activeMap

        if metode == "Ordinary Least Squares (OLS)":
            ols_result = os.path.join(dataset_path, "OLS_Result")
            ols_coeff = os.path.join(gdb_path, "OLS_Coeff")
            ols_diag = os.path.join(gdb_path, "OLS_Diag")
            ols_report = os.path.join(ws_path, "OLS_Report")
            ols_txt = os.path.join(ws_path, "OLS_Result.txt")

            for item in [ols_result, ols_coeff, ols_diag, ols_report, ols_txt]:
                self._hapus_jika_ada(item)

            try:
                arcpy.stats.OrdinaryLeastSquares(
                    in_feature, field_id, ols_result, field_nilai,
                    exp_var, ols_coeff, ols_diag, ols_report
                )
                with open(ols_txt, "w") as fp:
                    fp.write(arcpy.GetMessages())

                list_hasilakhir = self._parse_hasil_ols(ols_txt, var_real)
                self._hapus_jika_ada(ols_txt)

                if current_map:
                    current_map.addDataFromPath(ols_result)
                    current_map.addDataFromPath(ols_coeff)
                    current_map.addDataFromPath(ols_diag)

                arcpy.AddMessage("OLS Diagnostics ({})".format(ols_diag))
                arcpy.AddMessage("OLS Coefficient ({})".format(ols_coeff))
                arcpy.AddMessage("Summary of OLS Results ({})".format(ols_report))

            except arcpy.ExecuteError:
                arcpy.AddError(arcpy.GetMessages())
                raise

        elif metode == "Exploratory Regression":
            er_result = os.path.join(gdb_path, "ER_Result")
            er_report = os.path.join(ws_path, "ER_Report")
            er_txt = os.path.join(ws_path, "ER_ResultTemp.txt")

            for item in [er_result, er_report, er_txt]:
                self._hapus_jika_ada(item)

            try:
                arcpy.stats.ExploratoryRegression(
                    in_feature, field_nilai, exp_var, "", er_report,
                    er_result, max_exp, min_exp, 0.5, 0.05, 7.5, 0.1, 0.1
                )
                with open(er_txt, "w") as fp:
                    fp.write(arcpy.GetMessages())

                list_hasilakhir = self._parse_hasil_er(er_txt, var_real, cutoff)
                self._hapus_jika_ada(er_txt)

                if current_map:
                    current_map.addDataFromPath(er_result)

                arcpy.AddMessage("Summary of Exploratory Regression Result ({}.txt)".format(er_report))

            except arcpy.ExecuteError:
                arcpy.AddError(arcpy.GetMessages())
                raise

        # Buat tabel VariabelReady untuk tahap GWR
        vready = os.path.join(gdb_path, "VariabelReady")
        self._hapus_jika_ada(vready)
        arcpy.management.CreateTable(gdb_path, "VariabelReady")

        kolom_kedua = "probability" if metode == "Ordinary Least Squares (OLS)" else "significant"
        for nama_kolom in ["variable", kolom_kedua, "vif"]:
            arcpy.management.AddField(vready, nama_kolom, "TEXT", field_length=100)

        with arcpy.da.InsertCursor(vready, ["variable", kolom_kedua, "vif"]) as cursor:
            for baris in list_hasilakhir:
                cursor.insertRow(baris)

        if current_map:
            current_map.addDataFromPath(vready)

        arcpy.AddMessage("== Proses Selesai ==")


class Pemodelan_GWR_Sampel(object):
    def __init__(self):
        """Definisi tool Pemodelan Geographically Weighted Regression (GWR)."""
        self.label = "Pemodelan GWR (Sampel Prediksi)"
        self.description = "Menjalankan analisis Geographically Weighted Regression (GWR) pada Persil_Sampel dan menghasilkan Sampel_Prediksi."
        self.canRunInBackground = False

        self.info_text = (
            "Tools ini akan melakukan pemodelan spasial menggunakan \n"
            "metode Geographically Weighted Regression (GWR) pada \n"
            "Persil_Sampel untuk menghasilkan layer Sampel_Prediksi.\n\n"
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

        param_exp_var = arcpy.Parameter(
            displayName="Variabel Prediksi",
            name="explanatory_fields",
            datatype="Field",
            parameterType="Required",
            direction="Input",
            multiValue=True
        )
        param_exp_var.parameterDependencies = [param_sample.name]

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
            name="number_of_increment",
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
            param_exp_var,
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
            out_sampel_prediksi
        ]

    def updateParameters(self, parameters):
        """Mengunci teks informasi, mengisi path default, dan menyesuaikan visibilitas parameter GWR."""
        if parameters[0].altered:
            parameters[0].value = self.info_text

        try:
            configs = persil.get_config_values()
            project_cfg = configs["project_config"]
            dataset_path = project_cfg["dataset_path"]
            gdb_path = project_cfg.get("gdb_path") or os.path.dirname(dataset_path)

            if not parameters[1].altered:
                parameters[1].value = os.path.join(dataset_path, "Persil_Sampel")

            # Otomatis isi variabel prediksi dari tabel VariabelReady jika tersedia
            if not parameters[2].altered and parameters[1].value:
                vready_path = os.path.join(gdb_path, "VariabelReady")
                if arcpy.Exists(vready_path) and arcpy.Exists(parameters[1].valueAsText):
                    sample_fields = {f.name.lower(): f.name for f in arcpy.ListFields(parameters[1].valueAsText)}
                    vars_ready = []
                    with arcpy.da.SearchCursor(vready_path, ["variable"]) as cursor:
                        for row in cursor:
                            if row[0] and row[0].lower() in sample_fields:
                                vars_ready.append(sample_fields[row[0].lower()])
                    if vars_ready:
                        parameters[2].values = vars_ready
        except Exception:
            pass

        # Aktifkan sub-parameter ketetanggaan sesuai kombinasi tipe & metode yang dipilih
        nb_type = parameters[3].valueAsText
        nb_method = parameters[4].valueAsText

        is_num = (nb_type == "NUMBER_OF_NEIGHBORS")
        is_dist = (nb_type == "DISTANCE_BAND")
        is_golden = (nb_method == "GOLDEN_SEARCH")
        is_manual = (nb_method == "MANUAL_INTERVALS")
        is_user = (nb_method == "USER_DEFINED")

        parameters[5].enabled = is_num and (is_golden or is_manual)   # minimum_number_of_neighbors
        parameters[6].enabled = is_num and is_golden                   # maximum_number_of_neighbors
        parameters[7].enabled = is_dist and (is_golden or is_manual)  # minimum_search_distance
        parameters[8].enabled = is_dist and is_golden                  # maximum_search_distance
        parameters[9].enabled = is_num and is_manual                   # number_of_neighbors_increment
        parameters[10].enabled = is_dist and is_manual                 # search_distance_increment
        parameters[11].enabled = is_manual                             # number_of_increment
        parameters[12].enabled = is_num and is_user                    # number_of_neighbors
        parameters[13].enabled = is_dist and is_user                   # distance_band
        return

    def _get_field_name(self, fc_path, target_name):
        """Mencari nama field asli secara case-insensitive."""
        field_map = {f.name.lower(): f.name for f in arcpy.ListFields(fc_path)}
        return field_map.get(target_name.lower())

    def execute(self, parameters, messages):
        """Logika utama yang dijalankan saat tool dieksekusi."""
        arcpy.AddMessage("== Proses dimulai ==")
        arcpy.env.overwriteOutput = True

        configs = persil.get_config_values()
        dataset_path = configs["project_config"]["dataset_path"]

        sample_path = parameters[1].valueAsText
        explanatory_fields = parameters[2].valueAsText
        neighborhood_type = parameters[3].valueAsText
        neighborhood_selection_method = parameters[4].valueAsText

        # Ambil nilai hanya dari parameter ketetanggaan yang aktif agar tidak bentrok
        min_neighbors = parameters[5].value if parameters[5].enabled else None
        max_neighbors = parameters[6].value if parameters[6].enabled else None
        min_distance = parameters[7].value if parameters[7].enabled else None
        max_distance = parameters[8].value if parameters[8].enabled else None
        neighbors_inc = parameters[9].value if parameters[9].enabled else None
        distance_inc = parameters[10].value if parameters[10].enabled else None
        num_inc = parameters[11].value if parameters[11].enabled else None
        num_neighbors = parameters[12].value if parameters[12].enabled else None
        distance_band = parameters[13].value if parameters[13].enabled else None
        local_weighting_scheme = parameters[14].valueAsText or "GAUSSIAN"

        field_nilai = self._get_field_name(sample_path, "nilai")
        if not field_nilai:
            arcpy.AddError("Field 'nilai' tidak ditemukan pada {}.".format(sample_path))
            raise arcpy.ExecuteError

        sampel_prediksi_path = os.path.join(dataset_path, "Sampel_Prediksi")
        if arcpy.Exists(sampel_prediksi_path):
            arcpy.management.Delete(sampel_prediksi_path)

        arcpy.stats.GWR(
            in_features=sample_path,
            dependent_variable=field_nilai,
            model_type="CONTINUOUS",
            explanatory_variables=explanatory_fields,
            output_features=sampel_prediksi_path,
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
            robust_prediction="ROBUST",
            local_weighting_scheme=local_weighting_scheme
        )

        arcpy.SetParameterAsText(15, sampel_prediksi_path)

        aprx = arcpy.mp.ArcGISProject("CURRENT")
        if aprx.activeMap:
            aprx.activeMap.addDataFromPath(sampel_prediksi_path)

        arcpy.AddMessage("== Proses Selesai ==")

class Evaluasi_Model_GWR_MAPE(object):
    def __init__(self):
        """Definisi tool Evaluasi Model GWR (Persen Residual, MAPE, dan Grafik)."""
        self.label = "Evaluasi Model GWR (Hitung MAPE & Grafik)"
        self.description = "Menghitung persen residual, nilai MAPE, dan menampilkan grafik persen residual pada layer Sampel_Prediksi."
        self.canRunInBackground = False

        self.info_text = (
            "Tools ini akan menghitung persen residual (p_residu), \n"
            "nilai absolut persen residual (a_p_residu), dan nilai \n"
            "MAPE pada layer Sampel_Prediksi, serta menampilkan \n"
            "Grafik Persen Residu pada peta aktif.\n\n"
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

        param_prediksi = arcpy.Parameter(
            displayName="Sampel Prediksi",
            name="in_sampel_prediksi",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input"
        )

        return [penjelasan, param_prediksi]

    def updateParameters(self, parameters):
        """Mengunci teks informasi dan mengisi otomatis path Sampel_Prediksi."""
        if parameters[0].altered:
            parameters[0].value = self.info_text

        if not parameters[1].altered:
            try:
                configs = persil.get_config_values()
                dataset_path = configs["project_config"]["dataset_path"]
                parameters[1].value = os.path.join(dataset_path, "Sampel_Prediksi")
            except Exception:
                pass
        return

    def _get_field_name(self, field_map_lower, target_name):
        """Mencari nama field asli secara case-insensitive."""
        return field_map_lower.get(target_name.lower())

    def execute(self, parameters, messages):
        """Logika utama yang dijalankan saat tool dieksekusi."""
        arcpy.AddMessage("== Proses dimulai ==")
        arcpy.env.overwriteOutput = True

        sampel_prediksi_path = parameters[1].valueAsText
        if not arcpy.Exists(sampel_prediksi_path):
            arcpy.AddError("Feature class tidak ditemukan: {}".format(sampel_prediksi_path))
            raise arcpy.ExecuteError

        field_map = {f.name.lower(): f.name for f in arcpy.ListFields(sampel_prediksi_path)}
        field_nilai = self._get_field_name(field_map, "nilai")
        field_pred = self._get_field_name(field_map, "Predicted")

        if not field_nilai or not field_pred:
            arcpy.AddError("Field 'nilai' atau 'Predicted' tidak ditemukan pada {}.".format(sampel_prediksi_path))
            raise arcpy.ExecuteError

        # 1. Tambahkan field hasil evaluasi jika belum ada
        for nama_field in ["p_residu", "a_p_residu", "mape"]:
            if nama_field not in field_map:
                arcpy.management.AddField(sampel_prediksi_path, nama_field, "DOUBLE")

        # 2. Hitung persen residual dan akumulasi nilai untuk MAPE dalam satu kali pembacaan
        arcpy.AddMessage("== Hitung persen residual & MAPE ==")
        total_abs_residu = 0.0
        jumlah_data = 0

        with arcpy.da.UpdateCursor(sampel_prediksi_path, [field_nilai, field_pred, "p_residu", "a_p_residu"]) as cursor:
            for row in cursor:
                nilai_aktual, nilai_prediksi = row[0], row[1]
                if nilai_aktual is not None and nilai_aktual != 0 and nilai_prediksi is not None:
                    p_res = ((nilai_aktual - nilai_prediksi) / float(nilai_aktual)) * 100.0
                    a_p_res = abs(p_res)
                    row[2] = p_res
                    row[3] = a_p_res
                    cursor.updateRow(row)

                    total_abs_residu += a_p_res
                    jumlah_data += 1

        mape = (total_abs_residu / jumlah_data) if jumlah_data > 0 else 0.0
        judul_bawah = "Nilai MAPE = {:.4f}%".format(mape)
        arcpy.AddMessage("== {} ==".format(judul_bawah))

        # 3. Simpan nilai MAPE ke seluruh baris
        with arcpy.da.UpdateCursor(sampel_prediksi_path, ["mape"]) as cursor:
            for row in cursor:
                row[0] = mape
                cursor.updateRow(row)
        # 4. Tampilkan layer pada peta aktif dan buat grafik persen residual
        arcpy.AddMessage("== Plot persen residual ==")
        oid_fieldname = arcpy.Describe(sampel_prediksi_path).OIDFieldName

        aprx = arcpy.mp.ArcGISProject("CURRENT")
        current_map = aprx.activeMap
        if current_map:
            layer_name = os.path.basename(sampel_prediksi_path)

            # Hapus layer lama di peta agar cache kolom baru (p_residu) dan CIM terbarui
            for lyr in current_map.listLayers(layer_name):
                if lyr.isFeatureLayer:
                    current_map.removeLayer(lyr)

            layerout = current_map.addDataFromPath(sampel_prediksi_path)

            chart = arcpy.Chart("Grafik Persen Residu")
            chart.type = "line"
            chart.title = "Grafik Persen Residu"
            chart.datasource = layerout
            chart.xAxis.field = oid_fieldname
            chart.yAxis.field = "p_residu"
            chart.xAxis.title = judul_bawah
            chart.yAxis.title = "Persen Residu"
            chart.addToLayer(layerout)
        else:
            arcpy.AddWarning("Tidak ada peta aktif (Active Map) untuk menampilkan grafik.")

        arcpy.AddMessage("== Proses Selesai ==")


class Spasial_Autokorelasi_Moran(object):
    def __init__(self):
        """Definisi tool Autokorelasi Spasial (Global Moran's I)."""
        self.label = "Autokorelasi Spasial (Global Moran's I)"
        self.description = "Menguji pola autokorelasi spasial residual pada Sampel_Prediksi menggunakan Global Moran's I."
        self.canRunInBackground = False

        self.info_text = (
            "Tools ini akan menghitung indeks autokorelasi spasial \n"
            "(Global Moran's I), z-score, dan p-value pada kolom \n"
            "residual (StdResid) layer Sampel_Prediksi untuk \n"
            "memastikan residual tersebar secara acak, serta \n"
            "membuka laporan HTML hasilnya secara otomatis.\n\n"
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
            displayName="Sampel Prediksi",
            name="in_sample",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input"
        )

        param_field = arcpy.Parameter(
            displayName="Field Residual",
            name="input_field",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        param_field.parameterDependencies = [param_sample.name]
        param_field.filter.list = ["Short", "Long", "Float", "Double"]

        param_concept = arcpy.Parameter(
            displayName="Konseptualisasi Hubungan Spasial",
            name="conceptualization",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        param_concept.filter.type = "ValueList"
        param_concept.filter.list = [
            "INVERSE_DISTANCE",
            "INVERSE_DISTANCE_SQUARED",
            "FIXED_DISTANCE_BAND",
            "ZONE_OF_INDIFFERENCE",
            "CONTIGUITY_EDGES_ONLY",
            "CONTIGUITY_EDGES_CORNERS",
            "GET_SPATIAL_WEIGHTS_FROM_FILE"
        ]
        param_concept.value = "INVERSE_DISTANCE"

        param_dist_method = arcpy.Parameter(
            displayName="Metode Jarak",
            name="distance_method",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        param_dist_method.filter.type = "ValueList"
        param_dist_method.filter.list = ["EUCLIDEAN_DISTANCE", "MANHATTAN_DISTANCE"]
        param_dist_method.value = "EUCLIDEAN_DISTANCE"

        param_std = arcpy.Parameter(
            displayName="Standardisasi",
            name="standardization",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        param_std.filter.type = "ValueList"
        param_std.filter.list = ["NONE", "ROW"]
        param_std.value = "NONE"

        return [
            penjelasan,
            param_sample,
            param_field,
            param_concept,
            param_dist_method,
            param_std
        ]

    def updateParameters(self, parameters):
        """Mengunci teks informasi dan mengisi otomatis path Sampel_Prediksi serta field StdResid."""
        if parameters[0].altered:
            parameters[0].value = self.info_text

        try:
            if not parameters[1].altered:
                configs = persil.get_config_values()
                dataset_path = configs["project_config"]["dataset_path"]
                parameters[1].value = os.path.join(dataset_path, "Sampel_Prediksi")

            if not parameters[2].altered and parameters[1].value:
                sample_path = parameters[1].valueAsText
                if arcpy.Exists(sample_path):
                    field_map = {f.name.lower(): f.name for f in arcpy.ListFields(sample_path)}
                    if "stdresid" in field_map:
                        parameters[2].value = field_map["stdresid"]
        except Exception:
            pass
        return

    def _get_field_name(self, fc_path, target_name):
        """Mencari nama field asli secara case-insensitive."""
        field_map = {f.name.lower(): f.name for f in arcpy.ListFields(fc_path)}
        return field_map.get(target_name.lower())

    def execute(self, parameters, messages):
        """Logika utama yang dijalankan saat tool dieksekusi."""
        arcpy.AddMessage("== Proses dimulai ==")
        arcpy.env.overwriteOutput = True

        sample_path = parameters[1].valueAsText
        if not arcpy.Exists(sample_path):
            arcpy.AddError("Feature class tidak ditemukan: {}".format(sample_path))
            raise arcpy.ExecuteError

        raw_field = parameters[2].valueAsText
        input_field = self._get_field_name(sample_path, raw_field)
        if not input_field:
            arcpy.AddError("Field '{}' tidak ditemukan pada {}.".format(raw_field, sample_path))
            raise arcpy.ExecuteError

        conceptualization = parameters[3].valueAsText
        distance_method = parameters[4].valueAsText
        standardization = parameters[5].valueAsText

        moran = arcpy.stats.SpatialAutocorrelation(
            sample_path,
            input_field,
            "GENERATE_REPORT",
            conceptualization,
            distance_method,
            standardization
        )

        index_moran = moran.getOutput(0)
        z_score = moran.getOutput(1)
        p_value = moran.getOutput(2)
        report = moran.getOutput(3)

        arcpy.AddMessage("== Summary ==")
        arcpy.AddMessage("index_moran : {}".format(index_moran))
        arcpy.AddMessage("z_score     : {}".format(z_score))
        arcpy.AddMessage("p_value     : {}".format(p_value))
        arcpy.AddMessage("report      : {}".format(report))

        if report and os.path.exists(report):
            webbrowser.open(report)

        arcpy.AddMessage("== Proses Selesai ==")
