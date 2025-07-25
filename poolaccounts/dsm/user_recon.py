from .models import *
from django.http import JsonResponse , HttpResponse,FileResponse
import json
from .reconciliation import *
import os
import math
from datetime import date,timedelta
from fpdf import FPDF
from .common import format_indian_currency_withoutsymbol , get_quarter_end_date
from registration.fetch_data import getFCName
import pandas as pd

def get_quarter_dates(fin_year_str, quarter):
    start_year = int(fin_year_str.split('-')[0])
    end_year = start_year + 1


    quarter_dates = {
        "Q1": (date(start_year, 4, 1), date(start_year, 6, 30)),
        "Q2": (date(start_year, 7, 1), date(start_year, 9, 30)),
        "Q3": (date(start_year, 10, 1), date(start_year, 12, 31)),
        "Q4": (date(end_year, 1, 1), date(end_year, 3, 31)),
    }

    return quarter_dates.get(quarter)

def removeNanValues(lst):
    try:
        df = pd.DataFrame(lst)
        return df.fillna('' , inplace=True).values.tolist()
    except:
        return df.values.tolist()

def checkBillsNotified(acc_type , fin_year , quarter):
    try:
        if ReconNotified.objects.filter(
            Acc_type = acc_type ,
            Fin_year = fin_year ,
            Quarter = quarter ).count() > 0 :
            return True
        else : return False
    except:
        return False
def notifyReconBills(request):
    try:
        req_data = json.loads(request.body)
        ReconNotified(
            Acc_type = req_data['formdata']['acc_type'] ,
            Fin_year = req_data['formdata']['fin_year'] ,
            Quarter = req_data['formdata']['quarter'] 
        ).save()

        return JsonResponse({'status' : True , 'message' : 'Bills Notified Successfully'}  , safe=False)
    except:
        return JsonResponse({'status' : False , 'message' : f'Bills are already notified'} , safe= False)

def getLastReconSubmits(request):
    try:
        in_data = json.loads(request.body)
        last_recon_submits = list( ReconUploadStatus.objects.filter(Fin_code = in_data['fincode']).order_by('-Uploaded_time').values('Acc_type','Fin_year','Quarter','Uploaded_time' ,'Upload_status' ,'Admin_remarks' ) )

        return JsonResponse(last_recon_submits , safe=False)
    
    except:
        return JsonResponse([] , safe=False)
    
