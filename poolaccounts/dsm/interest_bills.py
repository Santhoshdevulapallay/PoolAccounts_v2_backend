import json ,pdb ,os ,math
import pandas as pd
from datetime import datetime
from django.http import HttpResponse , JsonResponse,FileResponse
from dsm.common import get_month_start_end_dates
from dsm.common import getFincode
from registration.extarctdb_errors import extractdb_errormsg
from poolaccounts.settings import BASE_DIR , base_dir
from .models import *
from dsm.common import no_data_found_df
from .engine_create import engine
from sqlalchemy.exc import IntegrityError

def getDelayedPayments(pay_model,start_date_obj,end_date_obj,pool_acc):

      payments_inselected_month_df=pd.DataFrame(pay_model.objects.filter(Paid_date__range=[start_date_obj,end_date_obj]).values('paystatus_fk__Fin_year','paystatus_fk__Week_no','paystatus_fk__Due_date','paystatus_fk__Entity','paystatus_fk__Fin_code','paystatus_fk__Final_charges','Paid_date','Paid_amount'),
            columns=['paystatus_fk__Fin_year', 'paystatus_fk__Week_no',
                                    'paystatus_fk__Due_date', 'paystatus_fk__Entity','paystatus_fk__Fin_code','paystatus_fk__Final_charges', 'Paid_date','Paid_amount','Acc_type'])

      # Convert date columns to datetime
      payments_inselected_month_df['paystatus_fk__Due_date'] = pd.to_datetime(payments_inselected_month_df['paystatus_fk__Due_date'])
      payments_inselected_month_df['Paid_date'] = pd.to_datetime(payments_inselected_month_df['Paid_date'])
      payments_inselected_month_df['Acc_type']=pool_acc

      return payments_inselected_month_df

def getMonthlyIntersetCalc(request):
      try:
            selected_month=request.body.decode()
            start_date_obj,end_date_obj=get_month_start_end_dates(selected_month)
            # get all letter dates
            letter_dates= list(TempInterestBaseModel.objects
                          .values('Letter_date')
                          .distinct()
                          .order_by('-Letter_date')
                          .values_list('Letter_date', flat=True))
            
            # check if already stored then return empty df
            if TempInterestBaseModel.objects.filter(Letter_date=start_date_obj).count() >0:
                  return JsonResponse([{}, letter_dates],safe=False)
         
            dsm_delayed_payments_df=getDelayedPayments(Payments,start_date_obj,end_date_obj,'DSM')
            sras_delayed_payments_df=getDelayedPayments(SRASPayments,start_date_obj,end_date_obj,'SRAS')
            tras_delayed_payments_df=getDelayedPayments(TRASPayments,start_date_obj,end_date_obj,'TRAS')
            mbas_delayed_payments_df=getDelayedPayments(MBASPayments,start_date_obj,end_date_obj,'MBAS')
            reac_delayed_payments_df=getDelayedPayments(REACPayments,start_date_obj,end_date_obj,'REAC')
            
            payments_inselected_month_df=pd.concat([dsm_delayed_payments_df,sras_delayed_payments_df,tras_delayed_payments_df,mbas_delayed_payments_df,reac_delayed_payments_df])
            
            # check if already stored or not
            # Collect indices of rows to be deleted
            indices_to_drop = []
            interest_qry=TempInterestBaseModel.objects.filter(Letter_date=start_date_obj)
            if interest_qry:
                  for index, row in payments_inselected_month_df.iterrows():
                        # check whether record already stored or not
                        if interest_qry.filter(Acc_type=row['Acc_type'],Fin_year=row['paystatus_fk__Fin_year'],Week_no=row['paystatus_fk__Week_no'],Entity=row['paystatus_fk__Entity']).count() > 0:
                              indices_to_drop.append(index)
                  # Drop the rows based on indices
                  payments_inselected_month_df.drop(indices_to_drop, inplace=True)

            # Filter rows where Paid_date is greater than paystatus_fk__Due_date
            filtered_df = payments_inselected_month_df[payments_inselected_month_df['Paid_date'] > payments_inselected_month_df['paystatus_fk__Due_date']].copy()
            # Calculate the difference in days and store in a new column
            filtered_df.loc[:, 'Days_Late'] = (filtered_df['Paid_date'] - filtered_df['paystatus_fk__Due_date']).dt.days 
            # Ensure Days_Late is not negative
            filtered_df.loc[:, 'Days_Late'] = filtered_df['Days_Late'].apply(lambda x: x if x > 0 else 0)

            filtered_df.loc[:, 'Interest_payable_topool'] = (filtered_df['Days_Late']*filtered_df['Paid_amount']*0.04)/100
            # consider amount greater than 0 only
            filtered_df=filtered_df[filtered_df['Interest_payable_topool']>0]
            # ceiling 
            filtered_df['Interest_payable_topool']=filtered_df['Interest_payable_topool'].apply(lambda x: math.ceil(x)) 
      
            

            return JsonResponse([filtered_df.to_dict(orient='records') , letter_dates],safe=False)
      
      except Exception as e:
            extractdb_errormsg(e)
            return None
      
