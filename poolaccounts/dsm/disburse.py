from collections import defaultdict
from operator import index
from dsm.common import no_data_found_df
from dsm.common import generateWeekRange
from dsm.common import add530hrstoDateString 
from dsm.common import getFeesChargesName ,getMergedAccts
from registration.custom_paths import get_current_financial_year
from registration.fetch_data import getFCNames
from registration.extarctdb_errors import extractdb_errormsg
from .models import *
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.http import HttpResponse , JsonResponse ,FileResponse
import json ,os ,pandas as pd
from .engine_create import *
from django.db.models import Max
from poolaccounts.settings import base_dir
import pdb , numpy as np
from datetime import datetime, timedelta
from io import StringIO
from django.db.models import F ,Count ,Sum , Q
from django.db.models.functions import Coalesce
import math ,ast
from .common import keys,legacy_keys
import pandas as pd

def poolAccPaidAmount(pool_acc):
    try:
        other_qry = Q(Is_disbursed=False)| Q(Is_disbursed__isnull=True)
        common_qry=( other_qry ) & Q(paystatus_fk__Legacy_dues=False)
        if pool_acc == 'DSM':
            # DSM Payments are approved but not considered in disbursement
            payment_qry=Payments.objects.filter(common_qry)
            paid_amount=payment_qry.aggregate(total_amount=Coalesce(Sum('Paid_amount'),0.0))
            
        elif pool_acc == 'IR':
            # IR Payments are approved but not considered in disbursement
            payment_qry=IRPayments.objects.filter(other_qry)
            paid_amount=payment_qry.aggregate(total_amount=Coalesce(Sum('Paid_amount'),0.0))
            
        elif pool_acc == 'SRAS':
            # SRAS Payments are approved but not considered in disbursement
            sras_payment_qry=SRASPayments.objects.filter(common_qry)
            
            paid_amount=sras_payment_qry.aggregate(total_amount=Coalesce(Sum('Paid_amount'),0.0))

        elif pool_acc == 'NET_AS':
            # SRAS Payments are approved but not considered in disbursement
            netas_payment_qry=NetASPayments.objects.filter(common_qry)
            
            paid_amount=netas_payment_qry.aggregate(total_amount=Coalesce(Sum('Paid_amount'),0.0))
            
        elif pool_acc == 'TRAS':
            # TRAS Payments are approved but not considered in disbursement
            tras_payment_qry=TRASPayments.objects.filter(common_qry)
            paid_amount=tras_payment_qry.aggregate(total_amount=Coalesce(Sum('Paid_amount'),0.0))

        elif pool_acc == 'MBAS':
            # MBAS Payments are approved but not considered in disbursement
            mbas_payment_qry=MBASPayments.objects.filter(common_qry)
            paid_amount=mbas_payment_qry.aggregate(total_amount=Coalesce(Sum('Paid_amount'),0.0))

        elif pool_acc == 'REAC':
            # REAC Payments are approved but not considered in disbursement
            reac_payment_qry=REACPayments.objects.filter(common_qry)
            paid_amount=reac_payment_qry.aggregate(total_amount=Coalesce(Sum('Paid_amount'),0.0))
           
        elif pool_acc == 'CONG':
            # CONG Payments are approved but not considered in disbursement
            cong_payment_qry=CONGPayments.objects.filter(common_qry)
            paid_amount=cong_payment_qry.aggregate(total_amount=Coalesce(Sum('Paid_amount'),0.0))
        
        elif pool_acc == 'REV':
            # REAC Payments are approved but not considered in disbursement
            reac_payment_qry=RevisionPayments.objects.filter(other_qry)
            paid_amount=reac_payment_qry.aggregate(total_amount=Coalesce(Sum('Paid_amount'),0.0))
        
        elif pool_acc == 'Shortfall':
            # REAC Payments are approved but not considered in disbursement
            shortfall_payment_qry=ShortfallPayments.objects.filter(Is_disbursed=False)
            paid_amount=shortfall_payment_qry.aggregate(total_amount=Coalesce(Sum('Paid_amount'),0.0))

        elif pool_acc == 'Interest':
            # REAC Payments are approved but not considered in disbursement
            int_payment_qry=InterestPayments.objects.filter(Is_disbursed=False)
            paid_amount=int_payment_qry.aggregate(total_amount=Coalesce(Sum('Paid_amount'),0.0))

        elif pool_acc == 'Others':
            # REAC Payments are approved but not considered in disbursement
            other_payment_qry=OtherPayments.objects.filter(Is_disbursed=False)
            paid_amount=other_payment_qry.aggregate(total_amount=Coalesce(Sum('Paid_amount'),0.0))
        else: 
            return 0
        return paid_amount['total_amount']
    
    except Exception as e:
        extractdb_errormsg(e)
        return 0
    
def poolAccLegacyPaidAmount(pool_acc):
    try:
        common_qry=( Q(Is_disbursed=False)| Q(Is_disbursed__isnull=True) ) & Q(paystatus_fk__Legacy_dues=True)

        if pool_acc == 'DSM':
            # DSM Payments are approved but not considered in disbursement
            payment_qry=Payments.objects.filter(common_qry)
           
            paid_amount=payment_qry.aggregate(total_amount=Coalesce(Sum('Paid_amount'),0.0))
            
        elif pool_acc == 'CONG':
            # SRAS Payments are approved but not considered in disbursement
            netas_payment_qry=CONGPayments.objects.filter(common_qry)
            paid_amount=netas_payment_qry.aggregate(total_amount=Coalesce(Sum('Paid_amount'),0.0))
            
        elif pool_acc == 'REAC':
            # REAC Payments are approved but not considered in disbursement
            reac_payment_qry=REACPayments.objects.filter(common_qry)
            paid_amount=reac_payment_qry.aggregate(total_amount=Coalesce(Sum('Paid_amount'),0.0))
        
        elif pool_acc == 'Legacy':
            # Legacy Payments are approved but not considered in disbursement
            reac_payment_qry=LegacyPayments.objects.filter(common_qry)
            paid_amount=reac_payment_qry.aggregate(total_amount=Coalesce(Sum('Paid_amount'),0.0))
           
        else: 
            return 0
        return paid_amount['total_amount']
    
    except Exception as e:
        extractdb_errormsg(e)
        return 0
    
def checkPendingMore2weeks(model,acctype):
    if acctype == 'DSM':
        df=pd.DataFrame(globals()['final_dsm_receivables'])
        # from these receivables get the pending more than 2 weeks
        for _,row in df.iterrows():
            previous_financial_year= str( int(float(row['Fin_year'][:4]))-1) +'-'+ str(int(float(row['Fin_year'][5:]))-1)

            temp_df=pd.DataFrame(model.objects.filter( 
                (
                    (Q(Fin_year=row['Fin_year']) & Q(Week_no__lt=row['Week_no'])) | 
                    Q(Fin_year=previous_financial_year)
                ),
                Q(Fin_code=row['Fin_code']),
                Q(PayableorReceivable='Payable')).values('Fin_year','Week_no','Final_charges','payments__Paid_amount'))
            if temp_df.shape[0] >= 2:
                # Keep rows where the specified column contains None values
                temp_df = temp_df[temp_df['payments__Paid_amount'].isna()]
                
            

def trasnformFinalReceivables(df,status):
    # assign Final_charges to new column
    df['Disburse_amount']=df['Final_charges']
    # Step 2: Get unique pairs of 'Fin_year' and 'Week_no'
    unique_pairs = df[['Fin_year', 'Week_no']].drop_duplicates()
    finyear_week_list= unique_pairs.values.tolist()
    
    if len(finyear_week_list)>1:
        sorted_data = sorted(finyear_week_list, key=lambda x: (int(x[0].split('-')[0]), x[1]))
        # column to be dropped from latest record , if sorted_data contains [['2024-25', 10], ['2024-25', 11], ['2024-25', 12]] then we have to consider 2nd from last record only
        fin_year=sorted_data[-1][0]
        week_no=sorted_data[-1][1]
      
        # drop from dsm_receivables_df contains fin_year and week_no
        filtered_df = df[~((df['Fin_year'] == fin_year) & (df['Week_no'] == week_no))]
        temp_df=filtered_df.copy()
        temp_df.sort_values(['Fin_year','Week_no','Entity'],inplace=True)
        
        final_receivables=temp_df.to_dict(orient='records')
    else:
        
        final_receivables=df.to_dict(orient='records')
    

    return final_receivables 