def reco_for_user(fin_code,startdate,enddate,acc_type):
    try:
        if acc_type == 'DSM':
            basemodel_obj = DSMBaseModel.objects.filter(Q(Letter_date__range=[startdate,enddate]))

            basemodel_qry = basemodel_obj.filter(Q(PayableorReceivable='Payable',payments__Paid_date__isnull=True ))
            basemodel_qry_rcv = basemodel_obj.filter(Q(PayableorReceivable='Receivable',dsmreceivables__disbursed_date__isnull=True ))
            basemodel_qry_next_rcv = basemodel_obj.filter(Q(PayableorReceivable='Receivable',dsmreceivables__disbursed_date__gt = enddate ))
            basemodel_qry_next_pay = basemodel_obj.filter(Q(PayableorReceivable='Payable',payments__Paid_date__gt=enddate))
            
            payments_model_qry = Payments.objects.filter(Paid_date__range=[startdate,enddate],is_revision=False)
            receivables_qry = DSMReceivables.objects.filter(disbursed_date__range=[startdate,enddate],is_revision=False)
            
            rev_payments_qry = RevisionPayments.objects.filter(Paid_date__range=[startdate,enddate])
            basemodel_obj_rev = RevisionBaseModel.objects.filter(Q(Letter_date__range=[startdate, enddate], Acc_type='DSM_REVISION'))
            receivables_qry_rev = RevisionReceivables.objects.filter(disbursed_date__range=[startdate,enddate])
            
            basemodel_qry_rcv_rev = basemodel_obj_rev.filter(Q(PayableorReceivable='Receivable',revisionreceivables__disbursed_date__isnull=True ))
            basemodel_qry_next_rcv_rev = basemodel_obj_rev.filter(Q(PayableorReceivable='Receivable',revisionreceivables__disbursed_date__gt = enddate ))
            rev_basemodel_qry = basemodel_obj_rev.filter(Q(PayableorReceivable='Payable',revisionpayments__Paid_date__isnull=True ))
            rev_basemodel_qry_next_pay = basemodel_obj_rev.filter(Q(PayableorReceivable='Payable',revisionpayments__Paid_date__gt=enddate))

        elif acc_type == 'REAC':
            basemodel_obj = REACBaseModel.objects.filter(Q(Letter_date__range=[startdate,enddate]))

            basemodel_qry = basemodel_obj.filter(Q(PayableorReceivable='Payable',reacpayments__Paid_date__isnull=True,Effective_end_date__isnull=True ))

            basemodel_qry_rcv = basemodel_obj.filter(Q(PayableorReceivable='Receivable',reacreceivables__disbursed_date__isnull=True,Effective_end_date__isnull=True ))

            basemodel_qry_next_rcv = basemodel_obj.filter(Q(PayableorReceivable='Receivable',reacreceivables__disbursed_date__gt = enddate ))

            basemodel_qry_next_pay = basemodel_obj.filter(Q(PayableorReceivable='Payable',reacpayments__Paid_date__gt=enddate ))

            payments_model_qry = REACPayments.objects.filter(Paid_date__range=[startdate,enddate])
            receivables_qry = REACReceivables.objects.filter(disbursed_date__range=[startdate,enddate])
            rev_payments_qry = RevisionPayments.objects.filter(Paid_date__range=[startdate,enddate],paystatus_fk__Acc_type='REAC_REVISION')
            basemodel_obj_rev = RevisionBaseModel.objects.filter(Q(Letter_date__range=[startdate, enddate], Acc_type='REAC_REVISION'))
            receivables_qry_rev = RevisionReceivables.objects.filter(disbursed_date__range=[startdate,enddate],rcvstatus_fk__Acc_type='REAC_REVISION')
            
            basemodel_qry_rcv_rev = basemodel_obj_rev.filter(Q(PayableorReceivable='Receivable',revisionreceivables__disbursed_date__isnull=True ))
            basemodel_qry_next_rcv_rev = basemodel_obj_rev.filter(Q(PayableorReceivable='Receivable',revisionreceivables__disbursed_date__gt = enddate ))
            rev_basemodel_qry = basemodel_obj_rev.filter(Q(PayableorReceivable='Payable',revisionpayments__Paid_date__isnull=True ))
            rev_basemodel_qry_next_pay = basemodel_obj_rev.filter(Q(PayableorReceivable='Payable',revisionpayments__Paid_date__gt=enddate))
            
            


        elif acc_type == 'NET_AS':
            basemodel_obj = NetASBaseModel.objects.filter(Q(Letter_date__range=[startdate,enddate]))

            basemodel_qry = basemodel_obj.filter(Q(PayableorReceivable='Payable',netaspayments__Paid_date__isnull=True, Effective_end_date__isnull=True ))

            basemodel_qry_rcv = basemodel_obj.filter(Q(PayableorReceivable='Receivable',netasreceivables__disbursed_date__isnull=True, Effective_end_date__isnull=True ))

            basemodel_qry_next_rcv = basemodel_obj.filter(Q(PayableorReceivable='Receivable',netasreceivables__disbursed_date__gt = enddate ))

            basemodel_qry_next_pay = basemodel_obj.filter(Q(PayableorReceivable='Payable',netaspayments__Paid_date__gt=enddate ))

            payments_model_qry = NetASPayments.objects.filter(Paid_date__range=[startdate,enddate])
            receivables_qry = NetASReceivables.objects.filter(disbursed_date__range=[startdate,enddate])
            rev_payments_qry = RevisionPayments.objects.filter(Paid_date__range=[startdate,enddate])

            basemodel_obj_rev = RevisionBaseModel.objects.filter(Q(Letter_date__range=[startdate, enddate], Acc_type='NETAS_REVISION'))
            receivables_qry_rev = RevisionReceivables.objects.filter(disbursed_date__range=[startdate,enddate])
            
            basemodel_qry_rcv_rev = basemodel_obj_rev.filter(Q(PayableorReceivable='Receivable',revisionreceivables__disbursed_date__isnull=True ))
            basemodel_qry_next_rcv_rev = basemodel_obj_rev.filter(Q(PayableorReceivable='Receivable',revisionreceivables__disbursed_date__gt = enddate ))
            rev_basemodel_qry = basemodel_obj_rev.filter(Q(PayableorReceivable='Payable',revisionpayments__Paid_date__isnull=True,Letter_date__range=[startdate,enddate] ))
            rev_basemodel_qry_next_pay = basemodel_obj_rev.filter(Q(PayableorReceivable='Payable',revisionpayments__Paid_date__gt=enddate,Letter_date__range=[startdate,enddate]))

        all_paid_inrange_df = pd.DataFrame(payments_model_qry.filter(paystatus_fk__Fin_code=fin_code).values('paystatus_fk__Week_no','paystatus_fk__Week_startdate','paystatus_fk__Week_enddate','paystatus_fk__Revision_no','paystatus_fk__Final_charges','paystatus_fk__Letter_date','Paid_date','Paid_amount') , columns = ['paystatus_fk__Week_no','paystatus_fk__Week_startdate','paystatus_fk__Week_enddate','paystatus_fk__Revision_no','paystatus_fk__Final_charges','paystatus_fk__Letter_date','Paid_date','Paid_amount'])
        all_paid_inrange_rev = all_paid_inrange_df[all_paid_inrange_df['paystatus_fk__Revision_no']>0]
        for _,row in all_paid_inrange_rev.iterrows():
            if acc_type == 'DSM' :
                df_dsm_pay = DSMBaseModel.objects.filter(
                    Week_no=row['paystatus_fk__Week_no'],
                    Week_startdate=row['paystatus_fk__Week_startdate'],
                    Week_enddate=row['paystatus_fk__Week_enddate'],
                    Fin_code=fin_code,
                    Revision_no=0
                ).values('Final_charges','Letter_date')
            elif acc_type == 'REAC':
                df_dsm_pay = REACBaseModel.objects.filter(
                    Week_no=row['paystatus_fk__Week_no'],
                    Week_startdate=row['paystatus_fk__Week_startdate'],
                    Week_enddate=row['paystatus_fk__Week_enddate'],
                    Fin_code=fin_code,
                    Revision_no=0
                ).values('Final_charges','Letter_date')
            elif acc_type == 'NET_AS':
                df_dsm_pay = NetASBaseModel.objects.filter(
                    Week_no=row['paystatus_fk__Week_no'],
                    Week_startdate=row['paystatus_fk__Week_startdate'],
                    Week_enddate=row['paystatus_fk__Week_enddate'],
                    Fin_code=fin_code,
                    Revision_no=0
                ).values('Final_charges','Letter_date')   
            all_paid_inrange_df.loc[all_paid_inrange_df['paystatus_fk__Week_no'] == row['paystatus_fk__Week_no'], 'paystatus_fk__Final_charges'] = df_dsm_pay[0]['Final_charges']
            all_paid_inrange_df.loc[all_paid_inrange_df['paystatus_fk__Week_no'] == row['paystatus_fk__Week_no'], 'paystatus_fk__Letter_date'] = df_dsm_pay[0]['Letter_date']        
        
        all_paid_inrange_df.drop(columns=['paystatus_fk__Revision_no'], inplace=True)
        # calculate outstanding amount

        all_paid_inrange_df['paystatus_fk__Letter_date'] = pd.to_datetime(all_paid_inrange_df['paystatus_fk__Letter_date'])
        start_date_pd = pd.to_datetime(startdate)

        all_paid_inrange_df.loc[
            (all_paid_inrange_df['paystatus_fk__Letter_date'].notna()) &
            (all_paid_inrange_df['paystatus_fk__Letter_date'] < start_date_pd),
            'paystatus_fk__Final_charges'
        ] = 0
        

        all_paid_inrange_df['Paid_date'] = pd.to_datetime(all_paid_inrange_df['Paid_date'])
        end_date_pd = pd.to_datetime(enddate)
        all_paid_inrange_df.loc[
            (all_paid_inrange_df['paystatus_fk__Letter_date'].notna()) &
            (all_paid_inrange_df['paystatus_fk__Letter_date'] > end_date_pd),
            'paystatus_fk__Final_charges'
        ] = 0
        
        all_paid_inrange_df.loc[
            (all_paid_inrange_df['Paid_date'].notna()) &
            (all_paid_inrange_df['Paid_date'] > end_date_pd),
            'Paid_amount'
        ] = 0
        
        # Set Final_charges to 0 for duplicate (Week_no, Week_startdate, Week_enddate), keep only the first occurrence
        duplicate_mask = all_paid_inrange_df.duplicated(subset=['paystatus_fk__Week_no', 'paystatus_fk__Week_startdate', 'paystatus_fk__Week_enddate'])
        all_paid_inrange_df.loc[duplicate_mask, 'paystatus_fk__Final_charges'] = 0

        all_paid_inrange_df['Outstanding'] = all_paid_inrange_df['paystatus_fk__Final_charges']  - all_paid_inrange_df['Paid_amount'] 
        
        
        all_paid_inrange = all_paid_inrange_df.values.tolist()
        all_paid_inrange_list=[list(ele) for ele in all_paid_inrange]

        not_paid_inrange_1=list(basemodel_qry.filter(Fin_code=fin_code,Revision_no = 0).values_list('Week_no','Week_startdate','Week_enddate','Final_charges','Letter_date'))
        
        not_paid_inrange_rev = list(rev_basemodel_qry.filter(Fin_code=fin_code).values_list('Final_charges', 'Letter_date'))
        not_paid_inrange_rev = [["Revision", pd.NaT, pd.NaT, ele[0], ele[1], '', 0] for ele in not_paid_inrange_rev]
        
        not_paid_inrange = not_paid_inrange_1+ not_paid_inrange_rev

        
        paid_outrange_1 = list(basemodel_qry_next_pay.filter(Fin_code=fin_code,Revision_no = 0).values_list('Week_no','Week_startdate','Week_enddate','Final_charges','Letter_date'))
        paid_outrange_rev = list(rev_basemodel_qry_next_pay.filter(Fin_code=fin_code).values_list('Final_charges', 'Letter_date'))
        paid_outrange_rev = [["Revision",pd.NaT, pd.NaT, ele[0], ele[1]] for ele in paid_outrange_rev]
        paid_outrange = paid_outrange_1 + paid_outrange_rev
        
        
        not_paid_inrange_list=[list(ele) for ele in not_paid_inrange]
        paid_outrange_list = [list(ele) for ele in paid_outrange]
        not_paid_inrange_list =  not_paid_inrange_list+paid_outrange_list
        
        for not_paid in not_paid_inrange_list:
            not_paid.append('')
            not_paid.append('')
            not_paid.append(not_paid[3])
            all_paid_inrange_list.append(not_paid.copy())

        
        
        all_paid_inrange_df_rev = pd.DataFrame(rev_payments_qry.filter(paystatus_fk__Fin_code=fin_code).values('paystatus_fk__Entity','paystatus_fk__Final_charges','paystatus_fk__Letter_date','Paid_date','Paid_amount') , columns = ['paystatus_fk__Entity','paystatus_fk__Final_charges','paystatus_fk__Letter_date','Paid_date','Paid_amount'])
        if len(all_paid_inrange_df_rev):
            all_paid_inrange_df_rev['paystatus_fk__Week_no'] = "Revision"
            all_paid_inrange_df_rev['paystatus_fk__Week_startdate'] = pd.NaT
            all_paid_inrange_df_rev['paystatus_fk__Week_enddate'] = pd.NaT
            all_paid_inrange_df_rev = all_paid_inrange_df_rev[['paystatus_fk__Week_no', 'paystatus_fk__Week_startdate', 'paystatus_fk__Week_enddate', 'paystatus_fk__Final_charges', 'paystatus_fk__Letter_date', 'Paid_date', 'Paid_amount']]
            all_paid_inrange_df_rev['paystatus_fk__Letter_date'] = pd.to_datetime(all_paid_inrange_df_rev['paystatus_fk__Letter_date'])
            start_date_pd = pd.to_datetime(startdate)
            all_paid_inrange_df_rev.loc[
                (all_paid_inrange_df_rev['paystatus_fk__Letter_date'].notna()) &
                (all_paid_inrange_df_rev['paystatus_fk__Letter_date'] < start_date_pd),
                'paystatus_fk__Final_charges'] = 0
            all_paid_inrange_df_rev['Paid_date'] = pd.to_datetime(all_paid_inrange_df_rev['Paid_date'])
            end_date_pd = pd.to_datetime(enddate)
            all_paid_inrange_df_rev.loc[
                (all_paid_inrange_df_rev['paystatus_fk__Letter_date'].notna()) &
                (all_paid_inrange_df_rev['paystatus_fk__Letter_date'] > end_date_pd),
                'paystatus_fk__Final_charges'] = 0
            all_paid_inrange_df_rev.loc[
                (all_paid_inrange_df_rev['Paid_date'].notna()) &
                (all_paid_inrange_df_rev['Paid_date'] > end_date_pd),
                'Paid_amount'] = 0
            
            all_paid_inrange_df_rev['Outstanding'] = all_paid_inrange_df_rev['paystatus_fk__Final_charges'] - all_paid_inrange_df_rev['Paid_amount']
            all_paid_inrange_list += all_paid_inrange_df_rev.values.tolist()


        
            
        if acc_type == 'DSM':
            excess_model_qry = ExcessBaseModel.objects.filter(Paid_date__range = [startdate,enddate] )
            excess_payments_qry = list(excess_model_qry.filter(Fin_code = fin_code,).values_list('Acc_Type','Final_charges','Paid_date','Final_charges'))
            excess_payments_list=[list(ele) for ele in excess_payments_qry]

            for excess in excess_payments_list:
                excess.insert(3, None)
                excess.insert(4, None)
                excess.append(0)
            all_paid_inrange_list+= excess_payments_list


        all_rcv_inrange_df=pd.DataFrame(receivables_qry.filter(rcvstatus_fk__Fin_code=fin_code).values('rcvstatus_fk__Week_no','rcvstatus_fk__Week_startdate','rcvstatus_fk__Week_enddate','rcvstatus_fk__Letter_date','rcvstatus_fk__Disbursement_date','rcvstatus_fk__Revision_no','rcvstatus_fk__Final_charges','Disbursed_amount','disbursed_date') , columns=['rcvstatus_fk__Week_no','rcvstatus_fk__Week_startdate','rcvstatus_fk__Week_enddate','rcvstatus_fk__Letter_date','rcvstatus_fk__Disbursement_date','rcvstatus_fk__Revision_no','rcvstatus_fk__Final_charges','Disbursed_amount','disbursed_date'])
        all_rcv_inrange_rev = all_rcv_inrange_df[all_rcv_inrange_df['rcvstatus_fk__Revision_no']>0]
        for _, row in all_rcv_inrange_rev.iterrows():
            if acc_type == 'DSM':
                df_dsm_rcv = DSMBaseModel.objects.filter(
                    Week_no=row['rcvstatus_fk__Week_no'],
                    Week_startdate=row['rcvstatus_fk__Week_startdate'],
                    Week_enddate=row['rcvstatus_fk__Week_enddate'],
                    Fin_code=fin_code,
                    Revision_no=0
                ).values('Final_charges','Letter_date')
            elif acc_type == 'REAC':    
                df_dsm_rcv = REACBaseModel.objects.filter(
                    Week_no=row['rcvstatus_fk__Week_no'],
                    Week_startdate=row['rcvstatus_fk__Week_startdate'],
                    Week_enddate=row['rcvstatus_fk__Week_enddate'],
                    Fin_code=fin_code,
                    Revision_no=0
                ).values('Final_charges','Letter_date')
            elif acc_type == 'NET_AS':
                df_dsm_rcv = NetASBaseModel.objects.filter(
                    Week_no=row['rcvstatus_fk__Week_no'],
                    Week_startdate=row['rcvstatus_fk__Week_startdate'],
                    Week_enddate=row['rcvstatus_fk__Week_enddate'],
                    Fin_code=fin_code,
                    Revision_no=0
                ).values('Final_charges','Letter_date')
            all_rcv_inrange_df.loc[all_rcv_inrange_df['rcvstatus_fk__Week_no'] == row['rcvstatus_fk__Week_no'], 'rcvstatus_fk__Final_charges'] = df_dsm_rcv[0]['Final_charges']
            all_rcv_inrange_df.loc[all_rcv_inrange_df['rcvstatus_fk__Week_no'] == row['rcvstatus_fk__Week_no'], 'rcvstatus_fk__Letter_date'] = df_dsm_rcv[0]['Letter_date']


        all_rcv_inrange_df.drop(columns=['rcvstatus_fk__Revision_no'], inplace=True)
        all_rcv_inrange_df['rcvstatus_fk__Letter_date'] = pd.to_datetime(all_rcv_inrange_df['rcvstatus_fk__Letter_date'])
        start_date = pd.to_datetime(startdate)

        all_rcv_inrange_df.loc[all_rcv_inrange_df['rcvstatus_fk__Letter_date'] < start_date, 'rcvstatus_fk__Final_charges'] = 0

        all_rcv_outrange_df=pd.DataFrame(basemodel_qry_rcv.filter(Fin_code=fin_code).values('Week_no','Week_startdate','Week_enddate','Letter_date','Disbursement_date','Final_charges') , columns=['Week_no','Week_startdate','Week_enddate','Letter_date','Disbursement_date','Final_charges'])
        all_rcv_outrange_df['Disbursed_amount'] = 0

        all_rcv_outrange_df['disbursed_date'] = pd.NaT

        all_rcv_out_next_df = pd.DataFrame(basemodel_qry_next_rcv.filter(Fin_code=fin_code).values('Week_no','Week_startdate','Week_enddate','Letter_date','Disbursement_date','Final_charges') , columns=['Week_no','Week_startdate','Week_enddate','Letter_date','Disbursement_date','Final_charges'])
        all_rcv_out_next_df['Disbursed_amount'] = 0

        all_rcv_out_next_df['disbursed_date'] = pd.NaT
                
        all_rcv_outrange_df.columns = ['rcvstatus_fk__Week_no','rcvstatus_fk__Week_startdate','rcvstatus_fk__Week_enddate', 'rcvstatus_fk__Letter_date','rcvstatus_fk__Disbursement_date', 'rcvstatus_fk__Final_charges', 'Disbursed_amount', 'disbursed_date']
        all_rcv_out_next_df.columns = ['rcvstatus_fk__Week_no','rcvstatus_fk__Week_startdate','rcvstatus_fk__Week_enddate', 'rcvstatus_fk__Letter_date','rcvstatus_fk__Disbursement_date', 'rcvstatus_fk__Final_charges', 'Disbursed_amount', 'disbursed_date']
        all_rcv_outrange_df['rcvstatus_fk__Letter_date'] = pd.to_datetime(all_rcv_outrange_df['rcvstatus_fk__Letter_date'])
        all_rcv_out_next_df['rcvstatus_fk__Letter_date'] = pd.to_datetime(all_rcv_out_next_df['rcvstatus_fk__Letter_date'])

        all_rcv_inrange_df_rev = pd.DataFrame(receivables_qry_rev.filter(rcvstatus_fk__Fin_code=fin_code).values('rcvstatus_fk__Final_charges','rcvstatus_fk__Letter_date','Disbursed_amount','disbursed_date') , columns = ['rcvstatus_fk__Final_charges','rcvstatus_fk__Letter_date','Disbursed_amount','disbursed_date'])
        
        if len(all_rcv_inrange_df_rev): 
            all_rcv_inrange_df_rev['rcvstatus_fk__Week_no'] = "Revision"
            all_rcv_inrange_df_rev['rcvstatus_fk__Week_startdate'] = pd.NaT
            all_rcv_inrange_df_rev['rcvstatus_fk__Week_enddate'] = pd.NaT
            all_rcv_inrange_df_rev['rcvstatus_fk__Disbursement_date'] = pd.NaT
            all_rcv_inrange_df_rev = all_rcv_inrange_df_rev[['rcvstatus_fk__Week_no', 'rcvstatus_fk__Week_startdate', 'rcvstatus_fk__Week_enddate', 'rcvstatus_fk__Letter_date', 'rcvstatus_fk__Disbursement_date', 'rcvstatus_fk__Final_charges', 'Disbursed_amount', 'disbursed_date']]
        else:
            all_rcv_inrange_df_rev = pd.DataFrame(columns=['rcvstatus_fk__Week_no', 'rcvstatus_fk__Week_startdate', 'rcvstatus_fk__Week_enddate', 'rcvstatus_fk__Letter_date', 'rcvstatus_fk__Disbursement_date', 'rcvstatus_fk__Final_charges', 'Disbursed_amount', 'disbursed_date'])

        all_rcv_inrange_df_rev['rcvstatus_fk__Letter_date'] = pd.to_datetime(all_rcv_inrange_df_rev['rcvstatus_fk__Letter_date'])
        all_rcv_inrange_df_rev.loc[all_rcv_inrange_df_rev['rcvstatus_fk__Letter_date'] < start_date, 'rcvstatus_fk__Final_charges'] = 0

        all_rcv_outrange_df_rev=pd.DataFrame(basemodel_qry_rcv_rev.filter(Fin_code=fin_code).values('Letter_date','Final_charges') , columns=['Letter_date','Final_charges'])

        if len(all_rcv_outrange_df_rev):
            all_rcv_outrange_df_rev['rcvstatus_fk__Week_no'] = "Revision"
            all_rcv_outrange_df_rev['rcvstatus_fk__Week_startdate'] = pd.NaT
            all_rcv_outrange_df_rev['rcvstatus_fk__Week_enddate'] = pd.NaT
            all_rcv_outrange_df_rev['rcvstatus_fk__Disbursement_date'] = pd.NaT
            all_rcv_outrange_df_rev['Disbursed_amount'] = 0
            all_rcv_outrange_df_rev['disbursed_date'] =  pd.NaT

            all_rcv_outrange_df_rev = all_rcv_outrange_df_rev[['rcvstatus_fk__Week_no', 'rcvstatus_fk__Week_startdate', 'rcvstatus_fk__Week_enddate', 'Letter_date', 'rcvstatus_fk__Disbursement_date', 'Final_charges', 'Disbursed_amount', 'disbursed_date']]

        else:
            all_rcv_outrange_df_rev = pd.DataFrame(columns=['rcvstatus_fk__Week_no', 'rcvstatus_fk__Week_startdate', 'rcvstatus_fk__Week_enddate', 'Letter_date', 'rcvstatus_fk__Disbursement_date', 'Final_charges','Disbursed_amount', 'disbursed_date'])
        
        all_rcv_outrange_df_rev.columns = ['rcvstatus_fk__Week_no','rcvstatus_fk__Week_startdate','rcvstatus_fk__Week_enddate', 'rcvstatus_fk__Letter_date','rcvstatus_fk__Disbursement_date', 'rcvstatus_fk__Final_charges', 'Disbursed_amount', 'disbursed_date']
        
        all_rcv_out_next_df_rev = pd.DataFrame(basemodel_qry_next_rcv_rev.filter(Fin_code=fin_code).values('Letter_date','Final_charges') , columns=['Letter_date','Final_charges'])
        if len(all_rcv_out_next_df_rev):    
            all_rcv_out_next_df_rev['rcvstatus_fk__Week_no'] = "Revision"
            all_rcv_out_next_df_rev['rcvstatus_fk__Week_startdate'] = pd.NaT
            all_rcv_out_next_df_rev['rcvstatus_fk__Week_enddate'] = pd.NaT
            all_rcv_out_next_df_rev['rcvstatus_fk__Disbursement_date'] = pd.NaT
            all_rcv_out_next_df_rev['Disbursed_amount'] = 0 
            all_rcv_out_next_df_rev['disbursed_date'] = pd.NaT
            all_rcv_out_next_df_rev = all_rcv_out_next_df_rev[['rcvstatus_fk__Week_no', 'rcvstatus_fk__Week_startdate', 'rcvstatus_fk__Week_enddate', 'Letter_date', 'rcvstatus_fk__Disbursement_date', 'Final_charges','Disbursed_amount', 'disbursed_date']]

        else:
            all_rcv_out_next_df_rev = pd.DataFrame(columns=['rcvstatus_fk__Week_no', 'rcvstatus_fk__Week_startdate', 'rcvstatus_fk__Week_enddate', 'Letter_date', 'rcvstatus_fk__Disbursement_date', 'Final_charges','Disbursed_amount', 'disbursed_date'])
        all_rcv_out_next_df_rev.columns = ['rcvstatus_fk__Week_no','rcvstatus_fk__Week_startdate','rcvstatus_fk__Week_enddate', 'rcvstatus_fk__Letter_date','rcvstatus_fk__Disbursement_date', 'rcvstatus_fk__Final_charges', 'Disbursed_amount', 'disbursed_date']    


        all_rcv_inrange_df_1 = pd.concat([all_rcv_inrange_df,all_rcv_outrange_df],ignore_index=True).sort_values(by='rcvstatus_fk__Letter_date').reset_index(drop=True)
        
        temp_rcv_inrange_df_1 = pd.concat([all_rcv_inrange_df_1,all_rcv_out_next_df],ignore_index=True)
        
        temp_rcv_inrange_df_2 = pd.concat([temp_rcv_inrange_df_1,all_rcv_inrange_df_rev],ignore_index=True)
        
        temp_rcv_inrange_df_3 = pd.concat([temp_rcv_inrange_df_2,all_rcv_outrange_df_rev],ignore_index=True)
        
        temp_rcv_inrange_df = pd.concat([temp_rcv_inrange_df_3,all_rcv_out_next_df_rev],ignore_index=True)
        
        # Step 1: Group and sum Disbursed_amount
        temp_rcv_inrange_df['Disbursed_amount'] = pd.to_numeric(temp_rcv_inrange_df['Disbursed_amount'], errors='coerce')  # ensure numeric
        # drop Entity name column
        temp_rcv_inrange_df.drop(columns=['rcvstatus_fk__Disbursement_date'] ,inplace= True)
        # Create a helper column to check duplicates of the Week_no + Letter_date combination
        duplicate_mask = temp_rcv_inrange_df.duplicated(subset=['rcvstatus_fk__Week_no', 'rcvstatus_fk__Letter_date'])
        # Set Final_charges to 0 where it's a duplicate
        temp_rcv_inrange_df.loc[duplicate_mask, 'rcvstatus_fk__Final_charges'] = 0
        # calculate Outstanding amount also
        temp_rcv_inrange_df['Outstanding'] = temp_rcv_inrange_df['rcvstatus_fk__Final_charges'] - temp_rcv_inrange_df['Disbursed_amount']
        temp_rcv_inrange_df['rcvstatus_fk__Letter_date'] = pd.to_datetime(temp_rcv_inrange_df['rcvstatus_fk__Letter_date'])

        all_rcv_inrange_list = temp_rcv_inrange_df.sort_values(by='rcvstatus_fk__Letter_date').reset_index(drop=True).values.tolist()    

        return all_paid_inrange_list,all_rcv_inrange_list
    except Exception as e:
        return [] , []



