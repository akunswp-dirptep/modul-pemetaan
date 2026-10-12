from datetime import datetime
import json
import sys
import arcpy, os, math
import uuid
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
        self.tools = [Identifikasi_Perubahan_Persil, 
                      Periksa_Perubahan_Persil,
                      Sesuaikan_Status_Perubahan_Persil,
                      Reset_Perubahan_Mengelompok,
                      Simpan_Perubahan_Ke_Persil_Layer,
                      Update_Luas_Tanah,
                      Edit_Bentuk_Persil,
                      Simpan_Bentuk_Persil,
                      Tampilkan_Simbologi_Persil,
                      Sinkronkan_Indikator_Persil,
                      Analisis_Bentuk_Persil_File,
                      Simpan_Perubahan_Ke_Persil_Baru,
                      Generate_Peta_Akhir,
                      ]
class Identifikasi_Perubahan_Persil(object):
    def __init__(self):
        self.label="Identifikasi Perubahan Persil"
        self.description="Identifikasi perubahan berbasis Centroid, Area, dan UID"
        self.canRunInBackground=False

    def getParameterInfo(self):
        peta_baru=arcpy.Parameter(
            displayName="Persil Baru",
            name="peta_baru",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")

        output_baru=arcpy.Parameter(
            displayName="Output Peta Baru",
            name="output_baru",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        output_indikator=arcpy.Parameter(
            displayName="Output Indikator",
            name="output_indikator",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return[peta_baru, output_baru, output_indikator]

    def isLicensed(self):
        return True

    def updateParameters(self,parameters):
        return

    def updateMessages(self,parameters):
        return

    def delete_if_exists(self,path):
        if arcpy.Exists(path):
            try:
                arcpy.management.Delete(path)
            except Exception:
                pass

    def generate_uid_field(self, fc, field_name):
        """Fungsi untuk membuat dan mengisi UID unik jika belum ada atau kosong"""
        field_names = [f.name.upper() for f in arcpy.ListFields(fc)]
        if field_name.upper() not in field_names:
            arcpy.management.AddField(fc, field_name, "TEXT", field_length=50)

        code_block = """import uuid
def get_uid(val):
    if not val or str(val).strip() == '':
        return str(uuid.uuid4())
    return val"""
        
        arcpy.management.CalculateField(
            fc, 
            field_name, 
            f"get_uid(!{field_name}!)", 
            "PYTHON3", 
            code_block
        )

    def save_layer(self, source_fc, dataset_path, output_name):
        sim_path = ''
        if output_name == "Persil_Baru":
            sim_path = r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Simbologi_Persil_Baru_Layer.lyrx"
        else:
            sim_path = r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Indikator_Perubahan_Persil.lyrx"
            
        if not os.path.exists(sim_path):
            arcpy.AddWarning(f"File simbolik {sim_path} tidak ditemukan. Simbologi tidak akan diterapkan.")
        else:
            arcpy.AddMessage(f"File simbolik {sim_path} ditemukan. Simbologi akan diterapkan.")
            
        output_path = os.path.join(dataset_path, output_name)
        self.delete_if_exists(output_path)
        arcpy.management.CopyFeatures(source_fc, output_path)

        return output_name, output_path, sim_path

    def execute(self,parameters,messages):
        messages.addMessage("== Proses dimulai ==")

        peta_baru_input = parameters[0].valueAsText
        
        # 1. PENGECEKAN KOORDINAT TM-3
        desc_baru = arcpy.Describe(peta_baru_input)
        sr = desc_baru.spatialReference
        if sr.name == "Unknown":
            messages.addErrorMessage("Sistem koordinat Persil Baru tidak diketahui (Unknown).")
            raise arcpy.ExecuteError
            
        sr_name_upper = sr.name.upper()
        if "TM3" not in sr_name_upper and "TM-3" not in sr_name_upper and "TM_3" not in sr_name_upper:
            messages.addErrorMessage(f"ERROR: Koordinat Persil Baru bukan TM-3 (Terdeteksi: {sr.name}). Tools dihentikan.")
            raise arcpy.ExecuteError
        messages.addMessage("Sistem Koordinat Valid.")

        configs = persil.get_config_values()
        dataset_path = configs["project_config"]["dataset_path"]
        peta_lama_input = os.path.join(dataset_path, "Persil_Layer")

        if not arcpy.Exists(peta_lama_input):
            messages.addErrorMessage("Persil_Lama belum tersedia")
            raise arcpy.ExecuteError

        # 2. GENERATE UID KE DATA ASLI (Nama Field maksimal 10 karakter agar support Shapefile)
        messages.addMessage("Memastikan keberadaan UID di Peta Asli...")
        self.generate_uid_field(peta_lama_input, "UID_Lama")
        self.generate_uid_field(peta_baru_input, "UID_Baru")

        # Paths in memory
        dest_lama_path = r"in_memory\PersilPetaLama"
        dest_baru_path = r"in_memory\PersilPetaBaru"
        temp_lama_path = r"in_memory\Peta_Temp_Lama"
        temp_baru_path = r"in_memory\Peta_Temp_Baru"
        indikator_temp = r"in_memory\Indikator_Perubahan"
        
        memory_layers = [dest_lama_path, dest_baru_path, temp_lama_path, temp_baru_path, indikator_temp]
        for lyr in memory_layers:
            self.delete_if_exists(lyr)

        messages.addMessage("Menyalin data ke memori...")
        arcpy.management.CopyFeatures(peta_lama_input, dest_lama_path)
        arcpy.management.CopyFeatures(peta_baru_input, dest_baru_path)

        # Buat duplikat untuk diolah menjadi layer indikator
        arcpy.management.CopyFeatures(dest_lama_path, temp_lama_path)
        arcpy.management.CopyFeatures(dest_baru_path, temp_baru_path)

        # Siapkan kolom yang diperlukan di layer temporary (Nama field dibatasi maks 10 char)
        messages.addMessage("Menyiapkan struktur field...")
        arcpy.management.AddField(temp_lama_path, "UID_Baru", "TEXT", field_length=50)
        arcpy.management.AddField(temp_lama_path, "Sumber", "TEXT", field_length=50, field_alias="Sumber Persil")
        arcpy.management.AddField(temp_lama_path, "Keterangan", "TEXT", field_length=255, field_alias="Keterangan Perubahan")
        
        arcpy.management.AddField(temp_baru_path, "UID_Lama", "TEXT", field_length=50)
        arcpy.management.AddField(temp_baru_path, "Sumber", "TEXT", field_length=50, field_alias="Sumber Persil")
        arcpy.management.AddField(temp_baru_path, "Keterangan", "TEXT", field_length=255, field_alias="Keterangan Perubahan")

        messages.addMessage("Membaca koordinat centroid (X,Y) dan Luasan...")

        # 3. EKSTRAK GEOMETRI & UID KE DICTIONARY
        dict_lama = {}
        with arcpy.da.SearchCursor(dest_lama_path, ["SHAPE@XY", "SHAPE@AREA", "UID_Lama"]) as sc:
            for row in sc:
                if row[0]:
                    x, y = round(row[0][0], 6), round(row[0][1], 6)
                    area = round(row[1], 1)
                    dict_lama[(x, y)] = {"area": area, "uid": row[2]}

        dict_baru = {}
        with arcpy.da.SearchCursor(dest_baru_path, ["SHAPE@XY", "SHAPE@AREA", "UID_Baru"]) as sc:
            for row in sc:
                if row[0]:
                    x, y = round(row[0][0], 6), round(row[0][1], 6)
                    area = round(row[1], 1)
                    dict_baru[(x, y)] = {"area": area, "uid": row[2]}

        messages.addMessage("Mengevaluasi perbedaan atribut...")

        # 4. IDENTIFIKASI PERUBAHAN PADA PERSIL LAMA
        with arcpy.da.UpdateCursor(temp_lama_path, ["SHAPE@XY", "SHAPE@AREA", "Sumber", "Keterangan", "UID_Baru"]) as uc:
            for row in uc:
                if not row[0]: continue
                x, y = round(row[0][0], 6), round(row[0][1], 6)
                area = round(row[1], 1)
                
                row[2] = "Persil Lama" 
                
                if (x, y) not in dict_baru:
                    row[3] = "Tidak ditemukan bidang pasangannya di Persil Baru"
                    row[4] = None # Tidak ada pasangan
                    uc.updateRow(row)
                elif area != dict_baru[(x, y)]["area"]:
                    row[3] = "Luas bidang berubah"
                    row[4] = dict_baru[(x, y)]["uid"] # Ambil UID pasangannya
                    uc.updateRow(row)
                else:
                    uc.deleteRow() # SAMA PERSIS, abaikan dari indikator

        # 5. IDENTIFIKASI PERUBAHAN PADA PERSIL BARU
        with arcpy.da.UpdateCursor(temp_baru_path, ["SHAPE@XY", "SHAPE@AREA", "Sumber", "Keterangan", "UID_Lama"]) as uc:
            for row in uc:
                if not row[0]: continue
                x, y = round(row[0][0], 6), round(row[0][1], 6)
                area = round(row[1], 1)
                
                row[2] = "Persil Baru"
                
                if (x, y) not in dict_lama:
                    row[3] = "Tidak ditemukan bidang pasangannya di Persil Lama"
                    row[4] = None # Tidak ada pasangan
                    uc.updateRow(row)
                elif area != dict_lama[(x, y)]["area"]:
                    row[3] = "Luas bidang berubah"
                    row[4] = dict_lama[(x, y)]["uid"] # Ambil UID pasangannya
                    uc.updateRow(row)
                else:
                    uc.deleteRow() # SAMA PERSIS, abaikan dari indikator

        messages.addMessage("Menggabungkan dan membersihkan field hasil indikator...")
        
        # 6. GABUNGKAN HASIL KE INDIKATOR & BERSIHKAN FIELD
        arcpy.management.Merge([temp_baru_path, temp_lama_path], indikator_temp)
        
        # Daftar field yang dipertahankan
        fields_to_keep = ["UID_Lama", "UID_Baru", "Sumber", "Keterangan"]
        
        for field in arcpy.ListFields(indikator_temp):
            field_name_upper = field.name.upper()
            is_system_field = field.type in ["OID", "Geometry"] or "SHAPE" in field_name_upper
            
            if not is_system_field and field_name_upper not in [f.upper() for f in fields_to_keep]:
                try:
                    arcpy.management.DeleteField(indikator_temp, field.name)
                except Exception:
                    pass

        # 7. PENYIMPANAN DAN PENERAPAN SIMBOLOGI
        f_lyr_name, lyr_path, sim_f_lyr_path = self.save_layer(dest_baru_path, dataset_path, "Persil_Baru")
        arcpy.management.MakeFeatureLayer(lyr_path, f_lyr_name)
        arcpy.management.ApplySymbologyFromLayer(f_lyr_name, sim_f_lyr_path)
        arcpy.SetParameter(1, f_lyr_name)
        parameters[1].symbology = sim_f_lyr_path
        
        s_lyr_name, lyr_path, sim_s_lyr_path = self.save_layer(indikator_temp, dataset_path, "Indikator_Perubahan_Persil")
        arcpy.management.MakeFeatureLayer(lyr_path, s_lyr_name)
        arcpy.management.ApplySymbologyFromLayer(s_lyr_name, sim_s_lyr_path)
        arcpy.SetParameter(2, s_lyr_name)
        parameters[2].symbology = sim_s_lyr_path

        messages.addMessage("== Proses selesai ==")
        return
    
class Tampilkan_Simbologi_Persil(object):
    """Tool untuk menampilkan simbologi pada layer Persil"""
    def __init__(self):
        self.label = "Tampilkan Simbologi Layer Identifikasi"
        self.description = "Tool untuk menampilkan simbologi "

        self.canRunInBackground = False

    def getParameterInfo(self):
        """Mendefinisikan parameter input tool"""
        penjelasan = arcpy.Parameter(
            displayName="Apa yang dilakukan tool ini?",
            name="penjelasan",
            datatype="GPString",    
            parameterType="Optional",
            direction="Input")
        
        penjelasan.value = (
            "Tool ini digunakan untuk menampilkan simbologi pada\n"
            "layer Identifikasi_Perubahan_Persil dan Persil_Baru.\n\n"
            "Direktorat Penilaian Tanah & Ekonomi Pertanahan\n"
            "Kementerian ATR/BPN\n"
            "Tahun: {}".format(datetime.now().year)
        )
        
        output_ts = arcpy.Parameter(
            name="Persil_Layer",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        output_tsi = arcpy.Parameter(
            name="Persil_Indikator_Layer",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )
        return [penjelasan, output_ts, output_tsi]

    def isLicensed(self):
        """Validasi lisensi ArcGIS"""
        return True

    def updateParameters(self, parameters):
        """Update parameter dynamically"""
        return

    def updateMessages(self, parameters):
        """Validasi dan update messages"""
        return

    def execute(self, parameters, messages):
        """Eksekusi utama tool untuk menampilkan simbologi pada layer Persil"""
        config_paths = persil.get_config_values()

        dataset_path = config_paths['project_config']['dataset_path']
        
        persil_path = os.path.join(dataset_path, 'Persil_Baru')
        sim_path = r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Simbologi_Persil_Baru_Layer.lyrx"
        indi_path = os.path.join(dataset_path, 'Indikator_Perubahan_Persil')
        sim_indi_path = r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Indikator_Perubahan_Persil.lyrx"

        arcpy.management.MakeFeatureLayer(persil_path, 'Persil_Baru')
        arcpy.management.ApplySymbologyFromLayer('Persil_Baru', sim_path)

        if arcpy.Exists(indi_path):
            arcpy.management.MakeFeatureLayer(indi_path, 'Indikator_Perubahan_Persil')
            arcpy.management.ApplySymbologyFromLayer('Indikator_Perubahan_Persil', sim_indi_path)

        arcpy.SetParameter(1, 'Persil_Baru')
        arcpy.SetParameter(2, 'Indikator_Perubahan_Persil' if arcpy.Exists(indi_path) else None)

class Periksa_Perubahan_Persil(object):
    def __init__(self):
        self.label="Periksa Perubahan Persil"
        self.description=""
        self.canRunInBackground=False

    def getParameterInfo(self):
        radius=arcpy.Parameter(
            displayName="Radius Toleransi Perubahan (m)",
            name="radius",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input"
        )
        radius.value=5.0

        output_layer=arcpy.Parameter(
            displayName="Output Layer",
            name="output_layer",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [radius, output_layer]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        messages.addMessage("== Proses dimulai: Pendekatan Intersect (Overlap Fisik) ==")

        configs = persil.get_config_values()
        dataset_path = configs["project_config"]["dataset_path"]
        
        # Mendapatkan path untuk symbology
        appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

        radius = parameters[0].value
        # Konversi toleransi radius menjadi luasan (m2)
        toleransi_m2 = math.pi * (radius ** 2)

        # Sumber layer (Kita asumsikan Persil_Baru dan Persil_Layer sudah ada di GDB)
        peta_baru_path = os.path.join(dataset_path, "Persil_Baru")
        peta_lama_path = os.path.join(dataset_path, "Persil_Layer")
        
        # Target output layer
        peta_indikator_nama = "Indikator_Perubahan_Persil"
        peta_indikator_path = os.path.join(dataset_path, peta_indikator_nama)

        # Paths untuk pemrosesan in_memory agar lebih cepat dan tidak mengotori GDB utama
        temp_baru = r"in_memory\Temp_Baru"
        temp_lama = r"in_memory\Temp_Lama"
        temp_intersect = r"in_memory\Temp_Intersect"

        # 1. Hapus layer memori jika ada dari proses sebelumnya
        for lyr in [temp_baru, temp_lama, temp_intersect]:
            if arcpy.Exists(lyr):
                arcpy.management.Delete(lyr)

        messages.addMessage("-> Menyiapkan data Persil Baru dan Lama...")
        arcpy.management.CopyFeatures(peta_baru_path, temp_baru)
        arcpy.management.CopyFeatures(peta_lama_path, temp_lama)

        # 2. Tambahkan field ID unik dan Luas Geometri Asli pada Temp Baru
        arcpy.management.AddField(temp_baru, "ID_Baru", "LONG")
        arcpy.management.AddField(temp_baru, "Luas_Baru", "DOUBLE")
        arcpy.management.CalculateField(temp_baru, "ID_Baru", "!OBJECTID!", "PYTHON3")
        arcpy.management.CalculateField(temp_baru, "Luas_Baru", "!shape.area!", "PYTHON3")

        # 3. Tambahkan field ID unik dan Luas Geometri Asli pada Temp Lama
        arcpy.management.AddField(temp_lama, "ID_Lama", "LONG")
        arcpy.management.AddField(temp_lama, "Luas_Lama", "DOUBLE")
        arcpy.management.CalculateField(temp_lama, "ID_Lama", "!OBJECTID!", "PYTHON3")
        arcpy.management.CalculateField(temp_lama, "Luas_Lama", "!shape.area!", "PYTHON3")

        # 4. PROSES INTI: Intersect (Memotong bidang yang benar-benar bertumpuk secara spasial)
        messages.addMessage("-> Memproses pemotongan tumpang tindih spasial (Intersect)...")
        arcpy.analysis.Intersect([temp_baru, temp_lama], temp_intersect)

        # Hitung luas area yang benar-benar bertumpuk
        arcpy.management.AddField(temp_intersect, "Luas_Irisan", "DOUBLE")
        arcpy.management.CalculateField(temp_intersect, "Luas_Irisan", "!shape.area!", "PYTHON3")

        # 5. Analisis hasil intersect menggunakan Python Dictionary
        # Kita cari overlap (irisan) yang paling besar untuk setiap Persil Baru
        messages.addMessage("-> Mengevaluasi luasan tumpang tindih...")
        overlap_dict = {}
        with arcpy.da.SearchCursor(temp_intersect, ["ID_Baru", "Luas_Irisan", "Luas_Lama", "Luas_Baru"]) as cursor:
            for row in cursor:
                id_b = row[0]
                luas_irisan = row[1]
                luas_lama = row[2]
                luas_baru = row[3]

                if id_b not in overlap_dict:
                    overlap_dict[id_b] = {
                        "max_irisan": luas_irisan,
                        "luas_lama": luas_lama,
                        "luas_baru": luas_baru
                    }
                else:
                    # Jika 1 Persil Baru menimpa beberapa Persil Lama, ambil irisan yang ukurannya paling dominan (terbesar)
                    if luas_irisan > overlap_dict[id_b]["max_irisan"]:
                        overlap_dict[id_b]["max_irisan"] = luas_irisan
                        overlap_dict[id_b]["luas_lama"] = luas_lama

        # 6. PENENTUAN STATUS: Update atau Tetap pada Persil Baru
        messages.addMessage("-> Menulis status 'update' / 'tetap' pada Persil Baru...")
        if "status_per" not in [f.name for f in arcpy.ListFields(temp_baru)]:
            arcpy.management.AddField(temp_baru, "status_per", "TEXT")

        with arcpy.da.UpdateCursor(temp_baru, ["ID_Baru", "status_per"]) as cursor:
            for row in cursor:
                id_b = row[0]
                
                if id_b in overlap_dict:
                    data = overlap_dict[id_b]
                    
                    # Hitung perbedaan antara Luas Irisan dengan Luas Aslinya
                    selisih_baru = abs(data["luas_baru"] - data["max_irisan"])
                    selisih_lama = abs(data["luas_lama"] - data["max_irisan"])
                    
                    # Jika selisihnya lebih kecil atau sama dengan toleransi_m2, 
                    # maka bidang itu dianggap tidak berubah ('tetap')
                    if selisih_baru <= toleransi_m2 and selisih_lama <= toleransi_m2:
                        row[1] = "tetap"
                    else:
                        row[1] = "update"
                else:
                    # Jika poligon Persil Baru tidak beririsan sama sekali dengan Persil Lama (di tempat kosong)
                    row[1] = "update"
                    
                cursor.updateRow(row)

        messages.addMessage("-> Menyimpan hasil akhir...")
        # 7. Timpa Indikator_Perubahan_Persil yang lama dengan hasil dari temp_baru
        if arcpy.Exists(peta_indikator_path):
            arcpy.management.Delete(peta_indikator_path)

        # Bersihkan kolom alat bantu (ID_Baru, Luas_Baru) agar Attribute Table tetap rapi
        arcpy.management.DeleteField(temp_baru, ["ID_Baru", "Luas_Baru"])

        arcpy.management.CopyFeatures(temp_baru, peta_indikator_path)

        # --- 8. Menerapkan Simbologi ---
        sim_indikator_akhir = os.path.join(appdata, "Simbologi_Persil_Updating_Final.lyr")
        
        # Masukkan ke dalam map (Table of Contents)
        arcpy.management.MakeFeatureLayer(peta_indikator_path, peta_indikator_nama)
        
        if os.path.exists(sim_indikator_akhir):
            arcpy.management.ApplySymbologyFromLayer(peta_indikator_nama, sim_indikator_akhir)
        
        # Penting! Set parameter symbology secara langsung agar warna tidak hilang di ArcGIS Pro
        arcpy.SetParameter(1, peta_indikator_nama)
        parameters[1].symbology = sim_indikator_akhir

        messages.addMessage("== Proses selesai ==")
        return

class Sesuaikan_Status_Perubahan_Persil(object):

    def __init__(self):
        self.label="Sesuaikan Status Perubahan Persil"
        self.description=""
        self.canRunInBackground=False

    def getParameterInfo(self):

        status_perubahan=arcpy.Parameter(
            displayName="Status Perubahan",
            name="status_perubahan",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )

        output_layer=arcpy.Parameter(
            displayName="Output Layer",
            name="output_layer",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output")

        status_perubahan.filter.list=["tetap","update"]

        return[status_perubahan, output_layer]

    def isLicensed(self):
        return True

    def updateParameters(self,parameters):
        return

    def updateMessages(self,parameters):
        return

    def execute(self,parameters,messages):

        arcpy.env.overwriteOutput=True

        messages.addMessage("== Proses dimulai ==")

        val=parameters[0].valueAsText

        configs=persil.get_config_values()

        dataset_path=configs["project_config"]["dataset_path"]

        layer_indikator=os.path.join(dataset_path,"Indikator_Perubahan_Persil")

        if not arcpy.Exists(layer_indikator):
            messages.addErrorMessage("== Layer Indikator_Perubahan_Persil tidak ditemukan ==")
            raise arcpy.ExecuteError

        fields=[f.name for f in arcpy.ListFields(layer_indikator)]

        if "status_per" not in fields:
            messages.addErrorMessage("== Field status_per tidak ditemukan ==")
            raise arcpy.ExecuteError

        selected_count=int(
            arcpy.management.GetCount(
                "Indikator_Perubahan_Persil"
            )[0]
        )

        if selected_count==0:
            messages.addErrorMessage("== Tidak ada fitur yang dipilih ==")
            raise arcpy.ExecuteError

        messages.addMessage("== Mengupdate status perubahan persil ==")

        with arcpy.da.UpdateCursor(
            "Indikator_Perubahan_Persil",
            ["status_per"]
        ) as cursor:

            for row in cursor:
                row[0]=val
                cursor.updateRow(row)
        
        del cursor
        arcpy.SetParameter(1, "Indikator_Perubahan_Persil")

        messages.addMessage(f"== {selected_count} fitur berhasil diperbarui ==")

        messages.addMessage("== Proses selesai ==")

        return   

    
class Reset_Perubahan_Mengelompok(object):

    def __init__(self):
        self.label="Reset Perubahan Mengelompok"
        self.description=""
        self.canRunInBackground=False

    def getParameterInfo(self):

        output_layer=arcpy.Parameter(
            displayName="Output Persil",
            name="output_layer",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return[output_layer]

    def isLicensed(self):
        return True

    def updateParameters(self,parameters):
        return

    def updateMessages(self,parameters):
        return

    def delete_if_exists(self,path):
        if arcpy.Exists(path):
            try:
                arcpy.management.Delete(path)
            except Exception:
                pass

    def execute(self,parameters,messages):

        messages.addMessage("== Proses dimulai ==")
        configs=persil.get_config_values()
        dataset_path=configs["project_config"]["dataset_path"]
        appdata=os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        persil_name="Indikator_Perubahan_Persil"
        persil_path=os.path.join(dataset_path,persil_name)

        if not arcpy.Exists(persil_path):
            messages.addErrorMessage("Feature class Indikator_Perubahan_Persil tidak ditemukan")
            raise arcpy.ExecuteError

        selected_count=len(arcpy.Describe(persil_name).FIDSet)

        if selected_count<=0:
            messages.addWarningMessage("Tidak ada fitur yang dipilih")
            return

        field_names=[field.name for field in arcpy.ListFields(persil_path)]

        if "kelompok_perubahan" not in field_names:
            messages.addWarningMessage("Field kelompok_perubahan tidak ditemukan")
            return

        messages.addMessage("== Reset Kelompok Perubahan ==")

        updated_count=0

        with arcpy.da.UpdateCursor(
            persil_name,
            ["kelompok_perubahan"]
        ) as cursor:

            for row in cursor:
                row[0]=None
                cursor.updateRow(row)
                updated_count+=1

        messages.addMessage(f"{updated_count} fitur berhasil direset")

        arcpy.SetParameter(0, persil_name)

        messages.addMessage("== Proses selesai ==")

        return

class Simpan_Perubahan_Ke_Persil_Layer(object):
    def __init__(self):
        self.label = "Simpan Perubahan Ke Persil Layer"
        self.description = "Menyisihkan bidang lama dan memasukkan bidang baru beserta atribut dari Persil Baru."
        self.canRunInBackground = False

    def getParameterInfo(self):
        
        # Parameter input membaca kolom dari Persil Baru
        f_id = arcpy.Parameter(displayName="Field ID (dari Persil Baru)", name="f_id", datatype="GPString", parameterType="Required", direction="Input")
        f_nib = arcpy.Parameter(displayName="Field NIB (dari Persil Baru)", name="f_nib", datatype="GPString", parameterType="Required", direction="Input")
        f_tipehak = arcpy.Parameter(displayName="Field TIPEHAK (dari Persil Baru)", name="f_tipehak", datatype="GPString", parameterType="Required", direction="Input")
        f_kec = arcpy.Parameter(displayName="Field KECAMATAN (dari Persil Baru)", name="f_kec", datatype="GPString", parameterType="Required", direction="Input")
        f_kel = arcpy.Parameter(displayName="Field KELURAHAN (dari Persil Baru)", name="f_kel", datatype="GPString", parameterType="Required", direction="Input")

        output_persil = arcpy.Parameter(
            displayName="Output Persil Layer",
            name="output_persil",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )
        
        output_sisih = arcpy.Parameter(
            displayName="Output Persil Disisihkan",
            name="output_sisih",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [f_id, f_nib, f_tipehak, f_kec, f_kel, output_persil, output_sisih]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        try:
            configs = persil.get_config_values()
            dataset_path = configs["project_config"]["dataset_path"]
            peta_baru_path = os.path.join(dataset_path, "Persil_Baru") # Ubah target baca field ke Persil Baru
            
            if arcpy.Exists(peta_baru_path):
                fields = [f.name for f in arcpy.ListFields(peta_baru_path)]
                upper_fields = [f.upper() for f in fields]
                
                for i in range(5):
                    parameters[i].filter.list = fields

                # Set Default Value otomatis jika nama field cocok
                def set_default(param, candidates):
                    if not param.value:
                        for cand in candidates:
                            if cand.upper() in upper_fields:
                                param.value = fields[upper_fields.index(cand.upper())]
                                break

                set_default(parameters[0], ["IDPERSIL", "ID"])
                set_default(parameters[1], ["NIB"])
                set_default(parameters[2], ["TIPEHAK"])
                set_default(parameters[3], ["WADMKC", "KECAMATAN"])
                set_default(parameters[4], ["WADMKD", "KELURAHAN"])
        except Exception:
            pass
        return

    def updateMessages(self, parameters):
        return

    def delete_if_exists(self, path):
        if arcpy.Exists(path):
            try:
                arcpy.management.Delete(path)
            except Exception:
                pass

    def add_field_if_not_exists(self, fc, field_name, field_type, field_length=None, field_alias=None):
        fields = [f.name.upper() for f in arcpy.ListFields(fc)]
        if field_name.upper() not in fields:
            arcpy.management.AddField(
                fc, 
                field_name, 
                field_type, 
                field_length=field_length, 
                field_alias=field_alias
            )

    def execute(self, parameters, messages):
        messages.addMessage("== Proses Simpan Perubahan Dimulai ==")

        f_id = parameters[0].valueAsText
        f_nib = parameters[1].valueAsText
        f_tipehak = parameters[2].valueAsText
        f_kecamatan = parameters[3].valueAsText
        f_kelurahan = parameters[4].valueAsText

        configs = persil.get_config_values()
        dataset_path = configs["project_config"]["dataset_path"]

        peta_baru_path = os.path.join(dataset_path, "Persil_Baru")
        indikator_path = os.path.join(dataset_path, "Indikator_Perubahan_Persil")
        peta_lama_path = os.path.join(dataset_path, "Persil_Layer")
        persil_disisihkan_path = os.path.join(dataset_path, "Persil_Disisihkan")

        required_fc = [peta_baru_path, indikator_path, peta_lama_path]
        for fc in required_fc:
            if not arcpy.Exists(fc):
                messages.addErrorMessage(f"Feature class {os.path.basename(fc)} tidak ditemukan!")
                raise arcpy.ExecuteError
                
        # 1. AMBIL DEFAULT VALUE WADMPR, WADMKK, THNNILAI DARI PERSIL LAMA
        def_wadmapr, def_wadmkk, def_thnnilai = None, None, None
        try:
            with arcpy.da.SearchCursor(peta_lama_path, ["WADMPR", "WADMKK", "THNNILAI"]) as sc:
                for row in sc:
                    def_wadmapr, def_wadmkk, def_thnnilai = row
                    break
        except Exception:
            messages.addWarningMessage("Peringatan: Gagal mendapatkan nilai default WADMPR/WADMKK/THNNILAI.")

        # 2. KUMPULKAN UID DARI INDIKATOR
        uid_lama_to_remove = set()
        uid_baru_to_add = set()

        ind_fields = [f.name.upper() for f in arcpy.ListFields(indikator_path)]
        if "UID_LAMA" not in ind_fields or "UID_BARU" not in ind_fields:
             messages.addErrorMessage("Field UID_Lama atau UID_Baru tidak ditemukan di layer Indikator.")
             raise arcpy.ExecuteError

        with arcpy.da.SearchCursor(indikator_path, ["UID_Lama", "UID_Baru"]) as cursor:
            for row in cursor:
                if row[0]: uid_lama_to_remove.add(row[0])
                if row[1]: uid_baru_to_add.add(row[1])

        if not uid_lama_to_remove and not uid_baru_to_add:
            messages.addMessage("Tidak ada perubahan yang perlu disimpan (Indikator kosong).")
            return

        # 3. SIAPKAN PERSIL DISISIHKAN DAN KOLOM STATUS LAMA
        if not arcpy.Exists(persil_disisihkan_path):
            arcpy.management.CreateFeatureclass(
                dataset_path, "Persil_Disisihkan", "POLYGON", template=peta_lama_path,
                spatial_reference=arcpy.Describe(peta_lama_path).spatialReference
            )

        # 4. PENYISIHAN (PERSIL LAMA -> DISISIHKAN)
        messages.addMessage(f"Mengeksekusi penyisihan {len(uid_lama_to_remove)} bidang lama...")
        temp_lyr_lama = "temp_lyr_lama"
        arcpy.management.MakeFeatureLayer(peta_lama_path, temp_lyr_lama)

        bidang_berhasil_disisihkan = 0
        for uid in uid_lama_to_remove:
            arcpy.management.SelectLayerByAttribute(temp_lyr_lama, "NEW_SELECTION", f"UID_Lama = '{uid}'")
            count = int(arcpy.management.GetCount(temp_lyr_lama)[0])
            if count > 0:
                arcpy.management.Append(temp_lyr_lama, persil_disisihkan_path, "NO_TEST")
                arcpy.management.DeleteRows(temp_lyr_lama)
                bidang_berhasil_disisihkan += count
        arcpy.management.SelectLayerByAttribute(temp_lyr_lama, "CLEAR_SELECTION")

        # 5. MAPPING ATRIBUT PERSIL BARU KE NAMA KOLOM STANDAR
        messages.addMessage("Menyelaraskan nama kolom pada Persil Baru...")
        
        self.add_field_if_not_exists(peta_baru_path, "IDPERSIL", "TEXT", 50)
        self.add_field_if_not_exists(peta_baru_path, "NIB", "TEXT", 50)
        self.add_field_if_not_exists(peta_baru_path, "TIPEHAK", "TEXT", 50)
        self.add_field_if_not_exists(peta_baru_path, "WADMKC", "TEXT", 50)
        self.add_field_if_not_exists(peta_baru_path, "WADMKD", "TEXT", 50)
        self.add_field_if_not_exists(peta_baru_path, "WADMPR", "TEXT", 50)
        self.add_field_if_not_exists(peta_baru_path, "WADMKK", "TEXT", 50)
        self.add_field_if_not_exists(peta_baru_path, "THNNILAI", "SHORT")
        self.add_field_if_not_exists(peta_baru_path, "perubahan", "TEXT", 50, "Status Perubahan")

        # Transfer nilai hanya jika nama field tujuan dan asal berbeda (agar tidak error)
        mapping_field = {
            "IDPERSIL": f_id,
            "NIB": f_nib,
            "TIPEHAK": f_tipehak,
            "WADMKC": f_kecamatan,
            "WADMKD": f_kelurahan
        }

        for target_field, source_field in mapping_field.items():
            if target_field.upper() != source_field.upper():
                arcpy.management.CalculateField(peta_baru_path, target_field, f"!{source_field}!", "PYTHON3")

        # Set Global Value untuk Persil Baru
        with arcpy.da.UpdateCursor(peta_baru_path, ["WADMPR", "WADMKK", "THNNILAI"]) as uc:
            for row in uc:
                row[0] = def_wadmapr
                row[1] = def_wadmkk
                row[2] = def_thnnilai
                uc.updateRow(row)

        # 6. PENAMBAHAN (PERSIL BARU -> PERSIL LAMA)
        messages.addMessage(f"Mengeksekusi penambahan {len(uid_baru_to_add)} bidang baru...")
        temp_lyr_baru = "temp_lyr_baru"
        arcpy.management.MakeFeatureLayer(peta_baru_path, temp_lyr_baru)

        bidang_berhasil_ditambah = 0
        for uid in uid_baru_to_add:
            arcpy.management.SelectLayerByAttribute(temp_lyr_baru, "NEW_SELECTION", f"UID_Baru = '{uid}'")
            count = int(arcpy.management.GetCount(temp_lyr_baru)[0])
            if count > 0:
                arcpy.management.CalculateField(temp_lyr_baru, "perubahan", "'menyebar'", "PYTHON3")
                arcpy.management.Append(temp_lyr_baru, peta_lama_path, "NO_TEST")
                bidang_berhasil_ditambah += count
        arcpy.management.SelectLayerByAttribute(temp_lyr_baru, "CLEAR_SELECTION")

        # 7. CLEANING
        messages.addMessage("Merapikan ulang nomor IDBIDANG pada Persil_Layer...")
        self.add_field_if_not_exists(peta_lama_path, "IDBIDANG", "LONG")
        with arcpy.da.UpdateCursor(peta_lama_path, ["OBJECTID", "IDBIDANG"], sql_clause=(None, "ORDER BY OBJECTID")) as cursor:
            for nomor, row in enumerate(cursor, start=1):
                row[1] = nomor
                cursor.updateRow(row)

        fields_to_delete = ["UID_Lama", "UID_Baru"]
        existing_fields = [f.name.upper() for f in arcpy.ListFields(peta_lama_path)]
        for field in fields_to_delete:
            if field.upper() in existing_fields:
                try: arcpy.management.DeleteField(peta_lama_path, field)
                except Exception: pass

        self.delete_if_exists(temp_lyr_lama)
        self.delete_if_exists(temp_lyr_baru)

        arcpy.SetParameter(5, "Persil_Layer")
        arcpy.SetParameter(6, "Persil_Disisihkan")

        messages.addMessage(f"Statistik: {bidang_berhasil_disisihkan} disisihkan, {bidang_berhasil_ditambah} di-update.")
        messages.addMessage("== Proses Simpan Perubahan Selesai ==")
        return
    
class Update_Luas_Tanah(object):

    def __init__(self):
        self.label="Update Luas Tanah"
        self.description=""
        self.canRunInBackground=False

    def getParameterInfo(self):

        output_layer=arcpy.Parameter(
            displayName="Output Peta Akhir",
            name="output_peta_akhir",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return[output_layer]

    def isLicensed(self):
        return True

    def updateParameters(self,parameters):
        return

    def updateMessages(self,parameters):
        return

    def delete_if_exists(self,path):

        if arcpy.Exists(path):

            try:
                arcpy.management.Delete(path)

            except Exception:
                pass

    def add_field_if_not_exists(self,feature_class,field_name,field_type):

        fields=[
            field.name.lower()
            for field in arcpy.ListFields(feature_class)
        ]

        if field_name.lower() not in fields:

            arcpy.management.AddField(
                feature_class,
                field_name,
                field_type
            )

    def execute(self,parameters,messages):

        messages.addMessage("== Proses dimulai ==")

        configs=persil.get_config_values()

        dataset_path=configs["project_config"]["dataset_path"]

        peta_persil_name="Persil_Layer"

        peta_persil_path=os.path.join(
            dataset_path,
            peta_persil_name
        )

        self.add_field_if_not_exists(
            peta_persil_path,
            "LUASM2",
            "DOUBLE"
        )

        messages.addMessage("== Hitung luas tanah ==")

        arcpy.management.CalculateField(
            peta_persil_path,
            "LUASM2",
            "!shape.area!",
            "PYTHON3"
        )

        self.delete_if_exists(peta_persil_name)

        arcpy.management.MakeFeatureLayer(
            peta_persil_path,
            peta_persil_name
        )

        parameters[0].value=peta_persil_name

        messages.addMessage("== Proses selesai ==")

        return
    

class Edit_Bentuk_Persil(object):

    def __init__(self):

        self.label = "Edit Bentuk Persil"
        self.description = ""
        self.canRunInBackground = False

    # =====================================================
    # PARAMETER
    # =====================================================

    def getParameterInfo(self):

        param_bentuk = arcpy.Parameter(
            displayName="Bentuk Persil",
            name="bentuk",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )

        param_bentuk.filter.list = [
            "Segi Banyak Tidak Beraturan",
            "Segi Tiga",
            "Segi Empat Tidak Beraturan",
            "Segi Empat Beraturan"
        ]

        output_layer = arcpy.Parameter(
            displayName="Output Persil",
            name="output_persil",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [
            param_bentuk,
            output_layer
        ]

    def isLicensed(self):
        return True

    def updateParameters(
        self,
        parameters
    ):
        return

    def updateMessages(
        self,
        parameters
    ):
        return

    # =====================================================
    # HELPER
    # =====================================================

    def get_skor_bentuk(
        self,
        bentuk
    ):

        mapping = {

            "Segi Banyak Tidak Beraturan": 2,
            "Segi Tiga": 1,
            "Segi Empat Tidak Beraturan": 3,
            "Segi Empat Beraturan": 4

        }

        return mapping.get(
            bentuk,
            1
        )

    def delete_if_exists(
        self,
        path
    ):

        if arcpy.Exists(path):

            try:

                arcpy.management.Delete(
                    path
                )

            except Exception:

                pass

    # =====================================================
    # EXECUTE
    # =====================================================

    def execute(
        self,
        parameters,
        messages
    ):

        import arcpy

        arcpy.env.overwriteOutput = True

        messages.addMessage(
            "== Proses dimulai =="
        )

        # =================================================
        # PARAMETER
        # =================================================

        bentuk = parameters[0].valueAsText
        configs = persil.get_config_values()

        skor_bentuk = (
            self.get_skor_bentuk(
                bentuk
            )
        )

        persil_update = "Persil_layer"

        fields = [
            field.name.lower()
            for field in arcpy.ListFields(
                persil_update
            )
        ]

        required_fields = [
            "BENTUK",
            "S_BENTUK"
        ]

        missing_fields = [
            field
            for field in required_fields
            if field.lower() not in fields
        ]

        if missing_fields:

            messages.addErrorMessage(
                (
                    "Field berikut "
                    "tidak ditemukan: "
                    f"{', '.join(missing_fields)}"
                )
            )

            raise arcpy.ExecuteError

        selected_count = len(
            arcpy.Describe(
                persil_update
            ).FIDSet
        )

        if selected_count <= 0:

            messages.addWarningMessage(
                (
                    "Tidak ada "
                    "fitur yang dipilih"
                )
            )

            return

        updated_count = 0

        with arcpy.da.UpdateCursor(
            persil_update,
            [
                "BENTUK",
                "S_BENTUK"
            ]
        ) as rows:

            for row in rows:

                row[0] = bentuk
                row[1] = float(
                    skor_bentuk
                )

                rows.updateRow(
                    row
                )

                updated_count += 1

        messages.addMessage(
            (
                f"{updated_count} "
                f"fitur berhasil "
                f"diupdate"
            )
        )

        persil_path = os.path.join(configs['project_config']['dataset_path'], 'Persil_Layer')
        
        sim_path = r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Simbologi_Bentuk_Persil.lyrx"
        
        arcpy.management.MakeFeatureLayer(persil_path, "Persil_Layer")
        arcpy.management.ApplySymbologyFromLayer("Persil_Layer", sim_path)


        arcpy.SetParameter(1, "Persil_Layer")

        return


#  Uji Coba
class Sinkronkan_Indikator_Persil(object):

    def __init__(self):
        self.label="Sinkronkan Indikator Persil"
        self.description=""
        self.canRunInBackground=False

    def getParameterInfo(self):

        output_layer=arcpy.Parameter(
            displayName="Output Persil Baru",
            name="output_persil",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [output_layer]

    def isLicensed(self):
        return True

    def updateParameters(self,parameters):
        return

    def updateMessages(self,parameters):
        return

    def delete_if_exists(self,path):

        if arcpy.Exists(path):

            try:
                arcpy.management.Delete(path)

            except Exception:
                pass

    def add_field_if_not_exists(
        self,
        feature_class,
        field_name,
        field_type,
        precision=None
    ):

        fields=[field.name.lower() for field in arcpy.ListFields(feature_class)]

        if field_name.lower() not in fields:

            if precision:

                arcpy.management.AddField(
                    feature_class,
                    field_name,
                    field_type,
                    field_precision=precision
                )

            else:

                arcpy.management.AddField(
                    feature_class,
                    field_name,
                    field_type
                )

    def execute(self,parameters,messages):

        messages.addMessage("== Proses dimulai ==")

        configs=persil.get_config_values()

        dataset_path=configs["project_config"]["dataset_path"]

        appdata=os.path.dirname(
            os.path.dirname(
                os.path.realpath(__file__)
            )
        )

        peta_baru_path=os.path.join(
            dataset_path,
            "Persil_Baru"
        )

        indikator_path=os.path.join(
            dataset_path,
            "Indikator_Perubahan_Persil"
        )

        temp_join="in_memory\\temp_join"

        persil_layer="Persil_Baru"

        required_fc=[
            peta_baru_path,
            indikator_path
        ]

        for fc in required_fc:

            if not arcpy.Exists(fc):

                messages.addErrorMessage(
                    f"Feature class {os.path.basename(fc)} tidak ditemukan"
                )

                raise arcpy.ExecuteError

        self.delete_if_exists(temp_join)
        self.delete_if_exists(persil_layer)

        self.add_field_if_not_exists(
            peta_baru_path,
            "status_per",
            "TEXT"
        )

        self.add_field_if_not_exists(
            peta_baru_path,
            "kelompok_perubahan",
            "SHORT"
        )

        self.add_field_if_not_exists(
            peta_baru_path,
            "klaster_zona",
            "SHORT"
        )

        messages.addMessage("== Spatial Join indikator ==")

        field_mapping=(
            f'IdBidang "IdBidang" true true false 9 Long 0 9,First,#,{peta_baru_path},IdBidang,-1,-1;'
            f'status_per "status_per" true true false 50 Text 0 0,First,#,{indikator_path},status_per,-1,-1;'
            f'kelompok_perubahan "kelompok_perubahan" true true false 2 Short 0 0,First,#,{indikator_path},kelompok_perubahan,-1,-1;'
            f'klaster_zona "klaster_zona" true true false 2 Short 0 0,First,#,{indikator_path},klaster_zona,-1,-1'
        )

        arcpy.analysis.SpatialJoin(
            peta_baru_path,
            indikator_path,
            temp_join,
            "JOIN_ONE_TO_ONE",
            "KEEP_ALL",
            field_mapping,
            "CONTAINS"
        )

        messages.addMessage("== Build indikator dictionary ==")

        indikator_dict={}

        with arcpy.da.SearchCursor(
            temp_join,
            [
                "IdBidang",
                "status_per",
                "kelompok_perubahan",
                "klaster_zona"
            ]
        ) as rows:

            for row in rows:

                indikator_dict[row[0]]={
                    "status_per":row[1],
                    "kelompok_perubahan":row[2],
                    "klaster_zona":row[3]
                }

        messages.addMessage("== Update Persil_Baru ==")

        with arcpy.da.UpdateCursor(
            peta_baru_path,
            [
                "IdBidang",
                "status_per",
                "kelompok_perubahan",
                "klaster_zona",
                "PREDICTED",
                "OBJECTID"
            ]
        ) as rows:

            for row in rows:

                bidang_id=row[0]

                if bidang_id in indikator_dict:

                    indikator=indikator_dict[bidang_id]

                    row[1]=indikator["status_per"]
                    row[2]=indikator["kelompok_perubahan"]
                    row[3]=indikator["klaster_zona"]

                if not row[1]:
                    row[1]="tetap"

                if row[1]=="update":
                    row[4]=None

                rows.updateRow(row)

        arcpy.management.MakeFeatureLayer(
            peta_baru_path,
            persil_layer
        )

        simbologi_path=os.path.join(
            appdata,
            "SimbologiPetaPersil.lyr"
        )

        if os.path.exists(simbologi_path):

            arcpy.management.ApplySymbologyFromLayer(
                persil_layer,
                simbologi_path
            )

        parameters[0].value=persil_layer

        try:

            aprx=arcpy.mp.ArcGISProject("CURRENT")

            current_map=aprx.activeMap

            hidden_layers=[
                "Indikator_Perubahan_Persil",
                "Peta_Lama",
                "Persil"
            ]

            for layer in current_map.listLayers():

                if layer.name in hidden_layers:
                    layer.visible=False

        except Exception:
            pass

        self.delete_if_exists(temp_join)

        messages.addMessage("== Proses selesai ==")

        return
    
class Simpan_Bentuk_Persil(object):

    def __init__(self):
        self.label="Simpan Bentuk Persil"
        self.description=""
        self.canRunInBackground=False

    def getParameterInfo(self):

        output_layer=arcpy.Parameter(
            displayName="Output Persil Baru",
            name="output_persil_baru",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return[output_layer]

    def isLicensed(self):
        return True

    def updateParameters(self,parameters):
        return

    def updateMessages(self,parameters):
        return

    def delete_if_exists(self,path):

        if arcpy.Exists(path):

            try:
                arcpy.management.Delete(path)

            except Exception:
                pass

    def add_field_if_not_exists(
        self,
        feature_class,
        field_name,
        field_type,
        field_length=None
    ):

        fields=[field.name for field in arcpy.ListFields(feature_class)]

        if field_name not in fields:

            if field_type=="TEXT":

                arcpy.management.AddField(
                    feature_class,
                    field_name,
                    field_type,
                    field_length=field_length or 255
                )

            else:

                arcpy.management.AddField(
                    feature_class,
                    field_name,
                    field_type
                )

    def execute(self,parameters,messages):

        import os,arcpy

        arcpy.env.overwriteOutput=True

        messages.addMessage("== Proses dimulai ==")

        configs=persil.get_config_values()
        dataset_path=configs["project_config"]["dataset_path"]

        source_name="Persil_Update"
        target_name="Persil_Baru"

        source_path=os.path.join(dataset_path,source_name)
        target_path=os.path.join(dataset_path,target_name)

        required_feature_classes=[source_path,target_path]

        for fc in required_feature_classes:
            if not arcpy.Exists(fc):
                messages.addErrorMessage(
                    f"Feature class {os.path.basename(fc)} tidak ditemukan"
                )

                raise arcpy.ExecuteError

        join_fields=["IdBidang","bentuk","s_bentuk"]

        source_fields=[
            field.name
            for field in arcpy.ListFields(source_path)
        ]

        target_fields=[
            field.name
            for field in arcpy.ListFields(target_path)
        ]

        missing_source=[
            field
            for field in join_fields
            if field not in source_fields
        ]

        missing_target=[
            field
            for field in join_fields
            if field not in target_fields
        ]

        if missing_source:

            messages.addErrorMessage(
                f"Field source tidak ditemukan: {', '.join(missing_source)}"
            )

            raise arcpy.ExecuteError

        if missing_target:

            messages.addMessage(
                "Field target tidak lengkap, menambahkan field yang hilang pada Persil_Baru"
            )

            field_defs={
                "IdBidang":"LONG",
                "bentuk":"TEXT",
                "s_bentuk":"DOUBLE"
            }

            for field in missing_target:

                self.add_field_if_not_exists(
                    target_path,
                    field,
                    field_defs.get(field,"TEXT"),
                    255 if field=="bentuk" else None
                )

            target_fields=[
                field.name
                for field in arcpy.ListFields(target_path)
            ]

            missing_target=[
                field
                for field in join_fields
                if field not in target_fields
            ]

            if missing_target:

                messages.addErrorMessage(
                    f"Field target tidak ditemukan: {', '.join(missing_target)}"
                )

                raise arcpy.ExecuteError

        messages.addMessage("== Membaca data Persil_Update ==")

        join_dictionary={}

        with arcpy.da.SearchCursor(
            source_path,
            join_fields
        ) as rows:

            for row in rows:

                id_bidang=row[0]

                join_dictionary[id_bidang]={
                    "bentuk":row[1],
                    "s_bentuk":row[2]
                }

        messages.addMessage("== Update bentuk Persil_Baru ==")

        updated_count=0

        with arcpy.da.UpdateCursor(
            target_path,
            join_fields
        ) as rows:

            for row in rows:

                id_bidang=row[0]

                if id_bidang in join_dictionary:

                    row[1]=join_dictionary[id_bidang]["bentuk"]
                    row[2]=join_dictionary[id_bidang]["s_bentuk"]

                    rows.updateRow(row)

                    updated_count+=1

        messages.addMessage(f"{updated_count} fitur berhasil diupdate")

        self.delete_if_exists(target_name)

        arcpy.management.MakeFeatureLayer(
            target_path,
            target_name
        )

        target_field_names=[
            field.name
            for field in arcpy.ListFields(target_name)
        ]

        if "Shape_Leng" in target_field_names:

            try:

                arcpy.management.DeleteField(
                    target_name,
                    "Shape_Leng"
                )

            except Exception:
                pass
        
        persil_path = os.path.join(dataset_path,"Persil_Layer")
        if arcpy.Exists(persil_path):
            arcpy.management.Delete(persil_path)

        arcpy.management.CopyFeatures(
            target_path,
            persil_path,
        )

        parameters[0].value=persil_path

        messages.addMessage("== Proses selesai ==")

        return


class Analisis_Bentuk_Persil_File(object):

    def __init__(self):
        self.label="Analisis Bentuk Persil File"
        self.description=""
        self.canRunInBackground=False

    def getParameterInfo(self):

        input_fc=arcpy.Parameter(
            displayName="Input Polygon",
            name="input_fc",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )

        field_id=arcpy.Parameter(
            displayName="Field ID Bidang",
            name="field_id",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        field_id.parameterDependencies=[input_fc.name]

        output_fc=arcpy.Parameter(
            displayName="Output Feature Class",
            name="output_fc",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output"
        )

        return[
            input_fc,
            field_id,
            output_fc
        ]

    def isLicensed(self):
        return True

    def updateParameters(self,parameters):
        return

    def updateMessages(self,parameters):
        return

    def delete_if_exists(self,path):

        if arcpy.Exists(path):

            try:
                arcpy.management.Delete(path)

            except Exception:
                pass

    def add_field_if_not_exists(
        self,
        feature_class,
        field_name,
        field_type
    ):

        field_names=[
            field.name.lower()
            for field in arcpy.ListFields(feature_class)
        ]

        if field_name.lower() not in field_names:

            arcpy.management.AddField(
                feature_class,
                field_name,
                field_type
            )

    def calculate_azimuth(
        self,
        x_start,
        y_start,
        x_end,
        y_end
    ):

        delta_y=y_end-y_start
        delta_x=x_end-x_start

        if delta_y==0:

            if delta_x>=0:
                azimuth=90

            else:
                azimuth=-90

        else:

            azimuth=math.atan(
                delta_x/delta_y
            )*(180/math.pi)

        if azimuth<-45:
            atrans=azimuth+180

        elif azimuth>=-45 and azimuth<=45:
            atrans=azimuth+90

        else:
            atrans=azimuth

        return(
            azimuth,
            atrans
        )

    def execute(
        self,
        parameters,
        messages
    ):

        import arcpy
        import math

        arcpy.env.overwriteOutput=True

        messages.addMessage(
            "== Proses dimulai =="
        )

        input_fc=parameters[0].valueAsText
        field_id=parameters[1].valueAsText
        output_fc=parameters[2].valueAsText

        if not arcpy.Exists(input_fc):

            messages.addErrorMessage(
                "Input feature class tidak ditemukan"
            )

            raise arcpy.ExecuteError

        temp_line="in_memory\\temp_line"
        temp_split="in_memory\\temp_split"
        temp_dissolve="in_memory\\temp_dissolve"

        cleanup_items=[
            temp_line,
            temp_split,
            temp_dissolve,
            output_fc
        ]

        for item in cleanup_items:
            self.delete_if_exists(item)

        messages.addMessage(
            "== Copy polygon =="
        )

        arcpy.management.CopyFeatures(
            input_fc,
            output_fc
        )

        messages.addMessage(
            "== Polygon to line =="
        )

        arcpy.management.PolygonToLine(
            output_fc,
            temp_line,
            "IGNORE_NEIGHBORS"
        )

        arcpy.management.SplitLine(
            temp_line,
            temp_split
        )

        field_definitions=[
            ("LebarSisi","DOUBLE"),
            ("XStart","DOUBLE"),
            ("XEnd","DOUBLE"),
            ("YStart","DOUBLE"),
            ("YEnd","DOUBLE"),
            ("Azimuth","DOUBLE"),
            ("ATrans","DOUBLE")
        ]

        for field_name,field_type in field_definitions:

            self.add_field_if_not_exists(
                temp_split,
                field_name,
                field_type
            )

        arcpy.management.CalculateField(
            temp_split,
            "LebarSisi",
            "!shape.length!",
            "PYTHON3"
        )

        messages.addMessage(
            "== Hitung azimuth =="
        )


        with arcpy.da.UpdateCursor(
            temp_split,
            [
                "SHAPE@",
                "XStart",
                "XEnd",
                "YStart",
                "YEnd",
                "Azimuth",
                "ATrans"
            ]
        ) as rows:

            for row in rows:

                geometry=row[0]

                x_start=geometry.firstPoint.X
                y_start=geometry.firstPoint.Y
                x_end=geometry.lastPoint.X
                y_end=geometry.lastPoint.Y

                azimuth,atrans=self.calculate_azimuth(
                    x_start,
                    y_start,
                    x_end,
                    y_end
                )

                row[1]=x_start
                row[2]=x_end
                row[3]=y_start
                row[4]=y_end
                row[5]=azimuth
                row[6]=atrans

                rows.updateRow(row)

        messages.addMessage(
            "== Dissolve =="
        )

        arcpy.management.Dissolve(
            temp_split,
            temp_dissolve,
            [field_id],
            [["ATrans","RANGE"]],
            "MULTI_PART",
            "DISSOLVE_LINES"
        )

        self.add_field_if_not_exists(
            output_fc,
            "bentuk",
            "TEXT"
        )

        self.add_field_if_not_exists(
            output_fc,
            "s_bentuk",
            "DOUBLE"
        )

        fields=[
            field.name
            for field in arcpy.ListFields(output_fc)
        ]

        if "Range_ATrans" in fields:

            arcpy.management.DeleteField(
                output_fc,
                "Range_ATrans"
            )

        arcpy.management.JoinField(
            output_fc,
            field_id,
            temp_dissolve,
            field_id,
            ["Range_ATrans"]
        )

        messages.addMessage(
            "== Hitung bentuk persil =="
        )

        with arcpy.da.UpdateCursor(
            output_fc,
            [
                "Range_ATrans",
                "bentuk",
                "s_bentuk"
            ]
        ) as rows:

            for row in rows:

                nilai=row[0]

                if nilai is None:
                    continue

                if nilai<16.3:

                    row[1]="Segi Empat Beraturan"
                    row[2]=4

                elif nilai>=16.3 and nilai<=58:

                    row[1]="Segi Empat Tidak Beraturan"
                    row[2]=3

                else:

                    row[1]="Segi Banyak Tidak Beraturan"
                    row[2]=1

                rows.updateRow(row)

        arcpy.management.AddGeometryAttributes(
            output_fc,
            "POINT_COUNT"
        )

        with arcpy.da.UpdateCursor(
            output_fc,
            [
                "bentuk",
                "s_bentuk",
                "PNT_COUNT"
            ]
        ) as rows:

            for row in rows:

                if row[2] and int(row[2])==4:

                    row[0]="Segi Tiga"
                    row[1]=2

                    rows.updateRow(row)

        fields=[
            field.name
            for field in arcpy.ListFields(output_fc)
        ]

        if "PNT_COUNT" in fields:

            arcpy.management.DeleteField(
                output_fc,
                "PNT_COUNT"
            )

        arcpy.management.MakeFeatureLayer(
            output_fc,
            "Output_Bentuk_Persil"
        )

        parameters[2].value=output_fc

        messages.addMessage(
            "== Proses selesai =="
        )

        return


class Simpan_Perubahan_Ke_Persil_Baru(object):

    def __init__(self):
        self.label="Simpan Perubahan Ke Persil Baru"
        self.description=""
        self.canRunInBackground=False

    def getParameterInfo(self):

        output_layer=arcpy.Parameter(
            displayName="Output Peta Persil",
            name="output_persil",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return[output_layer]

    def isLicensed(self):
        return True

    def updateParameters(self,parameters):
        return

    def updateMessages(self,parameters):
        return

    def delete_if_exists(self,path):
        if arcpy.Exists(path):
            try:
                arcpy.management.Delete(path)
            except Exception:
                pass

    def add_field_if_not_exists(self,feature_class,field_name,field_type,precision=None):

        fields=[field.name for field in arcpy.ListFields(feature_class)]

        if field_name not in fields:

            if precision:
                arcpy.management.AddField(
                    feature_class,
                    field_name,
                    field_type,
                    field_precision=precision
                )

            else:
                arcpy.management.AddField(
                    feature_class,
                    field_name,
                    field_type
                )

    def execute(self,parameters,messages):

        messages.addMessage("== Proses dimulai ==")
        configs=persil.get_config_values()
        dataset_path=configs["project_config"]["dataset_path"]
        appdata=os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        peta_baru_path=os.path.join(dataset_path,"Persil_Baru")
        indikator_path=os.path.join(dataset_path,"Indikator_Perubahan_Persil")
        peta_persil_path=os.path.join(dataset_path,"Peta_Persil")
        peta_persil="Peta_Persil"
        required_fc=[ peta_baru_path, indikator_path ]

        for fc in required_fc:
            if not arcpy.Exists(fc):
                messages.addErrorMessage(f"Feature class {os.path.basename(fc)} tidak ditemukan")
                raise arcpy.ExecuteError

        if arcpy.Exists(peta_persil_path):
            arcpy.management.Delete(peta_persil_path)

        self.delete_if_exists(peta_persil_path)
        self.delete_if_exists(peta_persil)

        messages.addMessage("== Spatial Join Persil ==")
        field_mapping=(
            f'NIB "NIB" true true false 5 Long 0 0,First,#,{peta_baru_path},NIB,-1,-1;'
            f'IdBidang "IdBidang" true true false 9 Long 0 9,First,#,{peta_baru_path},IdBidang,-1,-1;'
            f'ls_asal "ls_asal" true true false 19 Double 0 0,First,#,{peta_baru_path},ls_asal,-1,-1;'
            f'status_per "status_per" true true false 50 Text 0 0,First,#,{indikator_path},status_per,-1,-1;'
            f'kelompok_perubahan "kelompok_perubahan" true true false 2 Short 0 0,First,#,{indikator_path},kelompok_perubahan,-1,-1'
        )
        arcpy.analysis.SpatialJoin(
            peta_baru_path,
            indikator_path,
            peta_persil_path,
            "JOIN_ONE_TO_ONE",
            "KEEP_ALL",
            field_mapping,
            "CONTAINS"
        )

        self.add_field_if_not_exists(
            peta_persil_path,
            "PREDICTED",
            "DOUBLE",
            2
        )

        messages.addMessage("== Copy field PREDICTED ==")
        predicted_dict={}
        with arcpy.da.SearchCursor(
            peta_baru_path,
            ["IdBidang","PREDICTED"]
        ) as rows:
            for row in rows:
                predicted_dict[row[0]]=row[1]
        with arcpy.da.UpdateCursor(
            peta_persil_path,
            ["IdBidang","PREDICTED","status_per"]
        ) as rows:
            for row in rows:
                bidang_id=row[0]
                if bidang_id in predicted_dict:
                    row[1]=predicted_dict[bidang_id]
                if row[2]=="update":
                    row[1]=None
                rows.updateRow(row)

        messages.addMessage("== Update status default ==")

        with arcpy.da.UpdateCursor(
            peta_persil_path,
            ["status_per","IdBidang","OBJECTID"]
        ) as rows:

            for row in rows:

                if not row[0]:
                    row[0]="tetap"
                    row[1]=row[2]

                    rows.updateRow(row)

        self.delete_if_exists(peta_persil)

        arcpy.management.MakeFeatureLayer(
            peta_persil_path,
            peta_persil
        )


        parameters[0].value=peta_persil

        return
    
class Generate_Peta_Akhir(object):

    def __init__(self):

        self.label = "Generate Peta Akhir"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):

        output_layer = arcpy.Parameter(
            displayName="Output Peta Akhir",
            name="output_peta_akhir",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [output_layer]

    def isLicensed(self):
        return True

    def updateParameters(
        self,
        parameters
    ):
        return

    def updateMessages(
        self,
        parameters
    ):
        return

    # =====================================================
    # HELPER
    # =====================================================

    def delete_if_exists(
        self,
        path
    ):

        if arcpy.Exists(path):

            try:

                arcpy.management.Delete(
                    path
                )

            except Exception:

                pass

    def add_field_if_not_exists(
        self,
        feature_class,
        field_name,
        field_type
    ):

        fields = [
            field.name.lower()
            for field in arcpy.ListFields(
                feature_class
            )
        ]

        if field_name.lower() not in fields:

            arcpy.management.AddField(
                feature_class,
                field_name,
                field_type
            )

    def execute( self,  parameters, messages ):

        messages.addMessage(  "== Proses dimulai ==" )

        configs = persil.get_config_values()
        dataset_path =  configs["project_config"]["dataset_path"]
        daftar_variabel_path = configs["project_config"]["daftar_variabel_path"]

        with open(daftar_variabel_path, "r") as f:

            json_conf = (json.load(f))
            variable_config = json_conf['daftar_variabel']

        field_str_type = [
            "bentuk",
            "letak",
            "kls_jln",
            "elvasi",
            "zonasi"
        ]

        fields_dont_delete = []

        for item in variable_config:

            # Extract field_name from list format [display_name, field_name]
            field_name = ( item[1]   if isinstance(item, list) and len(item) > 1  else None )

            if not field_name:
                continue

            fields_dont_delete.append( field_name )

            if ( field_name.lower()  in field_str_type ):

                fields_dont_delete.append( f"s_{field_name}" )

        # =================================================
        # DATASET
        # =================================================

        peta_persil_path = os.path.join( dataset_path,  "Peta_Persil" )

        peta_lama_path = os.path.join( dataset_path,  "Persil_Layer" )

        centroid_path = os.path.join( dataset_path, "Persil_Lama_Centroid" )

        erase_path = os.path.join( dataset_path,  "Peta_Erase" )

        peta_akhir_path = os.path.join( dataset_path,  "Peta_Akhir")

        peta_akhir_layer = "Peta_Akhir"

        # =================================================
        # VALIDASI
        # =================================================

        required_fc = [
            peta_persil_path,
            peta_lama_path
        ]

        for fc in required_fc:

            if not arcpy.Exists(fc):

                messages.addErrorMessage(
                    (
                        f"Feature class "
                        f"{os.path.basename(fc)} "
                        f"tidak ditemukan"
                    )
                )

                raise arcpy.ExecuteError

        # =================================================
        # CLEANUP
        # =================================================

        cleanup_items = [
            centroid_path,
            erase_path,
            peta_akhir_path,
            peta_akhir_layer
        ]

        for item in cleanup_items:

            self.delete_if_exists(
                item
            )

        arcpy.management.FeatureToPoint(
            peta_lama_path,
            centroid_path,
            "INSIDE"
        )

        # =================================================
        # SELECT UPDATE
        # =================================================

        temp_persil = (
            "temp_persil"
        )

        self.delete_if_exists(
            temp_persil
        )

        arcpy.management.MakeFeatureLayer(
            peta_persil_path,
            temp_persil
        )

        arcpy.management.SelectLayerByAttribute(
            temp_persil,
            "NEW_SELECTION",
            "status_per = 'update'"
        )

        # =================================================
        # ERASE
        # =================================================

        messages.addMessage(
            "== Erase centroid =="
        )

        arcpy.analysis.Erase(
            centroid_path,
            temp_persil,
            erase_path
        )

        # =================================================
        # SPATIAL JOIN
        # =================================================

        messages.addMessage(
            "== Spatial Join =="
        )

        arcpy.analysis.SpatialJoin(
            peta_persil_path,
            erase_path,
            peta_akhir_path,
            "JOIN_ONE_TO_ONE",
            "KEEP_ALL",
            "",
            "INTERSECT"
        )

        #  Hapus Field Gabungan

        join_delete_fields = []

        fields = arcpy.ListFields( peta_akhir_path )

        for field in fields:

            if (field.name.lower().startswith( "join_")  or
                field.name.lower().startswith("target_")
            ):

                join_delete_fields.append(field.name)

        if join_delete_fields:

            arcpy.management.DeleteField(
                peta_akhir_path,
                join_delete_fields
            )

        # =================================================
        # OUTPUT LAYER
        # =================================================

        self.delete_if_exists(
            peta_akhir_layer
        )

        arcpy.management.MakeFeatureLayer(
            peta_akhir_path,
            peta_akhir_layer
        )

        parameters[0].value = (
            peta_akhir_layer
        )

        # =================================================
        # CLEANUP TEMP
        # =================================================

        self.delete_if_exists(
            temp_persil
        )

        # =================================================
        # FINISH
        # =================================================

        messages.addMessage(
            "== Proses selesai =="
        )

        return