def downloadIntersetCalc(request):
      try:
            selected_month=request.body.decode()
            start_date_obj,end_date_obj=get_month_start_end_dates(selected_month)

            dsm_delayed_payments_df=getDelayedPayments(Payments,start_date_obj,end_date_obj,'DSM')
            sras_delayed_payments_df=getDelayedPayments(SRASPayments,start_date_obj,end_date_obj,'SRAS')
            tras_delayed_payments_df=getDelayedPayments(TRASPayments,start_date_obj,end_date_obj,'TRAS')
            mbas_delayed_payments_df=getDelayedPayments(MBASPayments,start_date_obj,end_date_obj,'MBAS')
            reac_delayed_payments_df=getDelayedPayments(REACPayments,start_date_obj,end_date_obj,'REAC')
            
            payments_inselected_month_df=pd.concat([dsm_delayed_payments_df,sras_delayed_payments_df,tras_delayed_payments_df,mbas_delayed_payments_df,reac_delayed_payments_df])
            
            # check if already stored or not
            # Collect indices of rows to be deleted
            indices_to_drop = []
            interest_qry=TempInterestBaseModel.objects.filter(Letter_date=start_date_obj)
            if interest_qry:
                  for index, row in payments_inselected_month_df.iterrows():
                        # check whether record already stored or not
                        if interest_qry.filter(Acc_type=row['Acc_type'],Fin_year=row['paystatus_fk__Fin_year'],Week_no=row['paystatus_fk__Week_no'],Entity=row['paystatus_fk__Entity']).count() > 0:
                              indices_to_drop.append(index)
                  # Drop the rows based on indices
                  payments_inselected_month_df.drop(indices_to_drop, inplace=True)

            # Filter rows where Paid_date is greater than paystatus_fk__Due_date
            filtered_df = payments_inselected_month_df[payments_inselected_month_df['Paid_date'] > payments_inselected_month_df['paystatus_fk__Due_date']].copy()
            # Calculate the difference in days and store in a new column
            filtered_df.loc[:, 'Days_Late'] = (filtered_df['Paid_date'] - filtered_df['paystatus_fk__Due_date']).dt.days 
            # Ensure Days_Late is not negative
            filtered_df.loc[:, 'Days_Late'] = filtered_df['Days_Late'].apply(lambda x: x if x > 0 else 0)

            filtered_df.loc[:, 'Interest_payable_topool'] = (filtered_df['Days_Late']*filtered_df['Paid_amount']*0.04)/100
            # consider amount greater than 0 only
            filtered_df=filtered_df[filtered_df['Interest_payable_topool']>0]
            # ceiling 
            filtered_df['Interest_payable_topool']=filtered_df['Interest_payable_topool'].apply(lambda x: math.ceil(x)) 
            # rename the columns
            if not filtered_df.empty:
                  # Create new column names by removing the substring
                  filtered_df.columns= [col.replace('paystatus_fk__', '') for col in filtered_df.columns]
            else:
                  filtered_df=pd.DataFrame(['No Data found '])
            parent_folder = os.path.abspath(os.path.join(base_dir, os.pardir))
            directory = os.path.join(parent_folder, 'Files', 'ViewBills' )
                  
            in_filename='InterestCalc'+str(selected_month)+'.csv'
            full_path=os.path.join(directory, in_filename)
            filtered_df.to_csv(full_path,index=False)

            return FileResponse(open(full_path,'rb'),content_type='text/csv') 

      except Exception as e:
            extractdb_errormsg(e)
            return None

