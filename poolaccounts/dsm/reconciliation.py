
import json
from datetime import datetime
from django.http import JsonResponse,HttpResponse , FileResponse
from dsm.common import add530hrstoDateString, format_indian_currency,get_month_start_end_dates
from registration.extarctdb_errors import extractdb_errormsg
from openpyxl import load_workbook
from registration.models import Registration
from django.db.models import Q
from .models import *
from openpyxl.styles import PatternFill, Border, Side, Alignment, Protection, Font
import os , random
import pandas as pd
from poolaccounts.settings import base_dir
from dsm.user_recon import checkBillsNotified

def getPrevYearMonth(selected_month):
    # get closing balances of prev month (selected_monht in '2024-10' format)
    prev_monthyear_splt = selected_month.split('-')
    year , month = int(prev_monthyear_splt[0]) , int(prev_monthyear_splt[1])
    if month > 1:
        actual_month = month-1
        actual_month = '0'+ str(actual_month) if actual_month < 10 else actual_month
        actual_year = year
    else:
        actual_month = 12
        actual_year = year - 1

    prev_month_year = str(actual_year)+'-'+str(actual_month)

    return prev_month_year

def prepareSummarySheet(wb , summary_sheet):
    try:
        # finally add the Summary sheet
        sheet_title= 'Summary'
        ws_new = wb.create_sheet(title=sheet_title)
        # Define styles
        header_font = Font(bold=True, color="FFFFFF", size=12)
        header_fill = PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")
        center_alignment = Alignment(horizontal="left", vertical="center")
        thin_border = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin")
        )

        # Populate the sheet and apply styles
        for row_index, row_data in enumerate(summary_sheet, start=1):
            for col_index, value in enumerate(row_data, start=1):
                cell = ws_new.cell(row=row_index, column=col_index, value=value)
                
                # Apply header styles to the first row
                if row_index == 1:
                    cell.font = header_font
                    cell.fill = header_fill
                    cell.alignment = center_alignment
                else:
                    cell.alignment = center_alignment
                    cell.border = thin_border

        # Adjust column widths
        for col in ws_new.columns:
            max_length = 0
            column = col[0].column_letter  # Get column letter
            for cell in col:
                try:  # Check for cell value length
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                except:
                    pass
            adjusted_width = max_length + 2
            ws_new.column_dimensions[column].width = adjusted_width

        # Move the new sheet to the starting position and set as active
        wb._sheets.insert(0, wb._sheets.pop(-1))
        wb.active = ws_new
    except Exception as e:
        pass

    return wb

