

import json , os , pandas as pd
from django.http import HttpResponse , JsonResponse
from dsm.common import add530hrstoDateString
from registration.extarctdb_errors import extractdb_errormsg
from registration.models import Registration
from django.db.models import Q
from datetime import datetime , timedelta
import pandas as pd
from .short_fall_models import *

def shortfallStates(request):
    try:
        states_df = pd.DataFrame( Registration.objects.filter(Q(entity_type = 'buyer' ), ( Q(end_date__isnull = True) | Q(end_date__gte = datetime.now())) ).values('fees_charges_name' ,'fin_code') , columns=['fees_charges_name','fin_code'])

        states_df['final_charges'] = 0    
       
        return JsonResponse(states_df.to_dict(orient='records') , safe=False)
    
    except Exception as e:
        return HttpResponse(extractdb_errormsg(e),status=400)
    
def storeShortfallBill(request):
    try:
        formdata=json.loads(request.POST['formdata'])
        letter_date_str = json.loads( request.POST['letter_date'])
        letter_date = add530hrstoDateString(letter_date_str).date() 
        fin_year = request.POST['fin_year']
        due_date = letter_date + timedelta(days = 10)
       
        for row in formdata:
            ShortfallBaseModel(
                Fin_year = fin_year,
                Letter_date = letter_date ,
                Due_date = due_date ,
                Entity = row['fees_charges_name'] ,
                Final_charges = row['final_charges'] ,
                Fin_code = row['fin_code']
            ).save()

        return JsonResponse('success' , safe=False)
    
    except Exception as e:
          return HttpResponse(extractdb_errormsg(e),status=400)