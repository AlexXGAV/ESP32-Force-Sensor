from machine import ADC, Pin, RTC, SoftI2C
from time import sleep_ms, gmtime, time
import os
import utime
import network
import ntptime
import usocket as socket 
import _thread
import ssd1306
import gfx

PASSWORD = "123456789"
SSID = "SENSOR"

FSR_PIN = 32
adc = ADC(Pin(FSR_PIN))
adc.atten(ADC.ATTN_11DB) 	#ADC_ATTEN_DB_11 | 150 mV ~ 2450 mV
adc.width(ADC.WIDTH_12BIT)  #
RM = 1000.0 #RM ohm
VIN = 2.450 #V
MAXVALUE = 4095 #Max analog read value

rtc = RTC()
# Configuración del bus I2C
i2c = SoftI2C(scl=Pin(22), sda=Pin(21), freq=400000)  # Asegúrate de usar los pines GPIO correctos

# Crear objeto de pantalla OLED
OLED_WIDTH = 128
OLED_HEIGHT = 64
oled = ssd1306.SSD1306_I2C(OLED_WIDTH, OLED_HEIGHT, i2c)
graphics = gfx.GFX(OLED_WIDTH, OLED_HEIGHT, oled.pixel)

TIMEOUT_WIFI = 5000
FILENAME = "sensor_data.txt"
FILENAME_ID = "id_counter.txt"
FILENAME_DATE = "date.txt"

def display_principal(line1="", line2="", line3=""):
    info = "pass: "+PASSWORD if network.WLAN(network.AP_IF).active() else "ssid: "+SSID
    oled.fill(0)  # Limpiar la pantalla
    oled.text(str(gmtime(time())[2])+"-"+str(gmtime(time())[1])+"-"+str(gmtime(time())[0]), 0, 0)
    oled.text("Sensor Value:", 0, 8)
    oled.text(line1, 0, 20)
    oled.text(line2, 0, 30)
    oled.text(f"{info}" if not line3 == "" else line3, 0, 40)
    oled.text(f"{get_ip()}", 0, 50)
    oled.show()

def show_rect(rect=0, state=0):
    if rect == 1:
        graphics.fill_rect(85, 0, 10, 8, state)
        oled.show()
    if rect == 2:
        graphics.fill_rect(100, 0, 28, 8, state)
        oled.show()
    if rect == 3:
        graphics.fill_rect(0, 20, 128, 20, 0)

def display_sensor_value(value, max_value):
    show_rect(2,1)
    show_rect(3)
    oled.text("{:.9f}".format(value), 0, 20)
    oled.text("MAX {:.9f}".format(max_value), 0, 30)
    oled.show()

def parse_csv_line(line):
    parts = line.replace("(", "").replace(")", "").strip().split(',')

    if len(parts) >= 4:
        try:
            return [(parts[0]), (parts[1]), (parts[-2]), (parts[-1])]
        
        except (ValueError, IndexError) as e:
            display_principal("Error al procesar csv:",f"{e}")
            print(f"Error al procesar la línea: {line}, Error: {e}")
            return []
    else:
        display_principal("Error al procesar","csv: No hay","suficientes elementos")
        print(f"Error: La línea no tiene suficientes elementos: {parts}")
        return []


def get_last_10_readings():
    try:
        with open(FILENAME, 'r') as file:
            lines = file.readlines()

        # Excluye la primera línea (encabezado)
        data_lines = lines[1:]

        # Toma las últimas 10 líneas si hay suficientes, de lo contrario, toma todas las líneas disponibles
        last_10_lines = data_lines[-10:] if len(data_lines) >= 10 else data_lines

        return [parse_csv_line(line) for line in last_10_lines]
    except OSError as e:
        display_principal("Error al leer","el archivo CSV:",f"{e}")
        print("Error al leer el archivo CSV:", e)
        
        return []


