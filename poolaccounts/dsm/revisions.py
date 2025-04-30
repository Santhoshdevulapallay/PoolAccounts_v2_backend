
import numpy as np ,os
from dsm.common import getWeekDates,getFincode,add530hrstoDateString,removeSpaceDf,getAllPoolAccs,checkLegacyStatus,format_indian_currency,getFeesChargesName
from dsm.reports import getCalSum
from poolaccounts.settings import BASE_DIR
from .engine_create import *
from registration.extarctdb_errors import extractdb_errormsg
from django.http import FileResponse, HttpResponse , JsonResponse
import json,pdb ,pandas as pd
from .models import *
from django.db.models import Max
from datetime import timedelta
from datetime import datetime
from docxtpl import DocxTemplate
from docx2pdf import convert
from poolaccounts.settings import base_dir
from django.db import connection, transaction, DatabaseError
from django.db.models import Q

def getRevisionInterestUniqueDates():
    try:
        # get revision bill dates
        revision_interest_dates=[]
        # contains only revision account types
        pool_acct_types=list(PoolAccountTypes.objects.filter(Q(end_date__isnull=True) | Q(end_date__gte=timezone.now() )).exclude(~Q(acc_types__contains='REVISION')).values_list('acc_types' , flat=True) )

        for acc in pool_acct_types:
                letter_dates=list(RevisionBaseModel.objects.filter(Acc_type=acc).distinct('Letter_date').order_by('Letter_date').values_list('Letter_date',flat=True))
                revision_interest_dates.append({acc:letter_dates})
        # Interest bill date
        interest_dates=list(InterestBaseModel.objects.distinct('Letter_date').order_by('Letter_date').values_list('Letter_date',flat=True))
        revision_interest_dates.append({'Interest':interest_dates})

        return revision_interest_dates
    except Exception as e:
        extractdb_errormsg(e)
        return revision_interest_dates

def readDSMRevisionFile(df):
    try:
        # Find the index of rows containing 'Entity'
        entity_indices = df.index[df['Entity'] == 'Entity'].tolist()
        # Split the DataFrame based on the 'Entity' rows
        dfs_list = []
        start_idx = 0
        for idx in entity_indices:
            dfs_list.append(pd.DataFrame(df.iloc[start_idx:idx]))
            start_idx = idx 
        # this appends last entity table may be infirm power
        dfs_list.append(pd.DataFrame(df.iloc[start_idx:] ) )
        count=0
        infirm_table_df=pd.DataFrame([])
        final_states_gen_list=pd.DataFrame([])
        
        for in_df in dfs_list:
            # drop NaN columns specially for InterRegional df
            in_df = in_df.dropna(axis=1,how='all') # Specify 'how' parameter to 'all' to drop columns containing all NaN values
            #*****Now this is for state and generators
            # States Part
            if count == 0:
                in_df.columns =removeSpaceDf(in_df)
                # Drop rows with NaN values in 'PayableToPool/ReceviableFromPool' column
                # names changes from Entityt:E, UnderdrawlCharges(Rs):U ,OverdrawlCharges(Rs):O
                in_df.columns=['E','U','O','Po','F','P']
                in_df = in_df.dropna(subset=['P'])
                in_df=in_df[['E','F','P']]
                # rename the columns and append to dataframe
                in_df.rename(columns={'F':'DevFinal' ,'P':'PayRcv'},inplace=True)
                final_states_gen_list=pd.concat([final_states_gen_list ,in_df]) 
            elif count == 1:
                # CGS Part
                # changing the header 
                in_df.columns = in_df.iloc[0] 
                # skipping the first row , because it contains header only that we moved up
                in_df=in_df.iloc[1: ]
                in_df.columns = removeSpaceDf(in_df)
                # names changes from Entityt:E, UnderdrawlCharges(Rs):U ,OverdrawlCharges(Rs):O
                in_df.columns=['E','O','U','C','F','P']
                # Drop rows with NaN values in 'PayableToPool/ReceviableFromPool' column
                in_df = in_df.dropna(subset=['P'])
                in_df=in_df[['E','F','P']]
                # rename the columns and append to dataframe
                in_df.rename(columns={'F':'DevFinal' ,'P':'PayRcv'},inplace=True)
                final_states_gen_list=pd.concat([final_states_gen_list ,in_df]) 
            elif count == 2:
                pass
            elif count == 3:
                # Infirm drawl power
                in_df.columns = in_df.iloc[0] 
                # skipping the first row , because it contains header only that we moved up
                in_df=in_df.iloc[1: ]
                in_df.columns = removeSpaceDf(in_df)
                # names changed Entity:E ,DeviationEnergy:D , FinalCharges(Rs):F ..
                in_df.columns = ['E', 'D', 'F', 'P']
                # Drop rows with NaN values in 'Payable/Receviable' column
                in_df = in_df.dropna(subset=['P'])
                in_df=in_df[['E','F','P']]
                # rename the columns and append to dataframe
                in_df.rename(columns={'F':'DevFinal' ,'P':'PayRcv'},inplace=True)

                # dont push to database if DevFinal contains 0 , **simply drop it
                in_df['DevFinal'] = pd.to_numeric(in_df['DevFinal'], errors='coerce')
                # Drop rows where 'DevFinal' column contains 0
                in_df = in_df[in_df['DevFinal'] != 0]
                # replace values also 
                in_df['PayRcv'] = in_df['PayRcv'].replace('Payable to Pool', 'Payable')
                in_df['PayRcv'] = in_df['PayRcv'].replace('Receivable from Pool', 'Receivable')
                
                # assign infirm drawl entities to infirm_table_df for temporarily
                infirm_table_df=in_df.copy()
                infirm_table_df=infirm_table_df.fillna(0)
                final_states_gen_list=pd.concat([final_states_gen_list ,infirm_table_df]) 
            else:
                pass
            count+=1
        
        return final_states_gen_list
    except Exception as e:
        print(e)
    
