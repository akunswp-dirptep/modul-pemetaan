import os
import arcpy

appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_persil_path = os.path.join(appdata, "persil.dat")

conf_file = open(conf_persil_path, "r")
list_config = conf_file.readlines()
conf_file.close()

dataset_path = ""

for line in list_config:
    line = line.replace("\n", "")
    persil_config = []
    persil_config = line.split(",")
    if persil_config[0] == "dataset":
        dataset_path = persil_config[1]

persil = "Persil_Baru"
persil_path = os.path.join(dataset_path, persil)

ada_seleksi = 0
ada_seleksi = len(arcpy.Describe(persil).FIDSet)

if ada_seleksi > 0:
    with arcpy.da.UpdateCursor (persil, ["NILAI_LAMA","perubahan"]) as rows:
        for row in rows:
            row[0] = None
            row[1] = "menyebar"
            rows.updateRow(row)
    del row, rows

arcpy.MakeFeatureLayer_management(persil_path, "Persil_Baru")
arcpy.ApplySymbologyFromLayer_management("Persil_Baru", os.path.join(appdata, "Simbologi_PersilIndividual.lyrx"))
arcpy.SetParameter(0, "Persil_Baru")




