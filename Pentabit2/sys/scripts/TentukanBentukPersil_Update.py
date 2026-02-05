import os
import arcpy

arcpy.env.overwriteOutput = True

persil = arcpy.GetParameterAsText(0)
arcpy.AddMessage("== Proses dimulai ==")

arcpy.AddMessage("== Simplifikasi Polygon ==")
persil_simplified = arcpy.cartography.SimplifyPolygon(persil,'persil_simplified', 'POINT_REMOVE',1).getOutput(0)
persil_vertices = arcpy.management.FeatureVerticesToPoints(persil_simplified, 'persil_vertices', 'ALL').getOutput(0)
line_vertex = arcpy.management.PointsToLine(persil_vertices,'line_vertex', 'ORIG_FID').getOutput(0)
split_line = arcpy.management.SplitLine(line_vertex,'split_line').getOutput(0)


arcpy.AddField_management(split_line, 'Start', "TEXT")
arcpy.AddField_management(split_line, 'End', "TEXT")

with arcpy.da.UpdateCursor(split_line,['SHAPE@', 'ORIG_FID','Start', 'End']) as cur:
    for row in cur:
        row[2] = str(row[0].firstPoint.X) + "_" + str(row[0].firstPoint.Y)
        row[3] = str(row[0].lastPoint.X) + "_" + str(row[0].lastPoint.Y)
        if row[1] == None:
            row[1] = 0
        cur.updateRow(row)

arcpy.management.AddGeometryAttributes(split_line, 'LINE_BEARING')

arcpy.management.AddField(persil_vertices,'XY', 'TEXT')
arcpy.management.AddField(persil_vertices,'Start', 'TEXT')
arcpy.management.AddField(persil_vertices,'End', 'TEXT')
arcpy.management.AddField(persil_vertices,'Angle', 'DOUBLE')

cur = arcpy.da.UpdateCursor(persil_vertices, ['SHAPE@', 'XY', 'Start', 'End'])

for row in cur:
    shapeValue = row[0][0]
    row[1] = str(shapeValue.X) + '_' + str(shapeValue.Y)
    cur.updateRow(row)

arcpy.management.JoinField(persil_vertices, "XY", split_line, "Start", "BEARING")
arcpy.management.JoinField(persil_vertices, "XY", split_line, "End", "BEARING")

def internalAngle (fr,to):
 if fr == None or to == None: return 0
 external=180-fr+to
 if external<0:external+=360
 if external>360:external-=360
 return external

with arcpy.da.UpdateCursor(persil_vertices,['Angle', 'BEARING','BEARING_1']) as cur:
    for row in cur:
        row[0] = internalAngle(row[1],row[2])
        cur.updateRow(row)



arcpy.AddMessage("== Menentukan Bentuk ==")


arcpy.AddMessage("== Proses Selesai ==")