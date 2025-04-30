from django.http import HttpResponse , JsonResponse ,FileResponse
import os,json
from dsm.common import add530hrstoDateString
from registration.fetch_data import getFCNames
from registration.extarctdb_errors import extractdb_errormsg
from poolaccounts.settings import BASE_DIR ,base_dir
import pandas as pd 
from datetime import datetime
from .models import DSMBaseModel,AccountCodeDetails,Payments
from .mbas_models import MBASBaseModel
from .netas_models import NetASBaseModel
from .reac_models import REACBaseModel
from .sras_models import SRASBaseModel
from .tras_models import TRASBaseModel
from .scuc_models import SCUCBaseModel
from .short_fall_models import *
from .models import BankStatement,MappedBankEntries
from django.db.models import Q
from .legacy_models import LegacyBaseModel
from datetime import timedelta
from .interest_models import *
from .excess_models import * 
from .short_fall_models import *

def JVPoolAccDetails(fin_year,wk_no,account_codes_df,model_obj,acc_type):
    try:
        # get all bills
        jv_bills_df=pd.DataFrame(model_obj.objects.filter(Fin_year=fin_year , Week_no=wk_no).values('Fin_year','Fin_code','PayableorReceivable','Final_charges'),columns=['Fin_year', 'Fin_code', 'PayableorReceivable', 'Final_charges'])
    
        jv_bills_df['Account Code'] = jv_bills_df['PayableorReceivable'].apply(
            lambda x: account_codes_df[account_codes_df['acc_type'] == acc_type]['receivable_to_pool'].iloc[0] if x == 'Payable' else account_codes_df[account_codes_df['acc_type'] == acc_type]['disbursement_from_pool'].iloc[0]
        ).iloc[jv_bills_df.index]

    
        # Create new columns 'Amount Dr' and 'Amount Cr' and populate based on 'PayableorReceivable'
        jv_bills_df['Amount Dr'] = jv_bills_df['Final_charges'].where(jv_bills_df['PayableorReceivable'] == 'Payable', '')
        jv_bills_df['Amount Cr'] = jv_bills_df['Final_charges'].where(jv_bills_df['PayableorReceivable'] == 'Receivable', '')
        # drop those columns not required
        jv_bills_df.drop(columns=['Final_charges','PayableorReceivable'],inplace=True)
        # rename the columns
        jv_bills_df.rename(columns={'Fin_code':'Party Code','Fin_year':'Fin Year'},inplace=True)
        # create extra columns
        jv_bills_df['Sub Code']=1
        jv_bills_df['Remarks']= 'wk '+str(wk_no)
        jv_bills_df['TAN No']= ''
        column_order=['Account Code','Sub Code','Party Code','Remarks','Amount Dr','Amount Cr','Fin Year','TAN No']
        jv_bills_df=jv_bills_df[column_order]

        parent_folder = os.path.abspath(os.path.join(base_dir, os.pardir))
        directory = os.path.join(parent_folder, 'Files', 'ViewBills' )
        if not os.path.exists(directory):
            # Create the directory if it doesn't exist
            os.makedirs(directory)  

        in_filename='JV_'+str(fin_year)+str(wk_no)+'.csv'
        full_path=os.path.join(directory, in_filename)
        jv_bills_df.to_csv(full_path,index=False)

        return full_path
    
    except Exception as e:
        extractdb_errormsg(e)
        return ''
    
def downloadJV(request):
    try:
        input_data=json.loads(request.body)['formdata']
        account_codes_df=pd.DataFrame(AccountCodeDetails.objects.filter(acc_type=input_data['acc_type']).all().values())
        
        if input_data['acc_type'] == 'DSM':
            full_path=JVPoolAccDetails(input_data['fin_year'],input_data['wk_no'],account_codes_df,DSMBaseModel,input_data['acc_type'])

        elif input_data['acc_type'] == 'REAC':
            full_path=JVPoolAccDetails(input_data['fin_year'],input_data['wk_no'],account_codes_df,REACBaseModel,input_data['acc_type'])

        elif input_data['acc_type'] == 'NET_AS':
            full_path=JVPoolAccDetails(input_data['fin_year'],input_data['wk_no'],account_codes_df,NetASBaseModel,input_data['acc_type'])
        else:
            full_path=''

        return FileResponse(open(full_path,'rb'),content_type='text/csv') 
    
    except Exception as e:
        return HttpResponse(extractdb_errormsg(e),status=400)

