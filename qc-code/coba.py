import arcpy , json

gdb = r'E:\Akmal\Jobdesk\Uji Coba Plugin Penilaian Tanah\Pembaruan ZNT\Uji Coba Versi 6 2704\ZoneNilaiTanah.gdb\znt_ds\Titik_Sampel_dua'
data_json = r'"E:\Akmal\Jobdesk\Uji Coba Plugin Penilaian Tanah\Pembaruan ZNT\Uji Coba Versi 6 2704\titik_sampel.geojson"'
# arcpy.conversion.JSONToFeatures(data_json, gdb)
num = '01/2026'
print('01' in num)
