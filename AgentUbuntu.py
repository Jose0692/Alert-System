###############################
## AGENTE DESARROLADO POR JJ ##
###############################

#Version de python: 3.11.9

########################
## CONFIGURACION SMTP ##
########################

#Descargar libreria PYSNMP
#pip uninstall pysnmp -y
#pip install pysnmp==4.4.12
#Descargar libreria PYASN1
#pip uninstall pyasn1 -y
#pip install pyasn1==0.4.8

# LIBRERIAS NECESARIAS #
import smtplib
import time
from pysnmp.hlapi import (
    SnmpEngine, CommunityData, UdpTransportTarget,
    ContextData, ObjectType, ObjectIdentity, getCmd
)
import importlib
from email.message import EmailMessage

# CONFIGURACION SNMP #
proyectores = {
    "1": {"ip": "10.234.86.22", "status_proyector": 0, "screen_number": "Sala 1", "location_name": "Santa Catalina"},
    "2": {"ip": "10.234.86.38", "status_proyector": 0, "screen_number": "Sala 2", "location_name": "Santa Catalina"},
    "3": {"ip": "10.234.86.54", "status_proyector": 0, "screen_number": "Sala 3", "location_name": "Santa Catalina"},
    "4": {"ip": "10.234.86.70", "status_proyector": 0, "screen_number": "Sala 4", "location_name": "Santa Catalina"},
    "5": {"ip": "10.234.86.86", "status_proyector": 0, "screen_number": "Sala 5", "location_name": "Santa Catalina"},
    "6": {"ip": "10.234.86.102", "status_proyector": 0, "screen_number": "Sala 6", "location_name": "Santa Catalina"}
}

community = "public" 
oid_model = '1.3.6.1.2.1.1.1.0' 
oid_name = '1.3.6.1.2.1.1.5.0' 
oid = '1.3.6.1.4.1.12612.220.11.2.2.10.5.1.2.1' # OID para descripcion de alerta activa
#oid_horas_consumidas = '1.3.6.1.4.1.12612.220.11.2.2.4.8.1.2.1'  # OID para hora de lampara consumida
#oid_horas_restantes = '1.3.6.1.4.1.12612.220.11.2.2.4.8.1.2.1'  # OID para hora de lampara consumida
oid_error_global  = '1.3.6.1.4.1.12612.220.11.2.3.0.10.0'
oid_warning  = '1.3.6.1.4.1.12612.220.11.2.3.0.11.0'
oid_notification = '1.3.6.1.4.1.12612.220.11.2.3.0.12.0'

# CONSULTA SNMP #
def snmp_get(ip, community, oid):
    error_indication, error_status, error_index, var_binds = next(
        getCmd(SnmpEngine(),
               CommunityData(community, mpModel=0),  # SNMPv1
               UdpTransportTarget((ip, 161)),
               ContextData(),
               ObjectType(ObjectIdentity(oid)))
    )

    if error_indication:
        return f"SNMP error: {error_indication}"
    elif error_status:
        return f"{error_status.prettyPrint()}"
    else:
        for varBind in var_binds:
            return f'{varBind[1]}'
        
# CONFIGURACIÓN DE ENVIO DE CORREO #
email = "noc@cineplanet.com.pe"
password = "2025AV123/321"
receiver_emails = ["jpardo@cineplanet.com.pe"] 
smtp_server = "smtp.office365.com"
port = 587

def capturar_envio_alerta(proyector_data):  

    target_ip = proyector_data["ip"]  
    location_name = proyector_data["location_name"]
    screen_number = proyector_data["screen_number"]
    status_proyector = proyector_data["status_proyector"]

    # OBTENER INFO SNMP
    device_alert_warning = snmp_get(target_ip, community, oid_error_global) # LECTURA DE ALERTA DE ADVERTENCIA

    if status_proyector == device_alert_warning :
        print(f"No hay alertas para {target_ip}")
    else:
        proyector_data["status_proyector"] = device_alert_warning

        device_alert_description = snmp_get(target_ip, community, oid)
        device_model = snmp_get(target_ip, community, oid_model)

        alert_detail = []
        type_alert = ""
        code_alert = ""

        # Procesar alertas (sin cambios)
        if "SNMP error" in device_alert_description or "No Such Instance" in device_alert_description:
            alert_detail.append(f"Error en la consulta SNMP: {device_alert_description}")
        else:
            alerts = device_alert_description.split('\n') if '\n' in device_alert_description else [device_alert_description]
            
            for alert in alerts:
                parts = alert.split()
                if len(parts) >= 3:
                    type_alert = parts[0]  
                    if type_alert=="W":
                        type_alert = "Advertencia"
                    code_alert = parts[1]  
                    alert_text = ' '.join(parts[2:]) 
                    alert_detail.append(alert_text)
                else:
                    alert_detail.append(alert)

        # Solo enviar correo si hay alertas
        if alert_detail and any(alert.strip() for alert in alert_detail if "SNMP error" not in alert):
            msg = EmailMessage()
            msg['From'] = email
            msg['To'] = ", ".join(receiver_emails)
            msg['Subject'] = f"{location_name} | Sala {screen_number} | {alert_detail}" 
            msg.set_content(f"Complejo: {location_name}\nSala: {screen_number}\nModelo: {device_model}\nAlertas:\n" + "\n".join(alert_detail))

            try:
                with smtplib.SMTP(smtp_server, port) as server:
                    server.starttls()
                    server.login(email, password)
                    server.send_message(msg)
                    print(f"Email enviado para {target_ip}")
            except Exception as e:
                print(f"Error al enviar correo para {target_ip}: {str(e)}")
        else:
            print(f"No se envió correo para {target_ip} - No hay alertas válidas")

# PROCESA CADA IP EN LA LISTA #
def monitorizar_ips(proyectores, intervalo=10):
    print("Iniciando monitoreo de proyectores...")
    while True:
        try:
            for proyector_id, proyector_data in proyectores.items():
                print(f"\nConsultando proyector {proyector_id} ({proyector_data['ip']})...")
                capturar_envio_alerta(proyector_data)
            time.sleep(intervalo)
        except KeyboardInterrupt:
            print("\nMonitor detenido manualmente")
            break

if __name__ == "__main__":
    monitorizar_ips(proyectores, intervalo=10)    

###################################
## ENVIO DE MENSAJE POR WHATSAPP ##
###################################

#import requests

#url = "https://graph.facebook.com/v22.0/745562308629793/messages"
#headers = {
#    "Authorization": "Bearer EAAKPKAtBUfcBOxjxL5DgfCedIivJElYZCopK4uFjxcGsjtaMAFxBcBQ6uguNiZCiryw3OJqFGi9mEM9aTjID5TNDwtCR1RYHksfADzTm3XZC54rRj40pgW38ug6L6DTSgwBHJDDOWwTWZBdYdJeVXM6pAf512nGZCp9mqgTQyhOUbDVJ1Q7gr8sZAAdeSc0A0V5x6JZBNd7CdRfVaw39ZA05NYzRz41rGkfJXBwZD",
#    "Content-Type": "application/json"
#}
#data = {
#    "messaging_product": "whatsapp",
#    "to": "51981283879",
#    "type": "text",
#    "text": {"body": device_name}
#}

#try:
#    response = requests.post(url, headers=headers, json=data)
#    result = response.json()
    
#    if response.status_code == 200:
#        print("✅ Mensaje enviado. ID:", result["messages"][0]["id"])
#    else:
#        print("❌ Error:", result.get("error", {}).get("message", "Desconocido"))
        
#except Exception as e:
#    print("⚠️ Error en la conexión:", str(e))

###################################
###################################