def getFincodeUsingParentTable(mapped_df):
    try:
        # get the fincode using parent table id like DSMBaseModel 
        for idx,row in mapped_df.iterrows():
            fin_code=''
            if row['Pool_Acc'] == 'DSM':
                try:
                    dsm_obj_qry=DSMBaseModel.objects.get(id=row['Parent_id'])
                    fin_code=dsm_obj_qry.Fin_code
                except:
                    continue
              
            elif row['Pool_Acc'] == 'REAC':
                try:
                    dsm_obj_qry=REACBaseModel.objects.get(id=row['Parent_id'])
                    fin_code=dsm_obj_qry.Fin_code
                except:
                    continue

            elif row['Pool_Acc'] == 'NET_AS':
                try:
                    dsm_obj_qry=NetASBaseModel.objects.get(id=row['Parent_id'])
                    fin_code=dsm_obj_qry.Fin_code
                except:
                    continue
            elif row['Pool_Acc'] == 'Legacy':
                try:
                    dsm_obj_qry=LegacyBaseModel.objects.get(id=row['Parent_id'])
                    fin_code=dsm_obj_qry.Fin_code
                except:
                    continue
            elif row['Pool_Acc'] == 'Interest':
                try:
                    dsm_obj_qry=InterestBaseModel.objects.get(id=row['Parent_id'])
                    fin_code=dsm_obj_qry.Fin_code
                except:
                    continue
            elif row['Pool_Acc'] == 'EXCESS' :
                try:
                    dsm_obj_qry=ExcessBaseModel.objects.get(id=row['Parent_id'])
                    fin_code=dsm_obj_qry.Fin_code
                except:
                    continue
            elif row['Pool_Acc'] == 'Shortfall' :
                try:
                    dsm_obj_qry=ShortfallBaseModel.objects.get(id=row['Parent_id'])
                    fin_code=dsm_obj_qry.Fin_code
                except:
                    continue
            else:
                continue

            mapped_df.at[idx,'Fincode']=fin_code

    except Exception as e:
        extractdb_errormsg(e)

    return mapped_df
    
def downloadBankStmtFin(request):
    try:
        input_data=json.loads(request.body)['formdata']
        start_date=add530hrstoDateString(input_data['start_date']).date()
        end_date=add530hrstoDateString(input_data['end_date']).date()
        
        bank_statement_df=pd.DataFrame(BankStatement.objects.filter(PostDate__range=[start_date,end_date]).all().values(),columns=['id','ValueDate', 'PostDate', 'Description', 'Debit', 'Credit','Balance','IsSweep','BankType'])
        temp_mapped_txns_df=pd.DataFrame(MappedBankEntries.objects.filter(ValueDate_fk__PostDate__range=[start_date,end_date]).all().values(),columns=['Pool_Acc', 'Fin_year', 'Week_no', 'Amount', 'Entity','ValueDate_fk_id', 'Other_info', 'Status', 'Reject_remarks','Parent_id','Fincode'])
        
        mapped_txns_df=getFincodeUsingParentTable(temp_mapped_txns_df)
        # get the fincodes using parent table id
        merged_df=pd.merge(bank_statement_df,mapped_txns_df,left_on='id',right_on='ValueDate_fk_id',how='left')
        merged_df=merged_df.fillna('')
        merged_df=merged_df[['ValueDate', 'PostDate', 'Description', 'Debit', 'Credit','Balance','IsSweep','BankType','Pool_Acc', 'Fin_year', 'Week_no', 'Amount', 'Fincode', 'Other_info', 'Status', 'Reject_remarks']]

        # Group by Description and aggregate lists
        grouped = merged_df.groupby(['ValueDate', 'PostDate', 'Description', 'Debit', 'Credit','Balance','IsSweep','BankType']).agg({
            'Pool_Acc': list,
            'Fin_year': list,
            'Week_no': list,
            'Amount': list,
            'Fincode': list
        }).reset_index()

        # Expand lists into separate columns
        expanded_rows = []
        for _, row in grouped.iterrows():
            max_length = max(len(row['Pool_Acc']), len(row['Fin_year']), len(row['Week_no']), len(row['Amount']) ,len(row['Fincode']))
            expanded_row = {
                'ValueDate': row['ValueDate'] ,
                'PostDate': row['PostDate'] ,
                'Description': row['Description'] ,
                'Debit': row['Debit'] ,
                'Credit': row['Credit'] ,
                'Balance': row['Balance'] ,
                'IsSweep': row['IsSweep'] ,
                'BankType': row['BankType'] 
                }
            for i in range(max_length):
                expanded_row[f'Pool_Acc_{i+1}'] = row['Pool_Acc'][i] if i < len(row['Pool_Acc']) else None
                expanded_row[f'Fin_year_{i+1}'] = row['Fin_year'][i] if i < len(row['Fin_year']) else None
                expanded_row[f'Week_no_{i+1}'] = row['Week_no'][i] if i < len(row['Week_no']) else None
                expanded_row[f'Amount_{i+1}'] = row['Amount'][i] if i < len(row['Amount']) else None
                expanded_row[f'Fincode{i+1}'] = row['Fincode'][i] if i < len(row['Fincode']) else None
            expanded_rows.append(expanded_row)

        # Convert expanded rows back to DataFrame
        expanded_df = pd.DataFrame(expanded_rows)
        expanded_df.sort_values(['BankType','ValueDate'],inplace=True)

        parent_folder = os.path.abspath(os.path.join(base_dir, os.pardir))
        directory = os.path.join(parent_folder, 'Files', 'Trash' )
        if not os.path.exists(directory):
            # Create the directory if it doesn't exist
            os.makedirs(directory)  

        in_filename='BankStmt_'+str(start_date)+'.csv'
        full_path=os.path.join(directory, in_filename)
        expanded_df.to_csv(full_path,index=False)

        return FileResponse(open(full_path,'rb'),content_type='text/csv') 
    
    except Exception as e:
        return HttpResponse(extractdb_errormsg(e),status=400)
    
