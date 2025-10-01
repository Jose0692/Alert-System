###############################
## AGENTE DESARROLADO POR JJ ##
###############################

#VERSION DE PHYTON: 3.11.9

#DESCARGAR LIBRERIA PYSNMP
#pip uninstall pysnmp -y
#pip install pysnmp==4.4.12
#DESCARGAR LIBRERIA PYASN1
#pip uninstall pyasn1 -y
#pip install pyasn1==0.4.8

# LIBRERIAS NECESARIAS #

import threading
import json
import time
import os
import requests
import smtplib
from email.message import EmailMessage
import configparser
import requests
import json
import requests
import json
import socket
import re

url_cines="http://localhost:8000/cines"
url_zonas="http://localhost:8000/zonas"
url_paises="http://localhost:8000/paises"
url_salas="http://localhost:8000/salas"
smtp_server="smtp.office365.com"
noc_email="noc@cineplanet.com.pe"
pass_noc_email ="2025AV123/321"
whatsapp_number="51981283879"
url_whatsapp_api="https://graph.facebook.com/v22.0/745562308629793/messages"
authorization_beaver="Bearer EAAKPKAtBUfcBOxjxL5DgfCedIivJElYZCopK4uFjxcGsjtaMAFxBcBQ6uguNiZCiryw3OJqFGi9mEM9aTjID5TNDwtCR1RYHksfADzTm3XZC54rRj40pgW38ug6L6DTSgwBHJDDOWwTWZBdYdJeVXM6pAf512nGZCp9mqgTQyhOUbDVJ1Q7gr8sZAAdeSc0A0V5x6JZBNd7CdRfVaw39ZA05NYzRz41rGkfJXBwZD"

def cargar_config(ruta="config.json"):
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)

