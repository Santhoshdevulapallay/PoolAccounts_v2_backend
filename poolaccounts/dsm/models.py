from django.db import models
from registration.models import *
from django.utils import timezone

from .mbas_models import *
from .sras_models import *
from .tras_models import *
from .reac_models import *
from .interest_models import *
from .ancillarynet_models import *
from .netas_models import * 
from .scuc_models import * 
from .excess_models import * 
from .revision_models import * 
from .cong_models import *
from .reconciliation_models import *
from .legacy_models import *
from .short_fall_models import *
from .scuc_cc_models import *
from .recon_models import *
# Create your models here.

class DSMBaseModel(models.Model):
      Fin_year=models.CharField(max_length=15,blank=True)
      Week_no=models.IntegerField(blank=True)
      Week_startdate=models.DateField(default=None)
      Week_enddate=models.DateField(default=None)
      
      Revision_no =models.IntegerField(default=0 , blank=True,null=True)
      Letter_date=models.DateField(default=None,blank=True,null=True)
      Due_date=models.DateField(default=None,blank=True,null=True)
      Disbursement_date=models.DateField(default=None,blank=True,null=True)
      Lc_date=models.DateField(default=None,blank=True,null=True)
      Interest_levydate=models.DateField(default=None,blank=True,null=True)

      # Deviation Data also 
      Entity=models.TextField(default=None)
      Final_charges=models.FloatField(default=None,blank=True)
      PayableorReceivable=models.CharField(max_length=50,default=None,blank=True)
      Remarks=models.TextField(default=None,blank=True,null=True)
      Fin_code=models.CharField(max_length=100 ,default=None)    

      Is_disbursed=models.BooleanField(default=False,blank=True,null=True)
      Fully_disbursed=models.CharField(max_length=10,default=None,blank=True,null=True)     # P is partial and C is Complete

      Effective_start_date=models.DateField(default=None,blank=True,null=True)
      Effective_end_date=models.DateField(default=None,blank=True,null=True)
      Legacy_dues=models.BooleanField(default=False )
      
      def __str__(self):
            return self.Fin_code
      
      class Meta:
            db_table = 'dsm_basemodel'
            unique_together=['Fin_year','Week_no','Entity','Revision_no','Final_charges']


class Payments(models.Model):
      Paid_date=models.DateField(default=None)
      Description=models.CharField(max_length=400,default=None,blank=True,null=True)
      Paid_amount=models.FloatField(blank=True)
      Other_info=models.TextField(default=None,blank=True,null=True)
      Bank_type=models.CharField(default=None,blank=True,null=True)
      paystatus_fk=models.ForeignKey(DSMBaseModel,on_delete=models.SET_NULL,null=True)
      approved_date=models.DateTimeField(default=timezone.now )
      Is_disbursed=models.BooleanField(default=False,blank=True,null=True)
      is_revision = models.BooleanField(default=False,blank=True,null=True)
      def __str__(self):
        return ""
      
      class Meta:
            db_table = 'dsm_payments'
            unique_together=['Paid_date','Description','Paid_amount','paystatus_fk']
            
class DSMReceivables(models.Model):
      Disbursed_amount=models.FloatField(blank=True,null=True)
      rcvstatus_fk=models.ForeignKey(DSMBaseModel,on_delete=models.SET_NULL,null=True)
      
      iom_date=models.DateField(default=None,blank=True,null=True)
      disbursed_date=models.DateField(default=None,blank=True,null=True)
      neft_txnno=models.CharField(max_length=255,default=None,blank=True,null=True)
      is_revision = models.BooleanField(default=False,blank=True,null=True)
      def __str__(self):
        return self.rcvstatus_fk
      
      class Meta:
            db_table = 'dsm_receivables'
            
