import json
import os
from datetime import timedelta
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .models import Customer, Message
from . import whatsapp_api
from .services_data import SERVICES

VERIFY_TOKEN = os.getenv('VERIFY_TOKEN', 'YOUR_VERIFY_TOKEN')


@csrf_exempt
def whatsapp_webhook(request):
    if request.method == 'GET':
        mode = request.GET.get('hub.mode')
        token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')

        if mode and token:
            if mode == 'subscribe' and token == VERIFY_TOKEN:
                return HttpResponse(challenge, status=200)
            return HttpResponse('Forbidden', status=403)
        return HttpResponse('Bad Request', status=400)

    elif request.method == 'POST':
        try:
            body = json.loads(request.body)
            # Check if it's a WhatsApp status update or message
            if 'object' in body and body['object'] == 'whatsapp_business_account':
                for entry in body.get('entry', []):
                    for change in entry.get('changes', []):
                        value = change.get('value', {})
                        if 'messages' in value:
                            for msg in value['messages']:
                                process_incoming_message(msg, value.get('contacts', []))
            return HttpResponse('EVENT_RECEIVED', status=200)
        except Exception as e:
            print(f"Error processing webhook: {e}")
            return HttpResponse('Server Error', status=500)

def process_incoming_message(msg_data, contacts):
    phone_number = msg_data.get('from')
    msg_type = msg_data.get('type')
    
    # Get or create customer
    customer_name = ""
    if contacts:
        customer_name = contacts[0].get('profile', {}).get('name', '')
    customer, _ = Customer.objects.get_or_create(phone_number=phone_number, defaults={'name': customer_name})

    # Save inbound message
    Message.objects.create(
        customer=customer,
        direction='inbound',
        content=json.dumps(msg_data),
        message_type=msg_type
    )

    if msg_type == 'text':
        text_body = msg_data.get('text', {}).get('body', '').lower()
        if text_body in ['hi', 'hello']:
            # Reset current page
            customer.current_page = 1
            customer.save()
            
            # Send welcome template message
            whatsapp_api.send_welcome_template(phone_number)
            
        elif text_body == 'test':
            # Send a utility template to check if it arrives
            whatsapp_api.send_limit_reached_template(phone_number)
            
        elif text_body == 'test2':
            # Send a simple text message
            whatsapp_api.send_text_message(phone_number, "આ એક સાદો ટેસ્ટ મેસેજ છે. જો આ મેસેજ આવે તો સમજવું કે ફ્રી-ફોર્મ મેસેજ જાય છે પણ ટેમ્પલેટ નથી જતા.")

    elif msg_type == 'interactive':
        interactive_data = msg_data.get('interactive', {})
        if interactive_data.get('type') == 'list_reply':
            list_id = interactive_data.get('list_reply', {}).get('id', '')
            
            if list_id.startswith('more_'):
                try:
                    page = int(list_id.split('_')[1])
                    whatsapp_api.send_services_list(phone_number, page=page)
                except ValueError:
                    pass
            elif list_id in SERVICES:
                handle_service_request(customer, phone_number, list_id)
        elif interactive_data.get('type') == 'button_reply':
            button_title = interactive_data.get('button_reply', {}).get('title', '').strip()
            
            if button_title == "વધુ સેવાઓ જુઓ (More)":
                if customer.current_page == 1:
                    customer.current_page = 2
                    customer.save()
                    whatsapp_api.send_template(phone_number, "services_2")
                elif customer.current_page == 2:
                    customer.current_page = 3
                    customer.save()
                    whatsapp_api.send_template(phone_number, "services_3")
                else:
                    customer.current_page = 1
                    customer.save()
                    whatsapp_api.send_template(phone_number, "welcome_services")
            else:
                # Find service by title
                matched_service_code = None
                for code, info in SERVICES.items():
                    if info['title'].strip() == button_title:
                        matched_service_code = code
                        break
                
                if matched_service_code:
                    handle_service_request(customer, phone_number, matched_service_code)
                else:
                    whatsapp_api.send_text_message(phone_number, "Service not found. Please try again.")

    elif msg_type == 'button':
        button_title = msg_data.get('button', {}).get('text', '').strip()
        
        if button_title == "વધુ સેવાઓ જુઓ (More)":
            if customer.current_page == 1:
                customer.current_page = 2
                customer.save()
                whatsapp_api.send_template(phone_number, "services_2")
            elif customer.current_page == 2:
                customer.current_page = 3
                customer.save()
                whatsapp_api.send_template(phone_number, "services_3")
            else:
                customer.current_page = 1
                customer.save()
                whatsapp_api.send_template(phone_number, "welcome_services")
        else:
            # Find service by title
            matched_service_code = None
            for code, info in SERVICES.items():
                if info['title'].strip() == button_title:
                    matched_service_code = code
                    break
            
            if matched_service_code:
                handle_service_request(customer, phone_number, matched_service_code)
            else:
                whatsapp_api.send_text_message(phone_number, "Service not found. Please try again.")

def handle_service_request(customer, phone_number, service_code):
    service_details = SERVICES.get(service_code)
    if not service_details:
        whatsapp_api.send_text_message(phone_number, "Service not found.")
        return

    # Check 24-hour limit
    time_threshold = timezone.now() - timedelta(hours=24)
    if customer.last_service_viewed_at and customer.last_service_viewed_at >= time_threshold:
        # User has already requested a service in the last 24 hours
        whatsapp_api.send_limit_reached_template(phone_number)
        Message.objects.create(
            customer=customer,
            direction='outbound',
            content="Sent Limit Reached Template",
            message_type='template'
        )
    else:
        # Allow viewing service
        whatsapp_api.send_service_details_template(phone_number, service_details)
        
        # Update customer last viewed timestamp
        customer.last_service_viewed_at = timezone.now()
        customer.save()
        
        Message.objects.create(
            customer=customer,
            direction='outbound',
            content=f"Sent Service Details Template for {service_details['title']}",
            message_type='template'
        )

def get_all_data(request):
    customers = Customer.objects.prefetch_related('messages').all()
    data = []
    for customer in customers:
        customer_data = {
            'phone_number': customer.phone_number,
            'name': customer.name,
            'last_service_viewed_at': customer.last_service_viewed_at.isoformat() if customer.last_service_viewed_at else None,
            'current_page': customer.current_page,
            'created_at': customer.created_at.isoformat(),
            'messages': []
        }
        for message in customer.messages.all().order_by('timestamp'):
            customer_data['messages'].append({
                'direction': message.direction,
                'content': message.content,
                'message_type': message.message_type,
                'timestamp': message.timestamp.isoformat()
            })
        data.append(customer_data)
        
    return JsonResponse({'status': 'success', 'data': data})
