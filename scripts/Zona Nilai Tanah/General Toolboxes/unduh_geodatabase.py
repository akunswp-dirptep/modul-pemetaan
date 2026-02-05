import arcpy, os, json, zipfile
from sipentautils import zonalayer
from datetime import datetime
import time

# ======================
# ENVIRONMENT SETTINGS
# ======================

arcpy.env.outputZFlag = "Disabled"  # Menonaktifkan output nilai Z (3D)
arcpy.env.outputMFlag = "Disabled"  # Menonaktifkan output nilai M (measure)

# ======================
# PATH CONFIGURATION
# ======================

# Konfigurasi Path Aplikasi
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

# Konfigurasi Path Project
zl_path = zonalayer.isZonaLayerComply()  # Memeriksa dan mendapatkan path Zona Layer
ws_dir = os.path.dirname(os.path.dirname(os.path.dirname(zl_path)))  # Mendapatkan direktori workspace

# ======================
# ZIP COMPRESSION FUNCTION
# ======================

def compress_directory_to_zip(source_dir, output_folder):
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
                        arcpy.AddMessage(f"  Melewati file terkunci: {file}")
                        continue
                    
                    # Skip file yang sedang digunakan/dikunci
                    try:
                        # Coba buka file untuk membaca (test jika file terkunci)
                        with open(file_path, 'rb') as test_file:
                            pass
                            
                        # Hitung path relatif untuk disimpan dalam ZIP
                        arcname = os.path.relpath(file_path, source_dir)
                        zipf.write(file_path, arcname)
                        arcpy.AddMessage(f"  Menambahkan: {arcname}")
                        
                    except (PermissionError, IOError) as e:
                        arcpy.AddWarning(f"  Tidak dapat mengakses file (mungkin terkunci): {file} - {str(e)}")
                        continue
                    except Exception as e:
                        arcpy.AddWarning(f"  Error pada file {file}: {str(e)}")
                        continue
        
        arcpy.AddMessage(f"Kompresi berhasil! File ZIP disimpan di: {output_zip_path}")
        return output_zip_path
        
    except Exception as e:
        arcpy.AddError(f"Error dalam kompresi ZIP: {str(e)}")
        return None

def compress_with_retry(source_dir, output_folder, max_retries=3):
    """
    Mencoba kompresi dengan beberapa kali retry jika ada file terkunci
    """
    for attempt in range(max_retries):
        arcpy.AddMessage(f"Percobaan kompresi ke-{attempt + 1}")
        
        result = compress_directory_to_zip(source_dir, output_folder)
        if result:
            return result
        
        if attempt < max_retries - 1:
            arcpy.AddMessage(f"Menunggu 2 detik sebelum mencoba lagi...")
            time.sleep(2)
    
    return None

# ======================
# USER INPUT
# ======================

ws_baru = arcpy.GetParameterAsText(0)


# ======================
# MAIN PROCESSING
# ======================

# Pastikan ws_baru memiliki path yang valid
if ws_baru:
    # Pastikan parent directory exists
    parent_dir = os.path.dirname(ws_baru)
    if not os.path.exists(parent_dir) and parent_dir != "":
        arcpy.AddError(f"Directory parent tidak ditemukan: {parent_dir}")
    else:
        # Eksekusi kompresi dengan retry mechanism
        zip_file_path = compress_with_retry(ws_dir, ws_baru)
        
        if zip_file_path:
            arcpy.AddMessage(f"Proses kompresi selesai. File ZIP: {zip_file_path}")
        else:
            arcpy.AddError("Gagal mengompresi workspace setelah beberapa percobaan")
else:
    arcpy.AddError("Folder tujuan tidak valid")