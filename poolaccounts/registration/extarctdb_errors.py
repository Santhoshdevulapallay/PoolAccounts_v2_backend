
from .custom_paths import drive_folder_path
from datetime import datetime
import os

def write_to_file(data):
      record_time=datetime.now().strftime('%d-%m-%Y %H:%M:%S')
      today_file_name=datetime.now().strftime('%d-%m-%Y')
      if not os.path.exists(drive_folder_path):
            os.makedirs(drive_folder_path)

      log_file_path = os.path.join(drive_folder_path, f'log_file_{today_file_name}.txt')
      with open(log_file_path, 'a') as file:
            file.write(record_time + ' -- ' + str(data) + '\n')

def extractdb_errormsg(error):
      try:
            error_list=str(error).split("\nDETAIL: ")
            if len(error_list)>0:
                  detail = str(error).split("\nDETAIL: ")[1]
            else:
                  detail=error_list[0]
            write_to_file(detail)
            return detail
      except Exception as e:
            write_to_file(error)
            return str(e)