import subprocess
import time

# --- CONFIGURACIÓN ---
IP_OBJETIVO = "192.168.68.107"
INTERFAZ = None  # Cambia a "eth0" o "wlan0" si falla, si no, déjalo en None

def test_arping(ip, interface=None):
    # -c 1: envía un solo paquete
    # -w 1000000: espera 1 segundo
    cmd = ["sudo", "arping", "-c", "1", "-w", "1000000"]
    if interface:
        cmd.extend(["-I", interface])
    cmd.append(ip)
    
    start_time = time.time()
    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    end_time = time.time()
    
    latencia = (end_time - start_time) * 1000
    return res.returncode == 0, latencia

print(f"--- Probando respuesta de {IP_OBJETIVO} ---")
print("Presiona Ctrl+C para detener\n")

try:
    while True:
        exito, ms = test_arping(IP_OBJETIVO, INTERFAZ)
        
        timestamp = time.strftime("%H:%M:%S")
        if exito:
            print(f"[{timestamp}] ✅ DISPOSITIVO DETECTADO - Respuesta en {ms:.2f}ms")
        else:
            print(f"[{timestamp}] ❌ SIN RESPUESTA")
            
        time.sleep(2) # Pausa de 2 segundos entre pruebas
except KeyboardInterrupt:
    print("\nPrueba finalizada.")