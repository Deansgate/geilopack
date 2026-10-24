import os
import platform
import shutil
import ctypes


def detect(directory):
    ram = "unbekannt"
    if os.name == "nt":
        class Memory(ctypes.Structure):
            _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [
                (name, ctypes.c_ulonglong) for name in
                ("total", "available", "page_total", "page_available", "virtual_total", "virtual_available", "extended")]
        mem = Memory()
        mem.length = ctypes.sizeof(mem)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem)):
            ram = f"{mem.total / 1024 ** 3:.1f} GB"
    else:
        try:
            ram = f"{os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES') / 1024 ** 3:.1f} GB"
        except (ValueError, OSError, AttributeError):
            pass
    return (f"CPU: {platform.processor() or platform.machine()} · {os.cpu_count()} logische Kerne\n"
            f"RAM: {ram} · frei auf SSD/Laufwerk: {shutil.disk_usage(directory).free / 1024 ** 3:.1f} GB\n"
            "Audio: 48 kHz, Float32 intern · Verarbeitung: CPU · keine CUDA-Abhängigkeit\n"
            "GPU-Erkennung und KI-Modellauswahl: für die KI-Ausbaustufe geplant.")
