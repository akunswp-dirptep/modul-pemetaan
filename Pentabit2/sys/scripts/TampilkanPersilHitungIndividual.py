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

persil_fields = [field.name for field in arcpy.ListFields(persil_path)]
if "perubahan" not in persil_fields:
    arcpy.AddField_management(persil_path, "perubahan", "TEXT")

with arcpy.da.UpdateCursor (persil_path, ["status_per","clusternew", "perubahan"]) as rows:
    for row in rows:
        if row[0] == "update":
            if row[1]:
                row[2] = "mengelompok"
            else:
                row [2] = "menyebar"
        rows.updateRow(row)
del row, rows

if "lb_dpn_i" not in persil_fields and "ls_tnh_i" not in persil_fields:
    arcpy.AddField_management(persil_path, "lb_dpn_i", "SHORT")
    arcpy.AddField_management(persil_path, "ls_tnh_i", "SHORT")

if "NILAI_LAMA" not in persil_fields:
    arcpy.AddField_management(persil_path, "NILAI_LAMA", "DOUBLE")

rows = arcpy.UpdateCursor(persil_path)
for row in rows:
    value_ls_tnh = row.getValue("ls_tnh")
    value_lb_dpn = row.getValue("lb_dpn")
    if value_ls_tnh < 50:
        row.setValue("ls_tnh_i", 1)
    elif value_ls_tnh > 1000:
        row.setValue("ls_tnh_i", 2)
    elif value_ls_tnh >= 200 and value_ls_tnh <= 1000:
        row.setValue("ls_tnh_i", 3)
    elif value_ls_tnh >= 50 and value_ls_tnh < 100:
        row.setValue("ls_tnh_i", 4)
    elif value_ls_tnh >= 100 and value_ls_tnh <= 200:
        row.setValue("ls_tnh_i", 5)
    
    if value_lb_dpn < 6:
        row.setValue("lb_dpn_i", 1)
    elif value_lb_dpn > 6 and value_lb_dpn <= 10:
        row.setValue("lb_dpn_i", 2)
    elif value_lb_dpn > 10 and value_lb_dpn <= 15:
        row.setValue("lb_dpn_i", 3)
    elif value_lb_dpn > 15:
        row.setValue("lb_dpn_i", 4)
    elif value_lb_dpn <= 0:
        row.setValue("lb_dpn_i", 0)
    rows.updateRow(row)
del row, rows

arcpy.CalculateField_management(persil_path, "NILAI_LAMA", '!PREDICTED!', "PYTHON3")
arcpy.CalculateField_management(persil_path, "PREDICTED", 'None', "PYTHON3")
arcpy.MakeFeatureLayer_management(persil_path, "Persil_Baru")
arcpy.ApplySymbologyFromLayer_management("Persil_Baru", os.path.join(appdata, "Simbologi_PersilIndividual.lyrx"))
##arcpy.ApplySymbologyFromLayer_management("Persil_Baru", os.path.join(appdata, "Simbologi_PersilIndividual_v2_1.lyrx"))
arcpy.SetParameter(0, "Persil_Baru")

aprx = arcpy.mp.ArcGISProject("CURRENT")
map = aprx.activeMap
layers = map.listLayers()
for layer in layers:
    if layer.name == "Titik_Sampel_Update":
        layer.visible = False


