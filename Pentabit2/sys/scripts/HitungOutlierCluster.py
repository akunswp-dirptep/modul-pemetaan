import os
import arcpy

in_feature = arcpy.GetParameterAsText(0)
in_field = arcpy.GetParameterAsText(1)
out_feature = arcpy.GetParameterAsText(2)
nama_file = arcpy.GetParameterAsText(3)

arcpy.AddMessage("== Proses mulai ==")

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

clust_diss_path = os.path.join(appdata, "temporary.gdb", "clust_kv_diss")

arcpy.Dissolve_management(in_feature, clust_diss_path, ["No_Cluster"], [["STD", in_field], ["MEAN", in_field]])

arcpy.AddMessage("== Proses selesai ==")
