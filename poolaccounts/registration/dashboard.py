from dsm.models import BankStatement
from dsm.finance_reports import getOustandingdf

from registration.add530hrs import create_zip_file
from poolaccounts.settings import  base_dir
from registration.extarctdb_errors import extractdb_errormsg
from .models import *
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.http import HttpResponse , JsonResponse,FileResponse
from rest_framework import status
import pandas as pd
from io import StringIO
from datetime import datetime
import os ,json ,pdb ,ast,io,zipfile
from dsm.models import DSMBaseModel,DisbursementStatus
from dsm.reac_models import REACBaseModel
from dsm.netas_models import NetASBaseModel
from dsm.sras_models import SRASBaseModel,SRASReceivables
from dsm.tras_models import TRASBaseModel,TRASReceivables
from dsm.mbas_models import MBASBaseModel,MBASReceivables
from dsm.reac_models import REACBaseModel,REACReceivables
from dsm.scuc_models import SCUCBaseModel,SCUCReceivables
from django.http import HttpResponse , JsonResponse
from registration.extarctdb_errors import extractdb_errormsg
from registration.models import YearCalendar
from django.db.models import F ,Count ,Sum , Q
from django.db.models.functions import Coalesce
from dsm.common import keys
from dsm.models import *
from dsm.common import getBankShortNames , getFincode,getFeesChargesName
def getDisbursedStatus(model_obj_qry,fin_year,week_no,col_name):
      try:
            # status
            mod_obj_query=model_obj_qry.objects.filter(Fin_year=fin_year,Week_no=week_no,PayableorReceivable='Receivable',Effective_end_date__isnull=True)
            receivable_srpc=mod_obj_query.aggregate(total_amount=Coalesce(Sum('Final_charges'),0.0))

            actual_received=mod_obj_query.aggregate(total_amount=Coalesce(Sum(col_name),0.0))
            
            if receivable_srpc['total_amount'] - actual_received['total_amount'] <= 1:
                  return True , 100
            else: 
                  percent_disbursed=int( (actual_received['total_amount']/receivable_srpc['total_amount'])*100 )
                  #percent_disbursed = receivable_srpc['total_amount'] - actual_received['total_amount']
                  return False,percent_disbursed

      except Exception as e:
            return False
      
