from django.db import models
from django.utils import timezone


# SCUC related models
class SCUCBaseModel(models.Model):
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
      Fully_disbursed=models.CharField(max_length=10,default=None,blank=True,null=True)    

      Effective_start_date=models.DateField(default=None,blank=True,null=True)
      Effective_end_date=models.DateField(default=None,blank=True,null=True)
      Legacy_dues=models.BooleanField(default=False)
      
      def __str__(self):
            return self.Fin_code
      
      class Meta:
            db_table = 'scuc_basemodel'
            unique_together=['Fin_year','Week_no','Entity']


class SCUCPayments(models.Model):
      Paid_date=models.DateField(default=None)
      Description=models.CharField(max_length=400,default=None,blank=True,null=True)
      Paid_amount=models.FloatField(blank=True)
      Other_info=models.TextField(default=None,blank=True,null=True)
      Bank_type=models.CharField(default=None,blank=True,null=True)
      paystatus_fk=models.ForeignKey(SCUCBaseModel,on_delete=models.SET_NULL,null=True)
      approved_date=models.DateTimeField(default=timezone.now )

      def __str__(self):
        return self.paystatus_fk
      class Meta:
            db_table = 'scuc_payments'

class SCUCReceivables(models.Model):
      Disbursed_amount=models.FloatField(blank=True,null=True)
      rcvstatus_fk=models.ForeignKey(SCUCBaseModel,on_delete=models.SET_NULL,null=True)
      iom_date=models.DateField(default=None,blank=True,null=True)
      disbursed_date=models.DateField(default=None,blank=True,null=True)
      neft_txnno=models.CharField(max_length=255,default=None,blank=True,null=True)
      def __str__(self):
        return self.rcvstatus_fk
      
      class Meta:
            db_table = 'scuc_receivables'