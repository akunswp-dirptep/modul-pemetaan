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


class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [Sesuaikan_Kelas_dan_Lebar_Jalan,
                      Validasi_Topologi_Jaringan_Jalan,
                      Deteksi_Outlier_Jaringan_Jalan,
                      Tampilkan_Simbologi_Kelas_Jalan,
                      ]

    
class Sesuaikan_Kelas_dan_Lebar_Jalan(object):

    def __init__(self):
        self.label = "Sesuaikan Kelas dan Lebar Jalan"
        self.description = "Memperbarui atribut kelas dan lebar jalan pada fitur yang sedang dipilih."
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
            "Arteri Primer", "Arteri Sekunder", 
            "Kolektor Primer", "Kolektor Sekunder", 
            "Lokal Primer", "Lokal Sekunder", "Setapak"
        ]

        lb_jalan = arcpy.Parameter(
            displayName="Lebar Jalan",
            name="lb_jalan",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input"
        )

        return [kls_jln, lb_jalan]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):

        kls_jln = parameters[0].valueAsText
        lb_jalan = parameters[1].value

        try:
            configs = persil.get_config_values()
            kelas_jalan_config = configs["jaringan_jalan_config"]["skoring"]["kelas_jalan"]
            
            s_kls_jln = kelas_jalan_config.get(kls_jln, 0) 
        except Exception as e:
            messages.addErrorMessage(f"Gagal memuat konfigurasi: {str(e)}")
            return

        nama_fl_jarjal = 'Jaringan_Jalan'
    
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        m = aprx.activeMap
        
        layer_ditemukan = any(lyr.name == nama_fl_jarjal for lyr in m.listLayers())
        
        if not layer_ditemukan:
            messages.addErrorMessage(f"Layer '{nama_fl_jarjal}' tidak ditemukan di dalam project aktif.")
            return
        desc = arcpy.Describe(nama_fl_jarjal)
        if not desc.FIDSet:
            messages.addWarningMessage(f"Tidak ada fitur pada layer '{nama_fl_jarjal}' yang dipilih. Proses dihentikan.")
            return

        sampel_fields = [f.name.lower() for f in arcpy.ListFields(nama_fl_jarjal)]
        required_fields = ["kls_jln", "lb_jln", "s_klsjln"]
        
        missing_fields = [f for f in required_fields if f.lower() not in sampel_fields]

        if missing_fields:
            messages.addErrorMessage("Field berikut tidak ditemukan: {} ==".format(", ".join(missing_fields)))
            raise arcpy.ExecuteError

        fields_to_update = ["kls_jln", "lb_jln", "s_klsjln"]
        jumlah_update = 0

        try:
            with arcpy.da.UpdateCursor(nama_fl_jarjal, fields_to_update) as cursor:
                for row in cursor:
                    row[0] = kls_jln
                    row[1] = lb_jalan
                    row[2] = s_kls_jln
                    
                    cursor.updateRow(row)
                    jumlah_update += 1

            messages.addMessage(f"{jumlah_update} fitur jaringan jalan berhasil diperbarui")
            
        except Exception as e:
            messages.addErrorMessage(f"Gagal saat memperbarui atribut: {str(e)}")
            raise arcpy.ExecuteError

        symbology_path = r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Simbologi_Kelas_Jaringan_Jalan.lyrx"
        
        if os.path.exists(symbology_path):
            messages.addMessage(f"== Menerapkan simbologi dari {os.path.basename(symbology_path)} ==")
            try:
                arcpy.management.ApplySymbologyFromLayer(
                    in_layer=nama_fl_jarjal,
                    in_symbology_layer=symbology_path,
                    update_symbology="UPDATE"
                )
                messages.addMessage("== Simbologi berhasil diterapkan dan tampilan di-refresh ==")

            except Exception as e:
                messages.addWarningMessage(f"Gagal menerapkan simbologi: {str(e)}")
        else:
            messages.addWarningMessage(f"Peringatan: File simbologi tidak ditemukan di {symbology_path}")

        messages.addMessage("Proses selesai")
        return

