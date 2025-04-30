from dsm.common import getAllPoolAccs
from registration.add530hrs import add530hrstoDateString
from .models import *
from django.http import HttpResponse , JsonResponse

from .extarctdb_errors import *
from .custom_paths import week_proof_path , current_financial_year
import os , json ,requests
from django.db.models import Q
from datetime import timedelta , datetime
from fiscalyear import *
import pandas as pd
from dsm.models import TemporaryInterRegional , TemporaryMatched
from registration.custom_paths import get_current_financial_year

def getFinCodes():
      try:
            fin_codes=list(Registration.objects.filter(end_date__isnull=True).order_by('fin_code').values('fin_code','dsm_name',))
            return fin_codes
      
      except Exception as e:
            return HttpResponse(extractdb_errormsg(e),status=404)
      
def getFCNames():
      try:
            fc_names=list(Registration.objects.filter(end_date__isnull=True).order_by('fees_charges_name').values('fin_code','fees_charges_name'))
            return fc_names
      
      except Exception as e:
            return HttpResponse(extractdb_errormsg(e),status=404)
      
def getFCName(fin_code):
      try:
            fc_name_lst=list(Registration.objects.filter(end_date__isnull=True ,fin_code = fin_code ).values_list('fees_charges_name' , flat=True))
            return fc_name_lst[0] if len(fc_name_lst) else None

      except Exception as e:
            return None 
         
def getEntityNames():
      try:
            dsm_names=list(Registration.objects.filter(end_date__isnull=True).order_by('dsm_name').values('fin_code','dsm_name'))
            return dsm_names
      
      except Exception as e:
            return HttpResponse(extractdb_errormsg(e),status=404)

def getFinFCNames(request):
      try:
            fin_fc_names = getFCNames()
            return JsonResponse(fin_fc_names,safe=False)
      
      except Exception as e:
            return HttpResponse(extractdb_errormsg(e),status=404)
          
def getRegisteredEntities(request):
      try:
            entities=list(Registration.objects.filter(end_date__isnull=True).order_by('fin_code').all().values())

            return JsonResponse(entities,safe=False)
      
      except Exception as e:
            return HttpResponse(extractdb_errormsg(e),status=404)
      
def getBankDetails(request):
      try:
            bank_details=list(BankDetails.objects.filter(Q(end_date__isnull=True)|Q(end_date__gte=datetime.datetime.today())).values('bank_account','bank_name','ifsc_code','is_sbi','start_date','end_date','supporting_docs','fin_code_fk__fin_code','fin_code_fk__fees_charges_name','gst','pan_card'))

            return JsonResponse([bank_details,getFCNames()],safe=False)
      
      except Exception as e:
            return HttpResponse(extractdb_errormsg(e),status=404)

def fetchPoolAcctsEntities(request):
      try:
            # Fetch account types either end_date is null or end_date is future date like 2040-01-01
            pool_acct_types=list(PoolAccountTypes.objects.filter(Q(end_date__isnull=True) | Q(end_date__gte=timezone.now() )).order_by('acc_types').values_list('acc_types' , flat=True) )

            all_users_fees_charges_names=list(Registration.objects.filter(end_date__isnull=True).order_by('fees_charges_name').values_list('fees_charges_name' , flat=True))

            return JsonResponse([pool_acct_types ,all_users_fees_charges_names] , safe=False)
      
      except Exception as e:
            return HttpResponse(extractdb_errormsg(e),status=404)

def fetchedWeekFiles(request):
      try:
            #today = datetime.date.today()
            #if today.month == 4:
            #      current_financial_year = str(today.year - 1) + "-" + str(today.year)[2:]
            current_financial_year = '2025-26'
            # current_financial_year = get_current_financial_year()
            # get the latest 3 fetched weeks data  bills_uploaded_status=True
            latest_fetched_list=list(YearCalendar.objects.filter(srpc_fetch_status=True).order_by('-end_date')[:3].values('week_no','fetched_time'))

            already_files_fetched_wk =list(YearCalendar.objects.filter(fin_year=current_financial_year,srpc_fetch_status=True ).order_by('week_no').values_list('week_no' , flat=True))

            # if rpc file is fetched and then all bills_status should be True then only confirmed that all fetched bills are stored.
            fetched_but_notvalidated =list(YearCalendar.objects.filter( Q(fin_year=current_financial_year) , Q(srpc_fetch_status=True) , ( Q(ir_bills_uploaded_status=False) | Q(dsm_bills_uploaded_status=False) | (Q(mbas_bills_uploaded_status=False)) | (Q(reac_bills_uploaded_status=False)) | (Q(sras_bills_uploaded_status=False)) | (Q(tras_bills_uploaded_status=False)) ) ).order_by('week_no').values_list('week_no' , flat=True))

            # Fetch account types either end_date is null or end_date is future date like 2040-01-01
            pool_acct_types=getAllPoolAccs()

            # interregional latest 7 records
            inter_regional_latest_df=pd.DataFrame(TemporaryInterRegional.objects.filter(Fin_year=current_financial_year).order_by('-id')[:5].values('Fin_year','Week_no','WRSR','ERSR','WRWR','ERER' ,'WR_Revision_no','ER_Revision_no') )
            
            if not inter_regional_latest_df.empty:
                  # Group by 'Fin_year' and 'Week_no', then find max of 'WR_Revision_no' and 'ER_Revision_no'
                  max_revisions = inter_regional_latest_df.groupby(['Fin_year', 'Week_no']).agg({'WR_Revision_no': 'max', 'ER_Revision_no': 'max'}).reset_index()

                  # Merge with original DataFrame to get all column values corresponding to those rows
                  result = pd.merge(inter_regional_latest_df, max_revisions, on=['Fin_year', 'Week_no', 'WR_Revision_no', 'ER_Revision_no'], how='right')
                  inter_regional_latest_df = result.sort_values(by=['Fin_year', 'Week_no'], ascending=False)
                  
                  # Calculate the absolute difference between WRSR and WRWR
                  inter_regional_latest_df['WRWR'].fillna(0, inplace=True)
                  inter_regional_latest_df['ERER'].fillna(0, inplace=True)


                  inter_regional_latest_df['WRSR_WRWR_diff'] = abs(abs(inter_regional_latest_df['WRSR']) - abs(inter_regional_latest_df['WRWR']))

                  inter_regional_latest_df['ERSR_ERER_diff'] = abs(abs(inter_regional_latest_df['ERSR']) - abs(inter_regional_latest_df['ERER']))
                  
                  # Create a new column based on the condition
                  inter_regional_latest_df['WR Mismatch'] = ['Mismatch' if diff > 20000 else '--' for diff in inter_regional_latest_df['WRSR_WRWR_diff']]

                  inter_regional_latest_df['ER Mismatch'] = ['Mismatch' if diff > 20000 else '--' for diff in inter_regional_latest_df['ERSR_ERER_diff']]

                  # Drop the intermediate column WRSR_WRWR_diff if not needed
                  inter_regional_latest_df.drop(columns=['WRSR_WRWR_diff'], inplace=True)
                  inter_regional_latest_df.drop(columns=['ERSR_ERER_diff'], inplace=True)
                  inter_regional_latest_df.fillna('', inplace=True)
         
            return JsonResponse([latest_fetched_list, already_files_fetched_wk ,fetched_but_notvalidated,  pool_acct_types , inter_regional_latest_df.to_dict(orient='records')],safe=False)
      
      except Exception as e:
            
            return HttpResponse(extractdb_errormsg(e),status=404)

