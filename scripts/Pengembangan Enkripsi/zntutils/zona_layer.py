import json
import arcpy, arcgisscripting
import sys
import os
import datetime

def is_zona_layer_comply(show_path_message = True):
    """
    Memeriksa keberadaan, jumlah, dan validitas layer dengan nama 'Zona_Layer' dalam peta aktif.
    
    Fungsi ini akan:
    1. Memeriksa apakah ada layer dengan nama 'Zona_Layer' dalam peta aktif
    2. Memastikan hanya ada SATU layer dengan nama 'Zona_Layer'
    3. Memverifikasi bahwa layer tersebut benar-benar exist menggunakan arcpy.Exists()
    4. Mengembalikan path lengkap ke Zona_Layer jika semua kondisi terpenuhi
    5. Mengeluarkan error yang sesuai jika:
       - Tidak ditemukan Zona_Layer
       - Ditemukan lebih dari satu Zona_Layer
       - Zona_Layer tidak exist (sumber data tidak valid)
    
    Returns:
        str: Path lengkap menuju Zona_Layer yang valid
    
    Raises:
        SystemExit: Jika tidak ditemukan Zona_Layer, ditemukan lebih dari satu, atau layer tidak exist
    """
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    active_map = aprx.activeMap
    
    # Mencari semua layer dengan nama 'Zona_Layer'
    zona_layers = []
    for layer in active_map.listLayers():
        if layer.name == 'Zona_Layer':
            zona_layers.append(layer)
    
    # Memeriksa jumlah Zona_Layer yang ditemukan
    if len(zona_layers) == 0:
        # Tidak ditemukan Zona_Layer sama sekali
        arcpy.AddError('ERROR: File Zona Layer tidak ditemukan dalam peta aktif.')
        sys.exit()
    elif len(zona_layers) > 1:
        # Ditemukan lebih dari satu Zona_Layer
        arcpy.AddError(f'ERROR: Ditemukan {len(zona_layers)} Zona Layer pada project. Hanya boleh ada satu Zona Layer.')
        sys.exit()
    else:
        # Hanya ditemukan satu Zona_Layer (kondisi yang diinginkan)
        zona_layer = zona_layers[0]
        
        # Memeriksa apakah layer exist menggunakan arcpy.Exists()
        if not arcpy.Exists(zona_layer):
            arcpy.AddError('ERROR: Zona Layer ditemukan tetapi sumber data tidak valid atau tidak exist.')
            sys.exit()
        
        # Mendapatkan path lengkap ke Zona_Layer
        try:
            # Untuk feature layer, kita bisa mendapatkan katalog path
            if hasattr(zona_layer, 'dataSource'):
                layer_path = zona_layer.dataSource
                if show_path_message:
                    arcpy.AddMessage(f'Sukses: Zona Layer ditemukan dan valid. \nPath: {layer_path}')
                return layer_path
            else:
                # Untuk layer types lainnya
                arcpy.AddWarning('Peringatan: Tidak dapat menentukan path lengkap Zona Layer, tetapi layer valid.')
                return str(zona_layer)
                
        except Exception as e:
            arcpy.AddError(f'ERROR: Tidak dapat mengakses path Zona Layer. Detail: {str(e)}')
            sys.exit()