def getOustandingdf(acc_type):
    try:
        today_date=datetime.today().date()
        if acc_type == 'DSM':
            model_obj=DSMBaseModel
            col_name='payments__Paid_date'
            col_name2 = 'payments__Paid_amount'
            # parent_table_col='payments__paystatus_fk'
        elif acc_type == 'NET_AS':
            model_obj=NetASBaseModel
            col_name='netaspayments__Paid_date'
            col_name2 = 'netaspayments__Paid_amount'
            # parent_table_col='netaspayments__paystatus_fk'
        elif acc_type == 'REAC':
            model_obj=REACBaseModel
            col_name='reacpayments__Paid_date'
            col_name2 = 'reacpayments__Paid_amount'
            # parent_table_col='reacpayments__paystatus_fk'
        elif acc_type == 'Legacy':
            model_obj= LegacyBaseModel
            col_name='legacypayments__Paid_date'
            col_name2 = 'legacypayments__Paid_amount'
        elif acc_type == 'Shortfall':
            model_obj= ShortfallBaseModel
            col_name='shortfallpayments__Paid_date'
            col_name2 = 'shortfallpayments__Paid_amount'
        else:
            # if nothing matches return with empty dataframes
            return pd.DataFrame([],columns=['Fin_year','Week_no','Entity','Outstanding','Fin_code',col_name,col_name2]),pd.DataFrame([],columns=['Fin_code','Outstanding','Entity'])
        
        # get outstanding dues as on date , excluding the records which do not contain Fin codes
        if acc_type == 'Shortfall' :
            basemodel_df=pd.DataFrame(model_obj.objects.filter(Due_date__lt= today_date).exclude( Q(Fin_code__isnull=True) | Q(Fin_code='')).values('Fin_year','Letter_date','Entity','Final_charges','Fin_code',col_name,col_name2),columns=['Fin_year','Letter_date','Entity','Final_charges','Fin_code',col_name,col_name2])
            basemodel_df['Week_no'] = basemodel_df['Letter_date']

        else :
            basemodel_df=pd.DataFrame(model_obj.objects.filter(Due_date__lt= today_date,PayableorReceivable='Payable',Effective_end_date__isnull=True).exclude( Q(Fin_code__isnull=True) | Q(Fin_code='')).values('Fin_year','Week_no','Entity','Final_charges','Fin_code',col_name,col_name2),columns=['Fin_year','Week_no','Entity','Final_charges','Fin_code',col_name,col_name2])
        # rename the column

        basemodel_df[col_name2] = basemodel_df[col_name2].fillna(0)
        basemodel_grouped = basemodel_df.groupby(['Fin_code','Week_no','Fin_year']).agg({  'Entity': 'first','Final_charges':'mean', col_name : 'first',col_name2: 'sum',}).reset_index()

        basemodel_grouped['Outstanding'] = basemodel_grouped['Final_charges'] - basemodel_grouped[col_name2]
        basemodel_grouped.columns = ['Fin_code', 'Week_no', 'Fin_year', 'Entity', 'Final_charges','Paid_date', 'Paid_amount', 'Outstanding']
        
        #basemodel_df.rename(columns={'Final_charges':'Outstanding'},inplace=True)
       
        # Filter rows where 'payments__Paid_date' is None
        temp_filtered_df = basemodel_grouped[(basemodel_grouped['Outstanding']>5) & (basemodel_grouped['Fin_year'] >= '2023-24')]
        # now Paid_date column is no longer required
        #temp_filtered_df=temp_filtered_df.drop(columns=[col_name])
        # temp_filtered_df if outstanding is greater than 0
        #temp_filtered_df=temp_filtered_df[temp_filtered_df['Outstanding']>0]
        filtered_df=temp_filtered_df.copy()
        
        # sort by Entity
        filtered_df.sort_values(['Entity','Fin_year','Week_no'],inplace=True)
        # group by Entity and sum the Final_charges
        grouped_df = filtered_df.groupby('Fin_code').agg({ 'Outstanding': 'sum', 'Entity': 'first' }).reset_index()  # or 'last', depending on which Entity you want to retain
        #sort based on Entity 
        grouped_df.sort_values('Entity',inplace=True)
        # reorder the columns
        new_column_order=['Entity','Fin_code','Outstanding']
        grouped_df=grouped_df[new_column_order]
        return filtered_df,grouped_df
        
    except Exception as e:
        extractdb_errormsg(e)
        return pd.DataFrame([str(e)],columns=['Fin_year','Week_no','Entity','Outstanding','Fin_code',col_name]),pd.DataFrame([str(e)],columns=['Fin_code','Outstanding','Entity'])
    

