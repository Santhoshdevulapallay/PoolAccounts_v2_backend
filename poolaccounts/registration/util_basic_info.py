

from .models import Registration , BankDetails
from django.http import JsonResponse
import json , datetime
from django.db.models import  Q

def getUtilBasicDetails(request):
    try:
        in_data = json.loads(request.body)
        basic_details_lst = list(Registration.objects.filter(Q(fin_code = in_data['fincode']) , ( Q(end_date__isnull = True) | Q(end_date__gte = datetime.datetime.today() ))).values('fees_charges_name','entity_type','l1_phone','l2_phone','l1_mail','l2_mail'))
        details_dict = {
                'Entity Name' : 'No details found' ,
                'Entity Type' : '',
                'L1 Phone' : '' ,
                'L2 Phone' : '' ,
                'L1 Mail' : '',
                'L2 Mail' : '',
            }
        
        if len(basic_details_lst):
            details_dict = {
                'Entity Name' : basic_details_lst[0]['fees_charges_name'] ,
                'Entity Type' : basic_details_lst[0]['entity_type'] ,
                'L1 Phone' : basic_details_lst[0]['l1_phone'] ,
                'L2 Phone' : basic_details_lst[0]['l2_phone'] ,
                'L1 Mail' : basic_details_lst[0]['l1_mail'] ,
                'L2 Mail' : basic_details_lst[0]['l2_mail'] ,
            }

        bank_details_lst = list(BankDetails.objects.filter(Q(fin_code_fk__fin_code = in_data['fincode']) , ( Q(end_date__isnull = True) | Q(end_date__gte = datetime.datetime.today() ))).values('bank_account','beneficiary_name','bank_name','ifsc_code','pan_card','gst'))
        details_dict1 = {
                'Account No' : 'No details found' ,
                'Beneficiary Name' : '',
                'Bank Name' : '' ,
                'IFSC Code' : '' ,
                'PAN No' : '',
                'GSTIN' : '',
            }
        
        if len(bank_details_lst):
            details_dict1 = {
                'Account No' : bank_details_lst[0]['bank_account'] ,
                'Beneficiary Name' :  bank_details_lst[0]['beneficiary_name'],
                'Bank Name' :  bank_details_lst[0]['bank_name'] ,
                'IFSC Code' :  bank_details_lst[0]['ifsc_code'] ,
                'PAN No' :  bank_details_lst[0]['pan_card'],
                'GSTIN' :  bank_details_lst[0]['gst'],
            }

        return JsonResponse([details_dict , details_dict1 ], safe=False)
    except Exception as e:
        return JsonResponse([details_dict , details_dict1 ], safe=False)
  
