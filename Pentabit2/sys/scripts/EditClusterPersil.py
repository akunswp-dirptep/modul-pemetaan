import os
import arcpy

arcpy.AddMessage("== Proses dimulai ==")

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

hasil_cluster = "Hasil_Cluster"
no_cluster = float(arcpy.GetParameterAsText(0))
zonasi = float(arcpy.GetParameterAsText(1))

rows = arcpy.UpdateCursor(hasil_cluster)

for row in rows:
    row.No_Cluster = no_cluster
    row.S_Zonasi = zonasi
    rows.updateRow(row)

del row
del rows

arcpy.RefreshTOC()
arcpy.RefreshActiveView()
