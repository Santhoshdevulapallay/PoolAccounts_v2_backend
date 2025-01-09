from django.shortcuts import render

from dsm.common import getFincode
from dsm.bankstmt import check_string

from .register import *
from .fetch_data import *
from .bank_stmt import *
from .dsm_bill import *
from .configuration import *
from .auth_service import *
from dsm.models import *
from .dashboard import *
# Create your views here.


def tempStore(request):
   
    df=pd.read_csv(r'netas_payables.csv')
    for _ ,row in df.iterrows():
        if check_string(row['SRAS_id']):
            # get SRAS object
            sras_obj_qry=SRASBaseModel.objects.get(id=row['SRAS_id'])
            if sras_obj_qry.PayableorReceivable == 'Payable':
                SRASPayments(
                        Paid_date=row['Paid_date'],
                        Description='',
                        Paid_amount=sras_obj_qry.Final_charges,
                        Other_info='',
                        Bank_type=row['Bank_type'],
                        paystatus_fk=sras_obj_qry
                ).save()
            else:
                SRASReceivables(
                    Disbursed_amount=sras_obj_qry.Final_charges,
                    rcvstatus_fk=sras_obj_qry,
                    iom_date=row['approved_date'],
                    disbursed_date=row['approved_date'],
                    neft_txnno=''
                ).save()

        if check_string(row['TRAS_id']):
            # get TRAS object
            tras_obj_qry=TRASBaseModel.objects.get(id=row['TRAS_id'])
            if tras_obj_qry.PayableorReceivable == 'Payable':
                TRASPayments(
                        Paid_date=row['Paid_date'],
                        Description='',
                        Paid_amount=tras_obj_qry.Final_charges,
                        Other_info='',
                        Bank_type=row['Bank_type'],
                        paystatus_fk=tras_obj_qry
                ).save()
            else:
                TRASReceivables(
                    Disbursed_amount=tras_obj_qry.Final_charges,
                    rcvstatus_fk=tras_obj_qry,
                    iom_date=row['approved_date'],
                    disbursed_date=row['approved_date'],
                    neft_txnno=''
                ).save()

        if check_string(row['MBAS_id']):
            # get MBAS object
            mbas_obj_qry=MBASBaseModel.objects.get(id=row['MBAS_id'])
            if mbas_obj_qry.PayableorReceivable == 'Payable':
                MBASPayments(
                        Paid_date=row['Paid_date']  ,
                        Description='',
                        Paid_amount=mbas_obj_qry.Final_charges,
                        Other_info='',
                        Bank_type=row['Bank_type'],
                        paystatus_fk=mbas_obj_qry
                ).save()
            else:
                MBASReceivables(
                    Disbursed_amount=mbas_obj_qry.Final_charges,
                    rcvstatus_fk=mbas_obj_qry,
                    iom_date=row['approved_date'],
                    disbursed_date=row['approved_date'],
                    neft_txnno=''
                ).save()
        if check_string(row['SCUC_id']):
            # get SCUC object
            scuc_obj_qry=SCUCBaseModel.objects.get(id=row['SCUC_id'])
            if scuc_obj_qry.PayableorReceivable == 'Payable':
                SCUCPayments(
                        Paid_date=row['Paid_date'] ,
                        Description='',
                        Paid_amount=scuc_obj_qry.Final_charges,
                        Other_info='',
                        Bank_type=row['Bank_type'],
                        paystatus_fk=scuc_obj_qry
                ).save()
            else:
                SCUCReceivables(
                    Disbursed_amount=scuc_obj_qry.Final_charges,
                    rcvstatus_fk=scuc_obj_qry,
                    iom_date=row['approved_date'],
                    disbursed_date=row['approved_date'],
                    neft_txnno=''
                ).save()

        # now update NetASBasmodel
        netas_obj_qry=NetASBaseModel.objects.get(id=row['id'])
        NetASPayments(
            Paid_date=row['Paid_date'] ,
            Description='',
            Paid_amount=row['Paid_amount'],
            Other_info='',
            Bank_type=row['Bank_type'],
            paystatus_fk=netas_obj_qry
        ).save()
        print(row['Entity'])
        # dd=DSMBaseModel(
        #     Fin_year=row['Fin_year'],
        #     Week_no=row['Week_no'],
        #     Week_startdate=datetime.strptime(row['Week_startdate'],'%Y-%m-%d'),
        #     Week_enddate=datetime.strptime(row['Week_enddate'],'%Y-%m-%d'),
           
        #     Revision_no = 0,
        #     Letter_date=datetime.strptime(row['Letter_date'],'%Y-%m-%d'),
        #     Due_date=datetime.strptime(row['Payment_date'],'%Y-%m-%d'),
        #     Disbursement_date=datetime.strptime(row['Disbursement_date'],'%Y-%m-%d'),
        #     Lc_date=datetime.strptime(row['Lc_date'],'%Y-%m-%d'),
        #     Interest_levydate=datetime.strptime(row['Interest_levydate'],'%Y-%m-%d'),

        #     # Deviation Data also 
        #     Entity=row['Entity'],
        #     Final_charges=row['DevFinal'],
        #     PayableorReceivable=row['PayableorReceivable'],
        #     Fin_code=getFincode(row['Entity']),  

        #     Is_disbursed=True,
        #     Fully_disbursed='C' , # P is partial and C is Complete

        #     Effective_start_date=datetime.strptime(row['Letter_date'],'%Y-%m-%d'),
        #     Effective_end_date=None
        # )
        # dd
        # if row['Pay_amount'] >0:
        #     Payments(
        #             Paid_date=datetime.strptime(row['Pay_date'],'%Y-%m-%d'),
        #             Description='',
        #             Paid_amount=row['Pay_amount'],
        #             Other_info='',
        #             Bank_type=row['Bank_type'],
        #             paystatus_fk=dd
        #     )
        # reac_obj=DSMBaseModel.objects.filter(Fin_year=row['Fin_year'],Week_no=row['Week_no'],Entity=row['Entity'])
        # try:
        #     if len(reac_obj):
        #         # Payments(
        #         #     Paid_date=datetime.strptime(row['Pay_date'],'%d-%m-%Y'),
        #         #     Description='',
        #         #     Paid_amount=row['Pay_amount'],
        #         #     Other_info='',
        #         #     Bank_type=row['Bank_type'],
        #         #     paystatus_fk=DSMBaseModel.objects.get(Fin_year=row['Fin_year'],Week_no=row['Week_no'],Entity=row['Entity']),
        #         # )
        #         DSMReceivables(
        #             disbursed_date=datetime.strptime(row['disbursedate'],'%Y-%m-%d'),
        #             iom_date=datetime.strptime(row['disbursedate'],'%Y-%m-%d'),
        #             disbursed_amount=row['disburseamount'],
        #             rcvstatus_fk=DSMBaseModel.objects.get(Fin_year=row['Fin_year'],Week_no=row['Week_no'],Entity=row['Entity'])
        #         )
        #     else:
        #         print('missed rows' , row['Fin_year']+str(row['Week_no'])+row['Entity'])
        # except Exception as e:
        #     row['Entity']
        #     print(e , row['Entity'])
            
    #     try:
    #         BankDetails(
    #             bank_account=row['bank_account'],
    #             bank_name=row['bank_name'],
    #             ifsc_code=row['ifsc_code'],
    #             is_sbi=row['is_sbi'],
    #             start_date=row['start_date'],
    #             fin_code_fk_id=Registration.objects.get(fin_code=row['fin_code_fk_id'],end_date__isnull=True).id,
    #             gst=row['gst'],
    #             pan_card=row['pan_card'],
    #             beneficiary_name=row['beneficiary_name']
    #         )
    #     except Exception as e:
            
    #         print('missed' , row['beneficiary_name'],str(e))
        
    return JsonResponse('success',safe=False)

def scucStore(request):
    try:
        all_netas=list(TRASBaseModel.objects.filter(Fin_year='2024-25').all().values())
        
        for row in all_netas:
            try:
                fin_code=getFincode(row['Entity'])
               
                if fin_code:
                    TRASBaseModel.objects.filter(id=row['id']).update(Fin_code=fin_code)
              
            except Exception as e:
                
                continue
        
        return JsonResponse('success',safe=False)
    except Exception as e:
        pass