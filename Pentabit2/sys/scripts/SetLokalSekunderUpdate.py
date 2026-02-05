import sys, os
import arcpy

arcpy.AddMessage("== Proses dimulai ==")

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

# dataset_path = ""
jaringanjalan = "Jaringan_Jalan"
# jaringanjalan_path = ""
# simbologi_path = ""

field_names = [field.name for field in arcpy.ListFields(jaringanjalan)]
if 'kls_jln' not in field_names:
    arcpy.AddField_management(jaringanjalan, 'kls_jln', 'DOUBLE')
if 's_kls_jln' not in field_names:
    arcpy.AddField_management(jaringanjalan, 's_kls_jln', 'DOUBLE')

rows = arcpy.UpdateCursor(jaringanjalan)

for row in rows:
    row.kls_jln = "Lokal Sekunder"
    row.status_jal = "Update"
    row.s_kls_jln = 2
    rows.updateRow(row)

del row
del rows

#edit 28/9/22
arcpy.CalculateField_management(jaringanjalan, "s_kls_jln" ,"2", "PYTHON3", "")
arcpy.AddMessage("== Proses selesai ==")