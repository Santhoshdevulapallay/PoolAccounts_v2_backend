
from dsm.common import getWeekDates , getIRMaxRevision , getWRERCodes ,_create_columns ,format_indian_currency ,currency_to_float,add530hrstoDateString ,getMergedAccts,getFeesChargesName

from registration.extarctdb_errors import extractdb_errormsg
from .models import *
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.http import HttpResponse , JsonResponse
import json ,os ,pandas as pd ,pdb
from .engine_create import *
from django.db.models import Max
from datetime import timedelta , datetime
from django.db.models import F ,Count ,Sum , Q
import numpy as np
import ast

def getParentTableId(subrow,fin_year,week_no):
      try:
            acc_id=None
            if subrow['Acc_type'] == 'SRAS':
                  acc_id=SRASBaseModel.objects.get(Fin_year=fin_year,Week_no=week_no,Fin_code=subrow['Fin_code']).id
            
            elif subrow['Acc_type'] == 'TRAS':
                  acc_id=TRASBaseModel.objects.get(Fin_year=fin_year,Week_no=week_no,Fin_code=subrow['Fin_code']).id

            elif subrow['Acc_type'] == 'MBAS':
                  acc_id=MBASBaseModel.objects.get(Fin_year=fin_year,Week_no=week_no,Fin_code=subrow['Fin_code']).id

            elif subrow['Acc_type'] == 'SCUC':
                  acc_id=SCUCBaseModel.objects.get(Fin_year=fin_year,Week_no=week_no,Fin_code=subrow['Fin_code']).id
            else: 
                  pass    
      except Exception as e:
            extractdb_errormsg(e)

      return acc_id
            
def temporaryBills(request):
      try:
            request_data =json.loads(request.body)
            fin_year=request_data['formdata']['fin_year']
            week_no=request_data['formdata']['wk_no']
            acc_type = request_data['formdata']['acc_type']
            #if it is NET 
            if acc_type == 'NET_AS':
                  merged_accs=getMergedAccts()
                  merged_df=pd.DataFrame(TemporaryMatched.objects.filter(Fin_year=fin_year , Week_no = week_no, Acc_type__in=merged_accs ).order_by('Entity').all().values())
                 
                  # Update DevFinal based on PayRcv condition using a lambda function
                  merged_df['DevFinal'] = merged_df.apply(lambda row: float(row['DevFinal']) if row['PayRcv'] == 'Payable' else -1* float(row['DevFinal']), axis=1)
                  # no longer needed
                  merged_df.drop(columns=['PayRcv','Revision_no','Is_infirm'],inplace=True)
                  final_entities=[]
                  # using fin_code change name to fees&charges name
                  # for index,row in merged_df.iterrows():
                  #       # Get fees and charges name
                  #       merged_df.loc[index, 'Entity'] = getFeesChargesName(row['Fin_code'])
                        
                  for entity_name in merged_df['Entity'].unique():
                        temp_df= merged_df[merged_df['Entity'] == entity_name]
                        net_amount=0
                        temp_dict={
                              'Fin_year':fin_year,
                              'Week_no':week_no,
                              'Entity':'',
                              'Fin_code':'',
                              'DevFinal':'',
                              'PayRcv':'',
                              'SRAS_id':None,
                              'TRAS_id':None,
                              'MBAS_id':None,
                              'SCUC_id':None
                              }
                        for _,subrow in temp_df.iterrows():
                              temp_dict['Entity']=subrow['Entity']
                              temp_dict['Fin_code']=subrow['Fin_code']
                              net_amount+=subrow['DevFinal']

                              if subrow['Acc_type'] == 'SRAS':
                                    temp_dict['SRAS_id']=getParentTableId(subrow,fin_year,week_no)

                              if subrow['Acc_type'] == 'TRAS':
                                    temp_dict['TRAS_id']=getParentTableId(subrow,fin_year,week_no)

                              if subrow['Acc_type'] == 'MBAS':
                                    temp_dict['MBAS_id']=getParentTableId(subrow,fin_year,week_no)

                              if subrow['Acc_type'] == 'SCUC':
                                    temp_dict['SCUC_id']=getParentTableId(subrow,fin_year,week_no)

                        net_status = 'Payable' if net_amount > 0 else 'Receivable'
                        temp_dict['DevFinal']=net_amount
                        temp_dict['PayRcv']=net_status
                        final_entities.append(temp_dict)
                  
                  final_entities_df=pd.DataFrame(final_entities)
                  # replace NaN with empty string
                  final_entities_df=final_entities_df.fillna('') 
                  # calculating total amount before changing the Receivable sign
                  total_amount_to_pool = final_entities_df['DevFinal'].sum() if not final_entities_df.empty else 0

                  final_entities_df['DevFinal'] = final_entities_df.apply(lambda row: float(row['DevFinal']) if row['PayRcv'] == 'Payable' else -1* float(row['DevFinal']), axis=1)

                  final_entities_df.sort_values('Entity',inplace=True)
                  
                  final_entities_df['DevFinal']=final_entities_df['DevFinal'].apply(lambda x:format_indian_currency(x))
                  
                  return JsonResponse([final_entities_df.to_dict(orient='records') , [] , total_amount_to_pool] , safe=False) 
           
            # this section handles all other pool account types
            get_bills_qry =list(TemporaryMatched.objects.filter(Fin_year=fin_year , Week_no = week_no, Acc_type=acc_type ).order_by('Entity').all().values() )
            get_bills_df=pd.DataFrame(get_bills_qry,columns=['id', 'Acc_type', 'Fin_year', 'Week_no', 'Entity', 'Fin_code',
                  'DevFinal', 'PayRcv', 'Revision_no', 'Is_infirm']) 
            
            # first convert to numerical from char like 25,566,62
            get_bills_df['DevFinal'] = pd.to_numeric(get_bills_df['DevFinal'].str.replace(',', ''))
            # do calculate sum(Payables) - Sum(Receivables) + ( Sum(WR_SR) + Sum(ER_SR) ) // this is for user validation whether all bills are stored or not
            sum_of_payables = get_bills_df[get_bills_df['PayRcv'] == 'Payable']['DevFinal'].sum()
            sum_of_receivables = get_bills_df[get_bills_df['PayRcv'] == 'Receivable']['DevFinal'].sum()

            inter_regional_net_value=0
            get_interregional_qry=[]

            #**** if it is DSM then only calculate InterRegional for other accounts it is not necessary
            if acc_type == 'DSM':
                  max_wr_revision_no , max_er_revision_no = getIRMaxRevision(fin_year,week_no)
                  get_interregional_qry=list(TemporaryInterRegional.objects.filter(Fin_year=fin_year , Week_no =week_no , WR_Revision_no=max_wr_revision_no , ER_Revision_no=max_er_revision_no ).all().values())
                  get_interregional_df=pd.DataFrame(get_interregional_qry) 
                  try:
                        # Sum of WRSR and ERSR
                        sum_of_WRSR_ERSR = get_interregional_df['WRSR'].fillna(0) + get_interregional_df['ERSR'].fillna(0)
                        inter_regional_net_value=sum_of_WRSR_ERSR.values[0]
                  except : pass

            # now add all values 
            total_amount_to_pool = float(sum_of_payables- sum_of_receivables + inter_regional_net_value)
          
            return JsonResponse([get_bills_qry , get_interregional_qry , total_amount_to_pool] , safe=False)

      except Exception as e:
            return HttpResponse(extractdb_errormsg(e),status=400)


