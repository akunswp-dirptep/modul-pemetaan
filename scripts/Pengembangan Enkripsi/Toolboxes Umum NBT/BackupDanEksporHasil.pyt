# -*- coding: utf-8 -*-
from datetime import datetime
import sys
import arcpy, os, zipfile
import time
from collections import Counter

arcpy.env.outputZFlag = "Disabled"
arcpy.env.outputMFlag = "Disabled"

# Tambahkan parent directory ke sys.path
script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from nbtutils import persil

arcpy.env.outputZFlag = "Disabled"  
arcpy.env.outputMFlag = "Disabled"  

class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [Ekspor_Geodatabase, CekDuplikatField, UpdateAtributPersil]


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
            displayName="Simpan file ZIP (.zip)",
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

        config_paths = persil.get_config_values()
        dataset_path = config_paths['project_config']['dataset_path']
        persil_path = os.path.join(dataset_path, 'Persil_Layer')
        ws_dir = os.path.dirname(os.path.dirname(os.path.dirname(persil_path)))
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

class CekDuplikatField(object):
    def __init__(self):
        """Mendefinisikan properti dari tool Cek Duplikat."""
        self.label = "Cek Nilai Duplikat"
        self.description = "Mengecek dan menampilkan nilai duplikat pada field tertentu di dalam Feature Class atau Tabel."
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Mendefinisikan antarmuka input/output (Parameter) dari tool."""
        
        # Parameter 1: Input Feature Class / Layer
        param0 = arcpy.Parameter(
            displayName="Feature Class / Layer Input",
            name="in_features",
            datatype=["GPFeatureLayer", "DEFeatureClass", "DETable"],
            parameterType="Required",
            direction="Input"
        )

        # Parameter 2: Pilih Field (Otomatis menyesuaikan dengan Parameter 1)
        param1 = arcpy.Parameter(
            displayName="Pilih Field (Target)",
            name="in_field",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        # Menghubungkan pilihan field dengan layer yang dipilih di param0
        param1.parameterDependencies = [param0.name]
        
        # Opsional: Membatasi agar dropdown hanya memunculkan field bertipe angka dan teks
        param1.filter.list = ['Short', 'Long', 'Integer', 'Double', 'String']

        return [param0, param1]

    def isLicensed(self):
        """Mengecek lisensi (Biarkan True)."""
        return True

    def updateParameters(self, parameters):
        """Memperbarui nilai parameter sebelum tool dieksekusi (Opsional)."""
        return

    def updateMessages(self, parameters):
        """Menambahkan pesan error/warning kustom di UI (Opsional)."""
        return

    def execute(self, parameters, messages):
        """Logika utama program saat tombol 'Run' ditekan."""
        
        # Mengambil input dari antarmuka pengguna
        fc = parameters[0].valueAsText
        field = parameters[1].valueAsText

        arcpy.AddMessage(f"Memulai pengecekan duplikat pada field '{field}'...")

        nilai_list = []

        # Membaca data menggunakan SearchCursor
        try:
            with arcpy.da.SearchCursor(fc, [field]) as cursor:
                for row in cursor:
                    if row[0] is not None:
                        nilai_list.append(row[0])
                        
        except Exception as e:
            # Jika error, tampilkan peringatan merah muda di ArcGIS
            arcpy.AddError(f"Terjadi kesalahan saat membaca data: {e}")
            return

        # Menghitung jumlah kemunculan
        hitung_nilai = Counter(nilai_list)

        # Memfilter hanya nilai yang muncul lebih dari 1 kali
        duplikat = {nilai: jumlah for nilai, jumlah in hitung_nilai.items() if jumlah > 1}

        # Menampilkan hasil akhir di panel "Messages" ArcGIS Pro
        arcpy.AddMessage("-" * 40)
        if duplikat:
            # Teks akan berwarna kuning (Warning) jika ada duplikat
            arcpy.AddWarning(f"DITEMUKAN {len(duplikat)} NILAI DUPLIKAT:")
            for nilai, jumlah in duplikat.items():
                arcpy.AddMessage(f"> Nilai {nilai} muncul sebanyak {jumlah} kali.")
        else:
            # Teks akan berwarna hijau/normal jika aman
            arcpy.AddMessage("TIDAK ADA DUPLIKAT. Semua nilai unik.")
        arcpy.AddMessage("-" * 40)
        
        return
    

class UpdateAtributPersil(object):
    def __init__(self):
        self.label = "Update Atribut Persil (Null/Semua)"
        self.description = "Memperbarui field WADMKD dan WADMKC. Menyediakan opsi untuk meng-update semua data atau hanya yang masih kosong (Null)."
        self.canRunInBackground = False

    def getParameterInfo(self):
        
        param_utama = arcpy.Parameter(
            displayName="Persil Utama (Tujuan)",
            name="in_persil",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )
        
        param_target = arcpy.Parameter(
            displayName="Persil Target (Sumber Data)",
            name="target_persil",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )
        
        param_kunci = arcpy.Parameter(
            displayName="Field Kunci",
            name="key_field",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        param_kunci.value = "IDBIDANG"
        
        # Parameter 3: Opsi Dropdown untuk memilih mode update
        param_opsi = arcpy.Parameter(
            displayName="Opsi Update",
            name="update_option",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        param_opsi.filter.type = "ValueList"
        param_opsi.filter.list = ["Hanya Data Null", "Semua Data"]
        param_opsi.value = "Hanya Data Null" # Default pilihan
        
        return [param_utama, param_target, param_kunci, param_opsi]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        in_persil = parameters[0].valueAsText
        target_persil = parameters[1].valueAsText
        key_field = parameters[2].valueAsText
        update_option = parameters[3].valueAsText
        
        fields_to_update = ["WADMKD", "WADMKC"]
        
        # 1. Cek apakah field WADMKD dan WADMKC sudah ada di persil utama
        # Jika belum ada, script akan otomatis membuatnya terlebih dahulu
        existing_fields = [f.name for f in arcpy.ListFields(in_persil)]
        for field in fields_to_update:
            if field not in existing_fields:
                arcpy.management.AddField(in_persil, field, "TEXT", field_length=50)
                arcpy.AddMessage(f"Field {field} dibuat baru di Persil Utama.")

        # 2. Simpan data target ke dalam memori (Dictionary)
        arcpy.AddMessage("Membaca data dari Persil Target...")
        target_dict = {}
        
        with arcpy.da.SearchCursor(target_persil, [key_field] + fields_to_update) as cursor:
            for row in cursor:
                key = row[0]
                if key is not None:
                    # Simpan sebagai: target_dict[IDBIDANG] = (WADMKD, WADMKC)
                    target_dict[key] = (row[1], row[2])

        # 3. Proses Update Data
        arcpy.AddMessage(f"Memulai proses sinkronisasi dengan mode: {update_option}")
        update_count = 0
        
        # Gunakan UpdateCursor untuk menulis ke persil utama
        with arcpy.da.UpdateCursor(in_persil, [key_field] + fields_to_update) as cursor:
            for row in cursor:
                key = row[0]
                
                # Jika IDBIDANG ditemukan di persil target
                if key in target_dict:
                    target_wadmkd, target_wadmkc = target_dict[key]
                    is_updated = False
                    
                    if update_option == "Hanya Data Null":
                        # Update WADMKD jika isinya Null (None) atau teks kosong ("")
                        if row[1] is None or str(row[1]).strip() == "":
                            row[1] = target_wadmkd
                            is_updated = True
                        
                        # Update WADMKC jika isinya Null (None) atau teks kosong ("")
                        if row[2] is None or str(row[2]).strip() == "":
                            row[2] = target_wadmkc
                            is_updated = True
                            
                    elif update_option == "Semua Data":
                        # Timpa data secara langsung
                        row[1] = target_wadmkd
                        row[2] = target_wadmkc
                        is_updated = True
                        
                    # Simpan perubahan jika ada field yang terisi
                    if is_updated:
                        cursor.updateRow(row)
                        update_count += 1

        arcpy.AddMessage(f"Berhasil! Sebanyak {update_count} baris data pada Persil Utama telah diperbarui.")