def generate_html_table(data):
    # Genera una tabla HTML a partir de la lista de datos
    html_table = "<table border='1'><tr><th>ID</th><th>Date</th><th>Analog Data</th><th>Force (g)</th></tr>"
    
    for row in data:
        try:

            # Asegúrate de que la lista tenga al menos 4 elementos antes de intentar acceder a los índices específicos
            if len(row) >= 4:
                # Utiliza la cadena de fecha directamente
                html_table += f"<tr><td>{row[0]}</td><td>{row[1]}</td><td>{row[2]}</td><td>{row[3]}</td></tr>"
            else:
                display_principal("Error la fila no tiene ","suficientes elementos: {row}")
                print(f"Error: La fila no tiene suficientes elementos: {row}")
        except Exception as e:
            display_principal("Error al procesar la fila ","{row}")
            print(f"Error al procesar la fila: {row}, Error: {e}")

    html_table += "</table>"
    return html_table

def get_ip():
    return network.WLAN(network.AP_IF).ifconfig()[0] if network.WLAN(network.AP_IF).active() else network.WLAN(network.STA_IF).ifconfig()[0]

def connect_to_wifi(ssid, password):
    wlan = network.WLAN(network.STA_IF)
    
    if not wlan.isconnected():
        display_principal("Conectando WiFi...",f"{ssid}")
        print("Conectándose a la red WiFi...")
        wlan.active(True)
        wlan.connect(ssid, password)

        sleep_ms(TIMEOUT_WIFI)
        
        if wlan.isconnected():
            display_principal("Conexión WiFi","exitosa!")
            print(f"Conexión WiFi exitosa {get_ip()}")
            
        else:
            display_principal("Iniciando punto","de acceso...")
            print("No se pudo conectar a la red WiFi. Iniciando punto de acceso.")
            # Configurar el ESP32 como un punto de acceso
            wlan.active(False)  # Desactivar la interfaz de cliente
            ap = network.WLAN(network.AP_IF)
            ap.active(True)
            ap.config(essid=ssid, password=password, authmode=network.AUTH_WPA_WPA2_PSK)
            print("Configuración de punto de acceso completada")
            display_principal("Configuración AP","completada!!")
    else:
        display_principal("WiFi ya","conectado!")
        print("Ya está conectado a la red WiFi")

def set_ntp_time():
    try:
        # Configura el servidor NTP para obtener la hora
        ntptime.settime()
        (year, month, mday, weekday, hour, minute, second, milisecond)=rtc.datetime()
        rtc.init((year, month, mday, weekday, hour-6, minute, second, milisecond))
        
        print("Tiempo obtenido del servidor NTP y ajustado a la zona horaria de México")
        display_principal("Tiempo obtenido","y ajustado")
    except OSError as e:
        print("Error al obtener la hora desde el servidor NTP:", e)
        
        try:
            # Intenta obtener la hora desde un archivo local
            with open(FILENAME_DATE, 'r') as file:
                year = int(file.readline().strip())
                month = int(file.readline().strip())
                mday = int(file.readline().strip())
                hour = int(file.readline().strip())
                minute = int(file.readline().strip())
                second = int(file.readline().strip())
                
            (_, _, _, weekday, _, _, _, milisecond)=rtc.datetime()
            rtc.datetime((year, month, mday, weekday, hour, minute, second, milisecond))
            print("Tiempo obtenido de archivo local")
            display_principal("Tiempo obtenido","de archivo local")
        except OSError as e:
            print("Error al obtener la hora desde el archivo local:", e)
            display_principal("Tiempo","no sincronizado")

def get_force(x):
    force = 0
    #R_FSR = [(Vin*R)/Vo] - R
    Vo = x * VIN / MAXVALUE #0-4095 -> 0V - 2.45V
    #print("Vo:",Vo)
    if Vo != 0:
        resistance = ((VIN * RM / Vo) - RM)/1000.0 #kohm
        #print(f"RM: {resistance} kOhm")
        force = abs(resistance/153.18) **(-1/0.6991)
    return float(force)

def get_next_id():
    try:
        with open(FILENAME_ID, 'r') as file:
            current_id = int(file.read())
    except OSError as e:
        print("Error al leer el contador de ID:", e)
        current_id = 0
        display_principal("Error al leer ID",f"{e}")
    try:
        with open(FILENAME_ID, 'w') as file:
            file.write(str(current_id + 1))
    except OSError as e:
        print("Error al escribir el contador de ID:", e)
        display_principal("Error escribir ID",f"{e}")
    return current_id