def storeDSMBills(main_bills_df,disbursement_dates_qry,due_date_qry ,acc_type,letter_date,fin_year,week_no):
      try:
            week_start_date,week_end_date = getWeekDates(fin_year,week_no)
            disbursementdays_list=list(disbursement_dates_qry.filter(pool_acc=acc_type).values_list('days',flat=True))
            # get no of days for due date
            duedays_list=list(due_date_qry.values_list('dsm',flat=True))
            dueday_num=duedays_list[0] if len(duedays_list) else None
            disburseday_num=disbursementdays_list[0] if len(disbursementdays_list) else 0

            due_date= letter_date+timedelta(days= dueday_num )
            disbursement_date= letter_date+timedelta(days= disburseday_num )
            
            # drop acc_type column
            main_bills_df.drop(columns=['id','Acc_type'] ,inplace=True)
            
            # convert char to float for DevFinal column
            main_bills_df['DevFinal'] = main_bills_df['DevFinal'].str.replace(',', '').astype(float)

            # Group by 'Fin_code' and aggregate
            #main_bills_df = main_bills_df.groupby(['Fin_code' , 'PayRcv'], as_index=False).agg({
            #'Fin_year': 'first',
            #'Week_no': 'first',
            #'Entity': 'first',
            #'DevFinal': 'sum',
            #'PayRcv': 'first',
            #'Revision_no': 'first',
            #'Is_infirm': 'first'
            #})
            # Separate Payable and Receivable groups
            payable_df = main_bills_df[main_bills_df['PayRcv'] == 'Payable']
            receivable_df = main_bills_df[main_bills_df['PayRcv'] == 'Receivable']

            # Group and aggregate each group
            if not payable_df.empty:
                  payable_df = payable_df.groupby(['Fin_code', 'PayRcv'], as_index=False).agg({
                        'Fin_year': 'first',
                        'Week_no': 'first',
                        'Entity': 'first',
                        'DevFinal': 'sum',  # Summing DevFinal for Payables
                        'PayRcv': 'first',
                        'Revision_no': 'first',
                        'Is_infirm': 'first'
                  })

            if not receivable_df.empty:
                  receivable_df = receivable_df.groupby(['Fin_code', 'PayRcv'], as_index=False).agg({
                        'Fin_year': 'first',
                        'Week_no': 'first',
                        'Entity': 'first',
                        'DevFinal': 'sum',  # Summing DevFinal for Receivables
                        'PayRcv': 'first',
                        'Revision_no': 'first',
                        'Is_infirm': 'first'
                  })

            # Combine grouped and ungrouped data
            main_bills_df = pd.concat([payable_df, receivable_df], ignore_index=True)
            # create blank columns with length of dataframe
            main_bills_df = _create_columns(main_bills_df, [ 'Week_startdate','Week_enddate','Letter_date','Due_date','Disbursement_date','Lc_date','Interest_levydate','Remarks','Effective_start_date'])
            # replace '--' with None
            main_bills_df=main_bills_df.replace('--',None)
            main_bills_df['Week_startdate']=week_start_date
            main_bills_df['Week_enddate']=week_end_date

            # rename columns 
            main_bills_df.rename(columns= {'PayRcv' : 'PayableorReceivable' , 'DevFinal':'Final_charges'} ,inplace=True)
            reorder_columns=['Fin_year','Week_no','Week_startdate','Week_enddate','Letter_date','Due_date','Disbursement_date','Lc_date','Interest_levydate','Entity','Final_charges','PayableorReceivable','Remarks','Fin_code' , 'Revision_no','Is_disbursed','Effective_start_date']

            main_bills_df = main_bills_df.reindex(columns=reorder_columns)
            if not main_bills_df.empty:
                  # may be interregional entered
                  try:
                        main_bills_df['Letter_date']=letter_date
                        main_bills_df['Due_date']=due_date
                        main_bills_df['Disbursement_date']=disbursement_date
                        main_bills_df['Lc_date']=due_date
                        main_bills_df['Interest_levydate']=due_date
                        main_bills_df['Is_disbursed']=False
                        main_bills_df['Effective_start_date']=letter_date
                        ## added leagcy dues columns as false by praharsha korngi on 14.10.2024##
                        main_bills_df['Legacy_dues'] = False

                        with engine.connect() as connection:
                              main_bills_df.to_sql('dsm_basemodel', connection, if_exists='append',index=False)
                        # now update the dsm_bills_upload_status to True
                        YearCalendar.objects.filter(fin_year=fin_year,week_no=week_no).update(
                              dsm_bills_uploaded_status=True) 
                        
                        return JsonResponse({'status':True , 'message': 'DSM Bills are Submitted Successfully' },safe=False)
                  
                  except Exception as e:
                        print(e)
                        return JsonResponse({'status':False , 'message': 'Bills are already submitted , Please check' },safe=False)
                  
      except Exception as e:
            extractdb_errormsg(e)
            return  JsonResponse({'status':False ,'message':str(e) },safe=False)
      
