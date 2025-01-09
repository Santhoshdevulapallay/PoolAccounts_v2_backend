from dsm.common import no_data_found_df
from dsm.common import generateWeekRange
from registration.extarctdb_errors import extractdb_errormsg
from .models import *
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.http import HttpResponse , JsonResponse ,FileResponse
import json ,os ,pandas as pd
from .engine_create import *
from django.db.models import Max
from poolaccounts.settings import base_dir
import pdb
from django.db.models import Prefetch
from django.db.models import Q

def viewBills(request):
      try:
            request_data =json.loads(request.body)
            fin_years=request_data['formdata']['fin_year']
            week_nos_range=request_data['formdata']['wk_no']
            acc_type = request_data['formdata']['acc_type']
            all_payrcv=[]
            week_nos = generateWeekRange(week_nos_range)
            common_qry=Q(Fin_year__in=fin_years ,Week_no__in=week_nos,Entity__in=request_data['formdata']['usr'])
            admin_qry=Q(Fin_year__in=fin_years ,Week_no__in=week_nos)
            if acc_type == 'DSM':
                  # get payables separate and receivables separate
                  if request_data['formdata']['usr'] and len(request_data['formdata']['usr'])>0:
                        all_payrcv=list(DSMBaseModel.objects.filter(common_qry).order_by('Fin_year','Week_no').values('Fin_year','Week_no','Entity','Week_startdate','Week_enddate','Final_charges','PayableorReceivable','Fin_code'))
                  else:
                        all_payrcv=list(DSMBaseModel.objects.filter(admin_qry).order_by('Fin_year','Week_no').values('Fin_year','Week_no','Entity','Week_startdate','Week_enddate','Final_charges','PayableorReceivable','Fin_code'))

            elif acc_type == 'SRAS':
                  # get payables separate and receivables separate
                  if request_data['formdata']['usr'] and len(request_data['formdata']['usr'])>0:
                        all_payrcv=list(SRASBaseModel.objects.filter(common_qry).order_by('Fin_year','Week_no').values('Fin_year','Week_no','Entity','Week_startdate','Week_enddate','Final_charges','PayableorReceivable','Fin_code'))
                  else:
                        all_payrcv=list(SRASBaseModel.objects.filter(admin_qry).order_by('Fin_year','Week_no').values('Fin_year','Week_no','Entity','Week_startdate','Week_enddate','Final_charges','PayableorReceivable','Fin_code'))

            elif acc_type == 'TRAS':
                  # get payables separate and receivables separate
                  if request_data['formdata']['usr'] and len(request_data['formdata']['usr'])>0:
                        all_payrcv=list(TRASBaseModel.objects.filter(common_qry).order_by('Fin_year','Week_no').values('Fin_year','Week_no','Entity','Week_startdate','Week_enddate','Final_charges','PayableorReceivable','Fin_code'))
                  else:
                        all_payrcv=list(TRASBaseModel.objects.filter(admin_qry).order_by('Fin_year','Week_no').values('Fin_year','Week_no','Entity','Week_startdate','Week_enddate','Final_charges','PayableorReceivable','Fin_code'))

            elif acc_type == 'MBAS':
                  # get payables separate and receivables separate
                  if request_data['formdata']['usr'] and len(request_data['formdata']['usr'])>0:
                        all_payrcv=list(MBASBaseModel.objects.filter(common_qry).order_by('Fin_year','Week_no').values('Fin_year','Week_no','Entity','Week_startdate','Week_enddate','Final_charges','PayableorReceivable','Fin_code'))
                  else:
                        all_payrcv=list(MBASBaseModel.objects.filter(admin_qry).order_by('Fin_year','Week_no').values('Fin_year','Week_no','Entity','Week_startdate','Week_enddate','Final_charges','PayableorReceivable','Fin_code'))

            elif acc_type == 'REAC':
                  # get payables separate and receivables separate
                  if request_data['formdata']['usr'] and len(request_data['formdata']['usr'])>0:
                        all_payrcv=list(REACBaseModel.objects.filter(common_qry).order_by('Fin_year','Week_no').values('Fin_year','Week_no','Entity','Week_startdate','Week_enddate','Final_charges','PayableorReceivable','Fin_code'))
                  else:
                        all_payrcv=list(REACBaseModel.objects.filter(admin_qry).order_by('Fin_year','Week_no').values('Fin_year','Week_no','Entity','Week_startdate','Week_enddate','Final_charges','PayableorReceivable','Fin_code'))

            elif acc_type == 'NET_AS':
                  # get payables separate and receivables separate
                  if request_data['formdata']['usr'] and len(request_data['formdata']['usr'])>0:
                        all_payrcv=list(NetASBaseModel.objects.filter(common_qry).order_by('Fin_year','Week_no').values('Fin_year','Week_no','Entity','Week_startdate','Week_enddate','Final_charges','PayableorReceivable','Fin_code'))
                  else:
                        all_payrcv=list(NetASBaseModel.objects.filter(admin_qry).order_by('Fin_year','Week_no').values('Fin_year','Week_no','Entity','Week_startdate','Week_enddate','Final_charges','PayableorReceivable','Fin_code'))

            elif acc_type == 'CONG':
                  # get payables separate and receivables separate
                  if request_data['formdata']['usr'] and len(request_data['formdata']['usr'])>0:
                        all_payrcv=list(CONGBaseModel.objects.filter(common_qry).order_by('Fin_year','Week_no').values('Fin_year','Week_no','Entity','Week_startdate','Week_enddate','Final_charges','PayableorReceivable','Fin_code'))
                  else:
                       
                        all_payrcv=list(CONGBaseModel.objects.filter(admin_qry).order_by('Fin_year','Week_no').values('Fin_year','Week_no','Entity','Week_startdate','Week_enddate','Final_charges','PayableorReceivable','Fin_code'))
            else:
                  pass
                 
            return JsonResponse([all_payrcv] , safe=False)
           

      except Exception as e:
            return HttpResponse(extractdb_errormsg(e),status=400)