def getOutstandingDetails(request):
    try:
        input_data=json.loads(request.body)['formdata']
        acc_type=input_data['acc_type']
        
        full_breakup_details_df, grouped_df=getOustandingdf(acc_type)
        return JsonResponse([full_breakup_details_df.to_dict(orient='records') ,grouped_df.to_dict(orient='records')],safe=False)
    
    except Exception as e:
        return HttpResponse(extractdb_errormsg(e),status=400)
    
def getOutstandingWeekWise(request):
    try:
        input_data=json.loads(request.body)['formdata']
        acc_type=input_data['acc_type']
        
        full_breakup_details_df, grouped_df=getOustandingdf(acc_type)
        return JsonResponse([full_breakup_details_df.to_dict(orient='records') ,grouped_df.to_dict(orient='records')],safe=False)
    
    except Exception as e:
        return HttpResponse(extractdb_errormsg(e),status=400)



def downloadOutstandingXL(request):
    try:
        input_data=json.loads(request.body)['formdata']
        acc_type=input_data['acc_type']
        today_date=datetime.today().date()

        full_breakup_details_df, grouped_df=getOustandingdf(acc_type)

        parent_folder = os.path.abspath(os.path.join(base_dir, os.pardir))
        directory = os.path.join(parent_folder, 'Files', 'Outstanding' )
        
        if not os.path.exists(directory):
            # Create the directory if it doesn't exist
            os.makedirs(directory)

        in_filename=acc_type+'_Outstanding_'+str(today_date.strftime('%d-%m-%Y'))+'.xlsx'
        full_path=os.path.join(directory, in_filename)
        writer = pd.ExcelWriter(full_path, engine='xlsxwriter')

        grouped_df.to_excel(writer, sheet_name='Outstanding', index=False)
        full_breakup_details_df.to_excel(writer, sheet_name='Entity wise', index=False)

        writer.close()
        return FileResponse(open(full_path,'rb'),content_type='text/xlsx')
    
    except Exception as e:
        return HttpResponse(extractdb_errormsg(e),status=400)
    

