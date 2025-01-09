from django.test import TestCase

# Create your tests here.



# transactions_df=pd.read_excel(file,skiprows=19,skipfooter=2)
#                   # Replace spaces in column names with underscores
#                   transactions_df = transactions_df.rename(columns=lambda x: x.replace(' ', ''))
#                   transactions_df['TxnDate'] = pd.to_datetime(transactions_df['TxnDate'], format='%Y-%m-%d')
#                   transactions_df['ValueDate'] = pd.to_datetime(transactions_df['ValueDate'], format='%Y-%m-%d')

#                   transactions_df = transactions_df[(transactions_df['ValueDate'] >= start_date) & (transactions_df['ValueDate'] <= end_date)]
                  
#                   # Convert "Credit" and "Balance" columns to float
#                   transactions_df=transformNumeric(transactions_df ,'Debit')
#                   transactions_df=transformNumeric(transactions_df ,'Credit')      
#                   # merge Description and Ref No to single column
#                   transactions_df['Description'] = transactions_df['Description'] + transactions_df['RefNo./ChequeNo.'] 
                  
#                   # rename columns
#                   transactions_df.rename(columns={'TxnDate':'Post Date' ,'ValueDate':'Value Date', 'Debit':'Debit Amount','Credit':'Credit Amount'},inplace=True)