def transformPoolPrevWeek(obj_model):
    # disbursed already but not done fully only partial disbursement happend
    actual_rcvd_df=pd.DataFrame(obj_model.objects.filter(rcvstatus_fk__Is_disbursed=True,rcvstatus_fk__Fully_disbursed='P',rcvstatus_fk__PayableorReceivable='Receivable' ,rcvstatus_fk__Revision_no=0).values('rcvstatus_fk__Fin_year','rcvstatus_fk__Week_no','rcvstatus_fk__Entity','rcvstatus_fk__Final_charges','Disbursed_amount' ,'rcvstatus_fk__Fin_code','rcvstatus_fk__id') ,columns=['rcvstatus_fk__Fin_year','rcvstatus_fk__Week_no','rcvstatus_fk__Entity','rcvstatus_fk__Final_charges','Disbursed_amount' ,'rcvstatus_fk__Fin_code','rcvstatus_fk__id'] )
    
    actual_rcvd_df=actual_rcvd_df.groupby(['rcvstatus_fk__Fin_year','rcvstatus_fk__Week_no','rcvstatus_fk__Entity','rcvstatus_fk__Final_charges','rcvstatus_fk__Fin_code','rcvstatus_fk__id'])['Disbursed_amount'].sum().reset_index()
    # rcvstatus_fk__Final_charges is disbursible as per SRPC
    actual_rcvd_df['rcvstatus_fk__Final_charges']=pd.to_numeric(actual_rcvd_df['rcvstatus_fk__Final_charges'].fillna(0))
    
    # Disbursed_amount is already Disbursed by User
    actual_rcvd_df['Disbursed_amount']=pd.to_numeric(actual_rcvd_df['Disbursed_amount'].fillna(0))
    #left over amount to be Disbursed
    actual_rcvd_df['Final_charges']=actual_rcvd_df['rcvstatus_fk__Final_charges']-actual_rcvd_df['Disbursed_amount']
    # neglect if amount is <0
    actual_rcvd_df = actual_rcvd_df[actual_rcvd_df['Final_charges'] > 0]
    # Rounding the column to 2 decimal places
    actual_rcvd_df['Final_charges'] = actual_rcvd_df['Final_charges'].round(2)
    actual_rcvd_df['rcvstatus_fk__Final_charges']=actual_rcvd_df['Final_charges']

    actual_rcvd_df.rename(columns={'rcvstatus_fk__Fin_year':'Fin_year','rcvstatus_fk__Week_no':'Week_no','rcvstatus_fk__Entity':'Entity','rcvstatus_fk__Final_charges':'Disburse_amount' ,'rcvstatus_fk__Fin_code':'Fin_code','rcvstatus_fk__id':'id'},inplace=True)
   
    # actual_rcvd_list=actual_rcvd_df.to_dict(orient='records')
    
    return actual_rcvd_df

def appendFinalPrevweek(current_wk_list,prev_wk_list,pool_acc):
    try:
        current_wk_df=pd.DataFrame(current_wk_list)
        prev_wk_df=prev_wk_list
        unique_pairs = current_wk_df[['Fin_year', 'Week_no']].drop_duplicates()
        finyear_week_list= unique_pairs.values.tolist()
    
        user_already_disbursed_forweek_df=pd.DataFrame(TempDisbursedWeeks.objects.filter(pool_acctype=pool_acc).values('fin_year','week_no'),columns=['fin_year','week_no'])

        if len(finyear_week_list)>1:
            sorted_data = sorted(finyear_week_list, key=lambda x: (int(x[0].split('-')[0]), x[1]))
            # it contains more than 1 week then only append old week to prev_wk_df so that always current wk df contains 1 week df values
            if len(sorted_data)>1:
                # column to be dropped from latest record
                fin_year=sorted_data[-1][0]
                week_no=sorted_data[-1][1]

                # drop from dsm_receivables_df contains fin_year and week_no
                filtered_df = current_wk_df[~((current_wk_df['Fin_year'] == fin_year) & (current_wk_df['Week_no'] == week_no))]
                # append temp_df to prev_wk_df
                result_df=pd.concat([prev_wk_df,filtered_df])

                merged_df = result_df.merge(user_already_disbursed_forweek_df, how='left', left_on=['Fin_year', 'Week_no'], right_on=['fin_year', 'week_no'], indicator=True)
                final_df = merged_df[merged_df['_merge'] == 'left_only'].drop(columns=['fin_year', 'week_no', '_merge'])

                # if not result_df.empty:
                #     finyears = list(set(result_df[['Fin_year', 'Week_no']].drop_duplicates()['Fin_year'].values.tolist()))
                #     weeknos =  list(set(result_df[['Fin_year', 'Week_no']].drop_duplicates()['Week_no'].values.tolist()))
                #     # get unique finyear and weekno

                #     disbursed_entites_df=pd.DataFrame(DisbursedEntities.objects.filter(pool_acctype=pool_acc,payrcv='R',fin_year__in=finyears,week_no__in=weeknos).values('fin_year','week_no','entity','final_charges'),columns=['fin_year','week_no','entity','final_charges'])
                    
                #     # Merge dataframes to find matching rows
                #     merged_df = result_df.merge(disbursed_entites_df, how='left', 
                #                                 left_on=['Fin_year', 'Week_no', 'Entity', 'Disburse_amount'], 
                #                                 right_on=['fin_year', 'week_no', 'entity', 'final_charges'], 
                #                                 indicator=True)
                #     # Select rows that do not match
                #     result_df_filtered = merged_df[merged_df['_merge'] == 'left_only']
                #     # Drop auxiliary columns
                #     result_df_filtered = result_df_filtered.drop(columns=['fin_year', 'week_no', 'entity', 'final_charges', '_merge'])
                # else:
                #     result_df_filtered=pd.DataFrame([],columns=['Fin_year', 'Week_no', 'Entity', 'Disburse_amount', 'Fin_code', 'id',
                #                 'Disbursed_amount', 'Final_charges'])

                final_df=final_df.fillna(0)
                final_df.sort_values(['Fin_year','Week_no','Entity'],inplace=True)
                # from current_wk_df remove old weeks and store it again
                current_wk_filtered_df = current_wk_df[((current_wk_df['Fin_year'] == fin_year) & (current_wk_df['Week_no'] == week_no))]

                return final_df.to_dict(orient='records') , current_wk_filtered_df.to_dict(orient='records')
    except Exception as e:
        extractdb_errormsg(e)

    prev_wk_df=prev_wk_df.fillna(0)
    return prev_wk_df.to_dict(orient='records'),current_wk_df.to_dict(orient='records')
    
def getLastDisbursementSurplus():
    # always get the latest week based on Disbursed_date desc . If all are disbursed then only full disbursement happened
    dis_status = list(DisbursementStatus.objects.filter(final_disburse=True).order_by('-Disbursed_date')[:1].values('Disbursed_date','Surplus_amt','legacy_surplus_amt','dsm','mbas','sras','tras','dsm_prevwk','revision_disbursed','remarks'))
    
    # If no disbursement found then this is the first disbursement
    if dis_status:
        last_disbursed_date=dis_status[0]['Disbursed_date'].strftime('%d-%m-%Y')
        remarks = dis_status[0]['remarks']
        #if not None else consider 0
        surplus_amt=dis_status[0]['Surplus_amt'] if dis_status[0]['Surplus_amt'] else 0
        legacy_surplus_amt=dis_status[0]['legacy_surplus_amt'] if dis_status[0]['legacy_surplus_amt'] else 0
        # subtract revision disbursed amount if any
        surplus_amt=surplus_amt-dis_status[0]['revision_disbursed'] if dis_status[0]['revision_disbursed'] else surplus_amt
        
        return last_disbursed_date,surplus_amt,legacy_surplus_amt,remarks
    else:
        return None,0

def getPoolDisbursedAmount(disbursed_entities_qry,pool_acc):
    try:
        return disbursed_entities_qry.filter(pool_acctype=pool_acc).aggregate(total=Coalesce(Sum('final_charges'),0.0))['total']

    except Exception as e:
        extractdb_errormsg(e)
        return None