def save_to_csv(data):
    try:
        # Intenta abrir el archivo en modo de adición ('a')
        with open(FILENAME, mode='a') as file:
            # Verifica si el archivo está vacío
            file.seek(0, 2)  # Utiliza 2 como SEEK_END
            if file.tell() == 0:
                # Si el archivo está vacío, escribe los encabezados
                file.write("ID,Date,Analog Data,Force (g)\n")
    except OSError:
        # Si no se puede abrir, el archivo probablemente no existe, entonces crea los encabezados
        with open(FILENAME, 'w') as file:
            file.write("ID,Date,Analog Data,Force (g)\n")
    
    try:
        # Ahora, abre el archivo en modo de adición y agrega los nuevos datos
        with open(FILENAME, mode='a') as file:
            file.write(','.join(map(str, data)) + '\n')
    except OSError as e:
        print("Error al escribir en el archivo CSV:", e)
        display_principal("Error escribir CSV",f"{e}")

def main_loop():
    # Intenta obtener la hora desde el servidor NTP
    set_ntp_time()
    max_value = 0.0
    while True:
        fsrReading = adc.read()
        #print(fsrReading)
        if fsrReading > 31:
            # Si no se pudo obtener la hora desde NTP, utiliza la hora interna del ESP32
            # Obtén la fecha y hora actual con microsegundos
            current_time_us = rtc.datetime()
            
            formatted_time = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}.{:06d}".format(
                current_time_us[0], current_time_us[1], current_time_us[2],
                current_time_us[4], current_time_us[5], current_time_us[6],
                current_time_us[7]
            )

            fsrForce = get_force(fsrReading)
            data_to_save = [get_next_id(), formatted_time, fsrReading, "{:.9f}".format(fsrForce)]
            save_to_csv(data_to_save)
            if fsrForce > max_value: 
                max_value = fsrForce
            display_sensor_value(fsrForce, max_value)

        else:
            show_rect(2,0)
        sleep_ms(10)

