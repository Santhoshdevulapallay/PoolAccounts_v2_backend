from collections import defaultdict
from dsm.common import getBankShortNames , getFincode,getFeesChargesName,add530hrstoDateString,generateWeekRange,no_data_found_df,int_names,removeInterestTail,getMergedAccts,getWeekDates ,getBankShortNamesList,get_month_start_end_dates
from dsm.revisions import getRevisionInterestUniqueDates,getShortfallUniqueDates
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
import ast
import chardet
def transformColumn(transactions_df ,col_name):
      # Replace empty strings ('') with NaN in the specified column
      transactions_df[col_name].replace('', np.nan, inplace=True)
      transactions_df = transactions_df.dropna(subset=[col_name])
      
      # If you want to remove leading and trailing spaces, you can use the strip() method instead:
      transactions_df[col_name] = transactions_df[col_name].str.strip()
      try:
            transactions_df[col_name] = pd.to_datetime(transactions_df[col_name], format='%d/%m/%Y')
      except:
            transactions_df[col_name] = pd.to_datetime(transactions_df[col_name], format='%d-%m-%Y')

      return transactions_df

def transformNumeric(transactions_df ,col_name):
      # Convert "Credit" and "Balance" columns to float
      transactions_df[col_name] = pd.to_numeric(transactions_df[col_name], errors='coerce').apply(lambda x: 0 if pd.isna(x) else x)
      return transactions_df

def match_dict_key(string, maps_list):
      all_fincodes=[]
      for vals in maps_list:
            # Remove the square brackets and split the string by comma, then strip whitespace from each element
            short_names_list = [name.strip() for name in vals['short_names'].strip('[]').split(',')]
            # Check if any short name is present in the input string
            found_names = [name for name in short_names_list if name in string]
            
            if found_names!=[''] and found_names:
                  # if already present then do not add to avoid duplicates
                  if vals['fin_code'] not in all_fincodes:
                        all_fincodes.append(vals['fin_code'])
           
      return all_fincodes

def sweepTxn(row):
      try:
            # check whether Credit Amount is zero
            if row['Credit Amount'] == 0 or row['Credit Amount'] == 0.0:
                  mapped_status=True
                  split_status='C'
                  is_sweep=True
            else: 
                  mapped_status=False
                  split_status=None
                  is_sweep=False
            BankStatement(
                  ValueDate=row['Value Date'],
                  PostDate=row['Post Date'],
                  Description=row['Description'],
                  Debit=row['Debit Amount'],
                  Credit=row['Credit Amount'],
                  Balance=row['Balance'],
                  IsMapped=mapped_status,
                  SplitStatus=split_status,
                  IsSweep=is_sweep,
                  BankType=row['BankType']
            ).save()
            return 
      except Exception as e:
            # writing error into a log file
            extractdb_errormsg(e)
            return
def bankRowSave(row ,is_sweep ):
      try:
            # check if already present then skip
            if BankStatement.objects.filter(ValueDate=row['Value Date'],PostDate=row['Post Date'],Description=row['Description'],Credit=row['Credit Amount']).count() > 0:
                  return None
            
            bank_obj=BankStatement(
                  ValueDate=row['Value Date'],
                  PostDate=row['Post Date'],
                  Description=row['Description'],
                  Debit=row['Debit Amount'],
                  Credit=row['Credit Amount'],
                  Balance=row['Balance'],
                  IsMapped=True,
                  SplitStatus='C', #complete amount mapped
                  IsSweep=is_sweep,
                  BankType=row['BankType']
                  )
      except Exception as e:
            extractdb_errormsg(e)
            return None
      
      bank_obj.save()
      return bank_obj

def mappedTxn(pool_obj ,bank_obj,acc_type):
      # payment details
      # if more than 2 bills mapped then map to oldest bill
      try:
            if acc_type != 'REVISION':
                  MappedBankEntries(
                        Pool_Acc=acc_type,
                        Fin_year=pool_obj[0]['Fin_year'],
                        Week_no=pool_obj[0]['Week_no'],
                        Amount=pool_obj[0]['Final_charges'],
                        Entity=getFeesChargesName(pool_obj[0]['Fin_code']) ,
                        ValueDate_fk=bank_obj,
                        Status='N', #notified,
                        Parent_id=pool_obj[0]['id'] #here id may be DSMBaseModel or NETAsBaseModel or REACBaseModel
                  ).save()
            else:
                  MappedBankEntries(
                        Pool_Acc=pool_obj[0]['Acc_type']+'_REVISION',
                        Amount=pool_obj[0]['Final_charges'],
                        Entity=getFeesChargesName(pool_obj[0]['Fin_code']) ,
                        ValueDate_fk=bank_obj,
                        Status='N', #notified,
                        Parent_id=pool_obj[0]['id'], #here id may be DSMBaseModel or NETAsBaseModel or REACBaseModel
                        Other_info=pool_obj[0]['Letter_date']
                  ).save() 
      except Exception as e:
            extractdb_errormsg(e)
      return

def bankStmtStore(request):
      try:
            formdata=json.loads(request.POST['formdata'])

            start_date=np.datetime64(add530hrstoDateString(formdata['start_date']).date())
            end_date=np.datetime64(add530hrstoDateString(formdata['end_date']).date())

            bank_type=formdata['bank']
            mappings_list=getBankShortNamesList()
            
            file=request.FILES['file']
            
            if bank_type == 'IB':  
                  
                  transactions_df=pd.read_excel(file,skiprows=21,skipfooter=4)
                 
                  transactions_df=transformColumn(transactions_df ,'Value Date')
                  transactions_df=transformColumn(transactions_df ,'Post Date')     
                  transactions_df = transactions_df.rename(columns=lambda x: x.replace(" ", ""))
            
                  
                  transactions_df = transactions_df[(transactions_df['ValueDate'] >= start_date) & (transactions_df['ValueDate'] <= end_date)]
                 
                  # Convert "Credit" and "Balance" columns to float
                  transactions_df=transformNumeric(transactions_df ,'DebitAmount')
                  transactions_df=transformNumeric(transactions_df ,'CreditAmount')
                  # rename columns
                  transactions_df.rename(columns={'ValueDate':'Value Date','DebitAmount':'Debit Amount','CreditAmount':'Credit Amount',"PostDate" :'Post Date'},inplace=True)
                  

            elif bank_type == 'SBI':

                  file_contents=file.read()
                  text_data = file_contents.decode('utf-8')
                  metadata, transactions = text_data.split('\nTxn Date', 1)
                 
                  # Read transactions into a DataFrame
                  transactions_df = pd.read_csv(StringIO(transactions), delimiter='\t')
                  
                  transactions_df = transactions_df.loc[:, ~transactions_df.columns.str.contains('^Unnamed')]
                  # Remove spaces from column names
                  transactions_df = transactions_df.rename(columns=lambda x: x.replace(" ", ""))
                  transactions_df=transformColumn(transactions_df ,'ValueDate')
                  # create a dummy column as Post Date

                  transactions_df.loc[:, 'Post Date'] = transactions_df['ValueDate']
                  transactions_df = transactions_df[(transactions_df['ValueDate'] >= start_date) & (transactions_df['ValueDate'] <= end_date)]
                  # Convert "Credit" and "Balance" columns to float
                  transactions_df=transformNumeric(transactions_df ,'Debit')
                  transactions_df=transformNumeric(transactions_df ,'Credit')      
                  # merge Description and Ref No to single column
                  transactions_df['Description'] = transactions_df['Description'] + transactions_df['RefNo./ChequeNo.'] 
                  # rename columns
                  transactions_df.rename(columns={'ValueDate':'Value Date', 'Debit':'Debit Amount','Credit':'Credit Amount'},inplace=True)
            else:
                  # file is neither SBI nor IB
                  return HttpResponse(extractdb_errormsg('Improper file is selected'),status=400)
            
            
            if not transactions_df.empty:
                  transactions_df['BankType'] = bank_type
                  # get merged accounts
                  # merge_qry=list(MergedAccounts.objects.filter(Q(end_date__isnull=True)|Q(end_date__gte=datetime.now())).values_list('merged_accounts',flat=True))
                  # merged_accs = ast.literal_eval(merge_qry[0])
                  # all_ancillary_accts=['SRAS','TRAS','MBAS','SCUC']
                  # # Subtract merged_accs from all_ancillary_accts
                  # unmerged_accts = [acct for acct in all_ancillary_accts if acct not in merged_accs]
                  #iterate through dataframe and check it maps with any billamount with DS,SRAS,TRAS etc
                  
                  for _,row in transactions_df.iterrows():
                        try:  
                              #deleted legacy dues false by prahrsha korangi on 141024 ##
                              common_qry=Q(PayableorReceivable='Payable',Final_charges=row['Credit Amount'],Is_disbursed=False)
                              # if description contains TRANSFER CREDIT then sweep it   DEBIT SWEEP
                              if any(keyword in row['Description'] for keyword in ['TRANSFER CREDIT', 'WITHDRAWAL TRANSFER']):
                                    # below True is to identify Sweep Txn
                                    bank_obj=bankRowSave(row,True)
                                    continue
                              # get all fin_codes corresponding to entity
                              
                              fin_codes = match_dict_key(row['Description'], mappings_list)
                            
                              # check dsm bills first
                              dsm_obj= DSMBaseModel.objects.filter(common_qry)
                              reac_obj=REACBaseModel.objects.filter(common_qry)
                              netas_obj=NetASBaseModel.objects.filter(common_qry)
                              revision_obj=RevisionBaseModel.objects.filter(common_qry)
                              
                              dsm_obj=list(dsm_obj.filter(Fin_code__in=fin_codes).order_by('id').values('Fin_year','Week_no','Entity','Final_charges','Fin_code','id'))

                              reac_obj=list(reac_obj.filter(Fin_code__in=fin_codes).order_by('id').values('Fin_year','Week_no','Entity','Final_charges','Fin_code','id'))

                              netas_obj=list(netas_obj.filter(Fin_code__in=fin_codes).order_by('id').values('Fin_year','Week_no','Entity','Final_charges','Fin_code','id'))

                              revision_obj=list(revision_obj.filter(Fin_code__in=fin_codes).order_by('id').values('Letter_date','Acc_type','Entity','Final_charges','Fin_code','id'))
                              if len(fin_codes):
                                    if len(dsm_obj):
                                          #store in bankstatement table till user approves
                                          bank_obj=bankRowSave(row,False)
                                          if bank_obj:
                                                mappedTxn(dsm_obj ,bank_obj,'DSM')

                                    elif len(reac_obj):
                                          reac_bank_obj=bankRowSave(row,False)
                                          if reac_bank_obj:
                                                mappedTxn(reac_obj ,reac_bank_obj,'REAC')

                                    elif len(netas_obj):
                                          netas_bank_obj=bankRowSave(row,False)
                                          if netas_bank_obj:
                                                mappedTxn(netas_obj ,netas_bank_obj,'NET_AS')

                                    elif len(revision_obj):
                                        
                                          revisions_bank_obj=bankRowSave(row,False)
                                          if revisions_bank_obj:
                                                mappedTxn(revision_obj ,revisions_bank_obj,'REVISION')
                                    else:
                                          # if not mapped then store with Mapped status to False
                                          sweepTxn(row)
                              else:
                                    sweepTxn(row)

                        except Exception as e:
                              print(e)
                              extractdb_errormsg(e)

            return JsonResponse('success',safe=False)

      except Exception as e:
            print(e)
            return HttpResponse(extractdb_errormsg(e),status=400)

