
from django.http import HttpResponse , JsonResponse,FileResponse
from dsm.common import format_indian_currency,trimFilePath,number_to_words_rupees
from dsm.common import getMergedAccts
from dsm.disburse import getPaymentsConsideredForDisbursement
from registration.add530hrs import create_zip_file
from registration.extarctdb_errors import extractdb_errormsg
from .models import *
import json ,pdb
from datetime import datetime
from docxtpl import DocxTemplate
from docx2pdf import convert
from poolaccounts.settings import base_dir
from datetime import datetime
from docx2pdf import convert
import pythoncom ,os,ast,io,zipfile
from django.db.models import F ,Count ,Sum , Q

def intimateNLDC(request):
    try:
        req_data=json.loads(request.body)
        summary_amount=req_data['amount_in_pool']
        legacy_bills=req_data['is_legacy']
        
        IntimateNLDC (
            intimate_date=datetime.today(),
            amount_available=summary_amount,
            transfer_amount=summary_amount,
            is_transferred=False
        ).save()
        # get all pool account types
        all_pool_accs=list(PoolAccountTypes.objects.filter(Q(end_date__isnull=True)|Q(end_date__gte=datetime.now())).values_list('acc_types',flat=True))
        merged_accs=getMergedAccts()
        result_accs=[acc for acc in all_pool_accs if acc not in merged_accs ]
        pool_types = sorted(result_accs)

        for p_type in pool_types:
            getPaymentsConsideredForDisbursement(p_type,legacy_bills) #Payables status changer

        return JsonResponse('success',safe=False)
    
    except Exception as e:
        return HttpResponse(extractdb_errormsg(e),status=400)
    

def getIntimateSummary(request):
    try:
        summary_list=list(IntimateNLDC.objects.filter(is_transferred=False).all().values())
        # already transferred amounts
        transferred_list=list(IntimateNLDC.objects.filter(is_transferred=True).order_by('-intimate_date').all().values())

        return JsonResponse([summary_list,transferred_list],safe=False)
    
    except Exception as e:
        return HttpResponse(extractdb_errormsg(e),status=400)


def storeUploadedFile(directory,request):
    try:
        # store the file uploaded by user in a folder
        docx_directory=os.path.join(directory,'TransferIOMS')
        if not os.path.exists(docx_directory):
            os.makedirs(docx_directory)

        inname_file_path=request.FILES['files'].name
        output_uploaded_file=os.path.join(docx_directory, inname_file_path)
        with open(output_uploaded_file, 'wb+') as destination:
            for chunk in request.FILES['files'].chunks():
                destination.write(chunk)

        return trimFilePath(output_uploaded_file)
    except Exception as e:
        return ''

def storeDocSplitPath(doc,directory):
    try:
        docx_directory=os.path.join(directory,'Docx')
        if not os.path.exists(docx_directory):
                os.makedirs(docx_directory)

        inname_docx='Transfer_surplus_'+datetime.now().strftime('%d-%m-%Y')+'.docx'
        output_file=os.path.join(docx_directory, inname_docx)
        doc.save(output_file)
        # pythoncom.CoInitialize()

        # # Convert the Word file to PDF
        # pdf_file_path = output_file.replace('.docx', '.pdf')
        # convert(output_file, pdf_file_path)
        
        return trimFilePath(output_file)

    except Exception as e:
        return ''
    
