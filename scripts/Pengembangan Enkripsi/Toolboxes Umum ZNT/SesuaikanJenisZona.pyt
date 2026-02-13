import arcpy, os, sys
script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)

if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
from zntutils.zona_layer import get_config_values

class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox Sesuaikan Jenis Zona"
        self.alias = "toolbox_sesuaikan_jenis_zona"

        # List of tool classes associated with this toolbox
        self.tools = [Sesuaikan_Jenis_Zona]


class Sesuaikan_Jenis_Zona(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Sesuaikan Jenis Zona"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        jenis_zona = arcpy.Parameter(
            displayName="Jenis Zona",
            name="jenis_zona",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        jenis_zona.filter.type = "ValueList"
        jenis_zona.filter.list = ["Pertanian", "Non-Pertanian"]


        output_zl = arcpy.Parameter(
            name="output_zl",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [jenis_zona, output_zl]


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
        jenis_zona = parameters[0].valueAsText

        config_dan_paths = get_config_values()
        kode_zona = 1
        if jenis_zona == "Non-Pertanian":
            kode_zona = 1
        elif jenis_zona == "Pertanian":
            kode_zona = 2
        zl = "Zona_Layer"
        if not arcpy.Exists(zl):
            arcpy.AddError("ERROR: Masukkan data dasar terlebih dahulu.")
        else:
            ada_seleksi = len(arcpy.Describe(zl).FIDSet)  
            if ada_seleksi > 0:
                try:
                    with arcpy.da.UpdateCursor(zl, ["JNSZN", "PENGGUNAAN"]) as cursor:
                        for row in cursor:
                            row[0] = kode_zona  # Mengupdate kolom JNSZN dengan kode numerik
                            row[1] = jenis_zona       # Mengupdate kolom PENGGUNAAN dengan teks jenis
                            cursor.updateRow(row)  
                except Exception as e:

                    if str(e) == 'Cannot acquire a lock.':
                        arcpy.AddWarning(f'Tutup tabel atribut pada layer Zona_Layer sebelum menjalankan tool ini.')
                    else:
                        arcpy.AddWarning(f"ERROR: Terjadi kesalahan saat mengupdate atribut jenis zona. {e}")
        
                arcpy.CalculateField_management(
                    zl, 
                    "PENGGUNAAN", 
                    f'"{jenis_zona}"', 
                    "PYTHON3", 
                    ""
                )
                sim_path = os.path.join(config_dan_paths['symbology_folder'], "Simbologi_Sesuaikan_Jenis_Zona.lyrx")
                
                arcpy.management.MakeFeatureLayer(config_dan_paths['zl_path'], "Zona_Layer")
                arcpy.management.ApplySymbologyFromLayer("Zona_Layer", sim_path)
                arcpy.SetParameter(1, "Zona_Layer")
            elif ada_seleksi == 0:
                arcpy.AddWarning("Tidak ada fitur yang dipilih pada layer Zona_Layer.")
        return
 