def downloadReconReport(request):
    
    req_data=json.loads(request.body)
    
    start_date,end_date=get_month_start_end_dates(req_data['formdata']['selected_month'])
        
    startdate=add530hrstoDateString(start_date).date()
    enddate=add530hrstoDateString(end_date).date()
    acc_type = req_data['formdata']['acc_type']

    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = 'attachment;'
    
    wb=load_workbook(filename = 'DSM_FinReconReport.xlsx')         
    ws=wb.active
    all_users=list(Registration.objects.filter(Q(end_date__isnull=True)|Q(end_date__gte=datetime.today())).order_by('fees_charges_name').values_list('fees_charges_name','fin_code'))

    disbursed_entities_obj=DisbursedEntities.objects.filter(pool_acctype = acc_type).all()
    week_start_enddates_obj = YearCalendar.objects.all()

    prev_month_year = getPrevYearMonth(req_data['formdata']['selected_month']) 
    
    closing_balances_qry =  ClosingBalances.objects.filter(Month_year = prev_month_year , Acc_type = acc_type )

    parent_folder = os.path.abspath(os.path.join(base_dir, os.pardir))
    directory = os.path.join(parent_folder, 'Files', 'ReconSummary' )
    #import pdb ; pdb.set_trace()
    
    if not os.path.exists(directory):
        # Create the directory if it doesn't exist
        os.makedirs(directory)
   
    if acc_type == 'DSM':
        basemodel_obj = DSMBaseModel.objects.filter(Q(Letter_date__range=[startdate,enddate]) , Q(Revision_no = 0))

        basemodel_qry = basemodel_obj.filter(Q(PayableorReceivable='Payable',payments__Paid_date__isnull=True ))
        basemodel_qry_rcv = basemodel_obj.filter(Q(PayableorReceivable='Receivable',dsmreceivables__disbursed_date__isnull=True ))
        basemodel_qry_next_rcv = basemodel_obj.filter(Q(PayableorReceivable='Receivable',dsmreceivables__disbursed_date__gt = end_date ))
        basemodel_qry_next_pay = basemodel_obj.filter(Q(PayableorReceivable='Payable',payments__Paid_date__gt=end_date ))

        payments_model_qry = Payments.objects.filter(Paid_date__range=[startdate,enddate])
        receivables_qry = DSMReceivables.objects.filter(disbursed_date__range=[startdate,enddate])
        basemodel_obj_rev = RevisionBaseModel.objects.filter(Q(Letter_date__range=[startdate,enddate]) , Q(Acc_type = 'DSM_REVISION'))


    elif acc_type == 'REAC':
        basemodel_obj = REACBaseModel.objects.filter(Q(Letter_date__range=[startdate,enddate]))

        basemodel_qry = basemodel_obj.filter(Q(PayableorReceivable='Payable',reacpayments__Paid_date__isnull=True ))

        basemodel_qry_rcv = basemodel_obj.filter(Q(PayableorReceivable='Receivable',reacreceivables__disbursed_date__isnull=True ))

        basemodel_qry_next_rcv = basemodel_obj.filter(Q(PayableorReceivable='Receivable',reacreceivables__disbursed_date__gt = end_date ))

        basemodel_qry_next_pay = basemodel_obj.filter(Q(PayableorReceivable='Payable',reacpayments__Paid_date__gt=end_date ))

        payments_model_qry = REACPayments.objects.filter(Paid_date__range=[startdate,enddate])
        receivables_qry = REACReceivables.objects.filter(disbursed_date__range=[startdate,enddate])
        basemodel_obj_rev = RevisionBaseModel.objects.filter(Q(Letter_date__range=[startdate,enddate]) , Q(Acc_type = 'REAC_REVISION'))

    elif acc_type == 'NET_AS':
        basemodel_obj = NetASBaseModel.objects.filter(Q(Letter_date__range=[startdate,enddate]))

        basemodel_qry = basemodel_obj.filter(Q(PayableorReceivable='Payable',netaspayments__Paid_date__isnull=True ))

        basemodel_qry_rcv = basemodel_obj.filter(Q(PayableorReceivable='Receivable',netasreceivables__disbursed_date__isnull=True ))

        basemodel_qry_next_rcv = basemodel_obj.filter(Q(PayableorReceivable='Receivable',netasreceivables__disbursed_date__gt = end_date ))

        basemodel_qry_next_pay = basemodel_obj.filter(Q(PayableorReceivable='Payable',netaspayments__Paid_date__gt=end_date ))

        payments_model_qry = NetASPayments.objects.filter(Paid_date__range=[startdate,enddate])
        receivables_qry = NetASReceivables.objects.filter(disbursed_date__range=[startdate,enddate])
        basemodel_obj_rev = RevisionBaseModel.objects.filter(Q(Letter_date__range=[startdate,enddate]) , Q(Acc_type = 'NETAS_REVISION'))
    else:
        return HttpResponse('error' , status = 404)

    excess_model_qry = ExcessBaseModel.objects.filter(Paid_date__range = [startdate,enddate] )
    summary_sheet_data = [['Fin Code','Entity Name' , 'Closing Balance']]

    
    for user in all_users:
        try:
            fincode=user[1].replace(" ", "")
            closing_balance_list = list(closing_balances_qry.filter(Fin_code = fincode).values_list('Closing_amount',flat=True))
            closing_balance = closing_balance_list[0] if len(closing_balance_list) else 0

            source=wb.active
            
            target=wb.copy_worksheet(source)
            entity_name = [character for character in user[0] if character.isalnum()]
            entity_name = "".join(entity_name).upper()
            # if two entities names are same then generate Name with some random number
            sheet_name=entity_name[:20] if entity_name[:20] not in wb.sheetnames else entity_name[:20]+str(random.randint(1,10))
        
            target.title=sheet_name
            ws=wb[sheet_name]
            
            ws['A1'].value='DETAILS OF '+acc_type+' PAYMENT AND DISBURSEMENT of '+ str(user[0]) +'  DURING ('+(startdate.strftime("%d.%m.%Y"))+'-'+enddate.strftime("%d.%m.%Y") +')'
            
            start_payable, start_receivable = 6 , 6
            # payables
            #import pdb ; pdb.set_trace()
            all_paid_inrange = list(payments_model_qry.filter(paystatus_fk__Fin_code=fincode , paystatus_fk__Revision_no = 0).values_list('paystatus_fk__Fin_year','paystatus_fk__Week_no','paystatus_fk__Entity','paystatus_fk__Final_charges','paystatus_fk__Letter_date','Paid_date','Paid_amount'))
            
            all_paid_inrange_list=[list(ele) for ele in all_paid_inrange]

            not_paid_inrange=list(basemodel_qry.filter(Fin_code=fincode).values_list('Fin_year','Week_no','Entity','Final_charges','Letter_date'))


            
            #paid_inrange=list(basemodel_qry_prev.filter(Fin_code=fincode).values_list('Fin_year','Week_no','Entity','Final_charges','Letter_date'))

            paid_outrange = list(basemodel_qry_next_pay.filter(Fin_code=fincode).values_list('Fin_year','Week_no','Entity','Final_charges','Letter_date'))
            
            not_paid_inrange_list=[list(ele) for ele in not_paid_inrange]
            paid_outrange_list = [list(ele) for ele in paid_outrange]
            not_paid_inrange_list =  not_paid_inrange_list+paid_outrange_list
            
            for not_paid in not_paid_inrange_list:
                not_paid.append('')
                not_paid.append(0)
                all_paid_inrange_list.append(not_paid.copy())
            df_reco = pd.DataFrame(all_paid_inrange_list)
            if len(df_reco)>0:
                df_reco.columns = ['Fin_year','Week_no','Entity','Final_charges','Letter_date','Paid_date','Paid_amount']
                #df_reco.loc[df_reco['Week_no'] == 50, 'Final_charges'] = 0
                df_reco.loc[df_reco.duplicated(subset=['Week_no', 'Entity', 'Final_charges'], keep='first'),'Final_charges'] = 0
                all_paid_inrange_list1 = df_reco.values.tolist()
            else : 
                all_paid_inrange_list1 = all_paid_inrange_list
            

            # get iom data
            for iom in all_paid_inrange_list1:
                dis_date=list(disbursed_entities_obj.filter(fin_year=iom[0],week_no=iom[1]).distinct().values_list('disstatus_fk__Disbursed_date',flat=True))
                iom.insert(5, dis_date[0]) if len(dis_date) > 0 else iom.insert(5, '')
                # modify WeekNo column to add Startdate and Enddate
                start_end_date_list = list(week_start_enddates_obj.filter(fin_year=iom[0] , week_no=iom[1]).values_list('start_date','end_date'))
                if len(start_end_date_list) > 0:
                    start_date_in = start_end_date_list[0][0]
                    end_date_in = start_end_date_list[0][1]

                    full_date_str = str(iom[1]) +'(' +start_date_in.strftime('%d.%m.%Y') + '-' + end_date_in.strftime('%d.%m.%Y') + ' ) '
                    # replace just week no with start and end dates
                    iom[1] = full_date_str
                # remove Fin year not required
                iom.remove(iom[0])
                
                if iom[5] =='':
                    pass
                elif iom[3] < startdate and (startdate <= iom[5] <= enddate):
                    iom[2] = 0
                elif (startdate <= iom[3] <= enddate) and (iom[5] > enddate):
                    iom[6] = 0
                else :
                    pass
                
                iom.append(float(iom[2]) - float(iom[6]))

            #excess payments if any
            excess_payments_qry = list(excess_model_qry.filter(Fin_code = fincode).values_list('Acc_Type','Entity','Final_charges','Paid_date','Final_charges'))
            excess_payments_list=[list(ele) for ele in excess_payments_qry]

            for excess in excess_payments_list:
                excess.insert(3, None)
                excess.insert(4, None)
                excess.append(0)

            all_paid_inrange_list1+= excess_payments_list
            # Receivables
            all_rcv_inrange_df=pd.DataFrame(receivables_qry.filter(rcvstatus_fk__Fin_code=fincode , rcvstatus_fk__Revision_no = 0).values('rcvstatus_fk__Week_no','rcvstatus_fk__Entity','rcvstatus_fk__Letter_date','rcvstatus_fk__Disbursement_date','rcvstatus_fk__Final_charges','Disbursed_amount','disbursed_date') , columns=['rcvstatus_fk__Week_no','rcvstatus_fk__Entity','rcvstatus_fk__Letter_date','rcvstatus_fk__Disbursement_date','rcvstatus_fk__Final_charges','Disbursed_amount','disbursed_date'])
            
            all_rcv_inrange_df['rcvstatus_fk__Letter_date'] = pd.to_datetime(all_rcv_inrange_df['rcvstatus_fk__Letter_date'])
            all_rcv_inrange_df.loc[all_rcv_inrange_df['rcvstatus_fk__Letter_date'] < start_date, 'rcvstatus_fk__Final_charges'] = 0
            all_rcv_inrange_df = all_rcv_inrange_df.drop(columns=['rcvstatus_fk__Letter_date'])
            
            all_rcv_outrange_df=pd.DataFrame(basemodel_qry_rcv.filter(Fin_code=fincode).values('Week_no','Entity','Disbursement_date','Final_charges') , columns=['Week_no','Entity','Disbursement_date','Final_charges'])
            all_rcv_outrange_df['Disbursed_amount'] = 0

            all_rcv_outrange_df['disbursed_date'] = pd.NaT

            all_rcv_out_next_df = pd.DataFrame(basemodel_qry_next_rcv.filter(Fin_code=fincode).values('Week_no','Entity','Disbursement_date','Final_charges') , columns=['Week_no','Entity','Disbursement_date','Final_charges'])
            all_rcv_out_next_df['Disbursed_amount'] = 0

            all_rcv_out_next_df['disbursed_date'] = pd.NaT
            
            all_rcv_outrange_df.columns = ['rcvstatus_fk__Week_no', 'rcvstatus_fk__Entity', 'rcvstatus_fk__Disbursement_date', 'rcvstatus_fk__Final_charges', 'Disbursed_amount', 'disbursed_date']
            all_rcv_out_next_df.columns = ['rcvstatus_fk__Week_no', 'rcvstatus_fk__Entity', 'rcvstatus_fk__Disbursement_date', 'rcvstatus_fk__Final_charges', 'Disbursed_amount', 'disbursed_date']

            all_rcv_inrange_df_1 = pd.concat([all_rcv_inrange_df,all_rcv_outrange_df],ignore_index=True)
            all_rcv_inrange_df = pd.concat([all_rcv_inrange_df_1,all_rcv_out_next_df],ignore_index=True)
            
            if not all_rcv_inrange_df.empty:
                # Convert disbursed_date to datetime
                all_rcv_inrange_df["disbursed_date"] = pd.to_datetime(all_rcv_inrange_df["disbursed_date"])
                all_rcv_inrange_df["rcvstatus_fk__Disbursement_date"] = pd.to_datetime(all_rcv_inrange_df["rcvstatus_fk__Disbursement_date"])

                # Group by Week_no and Entity
                
                grouped_df = all_rcv_inrange_df.groupby(
                    ["rcvstatus_fk__Week_no", "rcvstatus_fk__Entity"]
                ).agg({
                        "rcvstatus_fk__Final_charges": "mean",
                        "Disbursed_amount": "sum",
                        "disbursed_date": "max",
                        "rcvstatus_fk__Disbursement_date" : "max",
                    }
                ).reset_index()
                
                
                # Extract date as datetime.date
                grouped_df["disbursed_date"] = grouped_df["disbursed_date"].dt.date
                grouped_df["rcvstatus_fk__Disbursement_date"] = grouped_df["rcvstatus_fk__Disbursement_date"].dt.date
                
                grouped_df.loc[grouped_df["rcvstatus_fk__Disbursement_date"] < startdate , "rcvstatus_fk__Final_charges"] = 0
                grouped_df = grouped_df.drop(columns=["rcvstatus_fk__Disbursement_date"])
                
                all_rcv_inrange_list = grouped_df.values.tolist()
                # iterate over list and find Balance due
                for rcv in all_rcv_inrange_list:
                    balance = float(rcv[2])-float(rcv[3])
                    rcv.insert( 4 , balance)
            else:
                all_rcv_inrange_list=[]

            # excess payments if disbursed
            excess_receivables_qry = list(excess_model_qry.filter(Fin_code = fincode , Is_disbursed = True).values_list('Acc_Type','Entity','Final_charges','Final_charges','Paid_date'))
            excess_receivables_list=[list(ele) for ele in excess_receivables_qry]

            for excess in excess_receivables_list:
                excess.insert(4,0) # this is outstanding 
            
            all_rcv_inrange_list+=excess_receivables_list
            # writing into excel Payable
            i=0
            payable_out=0
            for x in range(start_payable,len(all_paid_inrange_list1)+start_payable):
                j=0
                for y in range(1,9):
                    ws.cell(row=x,column=y).value=all_paid_inrange_list1[i][j]
                    j+=1
                
                payable_out+=all_paid_inrange_list1[i][-1]
                i+=1 

            start_payable+=i
            
            # Receivables
            i=0
            receivable_out=0
            for x in range(start_receivable,len(all_rcv_inrange_list)+start_receivable):
                j=0
                for y in range(9,15):
                    ws.cell(row=x,column=y).value=all_rcv_inrange_list[i][j]
                    j+=1     
                receivable_out+=all_rcv_inrange_list[i][-2]
                i+=1 
            start_receivable+=i
            

            present_row='6'
            if start_payable == 6:
                ws['B7'].value='TOTAL'
                ws['C7'].value=0
                ws['G7'].value=0
                ws['H7'].value=0
            else:
                present_row=str(start_payable)
                sum_hvalue = sum(ws[f"H{row}"].value or 0 for row in range(6, start_payable))
                
                ws['B'+present_row].value='TOTAL'
                ws['C'+present_row].value="=SUM(C6:C"+str(start_payable-1)+")"
                ws['G'+present_row].value="=SUM(G6:G"+str(start_payable-1)+")"
                ws['H'+present_row].value= sum_hvalue
                
            if start_receivable == 6:
                receivable_row='6'
                ws['J7'].value='TOTAL'
                ws['K7'].value=0
                ws['L7'].value=0
                ws['M7'].value=0

            else:
                receivable_row=str(start_receivable)

                sum_mvalue = sum(ws[f"M{row}"].value or 0 for row in range(6, start_receivable))

                ws['J'+receivable_row].value='TOTAL'
                ws['K'+receivable_row].value="=SUM(K6:K"+str(start_receivable-1)+")"
                ws['L'+receivable_row].value="=SUM(L6:L"+str(start_receivable-1)+")"
                ws['M'+receivable_row].value = sum_mvalue
            
            # # Fetch cell values
            H_present = ws['H' + str(present_row)].value or 0  # Default to 0 if None
            M_receivable = ws['M' + str(receivable_row)].value or 0
            
            # # Compute net balance
            net_balance = H_present - M_receivable + closing_balance
            # net_balance = "=H"+present_row+"-M"+receivable_row+"+H2"
            if start_payable==6 and start_receivable==6:
                ws['F8'].value='Net Balance'
                ws['G8'].value=0
            else:
                ws['G'+str(start_payable+2)].value='Net Balance'
                ws['H'+str(start_payable+2)].value = net_balance
                
                ws['G'+str(start_payable+2)].fill = PatternFill(start_color="00FFFF00", end_color="00FFFF00", fill_type = "solid") 
            # this is to add last month closing balance
            ws['H2'] = closing_balance
            
            # summary sheet
            summary_sheet_data.append([fincode , user[0] , net_balance])
        except Exception as e:
            continue

    del wb['Sheet1']   #deleting temp sheet
    wb = prepareSummarySheet(wb , summary_sheet_data)

    in_filename=str(req_data['formdata']['acc_type'])+'_MonthReconciliation_'+str(req_data['formdata']['selected_month'])+'.xlsx'
    full_path=os.path.join(directory, in_filename)
    wb.save(full_path)
    wb.save(response)    
    wb.close()
    return response  
    
   



