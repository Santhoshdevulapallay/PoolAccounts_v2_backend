from django.http import HttpResponse , JsonResponse,FileResponse
from dsm.common import format_indian_currency,trimFilePath,number_to_words_rupees
from registration.extarctdb_errors import extractdb_errormsg
from .models import *
import json ,pdb
from datetime import datetime
from docxtpl import DocxTemplate
from docx2pdf import convert
from poolaccounts.settings import base_dir
from .excess_models import *
import os,io,zipfile
from django.db.models import F ,Count ,Sum , Q

def getExcessSummary(request):
    try:

        excess_summary=list(ExcessBaseModel.objects.filter(Is_disbursed=False,Acc_Type='EXCESS').all().values())
        fees_charges_summary=list(ExcessBaseModel.objects.filter(Is_disbursed=False,Acc_Type='F&C').all().values())

        return JsonResponse([excess_summary,fees_charges_summary],safe=False)
    
    except Exception as e:
        return HttpResponse(extractdb_errormsg(e),status=400)
    
def generateExcessIOM(request):
    try:
        formdata=json.loads(request.body)
        if formdata['acc_type'] == 'EXCESS':
            doc = DocxTemplate("templates/EXCESS_IOM.docx")
        elif formdata['acc_type'] == 'F&C' :   
            doc = DocxTemplate("templates/F&C_IOM.docx")
        else:
            return HttpResponse('no file',status=404)
        
        # In-memory output file
        zip_buffer = io.BytesIO()
        # Create a zip file in memory
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for ent in formdata['final_summary']:
                subject='Refund of excess amount paid by M/s '+ent['Entity']+' Reg.' 
                # get bank account details
                bank_qry=list(BankDetails.objects.filter(Q(fin_code_fk__fin_code=ent['Fin_code']) ,(Q(fin_code_fk__end_date__isnull=True) | Q(fin_code_fk__end_date__gte=datetime.today()) ) ).values('bank_name','bank_account','ifsc_code') )

                if len(bank_qry) == 1:
                    bank_name=bank_qry[0]['bank_name']
                    account_no=bank_qry[0]['bank_account']
                    ifsc_code=bank_qry[0]['ifsc_code']
                else:
                    bank_name=''
                    account_no=''
                    ifsc_code=''
              
                context={
                        'entity_name':ent['Entity'],
                        'subject':subject,
                        'date':datetime.today().strftime('%d-%m-%Y'),
                        'value_date':ent['Paid_date'],
                        'description':ent['Description'],
                        'credit_amt':format_indian_currency(ent['Final_charges']),
                        'bank_type':ent['Bank_type'],
                        'account_no':account_no,
                        'bank_name':bank_name,
                        'ifsc_code':ifsc_code,
                        'fin_code':ent['Fin_code'],
                    }
               
                doc.render(context)
            
                # all MWH files goes to this folder
                parent_folder = os.path.abspath(os.path.join(base_dir, os.pardir))
                directory = os.path.join(parent_folder, 'IOMS')
                docx_directory=os.path.join(directory,'Docx')
                if not os.path.exists(docx_directory):
                    os.makedirs(docx_directory)

                inname_docx=ent['Entity']+'_IOM'+'.docx'
                output_file=os.path.join(docx_directory, inname_docx)
                doc.save(output_file)

                
                # Read the file content and add it to the zip file
                with open(output_file, 'rb') as file:
                    # Normalize the file path
                    normalized_path = os.path.normpath(output_file)
                    file_content = file.read()
                    zip_file.writestr(os.path.basename(normalized_path), file_content)

                # once document generated update Is_disbursed status=True
                ExcessBaseModel.objects.filter(id=ent['id']).update(Is_disbursed=True,Fully_disbursed='C',disbursed_date=datetime.today())

        # Seek to the beginning of the in-memory file
        zip_buffer.seek(0)
        # Create HTTP response
        response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename="files.zip"'

        return response
        
    except Exception as e:
        for ent in formdata['final_summary']:
            # once document generated update Is_disbursed status=True
            ExcessBaseModel.objects.filter(id=ent['id']).update(Is_disbursed=False,Fully_disbursed='')
        return HttpResponse(e)