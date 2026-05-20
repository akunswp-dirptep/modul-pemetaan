import json
import arcpy, arcgisscripting
import sys
import os
from .constant import LAYER_PERSIL


def is_persil_layer_comply(show_path_message = True):
    """
    Memeriksa keberadaan, jumlah, dan validitas layer dengan nama 'Persil' dalam peta aktif.
    
    Fungsi ini akan:
    1. Memeriksa apakah ada layer dengan nama 'Persil' dalam peta aktif
    2. Memastikan hanya ada SATU layer dengan nama 'Persil'
    3. Memverifikasi bahwa layer tersebut benar-benar exist menggunakan arcpy.Exists()
    4. Mengembalikan path lengkap ke Persil jika semua kondisi terpenuhi
    5. Mengeluarkan error yang sesuai jika:
       - Tidak ditemukan Persil
       - Ditemukan lebih dari satu Persil
       - Persil tidak exist (sumber data tidak valid)
    
    Returns:
        str: Path lengkap menuju Persil yang valid
    
    Raises:
        SystemExit: Jika tidak ditemukan Persil, ditemukan lebih dari satu, atau layer tidak exist
    """
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    active_map = aprx.activeMap
    
    # Mencari semua layer dengan nama 'Persil'
    layer_persil = []
    for layer in active_map.listLayers():
        if layer.name == LAYER_PERSIL:
            layer_persil.append(layer)
    
    # Memeriksa jumlah Persil yang ditemukan
    if len(layer_persil) == 0:
        # Tidak ditemukan Persil sama sekali
        arcpy.AddError('ERROR: File Persil tidak ditemukan dalam peta aktif.')
        sys.exit()
    elif len(layer_persil) > 1:
        # Ditemukan lebih dari satu Persil
        arcpy.AddError(f'ERROR: Ditemukan {len(layer_persil)} Persil pada project. Hanya boleh ada satu Persil.')
        sys.exit()
    else:
        # Hanya ditemukan satu Persil (kondisi yang diinginkan)
        persil = layer_persil[0]
        
        # Memeriksa apakah layer exist menggunakan arcpy.Exists()
        if not arcpy.Exists(persil):
            arcpy.AddError('ERROR: Persil ditemukan tetapi sumber data tidak valid atau tidak exist.')
            sys.exit()
        
        # Mendapatkan path lengkap ke Persil
        try:
            # Untuk feature layer, kita bisa mendapatkan katalog path
            if hasattr(persil, 'dataSource'):
                layer_path = persil.dataSource
                if show_path_message:
                    arcpy.AddMessage(f'Sukses: Persil ditemukan dan valid. \nPath: {layer_path}')
                return layer_path
            else:
                # Untuk layer types lainnya
                arcpy.AddWarning('Peringatan: Tidak dapat menentukan path lengkap Persil, tetapi layer valid.')
                return str(persil)
                
        except Exception as e:
            arcpy.AddError(f'ERROR: Tidak dapat mengakses path Persil. Detail: {str(e)}')
            sys.exit()

def get_config_values():

    """
    MENDAPATKAN KONFIGURASI DARI FILE config.json
    
    Fungsi ini:
    1. Mendapatkan path layer persil dari modul persil
    2. Membaca file config.json dari workspace directory
    3. Mengekstrak parameter-parameter penting
    4. Membangun semua path yang diperlukan untuk proses
    5. Memvalidasi keberadaan geodatabase
    
    Returns:
        dict: Dictionary berisi semua path dan parameter konfigurasi
    """
    persil_path = is_persil_layer_comply(show_path_message=False)  # Validasi compliance layer zona
    ws_dir = os.path.dirname(os.path.dirname(os.path.dirname(persil_path)))  # Navigasi ke root workspace
    config_path = os.path.join(ws_dir, "project_config.json")  # Path ke file config
    configs = None
    if arcpy.Exists(config_path):
         with open(config_path, 'r') as f:
            configs = json.load(f)

    # Validasi path GDB
    if configs["project_config"]['ws_path'] != ws_dir:
        arcpy.AddError(f"Path Geodatabase tidak valid, folder kemungkinan dipindahkan dari tempat awal \n Silahkan perbaiki path kembali dengan cara berikut:\n1. Ekspor Geodatabase menggunakaan Tools Ekspor Geodatabase pada menu Backup dan Ekspor Hasil\n2. Import kembali Geodatabase yang sudah diekspor menggunakan Tools Import Workspace pada menu Persiapan Data")
        sys.exit(1)

    return configs

def set_config_values(configs):

    persil_path = is_persil_layer_comply(show_path_message=False)  # Validasi compliance layer zona
    ws_dir = os.path.dirname(os.path.dirname(os.path.dirname(persil_path)))  # Navigasi ke root workspace
    config_path = os.path.join(ws_dir, "project_config.json")  # Path ke file config
    configs = None
    if arcpy.Exists(config_path):
         with open(config_path, 'w') as f:
            json.dump(configs, f)

    return configs

