
from django.http import HttpResponse , JsonResponse ,FileResponse
from dsm.common import _create_columns,getWeekDates,format_indian_currency,trimFilePath,getFeesChargesName
from dsm.disburse import getLastDisbursementSurplus
from registration.extarctdb_errors import extractdb_errormsg
from .models import *
import json ,pdb ,pandas as pd ,os
from docxtpl import DocxTemplate
from docx2pdf import convert
from poolaccounts.settings import base_dir
from datetime import datetime
from docx2pdf import convert
import pythoncom
from django.db.models import Q
def transformIOMPayabledf(payments_df,all_payables,row):
    try:
        for _,row1 in payments_df.iterrows():
            actual_payable_amt=row1['Final_charges']
            paid_amount=row1['Paid_amount']
            duetopool=actual_payable_amt-paid_amount
            temp_rec=row.to_dict()
            temp_rec['amount_payable']=format_indian_currency(actual_payable_amt)
            temp_rec['due_date']=row1['Due_date'].strftime('%d-%m-%Y') if row1['Due_date'] else None
            temp_rec['paid_date']=row1['Paid_date'].strftime('%d-%m-%Y') if row1['Paid_date'] else None
            temp_rec['paid_amount']=format_indian_currency(row1['Paid_amount'])
            temp_rec['credited_bank']=row1['Bank_type']
            temp_rec['duetopool']=format_indian_currency(duetopool)
            all_payables.append(temp_rec)
    except Exception as e:
        extractdb_errormsg(e)

    return all_payables
def transformIOMReceivabledf(receivables_df,dsm_all_receivables,row):
    try:
        for _,row1 in receivables_df.iterrows():
            actual_receivable_amt=row1['Final_charges']
            disbursed_amount=row1['Disbursed_amount']
            duetopool=actual_receivable_amt-disbursed_amount

            temp_rec=row.to_dict()
            temp_rec['amount_receivable']=format_indian_currency(actual_receivable_amt)
            temp_rec['disbursed_amount']=format_indian_currency(disbursed_amount)
            temp_rec['duetopool']=format_indian_currency(duetopool)
        
            dsm_all_receivables.append(temp_rec)
    except Exception as e:
        extractdb_errormsg(e)

    return dsm_all_receivables

def transformIOMReceivabledfNew(receivables_df,dsm_all_receivables,row):
    try:
        if len(receivables_df) == 1:
            # If there's only one row, take that row and don't skip it
            last_record = receivables_df.iloc[0].to_list()
            already_disbursed_amt = 0
        else:
            # Get the last record
            last_record = receivables_df.iloc[-1].to_list()
            already_disbursed_amt = receivables_df['Disbursed_amount'][:-1].sum()
        
        
        actual_receivable_amt=last_record[1]
        disbursed_amount=last_record[0]
        duetopool=actual_receivable_amt-disbursed_amount-already_disbursed_amt
        
        temp_rec=row.to_dict()
        temp_rec['amount_receivable']=format_indian_currency(actual_receivable_amt)
        temp_rec['disbursed_amount']=format_indian_currency(disbursed_amount)
        temp_rec['duetopool']=format_indian_currency(duetopool)
        temp_rec['already_disbursed']=format_indian_currency(already_disbursed_amt)
        # get bank account details
        bank_qry=list(BankDetails.objects.filter(Q(fin_code_fk__fin_code=row['fin_code']) ,(Q(fin_code_fk__end_date__isnull=True) | Q(fin_code_fk__end_date__gte=datetime.today()) ) ).values('bank_name','bank_account','ifsc_code') )
    
        temp_rec['entity']=getFeesChargesName(row['fin_code'])
        if len(bank_qry) == 1:
            bank_name=bank_qry[0]['bank_name']
            account_no=bank_qry[0]['bank_account']
            ifsc_code=bank_qry[0]['ifsc_code']
        else:
            bank_name=''
            account_no=''
            ifsc_code=''
        
        temp_rec['bank_name']=bank_name
        temp_rec['acc_no']=account_no
        temp_rec['ifsc_code']=ifsc_code

        dsm_all_receivables.append(temp_rec)
    
    except Exception as e:
        extractdb_errormsg(e)
    return dsm_all_receivables

