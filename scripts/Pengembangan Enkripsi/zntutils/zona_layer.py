import json
import arcpy, arcgisscripting
import sys
import os
import datetime

from .constant import PROJECT_CONFIG_FILE_NAME
from .system_utils import get_all_config

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

def check_if_there_selected_field(feature_layer = "Zona_Layer"):
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
    layer_name = feature_layer

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
    MENDAPATKAN KONFIGURASI DARI FILE config.json atau penilaian_tanah_config.bin
    
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
    new_config_path = os.path.join(ws_dir, PROJECT_CONFIG_FILE_NAME)  # Path ke file config baru (bin)
    configs = None
    if arcpy.Exists(config_path):
         with open(config_path, 'r') as f:
            configs = json.load(f)
    elif arcpy.Exists(new_config_path):
        configs = get_all_config(new_config_path)  

    # Validasi path GDB
    if configs['ws_path'] != ws_dir:
        arcpy.AddError(f"Path Workspace tidak valid, folder kemungkinan dipindahkan dari tempat awal \n Silahkan perbaiki path kembali dengan cara berikut:\n1. Ekspor Workspace menggunakaan Tools Ekspor Workspace pada menu Backup dan Ekspor Hasil\n2. Import kembali Workspace yang sudah diekspor menggunakan Tools Import Workspace pada menu Persiapan Data")
        sys.exit(1)
    appdata = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))
    ui_folder = os.path.join(appdata, "ui")
    symbology_folder = os.path.join(ui_folder, "symbology")
    temp_folder = os.path.join(appdata, "temp")

    config_dan_paths = {        
        "dataset_path": configs.get('dataset_path'),
        "tahun": configs.get('THNNILAI'),
        "provinsi": configs.get('WADMPR'),
        "kota": configs.get('WADMKK'),   
        "coor": configs.get('coord'),
        "gdb_path": configs.get('gdb_path'),
        "skala": configs.get('skala'), 
        "zl_path": zl_path,
        "appdata": appdata,
        "symbology_folder": symbology_folder,
        "temp_folder": temp_folder,
        "ws_dir": ws_dir
        }

    return config_dan_paths

def delete_bad_file():
    zl_path = is_zona_layer_comply(show_path_message=False)  # Validasi compliance layer zona
    gdb_path = os.path.dirname(os.path.dirname(zl_path))  # Navigasi ke root gdb
    arcpy.env.workspace = gdb_path
    keep_dataset = 'znt_ds'

    for fc in arcpy.ListFeatureClasses():
        fc_path = os.path.join(gdb_path, fc)
        if arcpy.Exists(fc_path):
            arcpy.management.Delete(fc_path)

    # 2. Hapus table di root
    for table in arcpy.ListTables():
        table_path = os.path.join(gdb_path, table)
        if arcpy.Exists(table_path):
            arcpy.management.Delete(table_path)

    # 3. Hapus raster (kalau ada)
    for raster in arcpy.ListRasters():
        raster_path = os.path.join(gdb_path, raster)
        if arcpy.Exists(raster_path):
            arcpy.management.Delete(raster_path)

    # 4. Hapus feature dataset selain yang ingin dipertahankan
    for dataset in arcpy.ListDatasets(feature_type='feature'):
        if dataset.lower() != keep_dataset.lower():
            dataset_path = os.path.join(gdb_path, dataset)
            if arcpy.Exists(dataset_path):
                arcpy.management.Delete(dataset_path)

    arcpy.management.ClearWorkspaceCache()
    return

def is_nullish_value(value):
    return value is None or (isinstance(value, str) and not value.strip())

