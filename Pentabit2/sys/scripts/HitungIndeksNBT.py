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
sampel_path = os.path.join(dataset_path, "Titik_Sampel_Update")
indeks_path = os.path.join(dataset_path, "Titik_Indeks")

arcpy.analysis.Identity(sampel_path, persil_path, "hi")
arcpy.management.AddField("hi", "indeks", "DOUBLE")

code_block = """
def doSomething(a,b):
    if a or b:
        return round(100 * (a/b), 2)
    else:
        return None
    """

arcpy.management.CalculateField("hi", "indeks", "doSomething(!nilai!,!NILAI_LAMA!)", "PYTHON3", code_block)
arcpy.management.Sort("hi", indeks_path, [["s_zonasi", "ASCENDING"], ["indeks", "ASCENDING"]])

with arcpy.da.UpdateCursor(indeks_path, "clusternew") as cursor:
    for row in cursor:
        if row[0]:
            cursor.deleteRow()
del row, cursor

arcpy.management.DeleteField(indeks_path,["FID_Titik_Sampel_Update","FID_Persil_Baru","NIB","ls_asal","ls_tnh","lb_dpn","bentuk","s_bentuk","letak","s_letak","s_kls_jln","lb_jln","kls_jln","jk_atrp","jk_atrs","jk_kolp","jk_kols","Shape_Le_1","tsk_st","SimLbDpn","sim_l_dpn","CBD","Banjir","ls_tnh_i","lb_dpn_i","perubahan","MEAN_nilai","STD_nilai","PTDDEV", "indeks_rata"])

arcpy.MakeFeatureLayer_management(indeks_path, "Titik_Indeks")
arcpy.MakeFeatureLayer_management(sampel_path, "Titik_Sampel_Update")
arcpy.ApplySymbologyFromLayer_management("Titik_Indeks", os.path.join(appdata, "Simbologi_Titik_Indeks.lyrx"))
arcpy.SetParameter(0, "Titik_Indeks")
arcpy.SetParameter(1, "Titik_Sampel_Update")

##aprx = arcpy.mp.ArcGISProject("CURRENT")
##map = aprx.activeMap
##layers = map.listLayers()
##for layer in layers:
##    if layer.name == "Titik_Sampel_Update":
##        layer.visible = False