def storeSRASBills(main_bills_df,disbursement_dates_qry,due_date_qry ,acc_type,letter_date,fin_year,week_no):
      try:
            week_start_date,week_end_date = getWeekDates(fin_year,week_no)
            
            disbursementdays_list=list(disbursement_dates_qry.filter(pool_acc=acc_type).values_list('days',flat=True))
            # get no of days for due date
            duedays_list=list(due_date_qry.values_list('sras',flat=True))
            
            dueday_num=duedays_list[0] if len(duedays_list) else None
            disburseday_num=disbursementdays_list[0] if len(disbursementdays_list) else None

            due_date= letter_date+timedelta(days= dueday_num )
            disbursement_date= letter_date+timedelta(days= disburseday_num )
            
            # drop acc_type column
            main_bills_df.drop(columns=['id','Acc_type'] ,inplace=True)

            # Group by 'Fin_code' and aggregate
            main_bills_df = main_bills_df.groupby(['Fin_code', 'PayRcv'], as_index=False).agg({
            'Fin_year': 'first',
            'Week_no': 'first',
            'Entity': 'first',
            'DevFinal': 'sum',
            'PayRcv': 'first',
            'Revision_no': 'first',
            'Is_infirm': 'first'
            })

            # create blank columns with length of dataframe
            main_bills_df = _create_columns(main_bills_df, [ 'Week_startdate','Week_enddate','Letter_date','Due_date','Disbursement_date','Lc_date','Interest_levydate','Remarks'])
            # replace '--' with None
            main_bills_df=main_bills_df.replace('--',None)
            main_bills_df['Week_startdate']=week_start_date
            main_bills_df['Week_enddate']=week_end_date
            # convert char to float for DevFinal column
            main_bills_df['DevFinal'] = main_bills_df['DevFinal'].str.replace(',', '').astype(float)

            # rename columns 
            main_bills_df.rename(columns= {'PayRcv' : 'PayableorReceivable' , 'DevFinal':'Final_charges'} ,inplace=True)
            reorder_columns=['Fin_year','Week_no','Week_startdate','Week_enddate','Letter_date','Due_date','Disbursement_date','Lc_date','Interest_levydate','Entity','Final_charges','PayableorReceivable','Remarks','Fin_code' , 'Revision_no','Is_disbursed']

            main_bills_df = main_bills_df.reindex(columns=reorder_columns)
            if not main_bills_df.empty:
                  # may be interregional entered
                  try:
                        main_bills_df['Letter_date']=letter_date
                        main_bills_df['Due_date']=due_date
                        main_bills_df['Disbursement_date']=disbursement_date
                        main_bills_df['Lc_date']=due_date
                        main_bills_df['Interest_levydate']=due_date
                        main_bills_df['Is_disbursed']=False
                        ## added leagcy dues columns as false by praharsha korngi on 14.10.2024##
                        main_bills_df['Legacy_dues'] = False

                        with engine.connect() as connection:
                              main_bills_df.to_sql('sras_basemodel', connection, if_exists='append',index=False)
                        # now update the dsm_bills_upload_status to True
                        YearCalendar.objects.filter(fin_year=fin_year,week_no=week_no).update(
                              sras_bills_uploaded_status=True)
                        return JsonResponse({'status':True , 'message': 'DSM Bills are Submitted Successfully' },safe=False)
                  
                  except Exception as e:
                        extractdb_errormsg(e)
                        return JsonResponse({'status':False , 'message': 'Bills are already submitted , Please check' },safe=False)
                  
      except Exception as e:
            extractdb_errormsg(e)
            return  JsonResponse({'status':False ,'message':str(e) },safe=False)
      
