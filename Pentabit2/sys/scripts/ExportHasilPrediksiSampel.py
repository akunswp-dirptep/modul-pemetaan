import os
import arcpy

out_folder  = arcpy.GetParameterAsText(0)
dbf = "tabel_prediksiSampel.dbf"

ResultsGWR_CY_supp_dbf = "C:\\znt\\sys\\results\\GWR_supp.dbf"

if not arcpy.Exists(ResultsGWR_CY_supp_dbf):
    arcpy.AddMessage("== Hasil proses GWR tidak ditemukan (" + ResultsGWR_CY_supp_dbf + ") ==")
else:
    # Process: Make Table View
    ResultsGWR_CY_supp_View = "temp_table_view"
    if arcpy.Exists(ResultsGWR_CY_supp_View):
        arcpy.Delete_management(ResultsGWR_CY_supp_View)
    arcpy.MakeTableView_management(ResultsGWR_CY_supp_dbf, ResultsGWR_CY_supp_View, "", "", "OID OID VISIBLE NONE;VARNAME VARNAME VISIBLE NONE;VARIABLE VARIABLE VISIBLE NONE;DEFINITION DEFINITION VISIBLE NONE")
    arcpy.TableToTable_conversion(ResultsGWR_CY_supp_View, out_folder, dbf)

arcpy.AddMessage("== Proses selesai ==")
