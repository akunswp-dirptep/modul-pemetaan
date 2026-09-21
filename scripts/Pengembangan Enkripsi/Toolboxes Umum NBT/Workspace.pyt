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
        self.tools = [Import_Workspace, Buat_Workspace]

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
                'path': {
                    constant.TEMPLATE_LAYER_NETWORK_DATASET_JARINGAN_JALAN: nd_path,
                    constant.TEMPLATE_LAYER_FEATURE_CLASS_JARINGAN_JALAN: jaringan_jalan_nd_path
                },
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

        conf_file = open(conf_path, "w")
        conf_file.write(json.dumps(json_config, indent=4))
        conf_file.close()

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