def processAllPayables(model_obj_qry ,iom_date,payrcv,prevwkstatus ,pool_acc,fin_year,week_no):
    #all_payables_df=pd.DataFrame(DisbursedEntities.objects.filter(disstatus_fk__Disbursed_date=iom_date,pool_acctype=pool_acc,payrcv=payrcv,is_prevweeks=prevwkstatus).values('fin_year','week_no','entity','fin_code','parent_table_id'))
    # create blank columns with length of dataframe
    #all_payables_df = _create_columns(all_payables_df, [ 'amount_payable','due_date','paid_date','paid_amount','credited_bank','duetopool'])
    #all_payables=[]
    # replace -- with None
    #all_payables_df=all_payables_df.apply(lambda x:x.replace('--',None))
    all_payables = []
    if pool_acc == 'DSM':
        #--current week----#
        current_week_payables_df=pd.DataFrame(DSMBaseModel.objects.filter(Fin_year=fin_year,Week_no=week_no,PayableorReceivable='Payable',Legacy_dues=False).values('id','Fin_year','Week_no','Entity','Fin_code','Final_charges','Due_date'))
        #l = current_week_payables_df['Fin_code','Final_charges'].unique()
        #   pdb.set_trace()
        current_week_payments_df=pd.DataFrame(Payments.objects.filter(paystatus_fk__Fin_year=fin_year,paystatus_fk__Week_no=week_no).values('Paid_date','Paid_amount','Bank_type','paystatus_fk_id','paystatus_fk__Fin_year','paystatus_fk__Week_no','paystatus_fk__Entity'))
        #pdb.set_trace()
        current_week_payments_df.rename(columns={'paystatus_fk_id':'id','paystatus_fk__Fin_year':'Fin_year','paystatus_fk__Week_no':'Week_no','paystatus_fk__Entity':'Entity'},inplace=True)
        
        all_week_payables_df = pd.DataFrame(DSMBaseModel.objects.filter(PayableorReceivable='Payable',Legacy_dues=False).values('Fin_year','Week_no','Entity','Fin_code','Final_charges','Due_date'))
        all_week_payments_df=pd.DataFrame(Payments.objects.values('Paid_date','Paid_amount','Bank_type','paystatus_fk__Fin_year','paystatus_fk__Week_no','paystatus_fk__Entity'))
        all_week_payments_df.rename(columns={'paystatus_fk__Fin_year':'Fin_year','paystatus_fk__Week_no':'Week_no','paystatus_fk__Entity':'Entity'},inplace=True)
        merged_all_weeks = pd.merge(all_week_payables_df,all_week_payments_df,on=['Fin_year','Week_no','Entity'],how='left')
        dis_status = pd.DataFrame(list(DisbursementStatus.objects.filter(final_disburse=True,legacy_status =False).order_by('-Disbursed_date').values('Disbursed_date')))
        start_date = dis_status.at[1,"Disbursed_date"]
        end_date = dis_status.at[0,"Disbursed_date"]
        merged_all_weeks_filtered = merged_all_weeks[(merged_all_weeks['Paid_date'] >= start_date) & (merged_all_weeks['Paid_date'] <= end_date)]
        temp_prev_weeks_payable = merged_all_weeks_filtered[(merged_all_weeks_filtered["Week_no"]<week_no) & (merged_all_weeks_filtered["Final_charges"] > 0)]


        merged_df=pd.merge(current_week_payables_df,current_week_payments_df,on=['id','Fin_year','Week_no','Entity'],how='left')
        merged_df=merged_df.fillna(0)
        duplicate= merged_df[merged_df.duplicated(subset=['id'],keep = False)]['id'].unique().tolist()

        for i in duplicate :
            filtered_indices = merged_df[merged_df['id'] == i].index
            merged_df.loc[filtered_indices[1:len(filtered_indices)],"Final_charges"] = 0

        # merged_df.rename(columns={'Fin_year':'fin_year','Week_no':'week_no','Fin_code':'fin_code','Entity':'entity','Due_date':'due_date','Paid_date':'paid_date','Paid_amount':'paid_amount','Bank_type':'credited_bank'},inplace=True)
        merged_df.rename(columns={'Fin_year':'fin_year','Week_no':'week_no','Fin_code':'fin_code','Entity':'entity'},inplace=True)
        prev_weeks_payable=temp_prev_weeks_payable.copy()
        prev_weeks_payable.rename(columns={'Fin_year':'fin_year','Week_no':'week_no','Fin_code':'fin_code','Entity':'entity'},inplace=True)
        
        for _,row in merged_df.iterrows():
            actual_payable_amt=row['Final_charges']
            paid_amount=row['Paid_amount']
            duetopool=actual_payable_amt-paid_amount
            temp_rec=row.to_dict()
            temp_rec['amount_payable']=format_indian_currency(actual_payable_amt)
            temp_rec['due_date']=row['Due_date'].strftime('%d-%m-%Y') if row['Due_date'] else '--'
            temp_rec['paid_date']=row['Paid_date'].strftime('%d-%m-%Y') if row['Paid_date'] else "--"
            temp_rec['paid_amount']=format_indian_currency(row['Paid_amount'])
            temp_rec['credited_bank']=row['Bank_type']
            temp_rec['duetopool']=format_indian_currency(duetopool)
            all_payables.append(temp_rec)
        all_prev_payables = []
        
        for _,row in prev_weeks_payable.iterrows():
            actual_payable_amt=row['Final_charges']
            paid_amount=row['Paid_amount']
            duetopool=actual_payable_amt-paid_amount
            temp_rec=row.to_dict()
            temp_rec['amount_payable']=format_indian_currency(actual_payable_amt)
            temp_rec['due_date']=row['Due_date'].strftime('%d-%m-%Y') if row['Due_date'] else '--'
            temp_rec['paid_date']=row['Paid_date'].strftime('%d-%m-%Y') if row['Paid_date'] else "--"
            temp_rec['paid_amount']=format_indian_currency(row['Paid_amount'])
            temp_rec['credited_bank']=row['Bank_type']
            temp_rec['duetopool']=format_indian_currency(duetopool)
            all_prev_payables.append(temp_rec)
        

        return all_payables,all_prev_payables

    elif pool_acc == 'NET_AS':
        current_week_payables_df=pd.DataFrame(NetASBaseModel.objects.filter(Fin_year=fin_year,Week_no=week_no,PayableorReceivable='Payable',Legacy_dues=False).values('Fin_year','Week_no','Entity','Fin_code','Final_charges','Due_date') , columns = ['Fin_year','Week_no','Entity','Fin_code','Final_charges','Due_date'] )
        current_week_payments_df=pd.DataFrame(NetASPayments.objects.filter(paystatus_fk__Fin_year=fin_year,paystatus_fk__Week_no=week_no).values('Paid_date','Paid_amount','Bank_type','paystatus_fk__Fin_year','paystatus_fk__Week_no','paystatus_fk__Entity'), columns=['Paid_date','Paid_amount','Bank_type','paystatus_fk__Fin_year','paystatus_fk__Week_no','paystatus_fk__Entity'])

        current_week_payments_df.rename(columns={'paystatus_fk__Fin_year':'Fin_year','paystatus_fk__Week_no':'Week_no','paystatus_fk__Entity':'Entity'},inplace=True)
        

        all_week_payables_df = pd.DataFrame(NetASBaseModel.objects.filter(PayableorReceivable='Payable',Legacy_dues=False).values('Fin_year','Week_no','Entity','Fin_code','Final_charges','Due_date') ,columns=['Fin_year','Week_no','Entity','Fin_code','Final_charges','Due_date'])
        all_week_payments_df=pd.DataFrame(NetASPayments.objects.values('Paid_date','Paid_amount','Bank_type','paystatus_fk__Fin_year','paystatus_fk__Week_no','paystatus_fk__Entity') ,columns=['Paid_date','Paid_amount','Bank_type','paystatus_fk__Fin_year','paystatus_fk__Week_no','paystatus_fk__Entity'])
        all_week_payments_df.rename(columns={'paystatus_fk__Fin_year':'Fin_year','paystatus_fk__Week_no':'Week_no','paystatus_fk__Entity':'Entity'},inplace=True)
        merged_all_weeks = pd.merge(all_week_payables_df,all_week_payments_df,on=['Fin_year','Week_no','Entity'],how='left')
        dis_status = pd.DataFrame(list(DisbursementStatus.objects.filter(final_disburse=True,legacy_status = False).order_by('-Disbursed_date').values('Disbursed_date')))
        start_date = dis_status.at[1,"Disbursed_date"]
        end_date = dis_status.at[0,"Disbursed_date"]
        merged_all_weeks_filtered = merged_all_weeks[(merged_all_weeks['Paid_date'] >= start_date) & (merged_all_weeks['Paid_date'] <= end_date)]
        temp_prev_weeks_payable = merged_all_weeks_filtered[(merged_all_weeks_filtered["Week_no"]<week_no) & (merged_all_weeks_filtered["Final_charges"] > 0)]


        merged_df=pd.merge(current_week_payables_df,current_week_payments_df,on=['Fin_year','Week_no','Entity'],how='left')
        merged_df=merged_df.fillna(0)
        # merged_df.rename(columns={'Fin_year':'fin_year','Week_no':'week_no','Fin_code':'fin_code','Entity':'entity','Due_date':'due_date','Paid_date':'paid_date','Paid_amount':'paid_amount','Bank_type':'credited_bank'},inplace=True)
        merged_df.rename(columns={'Fin_year':'fin_year','Week_no':'week_no','Fin_code':'fin_code','Entity':'entity'},inplace=True)
        prev_weeks_payable=temp_prev_weeks_payable.copy()
        prev_weeks_payable.rename(columns={'Fin_year':'fin_year','Week_no':'week_no','Fin_code':'fin_code','Entity':'entity'},inplace=True)
        
        
        for _,row in merged_df.iterrows():
            actual_payable_amt=row['Final_charges']
            paid_amount=row['Paid_amount']
            duetopool=actual_payable_amt-paid_amount
            temp_rec=row.to_dict()
            temp_rec['amount_payable']=format_indian_currency(actual_payable_amt)
            temp_rec['due_date']=row['Due_date'].strftime('%d-%m-%Y') if row['Due_date'] else '--'
            temp_rec['paid_date']=row['Paid_date'].strftime('%d-%m-%Y') if row['Paid_date'] else "--"
            temp_rec['paid_amount']=format_indian_currency(row['Paid_amount'])
            temp_rec['credited_bank']=row['Bank_type']
            temp_rec['duetopool']=format_indian_currency(duetopool)
            all_payables.append(temp_rec)
        all_prev_payables = []
        for _,row in prev_weeks_payable.iterrows():
            actual_payable_amt=row['Final_charges']
            paid_amount=row['Paid_amount']
            duetopool=actual_payable_amt-paid_amount
            temp_rec=row.to_dict()
            temp_rec['amount_payable']=format_indian_currency(actual_payable_amt)
            temp_rec['due_date']=row['Due_date'].strftime('%d-%m-%Y') if row['Due_date'] else '--'
            temp_rec['paid_date']=row['Paid_date'].strftime('%d-%m-%Y') if row['Paid_date'] else "--"
            temp_rec['paid_amount']=format_indian_currency(row['Paid_amount'])
            temp_rec['credited_bank']=row['Bank_type']
            temp_rec['duetopool']=format_indian_currency(duetopool)
            all_prev_payables.append(temp_rec)

        return all_payables,all_prev_payables
        #for _,row in all_payables_df.iterrows():
        #    payments_df=pd.DataFrame(model_obj_qry.filter(id=row['parent_table_id']).values('netaspayments__Paid_date',#'netaspayments__Paid_amount','netaspayments__Bank_type','Due_date','Final_charges','Entity'))
        #    payments_df.rename(columns={'netaspayments__Paid_date':'Paid_date' , 'netaspayments__Paid_amount':'Paid_amount',#'netaspayments__Bank_type':'Bank_type'} ,inplace=True)
        #    all_payables=transformIOMPayabledf(payments_df,all_payables,row)

    elif pool_acc == 'REAC':
        current_week_payables_df=pd.DataFrame(REACBaseModel.objects.filter(Fin_year=fin_year,Week_no=week_no,PayableorReceivable='Payable',Legacy_dues=False).values('Fin_year','Week_no','Entity','Fin_code','Final_charges','Due_date'))

        current_week_payments_df=pd.DataFrame(REACPayments.objects.filter(paystatus_fk__Fin_year=fin_year,paystatus_fk__Week_no=week_no).values('Paid_date','Paid_amount','Bank_type','paystatus_fk__Fin_year','paystatus_fk__Week_no','paystatus_fk__Entity'))

        current_week_payments_df.rename(columns={'paystatus_fk__Fin_year':'Fin_year','paystatus_fk__Week_no':'Week_no','paystatus_fk__Entity':'Entity'},inplace=True)
        

        all_week_payables_df = pd.DataFrame(REACBaseModel.objects.filter(PayableorReceivable='Payable',Legacy_dues=False).values('Fin_year','Week_no','Entity','Fin_code','Final_charges','Due_date'))
        all_week_payments_df=pd.DataFrame(REACPayments.objects.values('Paid_date','Paid_amount','Bank_type','paystatus_fk__Fin_year','paystatus_fk__Week_no','paystatus_fk__Entity'))
        all_week_payments_df.rename(columns={'paystatus_fk__Fin_year':'Fin_year','paystatus_fk__Week_no':'Week_no','paystatus_fk__Entity':'Entity'},inplace=True)
        merged_all_weeks = pd.merge(all_week_payables_df,all_week_payments_df,on=['Fin_year','Week_no','Entity'],how='left')
        dis_status = pd.DataFrame(list(DisbursementStatus.objects.filter(final_disburse=True,legacy_status = False).order_by('-Disbursed_date').values('Disbursed_date')))
        start_date = dis_status.at[1,"Disbursed_date"]
        end_date = dis_status.at[0,"Disbursed_date"]
        merged_all_weeks_filtered = merged_all_weeks[(merged_all_weeks['Paid_date'] >= start_date) & (merged_all_weeks['Paid_date'] <= end_date)]
        temp_prev_weeks_payable = merged_all_weeks_filtered[(merged_all_weeks_filtered["Week_no"]<week_no) & (merged_all_weeks_filtered["Final_charges"] > 0)]

        merged_df=pd.merge(current_week_payables_df,current_week_payments_df,on=['Fin_year','Week_no','Entity'],how='left')
        merged_df=merged_df.fillna(0)
        # merged_df.rename(columns={'Fin_year':'fin_year','Week_no':'week_no','Fin_code':'fin_code','Entity':'entity','Due_date':'due_date','Paid_date':'paid_date','Paid_amount':'paid_amount','Bank_type':'credited_bank'},inplace=True)
        merged_df.rename(columns={'Fin_year':'fin_year','Week_no':'week_no','Fin_code':'fin_code','Entity':'entity'},inplace=True)
        
        prev_weeks_payable=temp_prev_weeks_payable.copy()
        prev_weeks_payable.rename(columns={'Fin_year':'fin_year','Week_no':'week_no','Fin_code':'fin_code','Entity':'entity'},inplace=True)
        
        for _,row in merged_df.iterrows():
            actual_payable_amt=row['Final_charges']
            paid_amount=row['Paid_amount']
            duetopool=actual_payable_amt-paid_amount
            temp_rec=row.to_dict()
            temp_rec['amount_payable']=format_indian_currency(actual_payable_amt)
            temp_rec['due_date']=row['Due_date'].strftime('%d-%m-%Y') if row['Due_date'] else '--'
            temp_rec['paid_date']=row['Paid_date'].strftime('%d-%m-%Y') if row['Paid_date'] else "--"
            temp_rec['paid_amount']=format_indian_currency(row['Paid_amount'])
            temp_rec['credited_bank']=row['Bank_type']
            temp_rec['duetopool']=format_indian_currency(duetopool)
            all_payables.append(temp_rec)

        all_prev_payables = []
        
        for _,row in prev_weeks_payable.iterrows():
            actual_payable_amt=row['Final_charges']
            paid_amount=row['Paid_amount']
            duetopool=actual_payable_amt-paid_amount
            temp_rec=row.to_dict()
            temp_rec['amount_payable']=format_indian_currency(actual_payable_amt)
            temp_rec['due_date']=row['Due_date'].strftime('%d-%m-%Y') if row['Due_date'] else '--'
            temp_rec['paid_date']=row['Paid_date'].strftime('%d-%m-%Y') if row['Paid_date'] else "--"
            temp_rec['paid_amount']=format_indian_currency(row['Paid_amount'])
            temp_rec['credited_bank']=row['Bank_type']
            temp_rec['duetopool']=format_indian_currency(duetopool)
            all_prev_payables.append(temp_rec)
        
        return all_payables,all_prev_payables
    elif pool_acc == 'CONG':
        current_week_payables_df=pd.DataFrame(CONGBaseModel.objects.filter(Fin_year=fin_year,Week_no=week_no,PayableorReceivable='Payable',Legacy_dues=False).values('Fin_year','Week_no','Entity','Fin_code','Final_charges','Due_date'))

        current_week_payments_df=pd.DataFrame(CONGPayments.objects.filter(paystatus_fk__Fin_year=fin_year,paystatus_fk__Week_no=week_no).values('Paid_date','Paid_amount','Bank_type','paystatus_fk__Fin_year','paystatus_fk__Week_no','paystatus_fk__Entity'))

        current_week_payments_df.rename(columns={'paystatus_fk__Fin_year':'Fin_year','paystatus_fk__Week_no':'Week_no','paystatus_fk__Entity':'Entity'},inplace=True)
        

        all_week_payables_df = pd.DataFrame(CONGBaseModel.objects.filter(PayableorReceivable='Payable',Legacy_dues=False).values('Fin_year','Week_no','Entity','Fin_code','Final_charges','Due_date'))
        all_week_payments_df=pd.DataFrame(CONGPayments.objects.values('Paid_date','Paid_amount','Bank_type','paystatus_fk__Fin_year','paystatus_fk__Week_no','paystatus_fk__Entity'))
        all_week_payments_df.rename(columns={'paystatus_fk__Fin_year':'Fin_year','paystatus_fk__Week_no':'Week_no','paystatus_fk__Entity':'Entity'},inplace=True)
        merged_all_weeks = pd.merge(all_week_payables_df,all_week_payments_df,on=['Fin_year','Week_no','Entity'],how='left')
        dis_status = pd.DataFrame(list(DisbursementStatus.objects.filter(final_disburse=True,legacy_status = False).order_by('-Disbursed_date').values('Disbursed_date')))
        start_date = dis_status.at[1,"Disbursed_date"]
        end_date = dis_status.at[0,"Disbursed_date"]
        merged_all_weeks_filtered = merged_all_weeks[(merged_all_weeks['Paid_date'] >= start_date) & (merged_all_weeks['Paid_date'] <= end_date)]
        temp_prev_weeks_payable = merged_all_weeks_filtered[(merged_all_weeks_filtered["Week_no"]<week_no) & (merged_all_weeks_filtered["Final_charges"] > 0)]

        merged_df=pd.merge(current_week_payables_df,current_week_payments_df,on=['Fin_year','Week_no','Entity'],how='left')
        merged_df=merged_df.fillna(0)
        # merged_df.rename(columns={'Fin_year':'fin_year','Week_no':'week_no','Fin_code':'fin_code','Entity':'entity','Due_date':'due_date','Paid_date':'paid_date','Paid_amount':'paid_amount','Bank_type':'credited_bank'},inplace=True)
        merged_df.rename(columns={'Fin_year':'fin_year','Week_no':'week_no','Fin_code':'fin_code','Entity':'entity'},inplace=True)
        
        prev_weeks_payable=temp_prev_weeks_payable.copy()
        prev_weeks_payable.rename(columns={'Fin_year':'fin_year','Week_no':'week_no','Fin_code':'fin_code','Entity':'entity'},inplace=True)
        
        for _,row in merged_df.iterrows():
            actual_payable_amt=row['Final_charges']
            paid_amount=row['Paid_amount']
            duetopool=actual_payable_amt-paid_amount
            temp_rec=row.to_dict()
            temp_rec['amount_payable']=format_indian_currency(actual_payable_amt)
            temp_rec['due_date']=row['Due_date'].strftime('%d-%m-%Y') if row['Due_date'] else '--'
            temp_rec['paid_date']=row['Paid_date'].strftime('%d-%m-%Y') if row['Paid_date'] else "--"
            temp_rec['paid_amount']=format_indian_currency(row['Paid_amount'])
            temp_rec['credited_bank']=row['Bank_type']
            temp_rec['duetopool']=format_indian_currency(duetopool)
            all_payables.append(temp_rec)

        all_prev_payables = []
        
        for _,row in prev_weeks_payable.iterrows():
            actual_payable_amt=row['Final_charges']
            paid_amount=row['Paid_amount']
            duetopool=actual_payable_amt-paid_amount
            temp_rec=row.to_dict()
            temp_rec['amount_payable']=format_indian_currency(actual_payable_amt)
            temp_rec['due_date']=row['Due_date'].strftime('%d-%m-%Y') if row['Due_date'] else '--'
            temp_rec['paid_date']=row['Paid_date'].strftime('%d-%m-%Y') if row['Paid_date'] else "--"
            temp_rec['paid_amount']=format_indian_currency(row['Paid_amount'])
            temp_rec['credited_bank']=row['Bank_type']
            temp_rec['duetopool']=format_indian_currency(duetopool)
            all_prev_payables.append(temp_rec)
        
        return all_payables,all_prev_payables
    elif pool_acc == 'Legacy':
        current_week_payables_df=pd.DataFrame(LegacyBaseModel.objects.filter(PayableorReceivable='Payable',Legacy_dues=True,Is_interregional = False).values('Fin_year','Week_no','Entity','Fin_code','Final_charges','Due_date'))

        current_week_payments_df=pd.DataFrame(LegacyPayments.objects.values('Paid_date','Paid_amount','Bank_type','paystatus_fk__Fin_year','paystatus_fk__Week_no','paystatus_fk__Entity'))

        current_week_payments_df.rename(columns={'paystatus_fk__Fin_year':'Fin_year','paystatus_fk__Week_no':'Week_no','paystatus_fk__Entity':'Entity'},inplace=True)
        

        all_week_payables_df = pd.DataFrame(LegacyBaseModel.objects.filter(PayableorReceivable='Payable',Legacy_dues=True,Is_interregional = True).values('Fin_year','Week_no','Entity','Fin_code','Final_charges','Remarks'))
        all_week_payments_df=pd.DataFrame(LegacyPayments.objects.values('Paid_date','Paid_amount','Bank_type','paystatus_fk__Fin_year','paystatus_fk__Week_no','paystatus_fk__Entity'))
        all_week_payments_df.rename(columns={'paystatus_fk__Fin_year':'Fin_year','paystatus_fk__Week_no':'Week_no','paystatus_fk__Entity':'Entity'},inplace=True)
        merged_all_weeks = pd.merge(all_week_payables_df,all_week_payments_df,on=['Fin_year','Week_no','Entity'],how='left')
        dis_status = pd.DataFrame(list(DisbursementStatus.objects.filter(final_disburse=True,legacy_status = True).order_by('-Disbursed_date').values('Disbursed_date')))
        
        if len(dis_status) >1 :
            start_date = dis_status.at[1,"Disbursed_date"]
            end_date = dis_status.at[0,"Disbursed_date"]
            merged_all_weeks_filtered_ir = merged_all_weeks[(merged_all_weeks['Paid_date'] >= start_date) & (merged_all_weeks['Paid_date'] <= end_date)]

            merged_df=pd.merge(current_week_payables_df,current_week_payments_df,on=['Fin_year','Week_no','Entity'],how='left')
            merged_all_weeks_filtered=merged_df[(merged_df['Paid_date'] >= start_date) & (merged_df['Paid_date'] <= end_date)]
        else :
            end_date = dis_status.at[0,"Disbursed_date"]
            merged_all_weeks_filtered_ir = merged_all_weeks[(merged_all_weeks['Paid_date'] <= end_date)]

            merged_df=pd.merge(current_week_payables_df,current_week_payments_df,on=['Fin_year','Week_no','Entity'],how='left')
            merged_all_weeks_filtered=merged_df[(merged_df['Paid_date'] <= end_date)]
        

        # merged_df.rename(columns={'Fin_year':'fin_year','Week_no':'week_no','Fin_code':'fin_code','Entity':'entity','Due_date':'due_date','Paid_date':'paid_date','Paid_amount':'paid_amount','Bank_type':'credited_bank'},inplace=True)
        merged_all_weeks_filtered.rename(columns={'Fin_year':'fin_year','Week_no':'week_no','Fin_code':'fin_code','Entity':'entity'},inplace=True)
        
        prev_weeks_payable=merged_all_weeks_filtered_ir.copy()
        prev_weeks_payable.rename(columns={'Fin_year':'fin_year','Week_no':'week_no','Fin_code':'fin_code','Entity':'entity'},inplace=True)
        
        for _,row in merged_all_weeks_filtered.iterrows():
            actual_payable_amt=row['Final_charges']
            paid_amount=row['Paid_amount']
            duetopool=actual_payable_amt-paid_amount
            temp_rec=row.to_dict()
            temp_rec['amount_payable']=format_indian_currency(actual_payable_amt)
            temp_rec['due_date']=row['Due_date'].strftime('%d-%m-%Y') if row['Due_date'] else '--'
            temp_rec['paid_date']=row['Paid_date'].strftime('%d-%m-%Y') if row['Paid_date'] else "--"
            temp_rec['paid_amount']=format_indian_currency(row['Paid_amount'])
            temp_rec['credited_bank']=row['Bank_type']
            temp_rec['duetopool']=format_indian_currency(duetopool)
            all_payables.append(temp_rec)

        all_prev_payables = []
        
        for _,row in prev_weeks_payable.iterrows():
            actual_payable_amt=row['Final_charges']
            paid_amount=row['Paid_amount']
            duetopool=actual_payable_amt-paid_amount
            temp_rec=row.to_dict()
            temp_rec['amount_payable']=format_indian_currency(actual_payable_amt)
            temp_rec['due_date']=row['Remarks'] if row['Remarks'] else '--'
            temp_rec['paid_date']=row['Paid_date'].strftime('%d-%m-%Y') if row['Paid_date'] else "--"
            temp_rec['paid_amount']=format_indian_currency(row['Paid_amount'])
            temp_rec['credited_bank']=row['Bank_type']
            temp_rec['duetopool']=format_indian_currency(duetopool)
            all_prev_payables.append(temp_rec)
        
        return all_payables,all_prev_payables
    else:
        pass

    return all_payables