def start_web_server():
    addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(addr)
    s.listen(1)
    print('Listening on', addr)
    
    while True:
        try:
            conn, addr = s.accept()
            print('Connection from', addr)
            request = conn.recv(1024)
            print('Content received')
            show_rect(1, 1)

            # Manejar la solicitud de descarga
            if b'GET /download' in request:
                with open(FILENAME, 'r') as file:
                    file_content = file.read()
                download_response = "HTTP/1.1 200 OK\nContent-Type: text/csv\nContent-Disposition: attachment; filename=sensor_data.csv\n\n"
                download_response += file_content
                conn.send(download_response.encode())
            # Manejar la solicitud POST para configurar el RTC manualmente
            elif b'POST /config' in request:
                try:
                    # Obtener los datos del cuerpo de la solicitud POST
                    content = request.decode('utf-8').split('\r\n')
                    config_data = content[-1]
                    print("data sended", config_data)

                    # Dividir los datos en un diccionario de parámetros
                    params = {}
                    for param in config_data.split('&'):
                        key, value = param.split('=')
                        params[key] = value

                    (year_, month_, day_, weekday_, hour_, minute_, second_, milisecond_) = rtc.datetime()

                    # Extraer y convertir los valores del diccionario
                    year = int(params.get('year', year_)) if 'year' in params and params['year'] else year_
                    month = int(params.get('month', month_)) if 'month' in params and params['month'] else month_
                    day = int(params.get('day', day_)) if 'day' in params and params['day'] else day_
                    hour = int(params.get('hour', hour_)) if 'hour' in params and params['hour'] else hour_
                    minute = int(params.get('minute', minute_)) if 'minute' in params and params['minute'] else minute_
                    second = int(params.get('second', second_)) if 'second' in params and params['second'] else second_


                    # Configurar el RTC
                    rtc.datetime((year, month, day, weekday_, hour, minute, second, milisecond_))

                    # Guardar la configuración en el archivo date.txt
                    with open(FILENAME_DATE, 'w') as date_file:
                        date_file.write(f"{year}\n{month}\n{day}\n{hour}\n{minute}\n{second}")

                    response = "HTTP/1.1 200 OK\nContent-Type: text/html\n\n<html><meta charset='UTF-8'><meta name='viewport' content='width=device-width, initial-scale=1.0'><body><h1>RTC Configurado</h1></body></html>"
                    conn.send(response.encode())
                except Exception as e:
                    print("Error configurando el RTC:", e)
                    response = "HTTP/1.1 500 Internal Server Error\nContent-Type: text/html\n\n<html><meta charset='UTF-8'><meta name='viewport' content='width=device-width, initial-scale=1.0'><body><h1>Error interno del servidor</h1></body></html>"
                    conn.send(response.encode())
            # Manejar la solicitud POST para borrar la base de datos
            elif b'POST /delete' in request:
                try:
                    # Mostrar un formulario de confirmación en el navegador
                    delete_confirm_response = "HTTP/1.1 200 OK\nContent-Type: text/html\n\n"
                    delete_confirm_response += "<html><meta charset='UTF-8'><meta name='viewport' content='width=device-width, initial-scale=1.0'><body><h1>¿Estás seguro de que deseas borrar la base de datos?</h1>"
                    delete_confirm_response += "<form action='/confirmed_delete' method='post'>"
                    delete_confirm_response += "<input type='submit' value='Sí'>"
                    delete_confirm_response += "</form>"
                    delete_confirm_response += "</body></html>"
                    # Agregar botón para cancelar y redirigir a la página principal
                    delete_confirm_response += "<form action='/' method='get'>"
                    delete_confirm_response += "<input type='submit' value='No'>"
                    delete_confirm_response += "</form>"
                    delete_confirm_response += "</body></html>"
                    conn.send(delete_confirm_response.encode())
                except Exception as e:
                    print("Error mostrando el formulario de confirmación:", e)
            # Manejar la solicitud POST para confirmar y borrar la base de datos
            elif b'POST /confirmed_delete' in request:
                try:
                    # Borrar la base de datos (archivo sensor_data)
                    os.remove(FILENAME)
                    with open(FILENAME_ID, 'w') as file:
                        file.write(str(0))
                    print("Base de datos borrada")
                    
                    # Respuesta de confirmación
                    response = "HTTP/1.1 200 OK\nContent-Type: text/html\n\n"
                    response += "<html><meta charset='UTF-8'><meta name='viewport' content='width=device-width, initial-scale=1.0'><body><h1>Base de datos borrada exitosamente</h1></body></html>"
                    conn.send(response.encode())
                except Exception as e:
                    print("Error borrando la base de datos:", e)
            else:
                # Respuesta normal para la página web
                last_10_readings = get_last_10_readings()
                (year_, month_, day_, _, hour_, minute_, second_, _) = rtc.datetime()
                response = "HTTP/1.1 200 OK\nContent-Type: text/html\n\n<html><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width, initial-scale=1.0'><title>Sensor de Fuerza</title></head><body><h1>Sensor de Fuerza</h1><h2>Últimas 10 Lecturas</h2>"
                response += generate_html_table(last_10_readings)

                # Formulario para configurar manualmente el RTC
                response += "<h2>Configurar RTC Manualmente</h2>"
                response += "<form action='/config' method='post'>"
                response += f"Año: <input type='number' name='year' placeholder='{year_}'><br>"
                response += f"Mes: <input type='number' name='month' placeholder='{month_}'><br>"
                response += f"Día: <input type='number' name='day' placeholder='{day_}'><br>"
                response += f"Hora: <input type='number' name='hour' placeholder='{hour_}'><br>"
                response += f"Minuto: <input type='number' name='minute' placeholder='{minute_}'><br>"
                response += f"Segundo: <input type='number' name='second' placeholder='{second_}'><br>"
                response += "<input type='submit' value='Configurar RTC'>"
                response += "</form>"

                # Agregar botón de descarga con encabezados adicionales
                response += "<h2>Descargar Base de Datos</h2>"
                response += "<form action='/download' method='get'>"
                response += "<input type='submit' value='Descargar Base de Datos'>"
                response += "</form>"

                # Botón y formulario para borrar la base de datos
                response += "<h2>Borrar Base de Datos</h2>"
                response += "<form action='/delete' method='post'>"
                response += "<input type='submit' value='Borrar Base de Datos'>"
                response += "</form></body></html>"

                conn.send(response.encode())
        except Exception as e:
            print("Error handling request:", e)
        finally:
            conn.close()
            show_rect(1, 0)

if __name__ == "__main__":
    display_principal("Iniciando ESP32...")
    connect_to_wifi(ssid=SSID, password=PASSWORD)
    _thread.start_new_thread(main_loop, ())
    start_web_server()