def downloadBills(request):
      try:
            request_data =json.loads(request.body)
            fin_years=request_data['formdata']['fin_year']
            week_nos_range=request_data['formdata']['wk_no']
            acc_type = request_data['formdata']['acc_type']
            week_nos = generateWeekRange(week_nos_range)

            fin_years_str = '&'.join([str(num) for num in fin_years])
            week_nos_str = '&'.join([str(num) for num in week_nos])
            
            parent_folder = os.path.abspath(os.path.join(base_dir, os.pardir))
            directory = os.path.join(parent_folder, 'Files', 'ViewBills' )
            full_path=''
            common_qry=Q(Fin_year__in=fin_years ,Week_no__in=week_nos)
            if not os.path.exists(directory):
                  # Create the directory if it doesn't exist
                  os.makedirs(directory)

            if acc_type == 'DSM':
                  # get payables separate and receivables separate
                  dsm_allpayrcv=pd.DataFrame(DSMBaseModel.objects.filter(common_qry).order_by('Fin_year','Week_no','Entity').values('Fin_year','Week_no','Week_startdate','Week_enddate','Revision_no','Letter_date','Due_date','Disbursement_date','Entity','Final_charges','PayableorReceivable','Fin_code'))
                  
                  in_filename='dsm_bills&'+str(fin_years_str)+str(week_nos_str)+'.csv'

                  full_path=os.path.join(directory, in_filename)
                  if not dsm_allpayrcv.empty:
                        dsm_allpayrcv.to_csv(full_path,index=False,header=True)  
                  else:
                        no_data_found_df.to_csv(full_path,index=False,header=True)  
            
            elif acc_type == 'SRAS':
                  # get payables separate and receivables separate
                  sras_allpayrcv=pd.DataFrame(SRASBaseModel.objects.filter(common_qry).order_by('Fin_year','Week_no','Entity').values('Fin_year','Week_no','Week_startdate','Week_enddate','Revision_no','Letter_date','Due_date','Disbursement_date','Entity','Final_charges','PayableorReceivable','Fin_code'))
                  
                  in_filename='sras_bills&'+str(fin_years_str)+str(week_nos_str)+'.csv'
                  full_path=os.path.join(directory, in_filename)

                  if not sras_allpayrcv.empty:
                        sras_allpayrcv.to_csv(full_path,index=False,header=True)  
                  else:
                        no_data_found_df.to_csv(full_path,index=False,header=True)  

            elif acc_type == 'TRAS':
                  # get payables separate and receivables separate
                  tras_allpayrcv=pd.DataFrame(TRASBaseModel.objects.filter(common_qry).order_by('Fin_year','Week_no','Entity').values('Fin_year','Week_no','Week_startdate','Week_enddate','Revision_no','Letter_date','Due_date','Disbursement_date','Entity','Final_charges','PayableorReceivable','Fin_code'))
                  
                  in_filename='tras_bills&'+str(fin_years_str)+str(week_nos_str)+'.csv'
                  full_path=os.path.join(directory, in_filename)

                  if not tras_allpayrcv.empty:
                        tras_allpayrcv.to_csv(full_path,index=False,header=True)  
                  else:
                        no_data_found_df.to_csv(full_path,index=False,header=True)  

            elif acc_type == 'MBAS':
                  # get payables separate and receivables separate
                  mbas_allpayrcv=pd.DataFrame(MBASBaseModel.objects.filter(common_qry).order_by('Fin_year','Week_no','Entity').values('Fin_year','Week_no','Week_startdate','Week_enddate','Revision_no','Letter_date','Due_date','Disbursement_date','Entity','Final_charges','PayableorReceivable','Fin_code'))
                  
                  in_filename='mbas_bills&'+str(fin_years_str)+str(week_nos_str)+'.csv'
                  full_path=os.path.join(directory, in_filename)

                  if not mbas_allpayrcv.empty:
                        mbas_allpayrcv.to_csv(full_path,index=False,header=True)  
                  else:
                        no_data_found_df.to_csv(full_path,index=False,header=True)  

                  return FileResponse(open(full_path,'rb'),content_type='text/csv') 
            
            elif acc_type == 'REAC':
                  # get payables separate and receivables separate
                  reac_allpayrcv=pd.DataFrame(REACBaseModel.objects.filter(common_qry).order_by('Fin_year','Week_no','Entity').values('Fin_year','Week_no','Week_startdate','Week_enddate','Revision_no','Letter_date','Due_date','Disbursement_date','Entity','Final_charges','PayableorReceivable','Fin_code'))
                  
                  in_filename='sras_bills&'+str(fin_years_str)+str(week_nos_str)+'.csv'
                  full_path=os.path.join(directory, in_filename)

                  if not reac_allpayrcv.empty:
                        reac_allpayrcv.to_csv(full_path,index=False,header=True)  
                  else:
                        no_data_found_df.to_csv(full_path,index=False,header=True) 

            elif acc_type == 'NET_AS':
                  # get payables separate and receivables separate
                  netas_allpayrcv=pd.DataFrame(NetASBaseModel.objects.filter(common_qry).order_by('Fin_year','Week_no','Entity').values('Fin_year','Week_no','Week_startdate','Week_enddate','Revision_no','Letter_date','Due_date','Disbursement_date','Entity','Final_charges','PayableorReceivable','Fin_code'))
                  
                  in_filename='netas_bills&'+str(fin_years_str)+str(week_nos_str)+'.csv'
                  full_path=os.path.join(directory, in_filename)

                  if not netas_allpayrcv.empty:
                        netas_allpayrcv.to_csv(full_path,index=False,header=True)  
                  else:
                        no_data_found_df.to_csv(full_path,index=False,header=True)   
            elif acc_type == 'CONG':
                  # get payables separate and receivables separate
                  cong_allpayrcv=pd.DataFrame(CONGBaseModel.objects.filter(common_qry).order_by('Fin_year','Week_no','Entity').values('Fin_year','Week_no','Week_startdate','Week_enddate','Revision_no','Letter_date','Due_date','Disbursement_date','Entity','Final_charges','PayableorReceivable','Fin_code'))
                  
                  in_filename='cong_bills&'+str(fin_years_str)+str(week_nos_str)+'.csv'
                  full_path=os.path.join(directory, in_filename)

                  if not cong_allpayrcv.empty:
                        cong_allpayrcv.to_csv(full_path,index=False,header=True)  
                  else:
                        no_data_found_df.to_csv(full_path,index=False,header=True)   
            else:
                  pass

            return FileResponse(open(full_path,'rb'),content_type='text/csv')   
      except Exception as e:
            
            return HttpResponse(extractdb_errormsg(e),status=400)

