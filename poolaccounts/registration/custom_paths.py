import datetime,zipfile,os


def get_current_financial_year():
      # later uncomment it
      today = datetime.date.today()
      if today.month >= 4:
            return str(today.year) + "-" + str(today.year + 1)[2:]
      else:
            return str(today.year - 1) + "-" + str(today.year)[2:]

      # return '2023-24'


week_proof_path=r"\\fileserver\mo\ui"
current_financial_year=get_current_financial_year()

# regions=['Southern Region to Western Region', 'Western Region to Southern Region', 'Southern Region to Eastern Region', 'Eastern Region to Southern Region ']

# drive_folder_path='D:\\PoolAccounts\\Backend\\poolaccounts\\Files\\Logs\\'
drive_folder_path='D:\\PoolAccountsV2\\Poolaccounts_backend\\poolaccounts\\Files\\Logs\\'


