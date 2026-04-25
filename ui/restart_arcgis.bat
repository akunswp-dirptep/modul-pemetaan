@echo off
echo Membuka ulang ArcGIS...
timeout /t 2
set "ARCGIS_EXE=C:\Program Files\ArcGIS\Pro\bin\ArcGISPro.exe"
set "ARCGIS_PROJECT=C:\Users\PTEP ILASPP 1\Documents\ArcGIS\Projects\Percobaan Pembaruan ZNT\Percobaan Pembaruan ZNT.aprx"

if exist "%ARCGIS_PROJECT%" (
    start "" "%ARCGIS_EXE%" "%ARCGIS_PROJECT%"
) else (
    start "" "%ARCGIS_EXE%"
)