def downloadSummaryReconReport(request):
    try:
        req_data=json.loads(request.body)
        selected_month_year = req_data['formdata']['selected_month']
        start_date,end_date=get_month_start_end_dates(selected_month_year)
           
        enddate=add530hrstoDateString(end_date).date()

        # get summary 
        closing_balance_df = pd.DataFrame(ClosingBalances.objects.filter(Month_year = selected_month_year , Acc_type = req_data['formdata']['acc_type']).values('Fin_code' , 'Closing_amount') , columns = ['Fin_code' , 'Closing_amount'])

        registration_df = pd.DataFrame(Registration.objects.filter(Q(end_date__isnull=True)|Q(end_date__gte=datetime.today())).order_by('fees_charges_name').values_list('fees_charges_name','fin_code') , columns=['fees_charges_name','fin_code'])

        merged_df = pd.merge(closing_balance_df ,registration_df , left_on='Fin_code' , right_on='fin_code' , how='left')
        merged_df.drop(columns=['fin_code'] , inplace=True)
        merged_df.rename(columns= {'Fin_code' : 'Party Code' , 'fees_charges_name':'Name' ,'Closing_amount':'MO Balance'} , inplace=True)

        # merged_df['MO Balance']=merged_df['MO Balance'].apply(lambda x :format_indian_currency(x) )

        # add two extra columns like Fin Balance and Remarks
        merged_df['Fin Balance'] = None
        merged_df['Remarks'] = None
        # Specify the new order
        new_order = ["Party Code", "Name", "Fin Balance" ,"MO Balance" , "Remarks"]
        # Reorder the DataFrame
        merged_df = merged_df[new_order]
        parent_folder = os.path.abspath(os.path.join(base_dir, os.pardir))
        directory = os.path.join(parent_folder, 'Files', 'ReconSummary' )
        if not os.path.exists(directory):
                # Create the directory if it doesn't exist
                os.makedirs(directory)
        in_filename='recon_summary&'+str(selected_month_year)+'.csv'
        full_path=os.path.join(directory, in_filename)
        temp_out=open(full_path,'w')
        temp_out.write(' \n ')
        temp_out.write('Reconciliation Summary as on '+ enddate.strftime('%d.%m.%Y') +' \n')
        temp_out.close()
        merged_df.to_csv(full_path, mode='a',index=False )  
  
        return FileResponse(open(full_path,'rb'),content_type='text/csv') 
    
    except Exception as e:
        print(e)
        return HttpResponse(extractdb_errormsg(e),status=400)

