import arcpy
import os
import json
import zipfile

# ======================
# ENVIRONMENT SETTINGS
# ======================
arcpy.env.addOutputsToMap = True
arcpy.env.outputZFlag = "Disabled"
arcpy.env.outputMFlag = "Disabled"

# ======================
# PATH CONFIGURATION
# ======================

# Konfigurasi Path Aplikasi
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

# ======================
# USER INPUT
# ======================
zip_file = arcpy.GetParameterAsText(0)
output_path = arcpy.GetParameterAsText(1)
zona_layer_path = ''
def update_config_file(config_path, output_path):
    """
    Memperbarui file config.json dengan path yang baru
    """
    try:
        # Baca file config.json
        with open(config_path, 'r') as config_file:
            config_data = json.load(config_file)
        
        # Perbarui path sesuai dengan output_path
        config_data["ws_path"] = output_path
        config_data["dataset_path"] = os.path.join(output_path, "ZoneNilaiTanah.gdb", "znt_ds")
        config_data["gdb_path"] = os.path.join(output_path, "ZoneNilaiTanah.gdb")
        
        # Tulis kembali ke file
        with open(config_path, 'w') as config_file:
            json.dump(config_data, config_file, indent=4)
        
        return True
        
    except Exception as e:
        arcpy.AddError(f"Error saat memperbarui config.json: {e}")
        return False

def check_and_extract_config(zip_path):
    """
    Mengecek apakah file zip mengandung config.json atau config.dat
    dan melakukan ekstraksi jika ditemukan
    """
    try:
        # Cek apakah file zip ada
        if not os.path.exists(zip_path):
            arcpy.AddError(f"File zip tidak ditemukan: {zip_path}")
            return False
        
        # Buka file zip untuk membaca isinya
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Dapatkan daftar semua file dalam zip
            file_list = zip_ref.namelist()
            
            # Cek apakah ada config.json atau config.dat
            has_config_json = any('config.json' in f.lower() for f in file_list)
         
            
            if has_config_json:
                arcpy.AddMessage("File config ditemukan dalam zip. Melakukan ekstraksi...")
                
                # Tentukan direktori tujuan ekstraksi
                extract_dir = output_path
                
                # Buat direktori jika belum ada
                if not os.path.exists(extract_dir):
                    os.makedirs(extract_dir)
                
                # Ekstrak semua file
                zip_ref.extractall(extract_dir)
                
                arcpy.AddMessage(f"File berhasil diekstrak ke: {extract_dir}")
                
                # Cari path file config yang sebenarnya
                config_path = None
                for root, dirs, files in os.walk(extract_dir):
                    for file in files:
                        if file.lower() == 'config.json':
                            config_path = os.path.join(root, file)
                            break
                    if config_path:
                        break
                
                if config_path:
                    arcpy.AddMessage(f"File config ditemukan di: {config_path}")
                    
                    # Baca isi config file jika diperlukan
                    try:
                        if config_path.lower().endswith('.json'):
                            with open(config_path, 'r') as config_file:
                                config_data = json.load(config_file)
                                arcpy.AddMessage("Isi config.json sebelum diubah:")
                                arcpy.AddMessage(json.dumps(config_data, indent=2))
                            
                            # Perbarui config.json dengan path baru
                            update_success = update_config_file(config_path, output_path)
                            
                            if update_success:
                                # Baca lagi untuk menampilkan hasil perubahan
                                with open(config_path, 'r') as config_file:
                                    updated_config = json.load(config_file)
                                    zona_layer_path = os.path.join(updated_config['dataset_path'], 'Zona_Layer')
                                    arcpy.AddMessage("Isi config.json setelah diubah:")
                                    arcpy.AddMessage(json.dumps(updated_config, indent=2))
                    except Exception as e:
                        arcpy.AddWarning(f"Tidak dapat membaca file config: {e}")
                
                return True, zona_layer_path
            else:
                arcpy.AddMessage("Tidak ditemukan config.json dalam file zip")
                return False
                
    except zipfile.BadZipFile:
        arcpy.AddError("File yang dipilih bukan file zip yang valid")
        return False
    except Exception as e:
        arcpy.AddError(f"Error saat memproses file zip: {e}")
        return False

# ======================
# MAIN EXECUTION
# ======================
if zip_file:
    arcpy.AddMessage(f"Memproses file: {zip_file}")
    success, zona_layer_path = check_and_extract_config(zip_file)
    if success:
        arcpy.AddMessage("Proses selesai dengan sukses")
        arcpy.SetParameter(2, zona_layer_path)
    else:
        arcpy.AddMessage("Proses tidak berhasil")
else:
    arcpy.AddError("Tidak ada file zip yang dipilih")