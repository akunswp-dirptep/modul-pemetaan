import os
import arcpy

arcpy.AddMessage("== Proses dimulai ==")

persil_skor_baru = arcpy.GetParameterAsText(0)

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_config_path = os.path.join(appdata, "config.dat")
conf_persil_path = os.path.join(appdata, "persil.dat")

conf_file = open(conf_config_path, "r")
list_config = conf_file.readlines()
conf_file.close()

gdb_path = ""
persil_path = ""
dataset_path = ""

for line in list_config:
    line = line.replace("\n", "")
    config = []
    config = line.split(",")
    if config[0] == "gdb":
        gdb_path = config[1]
    if config[0] == "dataset":
        dataset_path = config[1]

conf_file = open(conf_persil_path, "r")
list_config = conf_file.readlines()
conf_file.close()

for line in list_config:
    line = line.replace("\n", "")
    config = []
    config = line.split(",")
    if config[0] == "persil":
        persil_path = config[1].split(";")[1]

arcpy.AddMessage("== Persiapan ==")

arcpy.AddMessage("== Backup data lama ==")

if (persil_path != persil_skor_baru) and (persil_skor_baru.strip() != ""):
    persil_backup = "PersilSkorBackup"
    persil_backup_path = os.path.join(dataset_path, persil_backup)
    if arcpy.Exists(persil_backup_path):
        arcpy.Delete_management(persil_backup_path)
    arcpy.FeatureClassToFeatureClass_conversion(persil_path, dataset_path, persil_backup)
    arcpy.Delete_management(persil_path)
    arcpy.FeatureClassToFeatureClass_conversion(persil_skor_baru, dataset_path, "Persil")

persil_untuk_prediksi = "Persil_Model"
persil_untuk_prediksi_path = os.path.join(dataset_path, persil_untuk_prediksi)

if arcpy.Exists(persil_untuk_prediksi_path):
    arcpy.Delete_management(persil_untuk_prediksi_path)

arcpy.FeatureClassToFeatureClass_conversion(persil_path, dataset_path, persil_untuk_prediksi)
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

fields = arcpy.ListFields(persil_untuk_prediksi_path)
for f in fields:
    if not (f.type == "Geometry" or f.type == "OID" or f.name == "IdBidang" or f.name == "NIB" or "shape".lower() in str(f.name).lower() or f.name in fields_dont_delete or f.name == "NILAI" or f.name=="FID"):
        arcpy.DeleteField_management(persil_untuk_prediksi_path, f.name)
        arcpy.AddMessage(f.name + " deleted")

for f in detail_fields:
    if f[1] == "Logaritmik":
        arcpy.CalculateField_management(persil_untuk_prediksi_path, f[0], "math.log(!" + f[0] + "!)", "PYTHON")
    elif f[1] == "Inverse":
        arcpy.CalculateField_management(persil_untuk_prediksi_path, f[0], "1 / !" + f[0] + "!", "PYTHON")

# field_names = [field.name for field in arcpy.ListFields(persil_untuk_prediksi_path)]
# if u'N_Prediksi' not in field_names:
#     arcpy.AddField_management(persil_untuk_prediksi_path, u'N_Prediksi', "DOUBLE")

if arcpy.Exists("Persil_Model"):
    arcpy.Delete_management("Persil_Model")

arcpy.MakeFeatureLayer_management(persil_untuk_prediksi_path, "Persil_Model")
arcpy.SetParameterAsText(1, "Persil_Model")

arcpy.AddMessage("== Proses selesai ==")
