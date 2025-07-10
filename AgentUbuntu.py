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
from pysnmp.hlapi import (
    SnmpEngine, CommunityData, UdpTransportTarget,
    ContextData, ObjectType, ObjectIdentity, getCmd
)
import importlib
from email.message import EmailMessage

# CONFIGURACION SNMP #
target_ips = [
    "10.234.0.22", "10.234.0.38", "10.234.0.54", "10.234.0.70", "10.234.0.86",
    "10.234.0.102", "10.234.0.118", "10.234.0.134", "10.234.0.150", "10.234.0.166",
    "10.234.0.182", "10.234.0.198", "10.234.0.214", "10.234.0.230",
    "10.234.66.22",  "10.234.66.38",  "10.234.66.54", 
    #"10.236.2.22",  "10.236.2.38",  "10.236.2.54",  "10.236.2.70",  "10.236.2.86", 
    #"10.236.2.102",  "10.236.2.118",  "10.236.2.134",  "10.236.2.150",  "10.236.2.166", 
    #"10.236.2.182"  
]
community = "public"  # Cambia esto si usas una comunidad diferente
oid_model = '1.3.6.1.2.1.1.5.0' 
oid = '1.3.6.1.4.1.12612.220.11.2.2.10.5.1.2.1' # OID para alerta activa
#oid = '1.3.6.1.4.1.12612.220.11.2.2.4.8.1.2.1'  # OID para hora de lampara consumida

# Consulta SNMP
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
        
# Configuración Outlook (sin cambios)
email = "noc@cineplanet.com.pe"
password = "2025AV123/321"
receiver_emails = ["jpardo@cineplanet.com.pe", "jmoreno@cineplanet.com.pe"] 
smtp_server = "smtp.office365.com"
port = 587

def process_ip(target_ip):
    # IDENTIFICACION DE COMPLEJO POR IP (sin cambios)
    octetos = target_ip.split('.')
    tercer_octeto = octetos[2]
    if tercer_octeto == '66':
        location_name = "Lurin"
    elif tercer_octeto == '0':
        location_name = "San Miguel"
    else:
        location_name = "Desconocido"

    # IDENTIFICACION DE SALA POR IP (sin cambios)
    cuarto_octeto = octetos[3]
    if cuarto_octeto == '22':        screen_number = "1"
    elif cuarto_octeto == '38':        screen_number = "2"
    elif cuarto_octeto == '54':        screen_number = "3"
    elif cuarto_octeto == '70':        screen_number = "4"
    elif cuarto_octeto == '86':        screen_number = "5"
    elif cuarto_octeto == '102':        screen_number = "6"
    elif cuarto_octeto == '118':        screen_number = "7"
    elif cuarto_octeto == '134':        screen_number = "8"
    elif cuarto_octeto == '150':        screen_number = "9"
    elif cuarto_octeto == '166':        screen_number = "10"
    elif cuarto_octeto == '182':        screen_number = "11"
    elif cuarto_octeto == '198':        screen_number = "12"
    elif cuarto_octeto == '214':        screen_number = "13"
    elif cuarto_octeto == '230':        screen_number = "14"
    else:
        screen_number = "Desconocida"

    # OBTENER INFO SNMP
    device_alert = snmp_get(target_ip, community, oid)
    device_model = snmp_get(target_ip, community, oid_model)

    alert_detail = []
    type_alert = ""
    code_alert = ""

    # Procesar alertas (sin cambios)
    if "SNMP error" in device_alert or "No Such Instance" in device_alert:
        alert_detail.append(f"Error en la consulta SNMP: {device_alert}")
    else:
        alerts = device_alert.split('\n') if '\n' in device_alert else [device_alert]
        
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
                print(f"✅ Email enviado para {target_ip}")
        except Exception as e:
            print(f"❌ Error al enviar correo para {target_ip}: {str(e)}")
    else:
        print(f"ℹ️ No se envió correo para {target_ip} - No hay alertas válidas")

# Procesar todas las IPs
for ip in target_ips:
    process_ip(ip)

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