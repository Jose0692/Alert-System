import threading
import json
import time
import os
import requests
import smtplib
from email.message import EmailMessage
import json
import socket
import re
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler
import sys

# Cargar variables de entorno
load_dotenv('.env')

# Configuración del sistema de logging
def configurar_logging():
    """Configura el sistema de logging con formato ordenado y relevante"""
    
    # Crear directorio de logs si no existe
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Configurar el logger principal
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Evitar propagación a logger root
    logger.propagate = False
    
    # Formato ordenado y limpio
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Handler para archivo (con rotación)
    file_handler = RotatingFileHandler(
        'logs/agent_ubuntu.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    
    # Handler para consola (solo mensajes importantes)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # Limpiar handlers existentes y agregar nuevos
    logger.handlers.clear()
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# Inicializar logging
logger = configurar_logging()

class GestorConexionesTCP:
    def __init__(self, puerto=43728, timeout_conexion=5, timeout_lectura=2):
        self.puerto = puerto
        self.timeout_conexion = timeout_conexion
        self.timeout_lectura = timeout_lectura
        self.conexiones = {}
        self.estados_previos = {}
        self.logger = logging.getLogger('GestorConexionesTCP')
        
    def conectar_equipo(self, ip):
        """Establece conexión TCP con un equipo"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(self.timeout_conexion)
            s.connect((ip, self.puerto))
            self.logger.info(f"Conectado al proyector en {ip}:{self.puerto}")
            self.conexiones[ip] = s
            return s
        except Exception as e:
            self.logger.error(f"Error al conectar a {ip}: {e}")
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
            self.logger.warning(f"Conexión perdida con {ip}, reconectando...")
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
                self.logger.info(f"Conexión cerrada con {ip}")
            except Exception as e:
                self.logger.error(f"Error al cerrar conexión con {ip}: {e}")
        self.conexiones.clear()

gestor_conexiones = GestorConexionesTCP()

def cargar_config_cine(ruta="config_cine.json"):
    logger = logging.getLogger('ConfigLoader')
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            config = json.load(f)
        logger.info(f"Configuración cargada desde {ruta}")
        return config
    except Exception as e:
        logger.error(f"Error al cargar configuración: {e}")
        raise

def generar_config_cine(cine_id):
    logger = logging.getLogger('ConfigGenerator')
    try:
        # Consumir los servicios
        url_cines = os.getenv("url_cines")
        url_zonas = os.getenv("url_zonas")
        url_paises = os.getenv("url_paises")
        url_salas = os.getenv("url_salas")
        
        logger.info("Obteniendo datos de servicios...")
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
            "telefono_wahtsapp": os.getenv("whatsapp_number"),
            "proyector_inicio": 22,
            "servidor_inicio": 26,
            "sala_salto": 16
        }

        # Guardar en config.info
        with open("config_cine.json", "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        logger.info(f"Archivo config_cine.json generado para cine {cine['nombre_cine']} con {num_salas} salas")
        return config

    except Exception as e:
        logger.error(f"Error al generar configuración: {e}")
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
    logger = logging.getLogger('EquiposGenerator')
    try:
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
        
        logger.info(f"Archivo {archivo_json} actualizado con {len(equipos_nuevos)} equipos")
        return equipos_nuevos
        
    except Exception as e:
        logger.error(f"Error al generar equipos: {e}")
        raise

def enviar_comando_hex(s, comando_hex):
    logger = logging.getLogger('ComandoTCP')
    try:
        comando = bytes.fromhex(comando_hex)
        s.sendall(comando)
        logger.debug(f"Comando enviado: {comando_hex}")
    except Exception as e:
        logger.error(f"Error al enviar comando: {e}")
        raise

def leer_respuesta_ascii(s, buffer_size=4096, timeout=2):
    logger = logging.getLogger('RespuestaTCP')
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
            logger.debug(f"Respuesta recibida: {len(data_total)} bytes")
        else:
            logger.warning("No se recibió respuesta")
            
        return data_total
    except Exception as e:
        logger.error(f"Error al leer respuesta: {e}")
        return b""

def procesar_mensajes_texto(ascii_text):
    """Procesa mensajes de alertas en texto ignorando basura antes del XML y retorna las alertas"""
    logger = logging.getLogger('ProcesadorAlertas')
    alertas_encontradas = []
    
    inicio = ascii_text.find("<?xml")
    if inicio != -1:
        ascii_text = ascii_text[inicio:]
    else:
        logger.warning("No se encontró XML en la respuesta")
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
        logger.warning("No se encontraron mensajes en la respuesta")
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
        logger.debug(f"Mensaje {idx} - Tipo: {tipo}, ID: {identificador}")
        
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

    logger.info(f"Procesadas {len(alertas_encontradas)} alertas")
    return alertas_encontradas

def consultar_tcp_numero_alertas(s):
    """Consulta el número de alertas activas y retorna las descripciones"""
    logger = logging.getLogger('ConsultorAlertas')
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
            logger.debug("No hay alertas activas")
            return False, []
        else:
            logger.warning(f"Alertas activas - Notificaciones: {notificaciones}, Warnings: {warnings}, Errores: {errores}")
            
            enviar_comando_hex(s, "FE 00 81 04 1A 9F FF")
            data_alertas = leer_respuesta_ascii(s)
            alertas_descripciones = []
            if data_alertas:
                ascii_text = data_alertas.decode("ascii", errors="ignore")
                alertas_descripciones = procesar_mensajes_texto(ascii_text)
            
            return True, alertas_descripciones

    except ValueError:
        logger.warning("No se encontró la cabecera 81 04 17 en la respuesta")
        return False, []

def monitorear_proyector(ip, cine_config, intervalo=2):
    """Monitorea un proyector específico en bucle infinito"""
    logger = logging.getLogger(f'Monitoreo.{ip}')
    logger.info(f"Iniciando monitoreo para proyector {ip}")
    
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
                    logger.info(f"Cambio de estado detectado en {ip}")
                    
                    # Consultar alertas si hay cambio
                    hay_alertas, descripciones_alertas = consultar_tcp_numero_alertas(s)
                    
                    # Verificar si ha pasado el tiempo mínimo desde el último correo
                    tiempo_actual = time.time()
                    if hay_alertas and descripciones_alertas and (tiempo_actual - ultimo_envio_correo) > tiempo_minimo_entre_alertas:
                        sala_numero = obtener_sala_por_ip(ip, cine_config)
                        logger.warning(f"Alertas detectadas en Sala {sala_numero} - IP: {ip}")
                        
                        # Enviar alerta por correo con las descripciones REALES
                        if enviar_alerta_correo(
                            cine_config, 
                            cine_config["cine_nombre"], 
                            sala_numero, 
                            "Proyector", 
                            descripciones_alertas
                        ):
                            ultimo_envio_correo = tiempo_actual
                            logger.info(f"Alerta enviada. Próxima alerta para {ip} en {tiempo_minimo_entre_alertas//60} minutos")
                    
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
                            logger.info(f"Alerta genérica enviada para {ip}")
                
                estado_previo = estado_actual
            else:
                logger.error(f"No se pudo establecer conexión con {ip}")
            
            time.sleep(intervalo)
            
        except Exception as e:
            logger.error(f"Error en monitoreo de {ip}: {e}")
            time.sleep(intervalo)

def obtener_sala_por_ip(ip, cine_config):
    for i in range(cine_config["cine_num_salas"]):
        proyector_ip = generar_ip(cine_config, "proyector", i)
        if proyector_ip == ip:
            return i + 1
    return "Desconocida"

def inicializar_conexiones_proyectores(cine_config):
    logger = logging.getLogger('InicializadorConexiones')
    logger.info("Inicializando conexiones TCP con proyectores...")
    
    for i in range(cine_config["cine_num_salas"]):
        proyector_ip = generar_ip(cine_config, "proyector", i)
        logger.info(f"Conectando a {proyector_ip}...")
        gestor_conexiones.conectar_equipo(proyector_ip)
        time.sleep(0.2)

def ciclo_monitoreo_continuo(cine_config):
    logger = logging.getLogger('CicloMonitoreo')
    logger.info("Iniciando monitoreo continuo de proyectores...")
    
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
        logger.info(f"Monitoreo iniciado para {proyector_ip}")
    
    # Mantener el hilo principal vivo
    try:
        while True:
            time.sleep(60)
            logger.debug("Monitoreo activo...")
    except KeyboardInterrupt:
        logger.info("Deteniendo monitoreo por interrupción de usuario")
        gestor_conexiones.cerrar_todas_conexiones()

def ciclo_actualizacion_equipos(cine_config):
    """Ciclo para actualizar información de equipos"""
    logger = logging.getLogger('ActualizadorEquipos')
    logger.info("Iniciando ciclo de actualización de equipos")
    
    while True:
        try:
            generar_equipos(cine_config)
            logger.info("Información de equipos actualizada")
            time.sleep(3600)  # Actualizar cada hora
        except Exception as e:
            logger.error(f"Error en actualización de equipos: {e}")
            time.sleep(300)  # Reintentar en 5 minutos si hay error

def enviar_alerta_correo(cine_config, complejo, sala, modelo, alertas):
    """Envía alerta por correo electrónico al zona_correo y como CCO al NOC"""
    logger = logging.getLogger('EmailSender')
    try:
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
                "icon": "",
                "titulo": "ERROR DETECTADO"
            },
            "warning": {
                "gradient": "linear-gradient(135deg, #d97706, #f59e0b)",
                "icon": "",
                "titulo": "ADVERTENCIA DETECTADA"
            },
            "notification": {
                "gradient": "linear-gradient(135deg, #2563eb, #3b82f6)",
                "icon": "",
                "titulo": "NOTIFICACION DETECTADA"
            }
        }

        color_config = colores[tipo_alerta]

        msg = EmailMessage()
        msg['Subject'] = f"Alerta detectada - {complejo} - Sala {sala}"
        msg['From'] = os.getenv("noc_email")
        msg['To'] = cine_config["zona_correo"]
        msg['Bcc'] = os.getenv("noc_email")

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
                    color: #292423;
                    font-weight: bold;
                }}
                .info-value {{
                    font-size: 10px;
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
                        padding:8px 8px;
                        color:#ffffff;
                        font-family:'Segoe UI',Arial,sans-serif;">
                <h1 style="margin:0;font-size:20px;font-weight:bold;color:#ffffff;">
                    {color_config['icon']} {color_config['titulo']}
                </h1>
            </div>

                <div class="section">
                    <div class="section-title">Información del equipo</div>
                    <div class="info-grid">
                        <div class="info-item"><span class="info-label">Complejo</span><span class="info-value">{complejo}</span></div>
                        <div class="info-item"><span class="info-label">Sala</span><span class="info-value">{sala}</span></div>
                        <div class="info-item"><span class="info-label">Equipo</span><span class="info-value">{modelo}</span></div>
                        <div class="info-item"><span class="info-label">Zona</span><span class="info-value">{cine_config['cine_zona']}</span></div>
                        <div class="info-item"><span class="info-label">País</span><span class="info-value">{cine_config['cine_pais']}</span></div>
                        <div class="info-item"><span class="info-label">Fecha</span><span class="info-value">{time.strftime('%Y-%m-%d %H:%M:%S')}</span></div>
                    </div>
                </div>

                <div class="section">
                    <div class="section-title">Alertas Detectadas</div>
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
                    <strong>Sistema de Monitoreo - NOC Audiovisual</strong><br>
                    Este mensaje es enviado automáticamente por el equipo NOC. No responder.<br>
                    {time.strftime('%Y-%m-%d %H:%M:%S')}
                </div>
            </div>
        </body>
        </html>
        """

        msg = EmailMessage()
        msg['Subject'] = f"Alerta detectada - {complejo} - Sala {sala}"
        msg['From'] = os.getenv("noc_email")
        msg['To'] = cine_config["zona_correo"]
        msg['Bcc'] = os.getenv("noc_email")

        # [Código HTML del correo...]
        
        msg.set_content(cuerpo, subtype='html')

        with smtplib.SMTP(os.getenv("smtp_server"), os.getenv("smtp_port")) as server:
            server.starttls()
            server.login(os.getenv("noc_email"), os.getenv("pass_noc_email"))
            server.send_message(msg)

        logger.info(f"Correo de alerta '{tipo_alerta}' enviado correctamente a {cine_config['zona_correo']}")
        return True

    except Exception as e:
        logger.error(f"Error al enviar correo de alerta: {e}")
        return False

def consultar_snmp(ip, oid="1.3.6.1.2.1.1.1.0"):
    logger = logging.getLogger('SNMP')
    logger.debug(f"Consultando SNMP a {ip} con OID {oid}")

if __name__ == "__main__":
    try:
        logger.info("Iniciando Agente de Monitoreo Ubuntu")
        
        cine_config = cargar_config_cine()
        generar_config_cine(cine_config["cine_id"])

        time.sleep(3)

        cine_nueva_config = cargar_config_cine()
        generar_equipos(cine_nueva_config)

        logger.info("Agente inicializado correctamente")

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

        logger.info("Todos los hilos iniciados correctamente")

        # Mantener el hilo principal vivo
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Agente detenido por el usuario")
            gestor_conexiones.cerrar_todas_conexiones()

    except Exception as e:
        logger.critical(f"Error crítico en el agente: {e}")
        gestor_conexiones.cerrar_todas_conexiones()