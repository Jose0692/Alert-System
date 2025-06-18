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

#Liberias necesarias
import smtplib
from pysnmp.hlapi import (
    SnmpEngine, CommunityData, UdpTransportTarget,
    ContextData, ObjectType, ObjectIdentity, getCmd
)
import importlib

location = "Lurin / Sala 1 / "
# Configuracion SNMP
#target_ip = "10.236.2.102" #Sala 6 Florida
#target_ip = "10.234.0.118" #Sala 7 San Miguel
target_ip = "10.234.66.22" #Sala 1 de Lurin
community = "public"  # Cambia esto si usas una comunidad diferente
# oid = '1.3.6.1.2.1.1.5.0' # OID para modelo
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

# Obtener info SNMP
device_alert = snmp_get(target_ip, community, oid)

#################################################
## ENVIO DE CORREO ELECTRONICO POR OUTLOOK 365 ##
#################################################

import smtplib
from email.message import EmailMessage

# Configuración Outlook
#email = "odooav@cineplanet.com.pe"
#password = "PlexPEOA25%"
email = "noc@cineplanet.com.pe"
password = "PlexPENA25%"
receiver_emails = ["jpardo@cineplanet.com.pe", "jmoreno@cineplanet.com.pe"] 
smtp_server = "smtp.office365.com"
port = 587

device_alert = device_alert
alert_detail = []
contador_alertas = 0

# 1. Verificar si hay error SNMP
if "SNMP error" in device_alert or "No Such Instance" in device_alert:
    alert_detail.append(f"Error en la consulta SNMP: {device_alert}")
else:
    # 2. Si es una cadena con múltiples líneas, splitear por saltos de línea
    alerts = device_alert.split('\n') if '\n' in device_alert else [device_alert]
    
    # 3. Procesar cada alerta
    for alert in alerts:
        parts = alert.split()
        if len(parts) >= 3:  # Asegurar que tiene formato "N 6200 texto - descripción"
            type_alert = parts[0]  
            if type_alert=="W":  # Verificar si es una alerta de tipo "N"
                type_alert = "Advertencia"
            code_alert = parts[1]  
            alert_text = ' '.join(parts[2:]) 
            alert_detail.append(alert_text)
        else:
            alert_detail.append(alert)  # Mantener el texto original si no cumple formato

#SE CREA EL CORREO
msg = EmailMessage()
msg['From'] = email
msg['To'] = ", ".join(receiver_emails)
msg['Subject'] = location + " " + " | ".join(alert_detail)
msg.set_content(f"Tipo: {type_alert}\nCódigo: {code_alert}\nDetalle: " + "".join(alert_detail))

#SE ENVIA CORREO
try:
    with smtplib.SMTP(smtp_server, port) as server:
        server.starttls()
        server.login(email, password)
        server.send_message(msg)
        print(f"✅ Email enviado a {receiver_emails}")
except Exception as e:
    print(f"❌ Error al enviar correo: {str(e)}")

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