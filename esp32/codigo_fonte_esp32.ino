#include <WiFi.h>
#include <PubSubClient.h>  tem que baixar essa
#include <time.h>

#define LED_VERMELHO 15
#define LED_VERDE    2
#define BOTAO        5
#define SENSOR_IR    16

const char* WIFI_SSID = "";
const char* WIFI_PASSWORD = "";

const char* MQTT_SERVER = "200.143.224.99";
const int MQTT_PORT = 1183;
const char* MQTT_USER = "AlunosIOT";
const char* MQTT_PASSWORD = "Brok3rIoT";

const char* TOPICO_LED = "AlertaRemedio/led";

WiFiClient espClient;
PubSubClient client(espClient);

bool verde = false;
bool objetoAntes = false;

unsigned long ultimoCiclo = 0;
#define INTERVALO_CICLO 10000UL

unsigned long ultimaTentativaWiFi = 0;
unsigned long ultimaTentativaMQTT = 0;

#define INTERVALO_WIFI 10000UL
#define INTERVALO_MQTT 5000UL

bool horarioConfigurado = false;

#define TAMANHO_FILA 10

String filaMQTT[TAMANHO_FILA];
int inicioFila = 0;
int fimFila = 0;
int quantidadeFila = 0;

void adicionarNaFila(String mensagem) {
  if (quantidadeFila >= TAMANHO_FILA) {
    return;
  }

  filaMQTT[fimFila] = mensagem;
  fimFila = (fimFila + 1) % TAMANHO_FILA;
  quantidadeFila++;
}

bool removerDaFila(String &mensagem) {
  if (quantidadeFila == 0) {
    return false;
  }

  mensagem = filaMQTT[inicioFila];
  inicioFila = (inicioFila + 1) % TAMANHO_FILA;
  quantidadeFila--;

  return true;
}

void configurarHorario() {
  if (horarioConfigurado) {
    return;
  }

  if (WiFi.status() != WL_CONNECTED) {
    return;
  }

  // Brasil: UTC-3 = -10800 segundos
  configTime(-10800, 0, "pool.ntp.org", "time.nist.gov");

  struct tm timeinfo;

  if (getLocalTime(&timeinfo)) {
    horarioConfigurado = true;
  }
}

String obterTimestamp() {
  struct tm timeinfo;

  if (horarioConfigurado && getLocalTime(&timeinfo)) {
    char buffer[25];
    strftime(buffer, sizeof(buffer), "%Y-%m-%d %H:%M:%S", &timeinfo);
    return String(buffer);
  }

  return "millis:" + String(millis());
}

void tentarConectarWiFi() {
  if (WiFi.status() == WL_CONNECTED) {
    configurarHorario();
    return;
  }

  if (ultimaTentativaWiFi != 0 && millis() - ultimaTentativaWiFi < INTERVALO_WIFI) {
    return;
  }

  ultimaTentativaWiFi = millis();

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
}

void tentarConectarMQTT() {
  if (WiFi.status() != WL_CONNECTED) {
    return;
  }

  if (client.connected()) {
    return;
  }

  if (ultimaTentativaMQTT != 0 && millis() - ultimaTentativaMQTT < INTERVALO_MQTT) {
    return;
  }

  ultimaTentativaMQTT = millis();

  if (client.connect("AlertaRemedioESP32", MQTT_USER, MQTT_PASSWORD)) {
    Serial.println("conectado");
  } else {
    Serial.print("falhou, codigo: ");
    Serial.println(client.state());
  }
}

void processarFilaMQTT() {
  if (!client.connected()) {
    return;
  }

  String mensagem;

  while (quantidadeFila > 0) {
    removerDaFila(mensagem);

    bool enviado = client.publish(TOPICO_LED, mensagem.c_str(), true);

    if (enviado) {
      Serial.print("MQTT enviado da fila: ");
      Serial.println(mensagem);
    } else {
      Serial.print("Não consegui enviar pro MQTT, devolvendo pra fila: ");
      Serial.println(mensagem);
      adicionarNaFila(mensagem);
      break;
    }
  }
}

void publicarMensagem(String mensagem) {
  if (client.connected()) {
    bool enviado = client.publish(TOPICO_LED, mensagem.c_str(), true);

    if (enviado) {
      Serial.print("MQTT enviado direto: ");
      Serial.println(mensagem);
    } else {
      adicionarNaFila(mensagem);
    }
  } else {
    adicionarNaFila(mensagem);
  }
}

void publicarLedLigado() {
  String cor;

  if (verde) {
    cor = "verde";
  } else {
    cor = "vermelho";
  }

  String timestamp = obterTimestamp();

  String payload = "{";
  payload += "\"cor\":\"" + cor + "\",";
  payload += "\"timestamp\":\"" + timestamp + "\"";
  payload += "}";

  publicarMensagem(payload);
}

void acenderVerde() {
  verde = true;

  digitalWrite(LED_VERDE, HIGH);
  digitalWrite(LED_VERMELHO, LOW);

  Serial.println("LED atual: verde");
}

void acenderVermelho() {
  verde = false;

  digitalWrite(LED_VERDE, LOW);
  digitalWrite(LED_VERMELHO, HIGH);

  Serial.println("LED atual: vermelho");
}

void setup() {
  Serial.begin(115200);

  pinMode(LED_VERMELHO, OUTPUT);
  pinMode(LED_VERDE, OUTPUT);
  pinMode(BOTAO, INPUT_PULLUP);
  pinMode(SENSOR_IR, INPUT);

  acenderVermelho();

  objetoAntes = (digitalRead(SENSOR_IR) == LOW);

  WiFi.mode(WIFI_STA);
  client.setServer(MQTT_SERVER, MQTT_PORT);

  ultimoCiclo = millis();
}

void loop() {
  tentarConectarWiFi();
  tentarConectarMQTT();

  if (client.connected()) {
    client.loop();
    processarFilaMQTT();
  }

  // Botão muda o estado do LED
  if (digitalRead(BOTAO) == LOW) {
    if (verde) {
      acenderVermelho();
    } else {
      acenderVerde();
    }

    delay(300);
  }

  // LOW = objeto detectado, HIGH = sem objeto
  bool objetoAgora = (digitalRead(SENSOR_IR) == LOW);

  // Acende verde quando o objeto sai da frente do sensor
  if (objetoAntes && !objetoAgora) {
    if (!verde) {
      acenderVerde();
    }
  }

  objetoAntes = objetoAgora;

  // Ciclo global:
  // a cada 5 segundos envia o estado atual com timestamp e depois deixa vermelho
  if (millis() - ultimoCiclo >= INTERVALO_CICLO) {
    ultimoCiclo = millis();

    publicarLedLigado();

    acenderVermelho();
  }
}