class IRBaseModel(models.Model):
      Fin_year=models.CharField(max_length=15,blank=True)
      Week_no=models.IntegerField(blank=True)

      Consider_Year=models.CharField(max_length=15,default=None,blank=True,null=True)
      Consider_Week_no=models.CharField(max_length=10,default=None,blank=True,null=True)
      
      Week_startdate=models.DateField(default=None)
      Week_enddate=models.DateField(default=None)

      Applicable_startdate=models.DateField(default=None,blank=True,null=True)
      Applicable_enddate=models.DateField(default=None,blank=True,null=True)

      Revision_no =models.IntegerField(default=None , blank=True,null=True)
  
      Letter_date=models.DateField(default=None,blank=True,null=True)
      Due_date=models.DateField(default=None,blank=True,null=True)
      Disbursement_date=models.DateField(default=None,blank=True,null=True)
      Lc_date=models.DateField(default=None,blank=True,null=True)
      Interest_levydate=models.DateField(default=None,blank=True,null=True)

      # Deviation Data also 
      Entity=models.TextField(default=None)
      Final_charges=models.FloatField(default=None,blank=True)
      PayableorReceivable=models.CharField(max_length=50,default=None,blank=True)
      Remarks=models.TextField(default=None,blank=True,null=True)
      Fin_code=models.CharField(max_length=100 ,default=None)    
      
      Is_disbursed=models.BooleanField(default=False,blank=True,null=True)
      Fully_disbursed=models.CharField(max_length=10,default=None,blank=True,null=True)

      def __str__(self):
            return self.Fin_code
      
      class Meta:
            db_table = 'ir_basemodel'
            unique_together=['Fin_year','Week_no','Entity']

class IRPayments(models.Model):
      Paid_date=models.DateField(default=None)
      Description=models.CharField(max_length=400,default=None,blank=True,null=True)
      Paid_amount=models.FloatField(blank=True)
      Other_info=models.TextField(default=None,blank=True,null=True)
      Bank_type=models.CharField(default=None,blank=True,null=True)
      paystatus_fk=models.ForeignKey(IRBaseModel,on_delete=models.SET_NULL,null=True)
      approved_date=models.DateTimeField(default=timezone.now )
      Is_disbursed=models.BooleanField(default=False,blank=True,null=True)

      def __str__(self):
        return self.paystatus_fk
      class Meta:
            db_table = 'ir_payments'

class IRReceivables(models.Model):
      Disbursed_amount=models.FloatField(blank=True,null=True)
      rcvstatus_fk=models.ForeignKey(IRBaseModel,on_delete=models.SET_NULL,null=True)
      
      def __str__(self):
        return self.rcvstatus_fk
      
      class Meta:
            db_table = 'ir_receivables'

class TemporaryMatched(models.Model):
      Acc_type=models.CharField(max_length=50,default=None)
      Fin_year=models.CharField(max_length=10,blank=True)
      Week_no=models.IntegerField(blank=True)
      Entity=models.CharField(max_length=500,default=None)
      Fin_code=models.CharField(max_length=15,default=None)
      DevFinal=models.CharField(max_length=50,default=None,blank=True,null=True)
      PayRcv=models.CharField(max_length=50,default=None,blank=True,null=True)
      Revision_no =models.IntegerField(default=None , blank=True,null=True)
      Is_infirm=models.BooleanField(default=None,blank=True,null=True)
      
      def __str__(self):
            return self.Fin_code
      
      class Meta:
            db_table = 'temporary_matched'
            unique_together=['Acc_type','Fin_year','Week_no','Entity']

class TemporaryInterRegional(models.Model):
      Fin_year=models.CharField(max_length=10,default=None)
      Week_no=models.IntegerField(default=None)
      WRSR=models.FloatField(default=None,blank=True,null=True)
      ERSR=models.FloatField(default=None,blank=True,null=True)
      WRWR=models.FloatField(default=None,blank=True ,null=True)
      ERER=models.FloatField(default=None,blank=True,null=True)
      WR_Revision_no =models.IntegerField(default=None , blank=True,null=True)
      ER_Revision_no =models.IntegerField(default=None , blank=True,null=True)

      def __str__(self):
            return self.WRSR
      
      class Meta:
            db_table = 'temporary_interregional'
            # unique_together=['Fin_year','Week_no','WRWR','ERER','WR_Revision_no','ER_Revision_no']

