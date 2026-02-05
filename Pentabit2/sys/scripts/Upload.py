import arcpy, os, zipfile, shutil, requests
from os.path import basename

# Define path for temporary file storage
path = os.path.join('C:\\PenilaianTanah\\Pentabit2\\sys', 'Temp_upload', "temp_shapefile")

def main_upload(project_id, username, menu, tahapan, in_feature, tahun, kategori, feature_class):
    zipname = None
    if len(tahun) == 4:  # Ensure the year format is correct
        arcpy.AddMessage('========== Preparing Temp Folder ==========')
        
        # Attempt to create the temporary directory
        try:
            if os.path.exists(path):
                shutil.rmtree(path)
            os.makedirs(path)
        except Exception as e:
            arcpy.AddError(f"Error creating temporary directory: {str(e)}")
            return

        temp_shapefile_folder = os.path.join(path, "temp_shapefile_output")
        try:
            os.makedirs(temp_shapefile_folder, exist_ok=True)
        except Exception as e:
            arcpy.AddError(f"Error creating shapefile output folder: {str(e)}")
            return

        # Attempt to export the feature class to a shapefile
        try:
            arcpy.AddMessage(f"Exporting feature class to shapefile: {feature_class}")
            arcpy.FeatureClassToShapefile_conversion([feature_class], temp_shapefile_folder)
        except Exception as e:
            arcpy.AddError(f"Error exporting feature class to shapefile: {str(e)}")
            return

        # Collect shapefile components
        shapefile_base = os.path.join(temp_shapefile_folder, os.path.basename(feature_class))
        extensions = [".shp", ".shx", ".dbf", ".prj", ".cpg", ".shp.xml", ".sbn", ".sbx"]
        shapefile_components = [shapefile_base + ext for ext in extensions if os.path.exists(shapefile_base + ext)]

        if not shapefile_components:
            arcpy.AddError("Shapefile components not found!")
            return

        # Attempt to zip the shapefile
        try:
            zipname = os.path.join(path, in_feature + ".zip")
            with zipfile.ZipFile(zipname, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file in shapefile_components:
                    zipf.write(file, basename(file))
                    arcpy.AddMessage(f"Zipped file: {basename(file)}")
            arcpy.AddMessage(f"Shapefile zipped at: {zipname}")
        except Exception as e:
            arcpy.AddError(f"Error creating zip file: {str(e)}")
            return

        # Attempt to upload the zip file
        try:
            arcpy.AddMessage('========== Uploading Zip File ==========')
            url = "https://sipenta.atrbpn.go.id/tatausaha/apis/upload"
            headers = {"Content-Type": "multipart/form-data"}
            with open(zipname, 'rb') as f:
                files = {'file': (in_feature + '.zip', f)}
                response = requests.post(url, data={'nomor_berkas': project_id, 'nik': username, 'param': menu, 'step': tahapan}, files=files)

                # Check if response indicates success or failure
                if '"error":false' in response.text:
                    # Extract and display the success message
                    start = response.text.find('"message":"') + len('"message":"')
                    end = response.text.find('"', start)
                    message = response.text[start:end]
                    arcpy.AddMessage(f"Upload successful: {message}")
                else:
                    # Extract and display the error message
                    start = response.text.find('"message":"') + len('"message":"')
                    end = response.text.find('"', start)
                    message = response.text[start:end]
                    arcpy.AddError(f"Upload failed: {message}")
##                    arcpy.AddMessage(f"Raw API Response: {response.text}")
        except requests.RequestException as e:
            arcpy.AddError(f"Error during file upload: {str(e)}")
    else:
        arcpy.AddError("Invalid year format!")

#========== START - Function baru untuk upload SHP diluar GDB ==========

def main_upload_shapefile(project_id, username, menu, tahapan, in_feature, tahun, kategori, shapefile_path):
    zipname = None
    if len(tahun) == 4:  # Ensure the year format is correct
        arcpy.AddMessage('========== Preparing Temp Folder ==========')
        
        # Attempt to create the temporary directory
        try:
            if os.path.exists(path):
                shutil.rmtree(path)
            os.makedirs(path)
        except Exception as e:
            arcpy.AddError(f"Error creating temporary directory: {str(e)}")
            return

        # Collect shapefile components
        shapefile_base = os.path.splitext(shapefile_path)[0]
        extensions = [".shp", ".shx", ".dbf", ".prj", ".cpg", ".shp.xml", ".sbn", ".sbx"]
        shapefile_components = [shapefile_base + ext for ext in extensions if os.path.exists(shapefile_base + ext)]

        if not shapefile_components:
            arcpy.AddError("Shapefile components not found!")
            return

        # Attempt to zip the shapefile
        try:
            zipname = os.path.join(path, in_feature + ".zip")
            with zipfile.ZipFile(zipname, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file in shapefile_components:
                    zipf.write(file, basename(file))
                    arcpy.AddMessage(f"Zipped file: {basename(file)}")
            arcpy.AddMessage(f"Shapefile zipped at: {zipname}")
        except Exception as e:
            arcpy.AddError(f"Error creating zip file: {str(e)}")
            return

        # Attempt to upload the zip file
        try:
            arcpy.AddMessage('========== Uploading Zip File ==========')
            url = "https://sipenta.atrbpn.go.id/tatausaha/apis/upload"
            headers = {"Content-Type": "multipart/form-data"}
            with open(zipname, 'rb') as f:
                files = {'file': (in_feature + '.zip', f)}
                response = requests.post(url, data={'nomor_berkas': project_id, 'nik': username, 'param': menu, 'step': tahapan}, files=files)

                # Check if response indicates success or failure
                if '"error":false' in response.text:
                    # Extract and display the success message
                    start = response.text.find('"message":"') + len('"message":"')
                    end = response.text.find('"', start)
                    message = response.text[start:end]
                    arcpy.AddMessage(f"Upload successful: {message}")
                else:
                    # Extract and display the error message
                    start = response.text.find('"message":"') + len('"message":"')
                    end = response.text.find('"', start)
                    message = response.text[start:end]
                    arcpy.AddError(f"Upload failed: {message}")
        except requests.RequestException as e:
            arcpy.AddError(f"Error during file upload: {str(e)}")
    else:
        arcpy.AddError("Invalid year format!")

#========== END - Function baru untuk upload SHP diluar GDB ============

def main_loop(project_id, username, menu, tahapan, in_feature, tahun, kategori, feature_class):
    arcpy.AddMessage('========== Starting Main Loop ==========')    
    # In this case, there is no splitting into chunks since shapefiles are handled in one go
    main_upload(project_id, username, menu, tahapan, in_feature, tahun, kategori, feature_class)
    arcpy.AddMessage('========== Process Complete ==========')

class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = ""

        # List of tool classes associated with this toolbox
        self.tools = [Upload_ZNT, Upload_NBT, Upload_Sampel_ZNT, Upload_Zona_ZNT, Upload_Sampel_NBT, Upload_Peta_Area_Kerja,
                      Upload_Peta_Rencana_Lokasi_Kegiatan, Upload_Peta_Lokasi_Kegiatan, Upload_Delineasi_Zona_Awal_Nilai_Tanah, Upload_Peta_Zona_Awal_Nilai_Tanah,
                      Upload_Peta_Sebaran_Sampel, Upload_Peta_Standar_Deviasi, Upload_Peta_Zona_Nilai_Tanah,
                      Upload_Layout_Peta_Sebaran_Sampel, Upload_Layout_Peta_Standar_Deviasi, Upload_Layout_Peta_Zona_Nilai_Tanah,
                      Upload_Peta_Area_Kerja_Pembaruan, Upload_Peta_Rencana_Lokasi_Kegiatan_Pembaruan, Upload_Peta_Lokasi_Kegiatan_Pembaruan, Upload_Delineasi_Zona_Awal_Nilai_Tanah_Pembaruan, Upload_Peta_Zona_Awal_Nilai_Tanah_Pembaruan,
                      Upload_Peta_Sebaran_Sampel_Pembaruan, Upload_Peta_Standar_Deviasi_Pembaruan, Upload_Peta_Zona_Nilai_Tanah_Pembaruan,
                      Upload_Layout_Peta_Sebaran_Sampel_Pembaruan, Upload_Layout_Peta_Standar_Deviasi_Pembaruan, Upload_Layout_Peta_Zona_Nilai_Tanah_Pembaruan,
                      Upload_Peta_Rencana_Lokasi_Kegiatan_Pembuatan_NBT, Upload_Peta_Lokasi_Kegiatan_Pembuatan_NBT, Upload_Peta_Area_Kerja_Pembuatan_NBT,
                      Upload_Peta_Sebaran_Sampel_Pembuatan_NBT]

#Class ujicoba ZNT
class Upload_ZNT(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Upload ZNT"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        param0 = arcpy.Parameter(
            displayName="NIK",
            name="username",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param1 = arcpy.Parameter(
            displayName="Nomor Berkas",
            name="project_id",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param2 = arcpy.Parameter(
            displayName="Tahun",
            name="tahun",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        param3 = arcpy.Parameter(
            displayName="Feature Class (GDB)",
            name="feature_class",
            datatype="DEFeatureClass",  # Changed from DEFolder to DEFeatureClass
            parameterType="Required",
            direction="Input")
        
        params = [param0, param1, param2, param3]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        username = parameters[0].valueAsText
        project_id = parameters[1].valueAsText
        tahun = parameters[2].valueAsText
        feature_class = parameters[3].valueAsText
##        in_feature = parameters[3].valueAsText

##        topo = 'Zona_Layer_Topology'
##        topologi = os.path.join(in_feature, "ZoneNilaiTanah.gdb", "znt_ds", 'Zona_Layer_Topology')
##        if arcpy.Exists(topologi):
##            arcpy.Delete_management(topologi)
##        if arcpy.Exists(topo):
##            arcpy.Delete_management(topo)

##        main_loop(project_id, "Zona_Layer", tahun, "ZNT", os.path.join(in_feature, "ZoneNilaiTanah.gdb")) #LAMA - pengunaan function main_loop yang lama
        main_loop(project_id, username, "Survei Batas Zona Awal Nilai Tanah", "Survei Batas Zona Awal Nilai Tanah", "Zona_Layer", tahun, "ZNT", feature_class)
        return       

#========== START FUNCTION UPLOAD PEMBUATAN ZNT ===============
#========== Persiapan - Peta Rencana Lokasi Kegiatan ==========
class Upload_Peta_Rencana_Lokasi_Kegiatan(object):
    def __init__(self):
        self.label = "Upload Peta Rencana Lokasi Kegiatan"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        param0 = arcpy.Parameter(
            displayName="NIK",
            name="username",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param1 = arcpy.Parameter(
            displayName="Nomor Berkas",
            name="project_id",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param2 = arcpy.Parameter(
            displayName="Tahun",
            name="tahun",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        param3 = arcpy.Parameter(
            displayName="Input Shapefile",
            name="shapefile_path",
            datatype="DEFile",  # Expect a shapefile (.shp)
            parameterType="Required",
            direction="Input")
        
        params = [param0, param1, param2, param3]
        return params

    def execute(self, parameters, messages):
        username = parameters[0].valueAsText
        project_id = parameters[1].valueAsText
        tahun = parameters[2].valueAsText
        shapefile_path = parameters[3].valueAsText

        # Use main_upload_shapefile for this class
        main_upload_shapefile(project_id, username, "Peta Rencana Lokasi Kegiatan", "Persiapan", "Zona_Layer", tahun, "ZNT", shapefile_path)
        return

#========== Persiapan - Peta Lokasi Kegiatan ==========
class Upload_Peta_Lokasi_Kegiatan(object):
    def __init__(self):
        self.label = "Upload Peta Lokasi Kegiatan"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        param0 = arcpy.Parameter(
            displayName="NIK",
            name="username",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param1 = arcpy.Parameter(
            displayName="Nomor Berkas",
            name="project_id",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param2 = arcpy.Parameter(
            displayName="Tahun",
            name="tahun",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        param3 = arcpy.Parameter(
            displayName="Input Shapefile",
            name="shapefile_path",
            datatype="DEFile",  # Expect a shapefile (.shp)
            parameterType="Required",
            direction="Input")
        
        params = [param0, param1, param2, param3]
        return params

    def execute(self, parameters, messages):
        username = parameters[0].valueAsText
        project_id = parameters[1].valueAsText
        tahun = parameters[2].valueAsText
        shapefile_path = parameters[3].valueAsText

        # Use main_upload_shapefile for this class
        main_upload_shapefile(project_id, username, "Peta Lokasi Kegiatan", "Persiapan", "Zona_Layer", tahun, "ZNT", shapefile_path)
        return

#========== Pembuatan Zona Awal - Peta Area Kerja ==========
class Upload_Peta_Area_Kerja(object):
    def __init__(self):
        self.label = "Upload Peta Area Kerja"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        param0 = arcpy.Parameter(
            displayName="NIK",
            name="username",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param1 = arcpy.Parameter(
            displayName="Nomor Berkas",
            name="project_id",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param2 = arcpy.Parameter(
            displayName="Tahun",
            name="tahun",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        param3 = arcpy.Parameter(
            displayName="Input Shapefile",
            name="shapefile_path",
            datatype="DEFile",  # Expect a shapefile (.shp)
            parameterType="Required",
            direction="Input")
        
        params = [param0, param1, param2, param3]
        return params

    def execute(self, parameters, messages):
        username = parameters[0].valueAsText
        project_id = parameters[1].valueAsText
        tahun = parameters[2].valueAsText
        shapefile_path = parameters[3].valueAsText

        # Use main_upload_shapefile for this class
        main_upload_shapefile(project_id, username, "Peta Area Kerja", "Pembuatan Zona Awal", "Zona_Layer", tahun, "ZNT", shapefile_path)
        return        

#========== Pembuatan Zona Awal - Delineasi Zona Awal Nilai Tanah ==========
class Upload_Delineasi_Zona_Awal_Nilai_Tanah(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Upload Delineasi Zona Awal Nilai Tanah"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        param0 = arcpy.Parameter(
            displayName="NIK",
            name="username",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param1 = arcpy.Parameter(
            displayName="Nomor Berkas",
            name="project_id",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param2 = arcpy.Parameter(
            displayName="Tahun",
            name="tahun",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        param3 = arcpy.Parameter(
            displayName="Feature Class (GDB)",
            name="feature_class",
            datatype="DEFeatureClass",  # Changed from DEFolder to DEFeatureClass
            parameterType="Required",
            direction="Input")
        
        params = [param0, param1, param2, param3]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        username = parameters[0].valueAsText
        project_id = parameters[1].valueAsText
        tahun = parameters[2].valueAsText
        feature_class = parameters[3].valueAsText

        main_loop(project_id, username, "Delineasi Zona Awal Nilai Tanah", "Pembuatan Zona Awal", "Zona_Layer", tahun, "ZNT", feature_class)
        
        return        

#========== Survei Batas Zona Awal Nilai Tanah - Peta Zona Awal Nilai Tanah (Peta Kerja) ==========
class Upload_Peta_Zona_Awal_Nilai_Tanah(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Upload Peta Zona Awal Nilai Tanah"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        param0 = arcpy.Parameter(
            displayName="NIK",
            name="username",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param1 = arcpy.Parameter(
            displayName="Nomor Berkas",
            name="project_id",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param2 = arcpy.Parameter(
            displayName="Tahun",
            name="tahun",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        param3 = arcpy.Parameter(
            displayName="Feature Class (GDB)",
            name="feature_class",
            datatype="DEFeatureClass",  # Changed from DEFolder to DEFeatureClass
            parameterType="Required",
            direction="Input")
        
        params = [param0, param1, param2, param3]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        username = parameters[0].valueAsText
        project_id = parameters[1].valueAsText
        tahun = parameters[2].valueAsText
        feature_class = parameters[3].valueAsText

        main_loop(project_id, username, "Survei Batas Zona Awal Nilai Tanah", "Survei Batas Zona Awal Nilai Tanah", "Zona_Layer", tahun, "ZNT", feature_class)
        return        

#========== Analisis dan Pengolahan Data - Peta Sebaran Sampel ==========
class Upload_Peta_Sebaran_Sampel(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Upload Peta Sebaran Sampel"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        param0 = arcpy.Parameter(
            displayName="NIK",
            name="username",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param1 = arcpy.Parameter(
            displayName="Nomor Berkas",
            name="project_id",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param2 = arcpy.Parameter(
            displayName="Tahun",
            name="tahun",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        param3 = arcpy.Parameter(
            displayName="Feature Class (GDB)",
            name="feature_class",
            datatype="DEFeatureClass",  # Changed from DEFolder to DEFeatureClass
            parameterType="Required",
            direction="Input")
        
        params = [param0, param1, param2, param3]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        username = parameters[0].valueAsText
        project_id = parameters[1].valueAsText
        tahun = parameters[2].valueAsText
        feature_class = parameters[3].valueAsText

        main_loop(project_id, username, "Peta Sebaran Sampel", "Analisis dan Pengolahan Data", "Titik_Sampel", tahun, "ZNT", feature_class)
        
        return

#========== Analisis dan Pengolahan Data - Peta Standar Deviasi ==========
class Upload_Peta_Standar_Deviasi(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Upload Peta Simpangan Baku Relatif"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        param0 = arcpy.Parameter(
            displayName="NIK",
            name="username",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param1 = arcpy.Parameter(
            displayName="Nomor Berkas",
            name="project_id",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param2 = arcpy.Parameter(
            displayName="Tahun",
            name="tahun",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        param3 = arcpy.Parameter(
            displayName="Feature Class (GDB)",
            name="feature_class",
            datatype="DEFeatureClass",  # Changed from DEFolder to DEFeatureClass
            parameterType="Required",
            direction="Input")
        
        params = [param0, param1, param2, param3]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        username = parameters[0].valueAsText
        project_id = parameters[1].valueAsText
        tahun = parameters[2].valueAsText
        feature_class = parameters[3].valueAsText

        main_loop(project_id, username, "Peta Standar Deviasi", "Analisis dan Pengolahan Data", "Zona_Layer", tahun, "ZNT", feature_class)
        
        return

#========== Analisis dan Pengolahan Data - Peta Zona Nilai Tanah ==========
class Upload_Peta_Zona_Nilai_Tanah(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Upload Peta Zona Nilai Tanah"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        param0 = arcpy.Parameter(
            displayName="NIK",
            name="username",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param1 = arcpy.Parameter(
            displayName="Nomor Berkas",
            name="project_id",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param2 = arcpy.Parameter(
            displayName="Tahun",
            name="tahun",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        param3 = arcpy.Parameter(
            displayName="Feature Class (GDB)",
            name="feature_class",
            datatype="DEFeatureClass",  # Changed from DEFolder to DEFeatureClass
            parameterType="Required",
            direction="Input")
        
        params = [param0, param1, param2, param3]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        username = parameters[0].valueAsText
        project_id = parameters[1].valueAsText
        tahun = parameters[2].valueAsText
        feature_class = parameters[3].valueAsText

        main_loop(project_id, username, "Peta Zona Nilai Tanah", "Analisis dan Pengolahan Data", "Zona_Layer", tahun, "ZNT", feature_class)
        
        return

#========== Penyajian Data - Peta Sebaran Sampel ==========
class Upload_Layout_Peta_Sebaran_Sampel(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Upload Layout Peta Sebaran Sampel"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        param0 = arcpy.Parameter(
            displayName="NIK",
            name="username",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param1 = arcpy.Parameter(
            displayName="Nomor Berkas",
            name="project_id",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param2 = arcpy.Parameter(
            displayName="Tahun",
            name="tahun",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        param3 = arcpy.Parameter(
            displayName="Feature Class (GDB)",
            name="feature_class",
            datatype="DEFeatureClass",  # Changed from DEFolder to DEFeatureClass
            parameterType="Required",
            direction="Input")
        
        params = [param0, param1, param2, param3]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        username = parameters[0].valueAsText
        project_id = parameters[1].valueAsText
        tahun = parameters[2].valueAsText
        feature_class = parameters[3].valueAsText

        main_loop(project_id, username, "Peta Sebaran Sampel", "Penyajian Peta", "Titik_Sampel", tahun, "ZNT", feature_class)
        
        return

#========== Penyajian Data - Peta Standar Deviasi ==========
class Upload_Layout_Peta_Standar_Deviasi(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Upload Layout Peta Simpangan Baku Relatif"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        param0 = arcpy.Parameter(
            displayName="NIK",
            name="username",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param1 = arcpy.Parameter(
            displayName="Nomor Berkas",
            name="project_id",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param2 = arcpy.Parameter(
            displayName="Tahun",
            name="tahun",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        param3 = arcpy.Parameter(
            displayName="Feature Class (GDB)",
            name="feature_class",
            datatype="DEFeatureClass",  # Changed from DEFolder to DEFeatureClass
            parameterType="Required",
            direction="Input")
        
        params = [param0, param1, param2, param3]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        username = parameters[0].valueAsText
        project_id = parameters[1].valueAsText
        tahun = parameters[2].valueAsText
        feature_class = parameters[3].valueAsText

        main_loop(project_id, username, "Peta Standar Deviasi", "Penyajian Peta", "Zona_Layer", tahun, "ZNT", feature_class)
        
        return

#========== Penyajian Data - Peta Zona Nilai Tanah ==========
class Upload_Layout_Peta_Zona_Nilai_Tanah(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Upload Layout Peta Zona Nilai Tanah"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        param0 = arcpy.Parameter(
            displayName="NIK",
            name="username",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param1 = arcpy.Parameter(
            displayName="Nomor Berkas",
            name="project_id",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param2 = arcpy.Parameter(
            displayName="Tahun",
            name="tahun",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        param3 = arcpy.Parameter(
            displayName="Feature Class (GDB)",
            name="feature_class",
            datatype="DEFeatureClass",  # Changed from DEFolder to DEFeatureClass
            parameterType="Required",
            direction="Input")
        
        params = [param0, param1, param2, param3]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        username = parameters[0].valueAsText
        project_id = parameters[1].valueAsText
        tahun = parameters[2].valueAsText
        feature_class = parameters[3].valueAsText

        main_loop(project_id, username, "Peta Zona Nilai Tanah", "Penyajian Peta", "Zona_Layer", tahun, "ZNT", feature_class)
        
        return

#========== END FUNCTION UPLOAD PEMBUATAN ZNT =================

#========== START FUNCTION UPLOAD PEMBARUAN ZNT ===============
class Upload_Peta_Rencana_Lokasi_Kegiatan_Pembaruan(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Upload Peta Rencana Lokasi Kegiatan Pembaruan ZNT"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        param0 = arcpy.Parameter(
            displayName="NIK",
            name="username",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param1 = arcpy.Parameter(
            displayName="Nomor Berkas",
            name="project_id",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param2 = arcpy.Parameter(
            displayName="Tahun",
            name="tahun",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        param3 = arcpy.Parameter(
            displayName="Input Shapefile",
            name="shapefile_path",
            datatype="DEFile",  # Expect a shapefile (.shp)
            parameterType="Required",
            direction="Input")
        
        params = [param0, param1, param2, param3]
        return params

    def execute(self, parameters, messages):
        username = parameters[0].valueAsText
        project_id = parameters[1].valueAsText
        tahun = parameters[2].valueAsText
        shapefile_path = parameters[3].valueAsText

        # Use main_upload_shapefile for this class
        main_upload_shapefile(project_id, username, "Peta Rencana Lokasi Kegiatan Pembaruan ZNT", "Persiapan", "Zona_Layer", tahun, "ZNT", shapefile_path)
        return

#========== Persiapan - Peta Lokasi Kegiatan ==========
class Upload_Peta_Lokasi_Kegiatan_Pembaruan(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Upload Peta Lokasi Kegiatan Pembaruan ZNT"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        param0 = arcpy.Parameter(
            displayName="NIK",
            name="username",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param1 = arcpy.Parameter(
            displayName="Nomor Berkas",
            name="project_id",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param2 = arcpy.Parameter(
            displayName="Tahun",
            name="tahun",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        param3 = arcpy.Parameter(
            displayName="Input Shapefile",
            name="shapefile_path",
            datatype="DEFile",  # Expect a shapefile (.shp)
            parameterType="Required",
            direction="Input")
        
        params = [param0, param1, param2, param3]
        return params

    def execute(self, parameters, messages):
        username = parameters[0].valueAsText
        project_id = parameters[1].valueAsText
        tahun = parameters[2].valueAsText
        shapefile_path = parameters[3].valueAsText

        # Use main_upload_shapefile for this class
        main_upload_shapefile(project_id, username, "Peta Lokasi Kegiatan Pembaruan ZNT", "Persiapan", "Zona_Layer", tahun, "ZNT", shapefile_path)
        return

#========== Pembuatan Zona Awal - Peta Area Kerja ==========
class Upload_Peta_Area_Kerja_Pembaruan(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Upload Peta Area Kerja Pembaruan ZNT"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        param0 = arcpy.Parameter(
            displayName="NIK",
            name="username",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param1 = arcpy.Parameter(
            displayName="Nomor Berkas",
            name="project_id",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param2 = arcpy.Parameter(
            displayName="Tahun",
            name="tahun",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        param3 = arcpy.Parameter(
            displayName="Feature Class (GDB)",
            name="feature_class",
            datatype="DEFeatureClass",  # Changed from DEFolder to DEFeatureClass
            parameterType="Required",
            direction="Input")
        
        params = [param0, param1, param2, param3]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        username = parameters[0].valueAsText
        project_id = parameters[1].valueAsText
        tahun = parameters[2].valueAsText
        feature_class = parameters[3].valueAsText

        #main_loop(project_id, username, "Peta Area Kerja", "Pembuatan Zona Awal", "Zona_Layer", tahun, "ZNT", feature_class)
        
        return        

#========== Pembuatan Zona Awal - Delineasi Zona Awal Nilai Tanah ==========
class Upload_Delineasi_Zona_Awal_Nilai_Tanah_Pembaruan(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Upload Delineasi Zona yang Diperbarui"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        param0 = arcpy.Parameter(
            displayName="NIK",
            name="username",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param1 = arcpy.Parameter(
            displayName="Nomor Berkas",
            name="project_id",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param2 = arcpy.Parameter(
            displayName="Tahun",
            name="tahun",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        param3 = arcpy.Parameter(
            displayName="Feature Class (GDB)",
            name="feature_class",
            datatype="DEFeatureClass",  # Changed from DEFolder to DEFeatureClass
            parameterType="Required",
            direction="Input")
        
        params = [param0, param1, param2, param3]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        username = parameters[0].valueAsText
        project_id = parameters[1].valueAsText
        tahun = parameters[2].valueAsText
        feature_class = parameters[3].valueAsText

        main_loop(project_id, username, "Peta Deliniasi ZNT", "Analisis & Delineasi Zona yang Mengalami Perubahan", "Zona_Layer", tahun, "ZNT", feature_class)
        
        return        

#========== Survei Batas Zona Awal Nilai Tanah - Peta Zona Awal Nilai Tanah (Peta Kerja) ==========
class Upload_Peta_Zona_Awal_Nilai_Tanah_Pembaruan(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Upload Peta Zona yang Diperbarui"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        param0 = arcpy.Parameter(
            displayName="NIK",
            name="username",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param1 = arcpy.Parameter(
            displayName="Nomor Berkas",
            name="project_id",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param2 = arcpy.Parameter(
            displayName="Tahun",
            name="tahun",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        param3 = arcpy.Parameter(
            displayName="Feature Class (GDB)",
            name="feature_class",
            datatype="DEFeatureClass",  # Changed from DEFolder to DEFeatureClass
            parameterType="Required",
            direction="Input")
        
        params = [param0, param1, param2, param3]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        username = parameters[0].valueAsText
        project_id = parameters[1].valueAsText
        tahun = parameters[2].valueAsText
        feature_class = parameters[3].valueAsText

        main_loop(project_id, username, "Peta Zona Diperbarui Analisis Pembaruan ZNT", "Analisis dan Pengolahan Data", "Zona_Layer", tahun, "ZNT", feature_class)
        return        

#========== Analisis dan Pengolahan Data - Peta Sebaran Sampel ==========
class Upload_Peta_Sebaran_Sampel_Pembaruan(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Upload Pembaruan Peta Sebaran Sampel"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        param0 = arcpy.Parameter(
            displayName="NIK",
            name="username",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param1 = arcpy.Parameter(
            displayName="Nomor Berkas",
            name="project_id",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param2 = arcpy.Parameter(
            displayName="Tahun",
            name="tahun",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        param3 = arcpy.Parameter(
            displayName="Feature Class (GDB)",
            name="feature_class",
            datatype="DEFeatureClass",  # Changed from DEFolder to DEFeatureClass
            parameterType="Required",
            direction="Input")
        
        params = [param0, param1, param2, param3]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        username = parameters[0].valueAsText
        project_id = parameters[1].valueAsText
        tahun = parameters[2].valueAsText
        feature_class = parameters[3].valueAsText

        main_loop(project_id, username, "Peta Sebaran Sampel Analisis Pembaruan ZNT", "Analisis dan Pengolahan Data", "Titik_Sampel", tahun, "ZNT", feature_class)
        
        return

#========== Analisis dan Pengolahan Data - Peta Standar Deviasi ==========
class Upload_Peta_Standar_Deviasi_Pembaruan(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Upload Pembaruan Peta Simpangan Baku Relatif"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        param0 = arcpy.Parameter(
            displayName="NIK",
            name="username",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param1 = arcpy.Parameter(
            displayName="Nomor Berkas",
            name="project_id",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param2 = arcpy.Parameter(
            displayName="Tahun",
            name="tahun",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        param3 = arcpy.Parameter(
            displayName="Feature Class (GDB)",
            name="feature_class",
            datatype="DEFeatureClass",  # Changed from DEFolder to DEFeatureClass
            parameterType="Required",
            direction="Input")
        
        params = [param0, param1, param2, param3]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        username = parameters[0].valueAsText
        project_id = parameters[1].valueAsText
        tahun = parameters[2].valueAsText
        feature_class = parameters[3].valueAsText

        main_loop(project_id, username, "Peta Simpangan Baku Relatif", "Analisis dan Pengolahan Data", "Zona_Layer", tahun, "ZNT", feature_class)
        
        return

#========== Analisis dan Pengolahan Data - Peta Zona Nilai Tanah ==========
class Upload_Peta_Zona_Nilai_Tanah_Pembaruan(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Upload Pembaruan Peta Zona Nilai Tanah"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        param0 = arcpy.Parameter(
            displayName="NIK",
            name="username",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param1 = arcpy.Parameter(
            displayName="Nomor Berkas",
            name="project_id",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param2 = arcpy.Parameter(
            displayName="Tahun",
            name="tahun",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        param3 = arcpy.Parameter(
            displayName="Feature Class (GDB)",
            name="feature_class",
            datatype="DEFeatureClass",  # Changed from DEFolder to DEFeatureClass
            parameterType="Required",
            direction="Input")
        
        params = [param0, param1, param2, param3]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        username = parameters[0].valueAsText
        project_id = parameters[1].valueAsText
        tahun = parameters[2].valueAsText
        feature_class = parameters[3].valueAsText

        main_loop(project_id, username, "Peta Zona Nilai Tanah Analisis Pembaruan ZNT", "Analisis dan Pengolahan Data", "Zona_Layer", tahun, "ZNT", feature_class)
        
        return

#========== Penyajian Data - Peta Sebaran Sampel ==========
class Upload_Layout_Peta_Sebaran_Sampel_Pembaruan(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Upload Layout Pembaruan Peta Sebaran Sampel"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        param0 = arcpy.Parameter(
            displayName="NIK",
            name="username",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param1 = arcpy.Parameter(
            displayName="Nomor Berkas",
            name="project_id",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param2 = arcpy.Parameter(
            displayName="Tahun",
            name="tahun",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        param3 = arcpy.Parameter(
            displayName="Feature Class (GDB)",
            name="feature_class",
            datatype="DEFeatureClass",  # Changed from DEFolder to DEFeatureClass
            parameterType="Required",
            direction="Input")
        
        params = [param0, param1, param2, param3]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        username = parameters[0].valueAsText
        project_id = parameters[1].valueAsText
        tahun = parameters[2].valueAsText
        feature_class = parameters[3].valueAsText

        main_loop(project_id, username, "Peta Sebaran Sampel Penyajian Peta Pembaruan ZNT", "Penyajian Peta", "Titik_Sampel", tahun, "ZNT", feature_class)
        
        return

#========== Penyajian Data - Peta Standar Deviasi ==========
class Upload_Layout_Peta_Standar_Deviasi_Pembaruan(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Upload Layout Pembaruan Peta Simpangan Baku Relatif"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        param0 = arcpy.Parameter(
            displayName="NIK",
            name="username",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param1 = arcpy.Parameter(
            displayName="Nomor Berkas",
            name="project_id",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param2 = arcpy.Parameter(
            displayName="Tahun",
            name="tahun",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        param3 = arcpy.Parameter(
            displayName="Feature Class (GDB)",
            name="feature_class",
            datatype="DEFeatureClass",  # Changed from DEFolder to DEFeatureClass
            parameterType="Required",
            direction="Input")
        
        params = [param0, param1, param2, param3]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        username = parameters[0].valueAsText
        project_id = parameters[1].valueAsText
        tahun = parameters[2].valueAsText
        feature_class = parameters[3].valueAsText

        main_loop(project_id, username, "Peta Standar Deviasi Pembaruan ZNT", "Penyajian Peta", "Zona_Layer", tahun, "ZNT", feature_class)
        
        return

#========== Penyajian Data - Peta Zona Nilai Tanah ==========
class Upload_Layout_Peta_Zona_Nilai_Tanah_Pembaruan(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Upload Layout Pembaruan Peta Zona Nilai Tanah"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        param0 = arcpy.Parameter(
            displayName="NIK",
            name="username",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param1 = arcpy.Parameter(
            displayName="Nomor Berkas",
            name="project_id",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param2 = arcpy.Parameter(
            displayName="Tahun",
            name="tahun",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        param3 = arcpy.Parameter(
            displayName="Feature Class (GDB)",
            name="feature_class",
            datatype="DEFeatureClass",  # Changed from DEFolder to DEFeatureClass
            parameterType="Required",
            direction="Input")
        
        params = [param0, param1, param2, param3]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        username = parameters[0].valueAsText
        project_id = parameters[1].valueAsText
        tahun = parameters[2].valueAsText
        feature_class = parameters[3].valueAsText

        main_loop(project_id, username, "Peta Zona Nilai Tanah Penyajian Peta Pembaruan ZNT", "Penyajian Peta", "Zona_Layer", tahun, "ZNT", feature_class)
        
        return
#========== END FUNCTION UPLOAD PEMBARUAN ZNT ===============

#Class ujicoba NBT
class Upload_NBT(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Testing Upload NBT"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        param0 = arcpy.Parameter(
            displayName="NIK",
            name="username",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param1 = arcpy.Parameter(
            displayName="Nomor Berkas",
            name="project_id",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param2 = arcpy.Parameter(
            displayName="Tahun",
            name="tahun",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        param3 = arcpy.Parameter(
            displayName="Feature Class (GDB)",
            name="feature_class",
            datatype="DEFeatureClass",  # Changed from DEFolder to DEFeatureClass
            parameterType="Required",
            direction="Input")
        
        params = [param0, param1, param2, param3]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        username = parameters[0].valueAsText
        project_id = parameters[1].valueAsText
        tahun = parameters[2].valueAsText
        feature_class = parameters[3].valueAsText

        main_loop(project_id, username, "Peta Area Kerja Pembuatan NBT", "Persiapan", "Zona_Layer", tahun, "ZNT", feature_class)
        
        return

#========== START FUNCTION UPLOAD PEMBUATAN NBT ===============
#========== Persiapan - Peta Rencana Lokasi Kegiatan ==========
class Upload_Peta_Rencana_Lokasi_Kegiatan_Pembuatan_NBT(object):
    def __init__(self):
        self.label = "Upload Peta Rencana Lokasi Kegiatan NBT"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        param0 = arcpy.Parameter(
            displayName="NIK",
            name="username",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param1 = arcpy.Parameter(
            displayName="Nomor Berkas",
            name="project_id",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param2 = arcpy.Parameter(
            displayName="Tahun",
            name="tahun",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        param3 = arcpy.Parameter(
            displayName="Input Shapefile",
            name="shapefile_path",
            datatype="DEFile",  # Expect a shapefile (.shp)
            parameterType="Required",
            direction="Input")
        
        params = [param0, param1, param2, param3]
        return params

    def execute(self, parameters, messages):
        username = parameters[0].valueAsText
        project_id = parameters[1].valueAsText
        tahun = parameters[2].valueAsText
        shapefile_path = parameters[3].valueAsText

        # Use main_upload_shapefile for this class
        main_upload_shapefile(project_id, username, "Peta Rencana Lokasi Kegiatan Pembuatan NBT", "Persiapan", "Zona_Layer", tahun, "ZNT", shapefile_path)
        return

#========== Persiapan - Peta Lokasi Kegiatan ==========
class Upload_Peta_Lokasi_Kegiatan_Pembuatan_NBT(object):
    def __init__(self):
        self.label = "Upload Peta Lokasi Kegiatan Pembuatan NBT"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        param0 = arcpy.Parameter(
            displayName="NIK",
            name="username",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param1 = arcpy.Parameter(
            displayName="Nomor Berkas",
            name="project_id",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param2 = arcpy.Parameter(
            displayName="Tahun",
            name="tahun",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        param3 = arcpy.Parameter(
            displayName="Input Shapefile",
            name="shapefile_path",
            datatype="DEFile",  # Expect a shapefile (.shp)
            parameterType="Required",
            direction="Input")
        
        params = [param0, param1, param2, param3]
        return params

    def execute(self, parameters, messages):
        username = parameters[0].valueAsText
        project_id = parameters[1].valueAsText
        tahun = parameters[2].valueAsText
        shapefile_path = parameters[3].valueAsText

        # Use main_upload_shapefile for this class
        main_upload_shapefile(project_id, username, "Peta Lokasi Kegiatan Pembuatan NBT", "Persiapan", "Zona_Layer", tahun, "ZNT", shapefile_path)
        return

#========== Pembuatan Zona Awal - Peta Area Kerja ==========
class Upload_Peta_Area_Kerja_Pembuatan_NBT(object):
    def __init__(self):
        self.label = "Upload Peta Area Kerja Pembuatan NBT"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        param0 = arcpy.Parameter(
            displayName="NIK",
            name="username",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param1 = arcpy.Parameter(
            displayName="Nomor Berkas",
            name="project_id",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param2 = arcpy.Parameter(
            displayName="Tahun",
            name="tahun",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        param3 = arcpy.Parameter(
            displayName="Input Shapefile",
            name="shapefile_path",
            datatype="DEFile",  # Expect a shapefile (.shp)
            parameterType="Required",
            direction="Input")
        
        params = [param0, param1, param2, param3]
        return params

    def execute(self, parameters, messages):
        username = parameters[0].valueAsText
        project_id = parameters[1].valueAsText
        tahun = parameters[2].valueAsText
        shapefile_path = parameters[3].valueAsText

        # Use main_upload_shapefile for this class
        main_upload_shapefile(project_id, username, "Peta Area Kerja Pembuatan NBT", "Pembuatan Zona Awal", "Zona_Layer", tahun, "ZNT", shapefile_path)
        return

#========== Pengumpulan Data Sampel Nilai Tanah - Peta Sebaran Sampel Pembuatan NBT ==========
class Upload_Peta_Sebaran_Sampel_Pembuatan_NBT(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Upload Peta Sebaran Sampel Pembuatan NBT"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        param0 = arcpy.Parameter(
            displayName="NIK",
            name="username",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param1 = arcpy.Parameter(
            displayName="Nomor Berkas",
            name="project_id",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param2 = arcpy.Parameter(
            displayName="Tahun",
            name="tahun",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        param3 = arcpy.Parameter(
            displayName="Feature Class (GDB)",
            name="feature_class",
            datatype="DEFeatureClass",  # Changed from DEFolder to DEFeatureClass
            parameterType="Required",
            direction="Input")
        
        params = [param0, param1, param2, param3]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        username = parameters[0].valueAsText
        project_id = parameters[1].valueAsText
        tahun = parameters[2].valueAsText
        feature_class = parameters[3].valueAsText

        main_loop(project_id, username, "Peta Sebaran Sampel", "Analisis dan Pengolahan Data", "Titik_Sampel", tahun, "ZNT", feature_class)
        
        return
    
#========== END FUNCTION UPLOAD PEMBARUAN NBT =================

class Upload_Sampel_ZNT(object):


    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Upload Titik Sampel Hasil Validasi ZNT"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        param0 = arcpy.Parameter(
            displayName="Username",
            name="username",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param1 = arcpy.Parameter(
            displayName="Password",
            name="password",
            datatype="GPStringHidden",
            parameterType="Required",
            direction="Input")
        param2 = arcpy.Parameter(
            displayName="Nomor Berkas",
            name="project_id",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")
        param3 = arcpy.Parameter(
            displayName="Tahun",
            name="tahun",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        param4 = arcpy.Parameter(
            displayName="User",
            name="user",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param5 = arcpy.Parameter(
            displayName="Nomor Berkas",
            name="kontrak",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")
        param6 = arcpy.Parameter(
            displayName="Workspace",
            name="workspace",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")
        
        param4.filter.type = "ValueList"
        param4.filter.list = ['Swakelola', 'Pihak Ke 3']

        param2.enabled = False
        param3.enabled = False
        param5.enabled = False
        param6.enabled = False
        params = [param4, param0, param1, param2, param5, param3, param6]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        if parameters[0].value and parameters[1].value and parameters[2].value:
            if not parameters[3].value and parameters[0].value == 'Swakelola':
                parameters[4].value = ''
                parameters[5].value = ''
                parameters[6].value = ''
                parameters[4].enabled = False
                parameters[5].enabled = False
                parameters[6].enabled = False
                drpdown = []
                list_project.clear()
                list_kontrak.clear()
                #list_sk.clear()
                url = "https://sipenta.atrbpn.go.id/api/index.php/api_sipenta/get_login_kontrak"

                session = requests.Session()
                response = session.get(url)
                client = requests.session()
                client.get(url)
                if 'tokencsrf' in client.cookies:
                    csrftoken = client.cookies['tokencsrf']
                else:
                    csrftoken = client.cookies['tokencsrf']

                cookies = {'tokencsrf': csrftoken}
                data = {
                    "username": parameters[1].value,
                    "password": parameters[2].value,
                    "tokencsrf": csrftoken}

                x = requests.post(url, cookies=cookies, data=data).text
                y = json.loads(x)
                if y["status"] == 'gagal':
                    arcpy.AddMessage(y["message"])
                    arcpy.AddError(y["status"])
                else:
                    if y["token"] and y["projects"]:
                        for g in y["projects"]:
                            drpdown.append(g["project_id"])

                        for h in y["project"]:
                            list_project[str(h["project_id"])] = h["tahun"]
                            list_kontrak[str(h["project_id"])] = h["kontrak"]
                            #list_sk[str(h["project_id"])] = h["sk"]
                            
                        parameters[3].filter.type = "ValueList"
                        parameters[3].filter.list = drpdown
                        parameters[3].enabled = True
                    else :
                        arcpy.AddMessage('Nomor Berkas Tidak Ditemukan')
                        arcpy.AddError('Nomor Berkas Tidak Ditemukan')
            elif parameters[3].value and parameters[0].value == 'Swakelola':
                thn = parameters[3].valueAsText
                parameters[5].value = list_project[thn]
                parameters[5].enabled = True
                parameters[6].enabled = True
            else:
                if not parameters[6].value and parameters[0].value == 'Pihak Ke 3':
                    parameters[3].filter.type = "ValueList"
                    parameters[3].filter.list = []
                    parameters[3].value = ''
                    parameters[4].value = ''
                    parameters[5].value = ''
                    parameters[6].value = ''
                    parameters[3].enabled = False
                    parameters[4].enabled = False
                    parameters[5].enabled = False
                    parameters[6].enabled = False

                    url = "https://sipenta.atrbpn.go.id/api/index.php/api_sipenta/get_login_mitra"

                    session = requests.Session()
                    response = session.get(url)
                    client = requests.session()
                    client.get(url)
                    if 'tokencsrf' in client.cookies:
                        csrftoken = client.cookies['tokencsrf']
                    else:
                        csrftoken = client.cookies['tokencsrf']

                    cookies = {'tokencsrf': csrftoken}
                    data = {
                        "username": parameters[1].value,
                        "password": parameters[2].value,
                        "tokencsrf": csrftoken}

                    x = requests.post(url, cookies=cookies, data=data).text
                    y = json.loads(x)
                    if y["status"] == 'gagal':
                        arcpy.AddMessage(y["message"])
                        arcpy.AddError(y["status"])
                    else:
                        if y["token"] and y["kontrak"]:
                            list_kontrak[str(y["nomorberkas"])] = y["kontrak"]
                            parameters[4].value = y["nomorberkas"]
                            parameters[4].enabled = True
                            parameters[5].value = y["tahun"]
                            parameters[5].enabled = True
                            parameters[6].enabled = True
                        else :
                            arcpy.AddMessage('Nomor Kontrak Tidak Ditemukan')
                            arcpy.AddError('Nomor Kontrak Tidak Ditemukan')            
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        kondisi = parameters[0].valueAsText
        username = parameters[1].valueAsText
        password = parameters[2].valueAsText
        project_id = ''
        if kondisi == 'Swakelola':
            project_id = parameters[3].valueAsText
        else:
            project_id = parameters[4].valueAsText
        in_feature = parameters[6].valueAsText
        tahun = parameters[5].valueAsText

        main_loop(project_id, "Titik_Sampel", tahun, 'Titik_Sampel_ZNT', os.path.join(in_feature, "ZoneNilaiTanah.gdb"))

##        ret = cek_status(username, password, project_id, in_feature, tahun, 'upload', 'ZNT')
##        if ret :
##            main_loop(project_id, "Zona_Layer", tahun, 'upload_znt', os.path.join(in_feature, "ZoneNilaiTanah.gdb"))
##        else :
##            arcpy.AddMessage('Syarat Upload ZNT Belum Terpenuhi');
    
        return

class Upload_Zona_ZNT(object):


    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Upload Titik Zona Hasil Validasi ZNT"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        param0 = arcpy.Parameter(
            displayName="Username",
            name="username",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param1 = arcpy.Parameter(
            displayName="Password",
            name="password",
            datatype="GPStringHidden",
            parameterType="Required",
            direction="Input")
        param2 = arcpy.Parameter(
            displayName="Nomor Berkas",
            name="project_id",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")
        param3 = arcpy.Parameter(
            displayName="Tahun",
            name="tahun",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        param4 = arcpy.Parameter(
            displayName="User",
            name="user",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param5 = arcpy.Parameter(
            displayName="Nomor Berkas",
            name="kontrak",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")
        param6 = arcpy.Parameter(
            displayName="Workspace",
            name="workspace",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")
        
        param4.filter.type = "ValueList"
        param4.filter.list = ['Swakelola', 'Pihak Ke 3']

        param2.enabled = False
        param3.enabled = False
        param5.enabled = False
        param6.enabled = False
        params = [param4, param0, param1, param2, param5, param3, param6]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        if parameters[0].value and parameters[1].value and parameters[2].value:
            if not parameters[3].value and parameters[0].value == 'Swakelola':
                parameters[4].value = ''
                parameters[5].value = ''
                parameters[6].value = ''
                parameters[4].enabled = False
                parameters[5].enabled = False
                parameters[6].enabled = False
                drpdown = []
                list_project.clear()
                list_kontrak.clear()
                #list_sk.clear()
                url = "https://sipenta.atrbpn.go.id/api/index.php/api_sipenta/get_login_kontrak"

                session = requests.Session()
                response = session.get(url)
                client = requests.session()
                client.get(url)
                if 'tokencsrf' in client.cookies:
                    csrftoken = client.cookies['tokencsrf']
                else:
                    csrftoken = client.cookies['tokencsrf']

                cookies = {'tokencsrf': csrftoken}
                data = {
                    "username": parameters[1].value,
                    "password": parameters[2].value,
                    "tokencsrf": csrftoken}

                x = requests.post(url, cookies=cookies, data=data).text
                y = json.loads(x)
                if y["status"] == 'gagal':
                    arcpy.AddMessage(y["message"])
                    arcpy.AddError(y["status"])
                else:
                    if y["token"] and y["projects"]:
                        for g in y["projects"]:
                            drpdown.append(g["project_id"])

                        for h in y["project"]:
                            list_project[str(h["project_id"])] = h["tahun"]
                            list_kontrak[str(h["project_id"])] = h["kontrak"]
                            #list_sk[str(h["project_id"])] = h["sk"]
                            
                        parameters[3].filter.type = "ValueList"
                        parameters[3].filter.list = drpdown
                        parameters[3].enabled = True
                    else :
                        arcpy.AddMessage('Nomor Berkas Tidak Ditemukan')
                        arcpy.AddError('Nomor Berkas Tidak Ditemukan')
            elif parameters[3].value and parameters[0].value == 'Swakelola':
                thn = parameters[3].valueAsText
                parameters[5].value = list_project[thn]
                parameters[5].enabled = True
                parameters[6].enabled = True
            else:
                if not parameters[6].value and parameters[0].value == 'Pihak Ke 3':
                    parameters[3].filter.type = "ValueList"
                    parameters[3].filter.list = []
                    parameters[3].value = ''
                    parameters[4].value = ''
                    parameters[5].value = ''
                    parameters[6].value = ''
                    parameters[3].enabled = False
                    parameters[4].enabled = False
                    parameters[5].enabled = False
                    parameters[6].enabled = False

                    url = "https://sipenta.atrbpn.go.id/api/index.php/api_sipenta/get_login_mitra"

                    session = requests.Session()
                    response = session.get(url)
                    client = requests.session()
                    client.get(url)
                    if 'tokencsrf' in client.cookies:
                        csrftoken = client.cookies['tokencsrf']
                    else:
                        csrftoken = client.cookies['tokencsrf']

                    cookies = {'tokencsrf': csrftoken}
                    data = {
                        "username": parameters[1].value,
                        "password": parameters[2].value,
                        "tokencsrf": csrftoken}

                    x = requests.post(url, cookies=cookies, data=data).text
                    y = json.loads(x)
                    if y["status"] == 'gagal':
                        arcpy.AddMessage(y["message"])
                        arcpy.AddError(y["status"])
                    else:
                        if y["token"] and y["kontrak"]:
                            list_kontrak[str(y["nomorberkas"])] = y["kontrak"]
                            parameters[4].value = y["nomorberkas"]
                            parameters[4].enabled = True
                            parameters[5].value = y["tahun"]
                            parameters[5].enabled = True
                            parameters[6].enabled = True
                        else :
                            arcpy.AddMessage('Nomor Kontrak Tidak Ditemukan')
                            arcpy.AddError('Nomor Kontrak Tidak Ditemukan')            
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        kondisi = parameters[0].valueAsText
        username = parameters[1].valueAsText
        password = parameters[2].valueAsText
        project_id = ''
        if kondisi == 'Swakelola':
            project_id = parameters[3].valueAsText
        else:
            project_id = parameters[4].valueAsText
        in_feature = parameters[6].valueAsText
        tahun = parameters[5].valueAsText

        main_loop(project_id, "Titik_Zona", tahun, 'Titik_Zona_ZNT', os.path.join(in_feature, "ZoneNilaiTanah.gdb"))

##        ret = cek_status(username, password, project_id, in_feature, tahun, 'upload', 'ZNT')
##        if ret :
##            main_loop(project_id, "Zona_Layer", tahun, 'upload_znt', os.path.join(in_feature, "ZoneNilaiTanah.gdb"))
##        else :
##            arcpy.AddMessage('Syarat Upload ZNT Belum Terpenuhi');
    
        return

class Upload_Sampel_NBT(object):


    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Upload Titik Sampel Hasil Validasi NBT"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        param0 = arcpy.Parameter(
            displayName="Username",
            name="username",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param1 = arcpy.Parameter(
            displayName="Password",
            name="password",
            datatype="GPStringHidden",
            parameterType="Required",
            direction="Input")
        param2 = arcpy.Parameter(
            displayName="Nomor Berkas",
            name="project_id",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")
        param3 = arcpy.Parameter(
            displayName="Tahun",
            name="tahun",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        param4 = arcpy.Parameter(
            displayName="User",
            name="user",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param5 = arcpy.Parameter(
            displayName="Nomor Berkas",
            name="kontrak",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")
        param6 = arcpy.Parameter(
            displayName="Workspace",
            name="workspace",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")
        
        param4.filter.type = "ValueList"
        param4.filter.list = ['Swakelola', 'Pihak Ke 3']

        param2.enabled = False
        param3.enabled = False
        param5.enabled = False
        param6.enabled = False

        params = [param4, param0, param1, param2, param5, param3, param6]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        if parameters[0].value and parameters[1].value and parameters[2].value:
            if not parameters[3].value and parameters[0].value == 'Swakelola':
                parameters[4].value = ''
                parameters[5].value = ''
                parameters[6].value = ''
                parameters[4].enabled = False
                parameters[5].enabled = False
                parameters[6].enabled = False
                drpdown = []
                list_project.clear()
                list_kontrak.clear()
                #list_sk.clear()
                url = "https://sipenta.atrbpn.go.id/api/index.php/api_sipenta/get_login_kontrak"

                session = requests.Session()
                response = session.get(url)
                client = requests.session()
                client.get(url)
                if 'tokencsrf' in client.cookies:
                    csrftoken = client.cookies['tokencsrf']
                else:
                    csrftoken = client.cookies['tokencsrf']

                cookies = {'tokencsrf': csrftoken}
                data = {
                    "username": parameters[1].value,
                    "password": parameters[2].value,
                    "tokencsrf": csrftoken}

                x = requests.post(url, cookies=cookies, data=data).text
                y = json.loads(x)
                if y["status"] == 'gagal':
                    arcpy.AddMessage(y["message"])
                    arcpy.AddError(y["status"])
                else:
                    if y["token"] and y["projects"]:
                        for g in y["projects"]:
                            drpdown.append(g["project_id"])

                        for h in y["project"]:
                            list_project[str(h["project_id"])] = h["tahun"]
                            list_kontrak[str(h["project_id"])] = h["kontrak"]
                            #list_sk[str(h["project_id"])] = h["sk"]
                            
                        parameters[3].filter.type = "ValueList"
                        parameters[3].filter.list = drpdown
                        parameters[3].enabled = True
                    else :
                        arcpy.AddMessage('Nomor Berkas Tidak Ditemukan')
                        arcpy.AddError('Nomor Berkas Tidak Ditemukan')
            elif parameters[3].value and parameters[0].value == 'Swakelola':
                thn = parameters[3].valueAsText
                parameters[5].value = list_project[thn]
                parameters[5].enabled = True
                parameters[6].enabled = True
            else:
                if not parameters[6].value and parameters[0].value == 'Pihak Ke 3':
                    parameters[3].filter.type = "ValueList"
                    parameters[3].filter.list = []
                    parameters[3].value = ''
                    parameters[4].value = ''
                    parameters[5].value = ''
                    parameters[6].value = ''
                    parameters[3].enabled = False
                    parameters[4].enabled = False
                    parameters[5].enabled = False
                    parameters[6].enabled = False

                    url = "https://sipenta.atrbpn.go.id/api/index.php/api_sipenta/get_login_mitra"

                    session = requests.Session()
                    response = session.get(url)
                    client = requests.session()
                    client.get(url)
                    if 'tokencsrf' in client.cookies:
                        csrftoken = client.cookies['tokencsrf']
                    else:
                        csrftoken = client.cookies['tokencsrf']

                    cookies = {'tokencsrf': csrftoken}
                    data = {
                        "username": parameters[1].value,
                        "password": parameters[2].value,
                        "tokencsrf": csrftoken}

                    x = requests.post(url, cookies=cookies, data=data).text
                    y = json.loads(x)
                    if y["status"] == 'gagal':
                        arcpy.AddMessage(y["message"])
                        arcpy.AddError(y["status"])
                    else:
                        if y["token"] and y["kontrak"]:
                            list_kontrak[str(y["nomorberkas"])] = y["kontrak"]
                            parameters[4].value = y["nomorberkas"]
                            parameters[4].enabled = True
                            parameters[5].value = y["tahun"]
                            parameters[5].enabled = True
                            parameters[6].enabled = True
                        else :
                            arcpy.AddMessage('Nomor Kontrak Tidak Ditemukan')
                            arcpy.AddError('Nomor Kontrak Tidak Ditemukan')            
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        kondisi = parameters[0].valueAsText
        username = parameters[1].valueAsText
        password = parameters[2].valueAsText
        project_id = ''
        if kondisi == 'Swakelola':
            project_id = parameters[3].valueAsText
        else:
            project_id = parameters[4].valueAsText
        in_feature = parameters[6].valueAsText
        tahun = parameters[5].valueAsText

        main_loop(project_id, "Titik_Sampel_Update", tahun, 'Titik_Sampel_NBT', os.path.join(in_feature, "znt_fgdb.gdb"))
    
        return