from datetime import datetime
import json
import sys
import arcpy, os, math

# Tambahkan parent directory ke sys.path
script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from nbtutils import constant, persil

class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [Hitung_Jarak_Fasilitas]


class Hitung_Jarak_Fasilitas(object):

    def __init__(self):
        self.label="Hitung Jarak Fasilitas"
        self.description=""
        self.canRunInBackground=False

    def getParameterInfo(self):

        output_persil=arcpy.Parameter(
            displayName="Output Persil",
            name="output_persil",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return[output_persil]

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

        field_names=[field.name for field in arcpy.ListFields(feature_class)]

        if field_name not in field_names:
            arcpy.management.AddField(feature_class,field_name,field_type)

    def execute(self,parameters,messages):

        messages.addMessage("== Proses mulai ==")

        configs=persil.get_config_values()

        dataset_path=configs["project_config"]["dataset_path"]
        dataset_fasilitas_path=configs["fasilitas_config"]["dataset_path"]
        jaringanjalan_nd_path=configs["jaringan_jalan_config"]["path"]["JaringanJalanForND"]
        nd_path=configs["jaringan_jalan_config"]["path"]["JaringanJalan_ND"]

        persil_nama="Persil_Layer"
        persil_path=os.path.join(dataset_path,persil_nama)

        persil_layer_centroid="Persil_Layer_Centroid"
        persil_layer_centroid_path=os.path.join(dataset_path,persil_layer_centroid)

        dataset_template_path=os.path.dirname(jaringanjalan_nd_path)

        self.delete_if_exists(persil_layer_centroid)
        self.delete_if_exists(persil_layer_centroid_path)

        messages.addMessage("== Membuat centroid persil ==")

        arcpy.management.FeatureToPoint(
            persil_path,
            persil_layer_centroid_path,
            "INSIDE"
        )

        messages.addMessage("== Persiapan network analyst ==")

        outNALayerName="hasil_na"
        impedance_attribute="P_Jalan"

        arcpy.env.workspace=dataset_fasilitas_path
        list_fc=arcpy.ListFeatureClasses()

        if not list_fc:
            messages.addWarningMessage("== Tidak ada fasilitas ditemukan ==")
            return

        for fc in list_fc:
            fasilitas=fc
            fasilitas_path=os.path.join(dataset_fasilitas_path,fasilitas)
            namafield=os.path.splitext(fasilitas)[0]
            arcpy.AddMessage(namafield)

            messages.addMessage(f"== Hitung jarak fasilitas: {fasilitas} ==")

            hasilNAObject=arcpy.na.MakeClosestFacilityLayer(
                nd_path,
                outNALayerName,
                impedance_attribute,
                "TRAVEL_FROM",
                default_number_facilities_to_find=1
            )

            outNALayer=hasilNAObject.getOutput(0)

            arcpy.na.AddLocations(
                outNALayer,
                "Incidents",
                persil_layer_centroid_path
            )

            arcpy.na.AddLocations(
                outNALayer,
                "Facilities",
                fasilitas_path
            )

            arcpy.na.Solve(outNALayer)
            aprx=arcpy.mp.ArcGISProject("CURRENT")
            m=aprx.activeMap
            m.addLayer(outNALayer)

            incident_path=os.path.join(dataset_template_path,f"incident_{fasilitas}")
            route_path=os.path.join(dataset_template_path,f"route_{fasilitas}")
            temp_join=os.path.join(dataset_template_path,"temp_join1")

            self.delete_if_exists(incident_path)
            self.delete_if_exists(route_path)
            self.delete_if_exists(temp_join)

            messages.addMessage("== Export hasil network analyst ==")

            for lyr in outNALayer.listLayers():

                if lyr.isGroupLayer:
                    continue

                if lyr.name=="Incidents":

                    arcpy.management.CopyFeatures(
                        lyr,
                        incident_path
                    )

                elif lyr.name=="Routes":

                    arcpy.management.CopyFeatures(
                        lyr,
                        route_path
                    )

            messages.addMessage("== Join route ==")

            arcpy.management.JoinField(
                incident_path,
                "OBJECTID",
                route_path,
                "IncidentID",
                ["Total_P_Jalan"]
            )

            messages.addMessage("== Spatial join ==")

            field_mapping=(
                f'IdBidang "IdBidang" true true false 4 Long 0 0 ,First,#,{persil_path},IdBidang,-1,-1;'
                f'Total_P_Jalan "Total_P_Jalan" true true false 8 Double 0 0 ,First,#,{incident_path},Total_P_Jalan,-1,-1'
            )

            arcpy.analysis.SpatialJoin(
                persil_path,
                incident_path,
                temp_join,
                "JOIN_ONE_TO_ONE",
                "KEEP_ALL",
                field_mapping,
                "INTERSECT"
            )

            self.add_field_if_not_exists(
                persil_path,
                namafield,
                "DOUBLE"
            )

            arcpy.management.JoinField(
                persil_path,
                "IdBidang",
                temp_join,
                "IdBidang",
                ["Total_P_Jalan"]
            )

            arcpy.management.CalculateField(
                persil_path,
                namafield,
                "!Total_P_Jalan!",
                "PYTHON3"
            )

            try:
                arcpy.management.DeleteField(persil_path,"Total_P_Jalan")
            except:
                pass

        self.delete_if_exists(persil_nama)

        arcpy.management.MakeFeatureLayer(
            persil_path,
            persil_nama
        )

        parameters[0].value=persil_nama

        messages.addMessage("== Proses selesai ==")
        return
