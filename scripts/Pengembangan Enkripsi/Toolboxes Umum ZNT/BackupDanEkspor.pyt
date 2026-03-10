# -*- coding: utf-8 -*-
from datetime import datetime
import sys
import arcpy, os, zipfile
import time

arcpy.env.outputZFlag = "Disabled"
arcpy.env.outputMFlag = "Disabled"

# Tambahkan parent directory ke sys.path
script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from zntutils import zona_layer as zonalayer

arcpy.env.outputZFlag = "Disabled"  
arcpy.env.outputMFlag = "Disabled"  


class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [Ekspor_Geodatabase, Ekspor_Zona]


class Ekspor_Geodatabase:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Ekspor Geodatabase"
        self.description = ""

    def getParameterInfo(self):

        """
        Kondisi yang harus dipenuhi oleh parameter pada tool ini:
        1. Hanya menerima path file (DEFile) sebagai output ZIP
        2. Filter file harus diatur untuk hanya menerima file dengan ekstensi .zip
        """

        
        #  Pemenuhan kondisi 1: Hanya menerima path file (DEFile) sebagai output ZIP
        output_zip_file = arcpy.Parameter(
            displayName="File ZIP (.zip)",
            name="output_zip_file",
            datatype="DEFile",
            parameterType="Required",
            direction="Output"
        )

        # Pemenuhan kondisi 2: Filter file harus diatur untuk hanya menerima file dengan ekstensi .zip
        output_zip_file.filter.list = ["zip"]

        params = [output_zip_file]
        return params

    def isLicensed(self):
        """Set whether the tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter. This method is called after internal validation."""
        return

    def execute(self, parameters, messages):

        """
        Pemenuhan kondisi yang harus dipenuhi oleh program pada tool ini:
        1. Menyimpan file ZIP yang dihasilkan ke lokasi yang dipilih oleh pengguna melalui parameter input.
        2. Melakukan pengecekan terlebihb dahulu apakah lokasi yang dipilih valid dan dapat diakses sebelum menyimpan file ZIP.
        """

        zl_path = zonalayer.is_zona_layer_comply(show_path_message=False)
        ws_dir = os.path.dirname(os.path.dirname(os.path.dirname(zl_path)))
        zip_path = parameters[0].valueAsText
        zip_filename = os.path.basename(zip_path)
        
        ws_baru = os.path.dirname(zip_path)
        arcpy.AddMessage(f"Path workspace: {ws_baru}")


        if ws_baru:
            # Pemenuhan kondisi 2: Melakukan pengecekan terlebihb dahulu apakah lokasi yang dipilih valid dan dapat diakses sebelum menyimpan file ZIP.
            parent_dir = os.path.dirname(ws_baru)

            if not os.path.exists(parent_dir) and parent_dir != "":
                arcpy.AddError(f"Directory parent tidak ditemukan: {parent_dir}")
            else:
                # Pemenuhan kondisi 1: Menyimpan file ZIP yang dihasilkan ke lokasi yang dipilih oleh pengguna melalui parameter input.
                zip_file_path = self.compress_directory_to_zip(ws_dir, ws_baru, zip_filename)
                
                if zip_file_path:
                    arcpy.AddMessage(f"Proses kompresi selesai. File ZIP: {zip_file_path}")
                else:
                    arcpy.AddError("Gagal mengompresi workspace setelah beberapa percobaan")
        else:
            arcpy.AddError("Folder tujuan tidak valid")
        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return
    
    def compress_directory_to_zip(self, source_dir, output_folder, zip_filename):
        """
        Mengompresi seluruh direktori menjadi file ZIP dan disimpan di folder tujuan
        Melewati file yang terkunci oleh ArcGIS
        
        Parameters:
        source_dir (str): Path direktori yang akan dikompresi
        output_folder (str): Path folder tujuan untuk menyimpan file ZIP
        """
        try:
            arcpy.AddMessage(f"Mengompresi direktori: {source_dir}")
            arcpy.AddMessage(f"Folder tujuan: {output_folder}")
            
            # Pastikan folder tujuan exists
            if not os.path.exists(output_folder):
                os.makedirs(output_folder)
                arcpy.AddMessage(f"Folder tujuan dibuat: {output_folder}")
            
            # Generate nama file ZIP berdasarkan nama folder source dan timestamp
            source_name = os.path.basename(source_dir)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if not zip_filename:
                zip_filename = f"{source_name}_backup_{timestamp}.zip"
            output_zip_path = os.path.join(output_folder, zip_filename)
            
            arcpy.AddMessage(f"Membuat file ZIP: {zip_filename}")
            
            # List file yang akan di-skip (file lock ArcGIS)
            skip_extensions = ['.lock', '.sr.lock']
            skip_keywords = ['.LAPTOP-', '.DESKTOP-']
            
            # Buat file ZIP
            with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Walk melalui semua file dan subdirektori
                for root, dirs, files in os.walk(source_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        
                        # Skip file lock ArcGIS
                        if any(file.endswith(ext) for ext in skip_extensions) or any(keyword in file for keyword in skip_keywords):

                            continue
                        
                        # Skip file yang sedang digunakan/dikunci
                        try:
                            # Coba buka file untuk membaca (test jika file terkunci)
                            with open(file_path, 'rb') as test_file:
                                pass
                                
                            # Hitung path relatif untuk disimpan dalam ZIP
                            arcname = os.path.relpath(file_path, source_dir)
                            zipf.write(file_path, arcname)
                            
                        except (PermissionError, IOError) as e:
                            arcpy.AddWarning(f"  Tidak dapat mengakses file (mungkin terkunci): {file} - {str(e)}")
                            continue
                        except Exception as e:
                            arcpy.AddWarning(f"  Error pada file {file}: {str(e)}")
                            continue

            return output_zip_path
            
        except Exception as e:
            arcpy.AddError(f"Error dalam kompresi ZIP: {str(e)}")
            return None

    def compress_with_retry(self, source_dir, output_folder, zip_filename, max_retries=3):
        """
        Mencoba kompresi dengan beberapa kali retry jika ada file terkunci
        """
        for attempt in range(max_retries):
            arcpy.AddMessage(f"Percobaan kompresi ke-{attempt + 1}")
            
            result = self.compress_directory_to_zip(source_dir, output_folder, zip_filename)
            if result:
                return result
            
            if attempt < max_retries - 1:
                arcpy.AddMessage(f"Menunggu 2 detik sebelum mencoba lagi...")
                time.sleep(2)
        
        return None

class Ekspor_Zona:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Ekspor Zona"
        self.description = ""

    def getParameterInfo(self):
        """
        Kondisi yang harus dipenuhi oleh parameter pada tool ini:
        1. Hanya menerima input folder (DEFolder) sebagai output ZIP
        """

        # Pemenuhan kondisi 1: Hanya menerima input folder (DEFolder) sebagai output ZIP
        folder_output= arcpy.Parameter(
            displayName="Folder Output",
            name="output_folder",
            datatype="DEFolder",
            parameterType="Required",
            direction="Input"
        )

        params = [folder_output]
        return params

    def isLicensed(self):
        """Set whether the tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter. This method is called after internal validation."""
        return
    def execute(self, parameters, messages):
        """The source code of the tool."""


        config_dan_paths = zonalayer.get_config_values()
        lokasi = config_dan_paths['provinsi']
        tahun = config_dan_paths['tahun']
        out = parameters[0].valueAsText
        zl_path = config_dan_paths['zl_path']
        # Define input layer and output shapefile path
        shp_name = "Zona_Layer_" + lokasi + "_" + tahun + ".shp"
        output_shp = os.path.join(out, shp_name)

        # If the shapefile already exists, delete it
        if arcpy.Exists(output_shp):
            arcpy.management.Delete(output_shp)

        # Project and export the shapefile
        out_coordinate_system = arcpy.Describe(zl_path).spatialReference
        arcpy.management.Project(zl_path, output_shp, out_coordinate_system)

        # Zipping the shapefile components
        def zip_shapefile(shp_path):

            base_name = os.path.splitext(shp_path)[0]
            

            extensions = [".shp", ".shx", ".dbf", ".prj", ".cpg", ".shp.xml", ".sbn", ".sbx"]  # Add other extensions if needed
            files_to_zip = [base_name + ext for ext in extensions if os.path.exists(base_name + ext)]
            

            zip_path = base_name + ".zip"
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file in files_to_zip:
                    zipf.write(file, os.path.basename(file))  \

            arcpy.AddMessage(f"== Zipping completed: {zip_path} ==")

        zip_shapefile(output_shp)

        arcpy.AddMessage("== Proses selesai ==")

        return