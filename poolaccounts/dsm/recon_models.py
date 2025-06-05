from django.db import models
from django.utils import timezone

class ReconUploadStatus(models.Model):
    Acc_type = models.CharField(max_length=15,default=None)
    Fin_year = models.CharField(max_length=15,blank=True)
    Quarter = models.CharField(max_length=5 ,blank=True)
    Fin_code = models.CharField(max_length=10 ,blank=True)
    Upload_status = models.CharField(max_length=5 , default=None) # N - notified , A - approved R - Rejected
    Uploaded_time=models.DateTimeField(default=timezone.now())
    File_path = models.TextField(default=None)
    Admin_remarks = models.CharField(max_length= 255 , default=None , blank=True , null=True)
    Admin_uploaded_time = models.DateTimeField(default=timezone.now())
    def __str__(self):
        return self.Fin_code
    
    class Meta:
        db_table = 'recon_uploadstatus'
        unique_together=['Fin_year','Quarter','Fin_code','Upload_status']

class ReconNotified(models.Model):
    Acc_type = models.CharField(max_length=15,default=None)
    Fin_year = models.CharField(max_length=15,blank=True)
    Quarter = models.CharField(max_length=5 ,blank=True)
    Notified_date = models.DateField(default = timezone.now().date() )

    class Meta:
        db_table = 'recon_notified'
        unique_together=['Acc_type','Fin_year','Quarter']

class ReconLastQuarterBalance(models.Model):
    Acc_type = models.CharField(max_length=15,default=None)
    Fin_year = models.CharField(max_length=15,blank=True)
    Quarter = models.CharField(max_length=5 ,blank=True)
    as_on_date = models.DateField(default=None,blank=True,null=True)
    Amount = models.FloatField(default = 0 )
    Fin_code = models.CharField(max_length=10 ,blank=True)
    class Meta:
        db_table = 'recon_lastquarterbalance'
        unique_together=['Acc_type','Fin_year','Quarter']