import pandas as pd
from datetime import timedelta,datetime
import pytz
import zipfile , os
from pathlib import Path


def add530hrstoDateString(datestr):
      date_obj = pd.to_datetime(datestr)
      date_obj += timedelta(hours=5, minutes=30)
      return date_obj

def sub530hrstoDateString(datestr):
      date_obj = pd.to_datetime(datestr)
      date_obj -= timedelta(hours=5, minutes=30)
      return date_obj



def combine_date_time(act_date,time_df):
      dt = datetime.combine(act_date, time_df)
      tz_utc = pytz.timezone('UTC')
      dt_utc = tz_utc.localize(dt)
      date_string = dt_utc.strftime('%Y-%m-%dT%H:%M:%SZ') 
      return date_string


def combine_date_time_forfictcompute(act_date,time_df):
      dt = datetime.combine(act_date, time_df)
      tz_utc = pytz.timezone('UTC')
      dt_utc = tz_utc.localize(dt)
      date_string = dt_utc.strftime('%Y-%m-%dT%H:%M:%SZ') 

      date_string=sub530hrstoDateString(date_string)

      return date_string

def nextTimeblkno(start_time,next_no):
      increment = timedelta(minutes=15)
      return start_time + (next_no * increment)

def previous_week():
      today = datetime.now()
      # Calculate the start and end date of the current week
      start_date = today - timedelta(days=today.weekday()+7)
      end_date = start_date + timedelta(days=6)

      # Format the start and end date to display only the date
      start_date = start_date.date()
      end_date = end_date.date()

      return start_date, end_date


def previous_week_withinput(given_date):
      given_datetime = datetime.strptime(given_date, "%d%m%y")
      start_date =( given_datetime - timedelta(days=7) ).date()
      end_date = ( given_datetime - timedelta(days=1)) .date()

      return start_date,end_date


def create_zip_file(file_path, dir_path ,filename):
      # here dir_path = 'D:\\PoolAccounts\\Backend\\poolaccounts'
      zip_filename=filename
      zip_file = zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED)
      for file in file_path:
            full_path = os.path.join(dir_path, file)
            file_name = Path(full_path).name
            zip_file.write(full_path, file_name)
      zip_file.close()       
      return zip_filename