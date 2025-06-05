
import ast
import pandas as pd
from dsm.models import TemporaryInterRegional,DisbursementStatus
from registration.models import *
from registration.extarctdb_errors import extractdb_errormsg
from django.http import HttpResponse , JsonResponse
from django.db.models import Max
from datetime import timedelta , datetime 
from django.db.models import F ,Count ,Sum , Q
import locale , calendar,os
from num2words import num2words
import zipfile

wr_name = 'Western Region'
er_name = 'Eastern Region'

wr_code =''
er_code = ''

srpc_file_names={'DSM':'dsm.csv' , 'SRAS':'sras.csv','MBAS':'mbas.csv','REAC':'reac.csv' ,'TRAS':'tras.csv','SCUC':'scuc.csv' ,'CONG':'cong.csv'}
int_names=['DSM_Int','SRAS_Int','TRAS_Int','MBAS_Int','REAC_Int']
no_data_found_df=pd.DataFrame(['No Data Found , Please check'])

month_name_dict={
      'jan':'jan',
      'feb':'feb',
      'mar':'mar',
      'apr':'apr',
      'may':'may',
      'jun':'june',
      'jul':'july',
      'aug':'aug',
      'sep':'sep',
      'oct':'oct',
      'nov':'nov',
      'dec':'dec'
}

keys = ['DSM', 'REAC', 'IR', 'NET_AS','Interest','REV','CONG','Others','Shortfall']
legacy_keys = ['DSM', 'REAC', 'CONG','Legacy']
def generateWeekRange(week_nos_range):
      try:
            # Split the input string by hyphen
            start_end = week_nos_range.split('-')
            if len(start_end) == 2:
                  # it converts '48-50' to [48,49,50]
                  start_number, end_number = map(int, week_nos_range.split('-'))
                  actual_end_number = end_number if end_number <= 52  else 52
                  week_nos = list(range(start_number, actual_end_number + 1))

            elif len(start_end) == 1:
                  actual_end_number = int(start_end[0]) if int(start_end[0]) <= 52  else 52
                  week_nos = [actual_end_number]
            else:
                  week_nos = []

            return week_nos
      except Exception as e:
            extractdb_errormsg(e)
            return []

def getWRERCodes():
      try:
            # hoping that fees and charges name is constant
            # always take latest codes
            wr_reg_qry=list(Registration.objects.filter(fees_charges_name ='POSOCO WR Deviation Pool Account Fund' , end_date__isnull=True).values('fin_code' ,'dsm_name'))

            er_reg_qry=list(Registration.objects.filter(fees_charges_name ='Power System Operation Corporation Ltd ERPC Deviation Pool Account' , end_date__isnull=True).values('fin_code' ,'dsm_name'))

            if len(wr_reg_qry):
                  wr_fin_code = wr_reg_qry[0]['fin_code']
                  wr_dsm_name =wr_reg_qry[0]['dsm_name']
            else:
                  # default name if nothing matches
                  wr_fin_code='--'
                  wr_dsm_name='Western Region'

            if len(er_reg_qry):
                  er_fin_code = er_reg_qry[0]['fin_code']
                  er_dsm_name =er_reg_qry[0]['dsm_name']
            else:
                  # default name if nothing matches
                  er_fin_code='--'
                  er_dsm_name='Eastern Region'

            return [wr_fin_code,wr_dsm_name,er_fin_code,er_dsm_name]
      
      except Exception as e:
            extractdb_errormsg(e)
            return ['--','Western Region','--','Eastern Region']

def _create_columns(df , columns_to_add ):
      new_columns_df = pd.DataFrame({col: ['--'] * len(df) for col in columns_to_add})
      df = pd.concat([df, new_columns_df], axis=1)
      return df

def getWeekDates(fin_year,week_no):
      try:
            week_start_date=None
            week_end_date=None
            # get weekstartdate and week enddate
            yr_cal_qry=list(YearCalendar.objects.filter(fin_year =fin_year , week_no = week_no).values_list('start_date' , 'end_date'))
            
            if len(yr_cal_qry):
                  week_start_date =yr_cal_qry[0][0]
                  week_end_date =yr_cal_qry[0][1]
            else:
                  week_start_date ='--'
                  week_end_date ='--'
      except Exception as e:
            extractdb_errormsg(e)
      
      return week_start_date, week_end_date

def getIRMaxRevision(fin_year,week_no):
      try:
            # Query the database to get the max values of wr_revision_no and er_revision_no
            max_values = TemporaryInterRegional.objects.filter(Fin_year=fin_year, Week_no=week_no).aggregate(
                  max_wr_revision_no=Max('WR_Revision_no'),
                  max_er_revision_no=Max('ER_Revision_no')
            )
            return max_values['max_wr_revision_no'] , max_values['max_er_revision_no']
      except Exception as e:
            extractdb_errormsg(e)

def add530hrstoDateString(datestr):
      date_obj = pd.to_datetime(datestr)
      date_obj += timedelta(hours=5, minutes=30)
      return date_obj


def getFeesChargesName(fin_code):
      try:
            reg_qry = Registration.objects.get(fin_code=fin_code ,end_date__isnull=True)
            reg_qry.fees_charges_name
            return reg_qry.fees_charges_name
      except Exception as e:
            extractdb_errormsg(e)
            return None
      

