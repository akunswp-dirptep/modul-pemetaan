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
sampel = "Titik_Sampel_Update"
sampel_path = os.path.join(dataset_path, sampel)

fields = [field.name for field in arcpy.ListFields(persil_path)]
if 'MEAN_nilai' in fields:
    arcpy.DeleteField_management(persil_path, ["MEAN_nilai", "STD_Nilai", "PTDDEV" ])
arcpy.AddField_management(persil_path, "MEAN_nilai", "DOUBLE")
arcpy.AddField_management(persil_path, "STD_nilai", "DOUBLE")
arcpy.AddField_management(persil_path, "PTDDEV", "DOUBLE")

arcpy.Identity_analysis(sampel_path, persil_path, "identity")

listcluster = []
for rows in arcpy.SearchCursor("identity", where_clause = "perubahan = 'mengelompok'"):
    listcluster.append(rows.clusternew)
del rows

# arcpy.AddMessage(list(dict.fromkeys(listcluster)))
c = 0 
for i in list(dict.fromkeys(listcluster)):
    c = c + 1
    cluster_i = "cluster_{}".format(c)
    dissolve_i = "dissolve_{}".format(c)
    arcpy.MakeFeatureLayer_management("identity", cluster_i, "clusternew = " + str(i))
    arcpy.AddField_management(cluster_i, "MEAN_nilai", "DOUBLE")
    arcpy.AddField_management(cluster_i, "STD_nilai", "DOUBLE")

    statistic_field = [["Nilai", "SUM"], ["Nilai", "MEAN"], ["Nilai", "MIN"], ["Nilai", "MAX"], ["Nilai", "STD"], ["Nilai", "COUNT"], ["Nilai", "RANGE"]]
    arcpy.Dissolve_management(cluster_i, dissolve_i, ["clusternew"], statistic_field,"MULTI_PART","DISSOLVE_LINES")

    with arcpy.da.UpdateCursor(dissolve_i, 'clusternew') as cursor:
        for row in cursor:
            if row[0] is None:
                cursor.deleteRow()
            elif row[0] == 0:
                cursor.deleteRow()

    arcpy.Intersect_analysis([persil_path, sampel_path], "temp", "ALL")
    arcpy.SelectLayerByAttribute_management("temp", "NEW_SELECTION", "clusternew = " + str(i))
    # arcpy.CopyFeatures_management("temp", "sampel_join")
    for row in arcpy.SearchCursor("temp"): 
        rowsa = arcpy.UpdateCursor (persil_path, "IdBidang = " + str(row.FID_Persil_Baru))
        for rowa in rowsa:
            rowa.setValue ("PREDICTED", row.getValue("nilai"))
            rowsa.updateRow(rowa)

    for row in arcpy.SearchCursor(dissolve_i): 
        rowsa = arcpy.UpdateCursor (persil_path, "clusternew = " + str(row.clusternew))
        for rowa in rowsa:
            if rowa.getValue("PREDICTED"):
                rowa.setValue ("MEAN_nilai", row.getValue("MEAN_nilai"))
                rowa.setValue ("STD_nilai", row.getValue("STD_nilai"))
            rowsa.updateRow(rowa)
    del row

    codeblock = """def doSomething(a, b):
        if a or b:
            return round((a/b)*100, 2)
        else:
            return None
        """

    arcpy.CalculateField_management(persil_path, "PTDDEV", "doSomething(!STD_Nilai!, !MEAN_Nilai!)", "PYTHON3", codeblock)

with arcpy.da.UpdateCursor(persil_path, ["perubahan", "PREDICTED"]) as cursor:
    for row in cursor:
        if row[0] != "individual":
            row[1] = None
        cursor.updateRow(row)

arcpy.MakeFeatureLayer_management(persil_path, "Persil_Baru")
arcpy.ApplySymbologyFromLayer_management("Persil_Baru", os.path.join(appdata, "Simbologi_Outlier_Persil_Baru.lyrx"))
arcpy.SetParameter(0, "Persil_Baru")


aprx = arcpy.mp.ArcGISProject("CURRENT")
map = aprx.activeMap
layers = map.listLayers()
for layer in layers:
    if layer.name == "Titik_Sampel_Update":
        layer.visible = True