def validate_zona_layer_before_upload(layer):
    if not layer or not arcpy.Exists(layer):
        return "Layer delineasi tidak ditemukan."

    try:
        desc = arcpy.Describe(layer)
        oid_field_name = desc.OIDFieldName
        shape_type = str(getattr(desc, "shapeType", "")).lower()
        
        # 1. BARU: Pengecekan Field Wajib
        field_names_upper = [field.name.upper() for field in arcpy.ListFields(layer)]
        wajib_fields = ["NOZN", "JNSZN", "NILAIZN", 'WADMPR', 'WADMKK']
        missing_fields = [f for f in wajib_fields if f not in field_names_upper]
        
        if missing_fields:
            return f"Validasi gagal: Layer tidak memiliki field wajib yang diperlukan. Pastikan mengupload Zona_Layer yang benar."

        # 2. Mengumpulkan Field Atribut
        attribute_fields = []
        for field in arcpy.ListFields(layer):
            field_name_upper = field.name.upper()
            if field.type in ("OID", "Geometry"):
                continue
            if field.name == oid_field_name or field.required:
                continue
            if field_name_upper in ("SHAPE_LENGTH", "SHAPE_AREA"):
                continue
            attribute_fields.append(field.name)

        # 3. Persiapan Cursor
        cursor_fields = ["OID@"]
        include_shape_area = shape_type == "polygon"
        if include_shape_area:
            cursor_fields.append("SHAPE@AREA")
        cursor_fields.extend(attribute_fields)

        # 4. Validasi per Baris (Row)
        with arcpy.da.SearchCursor(layer, cursor_fields) as cursor:
            for row in cursor:
                object_id = row[0]
                current_index = 1

                # Cek Luas Geometri
                if include_shape_area:
                    shape_area = row[current_index]
                    current_index += 1
                    if shape_area is None or shape_area <= 0:
                        return f"Terdapat baris dengan luas geometri 0 atau tidak valid pada OBJECTID {object_id}."

                # Cek Atribut Kosong
                if attribute_fields:
                    attribute_values = row[current_index:]
                    if all(is_nullish_value(value) for value in attribute_values):
                        return f"Terdapat baris yang semua nilai atributnya null/kosong pada OBJECTID {object_id}."
                        
    except arcpy.ExecuteError:
        return f"Gagal memvalidasi layer delineasi: {arcpy.GetMessages(2)}"
    except Exception as exc:
        return f"Gagal memvalidasi layer delineasi: {exc}"

    return None

def validate_kesesuaian_zona(config_dan_paths):
    """
    Fungsi untuk mengecek kesesuaian jenis zona antara layer delineasi (Zona Layer)
    dengan Titik Sampel/Titik Zona.
    """
    ts_path = os.path.join(config_dan_paths['dataset_path'], "Titik_Sampel")
    tz_path = os.path.join(config_dan_paths['dataset_path'], "Titik_Zona")
    zl_path = os.path.join(config_dan_paths['dataset_path'], "Zona_Layer")
    
    # Hapus topologi jika tidak diperlukan di proses ini
    zl_topology_path = os.path.join(config_dan_paths['dataset_path'], "Zona_Layer_Topology")
    if arcpy.Exists(zl_topology_path):
        arcpy.management.Delete(zl_topology_path)

    identity_layers = []
    
    try:
        # 1. Identity Titik Zona (jika ada)
        if arcpy.Exists(tz_path):
            arcpy.analysis.Identity(tz_path, zl_path, "identity_tz")
            identity_layers.append("identity_tz")

        # 2. Identity Titik Sampel (jika ada)
        if arcpy.Exists(ts_path):
            arcpy.analysis.Identity(ts_path, zl_path, "identity_ts")
            identity_layers.append("identity_ts")

        # 3. Pengumpulan Data (Dictionary)
        listzona = {}
        listsampel = {}

        for identity_fc in identity_layers:
            with arcpy.da.SearchCursor(identity_fc, ["NOZN", "JNSZN", "Zoning"]) as cursor:
                for nozona, jenis, zoning in cursor:
                    if nozona not in listzona:
                        listzona[nozona] = set()
                    if jenis is not None:
                        listzona[nozona].add(jenis)

                    if nozona not in listsampel:
                        listsampel[nozona] = set()
                    if zoning is not None:
                        listsampel[nozona].add(zoning)

        # 4. Pengecekan Perbedaan (Menggantikan UpdateCursor)
        mismatches = []
        
        with arcpy.da.SearchCursor(zl_path, ["NOZN"]) as cursor:
            for row in cursor:
                nozona = row[0]
                
                zl_type = set(listzona.get(nozona, []))
                titiksampel = set(listsampel.get(nozona, []))

                # Jika ada perbedaan antara jenis zona dan titik sampel
                if zl_type != titiksampel:
                    jenis_str = ", ".join(map(str, sorted(zl_type))) if zl_type else "Kosong"
                    sampel_str = ", ".join(map(str, sorted(titiksampel))) if titiksampel else "Tidak ada"
                    
                    mismatches.append(
                        f"- NOZN {nozona}: Zona layer ({jenis_str}) sedangkan Jenis Zona Pada Titik ({sampel_str})"
                    )

        # 5. Kembalikan string jika ada error, atau None jika aman
        if mismatches:
            error_message = "Terdapat perbedaan jenis zona pada data berikut:\n" + "\n".join(mismatches)
            return error_message

    except arcpy.ExecuteError:
        return f"Gagal memvalidasi kesesuaian zona: {arcpy.GetMessages(2)}"
    except Exception as exc:
        return f"Gagal memvalidasi kesesuaian zona: {exc}"
        
    finally:
        # 6. Cleanup temporary identity (ditaruh di blok finally agar selalu tereksekusi)
        for fc in identity_layers:
            if arcpy.Exists(fc):
                arcpy.management.Delete(fc)

    return None

