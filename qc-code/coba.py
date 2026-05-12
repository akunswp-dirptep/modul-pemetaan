import arcpy
import os

class Proyeksi_dan_Topologi(object):

    def __init__(self):
        self.label = "Proyeksi dan Topologi"
        self.description = "Melakukan proyeksi layer dan membuat aturan topologi"

    def getParameterInfo(self):

        param0 = arcpy.Parameter(
            displayName="Feature Class Input",
            name="input_fc",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input"
        )

        param1 = arcpy.Parameter(
            displayName="Output Geodatabase",
            name="output_gdb",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input"
        )

        return [param0, param1]

    def execute(self, parameters, messages):

        input_fc = parameters[0].valueAsText
        output_gdb = parameters[1].valueAsText

        # Nama hasil proyeksi
        output_fc = os.path.join(output_gdb, "hasil_proyeksi")

        # Sistem koordinat tujuan
        spatial_ref = arcpy.SpatialReference(32748)

        # Proses Proyeksi
        arcpy.management.Project(
            input_fc,
            output_fc,
            spatial_ref
        )

        arcpy.AddMessage("Proyeksi selesai")

        # Membuat Feature Dataset
        dataset_name = "TopologiDataset"

        dataset_path = arcpy.management.CreateFeatureDataset(
            output_gdb,
            dataset_name,
            spatial_ref
        )[0]

        # Copy feature ke dataset
        feature_topologi = os.path.join(dataset_path, "layer_topologi")

        arcpy.management.CopyFeatures(
            output_fc,
            feature_topologi
        )

        # Membuat Topology
        topology_name = "Topology_ZNT"

        topology_path = arcpy.management.CreateTopology(
            dataset_path,
            topology_name
        )[0]

        # Menambahkan feature class ke topology
        arcpy.management.AddFeatureClassToTopology(
            topology_path,
            feature_topologi,
            1,
            1
        )

        # Rule 1 : Tidak boleh ada gaps
        arcpy.management.AddRuleToTopology(
            topology_path,
            "Must Not Have Gaps (Area)",
            feature_topologi
        )

        # Rule 2 : Tidak boleh ada node
        arcpy.management.AddRuleToTopology(
            topology_path,
            "Must Not Have Dangles (Line)",
            feature_topologi
        )

        # Validasi topology
        arcpy.management.ValidateTopology(topology_path)

        arcpy.AddMessage("Topologi berhasil dibuat dan divalidasi")