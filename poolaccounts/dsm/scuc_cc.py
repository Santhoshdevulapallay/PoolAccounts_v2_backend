import json , os , pandas as pd
from django.http import HttpResponse , JsonResponse
from dsm.common import add530hrstoDateString
from dsm.reports import getCalSum
from registration.extarctdb_errors import extractdb_errormsg
from registration.models import Registration
from django.db.models import Q
from datetime import datetime , timedelta
import pandas as pd
from .scuc_cc_models import *
from .models import DisbursementStatus
import ast
from dsm.common import format_indian_currency , getFeesChargesName
from registration.models import BankDetails
from docxtpl import DocxTemplate
from poolaccounts.settings import base_dir

def scucCCEntities(request):
    try:
        entities_df = pd.DataFrame( Registration.objects.filter(Q(entity_type = 'Thermal-CGS') ,( Q(end_date__isnull = True) | Q(end_date__gte = datetime.now())) ).order_by('fees_charges_name').values('fees_charges_name' ,'fin_code') , columns=['fees_charges_name','fin_code'])

        entities_df['final_charges'] = 0    
        entities_df['payableorreceivable'] = ''    
       
        return JsonResponse(entities_df.to_dict(orient='records') , safe=False)
    
    except Exception as e:
        return HttpResponse(extractdb_errormsg(e),status=400)


def storescucCCBills(request):
    try:
        uptomonth=request.POST.get('uptomonth', '').strip()
        
        letter_date = add530hrstoDateString(json.loads(request.POST['letter_date'])).date() 
        entities_df = pd.DataFrame(ast.literal_eval(request.POST['entities_list']))
        fin_year = json.loads(request.POST['fin_year'])
        
        if not entities_df.empty:
            # Filter rows where 'PayableorReceivable' is not empty and 'Revised_charges' > 0
            resulted_df = entities_df[(entities_df["payableorreceivable"] != "") & (entities_df["final_charges"] > 0)]
        else:
            resulted_df = pd.DataFrame([])

        for _ , row in resulted_df.iterrows():
            SCUCCCBaseModel(
                Letter_date= letter_date ,
                Fin_year = fin_year,
                up_to_the_month = datetime.strptime(uptomonth, "%Y-%m").strftime("%b-%y"),
                Entity= row['fees_charges_name'] ,
                Final_charges= row['final_charges'] ,
                Fin_code= row['fin_code'] ,  
                PayableorReceivable= row['payableorreceivable']
            ).save()

        return JsonResponse('success' , safe=False)
    
    except Exception as e:
          return HttpResponse(extractdb_errormsg(e),status=400)


def getAllSCUCDatesPage(request):
    try:
        old_dates = list(SCUCCCBaseModel.objects.distinct('Letter_date').values_list('Letter_date' , flat=True))
        return JsonResponse({'success':True , 'old_dates' : old_dates} , safe=False)

    except Exception as e:
        return HttpResponse(extractdb_errormsg(e),status=400)

def getAllSCUCDates():
    try:
        scuc_dates=list(SCUCCCBaseModel.objects.distinct('Letter_date').order_by('Letter_date').values_list('Letter_date',flat=True))
        return scuc_dates
    except Exception as e:
        extractdb_errormsg(e)
        return []
    
def getSCUCCCBills(request):
    try:
        letter_date = request.body.decode('utf-8')
        bills_df = pd.DataFrame( SCUCCCBaseModel.objects.filter(Letter_date = letter_date , PayableorReceivable = 'Receivable').values('id', 'Entity',
       'Final_charges', 'PayableorReceivable') , columns=['id', 'Entity',
       'Final_charges', 'PayableorReceivable'])
        # get disbursed details also
        disbursed_df = pd.DataFrame(SCUCCCReceivables.objects.filter(rcvstatus_fk__Letter_date = letter_date).values('rcvstatus_fk__id','Disbursed_amount'), columns=['rcvstatus_fk__id','Disbursed_amount'])
        # Group by and sum
        result_df = disbursed_df.groupby("rcvstatus_fk__id", as_index=False)["Disbursed_amount"].sum()
     
        # merge df
        merged_df = pd.merge(bills_df , result_df ,left_on=['id'] , right_on=['rcvstatus_fk__id'] , how='left')
        # drop unnecessary columns
        merged_df.drop(columns=['rcvstatus_fk__id'] , inplace=True)
        # replace NaN with 0
        merged_df['Disbursed_amount'].fillna(0 , inplace=True)
        merged_df["Amount_to_disburse"] = merged_df["Final_charges"].astype(float) - merged_df["Disbursed_amount"].astype(float)
        # get latest surplus amount based on latest Disbursed_date
        latest_surplus_amount = DisbursementStatus.objects.filter().order_by('-Disbursed_date', '-id').values('Surplus_amt').first()
        surplus_amt = latest_surplus_amount['Surplus_amt'] if latest_surplus_amount else 0
        
        return JsonResponse({'success':True , 'specific_bills' : merged_df.to_dict(orient='records'), 'surplus_amount': surplus_amt} , safe=False)
    except Exception as e:
        return HttpResponse(extractdb_errormsg(e),status=400)
    
