import arcpy
import time

class ToolLogger:
    def __init__(self, tool_name):
        self.tool_name = tool_name
        self.start_time = time.time()
        arcpy.AddMessage(f"=== [{self.tool_name}] Start Time: {time.strftime('%A, %d %B %Y %H:%M:%S')} ===")

    def step(self, message):
        """Menandai tahapan utama proses"""
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