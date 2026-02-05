import os
import arcpy

arcpy.AddMessage("== Proses dimulai ==")

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_config_path = os.path.join(appdata, "config.dat")
conf_sampel_path = os.path.join(appdata, "sampel.dat")

conf_file = open(conf_config_path, "r")
list_config = conf_file.readlines()
conf_file.close()

gdb_path = ""
sampel_path = ""
dataset_path = ""

for line in list_config:
    line = line.replace("\n", "")
    config = []
    config = line.split(",")
    if config[0] == "gdb":
        gdb_path = config[1]
    if config[0] == "dataset":
        dataset_path = config[1]

conf_file = open(conf_sampel_path, "r")
list_config = conf_file.readlines()
conf_file.close()

for line in list_config:
    line = line.replace("\n", "")
    config = []
    config = line.split(",")
    if config[0] == "sampel":
        sampel_path = config[1]

arcpy.AddMessage("== Persiapan ==")

sampel_untuk_prediksi = "Sampel_Model"
sampel_untuk_prediksi_path = os.path.join(dataset_path, sampel_untuk_prediksi)

if arcpy.Exists(sampel_untuk_prediksi_path):
    arcpy.Delete_management(sampel_untuk_prediksi_path)

arcpy.FeatureClassToFeatureClass_conversion(sampel_path, dataset_path, sampel_untuk_prediksi)
cur = arcpy.SearchCursor(os.path.join(gdb_path, "template_var"), "StatusAktif='On'")
detail_fields = []
for c in cur:
    fdet = []
    fdet.append(c.NamaField)
    fdet.append(c.Hubungan)
    detail_fields.append(fdet)
del cur
fields_dont_delete = []
for f in detail_fields:
    fields_dont_delete.append(f[0])

arcpy.AddMessage("== Penyesuaian field dan transformasi data ==")

fields = arcpy.ListFields(sampel_untuk_prediksi_path)
for f in fields:
    if not (f.type == "Geometry" or f.type == "OID" or f.name == "IdBidang" or f.name == "NIB" or "shape".lower() in str(f.name).lower() or f.name in fields_dont_delete or str(f.name).lower() == "NILAI".lower() or f.name=="FID"):
        arcpy.DeleteField_management(sampel_untuk_prediksi_path, f.name)
        arcpy.AddMessage(f.name + " deleted")

for f in detail_fields:
    if f[1] == "Logaritmik":
        arcpy.CalculateField_management(sampel_untuk_prediksi_path, f[0], "math.log(!" + f[0] + "!)", "PYTHON")
    elif f[1] == "Inverse":
        arcpy.CalculateField_management(sampel_untuk_prediksi_path, f[0], "1 / !" + f[0] + "!", "PYTHON")

# field_names = [field.name for field in arcpy.ListFields(sampel_untuk_prediksi_path)]
# if u'N_Prediksi' not in field_names:
#     arcpy.AddField_management(sampel_untuk_prediksi_path, u'N_Prediksi', "DOUBLE")

if arcpy.Exists("Sampel_Model"):
    arcpy.Delete_management("Sampel_Model")

arcpy.MakeFeatureLayer_management(sampel_untuk_prediksi_path, "Sampel_Model")
arcpy.SetParameterAsText(0, "Sampel_Model")

arcpy.AddMessage("== Proses selesai ==")