def storeTRASBills(main_bills_df,disbursement_dates_qry,due_date_qry ,acc_type,letter_date,fin_year,week_no):
      try:
            week_start_date,week_end_date = getWeekDates(fin_year,week_no)
            disbursementdays_list=list(disbursement_dates_qry.filter(pool_acc=acc_type).values_list('days',flat=True))
            # get no of days for due date
            duedays_list=list(due_date_qry.values_list('tras',flat=True))
            dueday_num=duedays_list[0] if len(duedays_list) else None
            disburseday_num=disbursementdays_list[0] if len(disbursementdays_list) else 0

            due_date= letter_date+timedelta(days= dueday_num )
            disbursement_date= letter_date+timedelta(days= disburseday_num )
            
            # drop acc_type column
            main_bills_df.drop(columns=['id','Acc_type'] ,inplace=True)
            # Group by 'Fin_code' and aggregate
            main_bills_df = main_bills_df.groupby(['Fin_code', 'PayRcv'], as_index=False).agg({
            'Fin_year': 'first',
            'Week_no': 'first',
            'Entity': 'first',
            'DevFinal': 'sum',
            'PayRcv': 'first',
            'Revision_no': 'first',
            'Is_infirm': 'first'
            })

            # create blank columns with length of dataframe
            main_bills_df = _create_columns(main_bills_df, [ 'Week_startdate','Week_enddate','Letter_date','Due_date','Disbursement_date','Lc_date','Interest_levydate','Remarks'])
            # replace '--' with None
            main_bills_df=main_bills_df.replace('--',None)
            main_bills_df['Week_startdate']=week_start_date
            main_bills_df['Week_enddate']=week_end_date
            # convert char to float for DevFinal column
            main_bills_df['DevFinal'] = main_bills_df['DevFinal'].str.replace(',', '').astype(float)

            # rename columns 
            main_bills_df.rename(columns= {'PayRcv' : 'PayableorReceivable' , 'DevFinal':'Final_charges'} ,inplace=True)
            reorder_columns=['Fin_year','Week_no','Week_startdate','Week_enddate','Letter_date','Due_date','Disbursement_date','Lc_date','Interest_levydate','Entity','Final_charges','PayableorReceivable','Remarks','Fin_code' , 'Revision_no','Is_disbursed']

            main_bills_df = main_bills_df.reindex(columns=reorder_columns)
            if not main_bills_df.empty:
                  # may be interregional entered
                  try:
                        main_bills_df['Letter_date']=letter_date
                        main_bills_df['Due_date']=due_date
                        main_bills_df['Disbursement_date']=disbursement_date
                        main_bills_df['Lc_date']=due_date
                        main_bills_df['Interest_levydate']=due_date
                        main_bills_df['Is_disbursed']=False
                        ## added leagcy dues columns as false by praharsha korngi on 14.10.2024##
                        main_bills_df['Legacy_dues'] = False

                        with engine.connect() as connection:
                              main_bills_df.to_sql('tras_basemodel', connection, if_exists='append',index=False)
                        # now update the dsm_bills_upload_status to True
                        YearCalendar.objects.filter(fin_year=fin_year,week_no=week_no).update(
                              tras_bills_uploaded_status=True)
                        return JsonResponse({'status':True , 'message': 'TRAS Bills are Submitted Successfully' },safe=False)
                  
                  except Exception as e:
                        extractdb_errormsg(e)
                        return JsonResponse({'status':False , 'message': 'Bills are already submitted , Please check' },safe=False)
                  
      except Exception as e:
            extractdb_errormsg(e)
            return  JsonResponse({'status':False ,'message':str(e) },safe=False)
      
