import arcpy
import time

from secure import get_all_config

class ToolLogger:
    def __init__(self, tool_name):
        self.tool_name = tool_name
        self.start_time = time.time()
        arcpy.AddMessage(f"=== [{self.tool_name}] Start Time: {time.strftime('%A, %d %B %Y %H:%M:%S')} ===")

    def step(self, message, project_config_path):
        """Menandai tahapan utama proses""" 
        json_app = get_all_config()
        
        user_name = json_app['user_credential']['nama_pengguna']
        user_nik = json_app.get('nik')
        user_berkas = json_app.get('berkas')

        log = f'[{user_name}][{user_nik}][{user_berkas}]-{message}'
        app_log_key = json_app.get('log_data', None)
        

        if project_config_path:
            json_project = get_all_config(project_config_path)
            project_log_key = json_project.get('log_data', None)

        


        

        arcpy.AddMessage(f"\n*** {message.upper()} ***")

    def info(self, message):
        """Pesan detail/sub-langkah"""
        arcpy.AddMessage(f"   -> {message}")

    def warning(self, message):
        """Peringatan non-fatal"""
        arcpy.AddWarning(f"[WARNING] {message}")

    def error(self, message):
        """Pesan kesalahan"""
        arcpy.AddError(f"[ERROR] {message}")

    def finish(self, success=True):
        elapsed = time.time() - self.start_time
        status = "BERHASIL" if success else "GAGAL"
        arcpy.AddMessage(f"\n=== Proses {status} dalam {elapsed:.2f} detik ===")