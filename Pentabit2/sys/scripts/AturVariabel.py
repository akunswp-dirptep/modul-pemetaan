import os
import arcpy

fieldname = arcpy.GetParameterAsText(1)
status = arcpy.GetParameterAsText(2)
hubungan = arcpy.GetParameterAsText(3)

arcpy.AddMessage("== Proses dimulai ==")

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_config_path = os.path.join(appdata, "config.dat")

conf_file = open(conf_config_path, "r")
list_config = conf_file.readlines()
conf_file.close()

gdb_path = ""
dataset_path = ""

for line in list_config:
    line = line.replace("\n", "")
    config = []
    config = line.split(",")
    if config[0] == "gdb":
        gdb_path = config[1]
    if config[0] == "dataset":
        dataset_path = config[1]

tabel_path = os.path.join(gdb_path, "template_var")

cursor = arcpy.UpdateCursor(tabel_path)
try:
    for row in cursor:
        # arcpy.AddMessage(row.NamaField + " " + fieldname)
        if row.NamaField == fieldname:
            # arcpy.AddMessage("OK")
            cursor.deleteRow(row)
    del cursor

    cursor = arcpy.InsertCursor(tabel_path)
    feat = cursor.newRow()
    feat.NamaField = fieldname
    feat.StatusAktif = status
    feat.Hubungan = hubungan
    cursor.insertRow(feat)
except:
    arcpy.AddMessage("Error...")
    del cursor
finally:
    del cursor

arcpy.AddMessage("== Proses selesai ==")
