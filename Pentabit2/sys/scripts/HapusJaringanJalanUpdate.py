import arcpy
import os

arcpy.AddMessage("== Proses dimulai ==")

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

jaringanjalan = "Jaringan_Jalan"
jaringanjalan_temp = "Jaringan_Jalan_Temp"

ada_seleksi = 0
ada_seleksi = len(arcpy.Describe(jaringanjalan).FIDSet)

if ada_seleksi > 0:
    rows = arcpy.UpdateCursor(jaringanjalan)
    for row in rows:
        rows.deleteRow(row)

    # del row
    del row, rows
    #edit 30/9/22
    arcpy.management.MakeFeatureLayer(jaringanjalan, jaringanjalan_temp)
    arcpy.DeleteFeatures_management(jaringanjalan_temp)



# arcpy.RefreshTOC()
# arcpy.RefreshActiveView()
