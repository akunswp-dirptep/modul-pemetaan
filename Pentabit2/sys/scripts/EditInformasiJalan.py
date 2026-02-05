import arcpy
import os

arcpy.AddMessage("== Proses dimulai ==")

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

status = arcpy.GetParameterAsText(0)
kelas_jalan = arcpy.GetParameterAsText(1)
s_jalan = arcpy.GetParameterAsText(2)
lebar_jalan = arcpy.GetParameterAsText(3)

status_per = "Indikator_Akhir"

sampel_fields = [f.name for f in arcpy.ListFields(status_per)]

if "status_per" not in sampel_fields:
    arcpy.AddError("Field " + "status_per" + " tidak ditemukan.")
    raise arcpy.ExecuteError

rows = arcpy.UpdateCursor(status_per)

for row in rows:
    row.setValue("status_per", val.lower())
    rows.updateRow(row)

del row
del rows

arcpy.RefreshTOC()
arcpy.RefreshActiveView()