def reco_for_user2(fin_code,startdate,enddate,acc_type):
    try:
        if acc_type == 'DSM':
            basemodel_obj = DSMBaseModel.objects.filter(Q(Letter_date__range=[startdate,enddate]))

            basemodel_qry = basemodel_obj.filter(Q(PayableorReceivable='Payable',payments__Paid_date__isnull=True ))
            basemodel_qry_rcv = basemodel_obj.filter(Q(PayableorReceivable='Receivable',dsmreceivables__disbursed_date__isnull=True ))
            basemodel_qry_next_rcv = basemodel_obj.filter(Q(PayableorReceivable='Receivable',dsmreceivables__disbursed_date__gt = enddate ))
            basemodel_qry_next_pay = basemodel_obj.filter(Q(PayableorReceivable='Payable',payments__Paid_date__gt=enddate))
            
            payments_model_qry = Payments.objects.filter(Paid_date__range=[startdate,enddate],is_revision=False)
            receivables_qry = DSMReceivables.objects.filter(disbursed_date__range=[startdate,enddate],is_revision=False)
            
            rev_payments_qry = RevisionPayments.objects.filter(Paid_date__range=[startdate,enddate])
            basemodel_obj_rev = RevisionBaseModel.objects.filter(Q(Letter_date__range=[startdate, enddate], Acc_type='DSM_REVISION'))
            receivables_qry_rev = RevisionReceivables.objects.filter(disbursed_date__range=[startdate,enddate])
            
            basemodel_qry_rcv_rev = basemodel_obj_rev.filter(Q(PayableorReceivable='Receivable',revisionreceivables__disbursed_date__isnull=True ))
            basemodel_qry_next_rcv_rev = basemodel_obj_rev.filter(Q(PayableorReceivable='Receivable',revisionreceivables__disbursed_date__gt = enddate ))
            rev_basemodel_qry = basemodel_obj_rev.filter(Q(PayableorReceivable='Payable',revisionpayments__Paid_date__isnull=True ))
            rev_basemodel_qry_next_pay = basemodel_obj_rev.filter(Q(PayableorReceivable='Payable',revisionpayments__Paid_date__gt=enddate))

        elif acc_type == 'REAC':
            basemodel_obj = REACBaseModel.objects.filter(Q(Letter_date__range=[startdate,enddate],Revision_no=0))

            basemodel_qry = basemodel_obj.filter(Q(PayableorReceivable='Payable',reacpayments__Paid_date__isnull=True ))

            basemodel_qry_rcv = basemodel_obj.filter(Q(PayableorReceivable='Receivable',reacreceivables__disbursed_date__isnull=True ))

            basemodel_qry_next_rcv = basemodel_obj.filter(Q(PayableorReceivable='Receivable',reacreceivables__disbursed_date__gt = enddate ))

            basemodel_qry_next_pay = basemodel_obj.filter(Q(PayableorReceivable='Payable',reacpayments__Paid_date__gt=enddate ))

            payments_model_qry = REACPayments.objects.filter(Paid_date__range=[startdate,enddate])
            receivables_qry = REACReceivables.objects.filter(disbursed_date__range=[startdate,enddate])
            rev_payments_qry = RevisionPayments.objects.filter(Paid_date__range=[startdate,enddate])
            basemodel_obj_rev = RevisionBaseModel.objects.filter(Q(Letter_date__range=[startdate, enddate], Acc_type='REAC_REVISION'))
            receivables_qry_rev = RevisionReceivables.objects.filter(disbursed_date__range=[startdate,enddate])
            
            basemodel_qry_rcv_rev = basemodel_obj_rev.filter(Q(PayableorReceivable='Receivable',revisionreceivables__disbursed_date__isnull=True ))
            basemodel_qry_next_rcv_rev = basemodel_obj_rev.filter(Q(PayableorReceivable='Receivable',revisionreceivables__disbursed_date__gt = enddate ))
            rev_basemodel_qry = basemodel_obj_rev.filter(Q(PayableorReceivable='Payable',revisionpayments__Paid_date__isnull=True ))
            rev_basemodel_qry_next_pay = basemodel_obj_rev.filter(Q(PayableorReceivable='Payable',revisionpayments__Paid_date__gt=enddate))
            
            

        elif acc_type == 'NET_AS':
            basemodel_obj = NetASBaseModel.objects.filter(Q(Letter_date__range=[startdate,enddate],Revision_no =0))

            basemodel_qry = basemodel_obj.filter(Q(PayableorReceivable='Payable',netaspayments__Paid_date__isnull=True ))

            basemodel_qry_rcv = basemodel_obj.filter(Q(PayableorReceivable='Receivable',netasreceivables__disbursed_date__isnull=True ))

            basemodel_qry_next_rcv = basemodel_obj.filter(Q(PayableorReceivable='Receivable',netasreceivables__disbursed_date__gt = enddate ))

            basemodel_qry_next_pay = basemodel_obj.filter(Q(PayableorReceivable='Payable',netaspayments__Paid_date__gt=enddate ))

            payments_model_qry = NetASPayments.objects.filter(Paid_date__range=[startdate,enddate])
            receivables_qry = NetASReceivables.objects.filter(disbursed_date__range=[startdate,enddate])
            rev_payments_qry = RevisionPayments.objects.filter(Paid_date__range=[startdate,enddate])

            basemodel_obj_rev = RevisionBaseModel.objects.filter(Q(Letter_date__range=[startdate, enddate], Acc_type='NETAS_REVISION'))
            receivables_qry_rev = RevisionReceivables.objects.filter(disbursed_date__range=[startdate,enddate])
            
            basemodel_qry_rcv_rev = basemodel_obj_rev.filter(Q(PayableorReceivable='Receivable',revisionreceivables__disbursed_date__isnull=True ))
            basemodel_qry_next_rcv_rev = basemodel_obj_rev.filter(Q(PayableorReceivable='Receivable',revisionreceivables__disbursed_date__gt = enddate ))
            rev_basemodel_qry = basemodel_obj_rev.filter(Q(PayableorReceivable='Payable',revisionpayments__Paid_date__isnull=True,Letter_date__range=[startdate,enddate] ))
            rev_basemodel_qry_next_pay = basemodel_obj_rev.filter(Q(PayableorReceivable='Payable',revisionpayments__Paid_date__gt=enddate,Letter_date__range=[startdate,enddate]))

        all_paid_inrange_df = pd.DataFrame(payments_model_qry.filter(paystatus_fk__Fin_code=fin_code).values('paystatus_fk__Week_no','paystatus_fk__Week_startdate','paystatus_fk__Week_enddate','paystatus_fk__Revision_no','paystatus_fk__Final_charges','paystatus_fk__Letter_date','Paid_date','Paid_amount') , columns = ['paystatus_fk__Week_no','paystatus_fk__Week_startdate','paystatus_fk__Week_enddate','paystatus_fk__Revision_no','paystatus_fk__Final_charges','paystatus_fk__Letter_date','Paid_date','Paid_amount'])
        all_paid_inrange_rev = all_paid_inrange_df[all_paid_inrange_df['paystatus_fk__Revision_no']>0]
        for _,row in all_paid_inrange_rev.iterrows():
            if acc_type == 'DSM' :
                df_dsm_pay = DSMBaseModel.objects.filter(
                    Week_no=row['paystatus_fk__Week_no'],
                    Week_startdate=row['paystatus_fk__Week_startdate'],
                    Week_enddate=row['paystatus_fk__Week_enddate'],
                    Fin_code=fin_code,
                    Revision_no=0
                ).values('Final_charges','Letter_date')
            elif acc_type == 'REAC':
                df_dsm_pay = REACBaseModel.objects.filter(
                    Week_no=row['paystatus_fk__Week_no'],
                    Week_startdate=row['paystatus_fk__Week_startdate'],
                    Week_enddate=row['paystatus_fk__Week_enddate'],
                    Fin_code=fin_code,
                    Revision_no=0
                ).values('Final_charges','Letter_date')
            elif acc_type == 'NET_AS':
                df_dsm_pay = NetASBaseModel.objects.filter(
                    Week_no=row['paystatus_fk__Week_no'],
                    Week_startdate=row['paystatus_fk__Week_startdate'],
                    Week_enddate=row['paystatus_fk__Week_enddate'],
                    Fin_code=fin_code,
                    Revision_no=0
                ).values('Final_charges','Letter_date')   
            all_paid_inrange_df.loc[all_paid_inrange_df['paystatus_fk__Week_no'] == row['paystatus_fk__Week_no'], 'paystatus_fk__Final_charges'] = df_dsm_pay[0]['Final_charges']
            all_paid_inrange_df.loc[all_paid_inrange_df['paystatus_fk__Week_no'] == row['paystatus_fk__Week_no'], 'paystatus_fk__Letter_date'] = df_dsm_pay[0]['Letter_date']        
        
        all_paid_inrange_df.drop(columns=['paystatus_fk__Revision_no'], inplace=True)
        # calculate outstanding amount
        
        all_paid_inrange_df['paystatus_fk__Letter_date'] = pd.to_datetime(all_paid_inrange_df['paystatus_fk__Letter_date'])
        start_date_pd = pd.to_datetime(startdate)

        all_paid_inrange_df.loc[
            (all_paid_inrange_df['paystatus_fk__Letter_date'].notna()) &
            (all_paid_inrange_df['paystatus_fk__Letter_date'] < start_date_pd),
            'paystatus_fk__Final_charges'
        ] = 0
        

        all_paid_inrange_df['Paid_date'] = pd.to_datetime(all_paid_inrange_df['Paid_date'])
        end_date_pd = pd.to_datetime(enddate)
        all_paid_inrange_df.loc[
            (all_paid_inrange_df['paystatus_fk__Letter_date'].notna()) &
            (all_paid_inrange_df['paystatus_fk__Letter_date'] > end_date_pd),
            'paystatus_fk__Final_charges'
        ] = 0
        
        all_paid_inrange_df.loc[
            (all_paid_inrange_df['Paid_date'].notna()) &
            (all_paid_inrange_df['Paid_date'] > end_date_pd),
            'Paid_amount'
        ] = 0
        
        # Set Final_charges to 0 for duplicate (Week_no, Week_startdate, Week_enddate), keep only the first occurrence
        duplicate_mask = all_paid_inrange_df.duplicated(subset=['paystatus_fk__Week_no', 'paystatus_fk__Week_startdate', 'paystatus_fk__Week_enddate'])
        all_paid_inrange_df.loc[duplicate_mask, 'paystatus_fk__Final_charges'] = 0

        all_paid_inrange_df['Outstanding'] = all_paid_inrange_df['paystatus_fk__Final_charges']  - all_paid_inrange_df['Paid_amount'] 
        
        
        all_paid_inrange = all_paid_inrange_df.values.tolist()
        all_paid_inrange_list=[list(ele) for ele in all_paid_inrange]

        not_paid_inrange_1=list(basemodel_qry.filter(Fin_code=fin_code).values_list('Week_no','Week_startdate','Week_enddate','Final_charges','Letter_date'))
        
        not_paid_inrange_rev = list(rev_basemodel_qry.filter(Fin_code=fin_code).values_list('Final_charges', 'Letter_date'))
        not_paid_inrange_rev = [["Revision", pd.NaT, pd.NaT, ele[0], ele[1], '', 0] for ele in not_paid_inrange_rev]
        
        not_paid_inrange = not_paid_inrange_1+ not_paid_inrange_rev

        
        paid_outrange_1 = list(basemodel_qry_next_pay.filter(Fin_code=fin_code).values_list('Week_no','Week_startdate','Week_enddate','Final_charges','Letter_date'))
        paid_outrange_rev = list(rev_basemodel_qry_next_pay.filter(Fin_code=fin_code).values_list('Final_charges', 'Letter_date'))
        paid_outrange_rev = [["Revision",pd.NaT, pd.NaT, ele[0], ele[1]] for ele in paid_outrange_rev]
        paid_outrange = paid_outrange_1 + paid_outrange_rev
        
        
        not_paid_inrange_list=[list(ele) for ele in not_paid_inrange]
        paid_outrange_list = [list(ele) for ele in paid_outrange]
        not_paid_inrange_list =  not_paid_inrange_list+paid_outrange_list
        
        for not_paid in not_paid_inrange_list:
            not_paid.append('')
            not_paid.append('')
            not_paid.append(not_paid[3])
            all_paid_inrange_list.append(not_paid.copy())

        
        
        all_paid_inrange_df_rev = pd.DataFrame(rev_payments_qry.filter(paystatus_fk__Fin_code=fin_code).values('paystatus_fk__Entity','paystatus_fk__Final_charges','paystatus_fk__Letter_date','Paid_date','Paid_amount') , columns = ['paystatus_fk__Entity','paystatus_fk__Final_charges','paystatus_fk__Letter_date','Paid_date','Paid_amount'])
        if len(all_paid_inrange_df_rev):
            all_paid_inrange_df_rev['paystatus_fk__Week_no'] = "Revision"
            all_paid_inrange_df_rev['paystatus_fk__Week_startdate'] = pd.NaT
            all_paid_inrange_df_rev['paystatus_fk__Week_enddate'] = pd.NaT
            all_paid_inrange_df_rev = all_paid_inrange_df_rev[['paystatus_fk__Week_no', 'paystatus_fk__Week_startdate', 'paystatus_fk__Week_enddate', 'paystatus_fk__Final_charges', 'paystatus_fk__Letter_date', 'Paid_date', 'Paid_amount']]
            all_paid_inrange_df_rev['paystatus_fk__Letter_date'] = pd.to_datetime(all_paid_inrange_df_rev['paystatus_fk__Letter_date'])
            start_date_pd = pd.to_datetime(startdate)
            all_paid_inrange_df_rev.loc[
                (all_paid_inrange_df_rev['paystatus_fk__Letter_date'].notna()) &
                (all_paid_inrange_df_rev['paystatus_fk__Letter_date'] < start_date_pd),
                'paystatus_fk__Final_charges'] = 0
            all_paid_inrange_df_rev['Paid_date'] = pd.to_datetime(all_paid_inrange_df_rev['Paid_date'])
            end_date_pd = pd.to_datetime(enddate)
            all_paid_inrange_df_rev.loc[
                (all_paid_inrange_df_rev['paystatus_fk__Letter_date'].notna()) &
                (all_paid_inrange_df_rev['paystatus_fk__Letter_date'] > end_date_pd),
                'paystatus_fk__Final_charges'] = 0
            all_paid_inrange_df_rev.loc[
                (all_paid_inrange_df_rev['Paid_date'].notna()) &
                (all_paid_inrange_df_rev['Paid_date'] > end_date_pd),
                'Paid_amount'] = 0
            
            all_paid_inrange_df_rev['Outstanding'] = all_paid_inrange_df_rev['paystatus_fk__Final_charges'] - all_paid_inrange_df_rev['Paid_amount']
            all_paid_inrange_list += all_paid_inrange_df_rev.values.tolist()

            
            
        if acc_type == 'DSM':
            excess_model_qry = ExcessBaseModel.objects.filter(Paid_date__range = [startdate,enddate] )
            excess_payments_qry = list(excess_model_qry.filter(Fin_code = fin_code,).values_list('Acc_Type','Final_charges','Paid_date','Final_charges'))
            excess_payments_list=[list(ele) for ele in excess_payments_qry]

            for excess in excess_payments_list:
                excess.insert(3, None)
                excess.insert(4, None)
                excess.append(0)
            all_paid_inrange_list+= excess_payments_list

        all_rcv_inrange_df=pd.DataFrame(receivables_qry.filter(rcvstatus_fk__Fin_code=fin_code).values('rcvstatus_fk__Week_no','rcvstatus_fk__Week_startdate','rcvstatus_fk__Week_enddate','rcvstatus_fk__Letter_date','rcvstatus_fk__Disbursement_date','rcvstatus_fk__Revision_no','rcvstatus_fk__Final_charges','Disbursed_amount','disbursed_date') , columns=['rcvstatus_fk__Week_no','rcvstatus_fk__Week_startdate','rcvstatus_fk__Week_enddate','rcvstatus_fk__Letter_date','rcvstatus_fk__Disbursement_date','rcvstatus_fk__Revision_no','rcvstatus_fk__Final_charges','Disbursed_amount','disbursed_date'])
        all_rcv_inrange_rev = all_rcv_inrange_df[all_rcv_inrange_df['rcvstatus_fk__Revision_no']>0]
        for _, row in all_rcv_inrange_rev.iterrows():
            if acc_type == 'DSM':
                df_dsm_rcv = DSMBaseModel.objects.filter(
                    Week_no=row['rcvstatus_fk__Week_no'],
                    Week_startdate=row['rcvstatus_fk__Week_startdate'],
                    Week_enddate=row['rcvstatus_fk__Week_enddate'],
                    Fin_code=fin_code,
                    Revision_no=0
                ).values('Final_charges','Letter_date')
            elif acc_type == 'REAC':    
                df_dsm_rcv = REACBaseModel.objects.filter(
                    Week_no=row['rcvstatus_fk__Week_no'],
                    Week_startdate=row['rcvstatus_fk__Week_startdate'],
                    Week_enddate=row['rcvstatus_fk__Week_enddate'],
                    Fin_code=fin_code,
                    Revision_no=0
                ).values('Final_charges','Letter_date')
            elif acc_type == 'NET_AS':
                df_dsm_rcv = NetASBaseModel.objects.filter(
                    Week_no=row['rcvstatus_fk__Week_no'],
                    Week_startdate=row['rcvstatus_fk__Week_startdate'],
                    Week_enddate=row['rcvstatus_fk__Week_enddate'],
                    Fin_code=fin_code,
                    Revision_no=0
                ).values('Final_charges','Letter_date')
            all_rcv_inrange_df.loc[all_rcv_inrange_df['rcvstatus_fk__Week_no'] == row['rcvstatus_fk__Week_no'], 'rcvstatus_fk__Final_charges'] = df_dsm_rcv[0]['Final_charges']
            all_rcv_inrange_df.loc[all_rcv_inrange_df['rcvstatus_fk__Week_no'] == row['rcvstatus_fk__Week_no'], 'rcvstatus_fk__Letter_date'] = df_dsm_rcv[0]['Letter_date']

        all_rcv_inrange_df.drop(columns=['rcvstatus_fk__Revision_no'], inplace=True)
        all_rcv_inrange_df['rcvstatus_fk__Letter_date'] = pd.to_datetime(all_rcv_inrange_df['rcvstatus_fk__Letter_date'])
        start_date = pd.to_datetime(startdate)

        all_rcv_inrange_df.loc[all_rcv_inrange_df['rcvstatus_fk__Letter_date'] < start_date, 'rcvstatus_fk__Final_charges'] = 0

        all_rcv_outrange_df=pd.DataFrame(basemodel_qry_rcv.filter(Fin_code=fin_code).values('Week_no','Week_startdate','Week_enddate','Letter_date','Disbursement_date','Final_charges') , columns=['Week_no','Week_startdate','Week_enddate','Letter_date','Disbursement_date','Final_charges'])
        all_rcv_outrange_df['Disbursed_amount'] = 0

        all_rcv_outrange_df['disbursed_date'] = pd.NaT

        all_rcv_out_next_df = pd.DataFrame(basemodel_qry_next_rcv.filter(Fin_code=fin_code).values('Week_no','Week_startdate','Week_enddate','Letter_date','Disbursement_date','Final_charges') , columns=['Week_no','Week_startdate','Week_enddate','Letter_date','Disbursement_date','Final_charges'])
        all_rcv_out_next_df['Disbursed_amount'] = 0

        all_rcv_out_next_df['disbursed_date'] = pd.NaT
                
        all_rcv_outrange_df.columns = ['rcvstatus_fk__Week_no','rcvstatus_fk__Week_startdate','rcvstatus_fk__Week_enddate', 'rcvstatus_fk__Letter_date','rcvstatus_fk__Disbursement_date', 'rcvstatus_fk__Final_charges', 'Disbursed_amount', 'disbursed_date']
        all_rcv_out_next_df.columns = ['rcvstatus_fk__Week_no','rcvstatus_fk__Week_startdate','rcvstatus_fk__Week_enddate', 'rcvstatus_fk__Letter_date','rcvstatus_fk__Disbursement_date', 'rcvstatus_fk__Final_charges', 'Disbursed_amount', 'disbursed_date']
        all_rcv_outrange_df['rcvstatus_fk__Letter_date'] = pd.to_datetime(all_rcv_outrange_df['rcvstatus_fk__Letter_date'])
        all_rcv_out_next_df['rcvstatus_fk__Letter_date'] = pd.to_datetime(all_rcv_out_next_df['rcvstatus_fk__Letter_date'])

        all_rcv_inrange_df_rev = pd.DataFrame(receivables_qry_rev.filter(rcvstatus_fk__Fin_code=fin_code).values('rcvstatus_fk__Final_charges','rcvstatus_fk__Letter_date','Disbursed_amount','disbursed_date') , columns = ['rcvstatus_fk__Final_charges','rcvstatus_fk__Letter_date','Disbursed_amount','disbursed_date'])
        
        if len(all_rcv_inrange_df_rev): 
            all_rcv_inrange_df_rev['rcvstatus_fk__Week_no'] = "Revision"
            all_rcv_inrange_df_rev['rcvstatus_fk__Week_startdate'] = pd.NaT
            all_rcv_inrange_df_rev['rcvstatus_fk__Week_enddate'] = pd.NaT
            all_rcv_inrange_df_rev['rcvstatus_fk__Disbursement_date'] = pd.NaT
            all_rcv_inrange_df_rev = all_rcv_inrange_df_rev[['rcvstatus_fk__Week_no', 'rcvstatus_fk__Week_startdate', 'rcvstatus_fk__Week_enddate', 'rcvstatus_fk__Letter_date', 'rcvstatus_fk__Disbursement_date', 'rcvstatus_fk__Final_charges', 'Disbursed_amount', 'disbursed_date']]
        else:
            all_rcv_inrange_df_rev = pd.DataFrame(columns=['rcvstatus_fk__Week_no', 'rcvstatus_fk__Week_startdate', 'rcvstatus_fk__Week_enddate', 'rcvstatus_fk__Letter_date', 'rcvstatus_fk__Disbursement_date', 'rcvstatus_fk__Final_charges', 'Disbursed_amount', 'disbursed_date'])

        all_rcv_inrange_df_rev['rcvstatus_fk__Letter_date'] = pd.to_datetime(all_rcv_inrange_df_rev['rcvstatus_fk__Letter_date'])
        all_rcv_inrange_df_rev.loc[all_rcv_inrange_df_rev['rcvstatus_fk__Letter_date'] < start_date, 'rcvstatus_fk__Final_charges'] = 0

        all_rcv_outrange_df_rev=pd.DataFrame(basemodel_qry_rcv_rev.filter(Fin_code=fin_code).values('Letter_date','Final_charges') , columns=['Letter_date','Final_charges'])

        if len(all_rcv_outrange_df_rev):
            all_rcv_outrange_df_rev['rcvstatus_fk__Week_no'] = "Revision"
            all_rcv_outrange_df_rev['rcvstatus_fk__Week_startdate'] = pd.NaT
            all_rcv_outrange_df_rev['rcvstatus_fk__Week_enddate'] = pd.NaT
            all_rcv_outrange_df_rev['rcvstatus_fk__Disbursement_date'] = pd.NaT
            all_rcv_outrange_df_rev['Disbursed_amount'] = 0
            all_rcv_outrange_df_rev['disbursed_date'] =  pd.NaT

            all_rcv_outrange_df_rev = all_rcv_outrange_df_rev[['rcvstatus_fk__Week_no', 'rcvstatus_fk__Week_startdate', 'rcvstatus_fk__Week_enddate', 'Letter_date', 'rcvstatus_fk__Disbursement_date', 'Final_charges', 'Disbursed_amount', 'disbursed_date']]

        else:
            all_rcv_outrange_df_rev = pd.DataFrame(columns=['rcvstatus_fk__Week_no', 'rcvstatus_fk__Week_startdate', 'rcvstatus_fk__Week_enddate', 'Letter_date', 'rcvstatus_fk__Disbursement_date', 'Final_charges','Disbursed_amount', 'disbursed_date'])
        
        all_rcv_outrange_df_rev.columns = ['rcvstatus_fk__Week_no','rcvstatus_fk__Week_startdate','rcvstatus_fk__Week_enddate', 'rcvstatus_fk__Letter_date','rcvstatus_fk__Disbursement_date', 'rcvstatus_fk__Final_charges', 'Disbursed_amount', 'disbursed_date']
        
        all_rcv_out_next_df_rev = pd.DataFrame(basemodel_qry_next_rcv_rev.filter(Fin_code=fin_code).values('Letter_date','Final_charges') , columns=['Letter_date','Final_charges'])
        if len(all_rcv_out_next_df_rev):    
            all_rcv_out_next_df_rev['rcvstatus_fk__Week_no'] = "Revision"
            all_rcv_out_next_df_rev['rcvstatus_fk__Week_startdate'] = pd.NaT
            all_rcv_out_next_df_rev['rcvstatus_fk__Week_enddate'] = pd.NaT
            all_rcv_out_next_df_rev['rcvstatus_fk__Disbursement_date'] = pd.NaT
            all_rcv_out_next_df_rev['Disbursed_amount'] = 0 
            all_rcv_out_next_df_rev['disbursed_date'] = pd.NaT
            all_rcv_out_next_df_rev = all_rcv_out_next_df_rev[['rcvstatus_fk__Week_no', 'rcvstatus_fk__Week_startdate', 'rcvstatus_fk__Week_enddate', 'Letter_date', 'rcvstatus_fk__Disbursement_date', 'Final_charges','Disbursed_amount', 'disbursed_date']]

        else:
            all_rcv_out_next_df_rev = pd.DataFrame(columns=['rcvstatus_fk__Week_no', 'rcvstatus_fk__Week_startdate', 'rcvstatus_fk__Week_enddate', 'Letter_date', 'rcvstatus_fk__Disbursement_date', 'Final_charges','Disbursed_amount', 'disbursed_date'])
        all_rcv_out_next_df_rev.columns = ['rcvstatus_fk__Week_no','rcvstatus_fk__Week_startdate','rcvstatus_fk__Week_enddate', 'rcvstatus_fk__Letter_date','rcvstatus_fk__Disbursement_date', 'rcvstatus_fk__Final_charges', 'Disbursed_amount', 'disbursed_date']    

        all_rcv_inrange_df_1 = pd.concat([all_rcv_inrange_df,all_rcv_outrange_df],ignore_index=True).sort_values(by='rcvstatus_fk__Letter_date').reset_index(drop=True)
        
        temp_rcv_inrange_df_1 = pd.concat([all_rcv_inrange_df_1,all_rcv_out_next_df],ignore_index=True)
        
        temp_rcv_inrange_df_2 = pd.concat([temp_rcv_inrange_df_1,all_rcv_inrange_df_rev],ignore_index=True)
        
        temp_rcv_inrange_df_3 = pd.concat([temp_rcv_inrange_df_2,all_rcv_outrange_df_rev],ignore_index=True)
        
        temp_rcv_inrange_df = pd.concat([temp_rcv_inrange_df_3,all_rcv_out_next_df_rev],ignore_index=True)
        
        # Step 1: Group and sum Disbursed_amount
        temp_rcv_inrange_df['Disbursed_amount'] = pd.to_numeric(temp_rcv_inrange_df['Disbursed_amount'], errors='coerce')  # ensure numeric
        # drop Entity name column
        temp_rcv_inrange_df.drop(columns=['rcvstatus_fk__Disbursement_date'] ,inplace= True)
        # Create a helper column to check duplicates of the Week_no + Letter_date combination
        duplicate_mask = temp_rcv_inrange_df.duplicated(subset=['rcvstatus_fk__Week_no', 'rcvstatus_fk__Letter_date'])
        # Set Final_charges to 0 where it's a duplicate
        temp_rcv_inrange_df.loc[duplicate_mask, 'rcvstatus_fk__Final_charges'] = 0
        # calculate Outstanding amount also
        temp_rcv_inrange_df['Outstanding'] = temp_rcv_inrange_df['rcvstatus_fk__Final_charges'] - temp_rcv_inrange_df['Disbursed_amount']
        temp_rcv_inrange_df['rcvstatus_fk__Letter_date'] = pd.to_datetime(temp_rcv_inrange_df['rcvstatus_fk__Letter_date'])

        all_rcv_inrange_list = temp_rcv_inrange_df.sort_values(by='rcvstatus_fk__Letter_date').reset_index(drop=True).values.tolist()    

        return all_paid_inrange_list,all_rcv_inrange_list
    except Exception as e:
        import pdb
        pdb.set_trace()
        print(e)
        return [] , []