def processAllReceivables(poolacc_obj_qry ,iom_date,prevwkstatus,pool_acc,fin_year,week_no):
    #dsm_obj_qry= DSM Payables
    receivables_df=pd.DataFrame(DisbursedEntities.objects.filter(disstatus_fk__Disbursed_date=iom_date,pool_acctype=pool_acc,payrcv='R',is_prevweeks=prevwkstatus).values('fin_year','week_no','entity','fin_code','parent_table_id'),columns=['fin_year','week_no','entity','fin_code','parent_table_id'])
   
    receivables_df = receivables_df[receivables_df["week_no"] < week_no]
    # create blank columns with length of dataframe
    receivables_df = _create_columns(receivables_df, ['duetopool'])
    all_receivables=[]
    # replace -- with None
    receivables_df=receivables_df.apply(lambda x:x.replace('--',None))
    if pool_acc == 'DSM':
        #---current week disbursement-----#
        acc_basemodel_mdl=DSMBaseModel
        acc_receivables_mdl=DSMReceivables

    elif pool_acc == 'NET_AS':
        acc_basemodel_mdl=NetASBaseModel
        acc_receivables_mdl=NetASReceivables
    elif pool_acc == 'REAC':
        #---current week disbursement-----#
        acc_basemodel_mdl=REACBaseModel
        acc_receivables_mdl=REACReceivables
    
    elif pool_acc == 'CONG':
        #---current week disbursement-----#
        acc_basemodel_mdl=CONGBaseModel
        acc_receivables_mdl=CONGReceivables
        
    elif pool_acc == "Legacy" :
        dsm_receivables_df=pd.DataFrame(DisbursedEntities.objects.filter(disstatus_fk__Disbursed_date=iom_date,pool_acctype="DSM",payrcv='R',is_prevweeks=prevwkstatus).values('fin_year','week_no','entity','fin_code','parent_table_id'),columns=['fin_year','week_no','entity','fin_code','parent_table_id'])
        for _,row in dsm_receivables_df.iterrows():
            receivables_df=pd.DataFrame(DSMBaseModel.objects.all().filter(id=row['parent_table_id']).values('dsmreceivables__Disbursed_amount','Final_charges','Entity'))
            receivables_df.rename(columns={"dsmreceivables__Disbursed_amount":'Disbursed_amount'} ,inplace=True)
            all_receivables=transformIOMReceivabledfNew(receivables_df,all_receivables,row)

        
        netas_receivables_df=pd.DataFrame(DisbursedEntities.objects.filter(disstatus_fk__Disbursed_date=iom_date,pool_acctype="NET_AS",payrcv='R',is_prevweeks=prevwkstatus).values('fin_year','week_no','entity','fin_code','parent_table_id'),columns=['fin_year','week_no','entity','fin_code','parent_table_id'])
        
        current_receivables = []
        for _,row in netas_receivables_df.iterrows():
            receivables_df=pd.DataFrame(NetASBaseModel.objects.all().filter(id=row['parent_table_id']).values('netasreceivables__Disbursed_amount','Final_charges','Entity'))
            receivables_df.rename(columns={"netasreceivables__Disbursed_amount":'Disbursed_amount'} ,inplace=True)
            current_receivables=transformIOMReceivabledfNew(receivables_df,current_receivables,row)
        return all_receivables,current_receivables
        
        

    else: 
        pass

    current_week_receivables_df_base=pd.DataFrame(acc_basemodel_mdl.objects.filter(Fin_year=fin_year,Week_no=week_no,PayableorReceivable='Receivable',Legacy_dues=False).values('Fin_year','Week_no','Entity','Fin_code','Final_charges','Due_date') ,columns=['Fin_year','Week_no','Entity','Fin_code','Final_charges','Due_date'])
    current_week_receivables_df_rcv=pd.DataFrame(acc_receivables_mdl.objects.filter(rcvstatus_fk__Fin_year=fin_year,rcvstatus_fk__Week_no=week_no).values('disbursed_date','Disbursed_amount','rcvstatus_fk__Fin_year','rcvstatus_fk__Week_no','rcvstatus_fk__Entity') ,columns=['disbursed_date','Disbursed_amount','rcvstatus_fk__Fin_year','rcvstatus_fk__Week_no','rcvstatus_fk__Entity'])
    if not current_week_receivables_df_rcv.empty:
        current_week_receivables_df_rcv.rename(columns={'rcvstatus_fk__Fin_year':'Fin_year','rcvstatus_fk__Week_no':'Week_no','rcvstatus_fk__Entity':'Entity'},inplace=True)
        current_week_receivables_df = pd.merge(current_week_receivables_df_base,current_week_receivables_df_rcv,on=['Fin_year', 'Week_no','Entity'],how='left')
        current_week_receivables_df['duetopool'] = current_week_receivables_df['Final_charges'] -current_week_receivables_df['Disbursed_amount'] 
    else :
        current_week_receivables_df = current_week_receivables_df_base
        current_week_receivables_df['disbursed_date'] =  '--'
        current_week_receivables_df['Disbursed_amount'] =  0
        current_week_receivables_df['duetopool'] = current_week_receivables_df['Final_charges']

    current_receivables = []
    for _,row in current_week_receivables_df.iterrows():
        #pdb.set_trace()
        temp_rec=row.to_dict()
        temp_rec['amount_receivable']=format_indian_currency(row["Final_charges"])
        temp_rec['disbursed_amount']=format_indian_currency(row["Disbursed_amount"])
        temp_rec['duetopool']=format_indian_currency(row["duetopool"])
        #temp_rec['already_disbursed']=format_indian_currency(already_disbursed_amt)
        # get bank account details
        bank_qry=list(BankDetails.objects.filter(Q(fin_code_fk__fin_code=row['Fin_code']) ,(Q(fin_code_fk__end_date__isnull=True) | Q(fin_code_fk__end_date__gte=datetime.today()) ) ).values('bank_name','bank_account','ifsc_code') )

        temp_rec['entity']=getFeesChargesName(row['Fin_code'])
        if len(bank_qry) == 1:
            bank_name=bank_qry[0]['bank_name']
            account_no=bank_qry[0]['bank_account']
            ifsc_code=bank_qry[0]['ifsc_code']
        else:
            bank_name=''
            account_no=''
            ifsc_code=''
        
        temp_rec['bank_name']=bank_name
        temp_rec['acc_no']=account_no
        temp_rec['ifsc_code']=ifsc_code

        current_receivables.append(temp_rec)

    pool_acc_fields = {
        'DSM': 'dsmreceivables__Disbursed_amount',
        'NET_AS': 'netasreceivables__Disbursed_amount',
        'REAC': 'reacreceivables__Disbursed_amount',
        'CONG': 'congreceivables__Disbursed_amount'
    }
    
    for _,row in receivables_df.iterrows():
        receivables_df=pd.DataFrame(poolacc_obj_qry.filter(id=row['parent_table_id']).values(pool_acc_fields[pool_acc],'Final_charges','Entity'))
        receivables_df.rename(columns={pool_acc_fields[pool_acc]:'Disbursed_amount'} ,inplace=True)
        
        all_receivables=transformIOMReceivabledfNew(receivables_df,all_receivables,row)

    return all_receivables,current_receivables