def validasi_klaster_zona(config_dan_paths):
    """
    Memvalidasi kesesuaian atribut klaster antara 
    Titik Zona dan Zona Layer menggunakan tools Identity.
    """
    # 1. Ekstrak base path
    dataset_path = config_dan_paths.get('dataset_path', '')
    
    tz_path = os.path.join(dataset_path, "Titik_Zona")
    zl_path = os.path.join(dataset_path, "Zona_Layer")
    
    if not arcpy.Exists(tz_path):
        return None

    zona_beda = []

    # Helper function internal untuk menambahkan pesan unik (filter duplikat)
    def tambah_pesan(pesan):
        if pesan not in zona_beda:
            zona_beda.append(pesan)
    
    # 2. Persiapan variabel identity
    layer_path = tz_path
    layer_name = "Titik_Zona"
    identity_fc = r"memory\identity_tz"

    # Helper function internal untuk konversi string dengan aman
    def safe_str(val):
        return str(val).strip() if val is not None else None

    # Bersihkan file temporary di memory jika sebelumnya masih ada
    if arcpy.Exists(identity_fc):
        arcpy.management.Delete(identity_fc)

    # 3. Jalankan tools Identity
    # Identity ini akan menempelkan atribut Zona_Layer ke Titik_Zona yang ada di dalamnya
    arcpy.analysis.Identity(layer_path, zl_path, identity_fc)
    
    # Hanya perlu field NOZN dan klaster (cluster dari Titik, cluster_1 dari Zona Layer)
    kolom_perlu_dicek = ["NOZN", "cluster", "cluster_1"]

    with arcpy.da.SearchCursor(identity_fc, kolom_perlu_dicek) as cursor:
        for row in cursor:
            nozona = row[0]
            cluster_titik = row[1]
            cluster_zona = row[2]

            cluster_titik_str = safe_str(cluster_titik)
            cluster_zona_str = safe_str(cluster_zona)

            is_null_error = False

            # Validasi 1: Klaster Titik tidak boleh Null atau kosong
            if cluster_titik_str is None or cluster_titik_str == "":
                tambah_pesan(f"NOZN {nozona} (Klaster pada Titik Zona bernilai Null/Kosong)")
                is_null_error = True

            # Validasi 2: Klaster Zona tidak boleh Null atau kosong jika ada Titik Zona di dalamnya
            if cluster_zona_str is None or cluster_zona_str == "":
                tambah_pesan(f"NOZN {nozona} (Klaster pada Zona Layer bernilai Null/Kosong padahal memiliki Titik Zona)")
                is_null_error = True

            # Validasi 3: Kesesuaian Cluster
            # Hanya jalankan validasi ini jika tidak ada yang Null di atas
            if not is_null_error:
                if cluster_titik_str != cluster_zona_str:
                    tambah_pesan(f"NOZN {nozona} (Klaster Titik: {cluster_titik}, Klaster Zona: {cluster_zona})")

    # Bersihkan output memory setelah kursor selesai membaca
    arcpy.management.Delete(identity_fc)

    return zona_beda


def validasi_duplikasi_nozn(config_dan_paths):
        zl_path = os.path.join(config_dan_paths['dataset_path'], 'Zona_Layer')
        nozn_map = {}
        with arcpy.da.SearchCursor(zl_path, ["OBJECTID", "NOZN"]) as cur:
            for oid, nozn in cur:
                if nozn:
                    nozn_map.setdefault(str(nozn), []).append(oid)

        dup = [k for k, v in nozn_map.items() if len(v) > 1]
        return dup
            