def readREACRevisionFile(df):
    # Find the index of rows containing 'Entity'
    entity_indices = df.index[df['Entity'] == 'Entity'].tolist()
    # Split the DataFrame based on the 'Entity' rows
    dfs_list = []
    start_idx = 0
    for idx in entity_indices:
        dfs_list.append(pd.DataFrame(df.iloc[start_idx:idx]))
        start_idx = idx 
    # this appends last entity table may be infirm power
    dfs_list.append(pd.DataFrame(df.iloc[start_idx:] ) )
    count=0
    infirm_table_df=pd.DataFrame([])
    final_states_gen_list=pd.DataFrame([])
    
    for in_df in dfs_list:
        # drop NaN columns specially for InterRegional df
        in_df = in_df.dropna(axis=1,how='all') # Specify 'how' parameter to 'all' to drop columns containing all NaN values
        #*****Now this is for state and generators
        # States Part
        if count == 0:
            in_df.columns =removeSpaceDf(in_df)
            # Drop rows with NaN values in 'PayableToPool/ReceviableFromPool' column
            # names changes from Entityt:E, UnderdrawlCharges(Rs):U ,OverdrawlCharges(Rs):O
            in_df.columns=['E','U','O','Po','F','P']
            in_df = in_df.dropna(subset=['P'])
            in_df=in_df[['E','F','P']]
            # rename the columns and append to dataframe
            in_df.rename(columns={'F':'DevFinal' ,'P':'PayRcv'},inplace=True)
            final_states_gen_list=pd.concat([final_states_gen_list ,in_df]) 
        elif count == 1:
            # CGS Part
            # changing the header 
            in_df.columns = in_df.iloc[0] 
            # skipping the first row , because it contains header only that we moved up
            in_df=in_df.iloc[1: ]
            in_df.columns = removeSpaceDf(in_df)
            # names changes from Entityt:E, UnderdrawlCharges(Rs):U ,OverdrawlCharges(Rs):O
            in_df.columns=['E','O','U','C','F','P']
            # Drop rows with NaN values in 'PayableToPool/ReceviableFromPool' column
            in_df = in_df.dropna(subset=['P'])
            in_df=in_df[['E','F','P']]
            # rename the columns and append to dataframe
            in_df.rename(columns={'F':'DevFinal' ,'P':'PayRcv'},inplace=True)
            final_states_gen_list=pd.concat([final_states_gen_list ,in_df]) 
        
        elif count == 2:
            # Infirm drawl power
            in_df.columns = in_df.iloc[0] 
            # skipping the first row , because it contains header only that we moved up
            in_df=in_df.iloc[1: ]
            in_df.columns = removeSpaceDf(in_df)
            # names changed Entity:E ,DeviationEnergy:D , FinalCharges(Rs):F ..
            in_df.columns = ['E', 'D', 'F', 'P']
            # Drop rows with NaN values in 'Payable/Receviable' column
            in_df = in_df.dropna(subset=['P'])
            in_df=in_df[['E','F','P']]
            # rename the columns and append to dataframe
            in_df.rename(columns={'F':'DevFinal' ,'P':'PayRcv'},inplace=True)

            # dont push to database if DevFinal contains 0 , **simply drop it
            in_df['DevFinal'] = pd.to_numeric(in_df['DevFinal'], errors='coerce')
            # Drop rows where 'DevFinal' column contains 0
            in_df = in_df[in_df['DevFinal'] != 0]
            # replace values also 
            in_df['PayRcv'] = in_df['PayRcv'].replace('Payable to Pool', 'Payable')
            in_df['PayRcv'] = in_df['PayRcv'].replace('Receivable from Pool', 'Receivable')
            
            # assign infirm drawl entities to infirm_table_df for temporarily
            infirm_table_df=in_df.copy()
            infirm_table_df=infirm_table_df.fillna(0)
            final_states_gen_list=pd.concat([final_states_gen_list ,infirm_table_df]) 
        else:
            pass
        count+=1
    
    return final_states_gen_list
    