def storeSCUCBills(main_bills_df,disbursement_dates_qry,due_date_qry ,acc_type,letter_date,fin_year,week_no):
      try:
            week_start_date,week_end_date = getWeekDates(fin_year,week_no)
            disbursementdays_list=list(disbursement_dates_qry.filter(pool_acc=acc_type).values_list('days',flat=True))
            # get no of days for due date
            duedays_list=list(due_date_qry.values_list('tras',flat=True))
            dueday_num=duedays_list[0] if len(duedays_list) else None
            disburseday_num=disbursementdays_list[0] if len(disbursementdays_list) else 0

            due_date= letter_date+timedelta(days= dueday_num )
            disbursement_date= letter_date+timedelta(days= disburseday_num )
            
            # drop acc_type column
            main_bills_df.drop(columns=['id','Acc_type'] ,inplace=True)
            # Group by 'Fin_code' and aggregate
            main_bills_df = main_bills_df.groupby(['Fin_code', 'PayRcv'], as_index=False).agg({
            'Fin_year': 'first',
            'Week_no': 'first',
            'Entity': 'first',
            'DevFinal': 'sum',
            'PayRcv': 'first',
            'Revision_no': 'first',
            'Is_infirm': 'first'
            })
            # create blank columns with length of dataframe
            main_bills_df = _create_columns(main_bills_df, [ 'Week_startdate','Week_enddate','Letter_date','Due_date','Disbursement_date','Lc_date','Interest_levydate','Remarks'])
            # replace '--' with None
            main_bills_df=main_bills_df.replace('--',None)
            main_bills_df['Week_startdate']=week_start_date
            main_bills_df['Week_enddate']=week_end_date
            # convert char to float for DevFinal column
            main_bills_df['DevFinal'] = main_bills_df['DevFinal'].str.replace(',', '').astype(float)

            # rename columns 
            main_bills_df.rename(columns= {'PayRcv' : 'PayableorReceivable' , 'DevFinal':'Final_charges'} ,inplace=True)
            reorder_columns=['Fin_year','Week_no','Week_startdate','Week_enddate','Letter_date','Due_date','Disbursement_date','Lc_date','Interest_levydate','Entity','Final_charges','PayableorReceivable','Remarks','Fin_code' , 'Revision_no','Is_disbursed']

            main_bills_df = main_bills_df.reindex(columns=reorder_columns)
            if not main_bills_df.empty:
                  # may be interregional entered
                  try:
                        main_bills_df['Letter_date']=letter_date
                        main_bills_df['Due_date']=due_date
                        main_bills_df['Disbursement_date']=disbursement_date
                        main_bills_df['Lc_date']=due_date
                        main_bills_df['Interest_levydate']=due_date
                        main_bills_df['Is_disbursed']=False
                        ## added leagcy dues columns as false by praharsha korngi on 14.10.2024##
                        main_bills_df['Legacy_dues'] = False
                        with engine.connect() as connection:
                              main_bills_df.to_sql('scuc_basemodel', connection, if_exists='append',index=False)
                        # now update the dsm_bills_upload_status to True
                        YearCalendar.objects.filter(fin_year=fin_year,week_no=week_no).update(
                              scuc_bills_uploaded_status=True)
                        return JsonResponse({'status':True , 'message': 'SCUC Bills are Submitted Successfully' },safe=False)
                  
                  except Exception as e:
                        extractdb_errormsg(e)
                        return JsonResponse({'status':False , 'message': 'Bills are already submitted , Please check' },safe=False)
                  
      except Exception as e:
            extractdb_errormsg(e)
            return  JsonResponse({'status':False ,'message':str(e) },safe=False)
      
def storeMBASBills(main_bills_df,disbursement_dates_qry,due_date_qry ,acc_type,letter_date,fin_year,week_no):
      try:
            if not main_bills_df.empty:
                  week_start_date,week_end_date = getWeekDates(fin_year,week_no)
                  disbursementdays_list=list(disbursement_dates_qry.filter(pool_acc=acc_type).values_list('days',flat=True))
                  # get no of days for due date
                  duedays_list=list(due_date_qry.values_list('mbas',flat=True))
            
                  dueday_num=duedays_list[0] if len(duedays_list) else None
                  disburseday_num=disbursementdays_list[0] if len(disbursementdays_list) else 0
            
                  due_date= letter_date+timedelta(days= dueday_num )
                  disbursement_date= letter_date+timedelta(days= disburseday_num )
                  # drop acc_type column
                  main_bills_df.drop(columns=['id','Acc_type'] ,inplace=True)
                  # Group by 'Fin_code' and aggregate
                  main_bills_df = main_bills_df.groupby(['Fin_code', 'PayRcv'], as_index=False).agg({
                  'Fin_year': 'first',
                  'Week_no': 'first',
                  'Entity': 'first',
                  'DevFinal': 'sum',
                  'PayRcv': 'first',
                  'Revision_no': 'first',
                  'Is_infirm': 'first'
                  })
                  # create blank columns with length of dataframe
                  main_bills_df = _create_columns(main_bills_df, [ 'Week_startdate','Week_enddate','Letter_date','Due_date','Disbursement_date','Lc_date','Interest_levydate','Remarks'])
                  # replace '--' with None
                  main_bills_df=main_bills_df.replace('--',None)
                  main_bills_df['Week_startdate']=week_start_date
                  main_bills_df['Week_enddate']=week_end_date
                  # convert char to float for DevFinal column
                  main_bills_df['DevFinal'] = main_bills_df['DevFinal'].str.replace(',', '').astype(float)

                  # rename columns 
                  main_bills_df.rename(columns= {'PayRcv' : 'PayableorReceivable' , 'DevFinal':'Final_charges'} ,inplace=True)
                  reorder_columns=['Fin_year','Week_no','Week_startdate','Week_enddate','Letter_date','Due_date','Disbursement_date','Lc_date','Interest_levydate','Entity','Final_charges','PayableorReceivable','Remarks','Fin_code' , 'Revision_no','Is_disbursed']

                  main_bills_df = main_bills_df.reindex(columns=reorder_columns)
                  if not main_bills_df.empty:
                        # may be interregional entered
                        try:
                              main_bills_df['Letter_date']=letter_date
                              main_bills_df['Due_date']=due_date
                              main_bills_df['Disbursement_date']=disbursement_date
                              main_bills_df['Lc_date']=due_date
                              main_bills_df['Interest_levydate']=due_date
                              main_bills_df['Is_disbursed']=False
                              ## added leagcy dues columns as false by praharsha korngi on 14.10.2024##
                              main_bills_df['Legacy_dues'] = False

                              with engine.connect() as connection:
                                    main_bills_df.to_sql('mbas_basemodel', connection, if_exists='append',index=False)
                              # now update the dsm_bills_upload_status to True
                              YearCalendar.objects.filter(fin_year=fin_year,week_no=week_no).update(
                                    mbas_bills_uploaded_status=True)
                              return JsonResponse({'status':True , 'message': 'MBAS Bills are Submitted Successfully' },safe=False)
                        
                        except Exception as e:
                              
                              return JsonResponse({'status':False , 'message': 'Bills are already submitted , Please check' },safe=False)
            else :
                  YearCalendar.objects.filter(fin_year=fin_year,week_no=week_no).update(
                                    mbas_bills_uploaded_status=True)
                  return JsonResponse({'status':True , 'message': 'MBAS Bills are Submitted Successfully' },safe=False)
                  
      except Exception as e:
            extractdb_errormsg(e)
            return  JsonResponse({'status':False ,'message':str(e) },safe=False)
      