def getDashboardData(request):
      try:
            request_data=json.loads(request.body)
            fincode = request_data['fincode']

            
            # last week surplus , taking only latest disbursed value
            last_week_surplus_qry=list(DisbursementStatus.objects.filter(final_disburse=True).order_by('-Disbursed_date')[:1].values('Surplus_amt'))
            last_week_surplus_amt=last_week_surplus_qry[0]['Surplus_amt']

            # get last 5 weeeks
            fin_weeks=list(YearCalendar.objects.filter(srpc_fetch_status=True,dsm_bills_uploaded_status=True,netas_bills_uploaded_status=True,reac_bills_uploaded_status=True).order_by('-id').values('fin_year','week_no','start_date','end_date'))
            all_status=[]
            for fw in fin_weeks:
                  all_status_dict={
                        'dsm':False,
                        'reac':False,
                        'netas':False,
                        'dsm_percent':'',
                        'reac_percent':'',
                        'netas_percent':'',
                        'start_date':'',
                        'end_date':'',
                        'week_no':''
                  }
                  
                  all_status_dict['dsm'],all_status_dict['dsm_percent']=getDisbursedStatus(DSMBaseModel,fw['fin_year'],fw['week_no'],'dsmreceivables__Disbursed_amount')

                  all_status_dict['netas'],all_status_dict['netas_percent']=getDisbursedStatus(NetASBaseModel,fw['fin_year'],fw['week_no'],'netasreceivables__Disbursed_amount')

                  all_status_dict['reac'],all_status_dict['reac_percent']=getDisbursedStatus(REACBaseModel,fw['fin_year'],fw['week_no'],'reacreceivables__Disbursed_amount')
              
                  all_status_dict['start_date']=fw['start_date']
                  all_status_dict['end_date']=fw['end_date']
                  all_status_dict['week_no']=fw['week_no']
                  all_status.append(all_status_dict)

            # get the oustanding dues as on date
            final_outstanding_df=pd.DataFrame([])
            # to show in dashboard considering only DSM and REAC
            for acc_type in ['DSM','REAC','NET_AS','Legacy','Shortfall']:
                  filtered_df,grouped_df=getOustandingdf(acc_type)
                  grouped_df['PoolAcc']=acc_type
                  final_outstanding_df=pd.concat([final_outstanding_df,grouped_df])
            
            if fincode is None :
                  dsm_sum = final_outstanding_df[final_outstanding_df['PoolAcc']=='DSM']['Outstanding'].sum()
                  reac_sum = final_outstanding_df[final_outstanding_df['PoolAcc']=='REAC']['Outstanding'].sum()
                  netas_sum = final_outstanding_df[final_outstanding_df['PoolAcc']=='NET_AS']['Outstanding'].sum()
                  legacy_sum = final_outstanding_df[final_outstanding_df['PoolAcc']=='Legacy']['Outstanding'].sum()
                  last_st_upload = BankStatement.objects.values_list("ValueDate",flat=True).last().strftime("%d.%m.%Y")
                  shortfall_sum = final_outstanding_df[final_outstanding_df['PoolAcc']=='Shortfall']['Outstanding'].sum()
                  total = dsm_sum+reac_sum+netas_sum+legacy_sum+shortfall_sum
            # sort based on highest outstanding
            else :
                  dsm_sum = final_outstanding_df[(final_outstanding_df['PoolAcc']=='DSM')&(final_outstanding_df['Fin_code']==fincode)]['Outstanding'].sum()
                  reac_sum = final_outstanding_df[(final_outstanding_df['PoolAcc']=='REAC')&(final_outstanding_df['Fin_code']==fincode)]['Outstanding'].sum()
                  netas_sum = final_outstanding_df[(final_outstanding_df['PoolAcc']=='NET_AS')&(final_outstanding_df['Fin_code']==fincode)]['Outstanding'].sum()
                  legacy_sum = final_outstanding_df[(final_outstanding_df['PoolAcc']=='Legacy')&(final_outstanding_df['Fin_code']==fincode)]['Outstanding'].sum()
                  last_st_upload = BankStatement.objects.values_list("ValueDate",flat=True).last().strftime("%d.%m.%Y")
                  shortfall_sum = final_outstanding_df[(final_outstanding_df['PoolAcc']=='Shortfall')&(final_outstanding_df['Fin_code']==fincode)]['Outstanding'].sum()
                  total = dsm_sum+reac_sum+netas_sum+legacy_sum+shortfall_sum
            final_outstanding_df.sort_values('Outstanding',ascending=False, inplace=True)

            bank_stmt_df=pd.DataFrame(BankStatement.objects.all().values(),columns=['id', 'ValueDate', 'PostDate', 'Description', 'Debit', 'Credit','Balance', 'IsMapped', 'SplitStatus', 'IsSweep', 'BankType'])
            # exclude Statements if Status is Rejected
            mapped_bank_df=pd.DataFrame(MappedBankEntries.objects.exclude(Status='R').all().values() ,columns=['id', 'Pool_Acc', 'Fin_year', 'Week_no', 'Amount', 'Entity','ValueDate_fk_id', 'Other_info', 'Status', 'Reject_remarks','Parent_id'])

            merged_df=pd.merge(bank_stmt_df,mapped_bank_df,left_on=['id'],right_on=['ValueDate_fk_id'],how='left')
            merged_df=merged_df.fillna('')
            try :
                  entity = getFeesChargesName(fincode)
                  merged_df = merged_df[merged_df['Entity'] == entity][['ValueDate','Description','Credit','Pool_Acc','Fin_year','Week_no','Amount']]
                  merged_df = merged_df.sort_values(by='ValueDate', ascending=False)
                  merged_df['ValueDate'] = pd.to_datetime(merged_df['ValueDate'])
                  merged_df['ValueDate'] = merged_df['ValueDate'].dt.strftime("%d-%m-%Y")
            except :
                  pass
            
            
            disb_df = pd.DataFrame(DisbursedEntities.objects.all().values())          
            disb_date_df = pd.DataFrame(DisbursementStatus.objects.all().values())


            return JsonResponse([all_status,last_week_surplus_amt,final_outstanding_df.to_dict(orient='records'),dsm_sum,reac_sum,netas_sum,last_st_upload,legacy_sum,total,shortfall_sum,merged_df.to_dict(orient='records')],safe=False)

      except Exception as e:
            
            return HttpResponse('error occured',status=404)
      

def downloadDashboardBill(request):
      try:
            request_data=json.loads(request.body)
            acc_type = request_data['billtype']
            fincode = request_data['fincode']
            # get the oustanding dues as on date
            final_outstanding_df=pd.DataFrame([])
            # to show in dashboard considering only DSM and REAC
            filtered_df,grouped_df=getOustandingdf(acc_type)

            sum = filtered_df[filtered_df['Fin_code']==fincode]
            sum = sum.drop(columns=['Fin_code'])

            in_filename=fincode+"_"+str(acc_type)+'.csv'
            
            parent_folder = os.path.abspath(os.path.join(base_dir, os.pardir))
            directory = os.path.join(parent_folder, 'outstanding' )
            no_data_found_df=pd.DataFrame(['NO outstanding due , Please check'])
            full_path=os.path.join(directory, in_filename)

            if not sum.empty:
                  sum.to_csv(full_path,index=False,header=True)  
            else:
                  no_data_found_df.to_csv(full_path,index=False,header=True)

            return FileResponse(open(full_path,'rb'),content_type='text/csv')


      except Exception as e:
            print(e)
            
            return HttpResponse('error occured',status=404)