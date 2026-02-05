import os, arcpy


appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

dataset_path = ""

conf_jalan_path = os.path.join(appdata, "persil.dat")

conf_file = open(conf_jalan_path, "r")
list_config = conf_file.readlines()
conf_file.close()
for line in list_config:
    line = line.replace("\n", "")
    persil_config = []
    persil_config = line.split(",")
    if persil_config[0] == "dataset":
        dataset_path = persil_config[1]

persil = "Persil_Baru"
persil_path = os.path.join(dataset_path, persil)

with arcpy.da.UpdateCursor (persil_path, ["indeks_rata", "NILAI_LAMA", "PREDICTED"]) as cursors:
    for row in cursors:
        if not row [2]:
            if row[1] and row [0]:
                #row [2] = row [1] * row [0]
                row [2] = (row [1] * row [0])/100
        cursors.updateRow(row)
del row, cursors

arcpy.MakeFeatureLayer_management(persil_path, "Persil_Baru")
arcpy.ApplySymbologyFromLayer_management("Persil_Baru", os.path.join(appdata, "Simbologi_PetaNBTUpdate.lyrx"))
arcpy.SetParameter(0, "Persil_Baru")