def getPoolAccountSummary(surplus_amt,cal_already_disbursed_amt,legacy_surplus_amt):
    #here keys defined globally
    dsm_paid_amount, reac_paid_amount, ir_paid_amount, net_as_paid_amount,interest_paid_amount, revision_paid_amount,cong_paid_amount,other_misc_amount,shortfall_paid_amount = map(poolAccPaidAmount, keys)

    legacy_dsm_paid_amount, legacy_reac_paid_amount, legacy_net_as_paid_amount,legacy_paid_amount = map(poolAccLegacyPaidAmount, legacy_keys)
    
    # check is this how much surplus amount transferred to nldc
    intimated_nldc_qry=list(IntimateNLDC.objects.filter( ( Q(is_transferred=False) & Q(is_used_indisbursement=False)) | (Q(is_transferred=True) & Q(is_used_indisbursement=False)) ).values('transfer_amount','amount_available','is_transferred'))

    if len(intimated_nldc_qry) > 0 :
        first_dict = intimated_nldc_qry[0]
    else :
        first_dict = []
   
    intimated_tot_amount=0
    for nldc in intimated_nldc_qry:
        intimated_tot_amount+=nldc['amount_available'] - nldc['transfer_amount']

    if len(first_dict) == 0 :
        surplus_amt = surplus_amt
    elif not (first_dict['is_transferred']) :
        surplus_amt = 0
    else :
        surplus_amt = intimated_tot_amount
    
    nldc_split_qry=list(NLDCPoolAmountSplit.objects.filter(disburse_date=datetime.today() ).values('amount_for_dsm','amount_for_netas','amount_for_reac','is_user_checked'))
    if len(nldc_split_qry) :
        legacy_status = nldc_split_qry[0]['is_user_checked']
    else :
        legacy_status = False

    total_amount_inpool=math.floor(surplus_amt + dsm_paid_amount+net_as_paid_amount+reac_paid_amount+interest_paid_amount+ir_paid_amount+revision_paid_amount+cong_paid_amount+other_misc_amount+shortfall_paid_amount- cal_already_disbursed_amt )
    total_amount_inpool_legacy=math.floor(legacy_surplus_amt + legacy_dsm_paid_amount+legacy_reac_paid_amount+legacy_net_as_paid_amount+legacy_paid_amount- cal_already_disbursed_amt )
    
    if not legacy_status :
        total_amount_inpool=math.floor(surplus_amt + dsm_paid_amount+net_as_paid_amount+reac_paid_amount+interest_paid_amount+ir_paid_amount+revision_paid_amount+cong_paid_amount+other_misc_amount+shortfall_paid_amount- cal_already_disbursed_amt )
        total_amount_inpool_legacy=math.floor(legacy_surplus_amt + legacy_dsm_paid_amount+legacy_reac_paid_amount+legacy_net_as_paid_amount+legacy_paid_amount)
    else :
        total_amount_inpool=math.floor(surplus_amt + dsm_paid_amount+net_as_paid_amount+reac_paid_amount+interest_paid_amount+ir_paid_amount+revision_paid_amount+cong_paid_amount+other_misc_amount+shortfall_paid_amount )
        total_amount_inpool_legacy=math.floor(legacy_surplus_amt + legacy_dsm_paid_amount+legacy_reac_paid_amount+legacy_net_as_paid_amount+legacy_paid_amount- cal_already_disbursed_amt )

    
    all_poolaccounts_summary=[
                {'Total_amount_inpool':total_amount_inpool , 'Prev_wk': math.floor(surplus_amt) , 'DSM': dsm_paid_amount+ir_paid_amount+revision_paid_amount+other_misc_amount ,'NET_AS':net_as_paid_amount,'REAC':reac_paid_amount ,'CONG':cong_paid_amount, 'Int_Amount':interest_paid_amount,'Shortfall':shortfall_paid_amount,'Already_disbursed':cal_already_disbursed_amt ,'Legacy_total' : total_amount_inpool_legacy,'Legacy_DSM':legacy_dsm_paid_amount,'Legacy_REAC':legacy_reac_paid_amount,'Legacy_NET_AS':legacy_net_as_paid_amount ,'Legacy_legacy' : legacy_paid_amount, 'Prev_wk_legacy': math.floor(legacy_surplus_amt)
                }]
    return all_poolaccounts_summary

def getAlreadyDisbursedAmounts(partial_dis_status,nldc_split_qry):
    
    if partial_dis_status:
        table_id=partial_dis_status[0]['id']
    else:
        table_id=None
        # # recent disbursement happend but new disbursement not yet initiated so reset all values to 
        # nldc_split_qry[0]['amount_for_dsm']=0
        # nldc_split_qry[0]['amount_for_netas']=0
        # nldc_split_qry[0]['amount_for_reac']=0
        # return nldc_split_qry
    
    disbursed_entites_qry=DisbursedEntities.objects.filter(disstatus_fk_id=table_id,payrcv='R')
    
    # calculate already disbursed amount
    dsm_disbursed_amount_qry=disbursed_entites_qry.filter(pool_acctype='DSM').aggregate(total_amount=Coalesce(Sum('final_charges'),0.0))
    
    # calculate already disbursed amount
    netas_disbursed_amount_qry=disbursed_entites_qry.filter(pool_acctype='NET_AS').aggregate(total_amount=Coalesce(Sum('final_charges'),0.0))
    
    # calculate already disbursed amount
    reac_disbursed_amount_qry=disbursed_entites_qry.filter(pool_acctype='REAC').aggregate(total_amount=Coalesce(Sum('final_charges'),0.0))
    
    nldc_split_qry[0]['amount_for_dsm']=  nldc_split_qry[0]['amount_for_dsm']-dsm_disbursed_amount_qry['total_amount'] if nldc_split_qry[0]['amount_for_dsm']-dsm_disbursed_amount_qry['total_amount'] > 0 else 0

    nldc_split_qry[0]['amount_for_netas']=  nldc_split_qry[0]['amount_for_netas']-netas_disbursed_amount_qry['total_amount'] if nldc_split_qry[0]['amount_for_netas']-netas_disbursed_amount_qry['total_amount'] > 0 else 0

    nldc_split_qry[0]['amount_for_reac']=  nldc_split_qry[0]['amount_for_reac']-reac_disbursed_amount_qry['total_amount'] if nldc_split_qry[0]['amount_for_reac']-reac_disbursed_amount_qry['total_amount'] > 0 else 0

    return nldc_split_qry