def downloadPayRcv(request):
      try:
            request_data =json.loads(request.body)
            fin_years=request_data['formdata']['fin_year']
            week_nos_range=request_data['formdata']['wk_no']
            acc_type = request_data['formdata']['acc_type']
            week_nos = generateWeekRange(week_nos_range)

            fin_years_str = '&'.join([str(num) for num in fin_years])
            week_nos_str = '&'.join([str(num) for num in week_nos])
            
            parent_folder = os.path.abspath(os.path.join(base_dir, os.pardir))
            directory = os.path.join(parent_folder, 'Files', 'PayRcvBills' )
            common_qry=Q(Fin_year__in=fin_years ,Week_no__in=week_nos)

            if not os.path.exists(directory):
                  # Create the directory if it doesn't exist
                  os.makedirs(directory)

            if acc_type == 'DSM': 
                  # get payables separate and receivables separate
                  allpay_df=pd.DataFrame(DSMBaseModel.objects.filter(common_qry).select_related('payments').values('Fin_year','Week_no','Week_startdate','Week_enddate','Revision_no','Letter_date','Due_date','Disbursement_date','Entity','Final_charges','PayableorReceivable','Fin_code','payments__Paid_date',
                        'payments__Description',
                        'payments__Paid_amount',
                        'payments__Other_info'))
                  
                  allrcv_df=pd.DataFrame(DSMBaseModel.objects.filter(common_qry).select_related('dsmreceivables').values('Fin_year','Week_no','Week_startdate','Week_enddate','Revision_no','Letter_date','Due_date','Disbursement_date','Entity','Final_charges','PayableorReceivable','Fin_code',
                        'dsmreceivables__Disbursed_amount',
                        'dsmreceivables__disbursed_date',
                        'dsmreceivables__neft_txnno'))
                  
                  merge_df=pd.merge(allpay_df,allrcv_df,on=['Fin_year','Week_no','Fin_year','Week_no','Week_startdate','Week_enddate','Revision_no','Letter_date','Due_date','Disbursement_date','Entity','Final_charges','PayableorReceivable','Fin_code'])
                  merge_df.sort_values(['Fin_year','Week_no'],inplace=True)
                  in_filename='dsm_all&'+str(fin_years_str)+str(week_nos_str)+'.csv'
                  full_path=os.path.join(directory, in_filename)
                  if not merge_df.empty:
                        merge_df.to_csv(full_path,index=False,header=True)  
                  else:
                        no_data_found_df.to_csv(full_path,index=False,header=True)  
            
            
            elif acc_type == 'MBAS':
                  # get payables separate and receivables separate
                  mbas_allpayrcv=pd.DataFrame(MBASBaseModel.objects.filter(common_qry).values('Fin_year','Week_no','Week_startdate','Week_enddate','Revision_no','Letter_date','Due_date','Disbursement_date','Entity','Final_charges','PayableorReceivable','Fin_code'))
                  
                  in_filename='mbas_bills&'+str(fin_years_str)+str(week_nos_str)+'.csv'
                  full_path=os.path.join(directory, in_filename)

                  if not mbas_allpayrcv.empty:
                        mbas_allpayrcv.to_csv(full_path,index=False,header=True)  
                  else:
                        no_data_found_df.to_csv(full_path,index=False,header=True)  

                  return FileResponse(open(full_path,'rb'),content_type='text/csv') 
            
            elif acc_type == 'REAC':
                 # get payables separate and receivables separate
                  allpay_df=pd.DataFrame(REACBaseModel.objects.filter(common_qry).select_related('reacpayments').values('Fin_year','Week_no','Week_startdate','Week_enddate','Revision_no','Letter_date','Due_date','Disbursement_date','Entity','Final_charges','PayableorReceivable','Fin_code','reacpayments__Paid_date',
                        'reacpayments__Description',
                        'reacpayments__Paid_amount',
                        'reacpayments__Other_info'))
                  
                  allrcv_df=pd.DataFrame(REACBaseModel.objects.filter(common_qry).select_related('reacreceivables').values('Fin_year','Week_no','Week_startdate','Week_enddate','Revision_no','Letter_date','Due_date','Disbursement_date','Entity','Final_charges','PayableorReceivable','Fin_code',
                        'reacreceivables__Disbursed_amount',
                        'reacreceivables__disbursed_date',
                        'reacreceivables__neft_txnno'))
                
                  merge_df=pd.merge(allpay_df,allrcv_df,on=['Fin_year','Week_no','Fin_year','Week_no','Week_startdate','Week_enddate','Revision_no','Letter_date','Due_date','Disbursement_date','Entity','Final_charges','PayableorReceivable','Fin_code'])
                  merge_df.sort_values(['Fin_year','Week_no'],inplace=True)
                  in_filename='reac_all&'+str(fin_years_str)+str(week_nos_str)+'.csv'
                  full_path=os.path.join(directory, in_filename)
                  if not merge_df.empty:
                        merge_df.to_csv(full_path,index=False,header=True)  
                  else:
                        no_data_found_df.to_csv(full_path,index=False,header=True)  

            elif acc_type == 'NET_AS':
                  # get payables separate and receivables separate
                  allpay_df=pd.DataFrame(NetASBaseModel.objects.filter(common_qry).select_related('netaspayments').values('Fin_year','Week_no','Week_startdate','Week_enddate','Revision_no','Letter_date','Due_date','Disbursement_date','Entity','Final_charges','PayableorReceivable','Fin_code','netaspayments__Paid_date',
                        'netaspayments__Description',
                        'netaspayments__Paid_amount',
                        'netaspayments__Other_info'))
                  
                  allrcv_df=pd.DataFrame(NetASBaseModel.objects.filter(common_qry).select_related('netasreceivables').values('Fin_year','Week_no','Week_startdate','Week_enddate','Revision_no','Letter_date','Due_date','Disbursement_date','Entity','Final_charges','PayableorReceivable','Fin_code',
                        'netasreceivables__Disbursed_amount',
                        'netasreceivables__disbursed_date',
                        'netasreceivables__neft_txnno'))
                  
                  merge_df=pd.merge(allpay_df,allrcv_df,on=['Fin_year','Week_no','Fin_year','Week_no','Week_startdate','Week_enddate','Revision_no','Letter_date','Due_date','Disbursement_date','Entity','Final_charges','PayableorReceivable','Fin_code'])
                  merge_df.sort_values(['Fin_year','Week_no'],inplace=True)
                  in_filename='netass_all&'+str(fin_years_str)+str(week_nos_str)+'.csv'
                  full_path=os.path.join(directory, in_filename)
                  if not merge_df.empty:
                        merge_df.to_csv(full_path,index=False,header=True)  
                  else:
                        no_data_found_df.to_csv(full_path,index=False,header=True)

            elif acc_type == 'CONG':
                  # get payables separate and receivables separate
                  allpay_df=pd.DataFrame(CONGBaseModel.objects.filter(common_qry).select_related('congpayments').values('Fin_year','Week_no','Week_startdate','Week_enddate','Revision_no','Letter_date','Due_date','Disbursement_date','Entity','Final_charges','PayableorReceivable','Fin_code','congpayments__Paid_date',
                        'congpayments__Description',
                        'congpayments__Paid_amount',
                        'congpayments__Other_info'))
                  
                  allrcv_df=pd.DataFrame(CONGBaseModel.objects.filter(common_qry).select_related('congreceivables').values('Fin_year','Week_no','Week_startdate','Week_enddate','Revision_no','Letter_date','Due_date','Disbursement_date','Entity','Final_charges','PayableorReceivable','Fin_code',
                        'congreceivables__Disbursed_amount',
                        'congreceivables__disbursed_date',
                        'congreceivables__neft_txnno'))
                  
                  merge_df=pd.merge(allpay_df,allrcv_df,on=['Fin_year','Week_no','Fin_year','Week_no','Week_startdate','Week_enddate','Revision_no','Letter_date','Due_date','Disbursement_date','Entity','Final_charges','PayableorReceivable','Fin_code'])
                  merge_df.sort_values(['Fin_year','Week_no'],inplace=True)
                  in_filename='cong_all&'+str(fin_years_str)+str(week_nos_str)+'.csv'
                  full_path=os.path.join(directory, in_filename)
                  if not merge_df.empty:
                        merge_df.to_csv(full_path,index=False,header=True)  
                  else:
                        no_data_found_df.to_csv(full_path,index=False,header=True)

            elif acc_type == 'SRAS':
                  # get payables separate and receivables separate
                  allpay_df=pd.DataFrame(SRASBaseModel.objects.filter(common_qry).select_related('sraspayments').values('Fin_year','Week_no','Week_startdate','Week_enddate','Revision_no','Letter_date','Due_date','Disbursement_date','Entity','Final_charges','PayableorReceivable','Fin_code','sraspayments__Paid_date',
                        'sraspayments__Description',
                        'sraspayments__Paid_amount',
                        'sraspayments__Other_info'))
                  
                  allrcv_df=pd.DataFrame(SRASBaseModel.objects.filter(common_qry).select_related('srasreceivables').values('Fin_year','Week_no','Week_startdate','Week_enddate','Revision_no','Letter_date','Due_date','Disbursement_date','Entity','Final_charges','PayableorReceivable','Fin_code',
                        'srasreceivables__Disbursed_amount',
                        'srasreceivables__disbursed_date',
                        'srasreceivables__neft_txnno'))
                  
                  merge_df=pd.merge(allpay_df,allrcv_df,on=['Fin_year','Week_no','Fin_year','Week_no','Week_startdate','Week_enddate','Revision_no','Letter_date','Due_date','Disbursement_date','Entity','Final_charges','PayableorReceivable','Fin_code'])
                  merge_df.sort_values(['Fin_year','Week_no'],inplace=True)
                  in_filename='sras_all&'+str(fin_years_str)+str(week_nos_str)+'.csv'
                  full_path=os.path.join(directory, in_filename)
                  if not merge_df.empty:
                        merge_df.to_csv(full_path,index=False,header=True)  
                  else:
                        no_data_found_df.to_csv(full_path,index=False,header=True)  

            elif acc_type == 'TRAS':
                  # get payables separate and receivables separate
                  allpay_df=pd.DataFrame(TRASBaseModel.objects.filter(common_qry).select_related('mbaspayments').values('Fin_year','Week_no','Week_startdate','Week_enddate','Revision_no','Letter_date','Due_date','Disbursement_date','Entity','Final_charges','PayableorReceivable','Fin_code','mbaspayments__Paid_date',
                        'mbaspayments__Description',
                        'mbaspayments__Paid_amount',
                        'mbaspayments__Other_info'))
                  
                  allrcv_df=pd.DataFrame(TRASBaseModel.objects.filter(common_qry).select_related('mbasreceivables').values('Fin_year','Week_no','Week_startdate','Week_enddate','Revision_no','Letter_date','Due_date','Disbursement_date','Entity','Final_charges','PayableorReceivable','Fin_code',
                        'mbasreceivables__Disbursed_amount',
                        'mbasreceivables__disbursed_date',
                        'mbasreceivables__neft_txnno'))
                  
                  merge_df=pd.merge(allpay_df,allrcv_df,on=['Fin_year','Week_no','Fin_year','Week_no','Week_startdate','Week_enddate','Revision_no','Letter_date','Due_date','Disbursement_date','Entity','Final_charges','PayableorReceivable','Fin_code'])
                  merge_df.sort_values(['Fin_year','Week_no'],inplace=True)
                  in_filename='mbas_all&'+str(fin_years_str)+str(week_nos_str)+'.csv'
                  full_path=os.path.join(directory, in_filename)
                  if not merge_df.empty:
                        merge_df.to_csv(full_path,index=False,header=True)  
                  else:
                        no_data_found_df.to_csv(full_path,index=False,header=True)    

            else:
                  pass

            return FileResponse(open(full_path,'rb'),content_type='text/csv')   
      except Exception as e:
            return HttpResponse(extractdb_errormsg(e),status=400)