def storeREACBills(main_bills_df,disbursement_dates_qry,due_date_qry ,acc_type,letter_date,fin_year,week_no):
      try:
            week_start_date,week_end_date = getWeekDates(fin_year,week_no)
            disbursementdays_list=list(disbursement_dates_qry.filter(pool_acc=acc_type).values_list('days',flat=True))
            # get no of days for due date
            duedays_list=list(due_date_qry.values_list('reac',flat=True))
            dueday_num=duedays_list[0] if len(duedays_list) else None
            disburseday_num=disbursementdays_list[0] if len(disbursementdays_list) else None
           
            due_date= letter_date+timedelta(days= dueday_num )
            disbursement_date= letter_date+timedelta(days= disburseday_num )
            
            # drop acc_type column
            main_bills_df.drop(columns=['id','Acc_type'] ,inplace=True)
            # Group by 'Fin_code' and aggregate
            main_bills_df = main_bills_df.groupby(['Fin_code', 'PayRcv'], as_index=False).agg({
            'Fin_year': 'first',
            'Week_no': 'first',
            'Entity': 'first',
            'DevFinal': 'sum',
            'PayRcv': 'first',
            'Revision_no': 'first',
            'Is_infirm': 'first'
            })
            # create blank columns with length of dataframe
            main_bills_df = _create_columns(main_bills_df, [ 'Week_startdate','Week_enddate','Letter_date','Due_date','Disbursement_date','Lc_date','Interest_levydate','Remarks'])
            # replace '--' with None
            main_bills_df=main_bills_df.replace('--',None)
            main_bills_df['Week_startdate']=week_start_date
            main_bills_df['Week_enddate']=week_end_date
            # convert char to float for DevFinal column
            main_bills_df['DevFinal'] = main_bills_df['DevFinal'].str.replace(',', '').astype(float)

            # rename columns 
            main_bills_df.rename(columns= {'PayRcv' : 'PayableorReceivable' , 'DevFinal':'Final_charges'} ,inplace=True)
            reorder_columns=['Fin_year','Week_no','Week_startdate','Week_enddate','Letter_date','Due_date','Disbursement_date','Lc_date','Interest_levydate','Entity','Final_charges','PayableorReceivable','Remarks','Fin_code' , 'Revision_no','Is_disbursed']

            main_bills_df = main_bills_df.reindex(columns=reorder_columns)
            if not main_bills_df.empty:
                  # may be interregional entered
                  try:
                        main_bills_df['Letter_date']=letter_date
                        main_bills_df['Due_date']=due_date
                        main_bills_df['Disbursement_date']=disbursement_date
                        main_bills_df['Lc_date']=due_date
                        main_bills_df['Interest_levydate']=due_date
                        main_bills_df['Is_disbursed']=False
                        ## added leagcy dues columns as false by praharsha korngi on 14.10.2024##
                        main_bills_df['Legacy_dues'] = False
                        with engine.connect() as connection:
                              main_bills_df.to_sql('reac_basemodel', connection, if_exists='append',index=False)
                        # now update the dsm_bills_upload_status to True
                        YearCalendar.objects.filter(fin_year=fin_year,week_no=week_no).update(
                              reac_bills_uploaded_status=True)
                        return JsonResponse({'status':True , 'message': 'REAC Bills are Submitted Successfully' },safe=False)
                  
                  except Exception as e:
                        extractdb_errormsg(e)
                        return JsonResponse({'status':False , 'message': 'Bills are already submitted , Please check' },safe=False)
                  
      except Exception as e:
            extractdb_errormsg(e)
            return  JsonResponse({'status':False ,'message':str(e) },safe=False)
      