def getLastDisbursedWk(request):
    try:
        last_disbursed_date,surplus_amt,legacy_surplus_amt,remarks = getLastDisbursementSurplus()
        last_st_upload = BankStatement.objects.values_list("ValueDate",flat=True).last().strftime("%d-%m-%Y")
        
        partial_dis_status = list(DisbursementStatus.objects.filter(
            ( Q(dsm=False) | Q(net_as=False) |Q(reac=False) | Q(ir=False) | Q(dsm_prevwk=False)| Q(net_as_prevwk=False)| Q(reac_prevwk=False) | Q(final_disburse=False) )
            ).order_by('-Disbursed_date')[:1].values('Disbursed_date','Surplus_amt','dsm','net_as','reac','ir','cong', 'dsm_collected','id','dsm_prevwk','net_as_prevwk','sras_prevwk','tras_prevwk','reac_prevwk','mbas_prevwk','ir_prevwk','cong_prevwk'))
        

        # dsm_status and sras_status are accessing through global variable
        if partial_dis_status:
            # is to calculate already disbursed amount
            disbursed_entities_qry=DisbursedEntities.objects.filter(disstatus_fk__id=partial_dis_status[0]['id'],payrcv='R')
            cal_already_disbursed_df=pd.DataFrame(disbursed_entities_qry.values('final_charges'),columns=['final_charges'])
            cal_already_disbursed_amt=cal_already_disbursed_df['final_charges'].sum()

            dsm_disbursed_amount=getPoolDisbursedAmount(disbursed_entities_qry,'DSM')
            net_as_disbursed_amount=getPoolDisbursedAmount(disbursed_entities_qry,'NET_AS')
            reac_disbursed_amount=getPoolDisbursedAmount(disbursed_entities_qry,'REAC')
            ir_disbursed_amount=getPoolDisbursedAmount(disbursed_entities_qry,'IR')
            
            dsm_status=partial_dis_status[0]['dsm']
            net_as_status=partial_dis_status[0]['net_as']
            reac_status=partial_dis_status[0]['reac']
            ir_status=partial_dis_status[0]['ir']
            cong_status=partial_dis_status[0]['cong']

            dsm_prevwk_status=partial_dis_status[0]['dsm_prevwk']
            net_as_prevwk_status=partial_dis_status[0]['net_as_prevwk']
            reac_prevwk_status=partial_dis_status[0]['reac_prevwk']
            ir_prevwk_status=partial_dis_status[0]['ir_prevwk']
            cong_prevwk_status=partial_dis_status[0]['cong_prevwk']
           
        else:
            cal_already_disbursed_amt=0
            dsm_disbursed_amount=0
            net_as_disbursed_amount=0
            reac_disbursed_amount=0
            ir_disbursed_amount=0

            dsm_status=False
            net_as_status=False
            reac_status=False
            ir_status=False
            cong_status=False
            dsm_prevwk_status=False
            net_as_prevwk_status=False
            reac_prevwk_status=False
            ir_prevwk_status=False
            cong_prevwk_status=False
        
        all_poolaccounts_summary=getPoolAccountSummary(surplus_amt,cal_already_disbursed_amt,legacy_surplus_amt)

        # These are for Current Week
        current_wk_models = [
            (DSMBaseModel, 'dsm_status', 'final_dsm_receivables'),
            (NetASBaseModel, 'net_as_status', 'final_net_as_receivables'),
            (REACBaseModel, 'reac_status', 'final_reac_receivables'),
            (IRBaseModel, 'ir_status', 'final_ir_receivables'),
            (CONGBaseModel, 'cong_status', 'final_cong_receivables'),
        ]
        for model, status, final_var in current_wk_models:
            if not locals()[status]:
                receivables_df = pd.DataFrame(model.objects.filter(Q(Is_disbursed=False) ,Q(PayableorReceivable='Receivable'), (Q(Revision_no=0) | Q(Revision_no__isnull=True)) ).order_by('Fin_year', 'Week_no', 'Entity').values('Fin_year', 'Week_no', 'Entity', 'Final_charges', 'Fin_code', 'id'), columns=['Fin_year', 'Week_no', 'Entity', 'Final_charges', 'Fin_code', 'id'])
                globals()[final_var] = trasnformFinalReceivables(receivables_df,status)

            else:
                globals()[final_var] = []
        

        # theser are Partial DIsbursed weeks
        prev_wk_models = [
            (DSMReceivables, 'dsm_prevwk_status',   'dsm_prevwk_rcvd_list' ,'final_dsm_receivables','DSM'),
            (NetASReceivables, 'net_as_prevwk_status', 'net_as_prevwk_rcvd_list','final_net_as_receivables','NET_AS'),
            (REACReceivables, 'reac_prevwk_status', 'reac_prevwk_rcvd_list','final_reac_receivables','REAC'),
            (IRReceivables, 'ir_prevwk_status', 'ir_prevwk_rcvd_list','final_ir_receivables','IR'),
            (CONGReceivables, 'cong_prevwk_status', 'cong_prevwk_rcvd_list','final_cong_receivables','CONG')
        ]
        for model, status, final_var , curr_wk,pool_acc in prev_wk_models:
            if not locals()[status]:
                prev_wk_df=transformPoolPrevWeek(model)
                globals()[final_var],globals()[curr_wk] = appendFinalPrevweek(globals()[curr_wk],prev_wk_df,pool_acc)
            else:
                globals()[final_var] = []
        

        #get disbursement priority 
        disbursement_order=list(DisbursementOrder.objects.filter(Q(enddate__isnull=True)|Q(enddate__gte=datetime.now())).values('dsm','net_as','reac','ir','cong'))
        priority_list=[]
        # partially disbursed

       
        if len(partial_dis_status):
            for key,val in disbursement_order[0].items():
                for key2,val2 in partial_dis_status[0].items():
                    if key==key2:
                        # if disbursed then Success else Pending
                        message='Success' if val2  else 'Pending'
                        if key == 'dsm':
                            amount = dsm_disbursed_amount
                        elif key == 'net_as':
                            amount = net_as_disbursed_amount
                        elif key == 'reac':
                            amount = reac_disbursed_amount
                        elif key == 'ir':
                            amount = ir_disbursed_amount
                        else:
                            amount=None
                        # label is to show in front end for User , Priority is order of disbursement 
                        priority_list.append({'label':key , 'priority' :val,'status':message ,'already_disbursed_amount':amount})
        else:
            # fully disbursed , here status changed to 'Success' instead of pending check it
            for key,val in disbursement_order[0].items():
                priority_list.append({'label':key , 'priority' :val,'status':'Pending'})

        priority_list_sorted = sorted(priority_list, key=lambda x: x['priority'])
        # get all disbursed weeks
        disbursed_weeks_lst=list(DisbursementStatus.objects.filter(final_disburse=True).order_by('-Disbursed_date').values_list('Disbursed_date',flat=True))

        # unique Fin_year and Week_no
        dsm_finwk_df=pd.DataFrame(globals()['dsm_prevwk_rcvd_list'])
        if not dsm_finwk_df.empty:
            dsm_duplicate_removal =  dsm_finwk_df[['Fin_year', 'Week_no']].drop_duplicates() 
            dsm_unique_pairs_finwk=dsm_duplicate_removal.values.tolist()
        else:
            dsm_unique_pairs_finwk=[]
        # netas unique fin week
        netas_finwk_df=pd.DataFrame(globals()['net_as_prevwk_rcvd_list'])
        if not netas_finwk_df.empty:
            netas_duplicate_removal =  netas_finwk_df[['Fin_year', 'Week_no']].drop_duplicates() 
            netas_unique_pairs_finwk=netas_duplicate_removal.values.tolist()
        else:
            netas_unique_pairs_finwk=[]
        
        #reac unique fin week
        reac_finwk_df=pd.DataFrame(globals()['reac_prevwk_rcvd_list'])
        if not reac_finwk_df.empty:
            reac_duplicate_removal =  reac_finwk_df[['Fin_year', 'Week_no']].drop_duplicates() 
            reac_unique_pairs_finwk=reac_duplicate_removal.values.tolist()
        else:
            reac_unique_pairs_finwk=[]
        #congestion unique fin week
        cong_finwk_df=pd.DataFrame(globals()['cong_prevwk_rcvd_list'])
        if not cong_finwk_df.empty:
            cong_duplicate_removal =  cong_finwk_df[['Fin_year', 'Week_no']].drop_duplicates() 
            cong_unique_pairs_finwk=cong_duplicate_removal.values.tolist()
        else:
            cong_unique_pairs_finwk=[]


        unique_wk_dict={'dsm':dsm_unique_pairs_finwk ,'net_as':netas_unique_pairs_finwk,'reac':reac_unique_pairs_finwk,'cong':cong_unique_pairs_finwk }
        # get NLDCSplit amount for DSM and NETAS
        nldc_split_qry=list(NLDCPoolAmountSplit.objects.filter(disburse_date=datetime.today() ).values('amount_for_dsm','amount_for_netas','amount_for_reac','is_user_checked'))
        
        if not len(nldc_split_qry):
            nldc_split_qry=[{'amount_for_dsm':0,'amount_for_netas':0,'amount_for_reac':0,'is_user_checked':False}]
        
        nldc_split_qry = getAlreadyDisbursedAmounts(partial_dis_status ,nldc_split_qry)

        return JsonResponse([last_disbursed_date, all_poolaccounts_summary,[
            globals()['final_dsm_receivables'],globals()['final_net_as_receivables'],globals()['final_reac_receivables'] , globals()['final_ir_receivables'],globals()['final_cong_receivables'],  
            
            globals()['dsm_prevwk_rcvd_list'],globals()['net_as_prevwk_rcvd_list'],globals()['reac_prevwk_rcvd_list'] , globals()['ir_prevwk_rcvd_list'] ,globals()['cong_prevwk_rcvd_list']
            ] , partial_dis_status,priority_list_sorted ,disbursed_weeks_lst , unique_wk_dict , nldc_split_qry,remarks,last_st_upload ],safe=False)

    except Exception as e:
      print(e)
      return HttpResponse(extractdb_errormsg(e),status=404)