class BankStatement(models.Model):
      ValueDate=models.DateField(default=None)
      PostDate=models.DateField(default=None)
      Description=models.CharField(max_length=400,default=None,blank=True,null=True)
      Debit=models.FloatField(default=None,blank=True,null=True)
      Credit=models.FloatField(default=None,blank=True,null=True)
      Balance=models.CharField(default=None,blank=True,null=True)
      IsMapped=models.BooleanField(default=None)
      SplitStatus=models.CharField(default=None,max_length=5,blank=True,null=True)  # C - Complte , P - Partial 
      IsSweep=models.BooleanField(default=None,blank=True,null=True)
      BankType=models.CharField(max_length=50,default=None,blank=True,null=True)

      def __str__(self):
            return self.ValueDate
      
      class Meta:
            db_table = 'bank_statement'
            unique_together=['ValueDate','Description','Credit']

class BankRecon(models.Model):
      Startdate=models.DateField(default=None)
      Enddate=models.DateField(default=None)
      Banktype=models.CharField(max_length=50,default=None)
      Is_reconciled=models.BooleanField(default=None)

      def __str__(self):
            return self.Startdate
      
      class Meta:
            db_table = 'bank_reconciliation'
            unique_together=['Startdate','Enddate','Banktype']

class MappedBankEntries(models.Model):
      Pool_Acc=models.CharField(max_length=55,default=None)
      Fin_year=models.CharField(max_length=10,default=None,blank=True,null=True)
      Week_no=models.IntegerField(default=None,blank=True,null=True)
      Amount=models.FloatField(default=None)
      Entity=models.CharField(max_length=350,default=None,blank=True,null=True)
      ValueDate_fk=models.ForeignKey(BankStatement,on_delete=models.SET_NULL,null=True)
      Other_info=models.TextField(default=None,blank=True,null=True)
      Status=models.CharField(max_length=5,default=None,blank=True,null=True)  # N- Notified , A-Approved , R_Rejected
      Reject_remarks=models.TextField(default=None,blank=True,null=True)
      Parent_id=models.IntegerField(default=None,blank=True,null=True)

      class Meta:
            db_table = 'mapped_bankentries'
            # unique_together=['Pool_Acc','Fin_year','Week_no','Entity','ValueDate_fk','Status','Parent_id']

class DisbursementStatus(models.Model):
      Disbursed_date=models.DateField(default=None)
      Surplus_amt=models.FloatField(default=None,blank=True,null=True)
      dsm=models.BooleanField(default=False,null=True)
      legacy_surplus_amt = models.FloatField(default=None,blank=True,null=True)
      dsm_collected=models.FloatField(default=None,null=True)
      sras_collected=models.FloatField(default=None,null=True)
      tras_collected=models.FloatField(default=None,null=True)
      mbas_collected=models.FloatField(default=None,null=True)
      reac_collected=models.FloatField(default=None,null=True)
      legacy_status = models.BooleanField(default=False,null=True)
      sras=models.BooleanField(default=False,null=True)
      tras=models.BooleanField(default=False,null=True)
      mbas=models.BooleanField(default=False,null=True)
      reac=models.BooleanField(default=False,null=True)
      ir=models.BooleanField(default=False,null=True)
      net_as=models.BooleanField(default=False,null=True)
      cong=models.BooleanField(default=False,null=True)

      dsm_prevwk=models.BooleanField(default=False,null=True)
      sras_prevwk=models.BooleanField(default=False,null=True)
      tras_prevwk=models.BooleanField(default=False,null=True)
      mbas_prevwk=models.BooleanField(default=False,null=True)
      reac_prevwk=models.BooleanField(default=False,null=True)
      net_as_prevwk=models.BooleanField(default=False,null=True)
      ir_prevwk=models.BooleanField(default=False,null=True,blank=True)
      cong_prevwk=models.BooleanField(default=False,null=True,blank=True)

      revision_disbursed=models.FloatField(default=None,null=True)
      remarks=models.CharField(default=None,blank=True,null=True)
      final_disburse=models.BooleanField(default=False,null=True)
      
      def __str__(self):
        return str(self.Disbursed_date)
      
      class Meta:
            db_table = 'disbursement_status'
            unique_together=['Disbursed_date']

