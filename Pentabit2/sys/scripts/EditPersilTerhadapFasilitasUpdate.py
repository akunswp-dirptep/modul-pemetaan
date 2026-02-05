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
persil_update = "Persil_Baru"
persil_path = ""
simbologi_path = os.path.join(appdata, "SimbologiLebarJalanPersil.lyr")

for line in list_config:
    line = line.replace("\n", "")
    persil_config = []
    persil_config = line.split(",")
    if persil_config[0] == "persil":
        persil = persil_config[1].split(";")[0]
        persil_path = persil_config[1].split(";")[1]

namafield = arcpy.GetParameterAsText(1)
val = arcpy.GetParameter(2)

arcpy.AddMessage(namafield + ": " + str(val))

field_names = [field.name for field in arcpy.ListFields(persil_path)]
if namafield not in field_names:
    arcpy.AddField_management(persil_path, namafield, 'DOUBLE')

ada_seleksi = 0
ada_seleksi = len(arcpy.Describe(persil_update).FIDSet)

if ada_seleksi <= 0:
    sys.exit()

rows = arcpy.UpdateCursor(persil_update)

for row in rows:
    row.setValue(namafield, val)
    rows.updateRow(row)

del row
del rows

# if arcpy.Exists(persil):
#     arcpy.ApplySymbologyFromLayer_management(persil, simbologi_path)

#update 18/10/2021
#arcpy.RefreshTOC()
#arcpy.RefreshActiveView()
