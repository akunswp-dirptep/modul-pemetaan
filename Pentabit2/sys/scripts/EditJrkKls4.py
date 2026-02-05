import os
import arcpy

arcpy.AddMessage("== Proses dimulai ==")

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_jalan_path = os.path.join(appdata, "persil.dat")

conf_file = open(conf_jalan_path, "r")
list_config = conf_file.readlines()
conf_file.close()

dataset_path = ""
persil = ""
persil_path = ""
simbologi_path = os.path.join(appdata, "SimbologiLebarJalanPersil.lyr")

for line in list_config:
    line = line.replace("\n", "")
    persil_config = []
    persil_config = line.split(",")
    if persil_config[0] == "persil":
        persil = persil_config[1].split(";")[0]
        persil_path = persil_config[1].split(";")[1]

val = float(arcpy.GetParameterAsText(0))

j_4 = "Jarak_Persil_Ke_ArteriSekunder"
rows = arcpy.UpdateCursor(j_4)
# rows = arcpy.UpdateCursor(persil)

for row in rows:
    row.setValue("J_Kls4", val)
    if val > 0:
        val = "1"
    else:
        val = "0"
    row.setValue("sim_j_4", val)
    rows.updateRow(row)

del row
del rows

# if arcpy.Exists(persil):
#     arcpy.ApplySymbologyFromLayer_management(persil, simbologi_path)

arcpy.RefreshTOC()
arcpy.RefreshActiveView()
