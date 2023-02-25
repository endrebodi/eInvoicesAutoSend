import base64
import requests
import json
import sqlite3
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from io import BytesIO

url = 'https://efaktura.mfin.gov.rs/api/publicApi/sales-invoice/ids'
headers = {
    'accept': 'text/plain',
    'ApiKey': 'EFAKTUREAPIKEY'
}
response = requests.post(url, headers=headers)

time.sleep(1)  # Wait 1 second

if response.status_code == 200:
    response_json = json.loads(response.text)
    purchase_invoice_ids = response_json['SalesInvoiceIds']
    print(purchase_invoice_ids)
    conn = sqlite3.connect('sales_invoices.db')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS invoices (id INTEGER PRIMARY KEY)')
    cursor.execute('SELECT id FROM invoices')
    rows = cursor.fetchall()
    existing_ids = [row[0] for row in rows]
    for id in purchase_invoice_ids:
        if id not in existing_ids:
            cursor.execute('INSERT INTO invoices (id) VALUES (?)', (id,))
            conn.commit()
            # Send email with XML and PDF files
            invoice_url = f"https://efaktura.mfin.gov.rs/api/publicApi/sales-invoice/xml?invoiceId={id}"
            invoice_response = requests.get(invoice_url, headers=headers)
            if invoice_response.status_code == 200:
                # Extract XML and PDF data
                invoice_data = invoice_response.content
                xml_start_tag = b'<env:DocumentPdf mimeCode="application/pdf">'
                xml_end_tag = b'</env:DocumentPdf>'
                xml_start_index = invoice_data.find(xml_start_tag) + len(xml_start_tag)
                xml_end_index = invoice_data.find(xml_end_tag)
                xml_data = invoice_response.content
                pdf_data = base64.b64decode(invoice_data[xml_start_index:xml_end_index])
                
                # Attach XML and PDF files to email message
                message = MIMEMultipart()
                message['Subject'] = f'Izlazna_faktura_{id}'
                message['From'] = 'SENDERNAME'
                message['To'] = 'RECEIVEREMAILADDRESS'
                xml_attachment = MIMEApplication(xml_data, _subtype='xml')
                xml_attachment.add_header('Content-Disposition', 'attachment', filename=f'Izlazna_faktura_{id}.xml')
                message.attach(xml_attachment)
                pdf_attachment = MIMEApplication(pdf_data, _subtype='pdf')
                pdf_attachment.add_header('Content-Disposition', 'attachment', filename=f'Izlazna_faktura_{id}.pdf')
                message.attach(pdf_attachment)
                
                # Send email using SMTP server
                with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                    smtp.login('SENDEREMAILADDRESS', 'SENDEREMAILPASSWORD')
                    smtp.sendmail('SENDEREMAILADDRESS', 'RECEIVEREMAILADDRESS', message.as_string())
            else:
                print(f"Error {invoice_response.status_code}: {invoice_response.text}")
            time.sleep(5)  # Wait 5 seconds before sending the next command
    conn.close()
else:
    print(f"Error {response.status_code}: {response.text}")
