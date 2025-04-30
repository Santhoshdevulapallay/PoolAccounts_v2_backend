import json , os , pandas as pd
from django.http import HttpResponse , JsonResponse
from dsm.common import add530hrstoDateString
from registration.extarctdb_errors import extractdb_errormsg
from registration.models import Registration
from django.db.models import Q
from datetime import datetime , timedelta
import pandas as pd
from .scuc_cc_models import *

import ast
def scucCCEntities(request):
    try:
        entities_df = pd.DataFrame( Registration.objects.filter(Q(entity_type = 'Thermal-CGS') ,( Q(end_date__isnull = True) | Q(end_date__gte = datetime.now())) ).order_by('fees_charges_name').values('fees_charges_name' ,'fin_code') , columns=['fees_charges_name','fin_code'])

        entities_df['final_charges'] = 0    
        entities_df['payableorreceivable'] = ''    
       
        return JsonResponse(entities_df.to_dict(orient='records') , safe=False)
    
    except Exception as e:
        return HttpResponse(extractdb_errormsg(e),status=400)


def storescucCCBills(request):
    try:

        uptomonth=request.POST.get('uptomonth', '').strip()
        letter_date = add530hrstoDateString(json.loads(request.POST['letter_date'])).date() 
        entities_df = pd.DataFrame(ast.literal_eval(request.POST['entities_list']))
        fin_year = json.loads(request.POST['fin_year'])
        
        if not entities_df.empty:
            # Filter rows where 'PayableorReceivable' is not empty and 'Revised_charges' > 0
            resulted_df = entities_df[(entities_df["payableorreceivable"] != "") & (entities_df["final_charges"] > 0)]
        else:
            resulted_df = pd.DataFrame([])

        for _ , row in resulted_df.iterrows():
            SCUCCCBaseModel(
                Letter_date= letter_date ,
                Fin_year = fin_year,
                up_to_the_month = uptomonth,
                Entity= row['fees_charges_name'] ,
                Final_charges= row['final_charges'] ,
                Fin_code= row['fin_code'] ,  
                PayableorReceivable= row['payableorreceivable']
            ).save()

        return JsonResponse('success' , safe=False)
    
    except Exception as e:
          return HttpResponse(extractdb_errormsg(e),status=400)