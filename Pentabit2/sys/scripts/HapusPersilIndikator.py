import arcpy
import os

arcpy.AddMessage("== Proses dimulai ==")

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

peta_indikator = "Indikator_Perubahan_Persil"
peta_indikator_temp = "Indikator_Perubahan_Persil_temp"

ada_seleksi = 0
ada_seleksi = len(arcpy.Describe(peta_indikator).FIDSet)

if ada_seleksi > 0:
    rows = arcpy.UpdateCursor(peta_indikator)
    for row in rows:
        rows.deleteRow(row)
    del row, rows

    arcpy.management.MakeFeatureLayer(peta_indikator, peta_indikator_temp)
    arcpy.DeleteFeatures_management(peta_indikator_temp)

# arcpy.RefreshTOC()
# arcpy.RefreshActiveView()