def transfertoLegacy(request):
    try:
        summary_data = json.loads(request.body)['disburse_summary']
        to_be_transfer = json.loads(request.body)['transfer_to_legacy']
        # get latest record from Disbursement Status

        dis_status = list(DisbursementStatus.objects.filter(final_disburse=True).order_by('-Disbursed_date')[:1].all().values())
        intimate_to_NLDC = list(IntimateNLDC.objects.filter(is_used_indisbursement=False).order_by('-intimate_date').all().values())

        if len(intimate_to_NLDC):    
            return JsonResponse({'status' : False , 'message' :'Please check intimated to NLDC, if anything pending IR should be transfered!! '} , safe=False)
        
        else:
            data = dis_status[0]
            surplus_amt = int(data['Surplus_amt']) - int(to_be_transfer)
            legacy_surplus_amt = int(data['legacy_surplus_amt']) + int(to_be_transfer)
            remarks_1 = dis_status[0]['remarks']
            
            if remarks_1 is None:
                remarks_1 = ' '
            else :
                remarks_1

            DisbursementStatus.objects.filter(id= dis_status[0]['id']).update(
            Surplus_amt = surplus_amt, 
            remarks = remarks_1 +" _Amount of Rs. "+ str(to_be_transfer)+" from main to legacy on "+ datetime.today().strftime("%d-%m-%Y"),
            legacy_surplus_amt = legacy_surplus_amt
            )
            return JsonResponse({'status' : True , 'message' :' Transferred to Legacy from Main account Successfully amount of ₹ '+ str(to_be_transfer)} , safe=False)
    except Exception as e:
      return HttpResponse(extractdb_errormsg(e),status=404)



def transfertoMain(request):
    try:
        summary_data = json.loads(request.body)['disburse_summary']
        to_be_transfer = json.loads(request.body)['transfer_to_legacy']
        # get latest record from Disbursement Status
        dis_status = list(DisbursementStatus.objects.filter(final_disburse=True).order_by('-Disbursed_date')[:1].all().values())
        intimate_to_NLDC = list(IntimateNLDC.objects.filter(is_used_indisbursement=False).order_by('-intimate_date').all().values())
        if len(intimate_to_NLDC):
            return JsonResponse({'status' : False , 'message' :'Please check intimated to NLDC, if anything pending IR should be transfered!! '} , safe=False)
        else :
            data = dis_status[0]

            surplus_amt = int(data['Surplus_amt']) + int(to_be_transfer)
            legacy_surplus_amt_1 = int(data['legacy_surplus_amt']) - int(to_be_transfer)
            remarks_1 = dis_status[0]['remarks']
            if remarks_1 is None:
                remarks_1 = ' '
            else :
                remarks_1

            DisbursementStatus.objects.filter(id= dis_status[0]['id']).update(Surplus_amt = surplus_amt, remarks = remarks_1 +" _Amount of Rs. "+ str(to_be_transfer)+" from Legacy to Main on "+ datetime.today().strftime("%d-%m-%Y"),legacy_surplus_amt = legacy_surplus_amt_1) 
            return JsonResponse({'status' : True , 'message' :' Transferred to Main from Legacy account Successfully amount of ₹'+str(to_be_transfer)} , safe=False)
    except Exception as e:
      return HttpResponse(extractdb_errormsg(e),status=404)






def getDisburseDetails(request):
    try:
        input_data=json.loads(request.body)
      
        #current week entities pending for disbursement , exclude interregional
        base_model_qry=list(DSMBaseModel.objects.filter(Fin_year=input_data['fin_year'] , Week_no=input_data['wk_no'] , PayableorReceivable='Receivable',Legacy_dues=False).exclude(Fin_code__in=['A0077','A0076']).values('id','Entity','Final_charges','Fin_code'))

        for row in base_model_qry:
            row['Receivable_Amount'] = row['Final_charges']

        return JsonResponse([base_model_qry],safe=False)


    except Exception as e:
        return HttpResponse(extractdb_errormsg(e),status=404)
  
def getPaymentsOfCurrentDisburse(payments_model):
    # dsm payables for this disbursement
    payment_df=pd.DataFrame(payments_model.objects.filter(paystatus_fk__Is_disbursed=False).values('paystatus_fk__Fin_year','paystatus_fk__Week_no','paystatus_fk__Entity','paystatus_fk__Final_charges','paystatus_fk__Fin_code','paystatus_fk__id') ,columns=['paystatus_fk__Fin_year','paystatus_fk__Week_no','paystatus_fk__Entity','paystatus_fk__Final_charges','paystatus_fk__Fin_code','paystatus_fk__id'])
    payment_df['payrcv']='P'
    payment_df.rename(columns={'paystatus_fk__Fin_year':'fin_year', 'paystatus_fk__Week_no':'week_no','paystatus_fk__Entity':'entity','paystatus_fk__Final_charges':'final_charges','paystatus_fk__Fin_code':'fin_code' ,'paystatus_fk__id':'id'} ,inplace=True)
    payment_df=payment_df[['fin_year','week_no','entity','final_charges','fin_code','id','payrcv']]

    return payment_df