def reconciledDates(request):
      try:
            reconciled_dates=list(BankRecon.objects.order_by('-Startdate').all().values())
            return JsonResponse(reconciled_dates,safe=False)
      except Exception as e:
            return HttpResponse(extractdb_errormsg(e),status=400)
      
def monthBankRecon(request):
      try:
            formdata=json.loads(request.POST['formdata'])
            start_date,end_date=get_month_start_end_dates(formdata['selected_month'])
           
            bank_type=formdata['bank']
            file=request.FILES['file']
            
            if bank_type == 'IB':  
                  transactions_df=pd.read_excel(file,skiprows=21,skipfooter=4)
                  
                  transactions_df=transformColumn(transactions_df ,'Value Date')
                  transactions_df=transformColumn(transactions_df ,'Post Date')
                  
                  transactions_df = transactions_df[(transactions_df['Value Date'] >= start_date) & (transactions_df['Value Date'] <= end_date)]
                 
                  # Convert "Credit" and "Balance" columns to float
                  transactions_df=transformNumeric(transactions_df ,'Debit Amount')
                  transactions_df=transformNumeric(transactions_df ,'Credit Amount')
                  
            elif bank_type == 'SBI':
                  
                  file_contents=file.read()
                  text_data = file_contents.decode('utf-8')
                  metadata, transactions = text_data.split('\nTxn Date', 1)

                  # Read transactions into a DataFrame
                  transactions_df = pd.read_csv(StringIO(transactions), delimiter='\t')
                  
                  transactions_df = transactions_df.loc[:, ~transactions_df.columns.str.contains('^Unnamed')]
                  # Remove spaces from column names
                  transactions_df = transactions_df.rename(columns=lambda x: x.replace(" ", ""))
                  transactions_df=transformColumn(transactions_df ,'ValueDate')
                  # create a dummy column as Post Date

                  transactions_df.loc[:, 'Post Date'] = transactions_df['ValueDate']
                  transactions_df = transactions_df[(transactions_df['ValueDate'] >= start_date) & (transactions_df['ValueDate'] <= end_date)]
                  
                  # Convert "Credit" and "Balance" columns to float
                  transactions_df=transformNumeric(transactions_df ,'Debit')
                  transactions_df=transformNumeric(transactions_df ,'Credit')      
                  # merge Description and Ref No to single column
                  transactions_df['Description'] = transactions_df['Description'] + transactions_df['RefNo./ChequeNo.'] 
            else:
                  # file is neither SBI nor IB
                  return HttpResponse(extractdb_errormsg('Improper file is selected'),status=400)
            
            # Remove trailing hyphens from the 'column_name' column
            transactions_df['Description'] = transactions_df['Description'].str.rstrip('-')
            #remove spaces from column string
            transactions_df['Description']=transactions_df['Description'].str.replace(' ','')
            
            # get stored bank txns
            stored_bank_df=pd.DataFrame(BankStatement.objects.filter(ValueDate__range=[start_date,end_date],BankType=bank_type).values('ValueDate', 'Description','Debit', 'Credit', 'Balance', 'PostDate'))
            # convert transactions_df['Value Date'] to datetime
            stored_bank_df['ValueDate'] = pd.to_datetime(stored_bank_df['ValueDate'])
            stored_bank_df['Description']=stored_bank_df['Description'].str.replace(' ','')

           
            merged_df = pd.merge(transactions_df, stored_bank_df, how='left', indicator=True, on=['ValueDate', 'Description'])
            
            diff_df = merged_df[merged_df['_merge'] == 'left_only'].drop(columns=['_merge'])
            # replace nan with None
            diff_df=diff_df.fillna('')
            # empty means all are stored in database
            if diff_df.empty:
                  try:
                        BankRecon(
                              Startdate=start_date,
                              Enddate=end_date,
                              Banktype=bank_type,
                              Is_reconciled=True
                        ).save()
                        return JsonResponse({'status':True},safe=False)
                  
                  except Exception as e:
                        extractdb_errormsg(e)
                        return JsonResponse({'status':False,'records':str(e)},safe=False)
                  
            return JsonResponse({'status':False, 'records':diff_df.to_dict('records')},safe=False)

      except Exception as e:
            extractdb_errormsg(e)
            if "utf-8' codec can't decode" in str(e):
                  return JsonResponse({'status':False,'records':'Please download the Bank Statement again and upload.'})
            else:
                  return JsonResponse({'status':False,'records':str(e)},safe=False)
def bankStmtStatus(request):
      try:
            bank_stmt_obj=BankStatement.objects.all()
              
            total_transactions = list(bank_stmt_obj.values('ValueDate').annotate(date=F('ValueDate'), count=Count('ValueDate')).order_by('ValueDate'))

            mapped_transactions=list(bank_stmt_obj.filter(IsMapped=True,SplitStatus='C',IsSweep=False).values('ValueDate').annotate(date=F('ValueDate'), count=Count('ValueDate')).order_by('ValueDate'))

            # mapped but sweep transaction like DEBT TRANSFER and CREDIT TRANSFER
            sweep_transactions=list(bank_stmt_obj.filter(IsMapped=True,SplitStatus='C',IsSweep=True).values('ValueDate').annotate(date=F('ValueDate'), count=Count('ValueDate')).order_by('ValueDate'))
            # Not Mapped or Mapped But not fully
            notmapped_transactions=list(bank_stmt_obj.filter(Q(IsMapped=False) | ( Q(IsMapped=True) & Q(SplitStatus='P') ) ).values('ValueDate').annotate(date=F('ValueDate'), count=Count('ValueDate')).order_by('ValueDate'))

            # Combine transactions based on date
            combined_transactions = defaultdict(lambda: {'total_count': 0, 'mapped_count': 0 ,'sweep_count':0})

            for transaction in total_transactions:
                  combined_transactions[transaction['date']]['total_count'] += transaction['count']

            for transaction in mapped_transactions:
                  combined_transactions[transaction['date']]['mapped_count'] += transaction['count']

            for sw_transaction in sweep_transactions:
                  combined_transactions[sw_transaction['date']]['sweep_count'] += sw_transaction['count']

            # this format is for fullcalendar
            # 'color': '#1ba0f2'
            total_transactions = [{'date': item['date'], 'title': 'Total Txns:'+ str(item['count']), 'color': '#1ba0f2' } for item in total_transactions]

            # # 'color': '#16a855'
            mapped_transactions = [{'date': item['date'], 'title': 'Mapped Txns:'+str(item['count']),'color': '#16a855' } for item in mapped_transactions]

            sweep_transactions = [{'date': item['date'], 'title': 'Sweep Txns:'+str(item['count']),'color': '#DA49F4' } for item in sweep_transactions]

            # # 'color': '#c93416'
            notmapped_transactions = [{'date': item['date'], 'title': 'NotMapped Txns:'+str(item['count']),'color': '#c93416' } for item in notmapped_transactions]
            
            all_transactions=total_transactions+mapped_transactions+notmapped_transactions+sweep_transactions

            return JsonResponse([all_transactions,getRevisionInterestUniqueDates(),getShortfallUniqueDates()],safe=False)

      except Exception as e:
            return HttpResponse(extractdb_errormsg(e),status=400)
      
