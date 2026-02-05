import os
import arcpy

arcpy.AddMessage("== Proses dimulai ==")

untukcluster = arcpy.GetParameterAsText(0)

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

conf_persil_path = os.path.join(appdata, "persil.dat")
conf_file = open(conf_persil_path, "r")
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

a = []
rows = arcpy.da.SearchCursor(persil_path,["cluster","s_zonasi"])
for row in rows:
    # cluster = a.append(row.getValue("cluster"))
    # arcpy.AddMessage(cluster)
    cursora = [row[0] for row in arcpy.da.SearchCursor(persil_path, ["cluster","s_zonasi"], "cluster is not null")]
    if len(cursora) > 1:
        for rowa in cursora:
            a.append(rowa)
            if row[0]:
                b = a.append(row[1])
            arcpy.AddMessage(a)

        del rowa, cursora

del row, rows