def updateDisbursementStatus(dis_status_qry,pooltype,status,pool_summary,prev_wk_update_status):
    
    if pooltype == 'DSM':
        collected_amount=round(pool_summary['DSM'],2)
        # here C means Current Week so is_prevwk is False
        if status=='C':
            is_prevwk=False
            # if already status created then update it
            if len(dis_status_qry):
                DisbursementStatus.objects.filter(id=dis_status_qry[0]['id']).update(
                    dsm=True,
                    dsm_prevwk=True,
                    dsm_collected=collected_amount
                )
                unq_id=dis_status_qry[0]['id']
            else:
                # if not create then create it
                dis_stat=DisbursementStatus(
                    Disbursed_date=datetime.today(),
                    dsm=True,
                    dsm_prevwk=True,
                    dsm_collected=collected_amount
                )
                dis_stat.save()
                unq_id=dis_stat.id
        else:
            # this is for previous weeks
            is_prevwk=True
            # if already status created then update it
            if len(dis_status_qry):
                # DisbursementStatus.objects.filter(id=dis_status_qry[0]['id']).update(dsm_prevwk=True)
                unq_id=dis_status_qry[0]['id']
            else:
                # if not create then create it
                dis_stat=DisbursementStatus(
                    Disbursed_date=datetime.today())
                dis_stat.save()
                unq_id=dis_stat.id

        return unq_id,is_prevwk
        # return unq_id,is_prevwk , getPaymentsOfCurrentDisburse(Payments)
    elif pooltype == 'NET_AS':
        collected_amount=round(pool_summary['NET_AS'],2)
        # here C means Current Week so is_prevwk is False
        if status=='C':
            is_prevwk=False
            # if already status created then update it
            if len(dis_status_qry):
                DisbursementStatus.objects.filter(id=dis_status_qry[0]['id']).update(
                    net_as=True,
                    net_as_prevwk=True
                )
                unq_id=dis_status_qry[0]['id']
            else:
                # if not create then create it
                dis_stat=DisbursementStatus(
                    Disbursed_date=datetime.today(),
                    net_as=True,
                    net_as_prevwk=True
                )
                dis_stat.save()
                unq_id=dis_stat.id
        else:
            # this is for previous weeks
            is_prevwk=True
            # if already status created then update it
            if len(dis_status_qry):
                unq_id=dis_status_qry[0]['id']
            else:
                # if not create then create it
                dis_stat=DisbursementStatus(
                    Disbursed_date=datetime.today())
                dis_stat.save()
                unq_id=dis_stat.id

        return unq_id,is_prevwk 
    elif pooltype == 'REAC':
        collected_amount=round(pool_summary['REAC'],2)
        if status == 'C':
            is_prevwk=False
            # if already status created then update it
            if len(dis_status_qry):
                DisbursementStatus.objects.filter(id=dis_status_qry[0]['id']).update(
                    reac=True,reac_prevwk=True,reac_collected=collected_amount)
                unq_id=dis_status_qry[0]['id']
            else:
                # if not create then create it
                dis_stat=DisbursementStatus(
                    Disbursed_date=datetime.today(),
                    reac=True,reac_prevwk=True,reac_collected=collected_amount
                )
                dis_stat.save()
                unq_id=dis_stat.id
        else:
            is_prevwk=True
            # if already status created then update it
            if len(dis_status_qry):
                # DisbursementStatus.objects.filter(id=dis_status_qry[0]['id']).update(
                #    reac_collected=collected_amount)
                unq_id=dis_status_qry[0]['id']
            else:
                # if not create then create it
                dis_stat=DisbursementStatus(
                    Disbursed_date=datetime.today(),
                   reac_collected=collected_amount
                )
                dis_stat.save()
                unq_id=dis_stat.id
        return unq_id,is_prevwk
    
    elif pooltype == 'CONG':
        collected_amount=round(pool_summary['CONG'],2)
        if status == 'C':
            is_prevwk=False
            # if already status created then update it
            if len(dis_status_qry):
                DisbursementStatus.objects.filter(id=dis_status_qry[0]['id']).update(
                    cong=True,cong_prevwk=True)
                unq_id=dis_status_qry[0]['id']
            else:
                # if not create then create it
                dis_stat=DisbursementStatus(
                    Disbursed_date=datetime.today(),
                    cong=True,cong_prevwk=True
                )
                dis_stat.save()
                unq_id=dis_stat.id
        else:
            is_prevwk=True
            # if already status created then update it
            if len(dis_status_qry):
                unq_id=dis_status_qry[0]['id']
            else:
                # if not create then create it
                dis_stat=DisbursementStatus(
                    Disbursed_date=datetime.today())
                dis_stat.save()
                unq_id=dis_stat.id
        return unq_id,is_prevwk
    elif pooltype == 'IR':
        if status == 'C':
            is_prevwk=False
            # if already status created then update it
            if len(dis_status_qry):
                DisbursementStatus.objects.filter(id=dis_status_qry[0]['id']).update(
                    ir=True,ir_prevwk=True)
                unq_id=dis_status_qry[0]['id']
            else:
                # if not create then create it
                dis_stat=DisbursementStatus(
                    Disbursed_date=datetime.today(),
                    ir=True,ir_prevwk=True)
                dis_stat.save()
                unq_id=dis_stat.id
        else:
            is_prevwk=True
            # if already status created then update it
            if len(dis_status_qry):
                unq_id=dis_status_qry[0]['id']
            else:
                # if not create then create it
                dis_stat=DisbursementStatus(
                    Disbursed_date=datetime.today())
                dis_stat.save()
                unq_id=dis_stat.id
        return unq_id,is_prevwk
    
    elif pooltype == 'SRAS':
        collected_amount=round(pool_summary['SRAS'],2)
        if status=='C':
            is_prevwk=False
            # if already status created then update it
            if len(dis_status_qry):
                DisbursementStatus.objects.filter(id=dis_status_qry[0]['id']).update(
                    sras=True,sras_prevwk=True ,sras_collected=collected_amount)
                unq_id=dis_status_qry[0]['id']
            else:
                # if not create then create it
                dis_stat=DisbursementStatus(
                    Disbursed_date=datetime.today(),
                    sras=True,sras_prevwk=True,sras_collected=collected_amount
                )
                dis_stat.save()
                unq_id=dis_stat.id
        else:
            is_prevwk=True
            # if already status created then update it
            if len(dis_status_qry):
                unq_id=dis_status_qry[0]['id']
            else:
                # if not create then create it
                dis_stat=DisbursementStatus(
                    Disbursed_date=datetime.today()
                )
                dis_stat.save()
                unq_id=dis_stat.id
        return unq_id,is_prevwk
    
    elif pooltype == 'TRAS':
        collected_amount=round(pool_summary['TRAS'],2)
        if status == 'C':
            is_prevwk=False
            # if already status created then update it
            if len(dis_status_qry):
                DisbursementStatus.objects.filter(id=dis_status_qry[0]['id']).update(
                    tras=True,tras_prevwk=True,tras_collected=collected_amount)
                unq_id=dis_status_qry[0]['id']
            else:
                # if not create then create it
                dis_stat=DisbursementStatus(
                    Disbursed_date=datetime.today(),
                    tras=True,tras_prevwk=True,tras_collected=collected_amount
                )
                dis_stat.save()
                unq_id=dis_stat.id
        else:
            is_prevwk=True
            # if already status created then update it
            if len(dis_status_qry):
                unq_id=dis_status_qry[0]['id']
            else:
                # if not create then create it
                dis_stat=DisbursementStatus(
                    Disbursed_date=datetime.today())
                dis_stat.save()
                unq_id=dis_stat.id
        return unq_id,is_prevwk 
    elif pooltype == 'MBAS':
        collected_amount=round(pool_summary['MBAS'],2)
        if status == 'C':
            is_prevwk=False
            # if already status created then update it
            if len(dis_status_qry):
                DisbursementStatus.objects.filter(id=dis_status_qry[0]['id']).update(
                    mbas=True,mbas_prevwk=True,mbas_collected=collected_amount)
                unq_id=dis_status_qry[0]['id']
            else:
                # if not create then create it
                dis_stat=DisbursementStatus(
                    Disbursed_date=datetime.today(),
                    mbas=True,mbas_prevwk=True,mbas_collected=collected_amount
                )
                dis_stat.save()
                unq_id=dis_stat.id
        else:
            is_prevwk=True
            # if already status created then update it
            if len(dis_status_qry):
                unq_id=dis_status_qry[0]['id']
            else:
                # if not create then create it
                dis_stat=DisbursementStatus(
                    Disbursed_date=datetime.today())
                dis_stat.save()
                unq_id=dis_stat.id
        return unq_id,is_prevwk
    else:
        payment_df=pd.DataFrame([],columns=['fin_year','week_no','entity','final_charges','fin_code','payrcv'])
        return None,None 
    
def storeDisbursedValues(request):
    try:
        disburse_list=json.loads(request.body)
        disburse_df=pd.DataFrame(disburse_list['selected_rows'],columns=['Fin_year', 'Week_no', 'Entity', 'Final_charges', 'Fin_code', 'id','Disburse_amount'])

       
        dis_status_qry = list(DisbursementStatus.objects.filter(Disbursed_date=disburse_list['partial_status'][0]['Disbursed_date']).all().values()) if len(disburse_list['partial_status']) else []
        pooltype=disburse_list['pooltype'].upper()
        # it decides whether Previous weeks or current week
        status=disburse_list['status']
        # also check the previous week status if it is empty then change dsm_prevweek or sras_prevweek status True though user not selected 
        prev_wk_update_status=True if not disburse_list['prev_week_selected'] else False
     
        unq_id,is_prevwk =updateDisbursementStatus(dis_status_qry,pooltype,status,disburse_list['pool_summary'][0] ,prev_wk_update_status)
       
        # consider only rows which are greater than 0 receivable
        disburse_df=disburse_df[disburse_df['Final_charges'] > 0]
        
        # first store in temporary table before updating the DisbursementStatus
        if not disburse_df.empty:
            disburse_df['payrcv']='R'  #Receivables
            # rename the columns
            disburse_df.rename(columns={'Fin_year':'fin_year', 'Week_no':'week_no','Entity':'entity','Final_charges':'final_charges','Fin_code':'fin_code'} ,inplace=True)
            # drop columns , here Disburse_amount is the Amount Left or Amount as per SRPC that we dont need here
            disburse_df.drop(columns=['Disburse_amount'],inplace=True)
          
            disburse_df['pool_acctype']=pooltype
            disburse_df['disstatus_fk_id']=unq_id
            disburse_df['is_prevweeks']=is_prevwk
            # again rename id to parent_tableid
            disburse_df.rename(columns={'id':'parent_table_id'},inplace=True)
            
            # check if already present delete and push  ['disstatus_fk_id'].unique()
            for _,row in disburse_df.iterrows():
                DisbursedEntities.objects.filter(pool_acctype=pooltype,fin_year=row['fin_year'],week_no=row['week_no'],entity=row['entity'],is_prevweeks=is_prevwk).delete()
            # reorder the columns
            disburse_df=disburse_df[['fin_year','week_no','entity','final_charges','pool_acctype','disstatus_fk_id','fin_code','payrcv','is_prevweeks','parent_table_id']]
            with engine.connect() as connection:
                disburse_df.to_sql('disbursed_entities', connection, if_exists='append',index=False)  

        # now update that this week is disbursed by user but not the final disbursement
        if len(disburse_list['finwk_selected']):
            try:
                TempDisbursedWeeks(
                    pool_acctype=pooltype,
                    fin_year=disburse_list['finwk_selected'][0],
                    week_no=disburse_list['finwk_selected'][1]
                ).save()
            except Exception as e:

                extractdb_errormsg(e)
                # if already stored then skip , normally this case do not arise

        return JsonResponse('success',safe=False)

    except Exception as e:
        pdb.set_trace()
        return HttpResponse(extractdb_errormsg(e),status=404)