def save_gdb(ws_path: str, gdb_path: str, label: str):
    """
    Membuat salinan (backup) dari sebuah file geodatabase (GDB) ke folder 'Backup' 
    di dalam workspace yang ditentukan.

    Fungsi ini digunakan untuk menyimpan hasil proses atau versi sementara dari 
    sebuah geodatabase dengan nama file yang mencakup waktu pembuatan dan label 
    identifikasi. Tujuannya adalah agar setiap hasil pemrosesan tersimpan secara 
    historis dan tidak menimpa file lama.

    Parameter
    ----------
    ws_path : str
        Path ke direktori utama (workspace) tempat folder 'Backup' akan dibuat.
        Contoh: r"C:\\GIS_Project\\Workspace"

    gdb_path : str
        Path lengkap menuju geodatabase (*.gdb) yang ingin disalin atau dibackup.
        Contoh: r"C:\\GIS_Project\\Workspace\\Data\\ProsesZNT.gdb"

    label : str
        Label atau keterangan tambahan yang akan disertakan pada nama file hasil backup.
        Misalnya: "ZNT", "NBT", "Final", dsb.

    Return
    -------
    None
        Fungsi tidak mengembalikan nilai. 
        Namun, akan menghasilkan file GDB baru di folder "Backup" 
        dengan format nama:
        `process_<tanggal>_<jam>_<label>.gdb`

    Contoh
    -------
    >>> saveGDB(r"C:\\GIS_Project\\Workspace", r"C:\\GIS_Project\\Workspace\\Data\\ProsesZNT.gdb", "ZNT")
    # Akan membuat backup di:
    # C:\\GIS_Project\\Workspace\\Backup\\process_22102025_094530_ZNT.gdb
    """

    # --- Membuat folder Backup jika belum ada ---
    path = os.path.join(ws_path, 'Backup')
    if not os.path.exists(path):
        os.makedirs(path)

    # --- Menentukan nama file GDB hasil backup dengan timestamp ---
    now = datetime.datetime.now()
    dataset = 'process_' + now.strftime("%d%m%Y_%H%M%S") + "_" + label + ".gdb"
    backup_dataset_path = os.path.join(ws_path, "Backup", dataset)

    # --- Hapus backup lama jika nama file sama (kemungkinan sangat kecil tapi untuk keamanan) ---
    if arcpy.Exists(backup_dataset_path):
        arcpy.Delete_management(backup_dataset_path)

    # --- Membuat objek geoprocessing dan melakukan proses penyalinan GDB ---
    gp = arcgisscripting.create()
    gp.Copy_management(gdb_path, backup_dataset_path)

    # --- Terapkan kebijakan retensi: simpan maksimal 5 backup terakhir ---
    try:
        # Kumpulkan semua folder GDB pada folder Backup
        items = []
        for name in os.listdir(path):
            full = os.path.join(path, name)
            # Geodatabase adalah folder dengan akhiran .gdb
            if name.lower().endswith('.gdb') and os.path.isdir(full):
                items.append(full)

        # Jika jumlah backup melebihi 5, hapus yang paling lama
        if len(items) > 5:
            def _parse_timestamp_from_name(gdb_full_path):
                base = os.path.basename(gdb_full_path)
                # contoh: process_22102025_094530_ZNT.gdb
                name_no_ext = os.path.splitext(base)[0]
                parts = name_no_ext.split('_')
                if len(parts) >= 3 and parts[0].lower() == 'process':
                    date_part = parts[1]
                    time_part = parts[2]
                    try:
                        return datetime.datetime.strptime(date_part + time_part, '%d%m%Y%H%M%S')
                    except Exception:
                        return None
                return None

            # Susun item berdasarkan waktu dari nama; fallback ke mtime jika gagal
            def _sort_key(gdb_full_path):
                ts = _parse_timestamp_from_name(gdb_full_path)
                if ts is not None:
                    return ts
                # fallback: gunakan waktu modifikasi filesystem
                try:
                    return datetime.datetime.fromtimestamp(os.path.getmtime(gdb_full_path))
                except Exception:
                    # jika gagal, taruh paling lama dengan epoch
                    return datetime.datetime.fromtimestamp(0)

            items_sorted = sorted(items, key=_sort_key, reverse=True)  # terbaru dulu
            to_delete = items_sorted[5:]  # sisakan 5 terbaru

            for old_gdb in to_delete:
                try:
                    arcpy.Delete_management(old_gdb)
                except Exception as e:
                    arcpy.AddWarning(f"Gagal menghapus backup lama {os.path.basename(old_gdb)}: {str(e)}")
    except Exception as e:
        arcpy.AddWarning(f"Terjadi masalah saat menerapkan retensi backup: {str(e)}")