class Validasi_Topologi_Jaringan_Jalan(object):

    def __init__(self):
        self.label = "Validasi Topologi Jaringan Jalan"
        self.description = "Mengecek topologi jaringan jalan (Overlap, Dangles, Pseudo-Nodes, Intersect)."
        self.canRunInBackground = False

    def getParameterInfo(self):
        penjelasan = arcpy.Parameter(
            displayName="Informasi Tool",
            name="penjelasan",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )
        
        penjelasan.value = (
                "Tool ini secara otomatis membuat dan menjalankan\n"
                "evaluasi Topologi pada layer Jaringan Jalan.\n"
                "Aturan spasial yang dicek meliputi:\n\n"
                "  1. Must Not Overlap: Garis jalan tidak boleh\n"
                "      tumpang tindih.\n"
                "  2. Must Not Have Dangles: Ujung garis tidak\n"
                "      boleh menggantung tanpa tujuan.\n"
                "  3. Must Not Have Pseudo-Nodes: Tidak boleh ada\n"
                "      jalan terpotong (titik semu) jika tidak ada\n"
                "     persimpangan.\n"
                "  4. Must Not Intersect: Garis menempel/memotong\n"
                "      jalan lain harus diputus dengan node (simpul)\n\n"
                "Direktorat Penilaian Tanah dan Ekonomi Pertanahan,\n"
                "Kementerian ATR/BPN.\n"
                "Tahun: {}\n".format(datetime.now().year))
        
        output_topology = arcpy.Parameter(
            displayName="Output Topology",
            name="output_topology",
            datatype="DETopology",
            parameterType="Derived",
            direction="Output"
        )
        return [penjelasan, output_topology]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        try:
            configs = persil.get_config_values()
            dataset_path = configs["project_config"]["dataset_path"]
            
            jaringan_jalan_path = os.path.join(dataset_path, 'Jaringan_Jalan')
            jarjaltop_path = os.path.join(dataset_path, 'Topologi_Jaringan_Jalan')

            if arcpy.Exists(jarjaltop_path):
                messages.addMessage("== Menghapus file topologi lama... ==")
                try:
                    arcpy.management.Delete(jarjaltop_path)
                except Exception as e:
                    messages.addWarningMessage(f"Gagal menghapus topologi lama: {str(e)}")

            messages.addMessage("== Membuat topologi baru... ==")
            arcpy.management.CreateTopology(
                dataset_path,
                'Topologi_Jaringan_Jalan'
            )

            messages.addMessage("== Menambahkan layer Jaringan Jalan ke topologi... ==")
            arcpy.management.AddFeatureClassToTopology(
                in_topology=jarjaltop_path,
                in_featureclass=jaringan_jalan_path,
                xy_rank=1,
                z_rank=1
            )

            rules = [
                "Must Not Overlap (Line)",
                "Must Not Have Dangles (Line)",
                "Must Not Have Pseudo-Nodes (Line)", 
                "Must Not Intersect Or Touch Interior (Line)"
            ]

            messages.addMessage("== Menerapkan aturan spasial (rules)... ==")
            for rule in rules:
                arcpy.management.AddRuleToTopology(
                    in_topology=jarjaltop_path,
                    rule_type=rule,
                    in_featureclass=jaringan_jalan_path
                )

            messages.addMessage("Sedang memvalidasi topologi (mencari error)... ==")
            arcpy.management.ValidateTopology(in_topology=jarjaltop_path)
            parameters[1].value = jarjaltop_path
            messages.addMessage("Proses validasi topologi selesai")

        except Exception as e:
            messages.addErrorMessage(f"Terjadi kesalahan: {str(e)}")
            raise arcpy.ExecuteError

        return   
     