def getPendingBills(acc_type):
      try: 
            common_qry=Q(PayableorReceivable='Payable') & Q(Effective_end_date__isnull = True) & Q(Revision_no=0) & Q(Legacy_dues=False)
            if acc_type == 'DSM':
                  # DSM all pending payments , 
                  bills_df=pd.DataFrame(DSMBaseModel.objects.filter(common_qry ).values('Fin_year','Week_no','Fin_code','Final_charges','payments__Paid_amount','id'),columns=['Fin_year','Week_no','Fin_code','Final_charges','payments__Paid_amount','id'])
                  
                  # rename paidamount
                  bills_df.rename(columns={'payments__Paid_amount':'Paid_amount'},inplace=True)

            elif acc_type == 'NET_AS':
                  # DSM all pending payments , 
                  bills_df=pd.DataFrame(NetASBaseModel.objects.filter(common_qry).values('Fin_year','Week_no','Fin_code','Final_charges','netaspayments__Paid_amount','id'),columns=['Fin_year','Week_no','Fin_code','Final_charges','netaspayments__Paid_amount','id'])
                  
                  # rename paidamount
                  bills_df.rename(columns={'netaspayments__Paid_amount':'Paid_amount'},inplace=True)
            elif acc_type == 'SRAS':
                  # SRAS all pending payments , 
                  bills_df=pd.DataFrame(SRASBaseModel.objects.filter(common_qry).values('Fin_year','Week_no','Fin_code','Final_charges','sraspayments__Paid_amount','id'),columns=['Fin_year','Week_no','Fin_code','Final_charges','sraspayments__Paid_amount','id'])
                  # rename paidamount
                  bills_df.rename(columns={'sraspayments__Paid_amount':'Paid_amount'},inplace=True)
            elif acc_type == 'TRAS':
                  # TRAS all pending payments , 
                  bills_df=pd.DataFrame(TRASBaseModel.objects.filter(common_qry).values('Fin_year','Week_no','Fin_code','Final_charges','traspayments__Paid_amount','id'),columns=['Fin_year','Week_no','Fin_code','Final_charges','traspayments__Paid_amount','id'])
                  # rename paidamount
                  bills_df.rename(columns={'traspayments__Paid_amount':'Paid_amount'},inplace=True)

            elif acc_type == 'MBAS':
                  # MBAS all pending payments , 
                  bills_df=pd.DataFrame(MBASBaseModel.objects.filter(common_qry).values('Fin_year','Week_no','Fin_code','Final_charges','mbaspayments__Paid_amount','id'),columns=['Fin_year','Week_no','Fin_code','Final_charges','mbaspayments__Paid_amount','id'])
                  # rename paidamount
                  bills_df.rename(columns={'mbaspayments__Paid_amount':'Paid_amount'},inplace=True)

            elif acc_type == 'REAC':
                  # REAC all pending payments , 
                  bills_df=pd.DataFrame(REACBaseModel.objects.filter(common_qry).values('Fin_year','Week_no','Fin_code','Final_charges','reacpayments__Paid_amount','id'),columns=['Fin_year','Week_no','Fin_code','Final_charges','reacpayments__Paid_amount','id'])
                  # rename paidamount
                  bills_df.rename(columns={'reacpayments__Paid_amount':'Paid_amount'},inplace=True)

            elif acc_type == 'CONG':
                  # REAC all pending payments , 
                  bills_df=pd.DataFrame(CONGBaseModel.objects.filter(common_qry).values('Fin_year','Week_no','Fin_code','Final_charges','congpayments__Paid_amount','id'),columns=['Fin_year','Week_no','Fin_code','Final_charges','congpayments__Paid_amount','id'])
                  # rename paidamount
                  bills_df.rename(columns={'congpayments__Paid_amount':'Paid_amount'},inplace=True)
            elif acc_type == 'IR':
                  # IR all pending payments , 
                  bills_df=pd.DataFrame(IRBaseModel.objects.filter(Q(PayableorReceivable='Payable') & Q(Revision_no=0)).values('Fin_year','Week_no','Fin_code','Final_charges','irpayments__Paid_amount','id'),columns=['Fin_year','Week_no','Fin_code','Final_charges','irpayments__Paid_amount','id'])
                  # rename paidamount
                  bills_df.rename(columns={'irpayments__Paid_amount':'Paid_amount'},inplace=True)
            elif acc_type == 'Interest':
                  # Interest all pending payments , 
                  bills_df=pd.DataFrame(InterestBaseModel.objects.all().values('Fin_code','Final_charges','id','Entity'),columns=['Fin_code','Final_charges','id','Entity'])
                  payments_df=pd.DataFrame(InterestPayments.objects.all().values('Paid_amount','Fin_code'),columns=['Paid_amount','Fin_code'])
                  merged_df=pd.merge(bills_df,payments_df,on='Fin_code',how='left')
                  merged_df.fillna(0)

                  final_bills_df = merged_df[merged_df['Final_charges'] - merged_df['Paid_amount'] > 0]

                  bills_df['Fin_year']=None
                  bills_df['Week_no']=None
                  
                  # rename paidamount
                  bills_df.rename(columns={'interestpayments__Paid_amount':'Paid_amount'},inplace=True)

            elif acc_type == 'DSM_REVISION':
                  # DSM all pending payments , 
                  bills_df=pd.DataFrame(RevisionBaseModel.objects.filter(Q(PayableorReceivable='Payable')).values('Fin_code','Final_charges','revisionpayments__Paid_amount','id','Acc_type'),columns=['Fin_code','Final_charges','revisionpayments__Paid_amount','id','Acc_type'])
                  
                  # rename paidamount
                  bills_df.rename(columns={'revisionpayments__Paid_amount':'Paid_amount' ,'Acc_type':'Pool_acc'},inplace=True)
                  bills_df['Paid_amount'] = bills_df['Paid_amount'].fillna(0)
                  
                  grouped_bills_df = bills_df.groupby(['Pool_acc', 'Fin_code','Final_charges','id'])['Paid_amount'].sum()
                  grouped_bills_df=grouped_bills_df.reset_index()
                  
                  # add Fin_year and Week_no columns
                  grouped_bills_df['Fin_year']=None
                  grouped_bills_df['Week_no']=None

                  # True only if amount is pending else  drop
                  return grouped_bills_df[grouped_bills_df['Final_charges'] - grouped_bills_df['Paid_amount'] > 0]
                  
            else:
                  pass
            
            # because for Interest already update Pool_acc so no need to do it again
            if acc_type != 'Interest':
                  bills_df['Pool_acc']=acc_type

            bills_df['Paid_amount'] = bills_df['Paid_amount'].fillna(0)
            # to retain all columns using groupby
            grouped_bills_df = bills_df.groupby(['Pool_acc','Fin_year', 'Week_no', 'Fin_code','Final_charges','id'])['Paid_amount'].sum()
            grouped_bills_df=grouped_bills_df.reset_index()
           
            # True only if amount is pending else  drop
            grouped_bills_df['Final_charges']=grouped_bills_df['Final_charges']-grouped_bills_df['Paid_amount']
            final_bills_df = grouped_bills_df[grouped_bills_df['Final_charges'] > 0]
           
            return final_bills_df
      
      except Exception as e:
            extractdb_errormsg(e)
            return pd.DataFrame([str(e)])

def calOutstandingAmount(final_charges_lst):
      amount_to_be_paid=0
      amount_paid=0
      if final_charges_lst:
            for pay in final_charges_lst:
                  amount_to_be_paid=pay['Final_charges'] if  pay['Final_charges'] else 0
                 
                  amount_paid+=pay['Paid_amount'] if  pay['Paid_amount'] else 0 
      
      return amount_to_be_paid-amount_paid

def checkFinyearWeekno(in_data):
      # no fin_year or week_no selected then return 0
      if  (in_data['Fin_year'] == None or in_data['Fin_year'] == ''):
            return 0
      
      if  (in_data['Week_no'] == None or in_data['Week_no'] ==''):
            return 0
      
      return 0
