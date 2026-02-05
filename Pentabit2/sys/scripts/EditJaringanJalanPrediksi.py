import arcpy
import os

arcpy.AddMessage("== Proses dimulai ==")

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

jaringan_jalan = "Jaringan_Jalan"
kls_jln = arcpy.GetParameterAsText(0)
lb_jalan = arcpy.GetParameter(1)
s_kls_jln = 1

if kls_jln == "Arteri Primer":
    s_kls_jln = 7
elif kls_jln == "Arteri Sekunder":
    s_kls_jln = 6
elif kls_jln == "Kolektor Primer":
    s_kls_jln = 5
elif kls_jln == "Kolektor Sekunder":
    s_kls_jln = 4
elif kls_jln == "Lokal Primer":
    s_kls_jln = 3
elif kls_jln == "Lokal Sekunder":
    s_kls_jln = 2
elif kls_jln == "Lokal Setapak":
    s_kls_jln = 1
else:
    s_kls_jln = 1

sampel_fields = [f.name for f in arcpy.ListFields(jaringan_jalan)]

if "kls_jln" not in sampel_fields or "lb_jln" not in sampel_fields or "s_kls_jln" not in sampel_fields:
    arcpy.AddError("Field " + "kls_jln, lb_jln, s_kls_jln" + " tidak ditemukan.")
    raise arcpy.ExecuteError

ada_seleksi = 0
ada_seleksi = len(arcpy.Describe(jaringan_jalan).FIDSet)

if ada_seleksi > 0:
    rows = arcpy.UpdateCursor(jaringan_jalan)
    for row in rows:
        row.setValue("kls_jln", kls_jln)
        row.setValue("lb_jln", lb_jalan)
        row.setValue("s_kls_jln", s_kls_jln)
        rows.updateRow(row)
    del row
    del rows

#update 19/10/2021
#arcpy.RefreshTOC()
#arcpy.RefreshActiveView()