def getCalSum(out_lst , colname):
    try:
        df=pd.DataFrame(out_lst)
        # Clean the 'amount_payable' column
        df[colname] = df[colname].str.replace('₹', '').str.replace(',', '').str.replace(' ', '').astype(float)
        return format_indian_currency(df[colname].sum())
    except Exception as e:
      
        extractdb_errormsg(e)
        return None
    
def downloadIOM(request):
    try:
        formdata=json.loads(request.body)
      
        iom_date=formdata['iom_gen_form']['iom_date']
        acc_type=formdata['iom_gen_form']['acc_type']
        finyear,weekno=None,None
        #last_disbursed_date,surplus_amt = getLastDisbursementSurplus()
        
        if acc_type == 'DSM':
            doc = DocxTemplate("templates/IOM_template.docx")
            model_obj_qry=DSMBaseModel.objects.all()
            # first get the current week
            dsm_df=pd.DataFrame(model_obj_qry.distinct('Fin_year','Week_no').values('Fin_year','Week_no'))
            dsm_df.sort_values(['Fin_year','Week_no'],inplace=True)
            fin_year = dsm_df.iloc[-2]['Fin_year']
            week_no = dsm_df.iloc[-2]['Week_no']

            locals()['dsm_all_payables_df'],locals()['dsm_prev_payables_df'] = processAllPayables(model_obj_qry,iom_date,'P',False,acc_type,fin_year,week_no)
            locals()['dsm_prevweeks_receivables_df'],locals()['dsm_all_receivables_df'] = processAllReceivables(model_obj_qry,iom_date,True,acc_type,fin_year,week_no)  #True means Prev Weeks


            
            #for model,  all_payables,prev_wk_rcv,all_rcv in  [(DSMBaseModel,  'dsm_all_payables_df','dsm_prevweeks_receivables_df','dsm_all_receivables_df')]:
            #    model_obj_qry=model.objects.all()
            #    locals()[all_payables] = processAllPayables(model_obj_qry,iom_date,'P',False,acc_type)
            #    locals()[prev_wk_rcv] = processAllReceivables(model_obj_qry,iom_date,True,acc_type)  #True means Prev Weeks
            #    locals()[all_rcv] = processAllReceivables(model_obj_qry,iom_date,False,acc_type)      
            
            # IOM header data
            if locals()['dsm_all_receivables_df']:
                temp_df=pd.DataFrame(locals()['dsm_all_receivables_df'])
                finyear = temp_df['Fin_year'].unique()[0]
                weekno = temp_df['Week_no'].unique()[0]
                week_start_date,week_end_date=getWeekDates(finyear,weekno)
            

            
            acc_context={
                'payables':locals()['dsm_all_payables_df'], 
                'totalpayable':getCalSum(locals()['dsm_all_payables_df'] , 'amount_payable'),
                'totalpaid':getCalSum(locals()['dsm_all_payables_df'],'paid_amount'),
                'duetopool':getCalSum(locals()['dsm_all_payables_df'],'duetopool'),

                'payables1':locals()['dsm_prev_payables_df'], 
                'totalpayable1':getCalSum(locals()['dsm_prev_payables_df'] , 'amount_payable'),
                'totalpaid1':getCalSum(locals()['dsm_prev_payables_df'],'paid_amount'),
                'duetopool1':getCalSum(locals()['dsm_prev_payables_df'],'duetopool'),

                'prevweeks_receivables': locals()['dsm_all_receivables_df'], 
                'totalreceived':getCalSum(locals()['dsm_all_receivables_df'],'amount_receivable'),
                'totaldisbursed':getCalSum(locals()['dsm_all_receivables_df'],'disbursed_amount'),
                'receivabledue':getCalSum(locals()['dsm_all_receivables_df'],'duetopool'),
                'prevwkalreadydisburse' : getCalSum(locals()['dsm_all_receivables_df'],'already_disbursed'),

                'prevweeks_receivables1': locals()['dsm_prevweeks_receivables_df'], 
                'prevwktotalreceivable1':getCalSum(locals()['dsm_prevweeks_receivables_df'],'amount_receivable'),
                'prevwkalreadydisburse1' : getCalSum(locals()['dsm_prevweeks_receivables_df'],'already_disbursed'),
                'prevwktotalreceived1':getCalSum(locals()['dsm_prevweeks_receivables_df'],'disbursed_amount'),
                'prevwkreceivabledue1':getCalSum(locals()['dsm_prevweeks_receivables_df'],'duetopool'),

            }


        elif acc_type == 'NET_AS':
            doc = DocxTemplate("templates/Other_acc_template.docx")
            model_obj_qry=NetASBaseModel.objects.all()
            # first get the current week
            netas_df=pd.DataFrame(model_obj_qry.distinct('Fin_year','Week_no').values('Fin_year','Week_no'))
            netas_df.sort_values(['Fin_year','Week_no'],inplace=True)
            fin_year = netas_df.iloc[-2]['Fin_year']
            week_no = netas_df.iloc[-2]['Week_no']

            locals()['netas_all_payables_df'],locals()['netas_prev_payables_df'] = processAllPayables(model_obj_qry,iom_date,'P',False,acc_type,fin_year,week_no)
            #model_obj_qry=model.objects.all()
            #pdb.set_trace()
            locals()['netas_prevweeks_receivables_df'],locals()['netas_all_receivables_df'] = processAllReceivables(model_obj_qry,iom_date,True,acc_type,fin_year,week_no)  #True means Prev Weeks



            #for model,all_payables,prev_wk_rcv,all_rcv in [(NetASBaseModel,  'netas_all_payables_df','netas_prevweeks_receivables_df','netas_all_receivables_df')]:
            #    model_obj_qry=model.objects.all()
                #locals()[all_payables] = processAllPayables(model_obj_qry,iom_date,'P',False,acc_type)
            #    locals()[prev_wk_rcv],locals()[all_rcv] = processAllReceivables(model_obj_qry,iom_date,True,"R",acc_type,fin_year,week_no)  #True means Prev Weeks
            #    #locals()[all_rcv] = processAllReceivables(model_obj_qry,iom_date,True,"R",acc_type,fin_year,week_no)      
            #pdb.set_trace()

            # IOM header data
            if locals()['netas_all_receivables_df']:
                temp_df=pd.DataFrame(locals()['netas_all_receivables_df'])
                finyear = temp_df['Fin_year'].unique()[0]
                weekno = temp_df['Week_no'].unique()[0]
                week_start_date,week_end_date=getWeekDates(finyear,weekno)


            acc_context={
                'payables':locals()['netas_all_payables_df'], 
                'totalpayable':getCalSum(locals()['netas_all_payables_df'] , 'amount_payable'),
                'totalpaid':getCalSum(locals()['netas_all_payables_df'],'paid_amount'),
                'duetopool':getCalSum(locals()['netas_all_payables_df'],'duetopool'),
                
                'payables1':locals()['netas_prev_payables_df'], 
                'totalpayable1':getCalSum(locals()['netas_prev_payables_df'] , 'amount_payable'),
                'totalpaid1':getCalSum(locals()['netas_prev_payables_df'],'paid_amount'),
                'duetopool1':getCalSum(locals()['netas_prev_payables_df'],'duetopool'),
                
                'prevweeks_receivables': locals()['netas_all_receivables_df'], 
                'totalreceived':getCalSum(locals()['netas_all_receivables_df'],'amount_receivable'),
                'totaldisbursed':getCalSum(locals()['netas_all_receivables_df'],'disbursed_amount'),
                'receivabledue':getCalSum(locals()['netas_all_receivables_df'],'duetopool'),

                'prevweeks_receivables1':locals()['netas_prevweeks_receivables_df'], 
                'prevwktotalreceivable1':getCalSum(locals()['netas_prevweeks_receivables_df'],'amount_receivable'),
                'prevwkalreadydisburse1' : getCalSum(locals()['netas_prevweeks_receivables_df'],'already_disbursed'),
                'prevwktotalreceived':getCalSum(locals()['netas_prevweeks_receivables_df'],'disbursed_amount'),
                'prevwkreceivabledue1':getCalSum(locals()['netas_prevweeks_receivables_df'],'duetopool')
            }

        elif acc_type == 'REAC':
            doc = DocxTemplate("templates/Other_acc_template.docx")
            model_obj_qry=REACBaseModel.objects.all()
            # first get the current week
            reac_df=pd.DataFrame(model_obj_qry.distinct('Fin_year','Week_no').values('Fin_year','Week_no'))
            reac_df.sort_values(['Fin_year','Week_no'],inplace=True)
            fin_year = reac_df.iloc[-2]['Fin_year']
            week_no = reac_df.iloc[-2]['Week_no']
            
            locals()['reac_all_payables_df'],locals()['reac_prev_payables_df'] = processAllPayables(model_obj_qry,iom_date,'P',False,acc_type,fin_year,week_no)
            
            #locals()['reac_prevweeks_receivables_df'] = processAllReceivables(model_obj_qry,iom_date,True,acc_type)  #True means Prev Weeks
            locals()['reac_prevweeks_receivables_df'],locals()['reac_all_receivables_df'] = processAllReceivables(model_obj_qry,iom_date,True,acc_type,fin_year,week_no)     
            
            # IOM header data
            if locals()['reac_all_payables_df']:
                temp_df=pd.DataFrame(locals()['reac_all_payables_df'])
                finyear = temp_df['fin_year'].unique()[0]
                weekno = temp_df['week_no'].unique()[0]
                week_start_date,week_end_date=getWeekDates(finyear,weekno)
            
            acc_context={
                'payables':locals()['reac_all_payables_df'], 
                'totalpayable':getCalSum(locals()['reac_all_payables_df'] , 'amount_payable'),
                'totalpaid':getCalSum(locals()['reac_all_payables_df'],'paid_amount'),
                'duetopool':getCalSum(locals()['reac_all_payables_df'],'duetopool'),

                'payables1':locals()['reac_prev_payables_df'], 
                'totalpayable1':getCalSum(locals()['reac_prev_payables_df'] , 'amount_payable'),
                'totalpaid1':getCalSum(locals()['reac_prev_payables_df'],'paid_amount'),
                'duetopool1':getCalSum(locals()['reac_prev_payables_df'],'duetopool'),

                'prevweeks_receivables':locals()['reac_all_receivables_df'], 
                'totalreceived':getCalSum(locals()['reac_all_receivables_df'],'amount_receivable'),
                'totaldisbursed':getCalSum(locals()['reac_all_receivables_df'],'disbursed_amount'),
                'receivabledue':getCalSum(locals()['reac_all_receivables_df'],'duetopool'),

                
            }
        elif acc_type == 'Legacy':
            doc = DocxTemplate("templates/Legacy_template.docx")
            model_obj_qry=LegacyBaseModel.objects.all()
            # first get the current week
            #reac_df=pd.DataFrame(model_obj_qry.distinct('Fin_year','Week_no').values('Fin_year','Week_no'))
            #reac_df.sort_values(['Fin_year','Week_no'],inplace=True)
            fin_year = '2024-25'
            week_no = '1'
            
            locals()['legacy_all_payables_df'],locals()['legacy_prev_payables_df'] = processAllPayables(model_obj_qry,iom_date,'P',False,acc_type,fin_year,week_no)
            
            #locals()['reac_prevweeks_receivables_df'] = processAllReceivables(model_obj_qry,iom_date,True,acc_type)  #True means Prev Weeks
            locals()['legacy_prevweeks_receivables_df'],locals()['legacy_all_receivables_df'] = processAllReceivables(model_obj_qry,iom_date,True,acc_type,fin_year,week_no)     
            
            # IOM header data
            if locals()['legacy_all_payables_df']:
                temp_df=pd.DataFrame(locals()['legacy_all_payables_df'])
                finyear = temp_df['fin_year'].unique()[0]
                weekno = temp_df['week_no'].unique()[0]
                week_start_date,week_end_date=getWeekDates(finyear,weekno)
            
            acc_context={
                'payables':locals()['legacy_all_payables_df'], 
                'totalpayable':getCalSum(locals()['legacy_all_payables_df'] , 'amount_payable'),
                'totalpaid':getCalSum(locals()['legacy_all_payables_df'],'paid_amount'),
                'duetopool':getCalSum(locals()['legacy_all_payables_df'],'duetopool'),

                'payables1':locals()['legacy_prev_payables_df'], 
                'totalpayable1':getCalSum(locals()['legacy_prev_payables_df'] , 'amount_payable'),
                'totalpaid1':getCalSum(locals()['legacy_prev_payables_df'],'paid_amount'),
                'duetopool1':getCalSum(locals()['legacy_prev_payables_df'],'duetopool'),

                'prevweeks_receivables':locals()['legacy_prevweeks_receivables_df'], 
                'totalreceived':getCalSum(locals()['legacy_prevweeks_receivables_df'],'amount_receivable'),
                'totaldisbursed':getCalSum(locals()['legacy_prevweeks_receivables_df'],'disbursed_amount'),
                'receivabledue':getCalSum(locals()['legacy_prevweeks_receivables_df'],'duetopool'),

                'prevweeks_receivables1':locals()['legacy_all_receivables_df'], 
                'prevwktotalreceivable1':getCalSum(locals()['legacy_all_receivables_df'],'amount_receivable'),
                'prevwkalreadydisburse1' : getCalSum(locals()['legacy_all_receivables_df'],'already_disbursed'),
                'prevwktotalreceived':getCalSum(locals()['legacy_all_receivables_df'],'disbursed_amount'),
                'prevwkreceivabledue1':getCalSum(locals()['legacy_all_receivables_df'],'duetopool')
            }
        elif acc_type == 'CONG':
            doc = DocxTemplate("templates/Other_acc_template.docx")
            model_obj_qry=CONGBaseModel.objects.all()
            # first get the current week
            cong_df=pd.DataFrame(model_obj_qry.distinct('Fin_year','Week_no').values('Fin_year','Week_no'))
            cong_df.sort_values(['Fin_year','Week_no'],inplace=True)
            fin_year = cong_df.iloc[-1]['Fin_year']
            week_no = cong_df.iloc[-1]['Week_no']

            
            locals()['reac_all_payables_df'],locals()['reac_prev_payables_df'] = processAllPayables(model_obj_qry,iom_date,'P',False,acc_type,fin_year,week_no)

            #locals()['reac_prevweeks_receivables_df'] = processAllReceivables(model_obj_qry,iom_date,True,acc_type)  #True means Prev Weeks
            locals()['reac_prevweeks_receivables_df'],locals()['reac_all_receivables_df'] = processAllReceivables(model_obj_qry,iom_date,True,acc_type,fin_year,week_no)     

            # IOM header data
            if locals()['reac_all_payables_df']:
                temp_df=pd.DataFrame(locals()['reac_all_payables_df'])
                finyear = temp_df['fin_year'].unique()[0]
                weekno = temp_df['week_no'].unique()[0]
                week_start_date,week_end_date=getWeekDates(finyear,weekno)
            
            acc_context={
                'payables':locals()['reac_all_payables_df'], 
                'totalpayable':getCalSum(locals()['reac_all_payables_df'] , 'amount_payable'),
                'totalpaid':getCalSum(locals()['reac_all_payables_df'],'paid_amount'),
                'duetopool':getCalSum(locals()['reac_all_payables_df'],'duetopool'),


                'prevweeks_receivables':locals()['reac_all_receivables_df'], 
                'totalreceived':getCalSum(locals()['reac_all_receivables_df'],'amount_receivable'),
                'totaldisbursed':getCalSum(locals()['reac_all_receivables_df'],'disbursed_amount'),
                'receivabledue':getCalSum(locals()['reac_all_receivables_df'],'duetopool'),

                
            }
        else:
            week_start_date,week_end_date =None,None
        
        try:
            subject='Disbursement  from DAS Pool Account. / सप्ताह '+str(weekno)+' के लिए डीएसएम पूल से संवितरण ('+week_start_date.strftime('%d-%m-%Y')+'-'+week_end_date.strftime('%d-%m-%Y')+').' 
        except:
            subject='Disbursement  from DAS Pool Account. / सप्ताह '+'---'


        iom_date_str=datetime.strptime(iom_date,'%Y-%m-%d').strftime('%d-%m-%Y')
        context={
                'iom_date':iom_date_str,
                'weekno':weekno,
                'subject':subject,
                'acc_type':acc_type
            }

        context.update(acc_context)
        
        doc.render(context)   
        # all MWH files goes to this folder
        parent_folder = os.path.abspath(os.path.join(base_dir, os.pardir))
        directory = os.path.join(parent_folder, 'IOMS')

        docx_directory=os.path.join(directory,'Docx')

        if not os.path.exists(docx_directory):
                os.makedirs(docx_directory)

        inname_docx=iom_date_str+'_IOM'+'.docx'
        output_file=os.path.join(docx_directory, inname_docx)
        doc.save(output_file)

        # pythoncom.CoInitialize()
        # #Convert the Word file to PDF
        # pdf_file_path = output_file.replace('.docx', '.pdf')
        # convert(output_file, pdf_file_path)
       
        # with open(pdf_file_path, 'rb') as pdf_file:
        #     response = HttpResponse(pdf_file.read(), content_type='application/pdf')
        #     response['Content-Disposition'] = 'attachment;'
       
        with open(output_file, 'rb') as docx_file:
            response = HttpResponse(docx_file.read(), content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
            response['Content-Disposition'] = 'attachment;'
        return response
        
    except Exception as e:
       
        return HttpResponse(e)

def uploadSignedIOM(request):
    try:
        formdata=json.loads(request.POST['formdata'])
        file=request.FILES['file']
        # write the files into folder
        parent_folder = os.path.abspath(os.path.join(base_dir, os.pardir))
        directory = os.path.join(parent_folder, 'Files', 'SignedIOMs' , formdata['selected_date'])
        # add startdate and enddate to create new folder
        if not os.path.exists(directory):
                # Create the directory if it doesn't exist
                os.makedirs(directory)

        file_path=os.path.join(directory ,  file.name)
      
        with open(file_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)

        iom_date=datetime.strptime(formdata['selected_date'],'%Y-%m-%d').date()
        SignedIOMS.objects.filter(iom_date=iom_date,acc_type=formdata['acc_type']).delete()
        SignedIOMS(
            iom_path=trimFilePath(file_path),
            iom_date=iom_date,
            acc_type=formdata['acc_type']
        ).save()

        return JsonResponse({'status':True},safe=False)
    except Exception as e:
        
        return JsonResponse({'status':False},safe=False)


def downloadSignedIOM(request):
    try:
        formdata=json.loads(request.body)['formdata']
        selected_date=datetime.strptime(formdata['selected_date'],'%Y-%m-%d').date()
        # get the file path
        signediom_qry=SignedIOMS.objects.filter(iom_date=selected_date,acc_type=formdata['acc_type'])
        full_path=''
        if signediom_qry.count()>0:
            file_path=signediom_qry.all().values_list('iom_path',flat=True)[0]
            parent_folder = os.path.abspath(os.path.join(base_dir, os.pardir))
            full_path = os.path.join(parent_folder, file_path )
            return FileResponse(open(full_path,'rb'),content_type='application/pdf') 
    
        else:
            return JsonResponse({'message': 'No data exists'}, status=404,safe=False)

        
    except Exception as e:
        return HttpResponse('error')
    
def downloadFinExcel(request):
    try:
        formdata=json.loads(request.body)['formdata']
        selected_date=datetime.strptime(formdata['selected_date'],'%Y-%m-%d').date()
        disburse_entities_df=pd.DataFrame(DisbursedEntities.objects.filter(disstatus_fk__Disbursed_date=selected_date,pool_acctype=formdata['acc_type'],payrcv='R').values('fin_year','week_no','entity','final_charges','fin_code') ,columns=['fin_year','week_no','entity','final_charges','fin_code'])

        disburse_entities_df.rename(columns={'fin_year':'Fin Year','week_no':'Week No','entity':'Entity','final_charges':'Final Charges','fin_code':'Fin Code' },inplace=True)

        parent_folder = os.path.abspath(os.path.join(base_dir, os.pardir))
        directory = os.path.join(parent_folder, 'Files', 'Trash' )
        if not os.path.exists(directory):
            # Create the directory if it doesn't exist
            os.makedirs(directory)  

        in_filename='FinIOM_'+str(selected_date)+'.csv'
        full_path=os.path.join(directory, in_filename)
        disburse_entities_df.to_csv(full_path,index=False)

        return FileResponse(open(full_path,'rb'),content_type='text/csv') 
    
    except Exception as e:
        return HttpResponse('error')