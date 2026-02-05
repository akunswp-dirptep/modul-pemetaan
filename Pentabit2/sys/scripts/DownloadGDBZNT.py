import arcpy, os, sys

# Input Parameters
gdb_asal = arcpy.GetParameterAsText(0)  # The current GDB being worked on
ws_baru = arcpy.GetParameterAsText(1)   # Target folder for saving the backup
nama_pekerjaan = arcpy.GetParameterAsText(2)
nama_menu = arcpy.GetParameterAsText(3)
nama_tahapan = arcpy.GetParameterAsText(4)
jenis_lokasi = arcpy.GetParameterAsText(5)
lokasi = arcpy.GetParameterAsText(6)
tahun = arcpy.GetParameterAsText(7)
revisike = arcpy.GetParameterAsText(8)


# Construct new GDB path in the target folder
gdbname = "Pekerjaan " + nama_pekerjaan + "_Menu " + nama_menu + "_Tahapan " + nama_tahapan + "_" + jenis_lokasi + "_" + lokasi + "_Tahun " + str(tahun) + "_Revisi Ke " + str(revisike) + "_ZoneNilaiTanah.gdb"  # Adjust this name as needed
gdb_baru = os.path.join(ws_baru, gdbname)

if arcpy.Exists(gdb_baru):
    arcpy.AddError('Revisi Ke ' + str(revisike) + ' Sudah Ada')
    sys.exit(0)

# Message to indicate the copying process
arcpy.AddMessage(f"Copying GDB from {gdb_asal} to {gdb_baru}")

# Perform the GDB copy
arcpy.Copy_management(gdb_asal, gdb_baru)

# Success message
arcpy.AddMessage("GDB backup successful.")