def getWeekMaxRevision(request):
    try:
        in_data=json.loads(request.body)['formdata']
        fin_year=in_data['fin_year']
        wk_no=in_data['wk_no']

        week_start_date,week_end_date=getWeekDates(fin_year,wk_no)
        entity_list = []

        if in_data['acc_type'] =='DSM':
            dsm_base_model_obj = DSMBaseModel.objects.filter(Fin_year=in_data['fin_year'],Week_no=in_data['wk_no'])
            max_revision=dsm_base_model_obj.aggregate(Max('Revision_no'))['Revision_no__max']
            
            try:
                next_revision=max_revision+1
            except:
                next_revision=0
        
            entity_df = pd.DataFrame(dsm_base_model_obj.filter(Effective_end_date__isnull = True).order_by('Entity').values('id','Entity','Fin_code','Final_charges','PayableorReceivable') , columns= ['id','Entity','Fin_code','Final_charges','PayableorReceivable'])
            entity_df['Revised_charges'] = 0
            entity_df['RevisedPayableorReceivable'] = '' 

        if in_data['acc_type'] =='NET_AS':
            dsm_base_model_obj = NetASBaseModel.objects.filter(Fin_year=in_data['fin_year'],Week_no=in_data['wk_no'])
            max_revision=dsm_base_model_obj.aggregate(Max('Revision_no'))['Revision_no__max']
            
            try:
                next_revision=max_revision+1
            except:
                next_revision=0
        
            entity_df = pd.DataFrame(dsm_base_model_obj.filter(Effective_end_date__isnull = True).order_by('Entity').values('id','Entity','Fin_code','Final_charges','PayableorReceivable') , columns= ['id','Entity','Fin_code','Final_charges','PayableorReceivable'])
            entity_df['Revised_charges'] = 0
            entity_df['RevisedPayableorReceivable'] = '' 
         
        return JsonResponse({'next_revision':next_revision,'week_start_date':week_start_date,'week_end_date':week_end_date , 'entity_list':entity_df.to_dict(orient = 'records')},safe=False)
    
    except Exception as e:
        return HttpResponse(extractdb_errormsg(e),status=400)

def changeNameToFeesCharges(df , all_users):
    try:
        for index , row in df.iterrows():
                check_ent_exists = all_users.filter( Q(fees_charges_name=row['Entity']) | Q(dsm_name=row['Entity']) | Q(sras_name=row['Entity']) | Q(tras_name=row['Entity']) | Q(react_name=row['Entity']))

                if  check_ent_exists.count() :
                    # map the corresponding fin_code also
                    fees_charges_qry=list(check_ent_exists.values_list('fees_charges_name',flat=True))
                    df.loc[index ,'Entity']=fees_charges_qry[0]
        return df
    except :
        return None

def getRevisionCheckBills(request):
    try:
        formdata=json.loads(request.POST['formdata'])
        fin_year=formdata['fin_year']
        week_no=formdata['wk_no']
        srpc_df=pd.read_csv(request.FILES['files'])

        if formdata['acc_type'] == 'DSM':
            revised_df=readDSMRevisionFile(srpc_df) 

            # first remove , from DevFinal
            revised_df['DevFinal']=revised_df['DevFinal'].apply(lambda x:str(x).replace(',',''))
            revised_df.sort_values(['E'],inplace=True)
            # legacy_dues = checkLegacyStatus(fin_year,week_no)
            # import pdb ; pdb.set_trace()
            dsm_df=pd.DataFrame(DSMBaseModel.objects.filter(Fin_year=fin_year,Week_no=week_no).values('Entity','Final_charges','PayableorReceivable'), columns=['Entity','Final_charges','PayableorReceivable'])
            dsm_df['Final_charges'] = dsm_df['Final_charges'].astype(float)
            # Rename columns for consistency
            revised_df = revised_df.rename(columns={'E': 'Entity', 'DevFinal': 'Final_charges','PayRcv':'PayableorReceivable'})
            # Ensure both columns to compare are of the same type
            revised_df['Final_charges'] = revised_df['Final_charges'].astype(float)
            # change DSMName to Fees and Charges Name
            # get all users 
            all_users=Registration.objects.filter(Q(end_date__isnull=True)|Q(end_date__gte=timezone.now()))

            revised_df = changeNameToFeesCharges(revised_df , all_users)
            dsm_df = changeNameToFeesCharges(dsm_df , all_users)

            
            # Merge the DataFrames to find non-matching rows
            merged_df = pd.merge(revised_df, dsm_df, on=['Entity', 'Final_charges','PayableorReceivable'], how='left', indicator=True)
            # Filter to get rows that do not match
            non_matching_rows = merged_df[merged_df['_merge'] == 'left_only']
            # Drop the merge indicator column
            non_matching_rows = non_matching_rows.drop(columns=['_merge'])
            # now drop those rows greater than 0
            non_matching_rows=non_matching_rows[non_matching_rows['Final_charges']>0]
            # replace Nan with empty
            non_matching_rows.fillna('')
            return JsonResponse(non_matching_rows.to_dict(orient='records'),safe=False)
    
    except Exception as e:
        
        return HttpResponse(extractdb_errormsg(e),status=400)