def downloadReconUploadStatus(request):
    try:
        req_data=json.loads(request.body)['formdata']
        acc_type = req_data['acc_type']
        fin_year = req_data['fin_year']
        quarter = req_data['quarter']
        
        if not checkBillsNotified(acc_type , fin_year , quarter):
            return HttpResponse( 'Bills not notified , Please wait', status = 404)
        registration_df = pd.DataFrame(Registration.objects.filter(Q(end_date__isnull=True)|Q(end_date__gte=datetime.today())).order_by('fees_charges_name').values_list('fees_charges_name','fin_code') , columns=['fees_charges_name','fin_code'])

        signed_df = pd.DataFrame(ReconUploadStatus.objects.filter(Acc_type = acc_type ,Fin_year = fin_year , Quarter = quarter ).values('Fin_code','Upload_status','Uploaded_time') , columns=['Fin_code','Upload_status','Uploaded_time'] )

        merged_df = pd.merge(registration_df ,signed_df , left_on='fin_code' , right_on='Fin_code' , how='left')
        merged_df.drop(columns=['Fin_code' ] , inplace=True)
        merged_df.fillna('',inplace=True)
        merged_df.rename(columns= {'fin_code' : 'Party Code' , 'fees_charges_name':'Name' ,'Upload_status':'Upload Status' ,'Uploaded_time' :'Uploaded Time'} , inplace=True)
        # Specify the new order
        new_order = ["Party Code", "Name", "Upload Status" ,"Uploaded Time"]
        # Reorder the DataFrame
        merged_df = merged_df[new_order]
        parent_folder = os.path.abspath(os.path.join(base_dir, os.pardir))
        directory = os.path.join(parent_folder, 'Files', 'ReconSummary' )
        if not os.path.exists(directory):
            # Create the directory if it doesn't exist
            os.makedirs(directory)
        in_filename='recon_summary&'+fin_year+'&'+quarter+'.csv'
        full_path=os.path.join(directory, in_filename)
        temp_out=open(full_path,'w')
        temp_out.write(' \n ')
        temp_out.write('Reconciliation Summary for the fin year '+ req_data['fin_year'] +' and for the quarter '+ req_data['quarter'] +' \n')
        temp_out.close()
        merged_df.to_csv(full_path, mode='a',index=False )  
        return FileResponse(open(full_path,'rb'),content_type='text/csv') 
    
    except Exception as e:
        return HttpResponse(extractdb_errormsg(e),status=400)
