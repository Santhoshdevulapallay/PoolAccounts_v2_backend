from django.contrib import admin
from django.urls import path ,include
from . import views
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated

urlpatterns = [
      path('fetch_srpc_bills/',permission_classes([IsAuthenticated])(views.fetchSRPCBills )),
      path('srpc_file_status/',permission_classes([IsAuthenticated])(views.srpcFileStatus )),
      path('check_bill_validation/', permission_classes([IsAuthenticated])(views.checkBillValidation )),
     
      path('mapping_bills/',permission_classes([IsAuthenticated])( views.mapBills)),
      path('get_ir_revisionno/',permission_classes([IsAuthenticated])( views.getIRRevision )),
      path('get_weekstartend_dates/', permission_classes([IsAuthenticated])(views.getWeekStartEndDates )),

      path('check_interregional/', permission_classes([IsAuthenticated])(views.checkInterRegional )),
      path('store_ir/', permission_classes([IsAuthenticated])(views.storeIR )),
      # before storing get temporary stored bills
      path('get_temporary_bills/', permission_classes([IsAuthenticated])(views.temporaryBills )),
      path('store_bills/', permission_classes([IsAuthenticated])(views.storeBills )),
      path('store_nldc_ir_bills/', permission_classes([IsAuthenticated])(views.storeNLDCIntimatedIRBill )),
      
      path('view_bills/', permission_classes([IsAuthenticated])(views.viewBills )),
      path('download_bills/', permission_classes([IsAuthenticated])(views.downloadBills )),
      path('download_payrcv/', permission_classes([IsAuthenticated])(views.downloadPayRcv )),
      # bank statement 
      path('bankstmt_store/', permission_classes([IsAuthenticated])(views.bankStmtStore )),
      path('get_reconciled_dates/', permission_classes([IsAuthenticated])(views.reconciledDates )),
      path('month_bank_recon/', permission_classes([IsAuthenticated])(views.monthBankRecon )),
      path('view_bank_statement/', permission_classes([IsAuthenticated])(views.viewBankStatement )),

      path('bank_stmt_status/', permission_classes([IsAuthenticated])(views.bankStmtStatus )),
      path('get_bank_txns/', permission_classes([IsAuthenticated])(views.getBankTxns )),
      path('save_bank_payments/', permission_classes([IsAuthenticated])(views.saveBankPayments )),
      path('getBillAmount/', permission_classes([IsAuthenticated])(views.getBillAmount )),
     
      # admin approval payments
      path('pending_approvals/', permission_classes([IsAuthenticated])(views.pendingApprovals )),
      path('approve_payments/', permission_classes([IsAuthenticated])(views.approvePayments )),
      path('reject_payments/', permission_classes([IsAuthenticated])(views.rejectPayments )),

      # disbursement
      path('get_lastdisbursed_wk/', permission_classes([IsAuthenticated])(views.getLastDisbursedWk)),
      path('get_disburse_details/', permission_classes([IsAuthenticated])(views.getDisburseDetails)),
      # path('proceed_disbursement/', views.proceedDisbursement),
      path('store_disbursedvalues/', permission_classes([IsAuthenticated])(views.storeDisbursedValues)),
      path('final_disbursement/', permission_classes([IsAuthenticated])(views.finalDisbursement)),
      path('revoke_disbursement/', permission_classes([IsAuthenticated])(views.revokeDisbursement)),
      # REPORTS and IOMS
      path('download_iom/',permission_classes([IsAuthenticated])( views.downloadIOM)),
      path('download_transferIOM/',permission_classes([IsAuthenticated])( views.downloadTransferIOM)),

      # Finance Section
      path('download_jv/', permission_classes([IsAuthenticated])(views.downloadJV)),
      path('download_bankstatement_finance/', permission_classes([IsAuthenticated])(views.downloadBankStmtFin)),
      path('get_outstanding_details/', permission_classes([IsAuthenticated])(views.getOutstandingDetails)),
      path('get_outstanding_weekwise/', permission_classes([IsAuthenticated])(views.getOutstandingWeekWise)),
      path('download_outstanding/', permission_classes([IsAuthenticated])(views.downloadOutstandingXL)),
      path('get_unmappedtxn_details/', permission_classes([IsAuthenticated])(views.getUnMappedTxns)),

      # Interest section
      path('get_monthly_interestcalc/', permission_classes([IsAuthenticated])(views.getMonthlyIntersetCalc)),
      path('download_interest_details/', permission_classes([IsAuthenticated])(views.downloadIntersetCalc)),
      path('save_interest_bills/', permission_classes([IsAuthenticated])(views.saveInterestBills)),
      path('download_interestbills/', permission_classes([IsAuthenticated])(views.downloadInterestbills)),
      path('store_interest_finalbills/', permission_classes([IsAuthenticated])(views.storeFinalIntBills)),

      # Revision Module
      path('get_max_revision_weekdates/', permission_classes([IsAuthenticated])(views.getWeekMaxRevision)),
      path('get_revision_checkbill/', permission_classes([IsAuthenticated])(views.getRevisionCheckBills)),
      # not the final bill but individual bills like week wise and update in basemodel
      path('save_revision_bill/', permission_classes([IsAuthenticated])(views.saveRevisionBill)),
      path('get_all_revision_dates/',permission_classes([IsAuthenticated])( views.getAllRevisionDates)),
      path('net_revision_bills/', permission_classes([IsAuthenticated])(views.netRevisionBills)),
      path('download_revision_draft_bill/', permission_classes([IsAuthenticated])(views.downloadRevisionDraftBill)),
      path('store_net_revision_bills/', permission_classes([IsAuthenticated])(views.storeNetRevisionBills)),
      # revision iom
      path('revision_gen_iom/', permission_classes([IsAuthenticated])(views.revisionGenIOM)),

      # Intimate to NLDC 
      path('intimate_surplus/', permission_classes([IsAuthenticated])(views.intimateNLDC)),
      path('get_nldc_intimate_summary/', permission_classes([IsAuthenticated])(views.getIntimateSummary)),
      path('transfer_surplus/', permission_classes([IsAuthenticated])(views.transferSurplus)),
      path('nldc_splitamount/', permission_classes([IsAuthenticated])(views.nldcSplitAmount)),

      # Excess Payments
      path('get_excess_summary/', permission_classes([IsAuthenticated])(views.getExcessSummary)),
      path('excess_gen_iom/', permission_classes([IsAuthenticated])(views.generateExcessIOM)),

      # Signed IOM
      path('get_disbursed_weeks/', permission_classes([IsAuthenticated])(views.getDisbursedWeeks)),
      path('upload_signed_iom/', permission_classes([IsAuthenticated])(views.uploadSignedIOM)),
      path('download_signed_iom/', permission_classes([IsAuthenticated])(views.downloadSignedIOM)),
      path('download_fin_excel/', permission_classes([IsAuthenticated])(views.downloadFinExcel)),

      # Mail section
      path('send_mail_notmapped_txns/', permission_classes([IsAuthenticated])(views.sendMailNotMappedTxns)),
      path('send_mail_outstanding_txns/', permission_classes([IsAuthenticated])(views.sendMailOutstandingTxns)),
      # Reconciliation 
      path('download_recon_excel/', permission_classes([IsAuthenticated])(views.downloadReconReport)),
      path('download_summary_recon_excel/', permission_classes([IsAuthenticated])(views.downloadSummaryReconReport)),
]
