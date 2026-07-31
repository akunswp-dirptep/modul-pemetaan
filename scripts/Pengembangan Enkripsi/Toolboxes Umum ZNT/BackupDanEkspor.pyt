# -*- coding: utf-8 -*-
from datetime import datetime, timezone
import sys, requests
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
from zntutils.system_utils import get_user_data, setup_user_data, get_all_berkas_id, clear_user_data
from zntutils.constant import PREFERRED_BERKAS_ID, AUTH_KEY, CREDENTIAL_KEY, PREFERRED_SERVER_KEY

arcpy.env.outputZFlag = "Disabled"  
arcpy.env.outputMFlag = "Disabled"  


class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [Ekspor_Workspace, Simpan_Workspace_Ke_Sipenta, Ekspor_Zona]


class Ekspor_Workspace:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Ekspor Workspace"
        self.description = ""

    def getParameterInfo(self):

        output_zip_file = arcpy.Parameter(
            displayName="Simpan Zip (.zip)",
            name="output_zip_file",
            datatype="DEFile",
            parameterType="Required",
            direction="Output"
        )

        output_zip_file.filter.list = ["zip"]

        # 1. Dapatkan path folder utama user (C:\Users\NamaUser)
        user_home_dir = os.path.expanduser('~')
        
        # 2. Arahkan ke folder Downloads
        downloads_folder = os.path.join(user_home_dir, 'Downloads')
        
        # 3. Buat nama file default (opsional: tambahkan timestamp agar tidak menimpa file lama)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"Backup_Workspace_{timestamp}.zip"
        
        # 4. Set nilai default parameter ke path lengkap tersebut
        output_zip_file.value = os.path.join(downloads_folder, default_filename)

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
        Mengompresi direktori menjadi file ZIP dan disimpan di folder tujuan.
        HANYA mengambil file 'penilaian_tanah_config.bin' dan folder 'Zonenilaitanah.gdb'.
        Melewati file yang terkunci oleh ArcGIS.
        
        Parameters:
        source_dir (str): Path direktori yang akan dikompresi
        output_folder (str): Path folder tujuan untuk menyimpan file ZIP
        zip_filename (str): Nama file ZIP (opsional)
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
                        
                        # Hitung path relatif di awal untuk keperluan filtering
                        arcname = os.path.relpath(file_path, source_dir)
                        
                        # Pecah path untuk mengecek apakah file berada di dalam folder ZoneNilaiTanah.gdb
                        path_parts = arcname.split(os.sep)
                        
                        # FILTER UTAMA: Lewati jika BUKAN ZoneNilaiTanah.gdb dan BUKAN penilaian_tanah_config.bin
                        if 'ZoneNilaiTanah.gdb' not in path_parts and file != 'penilaian_tanah_config.bin':
                            continue
                        
                        # Skip file lock ArcGIS
                        if any(file.endswith(ext) for ext in skip_extensions) or any(keyword in file for keyword in skip_keywords):
                            continue
                        
                        # Coba akses dan masukkan ke dalam ZIP
                        try:
                            # Coba buka file untuk membaca (test jika file terkunci)
                            with open(file_path, 'rb') as test_file:
                                pass
                                
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