def userRecon(request):
    try:
        in_data = json.loads(request.body)
        fin_code = in_data['fincode']
        fin_year = in_data['formdata']['fin_year']
        quarter = in_data['formdata']['quarter']
        acc_type = in_data['formdata']['acc_type']
        if not checkBillsNotified(acc_type , fin_year , quarter):
            return HttpResponse( 'Bills not notified , Please wait', status = 404)
        
        start_date,end_date = get_quarter_dates(fin_year,quarter)
        all_payable_lst , all_receivable_lst = reco_for_user2(fin_code,start_date,end_date,acc_type)
        
        
        cleaned_payable_lst = removeNanValues(all_payable_lst)
        cleaned_receivable_lst = removeNanValues(all_receivable_lst)


        return JsonResponse([cleaned_payable_lst , cleaned_receivable_lst] , safe=False)

    except Exception as e:
        return HttpResponse(str(e) , status=404)

def createfolderforRecon(start_date,end_date):
    try:
        foldername = "Reco\\"+ start_date.strftime('%d-%m-%Y')+'&'+end_date.strftime('%d-%m-%Y')+'\\'
        try:   
            if not os.path.exists(os.path.dirname(foldername)):
                os.makedirs(os.path.dirname(foldername))
        except IOError:
            pass

    except Exception as e:
        pass