def storeCONGBills(main_bills_df,disbursement_dates_qry,due_date_qry ,acc_type,letter_date,fin_year,week_no):
      try:
            week_start_date,week_end_date = getWeekDates(fin_year,week_no)
            disbursementdays_list=list(disbursement_dates_qry.filter(pool_acc=acc_type).values_list('days',flat=True))
            
            # get no of days for due date
            duedays_list=list(due_date_qry.values_list('cong',flat=True))
            dueday_num=duedays_list[0] if len(duedays_list) else None
            disburseday_num=disbursementdays_list[0] if len(disbursementdays_list) else None
           
            due_date= letter_date+timedelta(days= dueday_num )
            disbursement_date= letter_date+timedelta(days= disburseday_num )
            
            # drop acc_type column
            main_bills_df.drop(columns=['id','Acc_type'] ,inplace=True)
            # Group by 'Fin_code' and aggregate
            main_bills_df = main_bills_df.groupby(['Fin_code', 'PayRcv'], as_index=False).agg({
            'Fin_year': 'first',
            'Week_no': 'first',
            'Entity': 'first',
            'DevFinal': 'sum',
            'PayRcv': 'first',
            'Revision_no': 'first',
            'Is_infirm': 'first'
            })

            # create blank columns with length of dataframe
            main_bills_df = _create_columns(main_bills_df, [ 'Week_startdate','Week_enddate','Letter_date','Due_date','Disbursement_date','Lc_date','Interest_levydate','Remarks'])
            # replace '--' with None
            main_bills_df=main_bills_df.replace('--',None)
            main_bills_df['Week_startdate']=week_start_date
            main_bills_df['Week_enddate']=week_end_date
            # convert char to float for DevFinal column
            main_bills_df['DevFinal'] = main_bills_df['DevFinal'].str.replace(',', '').astype(float)

            # rename columns 
            main_bills_df.rename(columns= {'PayRcv' : 'PayableorReceivable' , 'DevFinal':'Final_charges'} ,inplace=True)
            reorder_columns=['Fin_year','Week_no','Week_startdate','Week_enddate','Letter_date','Due_date','Disbursement_date','Lc_date','Interest_levydate','Entity','Final_charges','PayableorReceivable','Remarks','Fin_code' , 'Revision_no','Is_disbursed']

            main_bills_df = main_bills_df.reindex(columns=reorder_columns)
            if not main_bills_df.empty:
                  # may be interregional entered
                  try:
                        main_bills_df['Letter_date']=letter_date
                        main_bills_df['Due_date']=due_date
                        main_bills_df['Disbursement_date']=disbursement_date
                        main_bills_df['Lc_date']=due_date
                        main_bills_df['Interest_levydate']=due_date
                        main_bills_df['Is_disbursed']=False
                        ## added leagcy dues columns as false by praharsha korngi on 14.10.2024##
                        main_bills_df['Legacy_dues'] = False
                        with engine.connect() as connection:
                              main_bills_df.to_sql('cong_basemodel', connection, if_exists='append',index=False)
                        # now update the dsm_bills_upload_status to True
                        YearCalendar.objects.filter(fin_year=fin_year,week_no=week_no).update(
                              cong_bills_uploaded_status=True)
                        return JsonResponse({'status':True , 'message': 'Congestion Bills are Submitted Successfully' },safe=False)
                  
                  except Exception as e:
                        extractdb_errormsg(e)
                        return JsonResponse({'status':False , 'message': 'Bills are already submitted , Please check' },safe=False)
                  
      except Exception as e:
            extractdb_errormsg(e)
            return  JsonResponse({'status':False ,'message':str(e) },safe=False)
      


