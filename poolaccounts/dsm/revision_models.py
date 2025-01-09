from django.db import models
from django.utils import timezone

# Net AS related models
class RevisionBaseModel(models.Model):
      Letter_date=models.DateField(default=None)
      Acc_type=models.CharField(max_length=50,default=None)
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

      def __str__(self):
            return self.Letter_date
      
      class Meta:
            db_table = 'revision_basemodel'
            unique_together=['Acc_type','Letter_date','Entity']


class RevisionPayments(models.Model):
      Paid_date=models.DateField(default=None)
      Description=models.CharField(max_length=400,default=None,blank=True,null=True)
      Paid_amount=models.FloatField(blank=True)
      Other_info=models.TextField(default=None,blank=True,null=True)
      Bank_type=models.CharField(default=None,blank=True,null=True)
      paystatus_fk=models.ForeignKey(RevisionBaseModel,on_delete=models.SET_NULL,null=True)
      approved_date=models.DateTimeField(default=timezone.now )
      Is_disbursed=models.BooleanField(default=False,blank=True,null=True)

      def __str__(self):
        return self.paystatus_fk
      
      class Meta:
            db_table = 'revision_payments'

class RevisionReceivables(models.Model):
      Disbursed_amount=models.FloatField(blank=True,null=True)
      rcvstatus_fk=models.ForeignKey(RevisionBaseModel,on_delete=models.SET_NULL,null=True)
      
      iom_date=models.DateField(default=None,blank=True,null=True)
      disbursed_date=models.DateField(default=None,blank=True,null=True)
      neft_txnno=models.CharField(max_length=255,default=None,blank=True,null=True)
      def __str__(self):
        return self.rcvstatus_fk
      
      class Meta:
            db_table = 'revision_receivables'
            unique_together=['Disbursed_amount','rcvstatus_fk','disbursed_date']