def get_field_name(layer_path, expected):
        for f in arcpy.ListFields(layer_path):
            if f.name.lower() == expected.lower():
                return f.name
        return None

def validasi_nilai_tanah_negatif(layer_path, label):
        nilai_field = get_field_name(layer_path, "nilai")
        if not nilai_field:
            arcpy.AddWarning(f"Field 'nilai' tidak ditemukan pada {label}")
            sys.exit(0)

        invalid = []
        with arcpy.da.SearchCursor(layer_path, ["OID@", nilai_field]) as cur:
            for oid, nilai in cur:
                if nilai is not None and nilai < 0:
                    invalid.append((oid, nilai))

        return invalid

def validasi_titik_sampel_dan_titik_zona_dalam_satu_zona(config_dan_paths):
        dataset_path = config_dan_paths['dataset_path']

        tz_path = os.path.join(dataset_path, "Titik_Zona")
        zl_path = os.path.join(dataset_path, "Zona_Layer")
        ts_path = os.path.join(dataset_path, 'Titik_Sampel')

        zout = "memory/zona_join"
        sout = "memory/sampel_join"
        
        arcpy.analysis.SpatialJoin(zl_path, tz_path, zout, 'JOIN_ONE_TO_MANY')
        arcpy.analysis.SpatialJoin(zl_path, ts_path, sout, 'JOIN_ONE_TO_MANY')

        zona_dengan_titik_zona = set()
        with arcpy.da.SearchCursor(zout, ["Join_Count", "TARGET_FID"]) as cur:
            for jc, fid in cur:
                if jc > 0:
                    zona_dengan_titik_zona.add(fid)

        mapping_oid_dengan_nozn = {}
        with arcpy.da.SearchCursor(zl_path, ["OBJECTID", "NOZN"]) as cur:
            for oid, nozn in cur:
                mapping_oid_dengan_nozn[oid] = nozn

        outlier_nozn = set()
        with arcpy.da.SearchCursor(sout, ["Join_Count", "TARGET_FID"]) as cur:
            for jc, fid in cur:
                if jc > 0 and fid in zona_dengan_titik_zona:
                    nozn = mapping_oid_dengan_nozn.get(fid)
                    if nozn:
                        outlier_nozn.add(nozn)

        return outlier_nozn

def validasi_metode_pembuatan_min_3_titik_sampel(config_dan_paths):
        dataset_path = config_dan_paths['dataset_path']

        tz_path = os.path.join(dataset_path, "Titik_Zona")
        zl_path = os.path.join(dataset_path, "Zona_Layer")
        ts_path = os.path.join(dataset_path, 'Titik_Sampel')

        zout = "memory/zona_join"
        sout = "memory/sampel_join"
        
        arcpy.analysis.SpatialJoin(zl_path, tz_path, zout, 'JOIN_ONE_TO_MANY')
        arcpy.analysis.SpatialJoin(zl_path, ts_path, sout, 'JOIN_ONE_TO_MANY')

        zona_dengan_titik_zona = set()
        with arcpy.da.SearchCursor(zout, ["Join_Count", "TARGET_FID"]) as cur:
            for jc, fid in cur:
                if jc > 0:
                    zona_dengan_titik_zona.add(fid)

        mapping_oid_dengan_nozn = {}
        with arcpy.da.SearchCursor(zl_path, ["OBJECTID", "NOZN"]) as cur:
            for oid, nozn in cur:
                mapping_oid_dengan_nozn[oid] = nozn
            
        zona_outlier = {}
        with arcpy.da.SearchCursor(sout, ["TARGET_FID", "Join_Count"]) as cur:
            for fid, jc in cur:
                if jc > 0 and fid not in zona_dengan_titik_zona:
                    zona_outlier[fid] = zona_outlier.get(fid, 0) + jc

        invalid = []
        for fid, count in zona_outlier.items():
            if count < 3:
                invalid.append(f" NOZN {mapping_oid_dengan_nozn.get(fid)} - Jumlah Titik {count}")
            
        return invalid

