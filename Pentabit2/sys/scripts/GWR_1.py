import arcpy

# Check out any necessary licenses
arcpy.CheckOutExtension("GeoStats")

# Script arguments
Input_features = arcpy.GetParameterAsText(0)

Dependent_variable = arcpy.GetParameterAsText(1)

Explanatory_variable_s_ = arcpy.GetParameterAsText(2)

Kernel_type = arcpy.GetParameterAsText(3)
if Kernel_type == '#' or not Kernel_type:
    Kernel_type = "FIXED" # provide a default value if unspecified

Bandwidth_method = arcpy.GetParameterAsText(4)
if Bandwidth_method == '#' or not Bandwidth_method:
    Bandwidth_method = "AICc" # provide a default value if unspecified

Distance = arcpy.GetParameterAsText(5)

Number_of_neighbors = arcpy.GetParameterAsText(6)
if Number_of_neighbors == '#' or not Number_of_neighbors:
    Number_of_neighbors = "30" # provide a default value if unspecified

Weights = arcpy.GetParameterAsText(7)

Coefficient_raster_workspace = arcpy.GetParameterAsText(8)

Output_cell_size = arcpy.GetParameterAsText(9)

Prediction_locations = arcpy.GetParameterAsText(10)

Prediction_explanatory_variable_s_ = arcpy.GetParameterAsText(11)

# Local variables:
GWR_shp = Input_features
Output_prediction_feature_class = Input_features
Output_table = Input_features
Output_regression_rasters = Input_features

# Process: Geographically Weighted Regression
arcpy.GeographicallyWeightedRegression_stats(Input_features, Dependent_variable, Explanatory_variable_s_, GWR_shp, Kernel_type, Bandwidth_method, Distance, Number_of_neighbors, Weights, Coefficient_raster_workspace, Output_cell_size, Prediction_locations, Prediction_explanatory_variable_s_, Output_prediction_feature_class)