def getRevisionCheckBillsUserEntry(request):
    try:
        formdata=json.loads(request.POST['formdata'])
        fin_year = formdata['fin_year']
        week_no = formdata['wk_no']

        tabledata_df = pd.DataFrame(json.loads(request.POST['table_data']))

        if not tabledata_df.empty:
            # Filter rows where 'PayableorReceivable' is not empty and 'Revised_charges' > 0
            resulted_df = tabledata_df[(tabledata_df["PayableorReceivable"] != "") & (tabledata_df["Revised_charges"] > 0)]
        else:
            resulted_df = pd.DataFrame([])
        
        return JsonResponse(resulted_df.to_dict(orient='records'),safe=False)
    
    except Exception as e:
        print(e)
        return HttpResponse(extractdb_errormsg(e),status=400)



def saveRevisionBill(request):
    try:
        indata=json.loads(request.body)
        formdata=indata['formdata']
        effective_start_date=add530hrstoDateString(formdata['revision_date']).date()
        prev_end_date=effective_start_date-timedelta(days=1)
        table_data=indata['server_res']
        if formdata['acc_type'] == 'DSM':
            dsm_obj=DSMBaseModel.objects.filter(Fin_year=formdata['fin_year'],Week_no=formdata['wk_no'],Effective_end_date__isnull =True)

            for row in table_data:
                fin_code=getFincode(row['Entity'])
                # first get the old record
                old_record=list(dsm_obj.filter(Fin_code=row['Fin_code'] ,  PayableorReceivable = row['PayableorReceivable'],id=row['id']).all().values())
                # first update Effective_end_date of existing record
                dsm_obj.filter(Fin_code=row['Fin_code'],id=row['id']).update(Effective_end_date=prev_end_date)
                # create new record with same old data little change
                if len(old_record):
                    temp_dict=dict(old_record[0])
                    del temp_dict['id']
                    # temp_df=pd.DataFrame(old_record)
                    # temp_df['Effective_start_date']=effective_start_date
                    # temp_df['Effective_end_date']=None
                    # temp_df['Letter_date']=effective_start_date
                    # temp_df['Due_date']=None
                    # temp_df['Disbursement_date']=None
                    # temp_df['Lc_date']=None
                    # temp_df['Interest_levydate']=None
                    # temp_df['Is_disbursed']=False
                    # temp_df['Fully_disbursed']=None
                    # temp_df['Revision_no']=formdata['revision_no']
                    # temp_df['Final_charges']=row['Final_charges']
                    # temp_df['PayableorReceivable']=row['PayableorReceivable']
                    # temp_df['Remarks']=formdata['remarks']

                    temp_dict['Effective_start_date']=effective_start_date
                    temp_dict['Effective_end_date']=None
                    temp_dict['Letter_date']=effective_start_date
                    temp_dict['Due_date']=None
                    temp_dict['Disbursement_date']=None
                    temp_dict['Lc_date']=None
                    temp_dict['Interest_levydate']=None
                    temp_dict['Is_disbursed']=False
                    temp_dict['Fully_disbursed']=None
                    temp_dict['Revision_no']=formdata['revision_no']
                    temp_dict['Final_charges']=row['Revised_charges']
                    temp_dict['PayableorReceivable']=row['RevisedPayableorReceivable']
                    temp_dict['Remarks']=formdata['remarks']
                    new_record=DSMBaseModel.objects.create(**temp_dict)
                    # now change the existing paid_amount mapping to new record
                    Payments.objects.filter(paystatus_fk=row['id']).update(paystatus_fk=new_record)
                    DSMReceivables.objects.filter(rcvstatus_fk=row['id']).update(rcvstatus_fk=new_record)
                    # final_dsm_df=pd.concat([final_dsm_df,temp_df])            
            
        return JsonResponse([],safe=False)
    
    except Exception as e:
        
        return HttpResponse(extractdb_errormsg(e),status=400)
    

def getAllRevisionDates(request):
    try:
        pool_accs=getAllPoolAccs()
        filtered_pool_accs = [item for item in pool_accs if 'REVISION' in item]

        #now get the old revision dates for 3 pool accounts
        dsm_revision_dates=list(DSMBaseModel.objects.filter(Revision_no__gte=1).distinct('Effective_start_date').order_by('-Effective_start_date').values_list('Effective_start_date',flat=True))
        
        reac_revision_dates=list(REACBaseModel.objects.filter(Revision_no__gte=1).distinct('Effective_start_date').order_by('-Effective_start_date').values_list('Effective_start_date',flat=True))

        netas_revision_dates=list(NetASBaseModel.objects.filter(Revision_no__gte=1).distinct('Effective_start_date').order_by('-Effective_start_date').values_list('Effective_start_date',flat=True))

        filtered_dates=set(dsm_revision_dates+reac_revision_dates+netas_revision_dates)
        sorted_list = list(filtered_dates)
        
        return JsonResponse([filtered_pool_accs,sorted_list],safe=False)
    
    except Exception as e:
        return HttpResponse(extractdb_errormsg(e),status=400)