def validasi_cluster_minimal_satu_titik(config_dan_paths):
        dataset_path = config_dan_paths['dataset_path']

        tz_path = os.path.join(dataset_path, "Titik_Zona")
        zl_path = os.path.join(dataset_path, "Zona_Layer")

        zout = "memory/zona_join"        
        arcpy.analysis.SpatialJoin(zl_path, tz_path, zout, 'JOIN_ONE_TO_MANY')

        zona_dengan_titik_zona = set()
        with arcpy.da.SearchCursor(zout, ["Join_Count", "TARGET_FID"]) as cur:
            for jc, fid in cur:
                if jc > 0:
                    zona_dengan_titik_zona.add(fid)

        clusters = {'1': {}, '2': {}}

        with arcpy.da.SearchCursor(zl_path, ["OBJECTID", "cluster", "JNSZN"]) as cur:
            for oid, cl, jnszn in cur:
                if cl is not None:
                    clusters[str(jnszn)].setdefault(cl, []).append(oid)

        invalid_cluster = []
        for jnszn, cluster_dict in clusters.items():
            for cl, oids in cluster_dict.items():
                if not any(oid in zona_dengan_titik_zona for oid in oids):
                    invalid_cluster.append(f"Jenis Zona {jnszn}: Klaster {cl}")

        return invalid_cluster


def validasi_zona_layer_min_3_titik_sampel(config_dan_paths):
    dataset_path = config_dan_paths.get('dataset_path', '')

    zl_path = os.path.join(dataset_path, "Zona_Layer")
    ts_path = os.path.join(dataset_path, 'Titik_Sampel')

    sout = r"memory\sampel_join_all"
    
    # Hapus sisa memory jika fungsi dijalankan berulang
    if arcpy.Exists(sout):
        arcpy.management.Delete(sout)

    # Lakukan Spatial Join untuk melihat berapa banyak titik sampel yang jatuh di tiap zona
    arcpy.analysis.SpatialJoin(zl_path, ts_path, sout, 'JOIN_ONE_TO_MANY')

    # 1. Petakan OID dengan NOZN dan inisialisasi jumlah titik sampel = 0 untuk SEMUA zona
    mapping_oid_dengan_nozn = {}
    jumlah_titik_per_zona = {}
    
    with arcpy.da.SearchCursor(zl_path, ["OBJECTID", "NOZN"]) as cur:
        for oid, nozn in cur:
            mapping_oid_dengan_nozn[oid] = nozn
            jumlah_titik_per_zona[oid] = 0  # Default 0 agar zona yang kosong (0 titik) tetap terdeteksi

    # 2. Hitung akumulasi titik sampel dari hasil Spatial Join
    with arcpy.da.SearchCursor(sout, ["TARGET_FID", "Join_Count"]) as cur:
        for fid, jc in cur:
            if fid in jumlah_titik_per_zona:
                jumlah_titik_per_zona[fid] += jc

    # 3. Evaluasi semua zona, catat jika titik sampel kurang dari 3
    invalid = []
    for fid, count in jumlah_titik_per_zona.items():
        if count < 3:
            nozn = mapping_oid_dengan_nozn.get(fid)
            invalid.append(f"NOZN {nozn} - Jumlah Titik {count}")

    # Bersihkan output memory
    if arcpy.Exists(sout):
        arcpy.management.Delete(sout)

    return invalid