def transferSurplus(request):
    try:
        tobe_transferred = request.POST.get('tobe_transferred')
        er = float(request.POST.get('er'))
        nr = float(request.POST.get('nr'))
        wr = float(request.POST.get('wr'))
        ner = float(request.POST.get('ner'))
        psdf = float(request.POST.get('psdf'))
        notesheet_refno = request.POST.get('notesheet_refno')
        regions=[]
        all_file_paths=[]

        fin_code_dict={'er':'A0077','wr':'A0076','nr':None,'ner':None,'psdf':None}
        total_amount=0
        if er>0:
            regions.append({'entity':'ERPC','amount':format_indian_currency(er),'fin_code':fin_code_dict['er']})
            total_amount+=er
        if nr>0:
            regions.append({'entity':'NRPC','amount':format_indian_currency(nr),'fin_code':fin_code_dict['nr']})
            total_amount+=nr
        if wr>0:
            regions.append({'entity':'WRPC','amount':format_indian_currency(wr),'fin_code':fin_code_dict['wr']})
            total_amount+=wr
        if ner>0:
            regions.append({'entity':'NER','amount':format_indian_currency(ner),'fin_code':fin_code_dict['ner']})
            total_amount+=ner
        if psdf>0:
            regions.append({'entity':'PSDF','amount':format_indian_currency(psdf),'fin_code':fin_code_dict['psdf']})
            total_amount+=psdf

        doc = DocxTemplate("templates/IntimateNLDC.docx")
        context={
                'regions':regions,
                'today_date':datetime.now().strftime('%d-%m-%Y'),
                'notesheet_ref_no':notesheet_refno,
                'total_amount':format_indian_currency(total_amount),
                'total_in_words':number_to_words_rupees(total_amount)
            }
        doc.render(context)   
        parent_folder = os.path.abspath(os.path.join(base_dir, os.pardir))
        directory = os.path.join(parent_folder, 'IOMS')
       
        all_file_paths.append(storeDocSplitPath(doc,directory))
        all_file_paths.append(storeUploadedFile(directory,request))

        # Accessing and processing the 'row' data, which is a JSON string
        intimated_rows = json.loads(request.POST.get('row'))

        dis_status = list( DisbursementStatus.objects.filter(final_disburse=True).order_by('-Disbursed_date')[:1].values())

        surplus_amount = int(intimated_rows[0]['amount_available']) - int(tobe_transferred)
        for row in intimated_rows:
            IntimateNLDC.objects.filter(id=row['id']).update(
                is_transferred=True,
                transfer_amount=tobe_transferred,
                er=er,
                nr=nr,
                wr=wr,
                ner=ner,
                psdf=psdf,
                file_path=all_file_paths,
                is_used_indisbursement = True,
            )


        remarks_1 = dis_status[0]['remarks']
        if remarks_1 is None:
            remarks_1 = ' '
        else :
            remarks_1
        
        DisbursementStatus.objects.filter(id= dis_status[0]['id']).update(
            Surplus_amt = surplus_amount, 
            remarks = remarks_1 +" _Amount of Rs."+ tobe_transferred+" for inter-regional on "+ datetime.today().strftime("%d-%m-%Y")
            )

        return getIntimateSummary(request)
    
    except Exception as e:
        return HttpResponse(extractdb_errormsg(e),status=400)


def downloadTransferIOM(request):
    try:
        selected_row=json.loads(request.body)['row']
        file_paths=ast.literal_eval(selected_row['file_path'])
        #remove empty strings from list 
        file_paths = [file for file in file_paths if file]
        
        directory=os.path.dirname(base_dir)
        zip_fille=create_zip_file(file_paths,directory,'transfer_iom.zip')
        response = HttpResponse(open(zip_fille, 'rb').read(), content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename='+zip_fille

        return response
    
    except Exception as e:
        return HttpResponse(e)
    

def nldcSplitAmount(request):
    try:
        request_data=json.loads(request.body)
        # check if already present then delete
        NLDCPoolAmountSplit.objects.filter(disburse_date=datetime.today()).delete()
        NLDCPoolAmountSplit(
            disburse_date=datetime.today(),
            amount_for_dsm=request_data['dsm_amount'],
            amount_for_netas=request_data['netas_amount'],
            amount_for_reac=request_data['reac_amount'],
            is_user_checked=request_data['is_toggled']
        ).save()
        return JsonResponse({'status':True,'message':'Amounts Saved Successfully'},safe=False)
    
    except Exception as e:
        
        return  JsonResponse({'status':False,'message':str(e)},safe=False)
    
