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
from nbtutils import persil
class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [Import_Workspace]


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