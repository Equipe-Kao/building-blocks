"""
Script para enviar main.py e secrets.py ao Wokwi via RFC2217 (sem mpremote).
Uso: python wokwi.py
"""
import serial
import time
import sys

PORT  = "rfc2217://localhost:4001"
BAUD  = 115200
FILES = ["secrets.py", "main.py"]  # secrets primeiro, main por último

def send_file(ser, filename):
    print(f"Enviando {filename}...")

    with open(filename, "r") as f:
        code = f.read()

    # Entra no raw REPL
    ser.write(b'\r\x01')
    time.sleep(0.5)
    ser.read(ser.in_waiting or 1)

    # Envolve o código num exec() para salvar no sistema de arquivos
    wrapped = f"f=open('{filename}','w')\nf.write({repr(code)})\nf.close()\n"

    ser.write(wrapped.encode('utf-8'))
    time.sleep(0.3)
    ser.write(b'\x04')  # Ctrl+D para executar
    time.sleep(0.5)

    response = ser.read(ser.in_waiting or 1).decode(errors='replace')
    if 'Error' in response or 'Traceback' in response:
        print(f"  Erro ao enviar {filename}:\n{response}")
        return False

    print(f"  {filename} salvo com sucesso.")
    return True

def run_main(ser):
    print("Executando main.py...")

    with open("main.py", "r") as f:
        code = f.read()

    ser.write(b'\r\x01')
    time.sleep(0.5)
    ser.read(ser.in_waiting or 1)

    ser.write(code.encode('utf-8'))
    time.sleep(0.5)
    ser.write(b'\x04')  # Ctrl+D para executar

def main():
    print(f"Conectando a {PORT}...")
    try:
        ser = serial.serial_for_url(PORT, baudrate=BAUD, timeout=2)
    except Exception as e:
        print(f"Erro ao conectar: {e}")
        print("Verifique se a simulação Wokwi está rodando.")
        sys.exit(1)

    time.sleep(0.5)

    # Interrompe qualquer código em execução
    ser.write(b'\r\x03\x03')
    time.sleep(0.5)
    ser.read(ser.in_waiting or 1)

    # Envia secrets.py e main.py
    for filename in FILES:
        if not send_file(ser, filename):
            sys.exit(1)

    # Executa main.py
    run_main(ser)

    print()
    print("Código enviado! Mostrando saída (Ctrl+C para sair):\n")

    try:
        while True:
            if ser.in_waiting:
                data = ser.read(ser.in_waiting).decode(errors='replace')
                data = data.replace('\x04', '')
                if data.strip():
                    print(data, end='', flush=True)
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n\nDesconectado.")
        ser.write(b'\x03\x03')
        ser.write(b'\x02')
        ser.close()

if __name__ == "__main__":
    main()