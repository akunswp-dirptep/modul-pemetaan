import os
import arcpy
# from xlwt import Workbook, easyxf
# import dbfpy.dbf

output_folder = arcpy.GetParameterAsText(0)

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

dbffile = os.path.join(appdata, "results", "Source_Sampel.dbf")
shpfile = os.path.join(appdata, "results", "Source_Sampel.shp")

# dbf = dbfpy.dbf.Dbf(dbffile, readOnly=True)
# header_style = easyxf('font: name Arial, bold True, height 200;')
# book = Workbook()
# sheet1 = book.add_sheet("Sheet 1")
#
# for (i, name) in enumerate(dbf.fieldNames):
#     sheet1.write(0, i, name, header_style)
#
# for (i, thecol) in enumerate(dbf.fieldDefs):
#     name, thetype, thelen, thedec = str(thecol).split()
#     colwidth = max(len(name), int(thelen))
#     sheet1.col(i).width = colwidth * 310
#
# for row in range(1, len(dbf)):
#     for col in range(len(dbf.fieldNames)):
#         sheet1.row(row).write(col, dbf[row][col])
#
# out = os.path.join(output_folder, "tabel_prediksi_sampel.xls")
#
# if arcpy.Exists(out):
#     arcpy.Delete_management(out)
#
# # xls
# arcpy.AddMessage(out)
# book.save(out)

if arcpy.Exists("temp_tableview"):
    arcpy.Delete_management("temp_tableview")
if arcpy.Exists(os.path.join(output_folder, "tabel_sampel_prediksi.dbf")):
    arcpy.Delete_management(os.path.join(output_folder, "tabel_sampel_prediksi.dbf"))

arcpy.MakeTableView_management(dbffile, "temp_tableview")
arcpy.CopyRows_management("temp_tableview", os.path.join(output_folder, "tabel_sampel_prediksi.dbf"))

# shp
out = os.path.join(output_folder, "sampel_prediksi.shp")

if arcpy.Exists(out):
    arcpy.Delete_management(out)

arcpy.AddMessage(out)
arcpy.Copy_management(shpfile, out)