class DisbursedEntities(models.Model):
      fin_year=models.CharField(max_length=15,blank=True)
      week_no=models.IntegerField(blank=True)
      entity=models.TextField(default=None)
      final_charges=models.FloatField(default=None)
      pool_acctype=models.CharField(max_length=50,default=None,blank=True,null=True)
      disstatus_fk=models.ForeignKey(DisbursementStatus,on_delete=models.SET_NULL,null=True)
      fin_code=models.CharField(default=None)
      payrcv=models.CharField(default=None,max_length=15,blank=True,null=True)
      is_prevweeks=models.BooleanField(default=False)
      parent_table_id=models.IntegerField(default=None,blank=True,null=True)
      def __str__(self):
        return self.entity
      
      class Meta:
            db_table = 'disbursed_entities'

class TempDisbursedWeeks(models.Model):
      pool_acctype=models.CharField(default=None,max_length=50)
      fin_year=models.CharField(max_length=15,blank=True)
      week_no=models.IntegerField(blank=True)

      def __str__(self):
            return self.pool_acctype
            
      class Meta:
            db_table = 'temp_disbursedweeks'
            unique_together=['pool_acctype','fin_year','week_no']

class IomSerialNo(models.Model):
      iom_date=models.DateField(default=None)
      dsm_iom_serial_no=models.CharField(max_length=255,default=None,blank=True,null=True)
      sras_iom_serial_no=models.CharField(max_length=255,default=None,blank=True,null=True)
      tras_iom_serial_no=models.CharField(max_length=255,default=None,blank=True,null=True)
      mbas_iom_serial_no=models.CharField(max_length=255,default=None,blank=True,null=True)
      react_iom_serial_no=models.CharField(max_length=255,default=None,blank=True,null=True)
      ir_iom_serial_no=models.CharField(max_length=255,default=None,blank=True,null=True)

      def __str__(self):
        return self.iom_date
      
      class Meta:
            db_table = 'iom_serialnos'

class IntimateNLDC(models.Model):
      intimate_date=models.DateField(default=None)
      amount_available=models.FloatField(default=None,blank=True,null=True)
      transfer_amount=models.FloatField(default=0,blank=True,null=True)
      is_transferred=models.BooleanField(default=None,blank=True,null=True)
      er=models.FloatField(default=None,blank=True,null=True)
      nr=models.FloatField(default=None,blank=True,null=True)
      wr=models.FloatField(default=None,blank=True,null=True)
      ner=models.FloatField(default=None,blank=True,null=True)
      psdf=models.FloatField(default=None,blank=True,null=True)
      is_used_indisbursement=models.BooleanField(default=False,blank=True,null=True)
      file_path=models.TextField(default=None,blank=True,null=True)
      
      def __str__(self):
        return self.intimate_date
      
      class Meta:
            db_table = 'intimate_nldc'
            unique_together=['intimate_date','amount_available']

class AccountCodeDetails(models.Model):
      acc_type=models.CharField(default=None)
      receivable_to_pool=models.CharField(default=None,blank=True,null=True)
      disbursement_from_pool=models.CharField(default=None,blank=True,null=True)
      
      def __str__(self):
        return self.acc_type
      
      class Meta:
            db_table = 'accountcode_details'

class NLDCPoolAmountSplit(models.Model):
      disburse_date=models.DateField(default=None)
      amount_for_dsm=models.FloatField(default=None,blank=True,null=True)
      amount_for_netas=models.FloatField(default=None,blank=True,null=True)
      amount_for_reac=models.FloatField(default=None,blank=True,null=True)
      is_user_checked=models.BooleanField(default=None) # if user not entered manually then collect full amount for disbursal

      def __str__(self):
        return self.disburse_date
      
      class Meta:
            db_table = 'nldcpool_splitamount'

class SignedIOMS(models.Model):
      iom_path=models.CharField(max_length=255,default=None)
      iom_date=models.DateField(default=None)
      acc_type=models.CharField(default=None,max_length=50)
      uploaded_date=models.DateField(default=timezone.now )

      def __str__(self):
            return self.iom_date
      
      class Meta:
            db_table = 'signed_ioms'