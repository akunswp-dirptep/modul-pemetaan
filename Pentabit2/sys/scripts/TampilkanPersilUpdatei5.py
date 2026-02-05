import os
import arcpy

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_jalan_path = os.path.join(appdata, "persil.dat")

conf_file = open(conf_jalan_path, "r")
list_config = conf_file.readlines()
conf_file.close()

dataset_path = ""

for line in list_config:
    line = line.replace("\n", "")
    jalan_config = []
    jalan_config = line.split(",")
    if jalan_config[0] == "dataset":
        dataset_path = jalan_config[1]

persil = "Persil_Baru"
persil_path = os.path.join(dataset_path, persil)
#simbologi_path = os.path.join(appdata, "Simbologi_PersilZonasi.lyrx")

if arcpy.Exists(persil):
    arcpy.Delete_management(persil)
arcpy.MakeFeatureLayer_management(persil_path, persil)
#arcpy.ApplySymbologyFromLayer_management(persil, simbologi_path)
arcpy.SetParameterAsText(0, persil)


listzona = {}  

with arcpy.da.SearchCursor(persil,['zonasi','s_zonasi', 'min_lb_jln']) as rows:
    for row in rows:
            if row[0]:
                listzona[row[0]] = row[1:]

new_string = ';'.join([f"'{key}' {int(val[0] or 0)} {int(val[1] or 0)}" for key, val in listzona.items()])

zonasiupdate_conf_path = os.path.join(appdata, "zonasiupdate.dbf")


if os.path.exists(zonasiupdate_conf_path):
    os.remove(zonasiupdate_conf_path)

arcpy.CreateTable_management(appdata, "zonasiupdate.dbf", "")

with open(zonasiupdate_conf_path, "w") as f:
    f.write(new_string)