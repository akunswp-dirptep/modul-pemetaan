import os
import arcpy

arcpy.AddMessage("== Proses dimulai ==")

grf = r'C:\SpatialStats\Outputs\ResultsGWR_CY_2.grf'
data = r'C:\SpatialStats\Outputs\ResultsGWR_CY.shp'
output = "graph"

if arcpy.Exists(output):
	arcpy.Delete_management(output)

arcpy.env.overwriteOutput = True

graph = arcpy.Graph()
graph.addSeriesLineHorizontal(data, 'FID', 'Residual', 'FID')

arcpy.MakeGraph_management(grf, graph, output)

arcpy.SetParameterAsText(0, output)

del output

arcpy.AddMessage("== Proses selesai ==")
