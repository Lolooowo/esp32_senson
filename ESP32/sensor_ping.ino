#include <WiFi.h>
#include <HTTPClient.h>
#include <ESPping.h>
#include <DHT.h>
#include <ArduinoJson.h>

// ---------- Configuracion WiFi ----------
const char* ssid = "Juna";
const char* password = "moricalliope";

// ---------- API en tu PC ----------
const char* API_URL =
    "http://10.161.152.66:8000/mediciones";

const char* DISPOSITIVO = "esp32";

// ---------- Sensor DHT22 ----------
#define DHTPIN 4
#define DHTTYPE DHT22

DHT dht(DHTPIN, DHTTYPE);

// ---------- Destino del ping ----------
IPAddress destinoPing(10, 161, 152, 66);

// ---------- Intervalos ----------
const unsigned long INTERVALO_ENVIO = 10000;|
const unsigned long INTERVALO_RECONEXION = 15000;

unsigned long ultimoEnvio = 0;
unsigned long ultimaReconexion = 0;

bool wifiAnterior = false;


// ---------- Revisar conexion WiFi ----------
void revisarWiFi() {
  bool conectado = WiFi.status() == WL_CONNECTED;

  if (conectado != wifiAnterior) {
    wifiAnterior = conectado;

    if (conectado) {
      Serial.print("WiFi conectado. IP del ESP32: ");
      Serial.println(WiFi.localIP());
    } else {
      Serial.println("WiFi desconectado.");
    }
  }

  if (!conectado &&
      millis() - ultimaReconexion >= INTERVALO_RECONEXION) {

    ultimaReconexion = millis();

    Serial.println("Intentando reconectar al WiFi...");
    WiFi.reconnect();
  }
}


// ---------- Leer sensor, hacer ping y enviar ----------
void leerYEnviar() {
  Serial.println();
  Serial.println("========== NUEVA MEDICION ==========");

  float humedad = dht.readHumidity();
  float temperatura = dht.readTemperature();

  bool sensorCorrecto =
      !isnan(humedad) && !isnan(temperatura);

  if (sensorCorrecto) {
    Serial.print("Temperatura: ");
    Serial.print(temperatura, 2);

    Serial.print(" C | Humedad: ");
    Serial.print(humedad, 2);
    Serial.println(" %");
  } else {
    Serial.println(
        "Error DHT22: se enviaran valores null."
    );
  }

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println(
        "Sin WiFi: no se realiza ping ni envio."
    );
    return;
  }

  // Ejecutar ping.
  Serial.print("Haciendo ping a ");
  Serial.println(destinoPing);

  bool pingExitoso = Ping.ping(destinoPing, 4);
  float promedioPing = 0.0f;

  if (pingExitoso) {
    promedioPing = Ping.averageTime();

    Serial.print("Ping con respuesta. Promedio: ");
    Serial.print(promedioPing, 2);
    Serial.println(" ms");
  } else {
    Serial.println("Ping sin respuesta.");
  }

  // Construir JSON.
  // Estos nombres corresponden al modelo de FastAPI
  // que usamos anteriormente.
  JsonDocument documento;

  documento["dispositivo"] = DISPOSITIVO;
  documento["ip_destino"] = destinoPing.toString();
  documento["ping_exitoso"] = pingExitoso;

  if (sensorCorrecto) {
    documento["temperatura"] = temperatura;
    documento["humedad"] = humedad;
  } else {
    documento["temperatura"] = nullptr;
    documento["humedad"] = nullptr;
  }

  if (pingExitoso) {
    documento["ping_promedio_ms"] = promedioPing;
  } else {
    documento["ping_promedio_ms"] = nullptr;
  }

  String json;
  serializeJson(documento, json);

  Serial.println("JSON a enviar:");
  Serial.println(json);

  // Preparar solicitud HTTP.
  WiFiClient cliente;
  HTTPClient http;

  http.setConnectTimeout(5000);
  http.setTimeout(5000);

  if (!http.begin(cliente, API_URL)) {
    Serial.println(
        "No se pudo preparar la conexion HTTP."
    );
    return;
  }

  http.addHeader(
      "Content-Type",
      "application/json"
  );

  // Enviar datos.
  int codigoHTTP = http.POST(json);

  if (codigoHTTP > 0) {
    String respuesta = http.getString();

    Serial.print("Codigo HTTP: ");
    Serial.println(codigoHTTP);

    Serial.print("Respuesta API: ");
    Serial.println(respuesta);

    if (codigoHTTP == 201) {
      Serial.println(
          "La API confirmo el guardado en MySQL."
      );
    } else {
      Serial.println(
          "Respuesta inesperada: revisa el detalle de la API."
      );
    }
  } else {
    Serial.print("Error de conexion HTTP: ");
    Serial.println(
        HTTPClient::errorToString(codigoHTTP)
    );
  }

  http.end();

  Serial.println("===================================");
}


// ---------- Inicializacion ----------
void setup() {
  Serial.begin(115200);
  delay(2000);

  Serial.println("Iniciando monitoreo ESP32...");

  dht.begin();

  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);

  // Usa los nombres realmente declarados al principio.
  WiFi.begin(ssid, password);

  ultimaReconexion = millis();

  Serial.println("Intentando conectar al WiFi...");
}


// ---------- Bucle principal ----------
void loop() {
  revisarWiFi();

  if (millis() - ultimoEnvio >= INTERVALO_ENVIO) {
    leerYEnviar();

    // Esperar 10 segundos desde el final del ciclo.
    ultimoEnvio = millis();
  }

  delay(10);
}