from mailjet_rest import Client
import base64
from email_sender_keys import *


def send_email(email_to, email_reply_to, attached_file):
    """
    Envío de email con archivo adjunto a través de Mailjet \n
    Recuerda configurar archivo email_sender_keys.py
    Arguments:
        email_to: email de destinatario
        email_reply_to: email de respuesta
        attached_file: ruta relativa del archivo incluida la extensión. Solo acepta archivos con extensión .jpg
    """
    with open(attached_file, 'rb') as file:
        file_base64 = base64.b64encode(file.read()).decode('utf-8')

    mailjet = Client(auth=(MAILJET_API_KEY, MAILJET_SECRET_KEY), version='v3.1')
    data = {
        'Messages': [
            {
                "From": {
                    "Email": MAILJET_SENDER_EMAIL,
                    "Name": "Julio pruebas"
                },
                "To": [
                    {
                        "Email": email_to,
                        "Name": "You"
                    }
                ],
                "Headers": {
                    "Reply-To": email_reply_to,
                },
                "Subject": "Pruebas adjuntos",
                "TextPart": "Greetings from Mailjet!",
                "HTMLPart": "<h3>Dear passenger 1, welcome to <a href=\"https://www.mailjet.com/\">Mailjet</a>!</h3><br />May the delivery force be with you!",
                "Attachments": [
                    {
                        "ContentType": "image/jpg",
                        "Filename": "infografia.jpg",
                        "Base64Content": file_base64
                    }
                ]
            }
        ]
    }
    result = mailjet.send.create(data=data)
    print(result.status_code)
    print(result.json())