def netRevisionCalc(rev_df):
    try:
        # Group by the specified columns and sum the payments__Paid_amount
        
        grouped_df = rev_df.groupby(['Fin_year', 'Week_no', 'Fin_code']).agg({
            'Entity':'first',
            'Week_startdate': 'first',
            'Week_enddate': 'first',
            'Final_charges' : 'first',
            'PayableorReceivable': 'first',
            'Paid_amount': 'sum',
            'Disbursed_amount': 'sum'
        }).reset_index()
       
        # Apply the transformation
        grouped_df['Final_charges'] = grouped_df.apply(
            lambda row: row['Final_charges'] * -1 if row['PayableorReceivable'] == 'Receivable' else row['Final_charges'],
            axis=1
        )
        
        grouped_df['Paid_amount']=grouped_df['Paid_amount']*-1
        # rev_df['payments__Paid_amount'] = rev_df.apply(
        #     lambda row: row['payments__Paid_amount'] * -1 if row['PayableorReceivable'] == 'Payable' else row['payments__Paid_amount'],
        #     axis=1
        # )
        # rev_df['dsmreceivables__Disbursed_amount'] = rev_df.apply(
        #     lambda row: row['dsmreceivables__Disbursed_amount'] * -1 if row['PayableorReceivable'] == 'Receivable' else row['dsmreceivables__Disbursed_amount'],
        #     axis=1
        # )

        grouped_df['Final_charges'] = grouped_df['Final_charges']+grouped_df['Paid_amount']+grouped_df['Disbursed_amount']
        # Group by 'Entity' and sum the 'Final_charges'
        result_df = grouped_df.groupby('Fin_code').agg({
                    'Final_charges': 'sum',
                    'Entity': 'last'  # or ', '.join if you want all entity names
                }).reset_index()
        # Create the 'PayableorReceivable' column based on 'Final_charges'
        result_df['PayableorReceivable'] = result_df['Final_charges'].apply(
            lambda x: 'Payable' if x > 0 else 'Receivable'
        )
        # Convert all 'Final_charges' values to positive
        result_df['Final_charges'] = result_df['Final_charges'].abs()
        return result_df
    
    except Exception as e:
      
        return pd.DataFrame([])
    