def getNotifiedDate(acc_type , fin_year ,quarter):
    try:
        notified_date_lst = list(ReconNotified.objects.filter(
            Acc_type =acc_type ,
            Fin_year = fin_year ,
            Quarter =quarter
        ).values_list('Notified_date' , flat=True))

        if len(notified_date_lst) :
            return notified_date_lst[0].strftime('%d %B %Y')
    except : return None

def addSignBottom(pdf , img_path , entity_name , authroizedname):
    try:
        # add signature to bottom corner of the page
        # Signature image dimensions
        signature_width = 40  # in mm
        signature_height = 20  # in mm

        # Padding from edges
        right_padding = 10  # mm
        bottom_padding = 20  # mm (leave space for name below image)

        # Coordinates for the image
        img_x = pdf.w - signature_width - right_padding
        img_y = pdf.h - signature_height - bottom_padding

        # Add the signature image to bottom-right
        pdf.image(img_path, x=img_x, y=img_y, w=signature_width, h=signature_height)
        # Set Y position just below the image
        text_y = img_y + signature_height + 5  # Adjust gap if needed

        # Set font
        pdf.set_font("Arial", "BI" ,size=12)

        # Left-aligned entity name
        pdf.text(x=10, y=text_y, txt=f"( {entity_name} )")  # 10mm is typical left margin

        # Right-aligned authorized name
        right_text = f"( {authroizedname} )"
        right_text_width = pdf.get_string_width(right_text)
        right_margin = 10  # 10mm from right edge
        pdf.text(x=pdf.w - right_text_width - right_margin, y=text_y, txt=right_text)
        pdf.set_font("Arial", "B" ,size=10)
        return pdf
    except:
        return pdf

