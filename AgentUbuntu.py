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
noc_email="jpardo@cineplanet.com.pe"
pass_noc_email ="PlanetCineJP23$"
whatsapp_number="51981283879"
url_whatsapp_api="https://graph.facebook.com/v22.0/745562308629793/messages"
authorization_beaver="Bearer EAAKPKAtBUfcBOxjxL5DgfCedIivJElYZCopK4uFjxcGsjtaMAFxBcBQ6uguNiZCiryw3OJqFGi9mEM9aTjID5TNDwtCR1RYHksfADzTm3XZC54rRj40pgW38ug6L6DTSgwBHJDDOWwTWZBdYdJeVXM6pAf512nGZCp9mqgTQyhOUbDVJ1Q7gr8sZAAdeSc0A0V5x6JZBNd7CdRfVaw39ZA05NYzRz41rGkfJXBwZD"

class GestorConexionesTCP:
    def __init__(self, puerto=43728, timeout_conexion=5, timeout_lectura=2):
        self.puerto = puerto
        self.timeout_conexion = timeout_conexion
        self.timeout_lectura = timeout_lectura
        self.conexiones = {}
        self.estados_previos = {}
        
    def conectar_equipo(self, ip):
        """Establece conexión TCP con un equipo"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(self.timeout_conexion)
            s.connect((ip, self.puerto))
            print(f"✅ Conectado al proyector en {ip}:{self.puerto}")
            self.conexiones[ip] = s
            return s
        except Exception as e:
            print(f"❌ Error al conectar a {ip}: {e}")
            return None
    
    def verificar_conexion(self, ip):
        """Verifica si la conexión sigue activa y reconecta si es necesario"""
        if ip not in self.conexiones:
            return self.conectar_equipo(ip)
        
        s = self.conexiones[ip]
        try:
            # Intentar enviar un comando de prueba para verificar conexión
            s.settimeout(1)
            enviar_comando_hex(s, "FE 00 81 04 04 89 FF")
            data = s.recv(1)  # Intentar leer al menos un byte
            return s
        except:
            print(f"🔌 Conexión perdida con {ip}, reconectando...")
            try:
                s.close()
            except:
                pass
            return self.conectar_equipo(ip)
    
    def obtener_conexion(self, ip):
        """Obtiene una conexión activa, reconectando si es necesario"""
        return self.verificar_conexion(ip)
    
    def cerrar_todas_conexiones(self):
        """Cierra todas las conexiones activas"""
        for ip, s in self.conexiones.items():
            try:
                s.close()
                print(f"🔌 Conexión cerrada con {ip}")
            except Exception as e:
                print(f"⚠️ Error al cerrar conexión con {ip}: {e}")
        self.conexiones.clear()

gestor_conexiones = GestorConexionesTCP()

def cargar_config_cine(ruta="config_cine.json"):
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)

def generar_config_cine(cine_id):
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
            "smtp_server": smtp_server,
            "smtp_port": 587,
            "email_user": noc_email,
            "email_pass": pass_noc_email,
            "telefono_wahtsapp": whatsapp_number,
            "proyector_inicio": 22,
            "servidor_inicio": 26,
            "sala_salto": 16
        }

        # Guardar en config.info
        with open("config_cine.json", "w", encoding="utf-8") as f:
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
        proyector_existente = next((eq for eq in equipos_existentes 
                                  if eq["ip"] == proyector_ip and eq["tipo"] == "proyector"), None)
        
        if proyector_existente:
            equipo_proyector = {
                "tipo": "proyector",
                "sala": sala_numero,
                "ip": proyector_ip,
                "modelo": proyector_existente.get("modelo"),
                "estado_alerta": proyector_existente.get("estado_alerta"),
                "consumibles": proyector_existente.get("consumibles", []),
                "alertas": proyector_existente.get("alertas", []),
                "ultima_actualizacion": time.strftime("%Y-%m-%d %H:%M:%S"),
                "estado_actual_tcp": "estado_actual_tcp",
                "estado": proyector_existente.get("estado", "desconocido")
            }
        else:
            equipo_proyector = {
                "tipo": "proyector",
                "sala": sala_numero,
                "ip": proyector_ip,
                "modelo": None,
                "estado_alerta": "Sin alerta",
                "consumibles": [],
                "alertas": [],
                "ultima_actualizacion": time.strftime("%Y-%m-%d %H:%M:%S"),
                "estado_actual_tcp": "estado_actual_tcp",
                "estado": "activo"
            }
        
        equipos_nuevos.append(equipo_proyector)
        
        servidor_ip = generar_ip(cine_config, "servidor", i)
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
                "estado_actual_tcp": "estado_actual_tcp",
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
                "estado_actual_tcp": "estado_actual_tcp",
                "estado": "activo"
            }
        
        equipos_nuevos.append(equipo_servidor)
    
    with open(archivo_json, "w", encoding="utf-8") as f:
        json.dump(equipos_nuevos, f, indent=4, ensure_ascii=False)
    
    print(f"Archivo {archivo_json} generado/actualizado con {len(equipos_nuevos)} equipos")
    return equipos_nuevos

def enviar_comando_hex(s, comando_hex):
    try:
        comando = bytes.fromhex(comando_hex)
        s.sendall(comando)
        print(f"Comando enviado: {comando_hex}")
    except Exception as e:
        print(f"Error al enviar comando: {e}")
        raise

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
            except Exception as e:
                print(f"No se pudo decodificar en ASCII: {e}")
        else:
            print("No se recibió respuesta")

        return data_total
    except Exception as e:
        print(f"❌ Error al leer respuesta: {e}")
        return b""

def procesar_mensajes_texto(ascii_text):
    """Procesa mensajes de alertas en texto ignorando basura antes del XML y retorna las alertas"""
    alertas_encontradas = []
    
    inicio = ascii_text.find("<?xml")
    if inicio != -1:
        ascii_text = ascii_text[inicio:]
    else:
        print("⚠️ No se encontró XML en la respuesta")
        return alertas_encontradas

    # Patrón mejorado para capturar más detalles del XML
    patrones = [
        r'<message identifier="([^"]+)" type="([^"]+)">(.*?)</message>',
        r'<alert[^>]*code="([^"]*)"[^>]*>([^<]*)</alert>',
        r'<error[^>]*>([^<]*)</error>',
        r'<warning[^>]*>([^<]*)</warning>'
    ]
    
    # Buscar mensajes principales
    coincidencias = re.findall(patrones[0], ascii_text, re.DOTALL)

    if not coincidencias:
        print("⚠️ No se encontraron mensajes en la respuesta")
        # Intentar buscar otros patrones
        for patron in patrones[1:]:
            otras_coincidencias = re.findall(patron, ascii_text, re.DOTALL)
            if otras_coincidencias:
                for coincidencia in otras_coincidencias:
                    if isinstance(coincidencia, tuple):
                        alerta_texto = " - ".join(filter(None, coincidencia))
                    else:
                        alerta_texto = coincidencia
                    alertas_encontradas.append(f"ALERTA - {alerta_texto}")
        return alertas_encontradas

    for idx, (identificador, tipo, alerta) in enumerate(coincidencias, start=1):
        print(f"\n📌 Mensaje {idx}")
        print(f"Identificador: {identificador}")
        print(f"Tipo: {tipo}")
        print(f"Alerta: {alerta.strip()}")
        
        # Limpiar y formatear la alerta
        alerta_limpia = re.sub(r'\s+', ' ', alerta.strip())
        
        # Agregar a la lista de alertas con formato mejorado
        alerta_info = f"{tipo.upper()} - Código: {identificador} - Descripción: {alerta_limpia}"
        alertas_encontradas.append(alerta_info)
        
        # Buscar detalles adicionales dentro del mensaje
        detalles_patron = r'<detail[^>]*>([^<]*)</detail>'
        detalles = re.findall(detalles_patron, alerta, re.DOTALL)
        for detalle in detalles:
            detalle_limpio = re.sub(r'\s+', ' ', detalle.strip())
            if detalle_limpio:
                alertas_encontradas.append(f"   └─ Detalle: {detalle_limpio}")

    return alertas_encontradas

def consultar_tcp_numero_alertas(s):
    """Consulta el número de alertas activas y retorna las descripciones"""
    enviar_comando_hex(s, "FE 00 81 04 17 9C FF")
    data = leer_respuesta_ascii(s)
    if not data:
        return False, []

    try:
        idx = data.index(bytes.fromhex("81 04 17"))
        valores = data[idx+3:idx+15]
        notificaciones = int.from_bytes(valores[0:4], "big")
        warnings = int.from_bytes(valores[4:8], "big")
        errores = int.from_bytes(valores[8:12], "big")

        if notificaciones == 0 and warnings == 0 and errores == 0:
            print("✅ No hay alertas activas")
            return False, []
        else:
            print(f"⚠️ Alertas activas -> Notificaciones: {notificaciones}, Warnings: {warnings}, Errores: {errores}")
            
            enviar_comando_hex(s, "FE 00 81 04 1A 9F FF")
            data_alertas = leer_respuesta_ascii(s)
            alertas_descripciones = []
            if data_alertas:
                ascii_text = data_alertas.decode("ascii", errors="ignore")
                alertas_descripciones = procesar_mensajes_texto(ascii_text)
            
            return True, alertas_descripciones

    except ValueError:
        print("⚠️ No se encontró la cabecera 81 04 17 en la respuesta")
        return False, []

def monitorear_proyector(ip, cine_config, intervalo=2):
    """Monitorea un proyector específico en bucle infinito"""
    print(f"🎬 Iniciando monitoreo para proyector {ip}")
    
    estado_previo = None
    alertas_activas = []  # Para almacenar las alertas actuales
    ultimo_envio_correo = 0  # Timestamp del último correo enviado
    tiempo_minimo_entre_alertas = 200  # 4 minutos entre alertas (en segundos)
    
    while True:
        try:
            # Obtener conexión (se reconecta automáticamente si es necesario)
            s = gestor_conexiones.obtener_conexion(ip)
            
            if s:
                # Consultar estado actual
                enviar_comando_hex(s, "FE 00 81 04 04 89 FF")
                estado_actual = leer_respuesta_ascii(s)
                
                # Verificar si hay cambio de estado
                if estado_previo and estado_actual != estado_previo:
                    print(f"🔄 Cambio de estado detectado en {ip}")
                    
                    # Consultar alertas si hay cambio - AHORA CAPTURAMOS LAS DESCRIPCIONES
                    hay_alertas, descripciones_alertas = consultar_tcp_numero_alertas(s)
                    
                    # Verificar si ha pasado el tiempo mínimo desde el último correo
                    tiempo_actual = time.time()
                    if hay_alertas and descripciones_alertas and (tiempo_actual - ultimo_envio_correo) > tiempo_minimo_entre_alertas:
                        sala_numero = obtener_sala_por_ip(ip, cine_config)
                        print(f"🚨 Alertas detectadas en Sala {sala_numero} - IP: {ip}")
                        print(f"📋 Detalles de alertas: {descripciones_alertas}")
                        
                        # Enviar alerta por correo con las descripciones REALES
                        if enviar_alerta_correo(
                            cine_config, 
                            cine_config["cine_nombre"], 
                            sala_numero, 
                            "Proyector", 
                            descripciones_alertas  # Usar las alertas reales del proyector
                        ):
                            ultimo_envio_correo = tiempo_actual  # Actualizar timestamp
                            print(f"⏰ Próxima alerta para {ip} en {tiempo_minimo_entre_alertas//60} minutos")
                    
                    elif hay_alertas and (tiempo_actual - ultimo_envio_correo) > tiempo_minimo_entre_alertas:
                        # Si hay alertas pero no se pudieron obtener las descripciones
                        sala_numero = obtener_sala_por_ip(ip, cine_config)
                        descripciones_genericas = [
                            "Alerta detectada en proyector - No se pudieron obtener detalles específicos",
                            f"IP del equipo: {ip}",
                            f"Sala: {sala_numero}"
                        ]
                        
                        if enviar_alerta_correo(
                            cine_config, 
                            cine_config["cine_nombre"], 
                            sala_numero, 
                            "Proyector", 
                            descripciones_genericas
                        ):
                            ultimo_envio_correo = tiempo_actual
                            print(f"⏰ Próxima alerta para {ip} en {tiempo_minimo_entre_alertas//60} minutos")
                
                estado_previo = estado_actual
            else:
                print(f"❌ No se pudo establecer conexión con {ip}")
            
            time.sleep(intervalo)
            
        except Exception as e:
            print(f"❌ Error en monitoreo de {ip}: {e}")
            time.sleep(intervalo)

def obtener_sala_por_ip(ip, cine_config):
    for i in range(cine_config["cine_num_salas"]):
        proyector_ip = generar_ip(cine_config, "proyector", i)
        if proyector_ip == ip:
            return i + 1
    return "Desconocida"

def inicializar_conexiones_proyectores(cine_config):
    print("Inicializando conexiones TCP con proyectores...")
    
    for i in range(cine_config["cine_num_salas"]):
        proyector_ip = generar_ip(cine_config, "proyector", i)
        print(f"Conectando a {proyector_ip}...")
        gestor_conexiones.conectar_equipo(proyector_ip)
        time.sleep(0.2)  

def ciclo_monitoreo_continuo(cine_config):
    print("🎯 Iniciando monitoreo continuo de proyectores...")
    
    # Inicializar conexiones
    inicializar_conexiones_proyectores(cine_config)
    
    # Crear e iniciar hilos de monitoreo para cada proyector
    hilos = []
    for i in range(cine_config["cine_num_salas"]):
        proyector_ip = generar_ip(cine_config, "proyector", i)
        hilo = threading.Thread(
            target=monitorear_proyector, 
            args=(proyector_ip, cine_config, 10),
            daemon=True
        )
        hilo.start()
        hilos.append(hilo)
        print(f"📊 Monitoreo iniciado para {proyector_ip}")
    
    # Mantener el hilo principal vivo
    try:
        while True:
            time.sleep(60)
            print("💓 Monitoreo activo...")
    except KeyboardInterrupt:
        print("\n🛑 Deteniendo monitoreo...")
        gestor_conexiones.cerrar_todas_conexiones()

def ciclo_actualizacion_equipos(cine_config):
    """Ciclo para actualizar información de equipos"""
    while True:
        try:
            generar_equipos(cine_config)
            print("✅ Información de equipos actualizada")
            time.sleep(3600)  # Actualizar cada hora
        except Exception as e:
            print(f"❌ Error en actualización de equipos: {e}")
            time.sleep(300)  # Reintentar en 5 minutos si hay error

import smtplib
import re
import time
from email.message import EmailMessage

import smtplib
import re
import time
from email.message import EmailMessage

import smtplib
from email.message import EmailMessage
import time
import re

def enviar_alerta_correo(cine_config, complejo, sala, modelo, alertas):
    """Envía alerta por correo electrónico al zona_correo y como CCO al NOC"""
    try:
        noc_email = cine_config.get("noc_email", "jmoreno@cineplanet.com.pe")  # aseguramos variable

        # Detectar tipo principal de alerta
        tipo_alerta = "error"
        if alertas:
            for alerta in alertas:
                alerta_upper = alerta.upper()
                if "WARNING" in alerta_upper:
                    tipo_alerta = "warning"
                    break
                elif "NOTIFICATION" in alerta_upper:
                    tipo_alerta = "notification"
            for alerta in alertas:
                if "ERROR" in alerta.upper():
                    tipo_alerta = "error"
                    break

        colores = {
            "error": {
                "gradient": "linear-gradient(135deg, #dc2626, #ef4444)",
                "icon": "🚨",
                "titulo": "Alerta Crítica Detectada",
                "subtitulo": "Sistema de Monitoreo - Proyector"
            },
            "warning": {
                "gradient": "linear-gradient(135deg, #d97706, #f59e0b)",
                "icon": "",
                "titulo": "Advertencia Técnica",
                "subtitulo": "Sistema de Monitoreo - Proyector"
            },
            "notification": {
                "gradient": "linear-gradient(135deg, #2563eb, #3b82f6)",
                "icon": "ℹ️",
                "titulo": "Notificación del Sistema",
                "subtitulo": "Sistema de Monitoreo - Proyector"
            }
        }

        color_config = colores[tipo_alerta]

        msg = EmailMessage()
        msg['Subject'] = f"{color_config['icon']} {color_config['titulo']} - {complejo} - Sala {sala}"
        msg['From'] = cine_config["email_user"]
        msg['To'] = cine_config["zona_correo"]
        msg['Bcc'] = noc_email

        cuerpo = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: 'Segoe UI', 'Roboto', sans-serif;
                    background-color: #f8fafc;
                    color: #333;
                    padding: 20px;
                }}
                .container {{
                    max-width: 600px;
                    margin: auto;
                    background: #fff;
                    border-radius: 12px;
                    overflow: hidden;
                    box-shadow: 0 4px 10px rgba(0,0,0,0.1);
                }}
                .header {{
                    background: {color_config['gradient']};
                    color: #ffffff !important;
                    text-align: center;
                    padding: 24px 16px;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 22px;
                    font-weight: 700;
                    line-height: 1.4;
                }}
                .header .subtitle {{
                    margin-top: 6px;
                    font-size: 14px;
                    font-weight: 400;
                    color: #ffffff !important;
                    opacity: 1 !important;
                }}
                .section {{
                    padding: 20px 24px;
                    border-bottom: 1px solid #e2e8f0;
                }}
                .section-title {{
                    font-weight: 600;
                    margin-bottom: 16px;
                    color: #1e293b;
                }}
                .info-grid {{
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 10px;
                }}
                .info-item span {{
                    display: block;
                }}
                .info-label {{
                    font-size: 12px;
                    color: #64748b;
                    text-transform: uppercase;
                }}
                .info-value {{
                    font-size: 14px;
                    font-weight: 500;
                }}
                .alert-list {{
                    display: flex;
                    flex-direction: column;
                    gap: 12px;
                }}
                .alert-item {{
                    position: relative;
                    padding: 16px 16px 16px 36px;
                    border-radius: 8px;
                    border-left: 4px solid;
                    background: #f9fafb;
                    line-height: 1.5;
                    font-size: 14px;
                }}
                .alert-number {{
                    position: absolute;
                    top: 10px;
                    left: 10px;
                    background: #111827;
                    color: #fff;
                    border-radius: 50%;
                    width: 20px;
                    height: 20px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 12px;
                    font-weight: 600;
                }}
                .alert-item.error {{
                    background: #fef2f2;
                    border-color: #dc2626;
                }}
                .alert-item.warning {{
                    background: #fffbeb;
                    border-color: #d97706;
                }}
                .alert-item.notification {{
                    background: #eff6ff;
                    border-color: #2563eb;
                }}
                .alert-item.error .alert-number {{
                    background: #dc2626;
                }}
                .alert-item.warning .alert-number {{
                    background: #d97706;
                }}
                .alert-item.notification .alert-number {{
                    background: #2563eb;
                }}
                mark {{
                    background: #1e293b;
                    color: #f8fafc;
                    padding: 2px 5px;
                    border-radius: 3px;
                    font-family: monospace;
                    font-size: 12px;
                }}
                .footer {{
                    background: #f1f5f9;
                    padding: 16px;
                    text-align: center;
                    font-size: 12px;
                    color: #64748b;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div style="background:{'red' if tipo_alerta=='error' else ('#facc15' if tipo_alerta=='warning' else '#3b82f6')};
                        text-align:center;
                        padding:30px 20px;
                        color:#ffffff;
                        font-family:'Segoe UI',Arial,sans-serif;">
                <h1 style="margin:0;font-size:26px;font-weight:bold;color:#ffffff;">
                    {color_config['icon']} {color_config['titulo']}
                </h1>
                <p style="margin:6px 0 0 0;font-size:15px;color:#ffffff;">
                    {color_config['subtitulo']}
                </p>
            </div>

                <div class="section">
                    <div class="section-title">📋 Información del Equipo</div>
                    <div class="info-grid">
                        <div class="info-item"><span class="info-label">Complejo</span><span class="info-value">{complejo}</span></div>
                        <div class="info-item"><span class="info-label">Sala</span><span class="info-value">{sala}</span></div>
                        <div class="info-item"><span class="info-label">Modelo</span><span class="info-value">{modelo}</span></div>
                        <div class="info-item"><span class="info-label">Zona</span><span class="info-value">{cine_config['cine_zona']}</span></div>
                        <div class="info-item"><span class="info-label">País</span><span class="info-value">{cine_config['cine_pais']}</span></div>
                        <div class="info-item"><span class="info-label">Fecha</span><span class="info-value">{time.strftime('%Y-%m-%d %H:%M:%S')}</span></div>
                    </div>
                </div>

                <div class="section">
                    <div class="section-title">🔍 Alertas Técnicas Detectadas</div>
                    <div class="alert-list">
        """

        if alertas:
            for i, alerta in enumerate(alertas, 1):
                tipo_item = "error"
                alerta_upper = alerta.upper()
                if "WARNING" in alerta_upper:
                    tipo_item = "warning"
                elif "NOTIFICATION" in alerta_upper:
                    tipo_item = "notification"

                alerta_fmt = re.sub(r"(Código:\s*\w+)", r"<mark>\1</mark>", alerta)
                alerta_fmt = re.sub(r"(ID:\s*\w+)", r"<mark>\1</mark>", alerta_fmt)
                alerta_fmt = re.sub(r"(ERROR|WARNING|NOTIFICATION)", r"<strong>\1</strong>", alerta_fmt)

                cuerpo += f"""
                        <div class="alert-item {tipo_item}">
                            <div class="alert-number">{i}</div>
                            <div>{alerta_fmt}</div>
                        </div>
                """
        else:
            cuerpo += """
                        <div class="alert-item error">
                            <div class="alert-number">!</div>
                            <div>No se especificaron detalles de las alertas</div>
                        </div>
            """

        cuerpo += f"""
                    </div>
                </div>
                <div class="footer">
                    <strong>Sistema de Monitoreo NOC Audiovisual</strong><br>
                    Este es un mensaje automático, por favor no responder.<br>
                    {time.strftime('%Y-%m-%d %H:%M:%S')}
                </div>
            </div>
        </body>
        </html>
        """

        msg.set_content(cuerpo, subtype='html')

        with smtplib.SMTP(cine_config["smtp_server"], cine_config["smtp_port"]) as server:
            server.starttls()
            server.login(cine_config["email_user"], cine_config["email_pass"])
            server.send_message(msg)

        print(f"✅ Correo de alerta '{tipo_alerta}' enviado correctamente.")
        return True

    except Exception as e:
        print(f"❌ Error al enviar correo de alerta: {e}")
        return False

def consultar_snmp(ip, oid="1.3.6.1.2.1.1.1.0"):
    print("Aqui hago consultas SNMP", ip)

if __name__ == "__main__":
    try:
        cine_config = cargar_config_cine()
        generar_config_cine(cine_config["cine_id"])

        time.sleep(3)

        cine_nueva_config = cargar_config_cine()
        generar_equipos(cine_nueva_config)

        print("------------------------------------------------------------")
        print("---------------INICIANDO AGENTE DE MONITOREO----------------")
        print("------------------------------------------------------------")

        # Iniciar ciclos en hilos separados
        thread_monitoreo = threading.Thread(
            target=ciclo_monitoreo_continuo, 
            args=(cine_nueva_config,),
            daemon=True
        )
        
        thread_actualizacion = threading.Thread(
            target=ciclo_actualizacion_equipos, 
            args=(cine_nueva_config,),
            daemon=True
        )

        thread_monitoreo.start()
        thread_actualizacion.start()

        print("Agente inicializado correctamente")

        # Mantener el hilo principal vivo
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nAgente detenido por el usuario")
            gestor_conexiones.cerrar_todas_conexiones()

    except Exception as e:
        print(f"Error crítico: {e}")
        gestor_conexiones.cerrar_todas_conexiones()