def netRevisionBills(request):
    try:
        formdata=json.loads(request.body)
        common_qry=Q(Letter_date=formdata['revision_date'],Revision_no__gte=1)
        if formdata['acc_type'] == 'DSM_REVISION':
            # get all DSM bills of current selected revision_no
            all_payable_df = pd.DataFrame(DSMBaseModel.objects.filter(common_qry).values('Fin_year','Week_no','Week_startdate','Week_enddate','Entity','Final_charges','PayableorReceivable','Fin_code','payments__Paid_amount') , columns=['Fin_year','Week_no','Week_startdate','Week_enddate','Entity','Final_charges','PayableorReceivable','Fin_code','payments__Paid_amount'])
            all_payable_df['dsmreceivables__Disbursed_amount'] = 0

            all_receivable_df = pd.DataFrame(DSMBaseModel.objects.filter(common_qry).values('Fin_year','Week_no','Week_startdate','Week_enddate','Entity','Final_charges','PayableorReceivable','Fin_code','dsmreceivables__Disbursed_amount') ,columns=['Fin_year','Week_no','Week_startdate','Week_enddate','Entity','Final_charges','PayableorReceivable','Fin_code','dsmreceivables__Disbursed_amount'])
            all_receivable_df['payments__Paid_amount'] = 0

            all_rev_bills_df = pd.concat([all_payable_df ,all_receivable_df])
            
            all_rev_bills_df.rename(columns={'payments__Paid_amount':'Paid_amount','dsmreceivables__Disbursed_amount':'Disbursed_amount'},inplace=True)

        elif formdata['acc_type'] == 'REAC_REVISION':
            # get all DSM bills of current selected revision_no
            all_payable_df=pd.DataFrame(REACBaseModel.objects.filter(common_qry).values('Fin_year','Week_no','Week_startdate','Week_enddate','Entity','Final_charges','PayableorReceivable','Fin_code','reacpayments__Paid_amount'),columns=['Fin_year','Week_no','Week_startdate','Week_enddate','Entity', 'Final_charges', 'PayableorReceivable','Fin_code','reacpayments__Paid_amount'])
            all_payable_df['reacreceivables__Disbursed_amount'] = 0
            
            all_receivable_df=pd.DataFrame(REACBaseModel.objects.filter(common_qry).values('Fin_year','Week_no','Week_startdate','Week_enddate','Entity','Final_charges','PayableorReceivable','Fin_code'),columns=['Fin_year','Week_no','Week_startdate','Week_enddate','Entity', 'Final_charges', 'PayableorReceivable','Fin_code'])
            all_receivable_df['reacpayments__Paid_amount'] = 0

            all_rev_bills_df = pd.concat([all_payable_df ,all_receivable_df])
            # rename the columns
            all_rev_bills_df.rename(columns={'reacpayments__Paid_amount':'Paid_amount','reacreceivables__Disbursed_amount':'Disbursed_amount'},inplace=True)

        elif formdata['acc_type'] == 'NETAS_REVISION':
            # get all DSM bills of current selected revision_no
            all_payable_df=pd.DataFrame(NetASBaseModel.objects.filter(common_qry).values('Fin_year','Week_no','Week_startdate','Week_enddate','Entity','Final_charges','PayableorReceivable','Fin_code','netaspayments__Paid_amount'),columns=['Fin_year','Week_no','Week_startdate','Week_enddate','Entity', 'Final_charges', 'PayableorReceivable','Fin_code','netaspayments__Paid_amount'])
            all_payable_df['netasreceivables__Disbursed_amount'] = 0

            all_receivable_df=pd.DataFrame(NetASBaseModel.objects.filter(common_qry).values('Fin_year','Week_no','Week_startdate','Week_enddate','Entity','Final_charges','PayableorReceivable','Fin_code','netasreceivables__Disbursed_amount'),columns=['Fin_year','Week_no','Week_startdate','Week_enddate','Entity', 'Final_charges', 'PayableorReceivable','Fin_code','netasreceivables__Disbursed_amount'])
            all_receivable_df['netaspayments__Paid_amount'] = 0

            all_rev_bills_df = pd.concat([all_payable_df ,all_receivable_df])
            # rename the columns
            all_rev_bills_df.rename(columns={'netaspayments__Paid_amount':'Paid_amount','netasreceivables__Disbursed_amount':'Disbursed_amount'},inplace=True)

        else:
            return JsonResponse([],safe=False)
        
        #import pdb ; pdb.set_trace()
        all_rev_bills_df['Paid_amount']=all_rev_bills_df['Paid_amount'].fillna(0)
        all_rev_bills_df['Disbursed_amount']=all_rev_bills_df['Disbursed_amount'].fillna(0)
        
        temp_dsm_rev_bills=all_rev_bills_df.copy()
        # remove NaN with empty 
        all_rev_bills_df=all_rev_bills_df.fillna('')
        
        net_rev_df=netRevisionCalc(all_rev_bills_df)
        
        all_rev_bills_df[['Final_charges', 'Paid_amount','Disbursed_amount']] = all_rev_bills_df[['Final_charges', 'Paid_amount','Disbursed_amount']].abs()
        
        net_rev_df.fillna('')
        # modify values according to front end
        final_transform_list=[]
        for _,row in net_rev_df.iterrows():
            sub_bills=temp_dsm_rev_bills[temp_dsm_rev_bills['Fin_code']==row['Fin_code']].to_dict(orient='records')
           
            sub_bills_df=pd.DataFrame(sub_bills).groupby(['Fin_year', 'Week_no', 'Fin_code']).agg({
            'Entity':'first',
            'Week_startdate': 'first',
            'Week_enddate': 'first',
            'Final_charges' : 'mean',
            'PayableorReceivable': 'first',
            'Paid_amount': 'sum',
            'Disbursed_amount': 'sum'
            }).reset_index()
            sub_bills_df['Final_charges'] = sub_bills_df.apply(
                lambda row: row['Final_charges'] * -1 if row['PayableorReceivable'] == 'Receivable' else row['Final_charges'],
                axis=1
            )
            sub_bills_df['Paid_amount']=sub_bills_df['Paid_amount']*-1
            sub_bills_df['Diff_amount'] = sub_bills_df['Final_charges']+sub_bills_df['Paid_amount']+sub_bills_df['Disbursed_amount']
            
            sub_bills_df['Paid_amount'] = sub_bills_df['Paid_amount'].abs()
            sub_bills_df['Final_charges'] = sub_bills_df['Final_charges'].abs()
            sub_bills_df['Disbursed_amount'] = sub_bills_df['Disbursed_amount'].abs()
            sub_bills_df['Diff_amount'] = sub_bills_df['Diff_amount']

            temp_dict=row.to_dict()
            temp_dict['isExpand']=False
            temp_dict['billbreakup']=sub_bills_df.to_dict(orient='records')
            final_transform_list.append(temp_dict)

        
        return JsonResponse([final_transform_list],safe=False)
        
    except Exception as e:
        return HttpResponse(extractdb_errormsg(e),status=400)
    

