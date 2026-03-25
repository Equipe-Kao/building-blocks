import os
import network
import time
import json
import dht
from machine import Pin
from umqtt.simple import MQTTClient
from secrets import MQTT_USER, MQTT_PASSWORD

# ── Configurações ─────────────────────────────────────────────────────────────

SSID     = "Wokwi-GUEST"
PASSWORD = ""

MQTT_BROKER    = "d10f080e92054ccf9261241b924702f1.s1.eu.hivemq.cloud"
MQTT_PORT      = 8883
MQTT_CLIENT_ID = "esp32-01"
MQTT_TOPIC     = b"building-blocks/dados"

SEND_INTERVAL = 3  # segundos

# ── Sensor ────────────────────────────────────────────────────────────────────

sensor = dht.DHT22(Pin(4))

# ── WiFi ──────────────────────────────────────────────────────────────────────

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(SSID, PASSWORD)

    print("Conectando ao WiFi", end="")
    while not wlan.isconnected():
        time.sleep(0.5)
        print(".", end="")

    print("\nWiFi conectado!")
    print("IP:", wlan.ifconfig()[0])

# ── Sensor ────────────────────────────────────────────────────────────────────

def read_sensor():
    try:
        sensor.measure()
        temperature = sensor.temperature()
        humidity    = sensor.humidity()
        print(f"Temperatura: {temperature}")
        print(f"Umidade: {humidity}")
        return temperature, humidity
    except Exception as e:
        print("Erro ao ler DHT22:", e)
        return None, None

# ── JSON ──────────────────────────────────────────────────────────────────────

def build_json(temperature, humidity):
    payload = {
        "device_id":   "esp32-01",
        "timestamp":   time.ticks_ms(), # type: ignore
        "temperature": round(temperature, 2),
        "humidity":    round(humidity, 2),
    }
    result = json.dumps(payload)
    print("JSON gerado:", result)
    return result

# ── MQTT ──────────────────────────────────────────────────────────────────────

def connect_mqtt():
    client = MQTTClient(
        client_id = MQTT_CLIENT_ID,
        server    = MQTT_BROKER,
        port      = MQTT_PORT,
        user      = MQTT_USER,
        password  = MQTT_PASSWORD,
        ssl       = True,
        ssl_params = {"server_hostname": MQTT_BROKER},
    )

    print("Conectando ao broker MQTT...")
    client.connect()
    print("Conectado!")
    return client

def publish(client, payload):
    try:
        client.publish(MQTT_TOPIC, payload.encode())
        print("Mensagem publicada com sucesso")
    except Exception as e:
        print("Falha ao publicar:", e)
        raise  # sobe o erro para reconectar no loop

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    connect_wifi()

    client = None

    while True:
        if client is None:
            try:
                client = connect_mqtt()
            except Exception as e:
                print("Falha na conexão MQTT:", e)
                time.sleep(5)
                continue

        temperature, humidity = read_sensor()

        if temperature is not None:
            payload = build_json(temperature, humidity)
            try:
                publish(client, payload)
            except Exception:
                client = None  # força reconexão no próximo ciclo

        time.sleep(SEND_INTERVAL)

main()