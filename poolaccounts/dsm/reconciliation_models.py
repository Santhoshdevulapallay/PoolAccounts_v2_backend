from django.db import models



class ClosingBalances(models.Model):
    Month_year=models.CharField(max_length=15,default=None)
    Fin_code=models.CharField(max_length=10,default=None)
    Acc_type = models.CharField(default=None)
    Closing_amount = models.FloatField(default=None , blank=True , null=True)

    def __str__(self):
        return self.Fin_code
      
    class Meta:
        db_table = 'closing_balances'
        unique_together=['Fin_code','Month_year','Acc_type']