def getBillAmount(request):
      try:
            in_data=json.loads(request.body)
            fin_code= getFincode(in_data['Entity'])
            common_qry=Q(Fin_year=in_data['Fin_year'],Week_no=in_data['Week_no'],Fin_code=fin_code,PayableorReceivable='Payable',Revision_no=0)
            common_qry1=Q(Fin_year=in_data['Fin_year'],Week_no=in_data['Week_no'],Fin_code=fin_code,PayableorReceivable='Payable')
            
            if  fin_code:
                  if in_data['AccType'] == 'DSM':
                        try:
                              final_charges_lst=list(DSMBaseModel.objects.filter(common_qry).values('Final_charges','payments__Paid_amount'))
                        except:
                              return JsonResponse(0,safe=False)
                        # rename payments__Paid_amount to Paid_amount
                        
                        for item in final_charges_lst:
                              item['Paid_amount'] = item.pop('payments__Paid_amount')
                        final_charges=calOutstandingAmount(final_charges_lst)

                  elif in_data['AccType'] == 'REAC':
                        try:
                              final_charges_lst=list(REACBaseModel.objects.filter(common_qry).values('Final_charges','reacpayments__Paid_amount'))
                        except:
                              return JsonResponse(0,safe=False)
                        
                        # rename netaspayments__Paid_amount to Paid_amount
                        for item in final_charges_lst:
                              item['Paid_amount'] = item.pop('reacpayments__Paid_amount')
                        final_charges=calOutstandingAmount(final_charges_lst)

                  elif in_data['AccType'] == 'NET_AS':
                        try:
                              final_charges_lst=list(NetASBaseModel.objects.filter(common_qry).values('Final_charges','netaspayments__Paid_amount'))
                        except:
                              return JsonResponse(0,safe=False)
                        # rename netaspayments__Paid_amount to Paid_amount
                        
                        for item in final_charges_lst:
                              item['Paid_amount'] = item.pop('netaspayments__Paid_amount')
                        final_charges=calOutstandingAmount(final_charges_lst)
                  
                  elif in_data['AccType'] == 'Legacy':
                        try:
                              final_charges_lst=list(LegacyBaseModel.objects.filter(common_qry1).values('Final_charges','legacypayments__Paid_amount'))
                        except:
                              return JsonResponse(0,safe=False)
                        # rename netaspayments__Paid_amount to Paid_amount
                        
                        for item in final_charges_lst:
                              item['Paid_amount'] = item.pop('legacypayments__Paid_amount')
                        final_charges=calOutstandingAmount(final_charges_lst)

                  elif in_data['AccType'] == 'IR':
                        try:
                              final_charges_lst=list(IRBaseModel.objects.filter(common_qry).values('Final_charges','irpayments__Paid_amount'))
                        except:
                              return JsonResponse(0,safe=False)
                        # rename irpayments__Paid_amount to Paid_amount
                        for item in final_charges_lst:
                              item['Paid_amount'] = item.pop('irpayments__Paid_amount')
                        final_charges=calOutstandingAmount(final_charges_lst)

                  elif in_data['AccType'] == 'Interest':
                        try:
                              final_charges_lst=list(InterestBaseModel.objects.filter(Fin_code=fin_code,Letter_date=in_data['Week_no']).order_by('-Letter_date').values('Final_charges','interestpayments__Paid_amount'))
                              #final_charges=final_charges_lst[0]['Final_charges']
                        except:
                              return JsonResponse(0,safe=False)
                        # rename irpayments__Paid_amount to Paid_amount
                        for item in final_charges_lst:
                              item['Paid_amount'] = item.pop('interestpayments__Paid_amount')
                        final_charges=calOutstandingAmount(final_charges_lst)
                      
                  elif 'REVISION' in in_data['AccType'] :
                        try:
                              # see here Week_no means Revision_Dates dont confuse
                              final_charges_lst=list(RevisionBaseModel.objects.filter(Acc_type=in_data['AccType'],Letter_date=in_data['Week_no'], Fin_code=fin_code,PayableorReceivable='Payable').values('Final_charges','revisionpayments__Paid_amount'))
                        except:
                              return JsonResponse(0,safe=False)
                        # rename revisionpayments__Paid_amount to Paid_amount

                        for item in final_charges_lst:
                              item['Paid_amount'] = item.pop('revisionpayments__Paid_amount')

                        final_charges=calOutstandingAmount(final_charges_lst)

                  elif in_data['AccType'] == 'Shortfall':
                        try:
                              final_charges_lst=list(ShortfallBaseModel.objects.filter(Letter_date=in_data['Week_no'],Fin_code=fin_code).values('Final_charges','shortfallpayments__Paid_amount'))
                        except:
                              return JsonResponse(0,safe=False)
                        # rename netaspayments__Paid_amount to Paid_amount
                        
                        for item in final_charges_lst:
                              item['Paid_amount'] = item.pop('shortfallpayments__Paid_amount')
                        final_charges=calOutstandingAmount(final_charges_lst)
                  
                  elif in_data['AccType'] == 'CONG':
                        try:
                              final_charges_lst=list(CONGBaseModel.objects.filter(common_qry).values('Final_charges','congpayments__Paid_amount'))
                        except:
                              return JsonResponse(0,safe=False)
                        # rename sraspayments__Paid_amount to Paid_amount
                        for item in final_charges_lst:
                              item['Paid_amount'] = item.pop('congpayments__Paid_amount')
                        final_charges=calOutstandingAmount(final_charges_lst)

                  elif in_data['AccType'] == 'SRAS':
                        try:
                              final_charges_lst=list(SRASBaseModel.objects.filter(common_qry).values('Final_charges','sraspayments__Paid_amount'))
                        except:
                              return JsonResponse(0,safe=False)
                        # rename sraspayments__Paid_amount to Paid_amount
                        for item in final_charges_lst:
                              item['Paid_amount'] = item.pop('sraspayments__Paid_amount')
                        final_charges=calOutstandingAmount(final_charges_lst)

                  elif in_data['AccType'] == 'TRAS':
                        try:
                              final_charges_lst=list(TRASBaseModel.objects.filter(common_qry).values('Final_charges','traspayments__Paid_amount'))
                        except:
                              return JsonResponse(0,safe=False)
                        for item in final_charges_lst:
                              item['Paid_amount'] = item.pop('traspayments__Paid_amount')

                        final_charges=calOutstandingAmount(final_charges_lst)

                  elif in_data['AccType'] == 'MBAS':
                        try:
                              final_charges_lst=list(MBASBaseModel.objects.filter(common_qry).values('Final_charges','mbaspayments__Paid_amount'))
                        except:
                              return JsonResponse(0,safe=False)
                        
                        for item in final_charges_lst:
                              item['Paid_amount'] = item.pop('mbaspayments__Paid_amount')
                        final_charges=calOutstandingAmount(final_charges_lst)

                  else:
                        final_charges=0 

                  return JsonResponse(final_charges,safe=False)
            else: 
                  return JsonResponse('',safe=False)
      
      except Exception as e:
            return HttpResponse(extractdb_errormsg(e),status=400)
      


def getBankTxns(request):
      try:
            date_str=json.loads(request.body)['date']
            date_obj=add530hrstoDateString(date_str).date()

            unmapped_txns_df=pd.DataFrame(BankStatement.objects.filter(Q(ValueDate=date_obj), ( Q(IsMapped=False) | ( Q(IsMapped=True) & Q(SplitStatus='P')) )).values('ValueDate','Description','Credit','id') ,columns=['ValueDate','Description','Credit','id'])
            
            mapped_txns_df=pd.DataFrame(MappedBankEntries.objects.filter(ValueDate_fk__ValueDate=date_obj,Status__in=['N','A']).values('ValueDate_fk','Amount','ValueDate_fk__SplitStatus'),columns=['ValueDate_fk','Amount','ValueDate_fk__SplitStatus'])
            
            # mapped_txns_df=mapped_txns_df[mapped_txns_df['ValueDate_fk__SplitStatus']!='P']

            merged_df=unmapped_txns_df.merge(mapped_txns_df ,left_on='id', right_on='ValueDate_fk' ,how='left')
            
            # groupby ValueDate_fk and Sum the Amount
            merged_df['Amount'].fillna(0, inplace=True)
            
            # Group by 'ValueDate' and 'ValueDate_fk' and sum the 'Amount' column
            grouped_df = merged_df.groupby(['ValueDate','Description','Credit' ,'id'])['Amount'].sum().reset_index()
            grouped_df['Balance_left']=grouped_df['Credit'] - grouped_df['Amount']
            # grouped_df.rename(columns={'Amount':'Balance_left'},inplace=True)

            mapped_txns=list(MappedBankEntries.objects.filter(ValueDate_fk__ValueDate=date_obj).order_by('Entity').values('ValueDate_fk__ValueDate','ValueDate_fk__Description','Pool_Acc','Fin_year','Week_no','Amount','Entity','Other_info'))

            # modify unmapped_txns to compatible with front end
            unmapped_txns=grouped_df.to_dict(orient='records')
            # mappings_list=getBankShortNames()
            mappings_list=getBankShortNamesList()
            
            final_dsm_df=getPendingBills('DSM')
            
            final_netas_df=getPendingBills('NET_AS')
            # final_sras_df=getPendingBills('SRAS')
            # final_tras_df=getPendingBills('TRAS')
            # final_mbas_df=getPendingBills('MBAS')
            final_reac_df=getPendingBills('REAC')
            final_cong_df=getPendingBills('CONG')
            final_ir_df=getPendingBills('IR')
            final_dsm_revision_df=getPendingBills('DSM_REVISION')
            
            # Interest of all accounts
            # final_int_df=getPendingBills('Interest')
            result_df=pd.concat([final_dsm_df,final_netas_df,final_reac_df,final_cong_df,final_ir_df,final_dsm_revision_df])
            
            for row in unmapped_txns:
                  # check dsm bills first
                  temp_arr=[]
                  fin_codes = match_dict_key(row['Description'], mappings_list) 
                  if fin_codes:
                        for sub_fin in fin_codes:
                              temp_df=result_df[result_df['Fin_code']==sub_fin]  
                              if not temp_df.empty:
                                    for _,sub_row in temp_df.iterrows():
                                          temp_arr.append({'checked':False,'AccType':sub_row['Pool_acc'],'Entity': getFeesChargesName(sub_row['Fin_code']),'Fin_year': sub_row['Fin_year'], 'Week_no': sub_row['Week_no'] ,'Amount':sub_row['Final_charges'],'OtherInfo':'' ,'id':sub_row['id']})
                  else:
                        # match values within a range of ±1 rather than exact matches in a DataFrame column 
                        temp_df = result_df[(result_df['Final_charges'] >= row['Credit'] - 1) & (result_df['Final_charges'] <= row['Credit'] + 1)]

                        if not temp_df.empty:
                              for _,sub_row in temp_df.iterrows():
                                    temp_arr.append({'checked':False,'AccType':sub_row['Pool_acc'],'Entity': getFeesChargesName(sub_row['Fin_code']),'Fin_year': sub_row['Fin_year'], 'Week_no': sub_row['Week_no'] ,'Amount':sub_row['Final_charges'],'OtherInfo':'' ,'id':sub_row['id']})
                                    
                  row['isExpand']=False
                  row['userFields'] = temp_arr

            # get all pool account types
            all_pool_accs=list(PoolAccountTypes.objects.filter(Q(end_date__isnull=True)|Q(end_date__gte=datetime.now())).values_list('acc_types',flat=True))
            merged_accs=getMergedAccts()
            result_accs=[acc for acc in all_pool_accs if acc not in merged_accs ]
            result_accs = sorted(result_accs)

            return JsonResponse([unmapped_txns,mapped_txns ,getFCNames(),result_accs],safe=False)

      except Exception as e:
            return HttpResponse(extractdb_errormsg(e),status=400)
      