class Deteksi_Outlier_Jaringan_Jalan(object):

    def __init__(self):
        self.label = "Deteksi Outlier Jaringan Jalan"
        self.description = "Mendeteksi anomali/outlier lebar jalan berdasarkan kelas jalan menggunakan Anselin Local Moran's I."
        self.canRunInBackground = False

    def getParameterInfo(self):
        # 1. Parameter INPUT baru (User memilih kelas jalan)
        input_kelas_jalan = arcpy.Parameter(
            displayName="Pilih Kelas Jalan yang akan diproses",
            name="input_kelas_jalan",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
            multiValue=True # Memungkinkan user memilih lebih dari 1
        )
        
        # Filter Dropdown list untuk UI ArcMap/ArcGIS Pro
        input_kelas_jalan.filter.list = [
            "1 - Jalan Lokal Setapak",
            "2 - Jalan Lokal Sekunder",
            "3 - Jalan Lokal Primer",
            "4 - Jalan Kolektor Sekunder",
            "5 - Jalan Kolektor Primer",
            "6 - Jalan Arteri Sekunder",
            "7 - Jalan Arteri Primer"
        ]

        # 2. Parameter OUTPUT (Derived)
        output_jaringan_jalan = arcpy.Parameter(
            displayName="Output Jaringan Jalan",
            name="output_jaringan_jalan",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )
        output_lokal_setapak = arcpy.Parameter(
            displayName="Outlier Jalan Lokal Setapak",
            name="output_lokal_setapak", datatype="GPFeatureLayer", parameterType="Derived", direction="Output")
        output_lokal_sekunder = arcpy.Parameter(
            displayName="Outlier Jalan Lokal Sekunder",
            name="output_lokal_sekunder", datatype="GPFeatureLayer", parameterType="Derived", direction="Output")
        output_lokal_primer = arcpy.Parameter(
            displayName="Outlier Jalan Lokal Primer",
            name="output_lokal_primer", datatype="GPFeatureLayer", parameterType="Derived", direction="Output")
        output_kolektor_sekunder = arcpy.Parameter(
            displayName="Outlier Jalan Kolektor Sekunder",
            name="output_kolektor_sekunder", datatype="GPFeatureLayer", parameterType="Derived", direction="Output")
        output_kolektor_primer = arcpy.Parameter(
            displayName="Outlier Jalan Kolektor Primer",
            name="output_kolektor_primer", datatype="GPFeatureLayer", parameterType="Derived", direction="Output")
        output_arteri_sekunder = arcpy.Parameter(
            displayName="Outlier Jalan Arteri Sekunder",
            name="output_arteri_sekunder", datatype="GPFeatureLayer", parameterType="Derived", direction="Output")
        output_arteri_primer = arcpy.Parameter(
            displayName="Outlier Jalan Arteri Primer",
            name="output_arteri_primer", datatype="GPFeatureLayer", parameterType="Derived", direction="Output")

        return [
            input_kelas_jalan,         # Index 0
            output_jaringan_jalan,     # Index 1
            output_lokal_setapak,      # Index 2
            output_lokal_sekunder,     # Index 3
            output_lokal_primer,       # Index 4
            output_kolektor_sekunder,  # Index 5
            output_kolektor_primer,    # Index 6
            output_arteri_sekunder,    # Index 7
            output_arteri_primer       # Index 8
        ]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        messages.addMessage("== Proses Deteksi Outlier Dimulai ==")

        raw_selected_classes = parameters[0].valueAsText
        selected_class_ids = []
        
        if raw_selected_classes:
            class_list = [val.strip("'") for val in raw_selected_classes.split(";")]
            selected_class_ids = [int(val.split(" - ")[0]) for val in class_list]

        configs = persil.get_config_values()
        dataset_path = configs['project_config']['dataset_path']
        jaringanjalan_path = os.path.join(dataset_path, "Jaringan_Jalan")
        
        appdata = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.realpath(__file__))))))
        
        temp_gdb_path = arcpy.env.scratchGDB
        sim_path = os.path.join(appdata, "SimbologiOutlierKelasJalan.lyr")
        no_sim_path = os.path.join(appdata, "NoSimbologiJalan.lyr")

        field_names = [field.name for field in arcpy.ListFields(jaringanjalan_path)]
        if "s_klsjln" not in field_names or "lb_jln" not in field_names:
            messages.addWarningMessage("== PERINGATAN: Field 's_klsjln' atau 'lb_jln' tidak ditemukan! Proses dihentikan. ==")
            return

        def delete_if_exists(item):
            if arcpy.Exists(item):
                try:
                    arcpy.management.Delete(item)
                except Exception as e:
                    messages.addWarningMessage(f"Gagal menghapus temp data {item}: {e}")

        list_err = []

        outlier_mapping = {
            1: ("outlier_u_klsjln_1", "Jalan_Lokal_Setapak", 2),
            2: ("outlier_u_klsjln_2", "Jalan_Lokal_Sekunder", 3),
            3: ("outlier_u_klsjln_3", "Jalan_Lokal_Primer", 4),
            4: ("outlier_u_klsjln_4", "Jalan_Kolektor_Sekunder", 5),
            5: ("outlier_u_klsjln_5", "Jalan_Kolektor_Primer", 6),
            6: ("outlier_u_klsjln_6", "Jalan_Arteri_Sekunder", 7),
            7: ("outlier_u_klsjln_7", "Jalan_Arteri_Primer", 8)
        }

        for i in selected_class_ids:
            fc_name, lyr_name, param_idx = outlier_mapping[i]
            out_path = os.path.join(temp_gdb_path, fc_name)
            temp_lyr = "temp_lyr"

            messages.addMessage(f"== Menjalankan Anselin Local Moran's I untuk Kelas Jalan: {i} ==")
            
            delete_if_exists(out_path)
            delete_if_exists(temp_lyr)

            arcpy.management.MakeFeatureLayer(
                jaringanjalan_path, 
                temp_lyr, 
                f"s_klsjln = {i}"
            )

            row_count = int(arcpy.management.GetCount(temp_lyr)[0])
            messages.addMessage(f"   Jumlah record ditemukan: {row_count}")

            if row_count <= 2:
                messages.addMessage(f"   --> Kelas Jalan {i} dilewati. Butuh minimal 3 data spasial.")
                delete_if_exists(temp_lyr)
                continue

            try:
                arcpy.stats.ClustersOutliers(
                    temp_lyr,
                    "lb_jln",
                    out_path,
                    "INVERSE_DISTANCE_SQUARED",
                    "EUCLIDEAN_DISTANCE",
                    "NONE"
                )
                messages.addMessage("   --> Analisis Selesai.")

                delete_if_exists(lyr_name)
                if arcpy.Exists(out_path):
                    arcpy.management.MakeFeatureLayer(out_path, lyr_name)
                    if os.path.exists(sim_path):
                        arcpy.management.ApplySymbologyFromLayer(lyr_name, sim_path)
                    
                    # Set value ke parameter agar muncul di Map
                    parameters[param_idx].value = lyr_name

            except arcpy.ExecuteError:
                messages.addWarningMessage(f"   --> Error pada Kelas Jalan {i}")
                list_err.append(f"{fc_name}, {arcpy.GetMessages(2)}")
            
            finally:
                delete_if_exists(temp_lyr)

        if list_err:
            err_outlier_path = os.path.join(appdata, "err_outlier.err")
            with open(err_outlier_path, "w") as conf_file:
                conf_file.write("\n".join(list_err) + "\n")
            messages.addWarningMessage("Ada error yang direkam ke dalam file err_outlier.err")

        # --- 6. Set Jaringan Jalan Keseluruhan di TOC ---
        jaringanjalan_layer = "Jaringan_Jalan"
        delete_if_exists(jaringanjalan_layer)
        
        arcpy.management.MakeFeatureLayer(jaringanjalan_path, jaringanjalan_layer)
        if os.path.exists(no_sim_path):
            arcpy.management.ApplySymbologyFromLayer(jaringanjalan_layer, no_sim_path)

