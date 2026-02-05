import os, arcpy, json
from sipentautils import zonalayer

# ======================
# ENVIRONMENT SETTINGS
# ======================
arcpy.env.outputZFlag = "Disabled"
arcpy.env.outputMFlag = "Disabled"

# ======================
# PATH CONFIGURATION
# ======================

# Konfigurasi Path Aplikasi
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


# Konfigurasi Path Project
zl_path = zonalayer.isZonaLayerComply()
ws_dir = os.path.dirname(os.path.dirname(os.path.dirname(zl_path)))
config_path = os.path.join(ws_dir, "config.json")
configs = None
if os.path.exists(config_path):
    with open(config_path, 'r') as f:
        configs = json.load(f)

gdb_path = configs['gdb_path']

# ======================
# UNSELECT FIELD 
# ======================

zonalayer.checkIfThereSelectedField()

# ======================
# SET BACKUP
# ======================
tools_label = 'Pembuatan_ZNT-Pengolahan_Data_Dasar-Membuat_Kodifikasi_Zona'
zonalayer.saveGDB(ws_dir, gdb_path, label=tools_label)

# ======================
# MAIN PROCESSING
# ======================
# Mendapatkan daftar field yang ada dalam layer
field_names = [field.name for field in arcpy.ListFields(zl_path)]

# Memeriksa apakah field HISTZONE sudah ada
if "HISTZONE" not in field_names:
    """
    JIKA HISTZONE BELUM ADA:
    Membuat field HISTZONE baru dengan urutan nomor dan tipe zona
    """

    # Membuat field sementara untuk menyimpan tipe zona
    arcpy.AddField_management(zl_path, "temp", "STRING")

    # Mengisi field temp dengan 'N' atau 'P' berdasarkan JNSZN. N berarti NON-PERTANIAN, P berarti PERTANIAN
    expression = "abc(!JNSZN!)"
    codeblock = """def abc(JNSZN):
        if JNSZN == 1:
            return 'N'  
        elif JNSZN == 2:
            return 'P'  
        else:
            return ''   
        """
    arcpy.management.CalculateField(zl_path, "temp", expression, "PYTHON3", codeblock)
    
    # Menggabungkan NOZN dan temp menjadi HISTZONE (contoh: "1N", "2P")
    arcpy.management.CalculateField(zl_path, "HISTZONE", "str(!NOZN!) + !temp!", "PYTHON3")
    
    # Menghapus field sementara
    arcpy.management.DeleteField(zl_path, "temp")

else:
    """
    JIKA HISTZONE SUDAH ADA:
    Memperbarui nilai HISTZONE dengan mempertahankan nilai historis
    """
    
    # Menyimpan nilai HISTZONE yang ada ke field sementara
    arcpy.management.AddField(zl_path, "temp1", "STRING")
    arcpy.management.CalculateField(zl_path, "temp1", "!HISTZONE!", "PYTHON3")


    # Membuat field sementara untuk nilai zona baru
    arcpy.management.AddField(zl_path, "temp2", "STRING")
    
    # Mengisi field temp2 dengan 'N' atau 'P' berdasarkan JNSZN
    expression = "abc(!JNSZN!)"
    codeblock = """def abc(JNSZN):
        if JNSZN == 1:
            return 'N' 
        elif JNSZN == 2:
            return 'P' 
        else:
            return ''  
        """
    arcpy.management.CalculateField(zl_path, "temp2", expression, "PYTHON3", codeblock)
    
    # Membuat field sementara untuk gabungan NOZN + temp2
    arcpy.management.AddField(zl_path, "temp", "STRING")
    arcpy.management.CalculateField(zl_path, "temp", "str(!NOZN!) + !temp2!", "PYTHON3")
    
    # Membuat field sementara untuk hasil akhir
    arcpy.management.AddField(zl_path, "temp3", "STRING")
    """
    MEMPROSES LOGIKA HISTZONE:
    - Membandingkan nilai lama (temp1) dengan nilai baru (temp)
    - Menerapkan logika khusus untuk mempertahankan atau menggabungkan nilai
    """
    with arcpy.da.UpdateCursor(zl_path, ["temp1", "temp", "temp3"]) as rows:
        for row in rows:
            # Jika nilai lama pendek (<3 karakter)
            if len(row[0]) < 3:
                if row[0] == row[1]:  # Jika nilai lama sama dengan baru
                    row[2] = row[1]   # Gunakan nilai baru
                elif row[0] != row[1]:  # Jika berbeda
                    row[2] = row[0] + row[1]  # Gabungkan lama + baru
            
            # Jika nilai lama panjang (≥3 karakter)
            else:
                if row[0][-2:] == row[1][-2:]:  # Jika 2 karakter akhir sama
                    row[2] = row[0]  # Pertahankan nilai lama
                elif row[0][-2:] != row[1][-2:]:  # Jika 2 karakter akhir berbeda
                    row[2] = row[0] + row[1]  # Gabungkan lama + baru
            
            rows.updateRow(row)
    del rows, row
    
    # Memindahkan hasil akhir ke field HISTZONE
    arcpy.CalculateField_management(zl_path, "HISTZONE", "!temp3!", "PYTHON3")
    
    # Membersihkan semua field sementara
    arcpy.DeleteField_management(zl_path, "temp2")
    arcpy.DeleteField_management(zl_path, "temp")
    arcpy.DeleteField_management(zl_path, "temp1")
    arcpy.DeleteField_management(zl_path, "temp3")