def downloadRevisionDraftBill(request):
    try:
        request_data=json.loads(request.body)
        formdata=request_data['formdata']
        
        if formdata['acc_type'] == 'DSM_REVISION':
            # get all DSM bills of current selected revision_no
            all_dsm_rev_bills_df=pd.DataFrame(DSMBaseModel.objects.filter(Effective_start_date=formdata['revision_date'],Revision_no__gte=1).values('Fin_year','Week_no','Week_startdate','Week_enddate','Entity','Final_charges','PayableorReceivable','Fin_code','payments__Paid_amount','dsmreceivables__Disbursed_amount'),columns=['Fin_year','Week_no','Week_startdate','Week_enddate','Entity', 'Final_charges', 'PayableorReceivable','Fin_code','payments__Paid_amount','dsmreceivables__Disbursed_amount'])
            
            all_dsm_rev_bills_df.rename(columns={'payments__Paid_amount':'Paid_amount','dsmreceivables__Disbursed_amount':'Disbursed_amount'},inplace=True)
           
            all_dsm_rev_bills_df['Paid_amount']=all_dsm_rev_bills_df['Paid_amount'].fillna(0)
            all_dsm_rev_bills_df['Disbursed_amount']=all_dsm_rev_bills_df['Disbursed_amount'].fillna(0)
          
            all_dsm_rev_bills_df=all_dsm_rev_bills_df.fillna('')
            
            net_rev_df=netRevisionCalc(all_dsm_rev_bills_df)
           
            # all_dsm_rev_bills_df[['Final_charges', 'payments__Paid_amount','dsmreceivables__Disbursed_amount']] = all_dsm_rev_bills_df[['Final_charges', 'payments__Paid_amount','dsmreceivables__Disbursed_amount']].abs()
            
            net_rev_df.fillna('')
        
        parent_folder = os.path.abspath(os.path.join(base_dir, os.pardir))
        directory = os.path.join(parent_folder, 'Files', 'ViewBills' )
            
        in_filename='Revision'+str(formdata['revision_date'])+'.xlsx'
        full_path=os.path.join(directory, in_filename)
        
        #writer = pd.ExcelWriter(full_path, engine='xlsxwriter')
        #net_rev_df.to_excel(writer, sheet_name='Net Bills', index=False)
        #all_dsm_rev_bills_df.to_excel(writer, sheet_name='Week wise', index=False)
        with pd.ExcelWriter(full_path, engine='xlsxwriter') as writer:
            net_rev_df.to_excel(writer, sheet_name='Net Bills', index=False)
            all_dsm_rev_bills_df.to_excel(writer, sheet_name='Week wise', index=False)
            writer.close()
        return FileResponse(open(full_path,'rb'),content_type='text/xlsx')  
    
    except Exception as e:
        
        return HttpResponse(extractdb_errormsg(e),status=400)
    
def storeNetRevisionBills(request):
    try:
        request_data=json.loads(request.body)
        selected_rows=request_data['selected_rows']
        formdata=request_data['formdata']
        # Remove 'billbreakup' key from each dictionary
        for entry in selected_rows:
            del entry['isExpand']
            if 'billbreakup' in entry:
                del entry['billbreakup']
        
        net_entities_df=pd.DataFrame(selected_rows)
        net_entities_df['Letter_date']=formdata['revision_date']
        net_entities_df['Acc_type']=formdata['acc_type']
        net_entities_df['Is_disbursed']=False
        
        try:
            with engine.connect() as connection:
                net_entities_df.to_sql('revision_basemodel', connection, if_exists='append', index=False)
        except Exception as e:
            # Handle specific psycopg2 errors (e.g., unique constraint violation)
            if 'unique constraint' in str(e):
                return JsonResponse({'status': False, 'msg': 'Bills already Submitted Please check .'},safe=False)
            else:
                return JsonResponse({'status': False, 'msg': f'An error occurred while saving data: {str(e)}'},safe=False)

        return JsonResponse({'status':True ,'msg':'Bills Saved Successfully'},safe=False)
    
    except Exception as e:
        return HttpResponse(extractdb_errormsg(e),status=400)