def Tableheader(pdf , table_header):
    try:
        pdf.set_font("Times", "BU", 16)
        pdf.cell(0, 10, table_header, ln=True, align="C")
        return pdf
    
    except:
        return pdf
    
def print_table_with_wrapped_first_col(pdf, headers, data_rows, col_widths, max_height, line_height,authorized_img_path,entity_fc_name):
    
    def print_header():
        pdf.set_font("Arial", 'B', 10)
        pdf.set_fill_color(200, 220, 255)  # Light blue header
        for header, width in zip(headers, col_widths):
            pdf.cell(width, line_height * 2, header, border=1, align='C', fill=True)
        pdf.ln()

    # Print initial header
    print_header()
    addSignBottom(pdf , authorized_img_path , entity_fc_name,"Praharsha Korangi (Dy. Manager)")
    

    pdf.set_font("Arial", 'B', 10)

    for row in data_rows:
        # Step 1: compute wrapped lines for first column
        first_col_text = str(row[0])
        first_col_width = col_widths[0]
        str_width = pdf.get_string_width(first_col_text)
        num_lines = int(str_width / (first_col_width - 2)) + 1
        row_height = line_height * num_lines

        # Step 2: page break check
        if pdf.get_y() + row_height > max_height:
            pdf.add_page(orientation='L')
            print_header()
            addSignBottom(pdf , authorized_img_path , entity_fc_name,"Praharsha Korangi (Dy. Manager)")

        # Step 3: print first column (wrapped)
        x_start = pdf.get_x()
        y_start = pdf.get_y()
        pdf.multi_cell(first_col_width, line_height, first_col_text, border=1, align='C')

        # Step 4: print other columns
        pdf.set_xy(x_start + first_col_width, y_start)
        for datum, width in zip(row[1:], col_widths[1:]):
            pdf.cell(width, row_height, str(datum), border=1, align='C')
    
        # Step 5: move to next line
        pdf.ln(row_height)

       