def validate_simpangan_baku_relatif(config_dan_paths):
    """
    Fungsi untuk mengecek apakah nilai Simpangan Baku Relatif (SMPBKREL)
    pada tiap zona memenuhi syarat toleransi berdasarkan skala pengerjaan.
    """
    zl_path = os.path.join(config_dan_paths['dataset_path'], "Zona_Layer")
    
    # 1. Mengambil nilai skala dalam bentuk integer
    skala = config_dan_paths.get("skala")
    
    if skala is None:
        return "Skala Kosong"

    # 2. Menentukan batas toleransi berdasarkan skala
    if skala == 2500:
        toleransi_maksimal = 20.0
    elif skala == 5000:
        toleransi_maksimal = 22.5
    elif skala == 10000:
        toleransi_maksimal = 25.0
    elif skala == 25000:
        toleransi_maksimal = 30.0
    else:
        # Jika skala lebih besar dari 25000, Anda bisa menyesuaikan defaultnya
        toleransi_maksimal = 30.0 

    mismatches = []
    
    try:
        # 3. Pengecekan ketersediaan field yang dibutuhkan
        existing_fields = [f.name for f in arcpy.ListFields(zl_path)]
        if "SMPBKREL" not in existing_fields or "NOZN" not in existing_fields:
            return "Gagal memvalidasi: Field 'SMPBKREL' atau 'NOZN' belum tersedia di Zona_Layer. Harap pastikan kalkulasi ZNT sudah berjalan."

        # 4. Evaluasi nilai per zona
        with arcpy.da.SearchCursor(zl_path, ["NOZN", "SMPBKREL"]) as cursor:
            for nozona, smpbkrel in cursor:
                if smpbkrel is not None:
                    # Jika nilai simpangan baku relatif melebihi toleransi
                    if smpbkrel > toleransi_maksimal:
                        mismatches.append(
                            f"- NOZN {nozona}: Simpangan Baku Relatif ({round(smpbkrel, 2)}%) melebihi batas {toleransi_maksimal}%"
                        )
                else:
                    pass

        # 5. Kembalikan string error jika ada zona yang melanggar toleransi
        if mismatches:
            error_message = (
                f"Validasi Gagal: Terdapat zona yang melebihi batas toleransi Simpangan Baku Relatif (≤ {toleransi_maksimal}% untuk skala 1:{skala}):\n" + 
                "\n".join(mismatches)
            )
            return error_message

    except arcpy.ExecuteError:
        return f"Gagal mengeksekusi validasi simpangan baku relatif: {arcpy.GetMessages(2)}"
    except Exception as exc:
        return f"Gagal mengeksekusi validasi simpangan baku relatif: {exc}"

    # Jika list mismatches kosong, berarti semua zona aman
    return None

def validate_luas_minimal_zona(config_dan_paths):
    """
    Fungsi untuk mengecek apakah luas area tiap zona memenuhi syarat 
    Luas Zona Terkecil (minimal unit) berdasarkan skala pengerjaan peta.
    Aturan: (½ cm x skala peta) x (½ cm x skala peta)
    """
    zl_path = os.path.join(config_dan_paths['dataset_path'], "Zona_Layer")
    
    # 1. Mengambil nilai skala dalam bentuk integer
    skala = config_dan_paths.get("skala")
    
    if skala is None:
        return "Skala Kosong"

    if skala == 25000:
        luas_minimal = 15625.0    # 1,5625 Ha
    elif skala == 10000:
        luas_minimal = 2500.0     # 0,25 Ha
    elif skala == 5000:
        luas_minimal = 625.0      # 0,0625 Ha
    elif skala == 2500:
        luas_minimal = 156.25     # 0,015625 Ha
    else:
        luas_minimal = (0.005 * skala) ** 2 

    mismatches = []
    
    try:
        # 3. Pengecekan ketersediaan field yang dibutuhkan
        existing_fields = [f.name for f in arcpy.ListFields(zl_path)]
        if "NOZN" not in existing_fields:
            return "Gagal memvalidasi: Field 'NOZN' belum tersedia di Zona_Layer."

        # 4. Evaluasi nilai luas per zona
        with arcpy.da.SearchCursor(zl_path, ["NOZN", "SHAPE@AREA"]) as cursor:
            for nozona, luas_area in cursor:
                if luas_area is not None:

                    if luas_area < luas_minimal:
                        mismatches.append(
                            f"- NOZN {nozona}: Luas area ({round(luas_area, 2)} m2) kurang dari batas minimal ({luas_minimal} m2)"
                        )
                else:
                    mismatches.append(f"- NOZN {nozona}: Geometri kosong atau luas tidak terbaca.")

        # 5. Kembalikan string error jika ada zona yang melanggar ketentuan luas minimal
        if mismatches:
            error_message = (
                f"Validasi Gagal: Terdapat zona dengan luas di bawah batas minimum (≥ {luas_minimal} m2 untuk skala 1:{skala}):\n" + 
                "\n".join(mismatches)
            )
            return error_message

    except arcpy.ExecuteError:
        return f"Gagal mengeksekusi validasi luas minimal: {arcpy.GetMessages(2)}"
    except Exception as exc:
        return f"Gagal mengeksekusi validasi luas minimal: {exc}"

    return None