def getPaymentsConsideredForDisbursement(pool_acc,legacy_bills):
    other_qry = Q(Is_disbursed=False)| Q(Is_disbursed__isnull=True)
    #import pdb ; pdb.set_trace()
    if not legacy_bills:
        common_qry=( other_qry ) & Q(paystatus_fk__Legacy_dues=False)
    
        if pool_acc == 'DSM':
            # DSM Payments are approved and  considering in disbursement
            Payments.objects.filter(common_qry).update(Is_disbursed=True)

        elif pool_acc == 'REAC':
            # REAC Payments are approved and  considering in disbursement

            REACPayments.objects.filter(common_qry).update(Is_disbursed=True)

        elif pool_acc == 'Interest':
            # Interest Payments are approved but not considered in disbursement
            InterestPayments.objects.filter(Is_disbursed=False).update(Is_disbursed=True)
        
        elif pool_acc == 'NET_AS':
            # NETAS Payments are approved and  considering in disbursement
            NetASPayments.objects.filter(common_qry).update(Is_disbursed=True)
        
        elif pool_acc == 'CONG':
            # CONGESTION Payments are approved and  considering in disbursement
            CONGPayments.objects.filter(common_qry).update(Is_disbursed=True)
            # base_table_ids=list(CONGPayments.objects.filter(common_qry).values_list('paystatus_fk',flat=True))
            # CONGBaseModel.objects.filter(id__in=base_table_ids).update(Is_disbursed=True)

        elif 'REVISION' in pool_acc:
            # REVISION Payments are approved and  considering in disbursement
            RevisionPayments.objects.filter(other_qry).update(Is_disbursed=True)

        elif pool_acc == 'TRAS':
            # TRAS Payments are approved and  considering in disbursement
            TRASPayments.objects.filter(common_qry).update(Is_disbursed=True)
        
        elif pool_acc == 'MBAS':
            # MBAS Payments are approved and  considering in disbursement
            MBASPayments.objects.filter(common_qry).update(Is_disbursed=True)
        
        elif pool_acc == 'IR':
            # IR Payments are approved and  considering in disbursement
            IRPayments.objects.filter(other_qry).update(Is_disbursed=True)
        
        elif pool_acc == 'SRAS':
            # SRAS Payments are approved and  considering in disbursement
            SRASPayments.objects.filter(common_qry).update(Is_disbursed=True)
        
        elif pool_acc == 'Others':
            # Other Payments are approved and  considering in disbursement
            OtherPayments.objects.filter(Is_disbursed=False).update(Is_disbursed=True)
        elif pool_acc == 'Shortfall':
            ShortfallPayments.objects.filter(Is_disbursed = False).update(Is_disbursed=True)
            
        else:
            pass
    else:
        common_qry=( other_qry ) & Q(paystatus_fk__Legacy_dues=True)
        if pool_acc == 'DSM':
            # DSM Payments are approved and  considering in disbursement
            Payments.objects.filter(common_qry).update(Is_disbursed=True)

        elif pool_acc == 'REAC':
            # REAC Payments are approved and  considering in disbursement
            REACPayments.objects.filter(common_qry).update(Is_disbursed=True)

        elif pool_acc == 'NET_AS':
            # NETAS Payments are approved and  considering in disbursement
            NetASPayments.objects.filter(common_qry).update(Is_disbursed=True)
        elif pool_acc == "Legacy" :
            LegacyPayments.objects.filter(common_qry).update(Is_disbursed=True)

        else: pass

    return 

def finalAccwiseDisbursement(filtered_df , pool_base_model,pool_base_rcvmodel):
    
    pool_qry_obj=pool_base_model.objects.filter(Fin_year__in=filtered_df['fin_year'].unique(),Week_no__in=filtered_df['week_no'].unique())
    pool_rcv_qry_obj=pool_base_rcvmodel.objects.filter(rcvstatus_fk__Fin_year__in=filtered_df['fin_year'].unique(),rcvstatus_fk__Week_no__in=filtered_df['week_no'].unique())
    
    for _,row in filtered_df.iterrows():
        pool_sub_obj=pool_qry_obj.filter(id=row['parent_table_id'])
        # first update Receivables Table
        pool_base_rcvmodel(
            Disbursed_amount=row['final_charges'],
            rcvstatus_fk=pool_base_model.objects.get(id=row['parent_table_id']) ,
            disbursed_date=datetime.today()
        ).save()

        check_amt_disbursed=list(pool_rcv_qry_obj.filter(rcvstatus_fk__id=row['parent_table_id']).values('Disbursed_amount','rcvstatus_fk__Final_charges'))

        disbursed_amt=0
        actual_receivable_srpc=0
        # find amount to be disbursed and actually disbursed
        for item in check_amt_disbursed:
            disbursed_amt+=item['Disbursed_amount']
            actual_receivable_srpc=item['rcvstatus_fk__Final_charges']
        # if full amount disbursed then change Status to 'C'
        if int(disbursed_amt) == int(actual_receivable_srpc):
            pool_sub_obj.update(Is_disbursed=True,Fully_disbursed='C')
        else:
            # disbursed but not done fully
            pool_sub_obj.update(Is_disbursed=True,Fully_disbursed='P')
        
    return 

