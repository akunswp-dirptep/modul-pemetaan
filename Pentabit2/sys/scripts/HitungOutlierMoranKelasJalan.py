import os
import arcpy

arcpy.AddMessage("== Proses dimulai ==")

# get parameter
jaringanjalan_path = arcpy.GetParameterAsText(0)
jaringanjalan = "JaringanJalan"

appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_jalan_path = os.path.join(appdata, "jalan.dat")
conf_file = open(conf_jalan_path, "r")
list_config = conf_file.readlines()
conf_file.close()

list_err = []
dataset_path = ""

for line in list_config:
    line = line.replace("\n", "")
    jalan_config = []
    jalan_config = line.split(",")
    if jalan_config[0] == "dataset":
        dataset_path = jalan_config[1]
    if not jaringanjalan_path:
        if jalan_config[0] == "jaringanjalan":
            jaringanjalan = jalan_config[1].split(";")[0]
            jaringanjalan_path = jalan_config[1].split(";")[1]

temp_gdb_path = os.path.join(appdata, "temporary.gdb")

field_names = [field.name for field in arcpy.ListFields(jaringanjalan_path)]

if 'S_KlsJln' not in field_names or 'L_Jalan' not in field_names:
    arcpy.AddMessage("== Proses dihentikan, tidak ada field S_KlsJln atau L_Jalan. ==")
else:
    for i in range(1, 6):
        out_name = "outlier_klsjln_" + str(int(i))
        # out_path = os.path.join(output_folder, out_name + ".shp")
        out_path = os.path.join(temp_gdb_path, out_name)
        arcpy.AddMessage("== Anselin Local Moran's I: " + out_path + " ==")
        if arcpy.Exists(out_path):
            arcpy.Delete_management(out_path)
        temp_lyr = "temp_lyr"
        if arcpy.Exists(temp_lyr):
            arcpy.Delete_management(temp_lyr)
        arcpy.MakeFeatureLayer_management(jaringanjalan_path, temp_lyr, "S_KlsJln = " + str(i))
        row_count = arcpy.GetCount_management(temp_lyr)[0]
        arcpy.AddMessage("jumlah record:" + str(row_count))
        if int(row_count) > 2:
            try:
                result = arcpy.ClustersOutliers_stats(temp_lyr, "L_Jalan", out_path, "INVERSE_DISTANCE_SQUARED", "EUCLIDEAN_DISTANCE", "NONE")
                # arcpy.AddJoin_management(temp_lyr, "FID", out_name, "SOURCE_ID")
                # arcpy.CalculateField_management(temp_lyr, "oLMiIndex", "!" + out_name + ".LMiIndex!", "PYTHON")
                # arcpy.CalculateField_management(temp_lyr, "oLMiZScore", "!" + out_name + ".LMiZScore!", "PYTHON")
                # arcpy.CalculateField_management(temp_lyr, "oLMiPValue", "!" + out_name + ".LMiPValue!", "PYTHON")
                # arcpy.CalculateField_management(temp_lyr, "oCOType", "!" + out_name + ".COType!", "PYTHON")
                # arcpy.RemoveJoin_management(temp_lyr, out_name)
            except arcpy.ExecuteError:
                # arcpy.AddMessage(arcpy.GetMessage())
                arcpy.AddMessage("Error: " + out_name)
                list_err.append(out_name + "," + arcpy.GetMessages())
            # if arcpy.Exists(out_name + "_tbl"):
            #     arcpy.Delete_management(out_name + "_tbl")
            # arcpy.MakeTableView_management(out_path, out_name + "_tbl")
        else:
            arcpy.AddMessage(
                "Kelas Jalan " + str(i) + " tidak diproses. Jumlah record " + str(row_count) + ", kurang dari 3.")
        if arcpy.Exists(temp_lyr):
            arcpy.Delete_management(temp_lyr)
        arcpy.AddMessage("== Ok ==")

        # arcpy.AddMessage(list_err)

    err_outlier_path = os.path.join(appdata, "err_outlier.err")
    conf_file = open(err_outlier_path, "w")
    conf_file.write("\n".join(list_err) + "\n")
    conf_file.close()

arcpy.AddMessage("== Proses selesai ==")
