import arcpy, os

appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

persil = "Persil_Baru"
cluster_update = arcpy.GetParameterAsText(0)

ada_seleksi = 0
ada_seleksi = len(arcpy.Describe(persil).FIDSet)

if ada_seleksi <= 0:
    sys.exit()

fields = arcpy.ListFields(persil,"clusternew","SHORT")

rows = arcpy.UpdateCursor(persil)
for row in rows:
    row.setValue('status_per', 'update')
    row.setValue('clusternew', cluster_update)
    row.setValue('perubahan', 'mengelompok')
    rows.updateRow(row)   
del row, rows

arcpy.CalculateField_management(persil, "clusternew" ,cluster_update, "PYTHON3", "")
arcpy.AddMessage("== Proses selesai ==")