#after disbursing all Accounts this updates all basemodels .     
def finalDisbursement(request):
    try:
        in_data=json.loads(request.body)
        
        last_dis_date=in_data['last_disbursed_date']
        nldc_split_qry=list(NLDCPoolAmountSplit.objects.filter(disburse_date=datetime.today() ).values('amount_for_dsm','amount_for_netas','amount_for_reac','is_user_checked'))
        legacy_st = nldc_split_qry[0]['is_user_checked']
        
       
        if  last_dis_date:
            last_dis_date_object = datetime.strptime(last_dis_date, "%d-%m-%Y").date()
            # get the current disbursement date based on greater than last_disbursed_date
            dis_status_qry=DisbursementStatus.objects.filter(Disbursed_date__gt=last_dis_date_object)
        else:
            dis_status_qry=DisbursementStatus.objects.all()


        if len(dis_status_qry):
            dis_status=list(dis_status_qry.order_by('Disbursed_date').values('Disbursed_date','dsm','net_as','reac','ir','dsm_prevwk','net_as_prevwk','reac_prevwk','ir_prevwk','Surplus_amt'))
            
            # check all the disbursement status changed to 1 or not
            if (dis_status[0]['dsm'] and dis_status[0]['net_as']  and dis_status[0]['reac'] and dis_status[0]['ir'] and dis_status[0]['dsm_prevwk'] and dis_status[0]['net_as_prevwk'] and dis_status[0]['reac_prevwk'] and dis_status[0]['ir_prevwk']):
                # first do the DSM disbursement
                disbursement_date=dis_status[0]['Disbursed_date']
                dis_entities_df=pd.DataFrame(DisbursedEntities.objects.filter(disstatus_fk__Disbursed_date=disbursement_date ).all().values())

                amount_disbursed_thisdate = dis_entities_df[dis_entities_df['payrcv']=='R']['final_charges'].sum()
                intimate_nldc_qry=IntimateNLDC.objects.filter(is_used_indisbursement=False)

                if not legacy_st :
                    dis_status_prev_wk_legacy=list(DisbursementStatus.objects.filter(Disbursed_date=last_dis_date_object).values_list('legacy_surplus_amt',flat=True) )

                    prev_wk_amount_legacy = dis_status_prev_wk_legacy[0] if len(dis_status_prev_wk_legacy) else 0

                    if len(intimate_nldc_qry):
                        surplus_amount_qry=list(intimate_nldc_qry.values_list('amount_available','transfer_amount'))
                        surplus_amt=0

                        dsm_paid_amount, reac_paid_amount, ir_paid_amount, net_as_paid_amount,interest_paid_amount,rev_paid_amount,cong_paid_amount,other_misc_amount,shortfall_paid_amount = map(poolAccPaidAmount, keys)

                        surplus_amt=dsm_paid_amount+reac_paid_amount+ir_paid_amount+net_as_paid_amount+interest_paid_amount+rev_paid_amount+cong_paid_amount+other_misc_amount+shortfall_paid_amount                   

                        for vals in surplus_amount_qry:
                            surplus_amt+=vals[0]-vals[1]


                    else:
                        # get previous week amount from last disbursed date
                        dis_status_prev_wk=list(DisbursementStatus.objects.filter(Disbursed_date=last_dis_date_object).values_list('Surplus_amt','revision_disbursed') )
                        
                        if len(dis_status_prev_wk): 
                            surplus_amt = dis_status_prev_wk[0][0] if dis_status_prev_wk[0][0] else 0 #if None make it 0
                            revision_disbursed = dis_status_prev_wk[0][1] if dis_status_prev_wk[0][1] else 0
                            prev_wk_amount = surplus_amt - revision_disbursed
                        else: prev_wk_amount = 0
  
                        dsm_paid_amount, reac_paid_amount, ir_paid_amount, net_as_paid_amount,interest_paid_amount,rev_paid_amount,cong_paid_amount,other_misc_amount,shortfall_paid_amount = map(poolAccPaidAmount, keys)

                        surplus_amt=dsm_paid_amount+reac_paid_amount+ir_paid_amount+net_as_paid_amount+interest_paid_amount+rev_paid_amount+cong_paid_amount+other_misc_amount+prev_wk_amount+shortfall_paid_amount
                        
                    net_amount=surplus_amt-amount_disbursed_thisdate 
                    net_amount = net_amount if net_amount > 0 else 0
                    
                    # get all pool account types
                    all_pool_accs=list(PoolAccountTypes.objects.filter(Q(end_date__isnull=True)|Q(end_date__gte=datetime.now())).values_list('acc_types',flat=True))
                    merged_accs=getMergedAccts()
                    result_accs=[acc for acc in all_pool_accs if acc not in merged_accs ]
                    pool_types = sorted(result_accs)

                    for p_type in pool_types:
                        filtered_df=dis_entities_df[dis_entities_df['pool_acctype']==p_type]
                        if p_type=='DSM':
                            finalAccwiseDisbursement(filtered_df , DSMBaseModel,DSMReceivables)  #Receivables status changer
                        elif p_type=='NET_AS':
                            finalAccwiseDisbursement(filtered_df , NetASBaseModel,NetASReceivables)
                        elif p_type=='REAC':
                            finalAccwiseDisbursement(filtered_df , REACBaseModel,REACReceivables)
                        elif p_type=='SRAS':
                            finalAccwiseDisbursement(filtered_df , SRASBaseModel,SRASReceivables)
                        elif p_type=='TRAS':
                            finalAccwiseDisbursement(filtered_df , TRASBaseModel,TRASReceivables)
                        elif p_type=='MBAS':
                            finalAccwiseDisbursement(filtered_df , MBASBaseModel,MBASReceivables)
                        elif p_type=='IR':
                            finalAccwiseDisbursement(filtered_df , IRBaseModel,IRReceivables)
                        else:
                            pass

                        getPaymentsConsideredForDisbursement(p_type,legacy_st) #Payables status changer
                        
                    # changing final_disburse status to True , parallely update Surplus amount also
                    dis_status_qry.update(final_disburse=True,Surplus_amt=net_amount,legacy_surplus_amt=prev_wk_amount_legacy)
                        # update the Intimate NLDC table
                    intimate_nldc_qry.update(is_used_indisbursement=True)
                    TempDisbursedWeeks.objects.all().delete()
                    return JsonResponse({'status':True , 'message':'Disbursement done Successfully'},safe=False)
                else:
                    dis_status_prev_wk=list(DisbursementStatus.objects.filter(Disbursed_date=last_dis_date_object).values_list('Surplus_amt',flat=True) )

                    if len(dis_status_prev_wk):
                        prev_wk_amount=dis_status_prev_wk[0]
                    else :
                        prev_wk_amount=0
                    dis_status_prev_wk_legacy=list(DisbursementStatus.objects.filter(Disbursed_date=last_dis_date_object).values_list('legacy_surplus_amt',flat=True) )
                    if len(dis_status_prev_wk_legacy) :
                        prev_wk_amount_legacy=dis_status_prev_wk_legacy[0]
                    else :
                        prev_wk_amount_legacy = 0
                    
                    prev_wk_amount_legacy = 0 if prev_wk_amount_legacy is None else prev_wk_amount_legacy

                    legacy_dsm_paid_amount, legacy_reac_paid_amount, legacy_net_as_paid_amount,legacy_paid_amount = map(poolAccLegacyPaidAmount, legacy_keys)

                    surplus_amt = prev_wk_amount_legacy+legacy_dsm_paid_amount+legacy_reac_paid_amount+legacy_net_as_paid_amount+legacy_paid_amount
                    net_amount=surplus_amt-amount_disbursed_thisdate 
                    net_amount = net_amount if net_amount > 0 else 0

                    # get all pool account types
                    all_pool_accs=list(PoolAccountTypes.objects.filter(Q(end_date__isnull=True)|Q(end_date__gte=datetime.now())).values_list('acc_types',flat=True))
                    merged_accs=getMergedAccts()
                    result_accs=[acc for acc in all_pool_accs if acc not in merged_accs ]
                    pool_types = sorted(result_accs)

                    for p_type in pool_types:
                        filtered_df=dis_entities_df[dis_entities_df['pool_acctype']==p_type]
                        if p_type=='DSM':
                            finalAccwiseDisbursement(filtered_df , DSMBaseModel,DSMReceivables)  #Receivables status changer
                        elif p_type=='NET_AS':
                            finalAccwiseDisbursement(filtered_df , NetASBaseModel,NetASReceivables)
                        elif p_type=='REAC':
                            finalAccwiseDisbursement(filtered_df , REACBaseModel,REACReceivables)
                        elif p_type=='SRAS':
                            finalAccwiseDisbursement(filtered_df , SRASBaseModel,SRASReceivables)
                        elif p_type=='TRAS':
                            finalAccwiseDisbursement(filtered_df , TRASBaseModel,TRASReceivables)
                        elif p_type=='MBAS':
                            finalAccwiseDisbursement(filtered_df , MBASBaseModel,MBASReceivables)
                        elif p_type=='IR':
                            finalAccwiseDisbursement(filtered_df , IRBaseModel,IRReceivables)
                        else:continue

                        getPaymentsConsideredForDisbursement(p_type,legacy_st) #Payables status changer
                        # changing final_disburse status to True , parallely update Surplus amount also
                    dis_status_qry.update(final_disburse=True,Surplus_amt=prev_wk_amount,legacy_surplus_amt=net_amount,legacy_status = True , Disbursed_date = datetime.now().date())
                    TempDisbursedWeeks.objects.all().delete()
                    return JsonResponse({'status':True , 'message':'Legacy Disbursement done Successfully'},safe=False)     
            else: 
                return JsonResponse({'status':False , 'message':'Disbursement not completed for all Pool types  , Please complete those first'},safe=False)
        else:
            return JsonResponse({'status':False , 'message':'No pending Disbursements'},safe=False)
        
        
    except Exception as e:
        print(e)
        return HttpResponse(extractdb_errormsg(e),status=404)
    

def revokeDisbursement(request):
    try:
        in_data=json.loads(request.body)
        last_disbursed_date=datetime.strptime(in_data['last_disburse_date'],'%d-%m-%Y').date()
        
        dis_status_qry=DisbursementStatus.objects.filter(Disbursed_date__gte=last_disbursed_date)
        dis_entities=DisbursedEntities.objects.filter(disstatus_fk__Disbursed_date__gte=last_disbursed_date,payrcv='R')

        pool_acc_upper=in_data['selected_row']['label'].upper()
        # delete already temp disbursed weeks alse
        TempDisbursedWeeks.objects.filter(pool_acctype=pool_acc_upper).delete()
        
        if in_data['selected_row']['label'] == 'dsm':
            dis_status_qry.update(
                dsm=False,
                dsm_prevwk=False
            )
        elif in_data['selected_row']['label'] == 'net_as':
            dis_status_qry.update(
                net_as=False,
                net_as_prevwk=False
            )   
        elif in_data['selected_row']['label'] == 'reac':
            dis_status_qry.update(
                reac=False,
                reac_prevwk=False
            )
        elif in_data['selected_row']['label'] == 'cong':
            dis_status_qry.update(
                cong=False,
                cong_prevwk=False
            )
        elif in_data['selected_row']['label'] == 'ir':
            dis_status_qry.update(
                ir=False,
                ir_prevwk=False
            )
        else:
            pass
        dis_entities.filter(pool_acctype=pool_acc_upper).delete()
        return JsonResponse('Disbursement Revoked Successfully' , safe=False)
    except Exception as e:
        return HttpResponse(extractdb_errormsg(e),status=404)