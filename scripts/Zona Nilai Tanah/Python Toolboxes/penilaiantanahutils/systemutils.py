import os, arcpy

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
