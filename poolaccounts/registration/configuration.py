
import json ,pdb
from django.http import HttpResponse , JsonResponse ,FileResponse

from registration.fetch_data import getFCNames
from .models import *
from dsm.common import add530hrstoDateString
from django.db.models import Q
from datetime import datetime , timedelta
import pandas as pd
import numpy as np
def getConfigList(request):
   try:
      latest_order_list=list(DisbursementOrder.objects.order_by('-startdate').all().values())

      latest_duedates_list=list(PoolDuedates.objects.order_by('-startdate').all().values())

      return JsonResponse([latest_order_list,latest_duedates_list],safe=False)
   
   except Exception as e:
      return HttpResponse(e,status=404)
   

def disbursementOrder(request):
    try:
      formdata=json.loads(request.body)
      startdate = add530hrstoDateString(formdata['startdate'].replace('"','')).date()
      # first update the last record 
      DisbursementOrder.objects.filter(Q(enddate__isnull=True) | Q(enddate__gte=timezone.now() )).update(
         enddate=(datetime.today() - timedelta(days=1))
      )
      # insert new record
      DisbursementOrder(
        startdate=startdate,
        dsm=formdata['dsm'],
        sras=formdata['sras'],
        tras=formdata['tras'],
        mbas=formdata['mbas'],
        ir=formdata['ir']
      ).save()
      return JsonResponse('success',safe=False)
    
    except Exception as e:
      return HttpResponse(e,status=404)
  

def dueDatesConfig(request):
    try:
      formdata=json.loads(request.body)
      startdate = add530hrstoDateString(formdata['startdate'].replace('"','')).date()
      # first update the last record 
      PoolDuedates.objects.filter(Q(enddate__isnull=True) | Q(enddate__gte=timezone.now() )).update(
         enddate= (datetime.today() - timedelta(days=1))
      )
      # insert new record
      PoolDuedates(
        startdate=startdate,
        dsm=formdata['dsm'],
        sras=formdata['sras'],
        tras=formdata['tras'],
        mbas=formdata['mbas']
      ).save()
      return JsonResponse('success',safe=False)
    
    except Exception as e:
      return HttpResponse(e,status=404)
    

def shortNameMappings(request):
    try:
      # first update the last record 
      short_names_df=pd.DataFrame(BankShortNameMappings.objects.all().values())
      all_fincode_entity_df=pd.DataFrame(Registration.objects.filter(Q(end_date__isnull=True) | Q(end_date__gte=timezone.now())).values('fin_code','fees_charges_name'))
      
      merged_df=pd.merge(short_names_df,all_fincode_entity_df , on='fin_code',how='left')
      merged_df.sort_values('fees_charges_name',inplace=True)
      merged_df.fillna('' , inplace=True)
     
      return JsonResponse([merged_df.to_dict(orient='records'),getFCNames()],safe=False)
    
    except Exception as e:
      print(e)
      return HttpResponse(e,status=404)
    

def addNewShortName(request):
    try:
      in_data=json.loads(request.body)['formdata']
      existing_names=list(BankShortNameMappings.objects.filter(fin_code=in_data['fin_code']).values('short_names'))
      if len(existing_names):
        # Remove the brackets and split the string into a list
        short_names_list = existing_names[0]['short_names'].strip('[]').split(',')
        # Add the new short name
        short_names_list.append(in_data['short_name'])
        # Remove empty strings using list comprehension
        short_names_list = [name for name in short_names_list if name]
        # Join the list back into a string with the desired format
        new_short_names_str = '[' + ','.join(short_names_list) + ']'

        BankShortNameMappings.objects.filter(fin_code=in_data['fin_code']).update(
            short_names=new_short_names_str
          )
      else:
        BankShortNameMappings(
          fin_code=in_data['fin_code'],
          bank_type=in_data['bank_type'],
          short_names='[' + in_data['short_name'] + ']' 
         ).save()
        
      return shortNameMappings(request)
    
    except Exception as e:
      return HttpResponse(e,status=404)
  
def addEmployee(request):
    try:
      pass
        
      return shortNameMappings(request)
    
    except Exception as e:
      return HttpResponse(e,status=404)
  
