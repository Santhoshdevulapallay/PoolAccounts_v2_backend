from django.contrib import admin
from django.urls import path ,include
from . import views
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated

urlpatterns = [
      path('fetch_srpc_bills/',views.fetchSRPCBills ),
      path('upload_rpc_bills_manually/',views.uploadRPCBillManually ),

      path('srpc_file_status/',views.srpcFileStatus ),
      path('check_bill_validation/', views.checkBillValidation ),
     
      path('mapping_bills/', views.mapBills),
      path('get_ir_revisionno/', views.getIRRevision ),
      path('get_weekstartend_dates/', views.getWeekStartEndDates ),

      path('check_interregional/', views.checkInterRegional ),
      path('store_ir/', views.storeIR ),
      # before storing get temporary stored bills
      path('get_temporary_bills/', views.temporaryBills ),
      path('store_bills/', views.storeBills ),
      path('store_nldc_ir_bills/', views.storeNLDCIntimatedIRBill ),
      
      #shortfall bill
      path('get_shortfall_states/', views.shortfallStates ),
      path('store_shortfall_bills/', views.storeShortfallBill ),
      
      path('view_bills/', views.viewBills ),
      path('download_bills/', views.downloadBills ),
      path('download_payrcv/', views.downloadPayRcv ),
      # bank statement 
      path('bankstmt_store/', views.bankStmtStore ),
      path('get_reconciled_dates/', views.reconciledDates ),
      path('month_bank_recon/', views.monthBankRecon ),
      path('view_bank_statement/', views.viewBankStatement ),

      path('bank_stmt_status/', views.bankStmtStatus ),
      path('get_bank_txns/', views.getBankTxns ),
      path('save_bank_payments/', views.saveBankPayments ),
      path('getBillAmount/', views.getBillAmount ),
     
      # admin approval payments
      path('pending_approvals/', views.pendingApprovals ),
      path('approve_payments/', views.approvePayments ),
      path('reject_payments/', views.rejectPayments ),

      # disbursement
      path('get_lastdisbursed_wk/', views.getLastDisbursedWk),
      path('transfer_to_legacy/', views.transfertoLegacy),
      path('transfer_to_main/', views.transfertoMain),
      path('get_disburse_details/', views.getDisburseDetails),
      # path('proceed_disbursement/', views.proceedDisbursement),
      path('store_disbursedvalues/', views.storeDisbursedValues),
      path('final_disbursement/', views.finalDisbursement),
      path('revoke_disbursement/', views.revokeDisbursement),
      # REPORTS and IOMS
      path('download_iom/', views.downloadIOM),
      path('download_transferIOM/', views.downloadTransferIOM),

      # Finance Section
      path('download_jv/', views.downloadJV),
      path('download_bankstatement_finance/', views.downloadBankStmtFin),
      path('get_outstanding_details/', views.getOutstandingDetails),
      path('get_outstanding_weekwise/', views.getOutstandingWeekWise),
      path('download_outstanding/', views.downloadOutstandingXL),
      path('get_unmappedtxn_details/', views.getUnMappedTxns),
      path('get_flaggedtxn_details/',views.getFlaggedTxns),
      path('revoke_flaggedtxns/',views.revokeTxns),
      # Interest section
      path('get_monthly_interestcalc/', views.getMonthlyIntersetCalc),
      path('download_interest_details/', views.downloadIntersetCalc),
      path('save_interest_bills/', views.saveInterestBills),
      path('download_interestbills/', views.downloadInterestbills),
      path('store_interest_finalbills/', views.storeFinalIntBills),

      # Revision Module
      path('get_max_revision_weekdates/', views.getWeekMaxRevision),
      path('get_revision_checkbill/', views.getRevisionCheckBills),
      path('get_revision_checkbill_userentry/', views.getRevisionCheckBillsUserEntry),
      # not the final bill but individual bills like week wise and update in basemodel
      path('save_revision_bill/', views.saveRevisionBill),
      path('get_all_revision_dates/', views.getAllRevisionDates),
      path('net_revision_bills/', views.netRevisionBills),
      path('download_revision_draft_bill/', views.downloadRevisionDraftBill),
      path('store_net_revision_bills/', views.storeNetRevisionBills),
      # revision iom
      path('revision_gen_iom/', views.revisionGenIOM),

      # Intimate to NLDC 
      path('intimate_surplus/', views.intimateNLDC),
      path('get_nldc_intimate_summary/', views.getIntimateSummary),
      path('transfer_surplus/', views.transferSurplus),
      path('nldc_splitamount/', views.nldcSplitAmount),

      # Excess Payments
      path('get_excess_summary/', views.getExcessSummary),
      path('excess_gen_iom/', views.generateExcessIOM),

      # Signed IOM
      path('get_disbursed_weeks/', views.getDisbursedWeeks),
      path('upload_signed_iom/', views.uploadSignedIOM),
      path('download_signed_iom/', views.downloadSignedIOM),
      path('download_fin_excel/', views.downloadFinExcel),

      # Mail section
      path('send_mail_notmapped_txns/', views.sendMailNotMappedTxns),
      path('send_mail_outstanding_txns/', views.sendMailOutstandingTxns),
      # SCUC CC
      path('get_scuc_cc_entities/',views.scucCCEntities),
      path('store_scuc_cc_bills/',views.storescucCCBills),
      # Reconciliation 
      path('notify_recon_bills/',views.notifyReconBills),
      path('download_recon_excel/', views.downloadReconReport),
      path('download_summary_recon_excel/', views.downloadSummaryReconReport),
      path('download_recon_upload_status/', views.downloadReconUploadStatus),

      path('get_last_recon_submits/', views.getLastReconSubmits),
      path('utility_show_recon/', views.userRecon),
      path('generate_recon_pdf/', views.generateReconPDF),
      path('upload_recon_pdf/', views.uploadReconPDF),
      path('get_uploaded_copies/', views.getUploadedCopies),
      path('approve_reject_signed_copies/', views.approveRejectSignedCopies),
      path('download_recon_uploaded_pdfs/', views.downloadUploadedPDFs),
      # 
      # path('create_users/', views.createUsers),
]