def getParentModelID(pay):
      try:
            
            fin_code=getFincode(pay['Entity'])
         
            if pay['AccType'] == 'DSM':
                  try:
                        # here Entity using becuase firm and infirm may have Same Fin_code 
                        try:
                              dsm_id=DSMBaseModel.objects.get(Fin_year=pay['Fin_year'],Week_no=pay['Week_no'],Fin_code=fin_code,Final_charges=pay['Amount']).id
                        except:
                              # lets say user not paid the full amount like partial payment in that case above try block fails and execute the current except block.Here not considering the amount .
                              dsm_id=DSMBaseModel.objects.get(Fin_year=pay['Fin_year'],Week_no=pay['Week_no'],Fin_code=fin_code).id
                        pay['id']=dsm_id
                  except:
                        return False , pay
                  
            elif pay['AccType'] == 'NET_AS':
                  try:
                        # here Entity using becuase firm and infirm may have Same Fin_code 
                        try:
                              netas_id=NetASBaseModel.objects.get(Fin_year=pay['Fin_year'],Week_no=pay['Week_no'],Fin_code=fin_code,Final_charges=pay['Amount']).id
                        except:
                              netas_id=NetASBaseModel.objects.get(Fin_year=pay['Fin_year'],Week_no=pay['Week_no'],Fin_code=fin_code).id
                        pay['id']=netas_id
                  except:
                        return False , pay
            
            elif pay['AccType'] == 'Legacy':
                  try:
                        # here Entity using becuase firm and infirm may have Same Fin_code 
                        try:
                              legacy_id=LegacyBaseModel.objects.get(Fin_year=pay['Fin_year'],Week_no=pay['Week_no'],Fin_code=fin_code,Final_charges=pay['Amount']).id
                        except:
                              legacy_id=LegacyBaseModel.objects.get(Fin_year=pay['Fin_year'],Week_no=pay['Week_no'],Fin_code=fin_code).id
                        pay['id']=legacy_id
                  except:
                        return False , pay
            
            elif pay['AccType'] == 'Shortfall':
                  try:
                        # here Entity using becuase firm and infirm may have Same Fin_code 
                        try:
                              shortfall_id= ShortfallBaseModel.objects.get(Letter_date=pay['Week_no'],Fin_code=fin_code,Final_charges=pay['Amount']).id
                        except:
                              shortfall_id=ShortfallBaseModel.objects.get(Letter_date=pay['Week_no'],Fin_code=fin_code).id
                        pay['id'] = shortfall_id
                  except:
                        return False , pay

            elif pay['AccType'] == 'REAC':
                  try:
                        try:
                              reac_id=REACBaseModel.objects.get(Fin_year=pay['Fin_year'],Week_no=pay['Week_no'],Fin_code=fin_code,Final_charges=pay['Amount']).id
                        except:
                              reac_id=REACBaseModel.objects.get(Fin_year=pay['Fin_year'],Week_no=pay['Week_no'],Fin_code=fin_code).id
                        pay['id']=reac_id
                  except:
                        return False , pay

            elif pay['AccType'] == 'MBAS':
                  try:
                        try:
                              mbas_id=MBASBaseModel.objects.get(Fin_year=pay['Fin_year'],Week_no=pay['Week_no'],Fin_code=fin_code,Final_charges=pay['Amount']).id
                        except:
                              mbas_id=MBASBaseModel.objects.get(Fin_year=pay['Fin_year'],Week_no=pay['Week_no'],Fin_code=fin_code,Letter_date = pay['Week_no']).id
                        pay['id']=mbas_id
                  except:
                        return False , pay

            elif 'REVISION' in pay['AccType'] :
                  try:
                        try:
                              revision_id=RevisionBaseModel.objects.get(Acc_type=pay['AccType'],Fin_code=fin_code,Final_charges=pay['Amount'],Letter_date=pay['Week_no']).id
                        except:
                              revision_id=RevisionBaseModel.objects.get(Acc_type=pay['AccType'],Fin_code=fin_code,Letter_date=pay['Week_no']).id
                        pay['id']=revision_id
                  except:
                        return False , pay
                  
            elif pay['AccType'] == 'Interest':
                  try:
                        # not considering amount just mapping all payments to one entity
                        interest_id=InterestBaseModel.objects.get(Fin_code=fin_code,Letter_date=pay['Week_no']).id
                        pay['id']=interest_id
                  except:
                        return False , pay
                  
            elif pay['AccType'] == 'CONG':
                  try:
                        try:
                              cong_id=CONGBaseModel.objects.get(Fin_code=fin_code,Final_charges=pay['Amount']).id
                        except:
                              cong_id=CONGBaseModel.objects.get(Fin_code=fin_code).id

                        pay['id']=cong_id
                  except:
                        return False , pay
                  
            elif pay['AccType'] in ['EXCESS','F&C','SWEEP','Others']:
                  pay['id']=None
                  # only for excess payments and Fees and Charges ,SWEEP ,Others
                  return True,pay
            
            elif pay['AccType'] == 'SRAS':
                  try:
                        try:
                              sras_id=SRASBaseModel.objects.get(Fin_year=pay['Fin_year'],Week_no=pay['Week_no'],Fin_code=fin_code,Final_charges=pay['Amount']).id
                        except:
                              sras_id=SRASBaseModel.objects.get(Fin_year=pay['Fin_year'],Week_no=pay['Week_no'],Fin_code=fin_code).id

                        pay['id']=sras_id
                  except:
                        return False , pay
                  
            elif pay['AccType'] == 'TRAS':
                  try:
                        try:
                              tras_id=TRASBaseModel.objects.get(Fin_year=pay['Fin_year'],Week_no=pay['Week_no'],Fin_code=fin_code,Final_charges=pay['Amount']).id
                        except:
                              tras_id=TRASBaseModel.objects.get(Fin_year=pay['Fin_year'],Week_no=pay['Week_no'],Fin_code=fin_code).id
                        pay['id']=tras_id
                  except:
                        return False , pay
                  
            else:
                  return False , pay
            
            return True, pay
      except Exception as e:
            extractdb_errormsg(e)
            return 
      
def saveBankPayments(request):
      try:
            formdata=json.loads(request.body)
            return_msg='success'
            
            for row in formdata:
                  # get the total balance wrt txn , ignore Those statments are Rejected (R) by user 
                  already_mapped_amt=MappedBankEntries.objects.filter(ValueDate_fk=row['id']).exclude(Status='R').values('ValueDate_fk').annotate(total_amount=Sum('Amount'))
                  # no entry found means no txn mapped so assign total_amount
                  mapped_amount =already_mapped_amt[0]['total_amount'] if len(already_mapped_amt) else 0
                  left_over_bal=float(row['Credit']) - mapped_amount  
                  for pay in row['userFields']:
                        # AccType not null means atleast one entry mapped
                        if pay['AccType']!='' and pay['checked'] == True:
                              check,pay=getParentModelID(pay)
                              if check:
                                    # Now check mapped_amount should be less than credited amount - (mapped_amt + entered_amt)
                                    if left_over_bal - ( float(pay['Amount']) ) >= 0: 
                                          if check_string(pay['Week_no']) :
                                                wk_no = pay['Week_no'] 
                                                other_info = pay['OtherInfo']
                                          else:
                                                wk_no = 0
                                                other_info = pay['Week_no']
                                          if ( pay['AccType'] not in ['Interest','EXCESS','F&C','SWEEP','Others'] ) and ('REVISION' not in pay['AccType']):
                                                MappedBankEntries(
                                                      Pool_Acc=pay['AccType'],
                                                      Entity=pay['Entity'],
                                                      Fin_year=pay['Fin_year'],
                                                      Week_no=wk_no,
                                                      Amount=pay['Amount'],
                                                      Other_info=other_info,
                                                      ValueDate_fk=BankStatement.objects.get(id=row['id']), # here ID refers to BankTxn id 
                                                      Status='N',  #notified
                                                      Parent_id=pay['id'] #here id may be DSMBaseModel or NETAsBaseModel or REACBaseModel
                                                ).save()
                                          else:
                                                entity='' if pay['AccType'] == 'Others' else pay['Entity']
                                                
                                                MappedBankEntries(
                                                      Pool_Acc=pay['AccType'],
                                                      Entity=entity,
                                                      Fin_year='',
                                                      Week_no=None,
                                                      Amount=pay['Amount'],
                                                      Other_info=pay['OtherInfo'],
                                                      ValueDate_fk=BankStatement.objects.get(id=row['id']), # here ID refers to BankTxn id 
                                                      Status='N',  #notified
                                                      Parent_id=pay['id'] #here id may be DSMBaseModel or NETAsBaseModel or REACBaseModel
                                                ).save()

                                          # now update the mapped amount
                                          left_over_bal-=pay['Amount']
                                          bank_qry_obj=BankStatement.objects.filter(id=row['id']) # here ID refers to BankTxn id 
                                          #change the status of Bank Statement to Mapped  , Skip uptill 1 rupee
                                          if (left_over_bal <= 1):
                                                # full amount Mapped C (Complete)
                                                bank_qry_obj.update(
                                                      IsMapped=True,
                                                      SplitStatus='C'
                                                )
                                          else:
                                                # Mapped but Full Amount not mapped ,only P (Partial)
                                                bank_qry_obj.update(IsMapped=True, SplitStatus='P')
                                    else:
                                          return_msg ='Balance left is not enough to map'
                              else:
                                    return_msg=pay['Entity']+ ' Record Not Present ,Please check'
            return JsonResponse(return_msg,safe=False)
      except Exception as e:
            return HttpResponse(extractdb_errormsg(e),status=400)
    