def getUnMappedTxns(request):
    try:
        unmapped_txn_df=pd.DataFrame(BankStatement.objects.filter(IsMapped=False,Credit__gte=1).order_by('-ValueDate').all().values())
        # remove nan values 
        unmapped_txn_df=unmapped_txn_df.fillna('')

        return JsonResponse([unmapped_txn_df.to_dict(orient='records') , getFCNames()],safe=False)
    
    except Exception as e:
        return HttpResponse(extractdb_errormsg(e),status=400)

def getOustandingdf_15(acc_type):
    try:
        today_date=datetime.today().date()
        if acc_type == 'DSM':
            model_obj=DSMBaseModel
            col_name='payments__Paid_date'
            col_name2 = 'payments__Paid_amount'
            # parent_table_col='payments__paystatus_fk'
        elif acc_type == 'NET_AS':
            model_obj=NetASBaseModel
            col_name='netaspayments__Paid_date'
            col_name2 = 'netaspayments__Paid_amount'
            # parent_table_col='netaspayments__paystatus_fk'
        elif acc_type == 'REAC':
            model_obj=REACBaseModel
            col_name='reacpayments__Paid_date'
            col_name2 = 'reacpayments__Paid_amount'
            # parent_table_col='reacpayments__paystatus_fk'
        elif acc_type == 'Legacy':
            model_obj= LegacyBaseModel
            col_name='legacypayments__Paid_date'
            col_name2 = 'legacypayments__Paid_amount'
        else:
            # if nothing matches return with empty dataframes
            return pd.DataFrame([],columns=['Fin_year','Week_no','Entity','Outstanding','Fin_code',col_name,col_name2]),pd.DataFrame([],columns=['Fin_code','Outstanding','Entity'])
        
        # get outstanding dues as on date , excluding the records which do not contain Fin codes
        basemodel_df=pd.DataFrame(model_obj.objects.filter(Due_date__lt= today_date-timedelta(15,0,0),PayableorReceivable='Payable',Effective_end_date__isnull=True).exclude( Q(Fin_code__isnull=True) | Q(Fin_code='')).values('Fin_year','Week_no','Entity','Final_charges','Fin_code',col_name,col_name2),columns=['Fin_year','Week_no','Entity','Final_charges','Fin_code',col_name,col_name2])
        # rename the column

        basemodel_df[col_name2] = basemodel_df[col_name2].fillna(0)
        basemodel_grouped = basemodel_df.groupby(['Fin_code','Week_no','Fin_year']).agg({  'Entity': 'first','Final_charges':'mean', col_name : 'first',col_name2: 'sum',}).reset_index()

        basemodel_grouped['Outstanding'] = basemodel_grouped['Final_charges'] - basemodel_grouped[col_name2]
        basemodel_grouped.columns = ['Fin_code', 'Week_no', 'Fin_year', 'Entity', 'Final_charges','Paid_date', 'Paid_amount', 'Outstanding']
        
        #basemodel_df.rename(columns={'Final_charges':'Outstanding'},inplace=True)
       
        # Filter rows where 'payments__Paid_date' is None
        temp_filtered_df = basemodel_grouped[(basemodel_grouped['Outstanding']>5) & (basemodel_grouped['Fin_year'] >= '2023-24')]
        # now Paid_date column is no longer required
        #temp_filtered_df=temp_filtered_df.drop(columns=[col_name])
        # temp_filtered_df if outstanding is greater than 0
        #temp_filtered_df=temp_filtered_df[temp_filtered_df['Outstanding']>0]
        filtered_df=temp_filtered_df.copy()
        
        # sort by Entity
        filtered_df.sort_values(['Entity','Fin_year','Week_no'],inplace=True)
        # group by Entity and sum the Final_charges
        grouped_df = filtered_df.groupby('Fin_code').agg({ 'Outstanding': 'sum', 'Entity': 'first' }).reset_index()  # or 'last', depending on which Entity you want to retain
        #sort based on Entity 
        grouped_df.sort_values('Entity',inplace=True)
        # reorder the columns
        new_column_order=['Entity','Fin_code','Outstanding']
        grouped_df=grouped_df[new_column_order]

        return filtered_df,grouped_df
        
    except Exception as e:
        extractdb_errormsg(e)
        return pd.DataFrame([str(e)],columns=['Fin_year','Week_no','Entity','Outstanding','Fin_code',col_name]),pd.DataFrame([str(e)],columns=['Fin_code','Outstanding','Entity'])