class Simpan_Workspace_Ke_Sipenta:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Simpan Workspace ke Sipenta"
        self.description = "Tool untuk mengompresi workspace aktif dan mengunggahnya ke server Sipenta."

    def getParameterInfo(self):
        berkas_list = get_all_berkas_id()
        berkas_show = []
        
        if berkas_list is not None:
            can_show = 0
            for berkas in berkas_list:
                if berkas[1] is True:
                    
                    berkas_show.append(f"{berkas[0]}")
                    can_show += 1
            if can_show == 0:
                berkas_show = ['Tidak ada berkas yang dapat dipilih']
        else:
            berkas_show = ['Tidak ada berkas yang dapat dipilih']

        berkas = arcpy.Parameter(
            displayName="Berkas",
            name="berkas",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        
        berkas.filter.type = "ValueList"
        berkas.filter.list = berkas_show
        
        if berkas_list and can_show > 0:
            preferred_berkas=get_user_data(PREFERRED_BERKAS_ID)
            if preferred_berkas:
                if '01/' in preferred_berkas or '02/' in preferred_berkas :
                    berkas.value = preferred_berkas
                else:
                    berkas.value = berkas_show[0]           
        elif berkas_list and can_show == 0:
            berkas.value = 'Tidak ada berkas yang dapat dipilih'
        else:
            berkas.value = 'Tidak ada berkas yang dapat dipilih'

        
        judul = arcpy.Parameter(
            displayName="Judul",
            name="judul", 
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        
        catatan = arcpy.Parameter(
            displayName="Catatan",
            name="catatan",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        
        penjelasan = arcpy.Parameter(
            displayName="Penjelasan",
            name="petunjuk",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )
        
        penjelasan.value = (
            "Login terlebih dahulu untuk mengakses fitur ini.\n\n"
            "Direktorat Penilaian Tanah dan Ekonomi Pertanahan,\n"
            "Kementerian ATR/BPN.\n"
            f"Tahun: {datetime.now().year}\n"
        )

        params = [berkas, judul, catatan, penjelasan]
        return params

    def isLicensed(self):
        """Set whether the tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed."""
        berkas = parameters[0]
        judul = parameters[1]
        catatan = parameters[2]
        penjelasan = parameters[3]

        is_login = get_user_data(CREDENTIAL_KEY)

        # Jika belum login
        if not is_login:
            for param in [catatan, judul, berkas, penjelasan]:
                param.enabled = False
            penjelasan.enabled = True
            return

        # Jika sudah login
        else:
            for param in [catatan, judul, berkas, penjelasan]:
                param.enabled = True

            penjelasan.value = (
                "Tools ini berfungsi untuk menyimpan workspace ke Sipenta.\n\n"
                "Direktorat Penilaian Tanah dan Ekonomi Pertanahan,\n"
                "Kementerian ATR/BPN.\n"
                f"Tahun: {datetime.now().year}\n"
            )
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation."""
        return

    def execute(self, parameters, messages):
        """
        Pemenuhan kondisi yang harus dipenuhi oleh program pada tool ini:
        1. Menyimpan file ZIP yang dihasilkan ke lokasi yang dipilih.
        2. Melakukan pengecekan apakah lokasi dapat diakses.
        """
        zl_path = zonalayer.is_zona_layer_comply(show_path_message=False)
        ws_dir = os.path.dirname(os.path.dirname(os.path.dirname(zl_path)))
        server = get_user_data(PREFERRED_SERVER_KEY)
        use_production = True if server == "Produksi" or server == None else False

        berkas = parameters[0].valueAsText
        judul = parameters[1].valueAsText
        catatan = parameters[2].valueAsText

        # Mengambil token user untuk otorisasi upload
        user_data = get_user_data(CREDENTIAL_KEY)
        token = user_data.get(AUTH_KEY, None)
        if not token:
            arcpy.AddError("Sesi telah habis atau Anda belum login.")
            return

        if ws_dir:
            parent_dir = os.path.dirname(ws_dir)

            if not os.path.exists(parent_dir) and parent_dir != "":
                arcpy.AddError(f"Directory parent tidak ditemukan: {parent_dir}")
                return
            else:
                # Membuat format nama file zip agar rapi
                zip_filename = f"{judul.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
                
                # Menggunakan compress_with_retry agar tahan dari error file lock
                zip_file_path = self.compress_with_retry(ws_dir, ws_dir, zip_filename)
                
                if zip_file_path:
                    arcpy.AddMessage(f"Proses kompresi selesai. File ZIP: {zip_file_path}")
                    # Eksekusi proses upload jika zip berhasil dibuat
                    self.upload_zip_to_sipenta(berkas, token, judul, zip_file_path, catatan, use_production)

                else:
                    arcpy.AddError("Gagal mengompresi workspace setelah beberapa percobaan")
        else:
            arcpy.AddError("Folder tujuan tidak valid")
        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed."""
        return
    
    def compress_directory_to_zip(self, source_dir, output_folder, zip_filename):
        """
        Mengompresi seluruh direktori menjadi file ZIP dan melewati file terkunci.
        """
        try:
            arcpy.AddMessage(f"Mengompresi direktori: {source_dir}")
            arcpy.AddMessage(f"Folder tujuan: {output_folder}")
            
            # Pastikan folder tujuan exists
            if not os.path.exists(output_folder):
                os.makedirs(output_folder)
                arcpy.AddMessage(f"Folder tujuan dibuat: {output_folder}")
            
            source_name = os.path.basename(source_dir)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if not zip_filename:
                zip_filename = f"{source_name}_backup_{timestamp}.zip"
            output_zip_path = os.path.join(output_folder, zip_filename)
            
            arcpy.AddMessage(f"Membuat file ZIP: {zip_filename}")
            
            skip_extensions = ['.lock', '.sr.lock']
            skip_keywords = ['.LAPTOP-', '.DESKTOP-']
            
            with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(source_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        
                        # Skip file lock ArcGIS
                        if any(file.endswith(ext) for ext in skip_extensions) or any(keyword in file for keyword in skip_keywords):
                            continue
                        
                        try:
                            # Coba buka file untuk membaca (test jika terkunci)
                            with open(file_path, 'rb') as test_file:
                                pass
                                
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
        Mencoba kompresi dengan beberapa kali retry jika ada file terkunci.
        """
        for attempt in range(max_retries):
            arcpy.AddMessage(f"Percobaan kompresi ke-{attempt + 1}")
            
            result = self.compress_directory_to_zip(source_dir, output_folder, zip_filename)
            if result:
                return result
            
            if attempt < max_retries - 1:
                arcpy.AddMessage("Menunggu 2 detik sebelum mencoba lagi...")
                time.sleep(2)
        
        return None

    def upload_zip_to_sipenta(self, nomor_berkas, token, judul, zip_path, catatan, use_production=True):
        """
        Mengunggah hasil kompresi ke server Sipenta
        """
        zipname = os.path.basename(zip_path)
        try:
            arcpy.AddMessage('Mengupload file ke server...')
            test_url = "https://belajar.atrbpn.go.id/sipenta/tatausaha-2/api/pemetaan/workspace"
            prod_url = "https://sipenta.atrbpn.go.id/tatausaha/api/pemetaan/workspace"
            url = prod_url if use_production else test_url            

            headers = {
                "Authorization": f"Bearer {token}"
            }

            data = {
                "no_berkas": f'{nomor_berkas}',
                "judul": f'{judul}',
                "catatan": f'{catatan}',
            }

            with open(zip_path, "rb") as zip_file:
                files = {
                    "file": (
                        zipname,
                        zip_file,
                        "application/zip"
                    )
                }

                response = requests.post(
                    url,
                    headers=headers,
                    data=data,
                    files=files
                )
                # Wajib dipanggil untuk memicu exception jika status 4xx/5xx
                response.raise_for_status() 
                
                # Jika lolos dari raise_for_status, berarti sukses (200 OK)
                arcpy.AddMessage("File berhasil diupload ke modul tatausaha sipenta.")
                return response.json()

        # 1. Tangkap HTTPError (403, 404, 500, dll) DULUAN
        except requests.exceptions.HTTPError as e:
            response = e.response
            
            # Ambil JSON
            try:
                error_json = response.json()
                message = error_json.get("message", "")
            except ValueError:
                message = ""

            # Handle khusus 403
            if response.status_code == 403:
                if "expired" in message.lower():
                    # clear_user_data() 
                    arcpy.AddError("Token Anda kadaluarsa, silakan login ulang.")
                else:
                    error_message = message if message else "Periksa hak akses atau token."
                    # Tampilkan pesan spesifik dari JSON server
                    arcpy.AddError(f"Akses ditolak (403). Pesan: {error_message}")
            else:
                # Jika HTTP error lain (misal 500 Internal Server Error)
                arcpy.AddError(f"HTTP Error: {e}")
                
        # 2. Tangkap error Request secara umum (misal koneksi putus/timeout)
        except requests.RequestException as e:
            arcpy.AddError(f"Error koneksi ke server: {str(e)}")
            
        # 3. Tangkap error Python lainnya
        except Exception as e:
            arcpy.AddError(f"Error umum saat upload: {str(e)}")

        finally:
            arcpy.management.Delete(zip_path)
            
        return

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