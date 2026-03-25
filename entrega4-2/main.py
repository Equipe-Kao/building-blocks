import network
import time
import json
from machine import Pin, PWM
from umqtt.simple import MQTTClient
from secrets import MQTT_USER, MQTT_PASSWORD

# ── Configurações ─────────────────────────────────────────────────────────────

SSID     = "Wokwi-GUEST"
PASSWORD = ""

MQTT_BROKER      = "d10f080e92054ccf9261241b924702f1.s1.eu.hivemq.cloud"
MQTT_PORT        = 8883
MQTT_CLIENT_ID   = "esp32-02"

TOPIC_LED_CMD    = b"building-blocks/led/comando"   # subscribe — recebe "on" / "off"
TOPIC_LED_STATUS = b"building-blocks/led/status"    # publish  — confirma "on" / "off"
TOPIC_DADOS      = b"building-blocks/dados"         # subscribe — recebe JSON com temperatura

TEMP_THRESHOLD   = 30.0  # °C

# ── Hardware ──────────────────────────────────────────────────────────────────

led = Pin(4, Pin.OUT)   # GPIO 4 → resistor 1kΩ → LED vermelho → GND

# Servo no GPIO 5, PWM 50 Hz
# duty_u16: 500µs = 0° (~1638), 2500µs = 180° (~8192)
servo = PWM(Pin(5))
servo.freq(50)

def servo_angle(duty):
    servo.duty_u16(duty)

def _ticks_ms():
    try:
        return time.ticks_ms()
    except AttributeError:
        return int(time.time() * 1000)

def _ticks_diff(now, previous):
    try:
        return time.ticks_diff(now, previous)
    except AttributeError:
        return now - previous

# Estado do modo ventilador (servo)
fan_mode = False
fan_last_step_ms = 0
fan_position = 0

# ── WiFi ──────────────────────────────────────────────────────────────────────

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(SSID, PASSWORD)

    print("Conectando ao WiFi", end="")
    while not wlan.isconnected():
        time.sleep(0.5)
        print(".", end="")

    print("\nWiFi conectado! IP:", wlan.ifconfig()[0])

# ── Controle do LED ───────────────────────────────────────────────────────────

def set_led(client, state: bool):
    led.value(1 if state else 0)
    status = "on" if state else "off"
    print(f"LED → {status.upper()}")

    try:
        client.publish(TOPIC_LED_STATUS, status.encode())
        print(f"Status publicado: '{status}'")
    except Exception as e:
        print("Falha ao publicar status:", e)
        raise

# ── Controle do Servo ─────────────────────────────────────────────────────────

def handle_temperature(temp):
    global fan_mode

    if temp > TEMP_THRESHOLD:
        if not fan_mode:
            fan_mode = True
            print(f"Temperatura {temp}°C > {TEMP_THRESHOLD}°C → modo ventilador ATIVADO")
    else:
        if fan_mode:
            fan_mode = False
            servo_angle(1802)
            print(f"Temperatura {temp}°C <= {TEMP_THRESHOLD}°C → modo ventilador DESATIVADO")

def update_servo_fan():
    global fan_last_step_ms, fan_position

    if not fan_mode:
        return

    now = _ticks_ms()
    if _ticks_diff(now, fan_last_step_ms) >= 800: 
        fan_position = 7864 if fan_position == 1802 else 1802
        servo_angle(fan_position)
        fan_last_step_ms = now

# ── Callback de mensagens recebidas ──────────────────────────────────────────

_client = None

def on_message(topic, msg):
    print(f"Recebido | tópico: {topic} | msg: {msg}")

    if topic == TOPIC_LED_CMD:
        cmd = msg.decode().strip().lower()
        if cmd == "on":
            set_led(_client, True)
        elif cmd == "off":
            set_led(_client, False)
        else:
            print(f"Comando inválido: '{cmd}' — use 'on' ou 'off'")

    elif topic == TOPIC_DADOS:
        try:
            data = json.loads(msg.decode())
            temp = data.get("temperature")
            if temp is not None:
                handle_temperature(float(temp))
            else:
                print("Campo 'temperature' não encontrado no JSON")
        except Exception as e:
            print("Erro ao processar dados de temperatura:", e)

# ── MQTT ──────────────────────────────────────────────────────────────────────

def connect_mqtt():
    global _client

    client = MQTTClient(
        client_id  = MQTT_CLIENT_ID,
        server     = MQTT_BROKER,
        port       = MQTT_PORT,
        user       = MQTT_USER,
        password   = MQTT_PASSWORD,
        ssl        = True,
        ssl_params = {"server_hostname": MQTT_BROKER},
        keepalive  = 30,
    )

    client.set_callback(on_message)
    print("Conectando ao broker MQTT...")
    client.connect()
    print("Conectado ao broker!")

    client.subscribe(TOPIC_LED_CMD)
    print(f"Subscrito em: {TOPIC_LED_CMD}")

    client.subscribe(TOPIC_DADOS)
    print(f"Subscrito em: {TOPIC_DADOS}")

    _client = client
    return client

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    connect_wifi()
    servo_angle(1802)

    client = None

    while True:
        if client is None:
            try:
                client = connect_mqtt()
            except Exception as e:
                print("Falha na conexão MQTT:", e)
                time.sleep(5)
                continue

        try:
            client.check_msg()   # não-bloqueante: dispara on_message se houver msg
        except Exception as e:
            print("Erro ao verificar mensagens:", e)
            client = None        # força reconexão no próximo ciclo
            continue

        update_servo_fan()

        time.sleep(0.1)

main()