def storeASNETBills(main_bills_df,letter_date,fin_year,week_no):
      try:
            week_start_date,week_end_date = getWeekDates(fin_year,week_no)
            due_date= letter_date+timedelta(days= 10 )
            disbursement_date= letter_date+timedelta(days= 7 )
            # create blank columns with length of dataframe
            
            main_bills_df = _create_columns(main_bills_df, [ 'Week_startdate','Week_enddate','Letter_date','Due_date','Disbursement_date','Remarks'])
            # replace '--' with None
            main_bills_df=main_bills_df.replace('--',None)
            main_bills_df['Week_startdate']=week_start_date
            main_bills_df['Week_enddate']=week_end_date
            main_bills_df['DevFinal'] = main_bills_df['DevFinal'].apply(currency_to_float)
            # rename columns 
            main_bills_df.rename(columns= {'PayRcv' : 'PayableorReceivable' , 'DevFinal':'Final_charges'} ,inplace=True)

            reorder_columns=['Fin_year','Week_no','Week_startdate','Week_enddate','Letter_date','Due_date','Disbursement_date','Entity','Final_charges','PayableorReceivable','Remarks','Fin_code' , 'Revision_no','Is_disbursed','Fully_disbursed','SRAS_id','TRAS_id','MBAS_id','SCUC_id']
            main_bills_df = main_bills_df.reindex(columns=reorder_columns)
            
            if not main_bills_df.empty:
                  # may be interregional entered
                  try:
                        main_bills_df['Letter_date']=letter_date
                        main_bills_df['Due_date']=due_date
                        main_bills_df['Disbursement_date']=disbursement_date
                        main_bills_df['Is_disbursed']=False
                        main_bills_df['Revision_no']=0
                        ## added leagcy dues columns as false by praharsha korngi on 14.10.2024##
                        main_bills_df['Legacy_dues'] = False

                        main_bills_df.fillna('')
                        with engine.connect() as connection:
                              main_bills_df.to_sql('netas_basemodel', connection, if_exists='append',index=False)
                        #now update the dsm_bills_upload_status to True
                        YearCalendar.objects.filter(fin_year=fin_year,week_no=week_no).update(
                              netas_bills_uploaded_status=True)
                        return JsonResponse({'status':True , 'message': 'Net AS Bills are Submitted Successfully' },safe=False)
                  
                  except Exception as e:
                        extractdb_errormsg(e)
                        return JsonResponse({'status':False , 'message': 'Bills are already submitted , Please check' },safe=False)
                  
      except Exception as e:
            extractdb_errormsg(e)
            return  JsonResponse({'status':False ,'message':str(e) },safe=False)

def storeBills(request):
      try:
            request_data =json.loads(request.body)
            formdata =request_data['data']['formdata']
            
            main_bills_df =pd.DataFrame(request_data['data']['main_bills'])
            # interregional =request_data['interregional'][0]
            fin_year=formdata['fin_year']
            week_no=formdata['wk_no']
            acc_type=formdata['acc_type']

            letter_date=add530hrstoDateString(request_data['letter_date']).date() 
            
            disbursement_dates_qry=DisbursementDates.objects.filter( Q(end_date__isnull=True)| Q(end_date__gte=datetime.today()) )
            due_date_qry=PoolDuedates.objects.filter( Q(enddate__isnull=True)| Q(enddate__gte=datetime.today()))
            # store based on pool account type
            if acc_type == 'DSM':
                  # in main_bills_df Entity names are of Fees and Charges Names
                  return storeDSMBills(main_bills_df,disbursement_dates_qry,due_date_qry ,acc_type,letter_date,fin_year,week_no)

            elif acc_type == 'SRAS':
                  return storeSRASBills(main_bills_df,disbursement_dates_qry,due_date_qry ,acc_type,letter_date,fin_year,week_no)
            
            elif acc_type == 'TRAS':
                  return storeTRASBills(main_bills_df,disbursement_dates_qry,due_date_qry ,acc_type,letter_date,fin_year,week_no)
            
            elif acc_type == 'SCUC':
                  return storeSCUCBills(main_bills_df,disbursement_dates_qry,due_date_qry ,acc_type,letter_date,fin_year,week_no)
            
            elif acc_type == 'MBAS':
                  return storeMBASBills(main_bills_df,disbursement_dates_qry,due_date_qry ,acc_type,letter_date,fin_year,week_no)
            
            elif acc_type == 'REAC':
                  return storeREACBills(main_bills_df,disbursement_dates_qry,due_date_qry ,acc_type,letter_date,fin_year,week_no)
            
            elif acc_type == 'CONG':
                  return storeCONGBills(main_bills_df,disbursement_dates_qry,due_date_qry ,acc_type,letter_date,fin_year,week_no)
            
            elif acc_type == 'NET_AS':
                  # first check whether SCUC,SRAS,TRAS and MBAS bills uploaded or not
                  get_upload_status=list(YearCalendar.objects.filter(fin_year=fin_year,week_no=week_no).values('sras_bills_uploaded_status','tras_bills_uploaded_status','mbas_bills_uploaded_status','scuc_bills_uploaded_status'))

                  if len(get_upload_status):
                        if get_upload_status[0]['sras_bills_uploaded_status'] and get_upload_status[0]['tras_bills_uploaded_status'] and get_upload_status[0]['mbas_bills_uploaded_status'] and get_upload_status[0]['scuc_bills_uploaded_status']:
                              return storeASNETBills(main_bills_df,letter_date,fin_year,week_no)
                        else:
                              return JsonResponse({'status':False ,'message': 'Please First Store all of SRAS,TRAS ,MBAS and SCUC'},safe=False)
                  else:
                        return JsonResponse({'status':False ,'message': 'SRAS,TRAS ,MBAS and SCUC bills are not uploaded , Please check'})
            
            return  JsonResponse({'status':True ,'message': 'Bills Stored Successfully'})
      except Exception as e:
            return HttpResponse(extractdb_errormsg(e),status=400)
        
      