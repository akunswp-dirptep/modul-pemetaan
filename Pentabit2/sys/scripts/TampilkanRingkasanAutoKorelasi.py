import os
import re
import arcpy
import webbrowser

arcpy.AddMessage("== Proses dimulai ==")

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
result = os.path.join(appdata, "results")

filelist = os.listdir(result)
max = -1
fileto_open = ""

for f in filelist:
    #arcpy.AddMessage(f)
    if f.endswith(".html") and f.startswith("Morans"):
        nameonly = f.split(".")[0]
        #m = re.search(r'\d+$', nameonly)
        #if m is None:
        #    if max <= -1:
        #        fileto_open = nameonly + ".html"
        #else:
        s = os.path.getmtime(os.path.join(result, f))
        #arcpy.AddMessage(str(s))
        #s = nameonly.replace("MoransI_Result", "")
        if max < s:
            max = s
            fileto_open = nameonly + ".html"

#arcpy.AddMessage(fileto_open)

if fileto_open != "":
    webbrowser.open('file://' + os.path.join(result, fileto_open))

arcpy.AddMessage("== Proses selesai... ringkasan akan dibuka di browser ==")