def saveInterestBills(request):
      try:
            request_data=json.loads(request.body)
            selected_bills=request_data['selected_rows']
            start_date_obj,end_date_obj=get_month_start_end_dates(request_data['selected_month'])

            for row in selected_bills:
                  try:
                        TempInterestBaseModel(
                              Acc_type=row['Acc_type'],
                              Fin_year=row['paystatus_fk__Fin_year'],
                              Week_no=row['paystatus_fk__Week_no'], 
                              Revision_no=0, 
                              Letter_date=start_date_obj, 
                              Due_date=datetime.fromisoformat(row['paystatus_fk__Due_date']).date(),
                              Date_of_receipt=datetime.fromisoformat(row['Paid_date']).date(),
                              Entity=row['paystatus_fk__Entity'], 
                              Final_charges=row['Interest_payable_topool'], 
                              Fin_code=row['paystatus_fk__Fin_code'],
                              Amount_srpc_payabletopool=row['paystatus_fk__Final_charges'],
                              Paid_amount=row['Paid_amount'],
                              No_of_days_delayed=row['Days_Late']
                        ).save()
                  except Exception as e:
                        extractdb_errormsg(e)
            return JsonResponse('success',safe=False)
      
      except Exception as e:
            extractdb_errormsg(e)
            return None

def storeFinalIntBills(request):
      try:
            request_data=json.loads(request.body)
            letter_date=request_data['interest_date']
            # first get the temp stored bills
            stored_temp_df=pd.DataFrame(TempInterestBaseModel.objects.filter(Letter_date=letter_date).all().values())
            # first check whether all entities are having finance codes are not
            for index, row in stored_temp_df.iterrows():
                  if row['Fin_code'] == '' or pd.isna(row['Fin_code']):
                        # get the fincode
                        stored_temp_df.at[index, 'Fin_code'] = getFincode(row['Entity'])

            # df group by Entity and sum Final_charges
            result_df=stored_temp_df.groupby(['Entity','Fin_code'])['Final_charges'].sum().reset_index()                                                     
            result_df['Letter_date']=letter_date
            # drop rows not having fin_codes
            result_df=result_df[result_df['Fin_code']!='']

            try:
                  with engine.connect() as connection:
                        result_df.to_sql('interest_basemodel', connection, if_exists='append',index=False)
            except IntegrityError as e:
                  if 'unique constraint' in str(e.orig):
                        return JsonResponse({'status': False, 'message': 'Value already exists in the database.'}, safe=False)
                  else:
                        return JsonResponse({'status': False, 'message': str(e)}, safe=False)
            except Exception as e:
                  return JsonResponse({'status': False, 'message': str(e)}, safe=False)
            
            return JsonResponse({'status':True ,'message':'Bills are Stored Successfully , Check under View Bills'},safe=False)
      
      except Exception as e:
            return HttpResponse(extractdb_errormsg(e),status_code=500)


def downloadInterestbills(request):
      try:
            request_data =json.loads(request.body)
            letter_date=request_data['interest_date']
            
            parent_folder = os.path.abspath(os.path.join(BASE_DIR, os.pardir))
            directory = os.path.join(parent_folder, 'Files', 'InterestBills' )
            
            if not os.path.exists(directory):
                  # Create the directory if it doesn't exist
                  os.makedirs(directory)
            
            in_filename='interest_bills&'+letter_date+'.xlsx'
            full_path=os.path.join(directory, in_filename)

            writer = pd.ExcelWriter(full_path, engine='xlsxwriter')
            
            # get payables separate and receivables separate
            temp_interest_bills_df=pd.DataFrame(TempInterestBaseModel.objects.filter(Letter_date=letter_date).order_by('Acc_type','Fin_year','Week_no').values('Acc_type','Fin_year','Week_no','Entity','Amount_srpc_payabletopool','Due_date','Date_of_receipt','Paid_amount','No_of_days_delayed','Final_charges'))
            
            # final bills
            interest_bills_df=pd.DataFrame(InterestBaseModel.objects.filter(Letter_date=letter_date).values('Letter_date','Entity','Fin_code','Final_charges'))
            if not interest_bills_df.empty:
                  interest_bills_df.to_excel(writer, sheet_name='Final Bills', index=False)
            else:
                  no_data_found_df.to_excel(writer, sheet_name='Week wise', index=False)

            if not temp_interest_bills_df.empty:
                  temp_interest_bills_df.rename(columns={'Week_no':'Wk No. & period','Entity':'Constituent','Amount_srpc_payabletopool':'Amount receivable to pool (Rs.)','Due_date':'Due date for receipt','Date_of_receipt':'Date of receipt ','Paid_amount':'Amount received (Rs.)' ,'No_of_days_delayed':'No.of days Delayed  beyond 2 days','Final_charges':'Interest Payable to Pool (in Rs.)'},inplace=True)
                  
                  temp_interest_bills_df.to_excel(writer, sheet_name='Week wise', index=False)
            else:
                  no_data_found_df.to_excel(writer, sheet_name='Week wise', index=False)
            
            writer.close()
            return FileResponse(open(full_path,'rb'),content_type='text/xlsx')   
      except Exception as e:
            return HttpResponse(extractdb_errormsg(e),status=400)

