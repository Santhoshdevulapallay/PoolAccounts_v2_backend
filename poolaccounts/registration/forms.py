from django import forms
from .models import *



class NewRegistrationForm(forms.ModelForm):
      class Meta:
            model = Registration
            fields='__all__'
      def clean(self):
            cleaned_data = super().clean()
            fin_code = cleaned_data.get('fin_code')

            if Registration.objects.filter(fin_code=fin_code , end_date__isnull=True).exists():
                  raise forms.ValidationError('{fin_code} already exists')
            
class NewBankDetailsForm(forms.ModelForm):
      class Meta:
            model = BankDetails
            # fields=['bank_account','bank_name','ifsc_code','is_sbi','start_date','end_date','fin_code_fk']
            fields='__all__'

class NewLCDetailsForm(forms.ModelForm):
      class Meta:
            model = LCDetails
            # fields=['bank_account','bank_name','ifsc_code','is_sbi','start_date','end_date','fin_code_fk']
            fields='__all__'