class Tampilkan_Simbologi_Kelas_Jalan(object):

    def __init__(self):
        self.label = "Tampilkan Simbologi Kelas Jalan"
        self.description = "Menerapkan simbologi."
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
        messages.addMessage("== Proses dimulai ==")

        # 1. Ambil Konfigurasi dan Setup Path
        configs = persil.get_config_values()
        dataset_path = configs['project_config']['dataset_path']
        jaringanjalan = "Jaringan_Jalan"
        
        # PERBAIKAN: Menggabungkan dataset path dengan nama jaringan jalan
        jaringanjalan_path = os.path.join(dataset_path, jaringanjalan)
        simbologi_path = r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Simbologi_Kelas_Jaringan_Jalan.lyrx"
        temp_layer = "temp_layer"

        # Fungsi pembantu untuk menghapus item
        def delete_if_exists(item):
            if arcpy.Exists(item):
                try:
                    arcpy.management.Delete(item)
                except Exception as e:
                    messages.addWarningMessage(f"Gagal menghapus temp data {item}: {e}")

        delete_if_exists(temp_layer)

        # 2. Cek dan Tambahkan Kolom (Field) Jika Belum Ada
        field_names = [field.name for field in arcpy.ListFields(jaringanjalan_path)]

        if "kls_jln" not in field_names:
            messages.addMessage("--> Menambahkan field 'kls_jln'")
            arcpy.management.AddField(jaringanjalan_path, "kls_jln", "TEXT")

        if "s_klsjln" not in field_names:
            messages.addMessage("--> Menambahkan field 's_klsjln'")
            arcpy.management.AddField(jaringanjalan_path, "s_klsjln", "SHORT")

        # 3. Update Kolom yang Kosong (NULL)
        messages.addMessage("== Update kelas jalan kosong ==")
        arcpy.management.MakeFeatureLayer(jaringanjalan_path, temp_layer)

        # Seleksi record yang kosong
        arcpy.management.SelectLayerByAttribute(temp_layer, "NEW_SELECTION", "kls_jln IS NULL")

        # Cek berapa banyak data yang kosong
        row_count = int(arcpy.management.GetCount(temp_layer)[0])
        
        if row_count > 0:
            messages.addMessage(f"--> Mengupdate {row_count} record menjadi kelas 'Lokal'...")
            arcpy.management.CalculateField(temp_layer, "kls_jln", '"Lokal"', "PYTHON3")
            arcpy.management.CalculateField(temp_layer, "s_klsjln", "1", "PYTHON3")
        else:
            messages.addMessage("--> Tidak ada record bernilai NULL. Update dilewati.")

        delete_if_exists(temp_layer)
        delete_if_exists(jaringanjalan)

        # 4. Buat Layer Output dan Terapkan Simbologi
        arcpy.management.MakeFeatureLayer(jaringanjalan_path, jaringanjalan)

        if os.path.exists(simbologi_path):
            messages.addMessage("== Menerapkan file simbologi ==")
            arcpy.management.ApplySymbologyFromLayer(jaringanjalan, simbologi_path)
        else:
            messages.addWarningMessage(f"== PERINGATAN: File simbologi tidak ditemukan di:\n{simbologi_path} ==")

        # Kirim layer ke Map ArcGIS
        parameters[0].value = jaringanjalan

        messages.addMessage("== Proses selesai ==")
        return