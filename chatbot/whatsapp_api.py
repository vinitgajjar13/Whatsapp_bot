import os
import requests
import json
from django.conf import settings

WHATSAPP_TOKEN = os.getenv('ACCESS_TOKEN', 'YOUR_WHATSAPP_TOKEN_HERE')
PHONE_NUMBER_ID = os.getenv('PHONE_NUMBER_ID', 'YOUR_PHONE_NUMBER_ID_HERE')

def send_whatsapp_message(phone_number, payload):
    url = f"https://graph.facebook.com/v17.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(url, headers=headers, json=payload)
    resp_json = response.json()
    print("Meta API Response:", resp_json)
    return resp_json

def send_template(phone_number, template_name):
    """
    Sends a generic template by name.
    """
    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {
                "code": "gu"
            }
        }
    }
    return send_whatsapp_message(phone_number, payload)

def send_welcome_template(phone_number):
    return send_template(phone_number, "welcome_services")

def send_services_list(phone_number, page=1):
    """
    Sends an Interactive List Message with pagination.
    Shows up to 9 services per page, and a 10th item for 'More'.
    """
    from .services_data import SERVICES
    services_items = list(SERVICES.items())
    
    items_per_page = 9
    start_idx = (page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    
    current_services = services_items[start_idx:end_idx]
    
    rows = []
    for service_id, service_info in current_services:
        rows.append({
            "id": service_id,
            "title": service_info['title'][:24] # WhatsApp list title limit is 24 characters
        })
        
    if end_idx < len(services_items):
        rows.append({
            "id": f"more_{page+1}",
            "title": "વધુ સેવાઓ જુઓ (More)"
        })

    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {
                "type": "text",
                "text": "સરકારી સેવાઓ"
            },
            "body": {
                "text": "કૃપા કરીને નીચેના લિસ્ટમાંથી એક સેવા પસંદ કરો:"
            },
            "footer": {
                "text": f"પેજ {page}"
            },
            "action": {
                "button": "સેવાઓ જુઓ",
                "sections": [
                    {
                        "title": "ઉપલબ્ધ સેવાઓ",
                        "rows": rows
                    }
                ]
            }
        }
    }
    return send_whatsapp_message(phone_number, payload)

def send_service_details_template(phone_number, service_details):
    """
    Template 2: Variable template with service details.
    We assume template name is 'service_details' with 2 body variables (Name, Description).
    """
    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "template",
        "template": {
            "name": "service_details",
            "language": {
                "code": "gu"
            },
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": service_details['title']},
                        {"type": "text", "text": ", ".join(service_details['documents'])}
                    ]
                }
            ]
        }
    }
    return send_whatsapp_message(phone_number, payload)

def send_limit_reached_template(phone_number):
    """
    Template 3: Timeout/Limit reached template.
    We assume template name is 'limit_reached'
    """
    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "template",
        "template": {
            "name": "limit_reached",
            "language": {
                "code": "gu"
            }
        }
    }
    return send_whatsapp_message(phone_number, payload)

def send_welcome_interactive(phone_number, services_dict):
    """Fallback interactive message if templates aren't approved yet."""
    buttons = []
    # Max 3 buttons in WhatsApp API
    for code, details in list(services_dict.items())[:3]: 
        buttons.append({
            "type": "reply",
            "reply": {
                "id": code,
                "title": details['title'][:20]
            }
        })
        
    if not buttons:
        return send_text_message(phone_number, "Welcome! No services available right now.")
        
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": phone_number,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {
                "text": "Welcome! Please select a service:"
            },
            "action": {
                "buttons": buttons
            }
        }
    }
    return send_whatsapp_message(phone_number, payload)

def send_text_message(phone_number, text):
    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "text",
        "text": {"body": text}
    }
    return send_whatsapp_message(phone_number, payload)
