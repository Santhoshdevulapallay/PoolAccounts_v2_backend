from dsm.models import BankStatement
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


def uploadBankStmt(request):
      try:
            file=request.FILES['file']
            start_date= pd.to_datetime(request.POST['start_date'])
            end_date= pd.to_datetime(request.POST['end_date'])
            bank_type=request.POST['selected_bank']
            file_contents=file.read()
            text_data = file_contents.decode('utf-8')
            metadata, transactions = text_data.split('\nTxn Date', 1)

            # Read metadata into a DataFrame
            # metadata_df = pd.read_csv(StringIO(metadata), sep=':', header=None, index_col=0).T

            # Read transactions into a DataFrame
            transactions_df = pd.read_csv(StringIO(transactions), delimiter='\t')
            transactions_df = transactions_df.loc[:, ~transactions_df.columns.str.contains('^Unnamed')]

            # Remove spaces from column names
            transactions_df = transactions_df.rename(columns=lambda x: x.replace(" ", ""))
         
            # Convert "Value Date" to Date format
            transactions_df['ValueDate'] = pd.to_datetime(transactions_df['ValueDate'], format='%d/%m/%Y')
            transactions_df = transactions_df.dropna(subset=['ValueDate'])

            transactions_df = transactions_df[(transactions_df['ValueDate'] >= start_date) & (transactions_df['ValueDate'] <= end_date)]

            # Convert "Credit" and "Balance" columns to float
            transactions_df['Debit'] = pd.to_numeric(transactions_df['Debit'], errors='coerce').apply(lambda x: 0 if pd.isna(x) else x)
            transactions_df['Credit'] = pd.to_numeric(transactions_df['Credit'], errors='coerce').apply(lambda x: 0 if pd.isna(x) else x)
            transactions_df['Balance'] = pd.to_numeric(transactions_df['Balance'], errors='coerce').apply(lambda x: 0 if pd.isna(x) else x)
        
            bank_qry=BankStatement.objects.filter(value_date__range=[start_date,end_date])
            already_exists=[]
            new_rows_added=[]
            # check each row of dataframe if not contains in database then append
            for _ , row in transactions_df.iterrows():
                  if bank_qry.filter(bank_type=bank_type ,value_date=row['ValueDate'],description=row['Description'] ,ref_no=row['RefNo./ChequeNo.'] , credit=row['Credit'] ).count() < 1:
                        # not exists , so add the row
                        BankStatement(
                              value_date=row['ValueDate'],
                              description=row['Description'],
                              ref_no=row['RefNo./ChequeNo.'],
                              branch_code=row['BranchCode'],
                              debit=row['Debit'],
                              credit=row['Credit'],
                              balance=row['Balance'],
                              bank_type=bank_type
                        ).save()
                        new_rows_added.append({'value_date':row['ValueDate'].date() ,'description': row['Description'] , 'ref_no': row['RefNo./ChequeNo.'] , 'credit':row['Credit']})
                  else:
                        # later add this values to log file
                        already_exists.append({'value_date':row['ValueDate'] ,'description': row['Description'] , 'ref_no': row['RefNo./ChequeNo.'] ,'credit':row['Credit']})

            return JsonResponse([new_rows_added],safe=False)

      except (IntegrityError, ValidationError) as e:
            
            return HttpResponse(str(e),status=status.HTTP_400_BAD_REQUEST)

def downloadBankFiles(request):
      try:
            request_data =json.loads(request.body)

            if request_data['supporting_docs']:
                  supporting_docs=ast.literal_eval(request_data['supporting_docs']) 
                  # In-memory output file
                  zip_buffer = io.BytesIO()
                  # Create a zip file in memory
                  with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                        for file_path in supporting_docs:
                              # Normalize the file path
                              normalized_path = os.path.normpath(file_path)
                              # here os.path.dirname moves one folder back 
                              absolute_path = os.path.dirname(base_dir)+normalized_path
                              
                              # Read the file content and add it to the zip file
                              with open(absolute_path, 'rb') as file:
                                    file_content = file.read()
                                    zip_file.writestr(os.path.basename(normalized_path), file_content)

                  # Seek to the beginning of the in-memory file
                  zip_buffer.seek(0)

                  # Create HTTP response
                  response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
                  response['Content-Disposition'] = 'attachment; filename="files.zip"'

                  return response
            else:
                  return HttpResponse('No supporting documents available')
      except Exception as e:
            return HttpResponse(extractdb_errormsg(e),status=400)