def pendingApprovals(request):
      try:
            # mapped txns but not approved
            mapped_entries=list(MappedBankEntries.objects.filter(Status='N' ).order_by('-ValueDate_fk_id__ValueDate').values('Pool_Acc','Fin_year','Week_no','Amount','Entity','Other_info','id','ValueDate_fk_id__Description' ,'ValueDate_fk_id__ValueDate','ValueDate_fk_id__id','ValueDate_fk_id__BankType','Parent_id'))
            
            return JsonResponse(mapped_entries,safe=False)

      except Exception as e:
            return HttpResponse(extractdb_errormsg(e),status=400)

def check_string(s):
      try:
            if s is None:
                  return False
            elif s == "":
                  return False
            elif s == "None":
                  return False
            elif np.isnan(float(s)):
                  return False
            else:
                  return True
      except:
            return False
      
def approveNetASPayments(row,fin_code):
      netas_qry=list(NetASBaseModel.objects.filter(Fin_year=row['Fin_year'],Week_no=row['Week_no'],Entity=row['Entity'],Fin_code=fin_code,Legacy_dues=False).all().values())
      if len(netas_qry):
            # first check whether full amount paid or not
            if row['Amount'] == netas_qry[0]['Final_charges']:
                  # amount fully paid 
                  if check_string(netas_qry[0]['SRAS_id']):
                        # get SRAS object
                        sras_obj_qry=SRASBaseModel.objects.get(id=netas_qry[0]['SRAS_id'])
                        
                        SRASPayments(
                              Paid_date=row['ValueDate_fk_id__ValueDate']  ,
                              Description=row['ValueDate_fk_id__Description'],
                              Paid_amount=float(row['Amount']),
                              Other_info=row['Other_info'],
                              Bank_type=row['ValueDate_fk_id__BankType'],
                              paystatus_fk=sras_obj_qry
                        ).save()

                  if check_string(netas_qry[0]['TRAS_id']):
                        # get TRAS object
                        tras_obj_qry=TRASBaseModel.objects.get(id=netas_qry[0]['TRAS_id'])
                        TRASPayments(
                              Paid_date=row['ValueDate_fk_id__ValueDate']  ,
                              Description=row['ValueDate_fk_id__Description'],
                              Paid_amount=float(row['Amount']),
                              Other_info=row['Other_info'],
                              Bank_type=row['ValueDate_fk_id__BankType'],
                              paystatus_fk=tras_obj_qry
                        ).save()

                  if check_string(netas_qry[0]['MBAS_id']):
                        # get MBAS object
                        mbas_obj_qry=MBASBaseModel.objects.get(id=netas_qry[0]['MBAS_id'])
                        MBASPayments(
                              Paid_date=row['ValueDate_fk_id__ValueDate']  ,
                              Description=row['ValueDate_fk_id__Description'],
                              Paid_amount=float(row['Amount']),
                              Other_info=row['Other_info'],
                              Bank_type=row['ValueDate_fk_id__BankType'],
                              paystatus_fk=mbas_obj_qry
                        ).save()

                  if check_string(netas_qry[0]['SCUC_id']):
                        # get SCUC object
                        scuc_obj_qry=SCUCBaseModel.objects.get(id=netas_qry[0]['SCUC_id'])
                        SCUCPayments(
                              Paid_date=row['ValueDate_fk_id__ValueDate']  ,
                              Description=row['ValueDate_fk_id__Description'],
                              Paid_amount=float(row['Amount']),
                              Other_info=row['Other_info'],
                              Bank_type=row['ValueDate_fk_id__BankType'],
                              paystatus_fk=scuc_obj_qry
                        ).save()
                  
                  # now update NetASBasmodel
                  netas_obj_qry=NetASBaseModel.objects.get(id=netas_qry[0]['id'])
                  NetASPayments(
                        Paid_date=row['ValueDate_fk_id__ValueDate']  ,
                        Description=row['ValueDate_fk_id__Description'],
                        Paid_amount=float(row['Amount']),
                        Other_info=row['Other_info'],
                        Bank_type=row['ValueDate_fk_id__BankType'],
                        paystatus_fk=netas_obj_qry
                  ).save()
            else:
                  # not paid full amount
                  netas_obj_qry=NetASBaseModel.objects.get(id=netas_qry[0]['id'])
                  NetASPayments(
                        Paid_date=row['ValueDate_fk_id__ValueDate']  ,
                        Description=row['ValueDate_fk_id__Description'],
                        Paid_amount=float(row['Amount']),
                        Other_info=row['Other_info'],
                        Bank_type=row['ValueDate_fk_id__BankType'],
                        paystatus_fk=netas_obj_qry
                  ).save()
      return
      
