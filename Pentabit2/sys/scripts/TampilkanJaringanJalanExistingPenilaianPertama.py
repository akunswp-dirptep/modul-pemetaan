import os
import arcpy

arcpy.AddMessage("== Proses dimulai ==")

in_jaringan_jalan = arcpy.GetParameterAsText(0)
field_lebar_jalan = arcpy.GetParameterAsText(2)
field_kelas_jalan = arcpy.GetParameterAsText(3)

jaringan_jalan = "Jaringan_Jalan"
dataset_path = ""

appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
persil_conf_path = os.path.join(appdata, "jalan.dat")
conf_file = open(persil_conf_path, "r")
list_config = conf_file.readlines()
conf_file.close()

for line in list_config:
    line = line.replace("\n", "")
    jalan_config = []
    jalan_config = line.split(",")
    if jalan_config[0] == "dataset":
        dataset_path = jalan_config[1]

tempdata = os.path.join(appdata, "temp")
no_sim_path = os.path.join(appdata, "SimbologiJaringanJalanUpdate.lyr")

out_shp = "Jaringan_Jalan"
out_path = os.path.join(dataset_path, out_shp)

arcpy.AddMessage("== Tambah field status_jal ==")

arcpy.AddMessage("== Pindahkan shapefile ke temp ==")

if arcpy.Exists(os.path.join(dataset_path, "TopologiJaringanJalan")):
    arcpy.Delete_management(os.path.join(dataset_path, "TopologiJaringanJalan"))

if arcpy.Exists(out_path):
    arcpy.Delete_management(out_path)

arcpy.CopyFeatures_management(in_jaringan_jalan, out_path)

list_names = [f.name for f in arcpy.ListFields(out_path)]

if 'P_Jalan' not in list_names:
    arcpy.AddField_management(out_path, "P_Jalan", "DOUBLE")
if 'lb_jln' not in list_names:
    arcpy.AddField_management(out_path, "lb_jln", "DOUBLE")
if 'kls_jln' not in list_names:
    arcpy.AddField_management(out_path, "kls_jln", "TEXT")
if 's_kls_jln' not in list_names:
    arcpy.AddField_management(out_path, "s_kls_jln", "DOUBLE")

arcpy.CalculateField_management(out_path, "P_Jalan", "!shape.length!", "PYTHON")

if field_lebar_jalan != 'lb_jln' and field_lebar_jalan.strip() != "":
    arcpy.CalculateField_management(out_path, "lb_jln", "!" + field_lebar_jalan + "!", "PYTHON")
if field_kelas_jalan != 'kls_jln' and field_kelas_jalan.strip() != "":
    exp = "get(!" + field_kelas_jalan + "!)"
    code_block = """def get(b):
        if b == 'Arteri Primer':
            return 'Arteri Primer'
        elif b == 'Arteri Sekunder':
            return 'Arteri Sekunder'
        elif b == 'Kolektor Primer':
            return 'Kolektor Primer'
        elif b == 'Kolektor Sekunder':
            return 'Kolektor Sekunder'
        elif b == 'Lokal Primer':
            return 'Lokal Primer'
        elif b == 'Lokal Sekunder':
            return 'Lokal Sekunder'
        elif b == 'Lokal Setapak':
            return 'Lokal Setapak'
        else:
            return 'Lokal Setapak'"""
    arcpy.CalculateField_management(out_path, "kls_jln", exp, "PYTHON", code_block)

exp = "get(!kls_jln!)"
code_block = """
def get(b):
    if b == 'Arteri Primer':
        return 7
    elif b == 'Arteri Sekunder':
        return 6
    elif b == 'Kolektor Primer':
        return 5
    elif b == 'Kolektor Sekunder':
        return 4
    elif b == 'Lokal Primer':
        return 3
    elif b == 'Lokal Sekunder':
        return 2
    elif b == 'Lokal Setapak':
        return 1
    else:
        return 1"""
arcpy.CalculateField_management(out_path, "s_kls_jln", exp, "PYTHON", code_block)

if arcpy.Exists(jaringan_jalan):
    arcpy.Delete_management(jaringan_jalan)

arcpy.MakeFeatureLayer_management(out_path, jaringan_jalan)

arcpy.SetParameterAsText(1, jaringan_jalan)

arcpy.AddMessage("== Proses selesai ==")
