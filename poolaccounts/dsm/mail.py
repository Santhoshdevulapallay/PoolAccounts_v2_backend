from django.http import HttpResponse , JsonResponse,FileResponse
from dsm.common import get_month_start_end_dates
from dsm.common import getFincode
from dsm.common import format_indian_currency
from registration.extarctdb_errors import extractdb_errormsg
import json

import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from os.path import basename

import os
from registration.models import Registration,YearCalendar
import pandas as pd


def mail_sender(to_list,html_body,subject):
    try:
        username=os.environ.get('MAIL_USERNAME')
        password=os.environ.get('MAIL_PASSWORD')
        sender_mail=os.environ.get('SENDER_MAIL')

        port = 587
        smtp_server="mail.grid-india.in"
        server = smtplib.SMTP(smtp_server,port)
        server.starttls()
        server.login(username,password)
        cc="Nair.rethi@grid-india.in,phaneendra@grid-india.in,korangi@grid-india.in,dsmsrldc@grid-india.in"
        
        message = MIMEMultipart('alternative')
        message["Subject"] =subject
        message["To"] = ",".join(to_list) 
        message["Cc"] = cc
        toaddrs = to_list + cc.split(',')
        message.attach(MIMEText(html_body,'html'))
        server.sendmail(sender_mail,toaddrs, message.as_string())
      
        return True
    except Exception as e:
        extractdb_errormsg(str(e))
        return False

def mail_sender_customizedcc(to_list,html_body,subject,cc):
    try:
        username=os.environ.get('MAIL_USERNAME')
        password=os.environ.get('MAIL_PASSWORD')
        sender_mail=os.environ.get('SENDER_MAIL')

        port = 587
        smtp_server="mail.grid-india.in"
        server = smtplib.SMTP(smtp_server,port)
        server.starttls()
        server.login(username,password)
        message = MIMEMultipart('alternative')
        message["Subject"] =subject
        message["To"] = ",".join(to_list) 
        message["Cc"] = cc
        toaddrs = to_list + cc.split(',')
        message.attach(MIMEText(html_body,'html'))
        server.sendmail(sender_mail,toaddrs, message.as_string())
      
        return True
    except Exception as e:
        extractdb_errormsg(str(e))
        return False
    
def sendMailNotMappedTxns(request):
    try:
        formdata=json.loads(request.body)
        selected_txns_df=pd.DataFrame(formdata['selected_rows'])
        selected_txns_df.drop(columns=['id','PostDate','Debit','Balance','IsMapped','SplitStatus','IsSweep'],inplace=True)
        # change date format
        selected_txns_df['ValueDate'] = pd.to_datetime(selected_txns_df['ValueDate']).dt.strftime('%d-%m-%Y')
        
        selected_txns_df['Credit']=selected_txns_df['Credit'].apply(lambda x :format_indian_currency(x) )
       
        selected_txns=selected_txns_df.to_dict(orient='records')

        selected_entities=formdata['selected_entities']
        mail_list=list(Registration.objects.filter(fin_code__in=selected_entities).values_list('l1_mail','l2_mail'))

        senders_mail_list = list(set(email for email_tuple in mail_list for email in email_tuple if email))
        # Remove non-breaking spaces
        cleaned_emails = [email.replace('\xa0', '') for email in senders_mail_list]

        # senders_mail_list=['uday.santhosh@grid-india.in']

        # Creating HTML table
        html_table = "<table border='1'>\n"

        # Adding table header
        html_table += "  <tr>\n"
        for key in selected_txns[0].keys():
            html_table += f"    <th>{key}</th>\n"

        html_table += "  </tr>\n"

        # Adding table rows
        for row in selected_txns:
            html_table += "  <tr>\n"
            for value in row.values():
                html_table += f"    <td>{value}</td>\n"
            html_table += "  </tr>\n"
        html_table += "</table>"

        # Html Header Part and then append
        html = """\
            <html>
                <head>
                <style>
                    table, th, td {
                        border: 2.5px solid black;
                        border-collapse: collapse;
                    }
                    th, td {
                        padding: 5px;
                        text-align: center;    
                    }    
                </style>
                </head>
            <body>
            <p>Dear Sir/Madam,
            <br><br><strong> Unidentified Payment Receipts / अज्ञात भुगतान रसीदें : </strong><br>
            The following payments received from your entity but unable to book towards any week / आपकी इकाई से निम्नलिखित भुगतान प्राप्त हुए लेकिन किसी भी सप्ताह के लिए बुक नहीं किया जा सका  :<br>
            %s<br>Kindly reply at the earliest / कृपया यथाशीघ्र उत्तर दें  
            </p>
            <br><strong>Thanks and Regards</strong></br><strong>DSM-MO Section</strong></br><br></br>
            </body>
            </html>
            """ % (html_table)
        
        
        if mail_sender(cleaned_emails,html,"Unidenitified Transaction -reg."):
            return JsonResponse({'message':'Mail Sent Successfully','status':True},safe=False)
        else:
            return JsonResponse({'message':'Failed to Sent Mail','status':False},safe=False)
    except Exception as e:
            return HttpResponse(extractdb_errormsg(e),status_code=500)