def scucccDisbursement(request):
    try:
        in_data = json.loads(request.body)
        table_data = in_data['formdata']
        letter_date = in_data['letter_date']
        remaining_surplus_amount = in_data['remaining_balance']
        
        # check if already disbursed then send the file to frontend
        if SCUCCCReceivables.objects.filter(rcvstatus_fk__Letter_date = letter_date).count() > 0 :
            return JsonResponse({'success':True ,'message' : 'Already Disbursed for the date'} , safe=False)
        else:
            # Get the latest record by Disbursed_date and create a new DisbursementStatus
            # copying all fields, updating Surplus_amt and appending remark 'SCUC disbursement done'
            # latest_vals = DisbursementStatus.objects.order_by('-Disbursed_date', '-id').values().first()
            # if latest_vals:
            #     # remove id to allow creating a new record
            #     latest_vals.pop('id', None)
            #     # set Surplus_amt from request (remaining_surplus_amount)
            #     latest_vals['Surplus_amt'] = remaining_surplus_amount
            #     suffix = ' SCUC_CC disbursement done on ' + letter_date + ' with disbursal amount of '+ str(in_data['total_dis_amount'])
            #     latest_vals['remarks'] =  suffix.strip()
            #     # create a new DisbursementStatus row with updated surplus and remarks
            #     DisbursementStatus.objects.create(**latest_vals)

            latest_obj = (
                DisbursementStatus.objects
                .order_by('-Disbursed_date', '-id')
                .first()
            )

            if latest_obj:
                existing_remarks = latest_obj.remarks or ""
                suffix = (
                    " SCUC_CC disbursement done on "
                    + letter_date
                    + " with disbursal amount of "
                    + str(in_data['total_dis_amount'])
                )

                latest_obj.Surplus_amt = remaining_surplus_amount
                latest_obj.remarks = (existing_remarks + suffix).strip()
                latest_obj.save(update_fields=['Surplus_amt', 'remarks'])

            # store the disbursed values
            for row in table_data:
                SCUCCCReceivables(
                    Disbursed_amount=row['Amount_to_disburse'],
                    rcvstatus_fk=SCUCCCBaseModel.objects.get(id= row['id']),
                    iom_date = datetime.today().date(),
                    disbursed_date = datetime.today().date()
                ).save()
           
            return JsonResponse({'success':True ,'message' :'Disbursed Successfully , Proceed for IOM'} , safe=False)
    except Exception as e:
        return HttpResponse(extractdb_errormsg(e),status=400)

def downloadSCUCCCCIOM(request):
    try:
        letter_date = json.loads(request.body)['letter_date']
        # ***************** receivables section ****************
        all_receivables=[]
        receivables_df=pd.DataFrame(SCUCCCReceivables.objects.filter(rcvstatus_fk__Letter_date = letter_date ,rcvstatus_fk__PayableorReceivable='Receivable').values('rcvstatus_fk__Entity','rcvstatus_fk__Fin_code','rcvstatus_fk__Final_charges','Disbursed_amount'),columns=['rcvstatus_fk__Entity','rcvstatus_fk__Fin_code','rcvstatus_fk__Final_charges','Disbursed_amount'])
        # Remove prefix from column names
        receivables_df.rename(
            columns=lambda x: x.replace("rcvstatus_fk__", ""),
            inplace=True
        )
        for _,row in receivables_df.iterrows():
            temp_rec=row.to_dict()
            temp_rec['Final_charges']=format_indian_currency(temp_rec['Final_charges'])
            temp_rec['Disbursed_amount']=format_indian_currency(temp_rec['Disbursed_amount'])
            temp_rec['duetopool'] = format_indian_currency( row['Final_charges'] - row['Disbursed_amount'])
            # get bank account details
            bank_qry=list(BankDetails.objects.filter(Q(fin_code_fk__fin_code=row['Fin_code']) ,(Q(fin_code_fk__end_date__isnull=True) | Q(fin_code_fk__end_date__gte=datetime.today()) ) ).values('bank_name','bank_account','ifsc_code') )
            temp_rec['Entity']=getFeesChargesName(row['Fin_code'])

            bank_name, account_no, ifsc_code = (
                (bank_qry[0].get('bank_name', ''), bank_qry[0].get('bank_account', ''), bank_qry[0].get('ifsc_code', ''))
                if len(bank_qry) == 1 else ('', '', '')
            )

            temp_rec['bank_name']=bank_name
            temp_rec['acc_no']=account_no
            temp_rec['ifsc_code']=ifsc_code
            all_receivables.append(temp_rec)
        # now generate IOM
        try:
            subject='Disbursement  from DAS Pool Account. / सप्ताह '+' के लिए डीएसएम पूल से संवितरण .' 
        except:
            subject='Disbursement  from DAS Pool Account. / सप्ताह '+'---'

        doc = DocxTemplate("templates/SCUC_CC.docx")

        letter_date_str=datetime.strptime(letter_date,'%Y-%m-%d').strftime('%d-%m-%Y')
       
        context={
                'letter_date':letter_date_str,
                'subject':subject,
                'acc_type':'SCUC CC',
                'receivables':all_receivables,
                'totalreceived':getCalSum(all_receivables,'Final_charges'),
                'totaldisbursed':getCalSum(all_receivables,'Disbursed_amount'),
                'receivabledue':getCalSum(all_receivables,'duetopool')
            }

        doc.render(context)   
        # all MWH files goes to this folder
        parent_folder = os.path.abspath(os.path.join(base_dir, os.pardir))
        directory = os.path.join(parent_folder, 'IOMS')

        docx_directory=os.path.join(directory,'Docx')

        if not os.path.exists(docx_directory):
                os.makedirs(docx_directory)

        inname_docx=letter_date_str+'_SCUC_IOM'+'.docx'
        output_file=os.path.join(docx_directory, inname_docx)
        doc.save(output_file)

        with open(output_file, 'rb') as docx_file:
            response = HttpResponse(docx_file.read(), content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
            response['Content-Disposition'] = 'attachment;'

        return response
    except Exception as e:
        return HttpResponse(extractdb_errormsg(e),status=400)