def check_if_there_selected_field():
    """
    Memeriksa apakah masih ada fitur yang sedang dipilih (selected features)
    pada layer bernama 'Zona_Layer' sebelum menjalankan proses utama.

    Fungsi ini digunakan sebagai langkah pencegahan untuk memastikan bahwa
    pengguna tidak sedang dalam mode editing atau memiliki fitur yang masih
    terpilih di layer 'Zona_Layer'. Jika ada fitur yang masih terpilih, maka
    proses akan dihentikan dan pesan error akan ditampilkan di ArcGIS Pro.

    Tujuan
    -------
    - Mencegah konflik data atau error selama pemrosesan geoprocessing.
    - Menjamin bahwa operasi berjalan dalam kondisi layer yang bersih (tanpa seleksi aktif).

    Return
    -------
    None
        Fungsi tidak mengembalikan nilai.
        Jika ada fitur yang masih terseleksi, fungsi akan:
        - Menampilkan pesan error melalui `arcpy.AddError()`.
        - Menghentikan eksekusi skrip menggunakan `sys.exit(1)`.

    Contoh
    -------
    >>> checkIfThereSelectedField()
    # Jika tidak ada fitur yang terseleksi → proses lanjut.
    # Jika ada fitur terseleksi → tampil pesan error dan skrip berhenti.
    """

    # Nama layer yang akan diperiksa
    layer_name = "Zona_Layer"

    # Hitung jumlah fitur yang sedang terseleksi menggunakan FIDSet
    selected_features = len(arcpy.Describe(layer_name).FIDSet)

    # Jika masih ada fitur terseleksi, tampilkan pesan error dan hentikan program
    if selected_features > 0:
        arcpy.AddError(f"ERROR: Fitur Editing masih menyala pada {layer_name}. Matikan terlebih dahulu sebelum melanjutkan proses.")
        sys.exit(1)

def unselect_field():
    try:
    # Nonaktifkan field selection terlebih dahulu
        arcpy.SetProgressor("default", "Menonaktifkan field selection...")
        arcpy.env.autoCancelling = True
        
        # Akses project dan peta aktif
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        m = aprx.activeMap
        
        arcpy.AddMessage("Memulai proses membersihkan seleksi pada layer...")
        
        # Loop melalui semua layer
        for lyr in m.listLayers():
            if lyr.isFeatureLayer and lyr.supports("SHOWLABELS"):
                try:
                    arcpy.AddMessage(f"Memproses layer: {lyr.name}")
                    # Clear selection pada layer
                    arcpy.SelectLayerByAttribute_management(lyr, "CLEAR_SELECTION")
                except Exception as layer_error:
                    arcpy.AddWarning(f"Gagal membersihkan seleksi pada layer {lyr.name}: {str(layer_error)}")
                    continue
        
        arcpy.AddMessage("Proses membersihkan seleksi selesai.")
    
    except arcpy.ExecuteError:
        arcpy.AddError("ERROR:" + arcpy.GetMessages(2))
        sys.exit()
        
    except Exception as e:
        arcpy.AddError(f"ERROR: Terjadi kesalahan: {str(e)}")
        sys.exit()

    finally:
        # Pastikan untuk membersihkan resource
        try:
            del aprx, m
        except:
            pass

def get_config_values():

    """
    MENDAPATKAN KONFIGURASI DARI FILE config.json
    
    Fungsi ini:
    1. Mendapatkan path layer zona dari modul zonalayer
    2. Membaca file config.json dari workspace directory
    3. Mengekstrak parameter-parameter penting
    4. Membangun semua path yang diperlukan untuk proses
    5. Memvalidasi keberadaan geodatabase
    
    Returns:
        dict: Dictionary berisi semua path dan parameter konfigurasi
    """
    zl_path = is_zona_layer_comply(show_path_message=False)  # Validasi compliance layer zona
    ws_dir = os.path.dirname(os.path.dirname(os.path.dirname(zl_path)))  # Navigasi ke root workspace
    config_path = os.path.join(ws_dir, "config.json")  # Path ke file config
    configs = None
    
    # Membaca file config.json jika ada
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            configs = json.load(f)

    # Validasi path GDB
    if not arcpy.Exists(configs['dataset_path']):
        arcpy.AddError(f"Path GDB tidak valid: {configs['dataset_path']}")
        raise ValueError(f"Path GDB tidak valid: {configs['dataset_path']}")
    appdata = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))
    ui_folder = os.path.join(appdata, "ui")
    symbology_folder = os.path.join(ui_folder, "symbology")
    temp_folder = os.path.join(appdata, "temp")

    config_dan_paths = {        
        "dataset_path": configs['dataset_path'],
        "tahun": configs['THNNILAI'],
        "provinsi": configs['WADMPR'] ,
        "kota": configs['WADMKK'],   
        "coor": configs['coord'],
        "gdb_path": configs['gdb_path'],
        "zl_path": zl_path,
        "appdata": appdata,
        "symbology_folder": symbology_folder,
        "temp_folder": temp_folder,
        "ws_dir": ws_dir}

    return config_dan_paths

   