def sendMailOutstandingTxns(request):
    try:
        formdata=json.loads(request.body)
        selected_txns_df=pd.DataFrame(formdata['selected_rows'])
        cc_list=formdata['cc_list']
        cc_list_string = ", ".join(cc_list)
        
      
        acc_type=formdata['acc_type']
        calendar_df=pd.DataFrame(YearCalendar.objects.all().values('fin_year','week_no','start_date','end_date'))
        # rename the columns
        calendar_df.rename(columns={'fin_year':'Fin_year','week_no':'Week_no'},inplace=True)
        merged_df=pd.merge(selected_txns_df,calendar_df,on=['Fin_year','Week_no'],how='left')
        
        # Convert start_date and end_date to datetime format
        merged_df['start_date'] = pd.to_datetime(merged_df['start_date'])
        merged_df['end_date'] = pd.to_datetime(merged_df['end_date'])
        try:
            # Update the Week_no column with the desired format
            merged_df['Week_no'] = merged_df.apply(
                lambda row: f"{row['Week_no']} ({row['start_date'].strftime('%d-%m-%Y')} to {row['end_date'].strftime('%d-%m-%Y')})",
                axis=1
            )   
        except:
            # skip if error comes not a big issue
            pass
        
        # drop start_date and end_date columns
        merged_df.drop(columns=['start_date','end_date'],inplace=True)
        # Calculate the total outstanding for each Fin_code
        merged_df['Total_outstanding'] = merged_df.groupby('Fin_code')['Outstanding'].transform('sum')
        merged_df['Outstanding']=merged_df['Outstanding'].apply(lambda x :format_indian_currency(x) )
        merged_df['Final_charges'] = merged_df['Final_charges'].apply(lambda x :format_indian_currency(x) )
        merged_df['Paid_amount'] = merged_df['Paid_amount'].apply(lambda x :format_indian_currency(x) )
        merged_df['Total_outstanding']=merged_df['Total_outstanding'].apply(lambda x :format_indian_currency(x) )
       
        # Group by 'Fin_code' and iterate through each group
        grouped = merged_df.groupby('Fin_code')

        # Iterate through each group
        for fin_code, group in grouped:
            entity_outstanding=[]
            total_outstanding=0
            for _, row in group.iterrows():
                entity_dict=row.to_dict()
                total_outstanding=row['Total_outstanding']

                del entity_dict['Fin_code']
                del entity_dict['Total_outstanding']
                entity_outstanding.append(entity_dict)

            column_order = ['Fin_year', 'Week_no', 'Entity', 'Final_charges', 'Paid_date','Paid_amount', 'Outstanding']
            rearranged_data = [{key: (d[key] if d[key] is not None else '-') if key == 'Paid_date' else d[key] for key in column_order} for d in entity_outstanding]
            grand_total_row = {'Fin_year': ' ','Week_no': ' ','Entity': 'Grand Total','Final_charges': ' ','Paid_date': ' ','Paid_amount': ' ', 'Outstanding': total_outstanding}
            rearranged_data.append(grand_total_row)

            mail_list=list(Registration.objects.filter(fin_code=fin_code).values_list('l1_mail','l2_mail'))

            senders_mail_list = list(set(email for email_tuple in mail_list for email in email_tuple if email))
            # Remove non-breaking spaces
            cleaned_emails = [email.replace('\xa0', '') for email in senders_mail_list]
            # Creating HTML table
            html_table = "<table border='1'>\n"
            # Adding table header
            html_table += "  <tr>\n"
            for key in ['Fin Year', 'Week No', 'Entity', 'Final Charges', 'Paid Date','Paid Amount', 'Outstanding']:
                html_table += f"<th>{key}</th>\n"

            html_table += "  </tr>\n"
            # Adding table rows
            for row in rearranged_data:
                html_table += "  <tr>\n"
                for value in row.values():
                    html_table += f"    <td>{value}</td>\n"
                html_table += "  </tr>\n"
            html_table += "</table>"
            
            # Html Header Part and then append
            html = """\
                <html>
                    <head>
                    <style>
                        table, th, td {
                                    border: 1.5px solid black;
                                    border-collapse: collapse;
                                        }
                        th, td {
                            padding: 7.5px;
                            text-align: center;
                            font-family: 'Garamond', serif;
                            font-size: 15px; /* Adjust font size as needed */
                                }
                        th {
                            background-color: #f2f2f2; /* Light gray background for table header */
                            font-weight: bold;
                            }
                        body {
                            font-family: 'Garamond', serif;
                            font-size: 12px; /* Adjust overall font size as needed */
                            }
                        p, h4 {
                            margin: 10px 0;
                            font-weight: normal
                                }
                        .signature-line {
                            font-style: italic;
                            text-decoration: underline;
                                }
                    </style>
                    </head>
                <body>
                <p> Dear Sir/Madam , </p>
                <h4> This is to bring to your kind notice that your good office has outstanding dues of  %s towards %s Principal amount. Non payment of %s Charges is a matter of serious concern which is affecting the whole process of Regulatory Pool settlement Mechanism./
                <br>यह आपकी सूचना लाने के लिए है कि आपके कार्यालय में %s मूलधन राशि के लिए %s का बकाया है। डीएसएम शुल्क का भुगतान न करना गंभीर चिंता का विषय है जो नियामक पूल निपटान तंत्र की पूरी प्रक्रिया को प्रभावित कर रहा है </h4> <br> %s
                <br><strong ><span class="signature-line">It is requested to pay the outstanding amount %s immediately.</span> </br><strong> 
                <br></br><br><strong>Thanks and Regards</strong></br><strong>Praharsha Korangi</strong></br><strong>%s-MO Section</strong></br><br></br>
                </body>
                </html>
                """ % (str(total_outstanding),acc_type,acc_type,acc_type,str(total_outstanding),html_table,str(total_outstanding),acc_type)
           
            # cleaned_emails=['uday.santhosh@grid-india.in']
            # cc_list_string='uday.santhosh@grid-india.in'
            
            mail_sender_customizedcc(cleaned_emails,html,"Non payment of "+acc_type+" Outstanding dues -reg.",cc_list_string)
            
        return JsonResponse({'message':'Mail Sent Successfully','status':True},safe=False)
            
    except Exception as e:
            return HttpResponse(extractdb_errormsg(e),status_code=500)