def approveRevisionPayments(row,fin_code):
      try:
            revision_qry=list(RevisionBaseModel.objects.filter(id=row['Parent_id']).all().values())
            if len(revision_qry):
                  # check part payments made
                  total_amount = MappedBankEntries.objects.filter(Pool_Acc = row['Pool_Acc'], Entity = row['Entity'],Parent_id = row['Parent_id']).exclude(Status='R').aggregate(total=Sum('Amount'))['total']
                  # If no matching records, ensure total_amount is not None
                  total_amount = total_amount if total_amount is not None else 0.0
                  # first check whether full amount paid or not
                  if abs(total_amount - float(revision_qry[0]['Final_charges'])) <= 1:
                        # get the letter to identify all bills
                        letter_date=revision_qry[0]['Letter_date']
                        # get all bills related to this letter
                        if row['Pool_Acc'] == 'DSM_REVISION':
                              all_related_bills_df=pd.DataFrame(DSMBaseModel.objects.filter(Effective_start_date=letter_date,Fin_code=fin_code).values('Fin_year','Week_no','Week_startdate','Week_enddate','Entity','Final_charges','PayableorReceivable','Fin_code','payments__Paid_amount','dsmreceivables__Disbursed_amount'),columns=['Fin_year','Week_no','Week_startdate','Week_enddate','Entity', 'Final_charges', 'PayableorReceivable','Fin_code','payments__Paid_amount','dsmreceivables__Disbursed_amount'])

                              all_related_bills_df.rename(columns={'payments__Paid_amount':'Paid_amount','dsmreceivables__Disbursed_amount':'Disbursed_amount'},inplace=True)

                              all_related_bills_df['Paid_amount']=all_related_bills_df['Paid_amount'].fillna(0)
                              all_related_bills_df['Disbursed_amount']=all_related_bills_df['Disbursed_amount'].fillna(0)
                  
                              all_related_bills_df[['Final_charges', 'Paid_amount','Disbursed_amount']] = all_related_bills_df[['Final_charges', 'Paid_amount','Disbursed_amount']].abs()
                              all_related_bills_df.loc[all_related_bills_df.duplicated(subset=['Fin_year', 'Week_no', 'Fin_code','Paid_amount'], keep='first'), ['Paid_amount']] = 0
                              all_related_bills_df.loc[all_related_bills_df.duplicated(subset=['Fin_year', 'Week_no', 'Fin_code','Disbursed_amount'], keep='first'), ['Disbursed_amount']] = 0
                              all_related_bills_df.loc[all_related_bills_df.duplicated(subset=['Fin_year', 'Week_no', 'Fin_code','Final_charges'], keep='first'), ['Final_charges']] = 0

                              
                              sub_bills_df=all_related_bills_df.groupby(['Fin_year', 'Week_no', 'Fin_code']).agg({
                                    'Entity':'first',
                                    'Week_startdate': 'first',
                                    'Week_enddate': 'first',
                                    'Final_charges' : 'first',
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
                              # Update PayableorReceivable based on Diff_amount
                              sub_bills_df["PayableorReceivable"] = sub_bills_df["Diff_amount"].apply(lambda x: "Payable" if x > 0 else "Receivable")

                              for _ , sub_row in sub_bills_df.iterrows():
                                    dsm_obj=DSMBaseModel.objects.get(Fin_year = sub_row['Fin_year'] , Week_no = sub_row['Week_no'] , Fin_code = sub_row['Fin_code'] , Effective_end_date__isnull=True)
                                    if sub_row['PayableorReceivable'] == 'Payable':
                                          # here updating payables
                                          Payments(
                                                Paid_date=row['ValueDate_fk_id__ValueDate'],
                                                Description=row['ValueDate_fk_id__Description'],
                                                Paid_amount= sub_row['Diff_amount'] ,
                                                Other_info='Adjusting the cumulative bill',
                                                Bank_type=row['ValueDate_fk_id__BankType'],
                                                paystatus_fk=dsm_obj,
                                                approved_date=datetime.now() ,
                                                Is_disbursed = True,
                                                is_revision = True
                                                ).save()
                                    elif sub_row['PayableorReceivable'] == 'Receivable':
                                          DSMReceivables(
                                                Disbursed_amount=sub_row['Diff_amount'],
                                                rcvstatus_fk=dsm_obj,
                                                disbursed_date=row['ValueDate_fk_id__ValueDate'],
                                                neft_txnno=row['ValueDate_fk_id__Description'],
                                                is_revision = True
                                          ).save()

                                    else: continue
                                    # now update Basemodel
                                    DSMBaseModel.objects.filter(Fin_year = sub_row['Fin_year'] , Week_no = sub_row['Week_no'] , Fin_code = sub_row['Fin_code'] , Effective_end_date__isnull=False).update(Is_disbursed = True)

                        elif row['Pool_Acc'] == 'NETAS_REVISION':
                              all_related_bills_df=pd.DataFrame(NetASBaseModel.objects.filter(Effective_start_date=letter_date,Fin_code=fin_code).values('Fin_year','Week_no','Week_startdate','Week_enddate','Entity','Final_charges','PayableorReceivable','Fin_code','netaspayments__Paid_amount','netasreceivables__Disbursed_amount'),columns=['Fin_year','Week_no','Week_startdate','Week_enddate','Entity', 'Final_charges', 'PayableorReceivable','Fin_code','netaspayments__Paid_amount','netasreceivables__Disbursed_amount'])

                              all_related_bills_df.rename(columns={'netaspayments__Paid_amount':'Paid_amount','netasreceivables__Disbursed_amount':'Disbursed_amount'},inplace=True)

                              all_related_bills_df['Paid_amount']=all_related_bills_df['Paid_amount'].fillna(0)
                              all_related_bills_df['Disbursed_amount']=all_related_bills_df['Disbursed_amount'].fillna(0)
                  
                              all_related_bills_df[['Final_charges', 'Paid_amount','Disbursed_amount']] = all_related_bills_df[['Final_charges', 'Paid_amount','Disbursed_amount']].abs()
                              all_related_bills_df.loc[all_related_bills_df.duplicated(subset=['Fin_year', 'Week_no', 'Fin_code','Paid_amount'], keep='first'), ['Paid_amount']] = 0
                              all_related_bills_df.loc[all_related_bills_df.duplicated(subset=['Fin_year', 'Week_no', 'Fin_code','Disbursed_amount'], keep='first'), ['Disbursed_amount']] = 0
                              all_related_bills_df.loc[all_related_bills_df.duplicated(subset=['Fin_year', 'Week_no', 'Fin_code','Final_charges'], keep='first'), ['Final_charges']] = 0

                              
                              
                              sub_bills_df=all_related_bills_df.groupby(['Fin_year', 'Week_no', 'Fin_code']).agg({
                                    'Entity':'first',
                                    'Week_startdate': 'first',
                                    'Week_enddate': 'first',
                                    'Final_charges' : 'sum',
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
                              # Update PayableorReceivable based on Diff_amount
                              sub_bills_df["PayableorReceivable"] = sub_bills_df["Diff_amount"].apply(lambda x: "Payable" if x > 0 else "Receivable")

                              for _ , sub_row in sub_bills_df.iterrows():
                                    dsm_obj=NetASBaseModel.objects.get(Fin_year = sub_row['Fin_year'] , Week_no = sub_row['Week_no'] , Fin_code = sub_row['Fin_code'] , Effective_end_date__isnull=True)
                                    if sub_row['PayableorReceivable'] == 'Payable':
                                          # here updating payables
                                          NetASPayments(
                                                Paid_date=row['ValueDate_fk_id__ValueDate'],
                                                Description=row['ValueDate_fk_id__Description'],
                                                Paid_amount= sub_row['Diff_amount'] ,
                                                Other_info='Adjusting the cumulative bill',
                                                Bank_type=row['ValueDate_fk_id__BankType'],
                                                paystatus_fk=dsm_obj,
                                                approved_date=datetime.now() ,
                                                Is_disbursed = True
                                                ).save()
                                    elif sub_row['PayableorReceivable'] == 'Receivable':
                                          NetASReceivables(
                                                Disbursed_amount=sub_row['Diff_amount'],
                                                rcvstatus_fk=dsm_obj,
                                                disbursed_date=row['ValueDate_fk_id__ValueDate'],
                                                neft_txnno=row['ValueDate_fk_id__Description']
                                          ).save()

                                    else: continue
                                    # now update Basemodel
                                    NetASBaseModel.objects.filter(Fin_year = sub_row['Fin_year'] , Week_no = sub_row['Week_no'] , Fin_code = sub_row['Fin_code'] , Effective_end_date__isnull=False).update(Is_disbursed = True)
                        elif row['Pool_Acc'] == 'REAC_REVISION':
                              all_related_bills_df=pd.DataFrame(REACBaseModel.objects.filter(Effective_start_date=letter_date,Fin_code=fin_code).values('Fin_year','Week_no','Week_startdate','Week_enddate','Entity','Final_charges','PayableorReceivable','Fin_code','reacpayments__Paid_amount','reacreceivables__Disbursed_amount'),columns=['Fin_year','Week_no','Week_startdate','Week_enddate','Entity', 'Final_charges', 'PayableorReceivable','Fin_code','reacpayments__Paid_amount','reacreceivables__Disbursed_amount'])

                              all_related_bills_df.rename(columns={'reacpayments__Paid_amount':'Paid_amount','reacreceivables__Disbursed_amount':'Disbursed_amount'},inplace=True)

                              all_related_bills_df['Paid_amount']=all_related_bills_df['Paid_amount'].fillna(0)
                              all_related_bills_df['Disbursed_amount']=all_related_bills_df['Disbursed_amount'].fillna(0)
                  
                              all_related_bills_df[['Final_charges', 'Paid_amount','Disbursed_amount']] = all_related_bills_df[['Final_charges', 'Paid_amount','Disbursed_amount']].abs()
                              all_related_bills_df.loc[all_related_bills_df.duplicated(subset=['Fin_year', 'Week_no', 'Fin_code','Paid_amount'], keep='first'), ['Paid_amount']] = 0
                              all_related_bills_df.loc[all_related_bills_df.duplicated(subset=['Fin_year', 'Week_no', 'Fin_code','Disbursed_amount'], keep='first'), ['Disbursed_amount']] = 0
                              all_related_bills_df.loc[all_related_bills_df.duplicated(subset=['Fin_year', 'Week_no', 'Fin_code','Final_charges'], keep='first'), ['Final_charges']] = 0
                              
                              
                              sub_bills_df=all_related_bills_df.groupby(['Fin_year', 'Week_no', 'Fin_code']).agg({
                                    'Entity':'first',
                                    'Week_startdate': 'first',
                                    'Week_enddate': 'first',
                                    'Final_charges' : 'first',
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
                              # Update PayableorReceivable based on Diff_amount
                              sub_bills_df["PayableorReceivable"] = sub_bills_df["Diff_amount"].apply(lambda x: "Payable" if x > 0 else "Receivable")

                              for _ , sub_row in sub_bills_df.iterrows():
                                    dsm_obj=REACBaseModel.objects.get(Fin_year = sub_row['Fin_year'] , Week_no = sub_row['Week_no'] , Fin_code = sub_row['Fin_code'] , Effective_end_date__isnull=True)
                                    if sub_row['PayableorReceivable'] == 'Payable':
                                          # here updating payables
                                          REACPayments(
                                                Paid_date=row['ValueDate_fk_id__ValueDate'],
                                                Description=row['ValueDate_fk_id__Description'],
                                                Paid_amount= sub_row['Diff_amount'] ,
                                                Other_info='Adjusting the cumulative bill',
                                                Bank_type=row['ValueDate_fk_id__BankType'],
                                                paystatus_fk=dsm_obj,
                                                approved_date=datetime.now() ,
                                                Is_disbursed = True
                                                ).save()
                                    elif sub_row['PayableorReceivable'] == 'Receivable':
                                          REACReceivables(
                                                Disbursed_amount=sub_row['Diff_amount'],
                                                rcvstatus_fk=dsm_obj,
                                                disbursed_date=row['ValueDate_fk_id__ValueDate'],
                                                neft_txnno=row['ValueDate_fk_id__Description']
                                          ).save()

                                    else: continue
                                    # now update Basemodel
                                    REACBaseModel.objects.filter(Fin_year = sub_row['Fin_year'] , Week_no = sub_row['Week_no'] , Fin_code = sub_row['Fin_code'] , Effective_end_date__isnull=False).update(Is_disbursed = True)


                  revisionas_obj_qry=RevisionBaseModel.objects.get(id=row['Parent_id'])
                  RevisionPayments(
                        Paid_date=row['ValueDate_fk_id__ValueDate']  ,
                        Description=row['ValueDate_fk_id__Description'],
                        Paid_amount=float(row['Amount']),
                        Other_info=row['Other_info'],
                        Bank_type=row['ValueDate_fk_id__BankType'],
                        paystatus_fk=revisionas_obj_qry
                  ).save()
            
            return True , ''
      except Exception as e:
            return False , str(e)
     
def approvePayments(request):
      try:
            formdata=json.loads(request.body)
            message_list=[]
            for row in formdata['selected_rows']:
                  try:
                        fin_code=getFincode(row['Entity'])
                        if row['Pool_Acc'] == 'DSM' and fin_code:
                              dsm_obj_qry=DSMBaseModel.objects.get(id=row['Parent_id'])
                              Payments(
                                    Paid_date=row['ValueDate_fk_id__ValueDate']  ,
                                    Description=row['ValueDate_fk_id__Description'],
                                    Paid_amount=float(row['Amount']),
                                    Other_info=row['Other_info'],
                                    Bank_type=row['ValueDate_fk_id__BankType'],
                                    paystatus_fk=dsm_obj_qry,
                                    Is_disbursed=False
                              ).save()

                        elif row['Pool_Acc'] == 'NET_AS':
                              approveNetASPayments(row,fin_code)

                        elif row['Pool_Acc'] == 'REAC':
                              reac_obj_qry=REACBaseModel.objects.get(id=row['Parent_id'])
                              REACPayments(
                                    Paid_date=row['ValueDate_fk_id__ValueDate']  ,
                                    Description=row['ValueDate_fk_id__Description'],
                                    Paid_amount=float(row['Amount']),
                                    Other_info=row['Other_info'],
                                    Bank_type=row['ValueDate_fk_id__BankType'],
                                    paystatus_fk=reac_obj_qry,
                                    Is_disbursed=False
                              ).save()
                        
                        elif row['Pool_Acc'] == 'Legacy':
                              reac_obj_qry=LegacyBaseModel.objects.get(id=row['Parent_id'])
                              LegacyPayments(
                                    Paid_date=row['ValueDate_fk_id__ValueDate']  ,
                                    Description=row['ValueDate_fk_id__Description'],
                                    Paid_amount=float(row['Amount']),
                                    Other_info=row['Other_info'],
                                    Bank_type=row['ValueDate_fk_id__BankType'],
                                    paystatus_fk=reac_obj_qry,
                                    Is_disbursed=False
                              ).save()
                        
                        elif row['Pool_Acc'] == 'Shortfall':
                              reac_obj_qry=ShortfallBaseModel.objects.get(id=row['Parent_id'])
                              ShortfallPayments(
                                    Paid_date=row['ValueDate_fk_id__ValueDate']  ,
                                    Description=row['ValueDate_fk_id__Description'],
                                    Paid_amount=float(row['Amount']),
                                    Other_info=row['Other_info'],
                                    Bank_type=row['ValueDate_fk_id__BankType'],
                                    paystatus_fk=reac_obj_qry,
                                    Is_disbursed=False
                              ).save()

                        elif row['Pool_Acc'] == 'CONG':
                              reac_obj_qry=CONGBaseModel.objects.get(id=row['Parent_id'])
                              CONGPayments(
                                    Paid_date=row['ValueDate_fk_id__ValueDate']  ,
                                    Description=row['ValueDate_fk_id__Description'],
                                    Paid_amount=float(row['Amount']),
                                    Other_info=row['Other_info'],
                                    Bank_type=row['ValueDate_fk_id__BankType'],
                                    paystatus_fk=reac_obj_qry,
                                    Is_disbursed=False
                              ).save()
  
                        elif row['Pool_Acc'] == 'IR':
                              ir_obj_qry=IRBaseModel.objects.get(id=row['Parent_id'])
                              IRPayments(
                                    Paid_date=row['ValueDate_fk_id__ValueDate']  ,
                                    Description=row['ValueDate_fk_id__Description'],
                                    Paid_amount=float(row['Amount']),
                                    Other_info=row['Other_info'],
                                    Bank_type=row['ValueDate_fk_id__BankType'],
                                    paystatus_fk=ir_obj_qry
                              ).save()

                        elif 'REVISION' in row['Pool_Acc']:
                              check_stat , error = approveRevisionPayments(row,fin_code)
                              
                              if not check_stat:
                                    message_list.append([row['Entity'] + ' error occured '+str(error)+', Please check'])
                                    return JsonResponse([message_list],safe=False)
                              
                        elif row['Pool_Acc']  in ['EXCESS','F&C']:
                              ExcessBaseModel(
                                    Entity=row['Entity'],
                                    Final_charges=row['Amount'],
                                    Paid_date=row['ValueDate_fk_id__ValueDate']  ,
                                    Description=row['ValueDate_fk_id__Description'],
                                    Other_info=row['Other_info'],
                                    Bank_type=row['ValueDate_fk_id__BankType'],
                                    Fin_code=fin_code,
                                    Is_disbursed=False,
                                    Acc_Type=row['Pool_Acc']
                              ).save()
                              
                        elif row['Pool_Acc'] == 'Interest':
                              InterestPayments(
                                    Paid_date=row['ValueDate_fk_id__ValueDate']  ,
                                    Description=row['ValueDate_fk_id__Description'],
                                    Paid_amount=float(row['Amount']),
                                    Other_info=row['Other_info'],
                                    Bank_type=row['ValueDate_fk_id__BankType'],
                                    paystatus_fk=InterestBaseModel.objects.get(id=row['Parent_id']),
                                    approved_date=datetime.today()
                              ).save()

                        elif row['Pool_Acc'] == 'Others':
                              OtherPayments(
                                    Paid_date=row['ValueDate_fk_id__ValueDate']  ,
                                    Description=row['ValueDate_fk_id__Description'],
                                    Paid_amount=float(row['Amount']),
                                    Remarks=row['Other_info'],
                                    Bank_type=row['ValueDate_fk_id__BankType'],
                                    Is_disbursed=False
                              ).save()
                        elif row['Pool_Acc'] == 'TRAS':
                              tras_obj_qry=TRASBaseModel.objects.get(id=row['Parent_id'])
                              TRASPayments(
                                    Paid_date=row['ValueDate_fk_id__ValueDate']  ,
                                    Description=row['ValueDate_fk_id__Description'],
                                    Paid_amount=float(row['Amount']),
                                    Other_info=row['Other_info'],
                                    Bank_type=row['ValueDate_fk_id__BankType'],
                                    paystatus_fk=tras_obj_qry
                              ).save()

                        elif row['Pool_Acc'] == 'SRAS':
                              sras_obj_qry=SRASBaseModel.objects.get(id=row['Parent_id'])
                              SRASPayments(
                                    Paid_date=row['ValueDate_fk_id__ValueDate']  ,
                                    Description=row['ValueDate_fk_id__Description'],
                                    Paid_amount=float(row['Amount']),
                                    Other_info=row['Other_info'],
                                    Bank_type=row['ValueDate_fk_id__BankType'],
                                    paystatus_fk=sras_obj_qry
                              ).save()
                        elif row['Pool_Acc'] == 'MBAS':
                              mbas_obj_qry=MBASBaseModel.objects.get(id=row['Parent_id'])
                              MBASPayments(
                                    Paid_date=row['ValueDate_fk_id__ValueDate']  ,
                                    Description=row['ValueDate_fk_id__Description'],
                                    Paid_amount=float(row['Amount']),
                                    Other_info=row['Other_info'],
                                    Bank_type=row['ValueDate_fk_id__BankType'],
                                    paystatus_fk=mbas_obj_qry
                              ).save()
                              
                        elif row['Pool_Acc'] == 'SWEEP':
                              pass
                        else:
                              message_list.append([row['Entity']+ ' Fin code not found for the entity -- Please check'])
                              continue
                        
                        message_list.append([row['Entity']+ '-- Approved Successfully'])
                        # now change MappedBankEntries status
                        MappedBankEntries.objects.filter(id=row['id']).update(Status='A')
                  except Exception as e:
                        message_list.append([row['Entity'] + ' error occured '+str(e)+', Please check'])
                        continue
            
            return JsonResponse([message_list],safe=False)

      except Exception as e:
            return HttpResponse(extractdb_errormsg(e),status=400)
    
def rejectPayments(request):
      try:
            formdata=json.loads(request.body)
            for row in formdata['selected_rows']:
                  # now change MappedBankEntries status to Reject
                
                  MappedBankEntries.objects.filter(id=row['id']).update(Status='R')
                  BankStatement.objects.filter(id=row['ValueDate_fk_id__id']).update(
                        IsMapped=False,
                        SplitStatus='P'
                  )

            return JsonResponse('success',safe=False)

      except Exception as e:
            return HttpResponse(extractdb_errormsg(e),status=400)

def viewBankStatement(request):
      try:
            formdata=json.loads(request.body)
            start_date=add530hrstoDateString(formdata['start_date']).date()
            end_date=add530hrstoDateString(formdata['end_date']).date()
          
            bank_types=formdata['bank']
            
            bank_stmt_df=pd.DataFrame(BankStatement.objects.filter(PostDate__range=[start_date,end_date],BankType__in=bank_types).all().values(),columns=['id', 'ValueDate', 'PostDate', 'Description', 'Debit', 'Credit','Balance', 'IsMapped', 'SplitStatus', 'IsSweep', 'BankType'])
            # exclude Statements if Status is Rejected
            mapped_bank_df=pd.DataFrame(MappedBankEntries.objects.filter(ValueDate_fk__PostDate__range=[start_date,end_date],ValueDate_fk__BankType__in=bank_types ).exclude(Status='R').all().values() ,columns=['id', 'Pool_Acc', 'Fin_year', 'Week_no', 'Amount', 'Entity','ValueDate_fk_id', 'Other_info', 'Status', 'Reject_remarks','Parent_id'])

            merged_df=pd.merge(bank_stmt_df,mapped_bank_df,left_on=['id'],right_on=['ValueDate_fk_id'],how='left')
            
            merged_df=merged_df.fillna('')
            merged_df.sort_values(['PostDate','Entity'],inplace=True)
            return JsonResponse(merged_df.to_dict(orient='records'),safe=False)

      except Exception as e:
            return HttpResponse(extractdb_errormsg(e),status=400)