def ReconPDF(start_date, end_date, in_data , payable_data , receivable_data,opening_balance,closing_balance):
    try:
        fin_code = in_data['fincode']
        fin_year = in_data['formdata']['fin_year']
        quarter = in_data['formdata']['quarter']
        acc_type = in_data['formdata']['acc_type']
        notified_date = getNotifiedDate(acc_type , fin_year ,quarter)
        entity_fc_name  = getFCName(fin_code)

        createfolderforRecon(start_date, end_date)
        folder_path = f'Reco\\{start_date.strftime("%d-%m-%Y")}&{end_date.strftime("%d-%m-%Y")}'
        os.makedirs(folder_path, exist_ok=True)
        pdf_path = os.path.join(folder_path, f'{fin_code}.pdf')
        letter_head_path = 'templates\\Letter_head.png'
        hod_image_path = 'static\\40016.png'
        authorized_img_path = 'static\\00179.png'
        pdf = FPDF()
        pdf.add_page()

        line_height = 10
        max_height = pdf.h * 0.57  # 57% of page height
        
        # Add image at the top
        pdf.image(letter_head_path, x=0, y=0, w=pdf.w, h=70)
        # Move cursor below the image
        pdf.set_y(75)
        # Move below the image
        # Add Ref.No and Date in a single line
        pdf.set_font("Times",size=12)
        pdf.cell(0, 10, f'Ref.No :SRLDC/MO/DSM/{fin_year}/{quarter}', ln=0)
        pdf.cell(0, 10, f'Date : {notified_date}', ln=1, align='R')
        # Ref No
        pdf.cell(0, 10, "To :", ln=1)
        pdf.cell(0, 10, entity_fc_name, ln=1)
        #Subject
        pdf.set_font("Times","BU" , size=12)  # Reduce font size to 10
        pdf.multi_cell(0, 8,  f'Sub : Reconciliation of Deviation payment and disbursement during the period ({start_date.strftime("%d-%m-%Y")} to {end_date.strftime("%d-%m-%Y")}) of {fin_year}./ {fin_year}' )

        pdf.set_font("Arial", size=10)
        pdf.set_x(20) # Move 10 units from the left
        pdf.multi_cell(0, 9,  "1. Please find the statement in Annexures, duly signed containing the details of payment and disbursement of Deviation Charges with respect to your organization.|" )

        pdf.set_x(20) # Move 10 units from the left
        pdf.multi_cell(0, 9,  "2. Please find the statement in Annexures, duly signed containing the details of payment and disbursement of Deviation Charges with respect to your organization" )

        pdf.set_x(20) # Move 10 units from the left
        pdf.multi_cell(0, 9,  "3. You are requested to check and return the duplicate copy signed, dated and stamped on each page as token of your acknowledgement within 15 days" )

        pdf.set_x(20) # Move 10 units from the left
        pdf.multi_cell(0, 9,  "4. In case of any discrepancy found towards payment details, kindly mail to dsmsrldc@grid-india.in immediately for further clarification.")

        pdf.ln(4)
        pdf.set_font("Courier", size=12)
        pdf.cell(0, 10, "Thanking you", ln=0)
        pdf.cell(0, 10, "Yours Faithfully", ln=1, align='R')
        #add signature
        # Add some space before signature image
        pdf.ln(1)
        # Add text below image
        pdf.set_font("Times", "BI", 10)
        # Coordinates for the signature image
        signature_width = 30
        signature_height = 10

        # Set Y to where you want the image
        img_y = pdf.get_y()
        img_x = pdf.w - pdf.r_margin - signature_width  # Right-align image

        
        # Add the signature image
        pdf.image(hod_image_path, x=img_x, y=img_y, w=signature_width, h=signature_height)

        # Move cursor down slightly below image
        pdf.set_y(img_y + signature_height + 1)


        pdf.cell(0, 10, "C Rethi Nair", ln=1, align='R')
        pdf.cell(0, 10, "Deputy General Manager (MO),", ln=1, align='R')

  
        
        # bottom copy to
        pdf.set_font("Times", "BU", 9)
        pdf.cell(0, 10, "Copy Enclosed :", ln=1)
        pdf.set_x(20) # Move 10 units from the left
        pdf.multi_cell(0, 9,  f'1.Annexure I : Details of payments made by {entity_fc_name} to Deviation Pool during the period ({start_date.strftime("%d-%m-%Y")} to {end_date.strftime("%d-%m-%Y")})' )
        
        #  (Page 2) ****************************
        pdf.add_page(orientation='L') 
        pdf.set_font("Times", "BI" , 10)
        pdf.multi_cell(0, 9, f'Annexure I : Details of payments made by {entity_fc_name} to Deviation Pool / received by {entity_fc_name} from Deviation Pool during the period ({start_date.strftime("%d-%m-%Y")} to {end_date.strftime("%d-%m-%Y")}) / ({start_date.strftime("%d-%m-%Y")} to {end_date.strftime("%d-%m-%Y")}) ' ,align = 'C')
        pdf.ln(5)
        # Get full usable width of the page
        page_width = pdf.w - 2 * pdf.l_margin
        # Define column widths to fill full width
        col1_width = page_width * 0.8  # 70% for label
        col2_width = page_width * 0.2  # 30% for value

        # Create the row
        pdf.set_font("Times", "B" , 10)
        pdf.cell(col1_width, 9, f'Opening balance as on {start_date.strftime("%d-%m-%Y")} (A)',align = 'C' , border=1)
        pdf.cell(col2_width, 9,f'{opening_balance}', border=1,align = 'C' , ln=1)
        
        # ************************* Payable  Table ****************
       
        pdf = Tableheader(pdf , "Payable To Pool ")
        pdf.set_font("Times","B" , 10)
        # Define your column headers and column widths
        headers = ['Week No' ,'Final Charges(*Rs)' ,'Letter Date' ,'Paid Date' ,'Paid Amount(*Rs)' ,'Outstanding(*Rs)']
        num_cols = len(headers)
        # Calculate full usable width
        usable_width = pdf.w - 2 * pdf.l_margin
        # Divide width equally across all columns (or customize as needed)
        col_widths = [usable_width / num_cols] * num_cols
        # Print header row
        #for header, width in zip(headers, col_widths):
        #    pdf.cell(width, 10, header, border=1, align='C')
        #pdf.ln()
        
        #pdf.set_font("Courier","" , 12)
        # Add table rows
        #for row in payable_data:
        #    if pdf.get_y() + line_height > max_height:
        #        # Add signature at bottom before page break
        #        pdf = addSignBottom(pdf, authorized_img_path, entity_fc_name, "Praharsha Korangi (Dy. Manager)")
        #        # page reached the end so add new page and add payable headers also 
        #        pdf.add_page(orientation='L')
        #        pdf = Tableheader(pdf , "Payable To Pool")
        #        pdf.set_font("Times","B" , 10)
        #        for header, width in zip(headers, col_widths):
        #            pdf.cell(width, 10, header, border=1, align='C')
        #        pdf.set_font("Times","" , 12)

        print_table_with_wrapped_first_col(pdf, headers, payable_data, col_widths, max_height, line_height,authorized_img_path,entity_fc_name)

        #pdf = addSignBottom(pdf , authorized_img_path , entity_fc_name,"Praharsha Korangi (Dy. Manager)")
        # **************************** (Page 3)Receivable  Table ****************
        # break the page
        pdf.add_page(orientation='L') 
        pdf = Tableheader(pdf , "Receivable From Pool ")

        pdf.set_font("Times","B" , 12)
        # Define your column headers and column widths
        headers1= ['Week No' ,'Letter Date' ,'Final Charges(*Rs)' ,'Disbursed Amount(*Rs)','Disbursed Date','Outstanding (Rs)']
        num_cols = len(headers1)
        # Divide width equally across all columns (or customize as needed)
        col_widths1 = [usable_width / num_cols] * num_cols

        # Print header row
        #for header, width in zip(headers1, col_widths1):
        #    pdf.cell(width, 10, header, border=1, align='C')
        #pdf.ln()
        
        #pdf.set_font("Courier","" , 12)
        # Add table rows
        #for row in receivable_data:
        #    if pdf.get_y() + line_height > max_height:
        #        # Add signature at bottom before page break
        #        pdf = addSignBottom(pdf, authorized_img_path, entity_fc_name, "Praharsha Korangi (Dy. Manager)")
        #        pdf.add_page(orientation='L')
        #        pdf = Tableheader(pdf , "Receivable From Pool ")
        #        pdf.set_font("Times","B" , 10)
        #        for header, width in zip(headers1, col_widths1):
        #            pdf.cell(width, 10 , header, border=1, align='C')
        #        pdf.set_font("Courier","" , 12)

        #    for datum, width in zip(row, col_widths1):
        #        pdf.cell(width, line_height, str(datum), border=1, align='C')
        #    pdf.ln()
        print_table_with_wrapped_first_col(pdf, headers1, receivable_data, col_widths, max_height, line_height,authorized_img_path,entity_fc_name)
        pdf.ln()
        # Create the row
        pdf.set_font("Times", "B" , 12)
        pdf.cell(col1_width, 11, f'Closing balance in Rs. as on {end_date.strftime("%d-%m-%Y")} i.e., D = A+(B-C)',align = 'C' , border=1)
        pdf.cell(col2_width, 11, f'{closing_balance}', border=1,align = 'C' , ln=1)
        #pdf = addSignBottom(pdf , authorized_img_path , entity_fc_name,"Praharsha Korangi (Dy. Manager)")
        # ************************** Last Page ***********************
        # Finally add a remarks 
        pdf.add_page(orientation='L') 
        pdf.set_font("Courier","" , 12)
        pdf.cell( 0, 10 , 'Any Remarks :' ,ln=1)
        # Get margins and width
        left_margin = pdf.l_margin
        right_margin = pdf.w - pdf.r_margin
        y = pdf.get_y()  # current vertical position

        # Draw the line
        pdf.line(left_margin, y, right_margin, y)
        # Move to next line (optional)
        pdf.ln(8)
        y = pdf.get_y()  # current vertical position
        pdf.line(left_margin, y, right_margin, y)

        pdf = addSignBottom(pdf , authorized_img_path , entity_fc_name,"Praharsha Korangi (Dy. Manager)")
        # Output PDF
        pdf.output(pdf_path)
        return pdf_path
    
    except Exception as e:
        print("Error:", e)


