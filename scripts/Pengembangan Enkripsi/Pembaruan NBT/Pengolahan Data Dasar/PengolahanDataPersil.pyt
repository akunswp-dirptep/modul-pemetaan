from datetime import datetime
import json
import sys
import arcpy, os, math

# Tambahkan parent directory ke sys.path
script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
gp_dir = os.path.dirname(parent_dir)
if gp_dir not in sys.path:
    sys.path.insert(0, gp_dir)

from nbtutils import constant, persil


class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [Identifikasi_Perubahan_Persil, 
                    Periksa_Perubahan_Persil,
                      Sesuaikan_Status_Perubahan_Persil,
                      Menentukan_Perubahan_Mengelompok,
                      Reset_Perubahan_Mengelompok,
                      Simpan_Perubahan_Ke_Persil_Layer,
                      Update_Luas_Tanah,
                      Analisis_Bentuk_Persil,
                      Edit_Bentuk_Persil,
                      Simpan_Bentuk_Persil,
                      Tampilkan_Simbologi_Persil,
                      Sinkronkan_Indikator_Persil,
                      Analisis_Bentuk_Persil_File,
                      Simpan_Perubahan_Ke_Persil_Baru,
                      Generate_Peta_Akhir,
                      ]


class Identifikasi_Perubahan_Persil(object):
    def __init__(self):
        self.label="Tes Identifikasi Perubahan Persil"
        self.description=""
        self.canRunInBackground=False

    def getParameterInfo(self):
        peta_baru=arcpy.Parameter(
            displayName="Persil Baru",
            name="peta_baru",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")

        output_baru=arcpy.Parameter(
            displayName="Output Peta Baru",
            name="output_baru",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        output_indikator=arcpy.Parameter(
            displayName="Output Indikator",
            name="output_indikator",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return[peta_baru, output_baru, output_indikator]

    def isLicensed(self):
        return True

    def updateParameters(self,parameters):
        return

    def updateMessages(self,parameters):
        return

    def delete_if_exists(self,path):
        if arcpy.Exists(path):
            try:
                arcpy.management.Delete(path)
            except Exception as e:
                arcpy.AddWarning(str(e))

    def bersihkan_field(self,fc,allowed_fields):
        protected_fields={"FID"}
        protected_fields.update(allowed_fields)

        for field in arcpy.ListFields(fc):
            field_name=field.name

            is_protected=(
                field.type in["Geometry","OID"]
                or "shape" in field_name.lower()
                or field_name in protected_fields
            )

            if not is_protected:
                try:
                    arcpy.management.DeleteField(fc,field_name)
                except Exception as e:
                    arcpy.AddWarning(str(e))

    def calculate_area_field(self,fc,field_name="ls_asal"):
        field_names=[f.name for f in arcpy.ListFields(fc)]

        if field_name not in field_names:
            arcpy.management.AddField(fc,field_name,"DOUBLE")

        arcpy.management.CalculateField(fc,field_name,"!shape.area!","PYTHON3")

    def extract_changed_features(self,source_fc,compare_fc,layer_name,output_fc):
        self.delete_if_exists(layer_name)
        self.delete_if_exists(output_fc)

        arcpy.management.MakeFeatureLayer(source_fc,layer_name)

        arcpy.management.SelectLayerByLocation(
            layer_name,
            "CONTAINS",
            compare_fc,
            selection_type="NEW_SELECTION",
            invert_spatial_relationship="INVERT"
        )

        arcpy.management.CopyFeatures(layer_name,output_fc)

    def set_default_value(self, fc, field_name, value, field_type="TEXT", field_alias=None):
        field_names=[f.name for f in arcpy.ListFields(fc)]

        if field_name not in field_names:
            arcpy.management.AddField(fc,field_name,field_type, field_alias = field_alias)

        arcpy.management.CalculateField(fc,field_name,f'"{value}"',"PYTHON3")

    def save_layer(self,source_fc,dataset_path,output_name):

        sim_path = ''
        if output_name == "Persil_Baru":
            sim_path = r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Simbologi_Persil_Baru_Layer.lyrx"
        else:
            sim_path = r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Simbologi_Indikator_Perubahan_Persil_Layer.lyrx"
        if not os.path.exists(sim_path):
            arcpy.AddWarning(f"File simbolik {sim_path} tidak ditemukan. Simbologi tidak akan diterapkan.")
        else:
            arcpy.AddMessage(f"File simbolik {sim_path} ditemukan. Simbologi akan diterapkan.")
        output_path=os.path.join(dataset_path, output_name)

        self.delete_if_exists(output_path)

        arcpy.management.CopyFeatures(source_fc,output_path)

        return output_name, output_path, sim_path

    def execute(self,parameters,messages):
        messages.addMessage("== Proses dimulai ==")

        configs=persil.get_config_values()

        dataset_path=configs["project_config"]["dataset_path"]

        konfigurasi_variabel_path=configs["project_config"]["daftar_variabel_path"]

        peta_baru_input=parameters[0].valueAsText

        peta_lama_input=os.path.join(dataset_path,"Persil_Layer")

        if not arcpy.Exists(peta_lama_input):
            messages.addErrorMessage("Persil_Lama belum tersedia")
            raise arcpy.ExecuteError

        fields_dont_delete=[]

        if os.path.exists(konfigurasi_variabel_path):
            with open(konfigurasi_variabel_path,"r") as conf_file:
                json_variabel=json.load(conf_file)
            daftar_variabel=json_variabel.get("daftar_variabel",[])
            for row in daftar_variabel:
                if len(row)<2:
                    continue
                akronim=row[1]
                if akronim and akronim!="None":
                    fields_dont_delete.append(akronim)


        dest_lama_path=r"in_memory\PersilPetaLama"
        dest_baru_path=r"in_memory\PersilPetaBaru"
        temp_lama_path=r"in_memory\Peta_Temp_Lama"
        temp_baru_path=r"in_memory\Peta_Temp_Baru"
        indikator_temp=r"in_memory\Indikator_Perubahan"

        memory_layers=[
            dest_lama_path,
            dest_baru_path,
            temp_lama_path,
            temp_baru_path,
            indikator_temp,
            "PetaLamaLayer_Temp",
            "PetaBaruLayer_Temp"
        ]


        for lyr in memory_layers:
            self.delete_if_exists(lyr)

        arcpy.management.CopyFeatures(peta_lama_input, dest_lama_path)
        arcpy.management.CopyFeatures(peta_baru_input, dest_baru_path)

        self.bersihkan_field(dest_lama_path, fields_dont_delete)

        self.bersihkan_field(dest_baru_path,fields_dont_delete)

        self.calculate_area_field(dest_lama_path)

        self.calculate_area_field(dest_baru_path)

        self.extract_changed_features(dest_lama_path,dest_baru_path,"PetaLamaLayer_Temp",temp_lama_path)

        self.extract_changed_features(dest_baru_path,dest_lama_path,"PetaBaruLayer_Temp",temp_baru_path)

        arcpy.management.Merge([temp_baru_path,temp_lama_path],indikator_temp)

        self.set_default_value(indikator_temp,"indikator_perubahan","Indikator Periksa", field_alias="Indikator Perubahan")
        self.set_default_value(indikator_temp, 'kelompok_perubahan', None, 'SHORT', 'Kelompok Perubahan')
        self.set_default_value(indikator_temp, 'klaster_zona', None, 'SHORT', 'Klaster Zona')

        f_lyr_name, lyr_path, sim_lyr_path =self.save_layer(dest_baru_path, dataset_path,"Persil_Baru")
        arcpy.management.MakeFeatureLayer(lyr_path, f_lyr_name)
        arcpy.management.ApplySymbologyFromLayer(f_lyr_name, sim_lyr_path)
        arcpy.SetParameter(1, f_lyr_name)
        
        s_lyr_name, lyr_path, sim_lyr_path =self.save_layer(indikator_temp, dataset_path,"Indikator_Perubahan_Persil")
        arcpy.management.MakeFeatureLayer(lyr_path, s_lyr_name)
        arcpy.management.ApplySymbologyFromLayer(s_lyr_name, sim_lyr_path)
        arcpy.SetParameter(2, s_lyr_name)

        

        return

class Tampilkan_Simbologi_Persil(object):
    """Tool untuk menampilkan simbologi pada layer Persil"""
    def __init__(self):
        self.label = "Tampilkan Simbologi Layer Identifikasi"
        self.description = "Tool untuk menampilkan simbologi "

        self.canRunInBackground = False

    def getParameterInfo(self):
        """Mendefinisikan parameter input tool"""
        penjelasan = arcpy.Parameter(
            displayName="Apa yang dilakukan tool ini?",
            name="penjelasan",
            datatype="GPString",    
            parameterType="Optional",
            direction="Input")
        
        penjelasan.value = (
            "Tool ini digunakan untuk menampilkan simbologi pada\n"
            "layer Persil.\n\n"
            "Direktorat Penilaian Tanah & Ekonomi Pertanahan\n"
            "Kementerian ATR/BPN\n"
            "Tahun: {}".format(datetime.now().year)
        )
        
        output_ts = arcpy.Parameter(
            name="Persil_Layer",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        output_tsi = arcpy.Parameter(
            name="Persil_Indikator_Layer",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )
        return [penjelasan, output_ts, output_tsi]

    def isLicensed(self):
        """Validasi lisensi ArcGIS"""
        return True

    def updateParameters(self, parameters):
        """Update parameter dynamically"""
        return

    def updateMessages(self, parameters):
        """Validasi dan update messages"""
        return

    def execute(self, parameters, messages):
        """Eksekusi utama tool untuk menampilkan simbologi pada layer Persil"""
        config_paths = persil.get_config_values()

        dataset_path = config_paths['project_config']['dataset_path']
        
        persil_path = os.path.join(dataset_path, 'Persil_Baru')
        sim_path = r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Simbologi_Persil_Baru_Layer.lyrx"
        indi_path = os.path.join(dataset_path, 'Indikator_Perubahan_Persil')
        sim_indi_path = r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Simbologi_Indikator_Perubahan_Persil_Layer.lyrx"

        arcpy.management.MakeFeatureLayer(persil_path, 'Persil_Baru')
        arcpy.management.ApplySymbologyFromLayer('Persil_Baru', sim_path)

        if arcpy.Exists(indi_path):
            arcpy.management.MakeFeatureLayer(indi_path, 'Indikator_Perubahan_Persil')
            arcpy.management.ApplySymbologyFromLayer('Indikator_Perubahan_Persil', sim_indi_path)

        arcpy.SetParameter(1, 'Persil_Baru')
        arcpy.SetParameter(2, 'Indikator_Perubahan_Persil' if arcpy.Exists(indi_path) else None)

class Periksa_Perubahan_Persil(object):
    def __init__(self):
        self.label="Periksa Perubahan Persil"
        self.description=""
        self.canRunInBackground=False

    def getParameterInfo(self):
        radius=arcpy.Parameter(
            displayName="Radius Toleransi Perubahan (m)",
            name="radius",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input"
        )

        radius.value=5.0

        output_layer=arcpy.Parameter(
            displayName="Output Layer",
            name="output_layer",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return[ radius, output_layer]

    def isLicensed(self):
        return True

    def updateParameters(self,parameters):
        return

    def updateMessages(self,parameters):
        return

    def execute(self,parameters,messages):
        messages.addMessage("== Proses dimulai ==")

        configs=persil.get_config_values()

        dataset_path=configs["project_config"]["dataset_path"]

        appdata=os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

        radius=parameters[0].value

        toleransi_m2=math.pi*(radius**2)

        peta_baru="Persil_Baru"
        peta_lama="Persil_Layer"
        peta_indikator="Indikator_Perubahan_Persil"

        peta_indikator_path=os.path.join(dataset_path,peta_indikator)

        peta_indikator_update_path=r"in_memory\Peta_Indikator_Update"
        peta_indikator_lama_path=r"in_memory\Peta_Indikator_Lama"
        peta_indikator_akhir_path=r"in_memory\Indikator_Akhir"

        peta_update_path=os.path.join(dataset_path,peta_baru)
        peta_lama_path=os.path.join(dataset_path,peta_lama)

        memory_layers=[
            peta_indikator_update_path,
            peta_indikator_lama_path,
            peta_indikator_akhir_path
        ]

        for lyr in memory_layers:
            if arcpy.Exists(lyr):
                try:
                    arcpy.management.Delete(lyr)
                except:
                    pass

        messages.addMessage("== Join dengan Persil Update ==")

        arcpy.analysis.SpatialJoin(
            peta_indikator_path,
            peta_update_path,
            peta_indikator_update_path,
            "JOIN_ONE_TO_ONE",
            "KEEP_ALL",
            "OBJECTID \"OBJECTID\" true true false 9 Long 0 9 ,First,#,"+
            peta_indikator_path+",OBJECTID,-1,-1;"+
            
            "NIB \"NIB\" true true false 5 Long 0 0 ,First,#,"+
            peta_indikator_path+",NIB,-1,-1;"+
            
            "IdBidang \"IdBidang\" true true false 9 Long 0 9 ,First,#,"+
            peta_indikator_path+",IdBidang,-1,-1;"+
            
            "Predicted \"Predicted\" true true false 19 Double 0 0 ,First,#,"+
            peta_indikator_path+",Predicted,-1,-1;"+
            
            "Shape_Area \"Shape_Area\" true true false 19 Double 0 0 ,First,#,"+
            peta_indikator_path+",Shape_Area,-1,-1;"+
            
            "ls_asal \"ls_asal\" true true false 19 Double 0 0 ,First,#,"+
            peta_indikator_path+",ls_asal,-1,-1;"+
            
            "ls_tnh \"ls_tnh\" true true false 19 Double 0 0 ,First,#,"+
            peta_indikator_path+",ls_tnh,-1,-1;"+
            
            "indikator_perubahan \"indikator_perubahan\" true true false 254 Text 0 0 ,First,#,"+
            peta_indikator_path+",indikator_perubahan,-1,-1;"+
            
            "ls_dr_baru \"ls_dr_baru\" true true false 50 Double 0 0 ,First,#,"+
            peta_update_path+",ls_asal,-1,-1;"+
            
            "kelompok_perubahan \"kelompok_perubahan\" true true false 2 Short 0 0 ,Max,#,"+
            peta_update_path+",kelompok_perubahan,-1,-1;"+
            
            "klaster_zona \"klaster_zona\" true true false 2 Short 0 0 ,Max,#,"+
            peta_update_path+",klaster_zona,-1,-1",
            
            "INTERSECT",
            "",
            ""
        )

        list_field_update=[f.name for f in arcpy.ListFields(peta_indikator_update_path)]

        if "sts_persil" not in list_field_update:
            arcpy.management.AddField(peta_indikator_update_path,"sts_persil","TEXT")

        if "selisih_ba" not in list_field_update:
            arcpy.management.AddField(peta_indikator_update_path,"selisih_ba","DOUBLE")

        exp="myabs(!ls_asal!, !ls_dr_baru!)"

        code_block="""import math
def myabs(asal,baru):
    if asal is None:
        asal=0
    if baru is None:
        baru=0
    return math.fabs(asal-baru)
"""

        arcpy.management.CalculateField(
            peta_indikator_update_path,
            "selisih_ba",
            exp,
            "PYTHON3",
            code_block
        )

        exp=f"get(!selisih_ba!, {toleransi_m2})"

        code_block="""def get(b,toleransi):
    if b>toleransi:
        return 'update'
    else:
        return 'tetap'
"""

        arcpy.management.CalculateField(
            peta_indikator_update_path,
            "sts_persil",
            exp,
            "PYTHON3",
            code_block
        )

        messages.addMessage("== Join dengan Persil Lama ==")

        arcpy.analysis.SpatialJoin(
            peta_indikator_path,
            peta_lama_path,
            peta_indikator_lama_path,
            "JOIN_ONE_TO_ONE",
            "KEEP_ALL",
            
            "OBJECTID \"OBJECTID\" true true false 9 Long 0 9 ,First,#,"+
            peta_indikator_path+",OBJECTID,-1,-1;"+
            
            "NIB \"NIB\" true true false 5 Long 0 0 ,First,#,"+
            peta_indikator_path+",NIB,-1,-1;"+
            
            "IdBidang \"IdBidang\" true true false 9 Long 0 9 ,First,#,"+
            peta_indikator_path+",IdBidang,-1,-1;"+
            
            "Predicted \"Predicted\" true true false 19 Double 0 0 ,First,#,"+
            peta_indikator_path+",Predicted,-1,-1;"+
            
            "Shape_Area \"Shape_Area\" true true false 19 Double 0 0 ,First,#,"+
            peta_indikator_path+",Shape_Area,-1,-1;"+
            
            "ls_asal \"ls_asal\" true true false 19 Double 0 0 ,First,#,"+
            peta_indikator_path+",ls_asal,-1,-1;"+
            
            "ls_tnh \"ls_tnh\" true true false 19 Double 0 0 ,First,#,"+
            peta_indikator_path+",ls_tnh,-1,-1;"+
            
            "indikator_perubahan \"indikator_perubahan\" true true false 254 Text 0 0 ,First,#,"+
            peta_indikator_path+",indikator_perubahan,-1,-1;"+
            
            "ls_dr_lama \"ls_dr_lama\" true true false 50 Double 0 0 ,First,#,"+
            peta_lama_path+",ls_asal,-1,-1;"+
            
            "kelompok_perubahan \"kelompok_perubahan\" true true false 2 Short 0 0 ,Max,#,"+
            peta_lama_path+",kelompok_perubahan,-1,-1;"+
            
            "klaster_zona \"klaster_zona\" true true false 2 Short 0 0 ,Max,#,"+
            peta_lama_path+",klaster_zona,-1,-1",
            
            "INTERSECT",
            "",
            ""
        )

        list_field_lama=[f.name for f in arcpy.ListFields(peta_indikator_lama_path)]

        if "sts_persil" not in list_field_lama:
            arcpy.management.AddField(peta_indikator_lama_path,"sts_persil","TEXT")

        if "selisih_ba" not in list_field_lama:
            arcpy.management.AddField(peta_indikator_lama_path,"selisih_ba","DOUBLE")

        exp="myabs(!ls_asal!, !ls_dr_lama!)"

        code_block="""
import math
def myabs(asal,lama):
    if asal is None:
        asal=0
    if lama is None:
        lama=asal
    return math.fabs(asal-lama)
"""

        arcpy.management.CalculateField(
            peta_indikator_lama_path,
            "selisih_ba",
            exp,
            "PYTHON3",
            code_block
        )

        exp=f"get(!selisih_ba!, {toleransi_m2})"

        code_block="""
def get(b,toleransi):
    if b>toleransi:
        return 'update'
    else:
        return 'tetap'
"""

        arcpy.management.CalculateField(
            peta_indikator_lama_path,
            "sts_persil",
            exp,
            "PYTHON3",
            code_block
        )

        messages.addMessage("== Join dengan Persil Lama dan Update ==")

        fields=arcpy.ListFields(peta_indikator_lama_path,"cluster","SHORT")

        if len(fields)==0:
            arcpy.management.AddField(peta_indikator_lama_path,"cluster","SHORT")

        arcpy.analysis.SpatialJoin(
            peta_indikator_lama_path,
            peta_indikator_update_path,
            peta_indikator_akhir_path,
            "JOIN_ONE_TO_ONE",
            "KEEP_COMMON",

            "NIB \"NIB\" true true false 5 Long 0 0 ,First,#,"+
            peta_indikator_lama_path+",NIB,-1,-1;"+

            "IdBidang \"IdBidang\" true true false 9 Long 0 9 ,First,#,"+
            peta_indikator_lama_path+",IdBidang,-1,-1;"+

            "ls_asal \"ls_asal\" true true false 19 Double 0 0 ,First,#,"+
            peta_indikator_lama_path+",ls_asal,-1,-1;"+

            "indikator_perubahan \"indikator_perubahan\" true true false 254 Text 0 0 ,First,#,"+
            peta_indikator_lama_path+",indikator_perubahan,-1,-1;"+

            "ls_dr_lama \"ls_dr_lama\" true true false 19 Double 0 0 ,First,#,"+
            peta_lama_path+",ls_asal,-1,-1;"+

            "sts_per_la \"sts_per_la\" true true false 254 Text 0 0 ,First,#,"+
            peta_indikator_lama_path+",sts_persil,-1,-1;"+

            "selisih_la \"selisih_la\" true true false 19 Double 0 0 ,First,#,"+
            peta_indikator_lama_path+",selisih_ba,-1,-1;"+

            "ls_dr_baru \"ls_dr_baru\" true true false 50 Double 0 0 ,First,#,"+
            peta_indikator_update_path+",ls_dr_baru,-1,-1;"+

            "sts_per_ba \"sts_per_ba\" true true false 50 Text 0 0 ,First,#,"+
            peta_indikator_update_path+",sts_persil,-1,-1;"+

            "selisih_up \"selisih_up\" true true false 50 Double 0 0 ,First,#,"+
            peta_indikator_update_path+",selisih_ba,-1,-1;"+

            "kelompok_perubahan \"kelompok_perubahan\" true true false 2 Short 0 0 ,Max,#,"+
            peta_indikator_update_path+",kelompok_perubahan,-1,-1;"+

            "klaster_zona \"klaster_zona\" true true false 2 Short 0 0 ,Max,#,"+
            peta_indikator_update_path+",klaster_zona,-1,-1",

            "WITHIN",
            "",
            ""
        )

        list_field_akhir=[f.name for f in arcpy.ListFields(peta_indikator_akhir_path)]

        if "status_per" not in list_field_akhir:
            arcpy.management.AddField(peta_indikator_akhir_path,"status_per","TEXT")

        exp="get(!sts_per_la!, !sts_per_ba!)"

        code_block="""
def get(a,b):
    if a=='tetap' and b=='tetap':
        return 'tetap'
    else:
        return 'update'
"""

        arcpy.management.CalculateField(
            peta_indikator_akhir_path,
            "status_per",
            exp,
            "PYTHON3",
            code_block
        )

        arcpy.management.DeleteField(
            peta_indikator_akhir_path,
            [
                "ls_dr_lama",
                "sts_per_la",
                "selisih_la",
                "ls_dr_baru",
                "sts_per_ba",
                "selisih_up",
                "cluster"
            ]
        )

        if arcpy.Exists(peta_indikator_path):
            try:
                arcpy.management.Delete(peta_indikator_path)
            except:
                pass

        arcpy.management.CopyFeatures(peta_indikator_akhir_path,peta_indikator_path)

        sim_indikator_akhir=os.path.join(appdata,"Simbologi_Persil_Updating_Final.lyr")

        if arcpy.Exists("Indikator_Perubahan_Persil"):
            try:
                arcpy.management.Delete("Indikator_Perubahan_Persil")
            except:
                pass

        arcpy.management.MakeFeatureLayer(peta_indikator_path,"Indikator_Perubahan_Persil")

        if os.path.exists(sim_indikator_akhir):
            arcpy.management.ApplySymbologyFromLayer("Indikator_Perubahan_Persil",sim_indikator_akhir)

        parameters[1].value="Indikator_Perubahan_Persil"

        messages.addMessage("== Proses selesai ==")

        return

class Sesuaikan_Status_Perubahan_Persil(object):

    def __init__(self):
        self.label="Sesuaikan Status Perubahan Persil"
        self.description=""
        self.canRunInBackground=False

    def getParameterInfo(self):

        status_perubahan=arcpy.Parameter(
            displayName="Status Perubahan",
            name="status_perubahan",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )

        output_layer=arcpy.Parameter(
            displayName="Output Layer",
            name="output_layer",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output")

        status_perubahan.filter.list=["tetap","update"]

        return[status_perubahan, output_layer]

    def isLicensed(self):
        return True

    def updateParameters(self,parameters):
        return

    def updateMessages(self,parameters):
        return

    def execute(self,parameters,messages):

        arcpy.env.overwriteOutput=True

        messages.addMessage("== Proses dimulai ==")

        val=parameters[0].valueAsText

        configs=persil.get_config_values()

        dataset_path=configs["project_config"]["dataset_path"]

        layer_indikator=os.path.join(dataset_path,"Indikator_Perubahan_Persil")

        if not arcpy.Exists(layer_indikator):
            messages.addErrorMessage("== Layer Indikator_Perubahan_Persil tidak ditemukan ==")
            raise arcpy.ExecuteError

        fields=[f.name for f in arcpy.ListFields(layer_indikator)]

        if "status_per" not in fields:
            messages.addErrorMessage("== Field status_per tidak ditemukan ==")
            raise arcpy.ExecuteError

        selected_count=int(
            arcpy.management.GetCount(
                "Indikator_Perubahan_Persil"
            )[0]
        )

        if selected_count==0:
            messages.addErrorMessage("== Tidak ada fitur yang dipilih ==")
            raise arcpy.ExecuteError

        messages.addMessage("== Mengupdate status perubahan persil ==")

        with arcpy.da.UpdateCursor(
            "Indikator_Perubahan_Persil",
            ["status_per"]
        ) as cursor:

            for row in cursor:
                row[0]=val
                cursor.updateRow(row)
        
        del cursor
        arcpy.SetParameter(1, "Indikator_Perubahan_Persil")

        messages.addMessage(f"== {selected_count} fitur berhasil diperbarui ==")

        messages.addMessage("== Proses selesai ==")

        return   

# Bag 2
class Menentukan_Perubahan_Mengelompok(object):

    def __init__(self):
        self.label="Menentukan Perubahan Mengelompok"
        self.description=""
        self.canRunInBackground=False

    def getParameterInfo(self):

        param_cluster=arcpy.Parameter(
            displayName="Nomor Kelompok",
            name="cluster_update",
            datatype="GPLong",
            parameterType="Required",
            direction="Input"
        )

        output_layer=arcpy.Parameter(
            displayName="Output Persil",
            name="output_layer",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return[param_cluster, output_layer]

    def isLicensed(self):
        return True

    def updateParameters(self,parameters):
        return

    def updateMessages(self,parameters):
        return

    def delete_if_exists(self,path):
        if arcpy.Exists(path):
            try:
                arcpy.management.Delete(path)
            except Exception:
                pass

    def add_field_if_not_exists(self,feature_class,field_name,field_type,field_alias=None):
        field_names=[field.name for field in arcpy.ListFields(feature_class)]

        if field_name not in field_names:
            arcpy.management.AddField(feature_class,field_name,field_type, field_alias=field_alias)

    def execute(self,parameters,messages):
        messages.addMessage("== Proses dimulai ==")
        cluster_update=int(parameters[0].value)
        configs=persil.get_config_values()
        dataset_path=configs["project_config"]["dataset_path"]

        persil_name="Indikator_Perubahan_Persil"
        persil_path=os.path.join(dataset_path,persil_name)

        if not arcpy.Exists(persil_path):
            messages.addErrorMessage("Feature class Indikator_Perubahan_Persil tidak ditemukan")
            raise arcpy.ExecuteError

        selected_count=len(arcpy.Describe(persil_name).FIDSet)

        if selected_count<=0:
            messages.addWarningMessage("Tidak ada fitur yang dipilih")
            return

        self.add_field_if_not_exists(
            persil_path,
            'kelompok_perubahan',
            "SHORT",
            'Kelompok Perubahan'
        )

        messages.addMessage(f"== Update Kelompok Perubahan {cluster_update} ==")

        updated_count=0

        with arcpy.da.UpdateCursor( persil_name, ["kelompok_perubahan"]) as cursor:

            for row in cursor:
                row[0]=cluster_update
                cursor.updateRow(row)
                updated_count+=1
        
        del cursor

        messages.addMessage(f"{updated_count} fitur berhasil diupdate")
        arcpy.SetParameter(1, persil_name)

        messages.addMessage("== Proses selesai ==")

        return
    
class Reset_Perubahan_Mengelompok(object):

    def __init__(self):
        self.label="Reset Perubahan Mengelompok"
        self.description=""
        self.canRunInBackground=False

    def getParameterInfo(self):

        output_layer=arcpy.Parameter(
            displayName="Output Persil",
            name="output_layer",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return[output_layer]

    def isLicensed(self):
        return True

    def updateParameters(self,parameters):
        return

    def updateMessages(self,parameters):
        return

    def delete_if_exists(self,path):
        if arcpy.Exists(path):
            try:
                arcpy.management.Delete(path)
            except Exception:
                pass

    def execute(self,parameters,messages):

        messages.addMessage("== Proses dimulai ==")
        configs=persil.get_config_values()
        dataset_path=configs["project_config"]["dataset_path"]
        appdata=os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        persil_name="Indikator_Perubahan_Persil"
        persil_path=os.path.join(dataset_path,persil_name)

        if not arcpy.Exists(persil_path):
            messages.addErrorMessage("Feature class Indikator_Perubahan_Persil tidak ditemukan")
            raise arcpy.ExecuteError

        selected_count=len(arcpy.Describe(persil_name).FIDSet)

        if selected_count<=0:
            messages.addWarningMessage("Tidak ada fitur yang dipilih")
            return

        field_names=[field.name for field in arcpy.ListFields(persil_path)]

        if "kelompok_perubahan" not in field_names:
            messages.addWarningMessage("Field kelompok_perubahan tidak ditemukan")
            return

        messages.addMessage("== Reset Kelompok Perubahan ==")

        updated_count=0

        with arcpy.da.UpdateCursor(
            persil_name,
            ["kelompok_perubahan"]
        ) as cursor:

            for row in cursor:
                row[0]=None
                cursor.updateRow(row)
                updated_count+=1

        messages.addMessage(f"{updated_count} fitur berhasil direset")

        arcpy.SetParameter(0, persil_name)

        messages.addMessage("== Proses selesai ==")

        return

class Simpan_Perubahan_Ke_Persil_Layer(object):

    def __init__(self):
        self.label="Simpan Perubahan Ke Persil Layer"
        self.description=""
        self.canRunInBackground=False

    def getParameterInfo(self):

        simpan_ke_persil = arcpy.Parameter(
            displayName="Simpan Perubahan Ke Layer Sementara",
            name="simpan_ke_persil",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )

        simpan_ke_persil.value = False

        output_layer = arcpy.Parameter(
            displayName="Output Peta Persil",
            name="output_persil",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [
            simpan_ke_persil,
            output_layer
        ]

    def isLicensed(self):
        return True

    def updateParameters(self,parameters):
        return

    def updateMessages(self,parameters):
        return

    def delete_if_exists(self,path):
        if arcpy.Exists(path):
            try:
                arcpy.management.Delete(path)
            except Exception:
                pass

    def add_field_if_not_exists(self,feature_class,field_name,field_type,precision=None):

        fields=[field.name for field in arcpy.ListFields(feature_class)]

        if field_name not in fields:

            if precision:
                arcpy.management.AddField(
                    feature_class,
                    field_name,
                    field_type,
                    field_precision=precision
                )

            else:
                arcpy.management.AddField(
                    feature_class,
                    field_name,
                    field_type
                )

    def execute(self,parameters,messages):

        messages.addMessage("== Proses dimulai ==")
        simpan_ke_layer = parameters[0].value
        configs=persil.get_config_values()
        dataset_path=configs["project_config"]["dataset_path"]
        peta_baru_path=os.path.join(dataset_path,"Persil_Baru")
        indikator_path=os.path.join(dataset_path,"Indikator_Perubahan_Persil")
        peta_persil_path=os.path.join('in_memory',"Peta_Persil")
        peta_persil="Peta_Persil"
        required_fc=[ peta_baru_path, indikator_path ]

        for fc in required_fc:
            if not arcpy.Exists(fc):
                messages.addErrorMessage(f"Feature class {os.path.basename(fc)} tidak ditemukan")
                raise arcpy.ExecuteError

        if arcpy.Exists(peta_persil_path):
            arcpy.management.Delete(peta_persil_path)

        self.delete_if_exists(peta_persil_path)
        self.delete_if_exists(peta_persil)

        messages.addMessage("== Spatial Join Persil ==")
        field_mapping=(
            f'NIB "NIB" true true false 5 Long 0 0,First,#,{peta_baru_path},NIB,-1,-1;'
            f'IdBidang "IdBidang" true true false 9 Long 0 9,First,#,{peta_baru_path},IdBidang,-1,-1;'
            f'ls_asal "ls_asal" true true false 19 Double 0 0,First,#,{peta_baru_path},ls_asal,-1,-1;'
            f'status_per "status_per" true true false 50 Text 0 0,First,#,{indikator_path},status_per,-1,-1;'
            f'kelompok_perubahan "kelompok_perubahan" true true false 2 Short 0 0,First,#,{indikator_path},kelompok_perubahan,-1,-1'
        )
        arcpy.analysis.SpatialJoin(
            peta_baru_path,
            indikator_path,
            peta_persil_path,
            "JOIN_ONE_TO_ONE",
            "KEEP_ALL",
            field_mapping,
            "CONTAINS"
        )

        self.add_field_if_not_exists(
            peta_persil_path,
            "PREDICTED",
            "DOUBLE",
            2
        )

        messages.addMessage("== Copy field PREDICTED ==")
        predicted_dict={}
        with arcpy.da.SearchCursor(
            peta_baru_path,
            ["IdBidang","PREDICTED"]
        ) as rows:
            for row in rows:
                predicted_dict[row[0]]=row[1]
        with arcpy.da.UpdateCursor(
            peta_persil_path,
            ["IdBidang","PREDICTED","status_per"]
        ) as rows:
            for row in rows:
                bidang_id=row[0]
                if bidang_id in predicted_dict:
                    row[1]=predicted_dict[bidang_id]
                if row[2]=="update":
                    row[1]=None
                rows.updateRow(row)

        messages.addMessage("== Update status default ==")

        with arcpy.da.UpdateCursor(
            peta_persil_path,
            ["status_per","IdBidang","OBJECTID"]
        ) as rows:

            for row in rows:

                if not row[0]:
                    row[0]="tetap"
                    row[1]=row[2]

                    rows.updateRow(row)

        self.delete_if_exists(peta_persil)

        arcpy.management.MakeFeatureLayer(
            peta_persil_path,
            peta_persil
        )


        messages.addMessage(  "== Proses dimulai ==" )

        configs = persil.get_config_values()
        dataset_path =  configs["project_config"]["dataset_path"]
        daftar_variabel_path = configs["project_config"]["daftar_variabel_path"]

        with open(daftar_variabel_path, "r") as f:

            json_conf = (json.load(f))
            variable_config = json_conf['daftar_variabel']

        field_str_type = [
            "bentuk",
            "letak",
            "kls_jln",
            "elvasi",
            "zonasi"
        ]

        fields_dont_delete = []

        for item in variable_config:

            # Extract field_name from list format [display_name, field_name]
            field_name = ( item[1]   if isinstance(item, list) and len(item) > 1  else None )

            if not field_name:
                continue

            fields_dont_delete.append( field_name )

            if ( field_name.lower()  in field_str_type ):

                fields_dont_delete.append( f"s_{field_name}" )

        peta_persil_path = os.path.join( 'in_memory',  "Peta_Persil" )

        peta_lama_path = os.path.join( dataset_path,  "Persil_Layer" )

        centroid_path = os.path.join( 'in_memory', "Persil_Lama_Centroid" )

        erase_path = os.path.join( 'in_memory',  "Peta_Erase" )

        peta_akhir_path = os.path.join( dataset_path,  "Persil_Layer_Temp")

        peta_akhir_layer = "Peta_Layer_Temp"

        # =================================================
        # VALIDASI
        # =================================================

        required_fc = [
            peta_persil_path,
            peta_lama_path
        ]

        for fc in required_fc:

            if not arcpy.Exists(fc):

                messages.addErrorMessage(
                    (
                        f"Feature class "
                        f"{os.path.basename(fc)} "
                        f"tidak ditemukan"
                    )
                )

                raise arcpy.ExecuteError

        # =================================================
        # CLEANUP
        # =================================================

        cleanup_items = [
            centroid_path,
            erase_path,
            peta_akhir_path,
            peta_akhir_layer
        ]

        for item in cleanup_items:

            self.delete_if_exists(
                item
            )

        arcpy.management.FeatureToPoint(
            peta_lama_path,
            centroid_path,
            "INSIDE"
        )

        # =================================================
        # SELECT UPDATE
        # =================================================

        temp_persil = (
            "temp_persil"
        )

        self.delete_if_exists(
            temp_persil
        )

        arcpy.management.MakeFeatureLayer(
            peta_persil_path,
            temp_persil
        )

        arcpy.management.SelectLayerByAttribute(
            temp_persil,
            "NEW_SELECTION",
            "status_per = 'update'"
        )

        # =================================================
        # ERASE
        # =================================================

        messages.addMessage(
            "== Erase centroid =="
        )

        arcpy.analysis.Erase(
            centroid_path,
            temp_persil,
            erase_path
        )

        # =================================================
        # SPATIAL JOIN
        # =================================================

        messages.addMessage(
            "== Spatial Join =="
        )

        arcpy.analysis.SpatialJoin(
            peta_persil_path,
            erase_path,
            peta_akhir_path,
            "JOIN_ONE_TO_ONE",
            "KEEP_ALL",
            "",
            "INTERSECT"
        )

        #  Hapus Field Gabungan

        join_delete_fields = []

        fields = arcpy.ListFields( peta_akhir_path )

        for field in fields:

            if (field.name.lower().startswith( "join_")  or
                field.name.lower().startswith("target_")
            ):

                join_delete_fields.append(field.name)

        if join_delete_fields:

            arcpy.management.DeleteField(
                peta_akhir_path,
                join_delete_fields
            )
        
        if simpan_ke_layer:
            self.delete_if_exists(
            peta_akhir_layer
            )

            arcpy.management.MakeFeatureLayer(
                peta_akhir_path,
                peta_akhir_layer
            )

            arcpy.SetParameter(1, peta_akhir_layer)
        else:
            persil_path = os.path.join(dataset_path,"Persil_Layer")
            if arcpy.Exists(persil_path):
                arcpy.management.Delete(persil_path)

            arcpy.management.CopyFeatures(
                peta_akhir_path,
                persil_path,
            )
            arcpy.SetParameter(1, "Persil_Layer")
    

        self.delete_if_exists(
            temp_persil
        )
        return
 


class Update_Luas_Tanah(object):

    def __init__(self):
        self.label="Update Luas Tanah"
        self.description=""
        self.canRunInBackground=False

    def getParameterInfo(self):

        output_layer=arcpy.Parameter(
            displayName="Output Peta Akhir",
            name="output_peta_akhir",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return[output_layer]

    def isLicensed(self):
        return True

    def updateParameters(self,parameters):
        return

    def updateMessages(self,parameters):
        return

    def delete_if_exists(self,path):

        if arcpy.Exists(path):

            try:
                arcpy.management.Delete(path)

            except Exception:
                pass

    def add_field_if_not_exists(self,feature_class,field_name,field_type):

        fields=[
            field.name.lower()
            for field in arcpy.ListFields(feature_class)
        ]

        if field_name.lower() not in fields:

            arcpy.management.AddField(
                feature_class,
                field_name,
                field_type
            )

    def execute(self,parameters,messages):

        messages.addMessage("== Proses dimulai ==")

        configs=persil.get_config_values()

        dataset_path=configs["project_config"]["dataset_path"]

        peta_persil_name="Persil_Layer"

        peta_persil_path=os.path.join(
            dataset_path,
            peta_persil_name
        )

        self.add_field_if_not_exists(
            peta_persil_path,
            "LUASM2",
            "DOUBLE"
        )

        messages.addMessage("== Hitung luas tanah ==")

        arcpy.management.CalculateField(
            peta_persil_path,
            "LUASM2",
            "!shape.area!",
            "PYTHON3"
        )

        self.delete_if_exists(peta_persil_name)

        arcpy.management.MakeFeatureLayer(
            peta_persil_path,
            peta_persil_name
        )

        parameters[0].value=peta_persil_name

        messages.addMessage("== Proses selesai ==")

        return
    
class Analisis_Bentuk_Persil(object):

    def __init__(self):
        self.label="Analisis Bentuk Persil Tes"
        self.description=""
        self.canRunInBackground=False

    def getParameterInfo(self):

        update_only = arcpy.Parameter(
            displayName="Hanya Persil Status Update",
            name="update_only",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )

        update_only.value = True

        output_layer=arcpy.Parameter(
            displayName="Output Persil Update",
            name="output_persil",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [
            update_only,
            output_layer
        ]

    def isLicensed(self):
        return True

    def updateParameters(self,parameters):
        return

    def updateMessages(self,parameters):
        return

    def execute(
        self,
        parameters,
        messages
    ):

        update_only = parameters[0].value

        configs = persil.get_config_values()
        dataset_path = configs['project_config']['dataset_path']
        input_fc = os.path.join(dataset_path, 'Persil_Layer')

        temp_line="in_memory\\temp_line"
        temp_split="in_memory\\temp_split"
        temp_dissolve="in_memory\\temp_dissolve"
        temp_polygon = "in_memory\\temp_polygon"

        cleanup_items=[
            temp_line,
            temp_split,
            temp_dissolve,
        ]

        for item in cleanup_items:
            self.delete_if_exists(item)

        messages.addMessage(
            "== Copy polygon =="
        )
        input_layer = "input_layer"

        if update_only:

            arcpy.management.MakeFeatureLayer(
                input_fc,
                input_layer,
                "status_per = 'update'"
            )

        else:

            arcpy.management.MakeFeatureLayer(
                input_fc,
                input_layer
            )

        arcpy.management.CopyFeatures(
            input_layer,
            temp_polygon
        )

        messages.addMessage(
            "== Polygon to line =="
        )

        arcpy.management.PolygonToLine(
            temp_polygon,
            temp_line,
            "IGNORE_NEIGHBORS"
        )

        arcpy.management.SplitLine(
            temp_line,
            temp_split
        )

        field_definitions=[
            ("LebarSisi","DOUBLE"),
            ("XStart","DOUBLE"),
            ("XEnd","DOUBLE"),
            ("YStart","DOUBLE"),
            ("YEnd","DOUBLE"),
            ("Azimuth","DOUBLE"),
            ("ATrans","DOUBLE")
        ]

        for field_name,field_type in field_definitions:

            self.add_field_if_not_exists(
                temp_split,
                field_name,
                field_type
            )

        arcpy.management.CalculateField(
            temp_split,
            "LebarSisi",
            "!shape.length!",
            "PYTHON3"
        )

        messages.addMessage(
            "== Hitung azimuth =="
        )


        with arcpy.da.UpdateCursor(
            temp_split,
            [
                "SHAPE@",
                "XStart",
                "XEnd",
                "YStart",
                "YEnd",
                "Azimuth",
                "ATrans"
            ]
        ) as rows:

            for row in rows:

                geometry=row[0]

                x_start=geometry.firstPoint.X
                y_start=geometry.firstPoint.Y
                x_end=geometry.lastPoint.X
                y_end=geometry.lastPoint.Y

                azimuth,atrans=self.calculate_azimuth(
                    x_start,
                    y_start,
                    x_end,
                    y_end
                )

                row[1]=x_start
                row[2]=x_end
                row[3]=y_start
                row[4]=y_end
                row[5]=azimuth
                row[6]=atrans

                rows.updateRow(row)

        messages.addMessage(
            "== Dissolve =="
        )

        arcpy.management.Dissolve(
            temp_split,
            temp_dissolve,
            ['IdBidang'],
            [["ATrans","RANGE"]],
            "MULTI_PART",
            "DISSOLVE_LINES"
        )

        self.add_field_if_not_exists(
            temp_polygon,
            "bentuk",
            "TEXT"
        )

        self.add_field_if_not_exists(
            temp_polygon,
            "s_bentuk",
            "DOUBLE"
        )

        fields=[
            field.name
            for field in arcpy.ListFields(temp_polygon)
        ]

        if "Range_ATrans" in fields:

            arcpy.management.DeleteField(
                temp_polygon,
                "Range_ATrans"
            )

        arcpy.management.JoinField(
            temp_polygon,
            'IdBidang',
            temp_dissolve,
            'IdBidang',
            ["Range_ATrans"]
        )

        messages.addMessage(
            "== Hitung bentuk persil =="
        )

        with arcpy.da.UpdateCursor(
            temp_polygon,
            [
                "Range_ATrans",
                "bentuk",
                "s_bentuk"
            ]
        ) as rows:

            for row in rows:

                nilai=row[0]

                if nilai is None:
                    continue

                if nilai<16.3:

                    row[1]="Segi Empat Beraturan"
                    row[2]=4

                elif nilai>=16.3 and nilai<=58:

                    row[1]="Segi Empat Tidak Beraturan"
                    row[2]=3

                else:

                    row[1]="Segi Banyak Tidak Beraturan"
                    row[2]=1

                rows.updateRow(row)

        arcpy.management.AddGeometryAttributes(
            temp_polygon,
            "POINT_COUNT"
        )

        with arcpy.da.UpdateCursor(
            temp_polygon,
            [
                "bentuk",
                "s_bentuk",
                "PNT_COUNT"
            ]
        ) as rows:

            for row in rows:

                if row[2] and int(row[2])==4:

                    row[0]="Segi Tiga"
                    row[1]=2

                    rows.updateRow(row)

        fields=[
            field.name
            for field in arcpy.ListFields(temp_polygon)
        ]

        if "PNT_COUNT" in fields:

            arcpy.management.DeleteField(
                temp_polygon,
                "PNT_COUNT"
            )

        hasil_bentuk = {}

        with arcpy.da.SearchCursor(
            temp_polygon,
            [
                "IdBidang",
                "bentuk",
                "s_bentuk"
            ]
        ) as rows:

            for row in rows:

                hasil_bentuk[row[0]] = (
                    row[1],
                    row[2]
                )

        with arcpy.da.UpdateCursor(
            input_fc,
            [
                "IdBidang",
                "BENTUK",
                "s_bentuk"
            ],
            "status_per = 'update'"
        ) as rows:

            for row in rows:

                id_bidang = row[0]

                if id_bidang not in hasil_bentuk:
                    continue

                bentuk, skor = hasil_bentuk[id_bidang]

                row[1] = bentuk
                row[2] = skor

                rows.updateRow(row)

        arcpy.management.MakeFeatureLayer(
            input_fc,
            "Persil_Layer"
        )

        arcpy.SetParameter(1, "Persil_Layer")

        messages.addMessage(
            "== Proses selesai =="
        )

        return

    def delete_if_exists(self,path):

        if arcpy.Exists(path):

            try:
                arcpy.management.Delete(path)

            except Exception:
                pass

    def add_field_if_not_exists(
        self,
        feature_class,
        field_name,
        field_type
    ):

        field_names=[
            field.name.lower()
            for field in arcpy.ListFields(feature_class)
        ]

        if field_name.lower() not in field_names:

            arcpy.management.AddField(
                feature_class,
                field_name,
                field_type
            )

    def calculate_azimuth(
        self,
        x_start,
        y_start,
        x_end,
        y_end
    ):

        delta_y=y_end-y_start
        delta_x=x_end-x_start

        if delta_y==0:

            if delta_x>=0:
                azimuth=90

            else:
                azimuth=-90

        else:

            azimuth=math.atan(
                delta_x/delta_y
            )*(180/math.pi)

        if azimuth<-45:
            atrans=azimuth+180

        elif azimuth>=-45 and azimuth<=45:
            atrans=azimuth+90

        else:
            atrans=azimuth

        return(
            azimuth,
            atrans
        )

class Edit_Bentuk_Persil(object):

    def __init__(self):

        self.label = "Edit Bentuk Persil"
        self.description = ""
        self.canRunInBackground = False

    # =====================================================
    # PARAMETER
    # =====================================================

    def getParameterInfo(self):

        param_bentuk = arcpy.Parameter(
            displayName="Bentuk Persil",
            name="bentuk",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )

        param_bentuk.filter.list = [
            "Segi Banyak Tidak Beraturan",
            "Segi Tiga",
            "Segi Empat Tidak Beraturan",
            "Segi Empat Beraturan"
        ]

        output_layer = arcpy.Parameter(
            displayName="Output Persil",
            name="output_persil",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [
            param_bentuk,
            output_layer
        ]

    def isLicensed(self):
        return True

    def updateParameters(
        self,
        parameters
    ):
        return

    def updateMessages(
        self,
        parameters
    ):
        return

    # =====================================================
    # HELPER
    # =====================================================

    def get_skor_bentuk(
        self,
        bentuk
    ):

        mapping = {

            "Segi Banyak Tidak Beraturan": 2,
            "Segi Tiga": 1,
            "Segi Empat Tidak Beraturan": 3,
            "Segi Empat Beraturan": 4

        }

        return mapping.get(
            bentuk,
            1
        )

    def delete_if_exists(
        self,
        path
    ):

        if arcpy.Exists(path):

            try:

                arcpy.management.Delete(
                    path
                )

            except Exception:

                pass

    # =====================================================
    # EXECUTE
    # =====================================================

    def execute(
        self,
        parameters,
        messages
    ):

        import arcpy

        arcpy.env.overwriteOutput = True

        messages.addMessage(
            "== Proses dimulai =="
        )

        # =================================================
        # PARAMETER
        # =================================================

        bentuk = parameters[0].valueAsText
        configs = persil.get_config_values()

        skor_bentuk = (
            self.get_skor_bentuk(
                bentuk
            )
        )

        persil_update = "Persil_layer"

        fields = [
            field.name.lower()
            for field in arcpy.ListFields(
                persil_update
            )
        ]

        required_fields = [
            "BENTUK",
            "s_bentuk"
        ]

        missing_fields = [
            field
            for field in required_fields
            if field.lower() not in fields
        ]

        if missing_fields:

            messages.addErrorMessage(
                (
                    "Field berikut "
                    "tidak ditemukan: "
                    f"{', '.join(missing_fields)}"
                )
            )

            raise arcpy.ExecuteError

        selected_count = len(
            arcpy.Describe(
                persil_update
            ).FIDSet
        )

        if selected_count <= 0:

            messages.addWarningMessage(
                (
                    "Tidak ada "
                    "fitur yang dipilih"
                )
            )

            return

        updated_count = 0

        with arcpy.da.UpdateCursor(
            persil_update,
            [
                "BENTUK",
                "s_bentuk"
            ]
        ) as rows:

            for row in rows:

                row[0] = bentuk
                row[1] = float(
                    skor_bentuk
                )

                rows.updateRow(
                    row
                )

                updated_count += 1

        messages.addMessage(
            (
                f"{updated_count} "
                f"fitur berhasil "
                f"diupdate"
            )
        )

        persil_path = os.path.join(configs['project_config']['dataset_path'], 'Persil_Layer')
        arcpy.management.MakeFeatureLayer(
            persil_path,
            "Persil_Layer"
        )


        arcpy.SetParameter(1, "Persil_Layer")

        return


#  Uji Coba
class Sinkronkan_Indikator_Persil(object):

    def __init__(self):
        self.label="Sinkronkan Indikator Persil"
        self.description=""
        self.canRunInBackground=False

    def getParameterInfo(self):

        output_layer=arcpy.Parameter(
            displayName="Output Persil Baru",
            name="output_persil",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [output_layer]

    def isLicensed(self):
        return True

    def updateParameters(self,parameters):
        return

    def updateMessages(self,parameters):
        return

    def delete_if_exists(self,path):

        if arcpy.Exists(path):

            try:
                arcpy.management.Delete(path)

            except Exception:
                pass

    def add_field_if_not_exists(
        self,
        feature_class,
        field_name,
        field_type,
        precision=None
    ):

        fields=[field.name.lower() for field in arcpy.ListFields(feature_class)]

        if field_name.lower() not in fields:

            if precision:

                arcpy.management.AddField(
                    feature_class,
                    field_name,
                    field_type,
                    field_precision=precision
                )

            else:

                arcpy.management.AddField(
                    feature_class,
                    field_name,
                    field_type
                )

    def execute(self,parameters,messages):

        messages.addMessage("== Proses dimulai ==")

        configs=persil.get_config_values()

        dataset_path=configs["project_config"]["dataset_path"]

        appdata=os.path.dirname(
            os.path.dirname(
                os.path.realpath(__file__)
            )
        )

        peta_baru_path=os.path.join(
            dataset_path,
            "Persil_Baru"
        )

        indikator_path=os.path.join(
            dataset_path,
            "Indikator_Perubahan_Persil"
        )

        temp_join="in_memory\\temp_join"

        persil_layer="Persil_Baru"

        required_fc=[
            peta_baru_path,
            indikator_path
        ]

        for fc in required_fc:

            if not arcpy.Exists(fc):

                messages.addErrorMessage(
                    f"Feature class {os.path.basename(fc)} tidak ditemukan"
                )

                raise arcpy.ExecuteError

        self.delete_if_exists(temp_join)
        self.delete_if_exists(persil_layer)

        self.add_field_if_not_exists(
            peta_baru_path,
            "status_per",
            "TEXT"
        )

        self.add_field_if_not_exists(
            peta_baru_path,
            "kelompok_perubahan",
            "SHORT"
        )

        self.add_field_if_not_exists(
            peta_baru_path,
            "klaster_zona",
            "SHORT"
        )

        self.add_field_if_not_exists(
            peta_baru_path,
            "PREDICTED",
            "DOUBLE",
            2
        )

        messages.addMessage("== Spatial Join indikator ==")

        field_mapping=(
            f'IdBidang "IdBidang" true true false 9 Long 0 9,First,#,{peta_baru_path},IdBidang,-1,-1;'
            f'status_per "status_per" true true false 50 Text 0 0,First,#,{indikator_path},status_per,-1,-1;'
            f'kelompok_perubahan "kelompok_perubahan" true true false 2 Short 0 0,First,#,{indikator_path},kelompok_perubahan,-1,-1;'
            f'klaster_zona "klaster_zona" true true false 2 Short 0 0,First,#,{indikator_path},klaster_zona,-1,-1'
        )

        arcpy.analysis.SpatialJoin(
            peta_baru_path,
            indikator_path,
            temp_join,
            "JOIN_ONE_TO_ONE",
            "KEEP_ALL",
            field_mapping,
            "CONTAINS"
        )

        messages.addMessage("== Build indikator dictionary ==")

        indikator_dict={}

        with arcpy.da.SearchCursor(
            temp_join,
            [
                "IdBidang",
                "status_per",
                "kelompok_perubahan",
                "klaster_zona"
            ]
        ) as rows:

            for row in rows:

                indikator_dict[row[0]]={
                    "status_per":row[1],
                    "kelompok_perubahan":row[2],
                    "klaster_zona":row[3]
                }

        messages.addMessage("== Update Persil_Baru ==")

        with arcpy.da.UpdateCursor(
            peta_baru_path,
            [
                "IdBidang",
                "status_per",
                "kelompok_perubahan",
                "klaster_zona",
                "PREDICTED",
                "OBJECTID"
            ]
        ) as rows:

            for row in rows:

                bidang_id=row[0]

                if bidang_id in indikator_dict:

                    indikator=indikator_dict[bidang_id]

                    row[1]=indikator["status_per"]
                    row[2]=indikator["kelompok_perubahan"]
                    row[3]=indikator["klaster_zona"]

                if not row[1]:
                    row[1]="tetap"

                if row[1]=="update":
                    row[4]=None

                rows.updateRow(row)

        arcpy.management.MakeFeatureLayer(
            peta_baru_path,
            persil_layer
        )

        simbologi_path=os.path.join(
            appdata,
            "SimbologiPetaPersil.lyr"
        )

        if os.path.exists(simbologi_path):

            arcpy.management.ApplySymbologyFromLayer(
                persil_layer,
                simbologi_path
            )

        parameters[0].value=persil_layer

        try:

            aprx=arcpy.mp.ArcGISProject("CURRENT")

            current_map=aprx.activeMap

            hidden_layers=[
                "Indikator_Perubahan_Persil",
                "Peta_Lama",
                "Persil"
            ]

            for layer in current_map.listLayers():

                if layer.name in hidden_layers:
                    layer.visible=False

        except Exception:
            pass

        self.delete_if_exists(temp_join)

        messages.addMessage("== Proses selesai ==")

        return
    
class Simpan_Bentuk_Persil(object):

    def __init__(self):
        self.label="Simpan Bentuk Persil"
        self.description=""
        self.canRunInBackground=False

    def getParameterInfo(self):

        output_layer=arcpy.Parameter(
            displayName="Output Persil Baru",
            name="output_persil_baru",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return[output_layer]

    def isLicensed(self):
        return True

    def updateParameters(self,parameters):
        return

    def updateMessages(self,parameters):
        return

    def delete_if_exists(self,path):

        if arcpy.Exists(path):

            try:
                arcpy.management.Delete(path)

            except Exception:
                pass

    def add_field_if_not_exists(
        self,
        feature_class,
        field_name,
        field_type,
        field_length=None
    ):

        fields=[field.name for field in arcpy.ListFields(feature_class)]

        if field_name not in fields:

            if field_type=="TEXT":

                arcpy.management.AddField(
                    feature_class,
                    field_name,
                    field_type,
                    field_length=field_length or 255
                )

            else:

                arcpy.management.AddField(
                    feature_class,
                    field_name,
                    field_type
                )

    def execute(self,parameters,messages):

        import os,arcpy

        arcpy.env.overwriteOutput=True

        messages.addMessage("== Proses dimulai ==")

        configs=persil.get_config_values()
        dataset_path=configs["project_config"]["dataset_path"]

        source_name="Persil_Update"
        target_name="Persil_Baru"

        source_path=os.path.join(dataset_path,source_name)
        target_path=os.path.join(dataset_path,target_name)

        required_feature_classes=[source_path,target_path]

        for fc in required_feature_classes:
            if not arcpy.Exists(fc):
                messages.addErrorMessage(
                    f"Feature class {os.path.basename(fc)} tidak ditemukan"
                )

                raise arcpy.ExecuteError

        join_fields=["IdBidang","bentuk","s_bentuk"]

        source_fields=[
            field.name
            for field in arcpy.ListFields(source_path)
        ]

        target_fields=[
            field.name
            for field in arcpy.ListFields(target_path)
        ]

        missing_source=[
            field
            for field in join_fields
            if field not in source_fields
        ]

        missing_target=[
            field
            for field in join_fields
            if field not in target_fields
        ]

        if missing_source:

            messages.addErrorMessage(
                f"Field source tidak ditemukan: {', '.join(missing_source)}"
            )

            raise arcpy.ExecuteError

        if missing_target:

            messages.addMessage(
                "Field target tidak lengkap, menambahkan field yang hilang pada Persil_Baru"
            )

            field_defs={
                "IdBidang":"LONG",
                "bentuk":"TEXT",
                "s_bentuk":"DOUBLE"
            }

            for field in missing_target:

                self.add_field_if_not_exists(
                    target_path,
                    field,
                    field_defs.get(field,"TEXT"),
                    255 if field=="bentuk" else None
                )

            target_fields=[
                field.name
                for field in arcpy.ListFields(target_path)
            ]

            missing_target=[
                field
                for field in join_fields
                if field not in target_fields
            ]

            if missing_target:

                messages.addErrorMessage(
                    f"Field target tidak ditemukan: {', '.join(missing_target)}"
                )

                raise arcpy.ExecuteError

        messages.addMessage("== Membaca data Persil_Update ==")

        join_dictionary={}

        with arcpy.da.SearchCursor(
            source_path,
            join_fields
        ) as rows:

            for row in rows:

                id_bidang=row[0]

                join_dictionary[id_bidang]={
                    "bentuk":row[1],
                    "s_bentuk":row[2]
                }

        messages.addMessage("== Update bentuk Persil_Baru ==")

        updated_count=0

        with arcpy.da.UpdateCursor(
            target_path,
            join_fields
        ) as rows:

            for row in rows:

                id_bidang=row[0]

                if id_bidang in join_dictionary:

                    row[1]=join_dictionary[id_bidang]["bentuk"]
                    row[2]=join_dictionary[id_bidang]["s_bentuk"]

                    rows.updateRow(row)

                    updated_count+=1

        messages.addMessage(f"{updated_count} fitur berhasil diupdate")

        self.delete_if_exists(target_name)

        arcpy.management.MakeFeatureLayer(
            target_path,
            target_name
        )

        target_field_names=[
            field.name
            for field in arcpy.ListFields(target_name)
        ]

        if "Shape_Leng" in target_field_names:

            try:

                arcpy.management.DeleteField(
                    target_name,
                    "Shape_Leng"
                )

            except Exception:
                pass
        
        persil_path = os.path.join(dataset_path,"Persil_Layer")
        if arcpy.Exists(persil_path):
            arcpy.management.Delete(persil_path)

        arcpy.management.CopyFeatures(
            target_path,
            persil_path,
        )

        parameters[0].value=persil_path

        messages.addMessage("== Proses selesai ==")

        return


class Analisis_Bentuk_Persil_File(object):

    def __init__(self):
        self.label="Analisis Bentuk Persil File"
        self.description=""
        self.canRunInBackground=False

    def getParameterInfo(self):

        input_fc=arcpy.Parameter(
            displayName="Input Polygon",
            name="input_fc",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )

        field_id=arcpy.Parameter(
            displayName="Field ID Bidang",
            name="field_id",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        field_id.parameterDependencies=[input_fc.name]

        output_fc=arcpy.Parameter(
            displayName="Output Feature Class",
            name="output_fc",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output"
        )

        return[
            input_fc,
            field_id,
            output_fc
        ]

    def isLicensed(self):
        return True

    def updateParameters(self,parameters):
        return

    def updateMessages(self,parameters):
        return

    def delete_if_exists(self,path):

        if arcpy.Exists(path):

            try:
                arcpy.management.Delete(path)

            except Exception:
                pass

    def add_field_if_not_exists(
        self,
        feature_class,
        field_name,
        field_type
    ):

        field_names=[
            field.name.lower()
            for field in arcpy.ListFields(feature_class)
        ]

        if field_name.lower() not in field_names:

            arcpy.management.AddField(
                feature_class,
                field_name,
                field_type
            )

    def calculate_azimuth(
        self,
        x_start,
        y_start,
        x_end,
        y_end
    ):

        delta_y=y_end-y_start
        delta_x=x_end-x_start

        if delta_y==0:

            if delta_x>=0:
                azimuth=90

            else:
                azimuth=-90

        else:

            azimuth=math.atan(
                delta_x/delta_y
            )*(180/math.pi)

        if azimuth<-45:
            atrans=azimuth+180

        elif azimuth>=-45 and azimuth<=45:
            atrans=azimuth+90

        else:
            atrans=azimuth

        return(
            azimuth,
            atrans
        )

    def execute(
        self,
        parameters,
        messages
    ):

        import arcpy
        import math

        arcpy.env.overwriteOutput=True

        messages.addMessage(
            "== Proses dimulai =="
        )

        input_fc=parameters[0].valueAsText
        field_id=parameters[1].valueAsText
        output_fc=parameters[2].valueAsText

        if not arcpy.Exists(input_fc):

            messages.addErrorMessage(
                "Input feature class tidak ditemukan"
            )

            raise arcpy.ExecuteError

        temp_line="in_memory\\temp_line"
        temp_split="in_memory\\temp_split"
        temp_dissolve="in_memory\\temp_dissolve"

        cleanup_items=[
            temp_line,
            temp_split,
            temp_dissolve,
            output_fc
        ]

        for item in cleanup_items:
            self.delete_if_exists(item)

        messages.addMessage(
            "== Copy polygon =="
        )

        arcpy.management.CopyFeatures(
            input_fc,
            output_fc
        )

        messages.addMessage(
            "== Polygon to line =="
        )

        arcpy.management.PolygonToLine(
            output_fc,
            temp_line,
            "IGNORE_NEIGHBORS"
        )

        arcpy.management.SplitLine(
            temp_line,
            temp_split
        )

        field_definitions=[
            ("LebarSisi","DOUBLE"),
            ("XStart","DOUBLE"),
            ("XEnd","DOUBLE"),
            ("YStart","DOUBLE"),
            ("YEnd","DOUBLE"),
            ("Azimuth","DOUBLE"),
            ("ATrans","DOUBLE")
        ]

        for field_name,field_type in field_definitions:

            self.add_field_if_not_exists(
                temp_split,
                field_name,
                field_type
            )

        arcpy.management.CalculateField(
            temp_split,
            "LebarSisi",
            "!shape.length!",
            "PYTHON3"
        )

        messages.addMessage(
            "== Hitung azimuth =="
        )


        with arcpy.da.UpdateCursor(
            temp_split,
            [
                "SHAPE@",
                "XStart",
                "XEnd",
                "YStart",
                "YEnd",
                "Azimuth",
                "ATrans"
            ]
        ) as rows:

            for row in rows:

                geometry=row[0]

                x_start=geometry.firstPoint.X
                y_start=geometry.firstPoint.Y
                x_end=geometry.lastPoint.X
                y_end=geometry.lastPoint.Y

                azimuth,atrans=self.calculate_azimuth(
                    x_start,
                    y_start,
                    x_end,
                    y_end
                )

                row[1]=x_start
                row[2]=x_end
                row[3]=y_start
                row[4]=y_end
                row[5]=azimuth
                row[6]=atrans

                rows.updateRow(row)

        messages.addMessage(
            "== Dissolve =="
        )

        arcpy.management.Dissolve(
            temp_split,
            temp_dissolve,
            [field_id],
            [["ATrans","RANGE"]],
            "MULTI_PART",
            "DISSOLVE_LINES"
        )

        self.add_field_if_not_exists(
            output_fc,
            "bentuk",
            "TEXT"
        )

        self.add_field_if_not_exists(
            output_fc,
            "s_bentuk",
            "DOUBLE"
        )

        fields=[
            field.name
            for field in arcpy.ListFields(output_fc)
        ]

        if "Range_ATrans" in fields:

            arcpy.management.DeleteField(
                output_fc,
                "Range_ATrans"
            )

        arcpy.management.JoinField(
            output_fc,
            field_id,
            temp_dissolve,
            field_id,
            ["Range_ATrans"]
        )

        messages.addMessage(
            "== Hitung bentuk persil =="
        )

        with arcpy.da.UpdateCursor(
            output_fc,
            [
                "Range_ATrans",
                "bentuk",
                "s_bentuk"
            ]
        ) as rows:

            for row in rows:

                nilai=row[0]

                if nilai is None:
                    continue

                if nilai<16.3:

                    row[1]="Segi Empat Beraturan"
                    row[2]=4

                elif nilai>=16.3 and nilai<=58:

                    row[1]="Segi Empat Tidak Beraturan"
                    row[2]=3

                else:

                    row[1]="Segi Banyak Tidak Beraturan"
                    row[2]=1

                rows.updateRow(row)

        arcpy.management.AddGeometryAttributes(
            output_fc,
            "POINT_COUNT"
        )

        with arcpy.da.UpdateCursor(
            output_fc,
            [
                "bentuk",
                "s_bentuk",
                "PNT_COUNT"
            ]
        ) as rows:

            for row in rows:

                if row[2] and int(row[2])==4:

                    row[0]="Segi Tiga"
                    row[1]=2

                    rows.updateRow(row)

        fields=[
            field.name
            for field in arcpy.ListFields(output_fc)
        ]

        if "PNT_COUNT" in fields:

            arcpy.management.DeleteField(
                output_fc,
                "PNT_COUNT"
            )

        arcpy.management.MakeFeatureLayer(
            output_fc,
            "Output_Bentuk_Persil"
        )

        parameters[2].value=output_fc

        messages.addMessage(
            "== Proses selesai =="
        )

        return


class Simpan_Perubahan_Ke_Persil_Baru(object):

    def __init__(self):
        self.label="Simpan Perubahan Ke Persil Baru"
        self.description=""
        self.canRunInBackground=False

    def getParameterInfo(self):

        output_layer=arcpy.Parameter(
            displayName="Output Peta Persil",
            name="output_persil",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return[output_layer]

    def isLicensed(self):
        return True

    def updateParameters(self,parameters):
        return

    def updateMessages(self,parameters):
        return

    def delete_if_exists(self,path):
        if arcpy.Exists(path):
            try:
                arcpy.management.Delete(path)
            except Exception:
                pass

    def add_field_if_not_exists(self,feature_class,field_name,field_type,precision=None):

        fields=[field.name for field in arcpy.ListFields(feature_class)]

        if field_name not in fields:

            if precision:
                arcpy.management.AddField(
                    feature_class,
                    field_name,
                    field_type,
                    field_precision=precision
                )

            else:
                arcpy.management.AddField(
                    feature_class,
                    field_name,
                    field_type
                )

    def execute(self,parameters,messages):

        messages.addMessage("== Proses dimulai ==")
        configs=persil.get_config_values()
        dataset_path=configs["project_config"]["dataset_path"]
        appdata=os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        peta_baru_path=os.path.join(dataset_path,"Persil_Baru")
        indikator_path=os.path.join(dataset_path,"Indikator_Perubahan_Persil")
        peta_persil_path=os.path.join(dataset_path,"Peta_Persil")
        peta_persil="Peta_Persil"
        required_fc=[ peta_baru_path, indikator_path ]

        for fc in required_fc:
            if not arcpy.Exists(fc):
                messages.addErrorMessage(f"Feature class {os.path.basename(fc)} tidak ditemukan")
                raise arcpy.ExecuteError

        if arcpy.Exists(peta_persil_path):
            arcpy.management.Delete(peta_persil_path)

        self.delete_if_exists(peta_persil_path)
        self.delete_if_exists(peta_persil)

        messages.addMessage("== Spatial Join Persil ==")
        field_mapping=(
            f'NIB "NIB" true true false 5 Long 0 0,First,#,{peta_baru_path},NIB,-1,-1;'
            f'IdBidang "IdBidang" true true false 9 Long 0 9,First,#,{peta_baru_path},IdBidang,-1,-1;'
            f'ls_asal "ls_asal" true true false 19 Double 0 0,First,#,{peta_baru_path},ls_asal,-1,-1;'
            f'status_per "status_per" true true false 50 Text 0 0,First,#,{indikator_path},status_per,-1,-1;'
            f'kelompok_perubahan "kelompok_perubahan" true true false 2 Short 0 0,First,#,{indikator_path},kelompok_perubahan,-1,-1'
        )
        arcpy.analysis.SpatialJoin(
            peta_baru_path,
            indikator_path,
            peta_persil_path,
            "JOIN_ONE_TO_ONE",
            "KEEP_ALL",
            field_mapping,
            "CONTAINS"
        )

        self.add_field_if_not_exists(
            peta_persil_path,
            "PREDICTED",
            "DOUBLE",
            2
        )

        messages.addMessage("== Copy field PREDICTED ==")
        predicted_dict={}
        with arcpy.da.SearchCursor(
            peta_baru_path,
            ["IdBidang","PREDICTED"]
        ) as rows:
            for row in rows:
                predicted_dict[row[0]]=row[1]
        with arcpy.da.UpdateCursor(
            peta_persil_path,
            ["IdBidang","PREDICTED","status_per"]
        ) as rows:
            for row in rows:
                bidang_id=row[0]
                if bidang_id in predicted_dict:
                    row[1]=predicted_dict[bidang_id]
                if row[2]=="update":
                    row[1]=None
                rows.updateRow(row)

        messages.addMessage("== Update status default ==")

        with arcpy.da.UpdateCursor(
            peta_persil_path,
            ["status_per","IdBidang","OBJECTID"]
        ) as rows:

            for row in rows:

                if not row[0]:
                    row[0]="tetap"
                    row[1]=row[2]

                    rows.updateRow(row)

        self.delete_if_exists(peta_persil)

        arcpy.management.MakeFeatureLayer(
            peta_persil_path,
            peta_persil
        )


        parameters[0].value=peta_persil

        return
    
class Generate_Peta_Akhir(object):

    def __init__(self):

        self.label = "Generate Peta Akhir"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):

        output_layer = arcpy.Parameter(
            displayName="Output Peta Akhir",
            name="output_peta_akhir",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [output_layer]

    def isLicensed(self):
        return True

    def updateParameters(
        self,
        parameters
    ):
        return

    def updateMessages(
        self,
        parameters
    ):
        return

    # =====================================================
    # HELPER
    # =====================================================

    def delete_if_exists(
        self,
        path
    ):

        if arcpy.Exists(path):

            try:

                arcpy.management.Delete(
                    path
                )

            except Exception:

                pass

    def add_field_if_not_exists(
        self,
        feature_class,
        field_name,
        field_type
    ):

        fields = [
            field.name.lower()
            for field in arcpy.ListFields(
                feature_class
            )
        ]

        if field_name.lower() not in fields:

            arcpy.management.AddField(
                feature_class,
                field_name,
                field_type
            )

    def execute( self,  parameters, messages ):

        messages.addMessage(  "== Proses dimulai ==" )

        configs = persil.get_config_values()
        dataset_path =  configs["project_config"]["dataset_path"]
        daftar_variabel_path = configs["project_config"]["daftar_variabel_path"]

        with open(daftar_variabel_path, "r") as f:

            json_conf = (json.load(f))
            variable_config = json_conf['daftar_variabel']

        field_str_type = [
            "bentuk",
            "letak",
            "kls_jln",
            "elvasi",
            "zonasi"
        ]

        fields_dont_delete = []

        for item in variable_config:

            # Extract field_name from list format [display_name, field_name]
            field_name = ( item[1]   if isinstance(item, list) and len(item) > 1  else None )

            if not field_name:
                continue

            fields_dont_delete.append( field_name )

            if ( field_name.lower()  in field_str_type ):

                fields_dont_delete.append( f"s_{field_name}" )

        # =================================================
        # DATASET
        # =================================================

        peta_persil_path = os.path.join( dataset_path,  "Peta_Persil" )

        peta_lama_path = os.path.join( dataset_path,  "Persil_Layer" )

        centroid_path = os.path.join( dataset_path, "Persil_Lama_Centroid" )

        erase_path = os.path.join( dataset_path,  "Peta_Erase" )

        peta_akhir_path = os.path.join( dataset_path,  "Peta_Akhir")

        peta_akhir_layer = "Peta_Akhir"

        # =================================================
        # VALIDASI
        # =================================================

        required_fc = [
            peta_persil_path,
            peta_lama_path
        ]

        for fc in required_fc:

            if not arcpy.Exists(fc):

                messages.addErrorMessage(
                    (
                        f"Feature class "
                        f"{os.path.basename(fc)} "
                        f"tidak ditemukan"
                    )
                )

                raise arcpy.ExecuteError

        # =================================================
        # CLEANUP
        # =================================================

        cleanup_items = [
            centroid_path,
            erase_path,
            peta_akhir_path,
            peta_akhir_layer
        ]

        for item in cleanup_items:

            self.delete_if_exists(
                item
            )

        arcpy.management.FeatureToPoint(
            peta_lama_path,
            centroid_path,
            "INSIDE"
        )

        # =================================================
        # SELECT UPDATE
        # =================================================

        temp_persil = (
            "temp_persil"
        )

        self.delete_if_exists(
            temp_persil
        )

        arcpy.management.MakeFeatureLayer(
            peta_persil_path,
            temp_persil
        )

        arcpy.management.SelectLayerByAttribute(
            temp_persil,
            "NEW_SELECTION",
            "status_per = 'update'"
        )

        # =================================================
        # ERASE
        # =================================================

        messages.addMessage(
            "== Erase centroid =="
        )

        arcpy.analysis.Erase(
            centroid_path,
            temp_persil,
            erase_path
        )

        # =================================================
        # SPATIAL JOIN
        # =================================================

        messages.addMessage(
            "== Spatial Join =="
        )

        arcpy.analysis.SpatialJoin(
            peta_persil_path,
            erase_path,
            peta_akhir_path,
            "JOIN_ONE_TO_ONE",
            "KEEP_ALL",
            "",
            "INTERSECT"
        )

        #  Hapus Field Gabungan

        join_delete_fields = []

        fields = arcpy.ListFields( peta_akhir_path )

        for field in fields:

            if (field.name.lower().startswith( "join_")  or
                field.name.lower().startswith("target_")
            ):

                join_delete_fields.append(field.name)

        if join_delete_fields:

            arcpy.management.DeleteField(
                peta_akhir_path,
                join_delete_fields
            )

        # =================================================
        # OUTPUT LAYER
        # =================================================

        self.delete_if_exists(
            peta_akhir_layer
        )

        arcpy.management.MakeFeatureLayer(
            peta_akhir_path,
            peta_akhir_layer
        )

        parameters[0].value = (
            peta_akhir_layer
        )

        # =================================================
        # CLEANUP TEMP
        # =================================================

        self.delete_if_exists(
            temp_persil
        )

        # =================================================
        # FINISH
        # =================================================

        messages.addMessage(
            "== Proses selesai =="
        )

        return