def getFincode(entity_name):
      try:
            reg_qry = Registration.objects.get(( Q(fees_charges_name=entity_name) | Q(finance_name=entity_name) | Q(dsm_name=entity_name) | Q(sras_name=entity_name) | Q(tras_name=entity_name)| Q(react_name=entity_name) ) , end_date__isnull=True)

            return reg_qry.fin_code
      except Exception as e:
            return ''
 
def getBankShortNames():
      try:
            mappings_list=list(BankShortNameMappings.objects.filter(Q(end_date__isnull=True)|Q(end_date__gte=datetime.now())).values('short_name1','short_name2','short_name3','fin_code'))
            return mappings_list
      
      except Exception as e:
            return None
      
def getBankShortNamesList():
      try:
            mappings_list=list(BankShortNameMappings.objects.all().values('short_names','fin_code'))
            return mappings_list
      
      except Exception as e:
            return None

def removeSpaceDf(df):
      #remove \n and \r from column names
      return [col.replace('\n', '').replace('\r', '').replace(' ', '') for col in df.columns] 

def checkEntityExists(all_users,entity):
      check_ent_exists = all_users.filter( Q(fees_charges_name=entity) | Q(dsm_name=entity) | Q(sras_name=entity) | Q(tras_name=entity) | Q(react_name=entity))

      return check_ent_exists

#def format_indian_currency(amount):
#    try:
#      locale.setlocale(locale.LC_MONETARY, 'en_IN')
#      return locale.currency(amount, grouping=True)
#    except:
#          return amount
def format_indian_currency(amount):
    try:
        # Set locale for Indian currency formatting
        locale.setlocale(locale.LC_MONETARY, 'en_IN.UTF-8')
        
        # Check if the amount is negative
        is_negative = amount < 0
        
        # Format the absolute value of the amount
        formatted_amount = locale.currency(abs(amount), grouping=True)
        
        # Add the negative sign and Indian Rupee symbol if the amount is negative
        if is_negative:
            return '-₹' + formatted_amount[1:]
        else:
            return formatted_amount
    except:
        return amount
    
def format_indian_currency_withoutsymbol(amount):
    try:
        # Set locale for Indian currency formatting
        locale.setlocale(locale.LC_MONETARY, 'en_IN.UTF-8')
        # Check if the amount is negative
        is_negative = amount < 0
        # Format the absolute value of the amount
        formatted_amount = locale.currency(abs(amount), grouping=True)
        formatted_amount = formatted_amount.replace('₹' ,'').strip()
        # Add the negative sign and Indian Rupee symbol if the amount is negative
        if is_negative:
            return '-' + formatted_amount
        else:
            return formatted_amount
    except:
        return amount
    
def get_month_start_end_dates(selected_month):
    # Convert the string to a datetime object representing the first day of the month
    start_date = datetime.strptime(selected_month, '%Y-%m')
    # Get the year and month from the start_date
    year = start_date.year
    month = start_date.month

    # Get the last day of the month
    last_day = calendar.monthrange(year, month)[1]

    # Create the end_date datetime object
    end_date = datetime(year, month, last_day)

    # Format the dates as strings
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')

    return start_date_str, end_date_str

def removeInterestTail(pool_acc):
      return pool_acc.replace('_Int','')

# Function to clean and convert to float
def currency_to_float(value):
    # Remove currency symbol and commas
    cleaned_value = value.replace('₹', '').replace(',', '')
    # Convert to float
    return float(cleaned_value)

def getMergedAccts():
      # first get the merged accounts and then sum it as NetAS
      merge_qry=list(MergedAccounts.objects.filter(Q(end_date__isnull=True)|Q(end_date__gte=datetime.now())).values_list('merged_accounts',flat=True))
      merged_accs = ast.literal_eval(merge_qry[0])
      return merged_accs

def getAllPoolAccs():
      # Fetch account types either end_date is null or end_date is future date like 2040-01-01
      pool_acct_types=list(PoolAccountTypes.objects.filter(Q(end_date__isnull=True) | Q(end_date__gte=timezone.now() )).order_by('acc_types').values_list('acc_types' , flat=True) )
      return pool_acct_types

def trimFilePath(file_path):
      # Split the path into components
      path_parts = file_path.split(os.sep)

      # Remove the first four components like D:\\PoolAccounts\\Backend\\poolaccounts
      relative_path_parts = path_parts[4:]
      # Join the remaining components back into a path
      relative_path = os.sep.join(relative_path_parts)
      return relative_path



def number_to_words_rupees(number):
    words = num2words(number,  lang='en_IN')
    return f"{words.capitalize()} Rupees"

def getDisbursedWeeks(request):
      # get all disbursed weeks
      disbursed_weeks_lst=list(DisbursementStatus.objects.filter(final_disburse=True).order_by('-Disbursed_date').values_list('Disbursed_date',flat=True))

      return JsonResponse(disbursed_weeks_lst,safe=False)

def checkLegacyStatus(finyear , weekno):
      # here check the Legacy dues 
      if finyear in ('2021-22','2022-23','2023-24'):
            legacy_dues = True
      elif finyear == '2024-25' and int(weekno) < 24:
            legacy_dues = True
      else: legacy_dues = False

      return legacy_dues