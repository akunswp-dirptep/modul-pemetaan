from datetime import datetime
import sys
import uuid
import arcpy, os, json, zipfile

arcpy.env.outputZFlag = "Disabled"
arcpy.env.outputMFlag = "Disabled"

script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
from nbtutils import persil, constant
from zntutils.constant import PREFERRED_BERKAS_ID, CREDENTIAL_KEY, PREFERRED_SERVER_KEY, AUTH_KEY, NAMA_PROVINSI, KAB_KOTA
from zntutils import system_utils


def current_year():
    try:
        return int(datetime.now().year)
    except Exception:
        return None
class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [Import_Workspace, 
                      Buat_Workspace, 
                      Edit_Konfigurasi_Umum_Workspace,
                      Edit_Skoring_Kelas_Jalan_Workspace,
                      Edit_Skoring_Zonasi_Workspace
                      ]

class Buat_Workspace(object):

    def __init__(self):
        self.label = "Buat Workspace NBT"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):

        workspace_folder = arcpy.Parameter(
            displayName='Workspace',
            name='folder_path',
            datatype='DEFolder',
            parameterType='Required',
            direction='Input'
        )

        koordinat_system = arcpy.Parameter(
            displayName='Referensi Sistem Koordinat',
            name='spatial_reference',
            datatype='GPSpatialReference',
            parameterType='Required',
            direction='Input'
        )

        provinsi = arcpy.Parameter(
            displayName="Provinsi",
            name="provinsi",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        provinsi.filter.type = "ValueList"
        provinsi.filter.list = NAMA_PROVINSI

        kab_kota = arcpy.Parameter(
            displayName="Kabupaten/Kota",
            name="kab_kota",
            datatype="GPString",
            parameterType="Required",
            direction="Input")

        tahun_penilaian = arcpy.Parameter(
            displayName="Tahun Penilaian",
            name="tahun_penilaian",
            datatype="GPLong",
            parameterType="Required",
            direction="Input"
        )

        tahun_penilaian.value = current_year()

        output_fl = arcpy.Parameter(
            name='fl_output',
            datatype='GPFeatureLayer',
            parameterType='Derived',
            direction='Output'
        )

        return [koordinat_system, workspace_folder,  provinsi, kab_kota, tahun_penilaian, output_fl]

    def updateParameters(self, parameters):
        prov = parameters[2].valueAsText  # parameter Provinsi
        kab = parameters[3]               # parameter Kab/Kota

        if prov:
            kab.filter.type = "ValueList"
            kab.filter.list = KAB_KOTA.get(prov, [])
        else:
            kab.filter.list = []

    def execute(self, parameters, messages):

        folder_path = parameters[1].valueAsText
        spatial_reference = parameters[0].value
        provinsi = parameters[2].valueAsText
        kab_kota = parameters[3].valueAsText
        tahun_penilaian = parameters[4].value

        appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

        conf_path = os.path.join(folder_path, constant.PROJECT_CONFIG_FILE_NAME)
        id = str(uuid.uuid4())

        if arcpy.Exists(conf_path):
            arcpy.management.Delete(conf_path)

        gdbname = "NilaiBidangTanah.gdb"

        dataset = "nbt_ds"
        dataset_fasilitas = "fasilitas_ds"
        dataset_resiko = "resiko_ds"

        spatial_analysis_ds = "spatial_analysis_template_ds"
        # spatial_analysis_ds = "ds_znt_template"

        utils_folder = os.path.join(appdata, 'nbtutils')

        spatial_analysis_ds_path = os.path.join(
            utils_folder,
            "template.gdb",
            spatial_analysis_ds
        )

        gdb_path = os.path.join(folder_path, gdbname)

        dataset_path = os.path.join(gdb_path, dataset)
        dataset_fasilitas_path = os.path.join(gdb_path, dataset_fasilitas)
        dataset_resiko_path = os.path.join(gdb_path, dataset_resiko)

        nd_path = os.path.join(
            gdb_path,
            spatial_analysis_ds,
            constant.TEMPLATE_LAYER_NETWORK_DATASET_JARINGAN_JALAN
        )

        jaringan_jalan_nd_path = os.path.join(
            gdb_path,
            spatial_analysis_ds,
            constant.TEMPLATE_LAYER_FEATURE_CLASS_JARINGAN_JALAN
        )

        json_config = {
            'project_config': {
                'id': id,
                'ws_path': folder_path,
                'conf_path': conf_path,
                'gdb_path': gdb_path,
                'dataset_path': dataset_path,
                'skala': 1000,
                'provinsi': provinsi,
                'kab_kota': kab_kota,
                'tahun_penilaian': tahun_penilaian,
                'daftar_variabel_path': os.path.join(
                    folder_path,
                    constant.KONFIG_DAFTAR_VARIABEL
                )
            },

            'jaringan_jalan_config': {
                'skoring' : constant.SKORING_KELAS_JALAN
            },

            'persil_config': {
                'skoring' : {
                    'zonasi' : constant.SKORING_ZONASI,
                    'bentuk_persil' : constant.SKORING_BENTUK_PERSIL,
                    'letak' : constant.SKORING_LETAK
                }

            },

            'fasilitas_config': {
                'dataset_path': dataset_fasilitas_path
            },

            'resiko_config': {
                'dataset_path': dataset_resiko_path
            }
        }

        if arcpy.Exists(gdb_path):
            arcpy.management.Delete(gdb_path)

        system_utils.setup_project_config(json_config, conf_path)

        arcpy.management.CreateFileGDB(folder_path, gdbname)
        arcpy.management.CreateFeatureDataset(gdb_path,  dataset,  spatial_reference)
        arcpy.management.CreateFeatureDataset(gdb_path, dataset_fasilitas, spatial_reference)
        arcpy.management.CreateFeatureDataset(gdb_path, dataset_resiko, spatial_reference)

        fl = arcpy.management.CreateFeatureclass(
            dataset_path,
            constant.LAYER_PERSIL,
            "POLYGON",
            spatial_reference=spatial_reference
        )[0]

        arcpy.AddMessage("Menyalin template ke dalam workspace baru")

        saved_template = os.path.join(gdb_path, spatial_analysis_ds)

        arcpy.management.Project(
            spatial_analysis_ds_path,
            saved_template,
            spatial_reference
        )

        aprx = arcpy.mp.ArcGISProject("CURRENT")

        folder_connections = aprx.folderConnections

        if not any(
            fc['connectionString'] == folder_path
            for fc in folder_connections
        ):

            folder_connections.append({
                'connectionString': folder_path,
                'isHomeFolder': False
            })

            aprx.updateFolderConnections(
                folder_connections,
                validate=True
            )
        arcpy.SetParameter(5, fl)
        arcpy.AddMessage("Workspace berhasil dibuat")

class Edit_Konfigurasi_Umum_Workspace(object):

    def __init__(self):
        self.label = "Edit Konfigurasi Umum"
        self.description = (
            "Tool untuk membaca dan mengedit konfigurasi Umum workspace NBT."
        )
        self.canRunInBackground = False

    def getParameterInfo(self):
        workspace_folder = arcpy.Parameter(
            displayName="Pilih Folder Workspace",
            name="workspace_folder",
            datatype="DEFolder",
            parameterType="Required",
            direction="Input",
        )

        update_path = arcpy.Parameter(
            displayName="Perbarui lokasi folder workspace",
            name="update_path",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input",
        )
        update_path.value = False

        provinsi = arcpy.Parameter(
            displayName="Provinsi",
            name="provinsi",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
        )
        provinsi.filter.type = "ValueList"
        provinsi.filter.list = NAMA_PROVINSI

        kab_kota = arcpy.Parameter(
            displayName="Kabupaten/Kota",
            name="kab_kota",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
        )

        tahun_penilaian = arcpy.Parameter(
            displayName="Tahun Penilaian",
            name="tahun_penilaian",
            datatype="GPLong",
            parameterType="Required",
            direction="Input",
        )

        out_layer = arcpy.Parameter(
            displayName="Output Layer",
            name="out_layer",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output",
        )

        return [
            workspace_folder,
            update_path,
            provinsi,
            kab_kota,
            tahun_penilaian,
            out_layer,
        ]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        ws_param = parameters[0]
        prov_param = parameters[2]
        kab_param = parameters[3]
        thn_param = parameters[4]

        # Otomatis isi parameter dari file konfigurasi jika folder dipilih
        if ws_param.value and not ws_param.hasBeenValidated:
            ws_folder = ws_param.valueAsText
            config_path = os.path.join(
                ws_folder, constant.PROJECT_CONFIG_FILE_NAME
            )

            if os.path.exists(config_path):
                try:
                    config_data = system_utils.get_all_config(config_path)
                    project_config = config_data.get("project_config")

                    if isinstance(project_config, dict):
                        if not prov_param.altered:
                            prov_param.value = project_config.get("provinsi")
                        if not kab_param.altered:
                            kab_param.value = project_config.get("kab_kota")
                        if not thn_param.altered:
                            thn_param.value = project_config.get("tahun_penilaian")
                except Exception:
                    pass

        # Update pilihan filter Kabupaten/Kota berdasarkan Provinsi
        prov = prov_param.valueAsText
        if prov:
            kab_param.filter.type = "ValueList"
            kab_param.filter.list = KAB_KOTA.get(prov, [])
        else:
            kab_param.filter.list = []

    def updateMessages(self, parameters):
        ws_param = parameters[0]
        if ws_param.value:
            config_path = os.path.join(
                ws_param.valueAsText, constant.PROJECT_CONFIG_FILE_NAME
            )
            if not os.path.exists(config_path):
                ws_param.setErrorMessage(
                    "File konfigurasi (config) tidak ditemukan di dalam folder ini."
                )

    def execute(self, parameters, messages):
        ws_folder = parameters[0].valueAsText
        update_path_flag = parameters[1].value
        WADMPR = parameters[2].valueAsText
        WADMKK = parameters[3].valueAsText
        THNNILAI = parameters[4].valueAsText

        config_path = os.path.join(
            ws_folder, constant.PROJECT_CONFIG_FILE_NAME
        )

        if not os.path.exists(config_path):
            arcpy.AddError(
                "Proses dihentikan: File konfigurasi tidak ditemukan."
            )
            return

        try:
            # 1. Baca dan validasi data konfigurasi
            config_data = system_utils.get_all_config(config_path)
            if not isinstance(config_data, dict):
                arcpy.AddError(
                    "Format file konfigurasi tidak valid atau rusak."
                )
                return

            project_config = config_data.get("project_config", {})

            # 2. Timpa informasi atribut
            project_config["provinsi"] = WADMPR
            project_config["kab_kota"] = WADMKK
            project_config["tahun_penilaian"] = THNNILAI

            # 3. Logika Perbarui Path, Folder Connections, & Muat Layer
            if update_path_flag:
                config_data["ws_path"] = ws_folder
                config_data["gdb_path"] = os.path.join(
                    ws_folder, "ZoneNilaiTanah.gdb"
                )
                config_data["dataset_path"] = os.path.join(
                    ws_folder, "ZoneNilaiTanah.gdb", "znt_ds"
                )
                arcpy.AddMessage("✅ Path Workspace, GDB, dan Dataset telah disesuaikan.")

                # Update Folder Connections di Catalog ArcGIS Pro
                aprx = arcpy.mp.ArcGISProject("CURRENT")
                folder_connections = aprx.folderConnections

                if not any(
                    fc["connectionString"] == ws_folder
                    for fc in folder_connections
                ):
                    folder_connections.append(
                        {"connectionString": ws_folder, "isHomeFolder": False}
                    )
                    aprx.updateFolderConnections(
                        folder_connections, validate=True
                    )
                    arcpy.AddMessage(
                        f"📂 Folder {ws_folder} berhasil ditambahkan ke Folder Connections."
                    )
                else:
                    arcpy.AddMessage(
                        "ℹ️ Folder ini sudah terhubung di Catalog ArcGIS Pro."
                    )

                # Set Layer Output ke Peta
                zona_layer_path = os.path.join(
                    config_data["dataset_path"], "Zona_Layer"
                )
                if arcpy.Exists(zona_layer_path):
                    arcpy.SetParameter(5, zona_layer_path)  # Index 5 = out_layer
                    arcpy.AddMessage(
                        "🗺️ Layer Zona_Layer berhasil dimuat ke dalam peta."
                    )
                else:
                    arcpy.AddWarning(
                        f"⚠️ Zona_Layer tidak ditemukan di: {zona_layer_path}"
                    )

            # 4. Tulis kembali konfigurasi
            system_utils.setup_project_config(config_data, config_path)

            arcpy.AddMessage("✅ Konfigurasi workspace berhasil disimpan!")
            arcpy.AddMessage(f"   -> Tahun Penilaian: {THNNILAI}")
            arcpy.AddMessage(f"   -> Lokasi: {WADMKK}, {WADMPR}")

        except Exception as e:
            arcpy.AddError(
                f"Terjadi kesalahan saat mengedit file konfigurasi: {e}"
            )

class Edit_Skoring_Kelas_Jalan_Workspace(object):

    def __init__(self):
        self.label = "Edit Skoring Kelas Jalan"
        self.description = "Tool untuk membaca dan mengedit nilai skoring kelas jalan pada konfigurasi workspace NBT."
        self.canRunInBackground = False

    def getParameterInfo(self):
        # 0. Parameter Folder Workspace
        workspace_folder = arcpy.Parameter(
            displayName="Pilih Folder Workspace",
            name="workspace_folder",
            datatype="DEFolder",
            parameterType="Required",
            direction="Input",
        )

        # 1. Parameter Setapak
        param_setapak = arcpy.Parameter(
            displayName="Skor Setapak",
            name="skor_setapak",
            datatype="GPLong",
            parameterType="Required",
            direction="Input",
        )

        # 2. Parameter Lokal Sekunder
        param_lokal_sekunder = arcpy.Parameter(
            displayName="Skor Lokal Sekunder",
            name="skor_lokal_sekunder",
            datatype="GPLong",
            parameterType="Required",
            direction="Input",
        )

        # 3. Parameter Lokal Primer
        param_lokal_primer = arcpy.Parameter(
            displayName="Skor Lokal Primer",
            name="skor_lokal_primer",
            datatype="GPLong",
            parameterType="Required",
            direction="Input",
        )

        # 4. Parameter Kolektor Sekunder
        param_kolektor_sekunder = arcpy.Parameter(
            displayName="Skor Kolektor Sekunder",
            name="skor_kolektor_sekunder",
            datatype="GPLong",
            parameterType="Required",
            direction="Input",
        )

        # 5. Parameter Kolektor Primer
        param_kolektor_primer = arcpy.Parameter(
            displayName="Skor Kolektor Primer",
            name="skor_kolektor_primer",
            datatype="GPLong",
            parameterType="Required",
            direction="Input",
        )

        # 6. Parameter Arteri Sekunder
        param_arteri_sekunder = arcpy.Parameter(
            displayName="Skor Arteri Sekunder",
            name="skor_arteri_sekunder",
            datatype="GPLong",
            parameterType="Required",
            direction="Input",
        )

        # 7. Parameter Arteri Primer
        param_arteri_primer = arcpy.Parameter(
            displayName="Skor Arteri Primer",
            name="skor_arteri_primer",
            datatype="GPLong",
            parameterType="Required",
            direction="Input",
        )

        return [
            workspace_folder,
            param_setapak,
            param_lokal_sekunder,
            param_lokal_primer,
            param_kolektor_sekunder,
            param_kolektor_primer,
            param_arteri_sekunder,
            param_arteri_primer
        ]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        ws_param = parameters[0]

        # Otomatis isi parameter skor dari file konfigurasi jika folder dipilih
        if ws_param.value and not ws_param.hasBeenValidated:
            ws_folder = ws_param.valueAsText
            config_path = os.path.join(ws_folder, constant.PROJECT_CONFIG_FILE_NAME)

            if os.path.exists(config_path):
                try:
                    config_data = system_utils.get_all_config(config_path)
                    
                    # Ambil data skoring kelas jalan
                    jalan_config = config_data.get("jaringan_jalan_config", {}).get("skoring", {}).get("kelas_jalan", {})

                    if isinstance(jalan_config, dict):
                        # Set nilai parameter jika user belum mengubahnya secara manual
                        if not parameters[1].altered:
                            parameters[1].value = jalan_config.get("Setapak", 1)
                        if not parameters[2].altered:
                            parameters[2].value = jalan_config.get("Lokal Sekunder", 2)
                        if not parameters[3].altered:
                            parameters[3].value = jalan_config.get("Lokal Primer", 3)
                        if not parameters[4].altered:
                            parameters[4].value = jalan_config.get("Kolektor Sekunder", 4)
                        if not parameters[5].altered:
                            parameters[5].value = jalan_config.get("Kolektor Primer", 5)
                        if not parameters[6].altered:
                            parameters[6].value = jalan_config.get("Arteri Sekunder", 6)
                        if not parameters[7].altered:
                            parameters[7].value = jalan_config.get("Arteri Primer", 7)
                except Exception:
                    pass

    def updateMessages(self, parameters):
        ws_param = parameters[0]
        if ws_param.value:
            config_path = os.path.join(ws_param.valueAsText, constant.PROJECT_CONFIG_FILE_NAME)
            if not os.path.exists(config_path):
                ws_param.setErrorMessage("File konfigurasi (config) tidak ditemukan di dalam folder ini.")

    def execute(self, parameters, messages):
        ws_folder = parameters[0].valueAsText
        
        # Ambil nilai input dari user
        val_setapak = parameters[1].value
        val_lokal_sekunder = parameters[2].value
        val_lokal_primer = parameters[3].value
        val_kolektor_sekunder = parameters[4].value
        val_kolektor_primer = parameters[5].value
        val_arteri_sekunder = parameters[6].value
        val_arteri_primer = parameters[7].value

        config_path = os.path.join(ws_folder, constant.PROJECT_CONFIG_FILE_NAME)

        if not os.path.exists(config_path):
            arcpy.AddError("Proses dihentikan: File konfigurasi tidak ditemukan.")
            return

        try:
            # 1. Baca data konfigurasi
            config_data = system_utils.get_all_config(config_path)
            if not isinstance(config_data, dict):
                arcpy.AddError("Format file konfigurasi tidak valid atau rusak.")
                return

            # 2. Pastikan struktur dictionary untuk jaringan jalan tersedia
            if "jaringan_jalan_config" not in config_data:
                config_data["jaringan_jalan_config"] = {}
            if "skoring" not in config_data["jaringan_jalan_config"]:
                config_data["jaringan_jalan_config"]["skoring"] = {}
            if "kelas_jalan" not in config_data["jaringan_jalan_config"]["skoring"]:
                config_data["jaringan_jalan_config"]["skoring"]["kelas_jalan"] = {}

            # 3. Timpa nilai skoring kelas jalan dengan inputan baru
            config_data["jaringan_jalan_config"]["skoring"]["kelas_jalan"]["Setapak"] = val_setapak
            config_data["jaringan_jalan_config"]["skoring"]["kelas_jalan"]["Lokal Sekunder"] = val_lokal_sekunder
            config_data["jaringan_jalan_config"]["skoring"]["kelas_jalan"]["Lokal Primer"] = val_lokal_primer
            config_data["jaringan_jalan_config"]["skoring"]["kelas_jalan"]["Kolektor Sekunder"] = val_kolektor_sekunder
            config_data["jaringan_jalan_config"]["skoring"]["kelas_jalan"]["Kolektor Primer"] = val_kolektor_primer
            config_data["jaringan_jalan_config"]["skoring"]["kelas_jalan"]["Arteri Sekunder"] = val_arteri_sekunder
            config_data["jaringan_jalan_config"]["skoring"]["kelas_jalan"]["Arteri Primer"] = val_arteri_primer

            # 4. Tulis kembali konfigurasi (Simpan)
            system_utils.setup_project_config(config_data, config_path)

            # 5. Pesan sukses
            arcpy.AddMessage("✅ Konfigurasi skoring kelas jalan berhasil disimpan!")
            arcpy.AddMessage(f"   -> Setapak: {val_setapak}")
            arcpy.AddMessage(f"   -> Lokal Sekunder: {val_lokal_sekunder}")
            arcpy.AddMessage(f"   -> Lokal Primer: {val_lokal_primer}")
            arcpy.AddMessage(f"   -> Kolektor Sekunder: {val_kolektor_sekunder}")
            arcpy.AddMessage(f"   -> Kolektor Primer: {val_kolektor_primer}")
            arcpy.AddMessage(f"   -> Arteri Sekunder: {val_arteri_sekunder}")
            arcpy.AddMessage(f"   -> Arteri Primer: {val_arteri_primer}")

        except Exception as e:
            arcpy.AddError(f"Terjadi kesalahan saat mengedit file konfigurasi: {e}")

class Edit_Skoring_Zonasi_Workspace(object):

    def __init__(self):
        self.label = "Edit Skoring Zonasi"
        self.description = "Tool untuk membaca, menambah, menghapus, dan mengedit nilai skoring zonasi pada konfigurasi workspace NBT."
        self.canRunInBackground = False

    def getParameterInfo(self):
        # 0. Parameter Folder Workspace
        workspace_folder = arcpy.Parameter(
            displayName="Pilih Folder Workspace",
            name="workspace_folder",
            datatype="DEFolder",
            parameterType="Required",
            direction="Input",
        )

        # 1. Parameter Value Table untuk Zonasi
        param_zonasi = arcpy.Parameter(
            displayName="Tabel Skoring Zonasi",
            name="skoring_zonasi",
            datatype="GPValueTable",
            parameterType="Required",
            direction="Input",
        )
        
        # Mendefinisikan 2 kolom: Kolom 1 untuk Nama (String), Kolom 2 untuk Skor (Long/Integer)
        param_zonasi.columns = [["GPString", "Nama Zonasi"], ["GPLong", "Skor"]]

        return [workspace_folder, param_zonasi]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        ws_param = parameters[0]
        zonasi_param = parameters[1]

        # Otomatis isi parameter dari file konfigurasi jika folder dipilih
        if ws_param.value and not ws_param.hasBeenValidated:
            ws_folder = ws_param.valueAsText
            config_path = os.path.join(ws_folder, constant.PROJECT_CONFIG_FILE_NAME)

            if os.path.exists(config_path):
                try:
                    config_data = system_utils.get_all_config(config_path)
                    
                    # Ambil data skoring zonasi
                    zonasi_dict = config_data.get("persil_config", {}).get("skoring", {}).get("zonasi", {})

                    if isinstance(zonasi_dict, dict):
                        # Jika user belum mengutak-atik tabel, isi dengan data dari JSON
                        if not zonasi_param.altered:
                            # Format ValueTable membutuhkan List of Lists: [[nama1, skor1], [nama2, skor2]]
                            table_values = []
                            for nama, skor in zonasi_dict.items():
                                table_values.append([nama, skor])
                            
                            zonasi_param.values = table_values
                except Exception:
                    pass

    def updateMessages(self, parameters):
        ws_param = parameters[0]
        if ws_param.value:
            config_path = os.path.join(ws_param.valueAsText, constant.PROJECT_CONFIG_FILE_NAME)
            if not os.path.exists(config_path):
                ws_param.setErrorMessage("File konfigurasi (config) tidak ditemukan di dalam folder ini.")

    def execute(self, parameters, messages):
        ws_folder = parameters[0].valueAsText
        zonasi_table_values = parameters[1].value # Mengembalikan list of lists / recordset

        config_path = os.path.join(ws_folder, constant.PROJECT_CONFIG_FILE_NAME)

        if not os.path.exists(config_path):
            arcpy.AddError("Proses dihentikan: File konfigurasi tidak ditemukan.")
            return

        try:
            # 1. Baca data konfigurasi
            config_data = system_utils.get_all_config(config_path)
            if not isinstance(config_data, dict):
                arcpy.AddError("Format file konfigurasi tidak valid atau rusak.")
                return

            # 2. Pastikan struktur dictionary untuk persil_config tersedia
            if "persil_config" not in config_data:
                config_data["persil_config"] = {}
            if "skoring" not in config_data["persil_config"]:
                config_data["persil_config"]["skoring"] = {}
            
            # 3. Konversi data dari Value Table UI kembali menjadi Dictionary
            new_zonasi_dict = {}
            if zonasi_table_values:
                for row in zonasi_table_values:
                    # row[0] adalah Nama Zonasi, row[1] adalah Skor
                    nama_zonasi = row[0]
                    skor_zonasi = row[1]
                    
                    if nama_zonasi: # Pastikan namanya tidak kosong
                        # Handle jika user mengosongkan skor, beri default 0
                        new_zonasi_dict[nama_zonasi] = int(skor_zonasi) if skor_zonasi is not None else 0

            # 4. Timpa data zonasi lama dengan dictionary yang baru dibuat
            config_data["persil_config"]["skoring"]["zonasi"] = new_zonasi_dict

            # 5. Tulis kembali konfigurasi (Simpan ke JSON)
            system_utils.setup_project_config(config_data, config_path)

            # 6. Pesan sukses
            arcpy.AddMessage("✅ Konfigurasi skoring zonasi berhasil diperbarui!")
            arcpy.AddMessage("Daftar Skoring Zonasi saat ini:")
            for k, v in new_zonasi_dict.items():
                arcpy.AddMessage(f"   -> {k}: {v}")

        except Exception as e:
            arcpy.AddError(f"Terjadi kesalahan saat mengedit file konfigurasi: {e}")

class Import_Workspace(object):

    def __init__(self):

        self.label = "Import Workspace"
        self.description = "Tool untuk mengimpor workspace data ZNT."
    
    def getParameterInfo(self):
        zip_file = arcpy.Parameter(
            displayName="File ZIP berisi workspace (.zip)",
            name="zip_file",
            datatype="DEFile",
            parameterType="Required",
            direction="Input"
        )
        workspace_folder = arcpy.Parameter(
            displayName="Target Folder",
            name="output_path",
            datatype="DEFolder",
            parameterType="Required",
            direction="Input")
        
        output_zl_path = arcpy.Parameter(
            name="output_zl_path",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )
        return [zip_file, workspace_folder, output_zl_path]

    def isLicensed(self):
        """Set whether the tool is licensed to execute."""
        return True
    
    def updateParameters(self, parameters):
        return
    
    def updateMessages(self, parameters):
        return
    
    def execute(self, parameters, messages):
        zipfile_path = parameters[0].valueAsText
        output_path = parameters[1].valueAsText
        if zipfile_path:
            arcpy.AddMessage(f"Memproses file: {zipfile_path}")
            success, persil_layer_path = self.check_and_extract_config(zipfile_path, output_path)
            if success:
                arcpy.AddMessage("Proses selesai dengan sukses")
                aprx = arcpy.mp.ArcGISProject("CURRENT")
                folder_connections = aprx.folderConnections

                # Path folder yang ingin ditambahkan
                new_folder = output_path

                # Cek apakah folder sudah ada
                if not any(fc['connectionString'] == new_folder for fc in folder_connections):
                    
                    # Tambahkan folder baru ke list
                    folder_connections.append({
                        'connectionString': new_folder,
                        'isHomeFolder': False
                    })

                    # Update folder connections
                    aprx.updateFolderConnections(folder_connections, validate=True)
                arcpy.SetParameter(2, persil_layer_path)
            else:
                arcpy.AddMessage("Proses tidak berhasil")
        else:
            arcpy.AddError("Tidak ada file zip yang dipilih")
        return
    
    def update_config_file(self, config_path, output_path):
        """
        Memperbarui file project_config.json dengan path yang baru
        """
        try:

            if config_path.endswith('.json'):
                with open(config_path, 'r', encoding='utf-8') as config_file:
                    configs = json.load(config_file)

            if not isinstance(configs, dict):
                raise ValueError("Format file config tidak valid")

            config_data = configs.get("project_config", {})

            # path lama
            old_ws_path = config_data.get("ws_path", "")

            # path baru
            new_ws_path = output_path

            # ------------------------------------------------------------------
            # Fungsi rekursif untuk mengganti seluruh path yang mengandung ws_path
            # ------------------------------------------------------------------
            def replace_paths(obj, old_root, new_root):
                if isinstance(obj, dict):
                    return {
                        key: replace_paths(value, old_root, new_root)
                        for key, value in obj.items()
                    }

                elif isinstance(obj, list):
                    return [
                        replace_paths(item, old_root, new_root)
                        for item in obj
                    ]

                elif isinstance(obj, str):
                    if old_root and obj.startswith(old_root):
                        return obj.replace(old_root, new_root, 1)
                    return obj

                return obj

            configs = replace_paths(configs, old_ws_path, new_ws_path)

            # ------------------------------------------------------------------
            # Pastikan beberapa path utama dibentuk ulang
            # ------------------------------------------------------------------
            configs["project_config"]["ws_path"] = new_ws_path
            configs["project_config"]["conf_path"] = os.path.join(
                new_ws_path,
                "project_config.json"
            )

            configs["project_config"]["gdb_path"] = os.path.join(
                new_ws_path,
                "NilaiBidangTanah.gdb"
            )

            configs["project_config"]["dataset_path"] = os.path.join(
                new_ws_path,
                "NilaiBidangTanah.gdb",
                "nbt_ds"
            )

            configs["project_config"]["daftar_variabel_path"] = os.path.join(
                new_ws_path,
                "konfigurasi_variabel.json"
            )
            with open(config_path, 'w', encoding='utf-8') as config_file:
                json.dump(configs, config_file, indent=4)
            
            return True
            
        except Exception as e:
            arcpy.AddError(f"Error saat memperbarui config.json: {e}")
            return False


    def check_and_extract_config(self, zip_path, output_path):
        """
        Mengecek apakah file zip mengandmung project_config.json
        dan melakukan ekstraksi jika ditemukan
        """
        zona_layer_path = None
        try:
            # Cek apakah file zip ada
            if not os.path.exists(zip_path):
                arcpy.AddError(f"File zip tidak ditemukan: {zip_path}")
                return False, None
            
            # Buka file zip untuk membaca isinya
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Dapatkan daftar semua file dalam zip
                file_list = zip_ref.namelist()
                
                # Cek apakah ada config.json atau config.dat
                has_config_json = any(
                    'project_config.json' in f.lower()
                    for f in file_list
                )
            
                
                if has_config_json:
                    arcpy.AddMessage("File config ditemukan dalam zip. Melakukan ekstraksi...")
                    
                    # Tentukan direktori tujuan ekstraksi
                    extract_dir = output_path
                    
                    # Buat direktori jika belum ada
                    if not os.path.exists(extract_dir):
                        os.makedirs(extract_dir)
                    
                    # Ekstrak semua file
                    zip_ref.extractall(extract_dir)
                    
                    # Cari path file config yang sebenarnya
                    config_path = None
                    for root, dirs, files in os.walk(extract_dir):
                        for file in files:
                            if file.lower() == 'project_config.json':
                                config_path = os.path.join(root, file)
                                break
                        if config_path:
                            break
                    
                    if config_path:
                        # Baca isi config file jika diperlukan
                        try:
                            update_success = self.update_config_file(config_path, output_path)                                
                            if update_success:



                                dataset_path = os.path.join(output_path, 'NilaiBidangTanah.gdb', 'nbt_ds')
                                persil_layer_peth = os.path.join(dataset_path, 'Persil_Layer')
                            else:
                                return False, None


                        except Exception as e:
                            arcpy.AddWarning(f"Tidak dapat membaca file config: {e}")
                            return False, None
                    else:
                        arcpy.AddError("File config tidak ditemukan setelah ekstraksi")
                        return False, None
                    
                    if persil_layer_peth is None:
                        arcpy.AddError("Path Zona_Layer tidak berhasil dibentuk dari config")
                        return False, None

                    return True, persil_layer_peth
                else:
                    arcpy.AddMessage("Tidak ditemukan config.json dalam file zip")
                    return False, None
                    
        except zipfile.BadZipFile:
            arcpy.AddError("File yang dipilih bukan file zip yang valid")
            return False, None
        except Exception as e:
            arcpy.AddError(f"Error saat memproses file zip: {e}")
            return False, None