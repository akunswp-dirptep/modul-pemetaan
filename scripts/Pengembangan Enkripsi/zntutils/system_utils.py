import json
import os, arcpy, datetime
 
def current_year():
    try:
        return int(datetime.now().year)
    except Exception:
        return None
 
