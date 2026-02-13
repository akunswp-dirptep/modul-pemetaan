import json
import os, arcpy, datetime



def reload_all_toolboxes_in_folder(toolbox_folder):
     
    if not os.path.exists(toolbox_folder):
        arcpy.AddError(f"Folder toolbox tidak ditemukan: {toolbox_folder}")
        return
        
     # Cari semua file .pyt di folder
    pyt_files = [f for f in os.listdir(toolbox_folder) if f.endswith('.pyt')]
        
    if not pyt_files:
        arcpy.AddWarning(f"Tidak ada file .pyt ditemukan di {toolbox_folder}")
        return
        
    # Refresh katalog
    try:
        arcpy.management.RefreshCatalog(toolbox_folder)
    except Exception:
        try:
            arcpy.RefreshCatalog(toolbox_folder)
        except Exception:
            pass
        
    # Load toolbox di proyek saat ini
    try:
        # Hapus dan reload menggunakan ImportToolbox (lebih reliable)
        for pyt_file in pyt_files:
            pyt_path = os.path.join(toolbox_folder, pyt_file)
            try:
                arcpy.ImportToolbox(pyt_path)
                arcpy.AddMessage(f"✓ Berhasil memuat: {pyt_file}")
            except Exception as e:
                arcpy.AddWarning(f"✗ Gagal memuat {pyt_file}: {str(e)}")
            
        arcpy.AddMessage(f"Selesai: semua toolbox telah di-reload")
            
    except Exception as e:
        arcpy.AddWarning(f"Error saat reload toolbox: {str(e)}")

def get_preferred_server_connection():
    config_path = r'C:\PenilaianTanah\config\user_config.json'
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r') as config_file:
                data = json.load(config_file)
                preferred_server = data.get('preferred_server', None)
                return preferred_server
        else:
            return None
    except Exception as e:
        arcpy.AddError(f"Gagal membaca user config: {str(e)}")
        return None

def setup_preferred_server_connection(preferred_server: str):

    config_path = r'C:\PenilaianTanah\config\user_config.json'
    try:
        # Cek apakah file ada
        if os.path.exists(config_path):
            # File ada, baca isinya
            try:
                with open(config_path, 'r') as config_file:
                    data = json.load(config_file)
                    
                # Validasi format JSON
                if 'preferred_server' not in data or not isinstance(data['preferred_server'], str):
                    # Format tidak sesuai, buat struktur baru
                    data = {"preferred_server": preferred_server}
                
                if data['preferred_server'] != preferred_server:
                    data['preferred_server'] = preferred_server
                    
            except json.JSONDecodeError:
                # File rusak/tidak valid, buat struktur baru
                arcpy.AddWarning("File config.json rusak, membuat struktur baru...")
                data = {"preferred_server": preferred_server}
        else:
            # File belum ada, buat struktur baru
            # Pastikan direktori Menu ada
            menu_dir = os.path.dirname(config_path)
            if not os.path.exists(menu_dir):
                os.makedirs(menu_dir)
            
            data = {"preferred_server": preferred_server}
        

        # Simpan kembali ke file
        with open(config_path, 'w') as config_file:
            json.dump(data, config_file, indent=4)
        
        return True
        
    except Exception as e:
        arcpy.AddError(f"Gagal menyimpan user config: {str(e)}")
        return False
    
def current_year():
    try:
        return int(datetime.now().year)
    except Exception:
        return None
 
def renew_preferred_server(server:str):
    
    setup_preferred_server_connection(server)
    all_toolboxes_folder_need_reload = [
                r"C:\PenilaianTanah\scripts\Pengembangan Enkripsi\Pembaruan ZNT",
                r"C:\PenilaianTanah\scripts\Pengembangan Enkripsi\Pembuatan ZNT"
            ]

    try:
        for folder in all_toolboxes_folder_need_reload:
            reload_all_toolboxes_in_folder(folder)

    except Exception as e:
        arcpy.AddWarning(f"Gagal memuat ulang toolbox: {str(e)}")
