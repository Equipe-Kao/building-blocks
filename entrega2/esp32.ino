#include <WiFi.h>
#include <HTTPClient.h>
#include "DHT.h"

#define DHTPIN 4
#define DHTTYPE DHT22

DHT dht (DHTPIN, DHTTYPE);

const char* ssid = "Wokwi-GUEST";
const char* password = "";
const char* serverUrl = "https://building-blocks-v8gg.onrender.com/api/dados";

unsigned long sendInterval = 5000;
unsigned long lastSend = 0;

void setup(){
  Serial.begin(115200);
  delay(1000);
  dht.begin();
  connectWiFi();
}

void loop(){
  if (millis() - lastSend > sendInterval) {
    lastSend = millis();
    float temperature;
    float humidity;
    
    if (readSensor (temperature, humidity)) {
      String jsonPayload = buildJson(temperature, humidity);
      sendHTTP(jsonPayload);
    }
  }
}

void connectWiFi() {
  Serial.println("Conectando ao WiFi...");
  WiFi.begin(ssid, password);
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
  }
  
  Serial.print(".");
  Serial.println("\nWiFi conectado!");
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());
}

bool readSensor (float &temperature, float &humidity) {
  humidity = dht.readHumidity();
  temperature = dht.readTemperature();
  
  if (isnan (humidity) || isnan (temperature)) {
    Serial.println("Erro ao ler DHT22");
    return false;
  }
  
  Serial.print("Temperatura: ");
  Serial.println(temperature);
  Serial.print("Umidade: ");
  Serial.println(humidity);
  
  return true;
}

String buildJson(int raw, float percent) {
  unsigned long timestamp = millis();
  String json = "{";
  json += "\"device_id\":\"esp32-01\",";
  json += "\"timestamp\":" + String(timestamp) + ",";
  json += "\"soil_moisture_raw\":" + String(raw) + ",";
  json += "\"soil_moisture_percent\":" + String(percent, 2);
  json += "}";
  
  Serial.println("JSON Gerado:");
  Serial.println(json);
  
  return json;
}

void sendHTTP(String payload) {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(serverUrl);
    http.addHeader("Content-Type", "application/json");
    
    int httpResponseCode = http.POST(payload);
    Serial.print("HTTP Response code: ");
    Serial.println(httpResponseCode);
    
    String response = http.getString();
    Serial.println("Resposta do servidor:");
    Serial.println(response);
    
    http.end();
  } else {
    Serial.println("WiFi desconectado.");
  }
}