def generar_config(
    cine_id,
):
    try:
        # Consumir los servicios
        cines = requests.get(url_cines).json()
        zonas = requests.get(url_zonas).json()
        paises = requests.get(url_paises).json()
        salas = requests.get(url_salas).json()

        # Buscar cine
        cine = next((c for c in cines if c["id_cine"] == cine_id), None)
        if not cine:
            raise ValueError(f"Cine con id {cine_id} no encontrado")

        # Buscar zona
        zona = next((z for z in zonas if z["id_zona"] == cine["id_zona"]), None)
        if not zona:
            raise ValueError(f"Zona con id {cine['id_zona']} no encontrada")

        # Buscar país
        pais = next((p for p in paises if p["id_pais"] == zona["id_pais"]), None)
        if not pais:
            raise ValueError(f"País con id {zona['id_pais']} no encontrado")

        # Contar salas
        num_salas = sum(1 for s in salas if s["id_cine"] == cine_id)

        # Armar config completo
        config = {
            "cine_id": cine["id_cine"],
            "cine_numero": cine["num_cine"], 
            "cine_nombre": cine["nombre_cine"],
            "cine_num_salas": num_salas,
            "cine_pais": pais["nombre_pais"],
            "cine_zona": zona["nombre_zona"],
            "pais_octeto": pais["octeto_pais"],
            "zona_correo": zona["correo_zona"],
            "smtp_server" : smtp_server,
            "smtp_port" : 587,
            "email_user" : noc_email,
            "email_pass" : pass_noc_email,
            "telefono_wahtsapp" : whatsapp_number,
            "proyector_inicio": 22,
            "servidor_inicio": 26,
            "sala_salto": 16
        }

        # Guardar en config.info
        with open("config.json", "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        print("✅ Archivo config.info generado correctamente.")
        return config

    except Exception as e:
        print("⚠️ Error al generar config:", str(e))
        return None

def generar_ip(cine_config, tipo, indice):
    base = f"10.{cine_config['pais_octeto']}.{cine_config['cine_numero']}"
    if tipo == "proyector":
        host = cine_config['proyector_inicio'] + (indice * cine_config['sala_salto'])
    elif tipo == "servidor":
        host = cine_config['servidor_inicio'] + (indice * cine_config['sala_salto'])
    else:
        raise ValueError("Tipo desconocido")
    return f"{base}.{host}"

def generar_equipos(cine_config, archivo_json="estado_equipo.json"):

    if os.path.exists(archivo_json):
        try:
            with open(archivo_json, "r", encoding="utf-8") as f:
                equipos_existentes = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            equipos_existentes = []
    else:
        equipos_existentes = []
    
    equipos_nuevos = []
    for i in range(cine_config["cine_num_salas"]):
        sala_numero = i + 1
        
        proyector_ip = generar_ip(cine_config, "proyector", i)
        # Buscar si ya existe información de este proyector
        proyector_existente = next((eq for eq in equipos_existentes 
                                  if eq["ip"] == proyector_ip and eq["tipo"] == "proyector"), None)
        
        if proyector_existente:
            # Mantener datos existentes y actualizar estructura si es necesario
            equipo_proyector = {
                "tipo": "proyector",
                "sala": sala_numero,
                "ip": proyector_ip,
                "modelo": proyector_existente.get("modelo"),
                "estado_alerta": proyector_existente.get("estado_alerta"),
                "consumibles": proyector_existente.get("consumibles", []),
                "alertas": proyector_existente.get("alertas", []),
                "ultima_actualizacion": time.strftime("%Y-%m-%d %H:%M:%S"),
                "estado": proyector_existente.get("estado", "desconocido")
            }
        else:
            # Crear nuevo equipo
            equipo_proyector = {
                "tipo": "proyector",
                "sala": sala_numero,
                "ip": proyector_ip,
                "modelo": None,
                "estado_alerta": "Sin alerta",
                "consumibles": [],
                "alertas": [],
                "ultima_actualizacion": time.strftime("%Y-%m-%d %H:%M:%S"),
                "estado": "activo"
            }
        
        equipos_nuevos.append(equipo_proyector)
        
        # Servidor
        servidor_ip = generar_ip(cine_config, "servidor", i)
        # Buscar si ya existe información de este servidor
        servidor_existente = next((eq for eq in equipos_existentes 
                                 if eq["ip"] == servidor_ip and eq["tipo"] == "servidor"), None)
        
        if servidor_existente:
            equipo_servidor = {
                "tipo": "servidor",
                "sala": sala_numero,
                "ip": servidor_ip,
                "modelo": servidor_existente.get("modelo"),
                "consumibles": servidor_existente.get("consumibles", []),
                "alertas": servidor_existente.get("alertas", []),
                "ultima_actualizacion": time.strftime("%Y-%m-%d %H:%M:%S"),
                "estado": servidor_existente.get("estado", "desconocido")
            }
        else:
            equipo_servidor = {
                "tipo": "servidor",
                "sala": sala_numero,
                "ip": servidor_ip,
                "modelo": None,
                "consumibles": [],
                "alertas": [],
                "ultima_actualizacion": time.strftime("%Y-%m-%d %H:%M:%S"),
                "estado": "activo"
            }
        
        equipos_nuevos.append(equipo_servidor)
    
    # Guardar en el archivo JSON
    with open(archivo_json, "w", encoding="utf-8") as f:
        json.dump(equipos_nuevos, f, indent=4, ensure_ascii=False)
    
    print(f"Archivo {archivo_json} generado/actualizado con {len(equipos_nuevos)} equipos")
    return equipos_nuevos

def conectar_equipo_tcp(ip, puerto):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((ip, puerto))
        print(f"Conectado al proyector en {ip}:{puerto} por TCP")
        return s
    except Exception as e:
        print(f"Error al conectar por TCP: {e}")
        return None

def conectar_proyectores_tcp(archivo_json="estado_equipo.json", puerto=43728):

    conexiones = {}

    if not os.path.exists(archivo_json):
        print(f"El archivo {archivo_json} no existe.")
        return

    with open(archivo_json, "r", encoding="utf-8") as f:
        equipos = json.load(f)

    for equipo in equipos:
        if equipo.get("tipo") == "proyector":
            ip = equipo.get("ip")
            print(f"Intentando conectar al proyector en IP: {ip}")
            conexion = conectar_equipo_tcp(ip, puerto)
            if conexion:
                conexiones[ip] = conexion

    return conexiones

def enviar_comando_hex(s, comando_hex):
    try:
        comando = bytes.fromhex(comando_hex)
        s.sendall(comando)
        print(f"Comando enviado: {comando_hex}")
    except Exception as e:
        print(f"Error al enviar comando: {e}")

def leer_respuesta_ascii(s, buffer_size=4096, timeout=2):
    try:
        s.settimeout(timeout)
        data_total = b""
        while True:
            try:
                data = s.recv(buffer_size)
                if not data:
                    break
                data_total += data
            except socket.timeout:
                break
        
        if data_total:
                      
            try:
                ascii_text = data_total.decode("ascii", errors="ignore")
                print("Respuesta en ASCII:", ascii_text.strip())
            except Exception as e:
                print(f"No se pudo decodificar en ASCII: {e}")
        else:
            print("No se recibió respuesta")

        return data_total
    except Exception as e:
        print(f"Error al leer respuesta: {e}")
        return b""

def procesar_mensajes_texto(ascii_text):
    """Procesa mensajes de alertas en texto ignorando basura antes del XML"""
    # 🔎 Buscar dónde empieza realmente el XML
    inicio = ascii_text.find("<?xml")
    if inicio != -1:
        ascii_text = ascii_text[inicio:]
    else:
        print("⚠️ No se encontró XML en la respuesta")
        return

    # Buscar todos los mensajes <message ...> ... </message>
    patron = r'<message identifier="([^"]+)" type="([^"]+)">(.*?)</message>'
    coincidencias = re.findall(patron, ascii_text, re.DOTALL)

    if not coincidencias:
        print("⚠️ No se encontraron mensajes en la respuesta")
        return

    for idx, (identificador, tipo, alerta) in enumerate(coincidencias, start=1):
        print(f"\n📌 Mensaje {idx}")
        print(f"Identificador: {identificador}")
        print(f"Tipo: {tipo}")
        print(f"Alerta: {alerta.strip()}")

def consultar_tcp_numero_alertas(s):
    
    enviar_comando_hex(s, "FE 00 81 04 17 9C FF")
    data = leer_respuesta_ascii(s)
    if not data:
        return

    try:
        idx = data.index(bytes.fromhex("81 04 17"))
        valores = data[idx+3:idx+15]  # 12 bytes después de 81 04 17
        notificaciones = int.from_bytes(valores[0:4], "big")
        warnings = int.from_bytes(valores[4:8], "big")
        errores = int.from_bytes(valores[8:12], "big")

        if notificaciones == 0 and warnings == 0 and errores == 0:
            print("✅ No hay alertas activas")
        else:
            print(f"⚠️ Alertas activas -> Notificaciones: {notificaciones}, Warnings: {warnings}, Errores: {errores}")
            
            # Enviar FE 00 81 04 1A 9F FF si hay alertas
            enviar_comando_hex(s, "FE 00 81 04 1A 9F FF")
            data_alertas = leer_respuesta_ascii(s)
            if data_alertas:
                ascii_text = data_alertas.decode("ascii", errors="ignore")
                procesar_mensajes_texto(ascii_text)

    except ValueError:
        print("⚠️ No se encontró la cabecera 81 04 17 en la respuesta")

def consultar_tcp_estado(s, comando_hex, intervalo=5):
    print("Consultando estado por TCP...")

def consultar_snmp(ip, oid="1.3.6.1.2.1.1.1.0"):
    print("Aqui hago consultas SNMP", ip)

def enviar_alerta_correo(cine_config, complejo, sala, modelo, alertas):
  
    config = configparser.ConfigParser()
    config.read("config.ini")

    receiver_email = cine_config.get("zona_correo")
    receiver_email_cc = cine_config.get("email_user")
    smtp_server = cine_config.get("smtp_server")
    smtp_port = cine_config.get("smtp_port")
    email_user = cine_config.get("email_user")
    email_pass = cine_config.get("email_pass")

    if not alertas or all("SNMP error" in alerta for alerta in alertas):
        print("No hay alertas válidas para enviar por correo.")
        return

    subject = f"{complejo} | Sala {sala} | ALERTA DETECTADA"
    body = (
        f"📢 *Alerta detectada*\n\n"
        f"🎬 Complejo: {complejo}\n"
        f"🖥️ Sala: {sala}\n"
        f"📦 Modelo: {modelo}\n\n"
        f"⚠️ Alertas:\n" + "\n".join(alertas)
    )

    msg = EmailMessage()
    msg["From"] = email_user
    msg["To"] = receiver_email
    msg["Cc"] = receiver_email_cc
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        with smtplib.SMTP(smtp_server,smtp_port) as server:
            server.starttls()
            server.login(email_user, email_pass)
            server.send_message(msg)
            print(f"Email enviado a {', '.join(receiver_email)}")
    except Exception as e:
        print(f"Error al enviar correo: {str(e)}")

def enviar_alerta_whatsapp(cine_config, complejo, sala, modelo, alertas):
        
    config = configparser.ConfigParser()
    config.read("config.ini")
    
    telefono_wahtsapp = cine_config.get("telefono_wahtsapp")

    url = url_whatsapp_api
    headers = {
        "Authorization": authorization_beaver,
        "Content-Type": "application/json"
    }

    cuerpo = f" *Alerta en Complejo {complejo}*\n\n Sala: {sala}\n Mensaje: {alertas}"

    data = {
        "messaging_product": "whatsapp",
        "to": telefono_wahtsapp, 
        "type": "text",
        "text": {"body": cuerpo}
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        result = response.json()
        
        if response.status_code == 200:
            print("Mensaje enviado. ID:", result["messages"][0]["id"])
        else:
            print("Error:", result.get("error", {}).get("message", "Desconocido"))
            
    except Exception as e:
        print("Error en la conexión:", str(e))

def ciclo_monitoreo_continuo(cine_config):
    cine_config = cargar_config()
    num_salas = cine_config.get("cine_num_salas", 0)

    while True:  
        print("Consultando por alertas...")
        for i in range(num_salas):
            proyector_ip = generar_ip(cine_config, "proyector", i)
            servidor_ip  = generar_ip(cine_config, "servidor", i)

            resultado_tcp_proyector = consultar_tcp_estado(proyector_ip)
            resultado_tcp_servidor = consultar_tcp_estado(servidor_ip)

        print("Revision completa")
        
        time.sleep(1)

def ciclo_actualizacion_equipos(cine_config):
    generar_equipos(cine_config)
    print("Iniciando ciclo de actualizacion de equipos...")

if __name__ == "__main__":

    cine_config = cargar_config()
    generar_config(cine_config["cine_id"])

    time.sleep(3)

    cine_nueva_config = cargar_config()
    generar_equipos(cine_nueva_config)

    print("------------------------------------------------------------")
    print("---------------INICIANDO AGENTE DE MONITOREO----------------")
    print("------------------------------------------------------------")

    print("REVISION INICIAL COMPLETA, INICIANDO MONITOREO CONTINUO...")
    time.sleep(3)

    print("ESTABLECIENDO CONEXIONES TCP A PROYECTORES...")
    conexiones = conectar_proyectores_tcp()
    time.sleep(3)

    thead1 = threading.Thread(target=ciclo_monitoreo_continuo, args=(cine_nueva_config,))
    thead2 = threading.Thread(target=ciclo_actualizacion_equipos, args=(cine_nueva_config,))

    thead1.start()
    thead2.start()

    thead1.join()
    thead2.join()