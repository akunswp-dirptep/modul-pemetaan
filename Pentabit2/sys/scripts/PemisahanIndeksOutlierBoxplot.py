import arcpy, os, numpy

arcpy.env.outputZFlag = "Disabled"
arcpy.env.outputMFlag = "Disabled"

# Read configuration from file
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_path = os.path.join(appdata, "persil.dat")

conf_file = open(conf_path, "r")
list_config = conf_file.readlines()
conf_file.close()

# Initialize dataset paths
dataset_path = ""
persil = ""
persil_path = ""

for line in list_config:
    line = line.replace("\n", "")
    persil_config = line.split(",")
    if persil_config[0] == "dataset":
        dataset_path = persil_config[1]
    if persil_config[0] == "persil":
        persil = persil_config[1].split(";")[0]
        persil_path = persil_config[1].split(";")[1]

# Path to sample points
titik_indeks = os.path.join(dataset_path, "titik_indeks")

# Function to calculate quartiles and IQR using numpy
def calculate_boxplot_values(data_list):
    Q1 = numpy.percentile(data_list, 25)
    median = numpy.percentile(data_list, 50)
    Q3 = numpy.percentile(data_list, 75)
    IQR = Q3 - Q1
    # Calculate lower and upper bounds for outliers using the 1.5 * IQR rule
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    return Q1, median, Q3, lower_bound, upper_bound

# Prepare the feature class for outlier labeling
fields = [field.name for field in arcpy.ListFields(titik_indeks)]
if 'outlier' not in fields:
    arcpy.AddField_management(titik_indeks, "outlier", "TEXT")

# Get list of unique zonasi (zones)
listzonasi = []
zonasi_dict = {}  # Dictionary to store s_zonasi as key and nama_zonasi as value
rows = arcpy.SearchCursor(titik_indeks)
for row in rows:
    nama_zonasi = row.getValue("zonasi")
    s_zonasi = int(row.getValue("s_zonasi"))
    listzonasi.append(s_zonasi)
    zonasi_dict[s_zonasi] = nama_zonasi  # Store the relationship between s_zonasi and nama_zonasi
del row, rows

# Remove duplicate zonasi values
listzonasi = list(dict.fromkeys(listzonasi))

# Identify outliers using the boxplot method
for i in listzonasi:
    # Get the corresponding name of the zonasi from the dictionary
    nama_zonasi = zonasi_dict[i]
        
    # Extract indeks values for the current zonasi
    data = [row[0] for row in arcpy.da.SearchCursor(titik_indeks, 'indeks', "s_zonasi = " + str(i))]

    # Check if there are fewer than 10 sample points in the current zonasi
    if len(data) < 10:
        arcpy.DeleteField_management(titik_indeks, 'outlier')
        arcpy.AddMessage("Field 'outlier' dihapus karena sampel kurang dari 10 untuk {}".format(nama_zonasi))
        error_message = 'Titik Sampel kurang dari 10 untuk zona {}'.format(nama_zonasi)
        arcpy.AddMessage(error_message)
        arcpy.AddError(error_message)
        
        # Stop the script
        sys.exit(1)
    else:
        # Sort the indeks data for the current zonasi
        data_sorted = sorted(data)
        
        # Calculate Q1, Median, Q3, and outlier bounds
        Q1, median, Q3, lower_bound, upper_bound = calculate_boxplot_values(data_sorted)
        batas = [Q1, median, Q3]
        arcpy.AddMessage("(Q1, median, Q3) for zonasi {}: {}".format(nama_zonasi, batas))
        arcpy.AddMessage("Lower Bound: {}, Upper Bound: {} for zonasi {}".format(lower_bound, upper_bound, nama_zonasi))

        # Update the outliers based on the 1.5 * IQR rule
        outlier = arcpy.UpdateCursor(titik_indeks, "s_zonasi = " + str(i) + 
                                     " and (indeks < " + str(lower_bound) + " or indeks > " + str(upper_bound) + ")")
        for row in outlier:
            row.setValue("outlier", "Indeks Outlier")
            outlier.updateRow(row)
        del outlier

#Uncomment (Alt + 4) if the sample is less than 10.
##if len(listzonasi) > 0:
##    for i in listzonasi:
##        # Get the corresponding name of the zonasi from the dictionary
##        nama_zonasi = zonasi_dict[i]
##        
##        data = [row[0] for row in arcpy.da.SearchCursor(titik_indeks, 'indeks', "s_zonasi = " + str(i))]
##
##        if len(data) >= 3:  # Ensure enough data points for statistical calculation
##            # Sort the indeks data for the current zonasi
##            data_sorted = sorted(data)
##            
##            # Calculate Q1, Median, Q3, and outlier bounds
##            Q1, median, Q3, lower_bound, upper_bound = calculate_boxplot_values(data_sorted)
##            batas = [Q1, median, Q3]
##            arcpy.AddMessage("(Q1, median, Q3) for zonasi {}: {}".format(nama_zonasi, batas))
##            arcpy.AddMessage("Lower Bound: {}, Upper Bound: {} for zonasi {}".format(lower_bound, upper_bound, nama_zonasi))
##
##            # Update the outliers based on the 1.5 * IQR rule
##            outlier = arcpy.UpdateCursor(titik_indeks, "s_zonasi = " + str(i) + 
##                                         " and (indeks < " + str(lower_bound) + " or indeks > " + str(upper_bound) + ")")
##            for row in outlier:
##                row.setValue("outlier", "Indeks Outlier")
##                outlier.updateRow(row)
##            del outlier

# Apply symbology (if applicable)
arcpy.MakeFeatureLayer_management(titik_indeks, "Titik_Indeks")
arcpy.ApplySymbologyFromLayer_management("Titik_Indeks", os.path.join(appdata, "Simbologi_Titik_Indeks_Outlier.lyrx"))
arcpy.SetParameter(0, "Titik_Indeks")