def generateReconPDF(request):
    try:
        in_data = json.loads(request.body)
        fin_code = in_data['fincode']
        fin_year = in_data['formdata']['fin_year']
        quarter = in_data['formdata']['quarter']
        acc_type = in_data['formdata']['acc_type']

        if not checkBillsNotified(acc_type , fin_year , quarter):
            return HttpResponse( 'Bills not notified ', status = 404)
        
        start_date,end_date = get_quarter_dates(fin_year,quarter)
        # check already submitted or not
        recon_qry = ReconUploadStatus.objects.filter(
                    Acc_type = acc_type ,
                    Fin_year = fin_year ,
                    Quarter = quarter ,
                    Fin_code = fin_code ,
                    Upload_status = 'A'
                )
        if recon_qry.count() > 0:
            pdf_path = list(recon_qry.values_list('File_path' , flat=True))
            return FileResponse(open(pdf_path[0],'rb'),content_type='application/pdf')
            


        all_payable_lst , all_receivable_lst = reco_for_user(fin_code,start_date,end_date,acc_type)

        o_b = ReconLastQuarterBalance.objects.filter(Fin_code = fin_code, Acc_type =acc_type ,as_on_date = start_date-timedelta(days=1)).values()
        df_o_b = pd.DataFrame.from_records(o_b)

        # convert Payable List to dataframe and do some modifications
        payable_df = pd.DataFrame(all_payable_lst)

        if not payable_df.empty:
            for i in range(0, payable_df.shape[0]):
                try :
                    payable_df.at[i, 0] = "Wk " + str(payable_df.at[i, 0]) + "( " + payable_df.at[i, 1].strftime('%d-%m-%Y') + " to " + payable_df.at[i, 2].strftime('%d-%m-%Y') + " )"
                except Exception as e:
                    payable_df.at[i, 0] = str(payable_df.at[i, 0]) + " dated "  + payable_df.at[i, 4].strftime('%d-%m-%Y')  

            payable_df = payable_df[[0, 3, 4, 5, 6, 7]]
            payable_df.columns = [0, 1, 2, 3, 4, 5]

            payable_df[payable_df.columns[2]] = pd.to_datetime(payable_df[payable_df.columns[2]])
            payable_df = payable_df.sort_values(by=payable_df.columns[2])

            payable_df[4] = payable_df[4].replace('', 0)  # fill empty string in paid amount with 0
            payable_df[5] = payable_df[1] - payable_df[4]
            
            if len(payable_df):
                total1 = payable_df[5].sum()

                
                payable_df.at[len(payable_df), 0] = 'TOTAL (B)'
                payable_df.at[len(payable_df) - 1, 1] = payable_df[1].sum()
                payable_df.at[len(payable_df) - 1, 4] = payable_df[4].sum()
                payable_df.at[len(payable_df) - 1, 5] = payable_df[5].sum()

                payable_df.fillna('', inplace=True)

                
                payable_df[2] = pd.to_datetime(payable_df[2]).dt.strftime('%d-%m-%Y')
                payable_df[3] = pd.to_datetime(payable_df[3]).dt.strftime('%d-%m-%Y')
                payable_df[1] = payable_df[1].apply(lambda x: format_indian_currency_withoutsymbol(x))  # final charges
                payable_df[4] = payable_df[4].apply(lambda x: format_indian_currency_withoutsymbol(x))  # paid amount
                payable_df[5] = payable_df[5].apply(lambda x: format_indian_currency_withoutsymbol(x))  # outstanding
                payable_df.fillna('--', inplace=True)
                payable_df.at[len(payable_df) - 1, 2] = ' '
                payable_df.at[len(payable_df) - 1, 3] = ' '

        else:
            payable_df = pd.DataFrame(columns=[0, 1, 2, 3, 4, 5])
            total1 = 0

        # convert Receivable List to dataframe
        receivable_df = pd.DataFrame(all_receivable_lst)

        for i in range(0,receivable_df.shape[0]):
            try :
                receivable_df.at[i,0] = "Wk " + str(receivable_df.at[i,0])+"( "+receivable_df.at[i,1].strftime('%d-%m-%Y')+" to "+receivable_df.at[i,2].strftime('%d-%m-%Y')+" )"
            except Exception as e:
                receivable_df.at[i,0] = str(receivable_df.at[i,0])+" dated "+receivable_df.at[i,3].strftime('%d-%m-%Y')
        receivable_df = receivable_df[[0,3,4,5,6,7]]
        receivable_df.columns = [0,1,2,3,4,5]

        receivable_df = receivable_df.sort_values(by=payable_df.columns[1])
        
        if len(receivable_df) :
            total2 = receivable_df[5].sum()
            receivable_df.at[len(receivable_df),0] = 'Total(C)'
            receivable_df.loc[len(receivable_df)-1,2] = receivable_df[2].sum()
            receivable_df.loc[len(receivable_df)-1,3] = receivable_df[3].sum()
            receivable_df.loc[len(receivable_df)-1,5] = receivable_df[5].sum()
        
            receivable_df[1] = pd.to_datetime(receivable_df[1]).dt.strftime('%d-%m-%Y')
            receivable_df[4] = pd.to_datetime(receivable_df[4]).dt.strftime('%d-%m-%Y')
            receivable_df[2]=receivable_df[2].apply(lambda x:format_indian_currency_withoutsymbol(x))
            receivable_df[3]=receivable_df[3].apply(lambda x:format_indian_currency_withoutsymbol(x))
            receivable_df[5]=receivable_df[5].apply(lambda x:format_indian_currency_withoutsymbol(x))
            receivable_df.fillna('--' , inplace=True)
            receivable_df.loc[len(receivable_df)-1,1] = ' '
            receivable_df.loc[len(receivable_df)-1,4] = ' '
        else:
            receivable_df = pd.DataFrame(columns=[0, 1, 2, 3, 4, 5])
            total2 = 0
        opening_balance = df_o_b['Amount'].apply(lambda x:format_indian_currency_withoutsymbol(x))

        closing_balance = (df_o_b['Amount'] + (total1 -total2)).apply(lambda x:format_indian_currency_withoutsymbol(x))

        pdf_path = ReconPDF(start_date,end_date,in_data , payable_df.values.tolist() , receivable_df.values.tolist(),opening_balance[0],closing_balance[0])
        
        return FileResponse(open(pdf_path,'rb'),content_type='application/pdf')
        
    except Exception as e:
        return HttpResponse(str(e) , status = 404)


def uploadReconPDF(request):
    try:
        formdata = json.loads(request.POST['formdata'])
        fincode = request.POST['fincode']
        # check if already entry made 
        if ReconUploadStatus.objects.filter(
            Acc_type = formdata['acc_type'] ,
            Fin_year = formdata['fin_year'] ,
            Quarter = formdata['quarter'] ,
            Fin_code = fincode 
        ).exclude(Upload_status='R').count() > 0 :
            return JsonResponse({'status' : False , 'error' : f"Already Submitted for {formdata['quarter']}"} , safe=False)
        
        folder_path = f'Reco\\UploadedFiles\\'
        os.makedirs(folder_path, exist_ok=True)
        file_name = formdata['acc_type'] + '&' +formdata['fin_year']+'&'+ formdata['quarter'] +'&'+fincode +'.pdf'
        pdf_path = os.path.join(folder_path, file_name)
        up_file = request.FILES['file']
        with open(pdf_path, 'wb+') as destination:
            for chunk in up_file.chunks():
                destination.write(chunk)
        # now store the details in table
        ReconUploadStatus(
            Acc_type = formdata['acc_type'] ,
            Fin_year = formdata['fin_year'] ,
            Quarter = formdata['quarter'] ,
            Fin_code = fincode ,
            Upload_status = 'N' ,
            File_path = pdf_path 
        ).save()

        return JsonResponse({'status' : True} , safe=False)
    except Exception as e:
        return JsonResponse({'status' : False , 'error' : str(e)} , safe=False)

def getUploadedCopies(request):
    try:
        in_data = json.loads(request.body)
        
        signed_df = pd.DataFrame(ReconUploadStatus.objects.filter(Acc_type = in_data['acc_type'] ,Fin_year = in_data['fin_year'] , Quarter = in_data['quarter'] ,Fin_code__in = in_data['usr'] , Upload_status = in_data['status'] ).all().values() , columns=['Acc_type', 'Fin_year' , 'Quarter' ,'Fin_code','Upload_status' ,'Uploaded_time','File_path' ,'Admin_remarks' 'Admin_uploaded_time' ] )
        
        # if signed_df.empty:
        #     return JsonResponse({'status': True ,'data' : [] } , safe=False) 
        
        fc_names_df=pd.DataFrame(Registration.objects.filter(Q(end_date__isnull=True) , Q(fin_code__in = in_data['usr'])).values('fin_code','fees_charges_name'))
        if in_data['status'] == 'A':
            # merge df and
            merge_df = pd.merge(fc_names_df ,signed_df , left_on='fin_code' , right_on = 'Fin_code' , how = 'left')
        else :
            # merge df and
            merge_df = pd.merge(signed_df , fc_names_df , left_on='Fin_code' , right_on = 'fin_code' , how = 'left')
       
        merge_df['Is_upload'] = merge_df['Uploaded_time'].notna()
        merge_df.fillna('',inplace=True)
        merge_df.sort_values(by=['fees_charges_name'] , inplace=True)
        return JsonResponse({'status': True ,'data' : merge_df.to_dict(orient='records') } , safe=False)

    except Exception as e:
      
        return JsonResponse({'status' : False , 'error' : str(e)} , safe=False)
    
def approveRejectSignedCopies(request):
    try:
        in_data = json.loads(request.body)
        selected_row = in_data['selected_row']
        quarter_year = int(selected_row['Fin_year'][0:4])
        # exclude already rejected details
        ReconUploadStatus.objects.filter(
            Acc_type = selected_row['Acc_type'] ,
            Fin_year = selected_row['Fin_year'] ,
            Quarter  = selected_row['Quarter'] ,
            Fin_code = selected_row['Fin_code'] 
        ).exclude(Upload_status = 'R').update(
            Upload_status = in_data['approve_type'] ,
            Admin_remarks = in_data['admin_remarks'] 
        ) 
        # update balance for next quarter
        ReconLastQuarterBalance (
            Acc_type = selected_row['Acc_type'] ,
            Fin_year = selected_row['Fin_year'] ,
            Quarter = selected_row['Quarter'] ,
            as_on_date = get_quarter_end_date(selected_row['Quarter'], quarter_year) ,
            Amount = in_data['opening_bal_nextquarter'] ,
            Fin_code = selected_row['Fin_code'] 
        ).save()
        message = 'Approved Successfully' if in_data['approve_type'] == 'A' else 'Rejected Successfully '
        return JsonResponse({'status': True ,'message' : message } , safe=False)
    except Exception as e:
        return JsonResponse({'status' : False , 'error' : str(e)} , safe=False)
    

def downloadUploadedPDFs(request):
    try:
        file_path = request.body.decode('utf-8') 
        return FileResponse(open(file_path,'rb'),content_type='application/pdf')
    except Exception as e:
        return HttpResponse(str(e) , status = 404)