def revisionGenIOM(request):
    try:
        request_data=json.loads(request.body)
        formdata=request_data['formdata']
        revision_date=formdata['revision_date']
        acc_type=formdata['acc_type']
        # get revision bills from base model
        base_qry=RevisionBaseModel.objects.filter(Letter_date=revision_date,Acc_type=acc_type)

        payables_df=pd.DataFrame(base_qry.filter(PayableorReceivable='Payable').values('Letter_date','Entity','Final_charges','Fin_code','id'),columns=['Letter_date','Entity','Final_charges','Fin_code','id'])

        payments_df=pd.DataFrame(RevisionPayments.objects.filter(paystatus_fk__Letter_date=revision_date,paystatus_fk__Acc_type=acc_type).values('Paid_date','Paid_amount','paystatus_fk__Letter_date','Bank_type'),columns=['Paid_date','Paid_amount','paystatus_fk__id','Bank_type'])

        merged_payables_df=pd.merge(payables_df,payments_df,left_on=['id'],right_on=['paystatus_fk__id'],how='left')
        merged_payables_df=merged_payables_df.fillna('')
        # remove columns
        merged_payables_df.drop(columns=['id'],inplace=True)
        all_payables=[]
        for _,row in merged_payables_df.iterrows():
            actual_payable_amt=row['Final_charges']
            paid_amount=row['Paid_amount']
            try:
                duetopool=actual_payable_amt-paid_amount
            except:
                duetopool=actual_payable_amt
            temp_rec=row.to_dict()
            temp_rec['amount_payable']=format_indian_currency(actual_payable_amt)
            temp_rec['paid_date']=row['Paid_date'].strftime('%d-%m-%Y') if row['Paid_date'] else "--"
            temp_rec['Letter_date']=row['Letter_date'].strftime('%d-%m-%Y') if row['Letter_date'] else "--"
            temp_rec['paid_amount']=format_indian_currency(row['Paid_amount'])
            temp_rec['credited_bank']=row['Bank_type']
            temp_rec['duetopool']=format_indian_currency(duetopool)
            all_payables.append(temp_rec)
       
        # ***************** receivables section ****************
        all_receivables=[]
        receivables_df=pd.DataFrame(base_qry.filter(PayableorReceivable='Receivable').values('Letter_date','Entity','Final_charges','Fin_code','id'),columns=['Letter_date','Entity','Final_charges','Fin_code','id'])

        amount_disbursing=0
        # now change the status to Is_disbursed=True
        for _,row in receivables_df.iterrows():
            RevisionBaseModel.objects.filter(id=row['id']).update(Is_disbursed=True,Fully_disbursed='C')
            # make a entry in receivables table also
            try:
                amount_disbursing+=row['Final_charges']
                RevisionReceivables(
                    Disbursed_amount=row['Final_charges'],
                    rcvstatus_fk=RevisionBaseModel.objects.get(id=row['id']),
                    iom_date=revision_date,
                    disbursed_date=datetime.today()
                ).save()
            except: 
                pass
        # get the latest record from disbursement status and update DisbursementStatus
        latest_record=list(DisbursementStatus.objects.order_by('-Disbursed_date')[:1].values('id'))
      
        if latest_record:
            DisbursementStatus.objects.filter(id=latest_record[0]['id']).update(revision_disbursed=amount_disbursing,remarks=
                'The amount disbursed for the revised IOM dated '+revision_date+' for account type '+acc_type+'.')


        for _,row in receivables_df.iterrows():
            temp_rec=row.to_dict()
            temp_rec['Final_charges']=format_indian_currency(temp_rec['Final_charges'])
            temp_rec['duetopool']=format_indian_currency(0)
            # get bank account details
            bank_qry=list(BankDetails.objects.filter(Q(fin_code_fk__fin_code=row['Fin_code']) ,(Q(fin_code_fk__end_date__isnull=True) | Q(fin_code_fk__end_date__gte=datetime.today()) ) ).values('bank_name','bank_account','ifsc_code') )
            temp_rec['Entity']=getFeesChargesName(row['Fin_code'])

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
            all_receivables.append(temp_rec)

        # now generate IOM
        try:
            subject='Disbursement  from DAS Pool Account. / सप्ताह '+' के लिए डीएसएम पूल से संवितरण .' 
        except:
            subject='Disbursement  from DAS Pool Account. / सप्ताह '+'---'

        doc = DocxTemplate("templates/Revision_IOM.docx")

        revision_date_str=datetime.strptime(revision_date,'%Y-%m-%d').strftime('%d-%m-%Y')
        context={
                'iom_date':revision_date_str,
                'subject':subject,
                'acc_type':acc_type,
                'payables':all_payables,
                'totalpayable':getCalSum(all_payables,'amount_payable'),
                'totalpaid':getCalSum(all_payables,'paid_amount'),
                'duetopool':getCalSum(all_payables,'duetopool'),
                'receivables':all_receivables,
                'totalreceived':getCalSum(all_receivables,'Final_charges'),
                'totaldisbursed':getCalSum(all_receivables,'Final_charges'),
                'receivabledue':getCalSum(all_receivables,'duetopool')
            }

        doc.render(context)   
        # all MWH files goes to this folder
        parent_folder = os.path.abspath(os.path.join(base_dir, os.pardir))
        directory = os.path.join(parent_folder, 'IOMS')

        docx_directory=os.path.join(directory,'Docx')

        if not os.path.exists(docx_directory):
                os.makedirs(docx_directory)

        inname_docx=revision_date_str+'_Revision_IOM'+'.docx'
        output_file=os.path.join(docx_directory, inname_docx)
        doc.save(output_file)

        with open(output_file, 'rb') as docx_file:
            response = HttpResponse(docx_file.read(), content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
            response['Content-Disposition'] = 'attachment;'

        return response
    
    except Exception as e:
        # now change the status to Is_disbursed=True
        for _,row in receivables_df.iterrows():
            RevisionBaseModel.objects.filter(id=row['id']).update(Is_disbursed=False,Fully_disbursed='')
            # make a entry in receivables table also
            try:
                RevisionReceivables.objects.filter(
                    Disbursed_amount=row['Final_charges'],
                    rcvstatus_fk=RevisionBaseModel.objects.get(id=row['id'])).delete()
            except: 
                pass

        return HttpResponse(extractdb_errormsg(e),status=400)

def getShortfallUniqueDates():
    try:
        shortfall_dates=list(ShortfallBaseModel.objects.distinct('Letter_date').order_by('Letter_date').values_list('Letter_date',flat=True))
        return shortfall_dates
    except Exception as e:
        extractdb_errormsg(e)
        return []