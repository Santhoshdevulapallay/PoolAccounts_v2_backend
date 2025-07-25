import pandas as pd
from .common import *
from .models import *
from dsm.common import _create_columns , srpc_file_names
from django.db.models import Q
from .engine_create import *
import pdb

def updateFinCodeFCName(temp_dict,fin_code_fees_charges_qry):
  # assign fin_code , if no fin_code then empty
  try:
    temp_dict['Fin_code']=fin_code_fees_charges_qry[0][0]
    temp_dict['Entity'] = fin_code_fees_charges_qry[0][1]
  except Exception as e:
    extractdb_errormsg(e)
    temp_dict['Fin_code']=''
  
  return temp_dict
def readDSMFile(path,acc_type,fin_year,week_no):
  try:
    # reading DSM File , srpc_file_names (is a global variable declared in common.py)
    df=pd.read_csv(path+'\\Zip_Data\\'+srpc_file_names[acc_type])
    # Find the index of rows containing 'Entity'
    entity_indices = df.index[df['Entity'] == 'Entity'].tolist()
    # Split the DataFrame based on the 'Entity' rows
    dfs_list = []
    start_idx = 0
    for idx in entity_indices:
          dfs_list.append(pd.DataFrame(df.iloc[start_idx:idx]))
          start_idx = idx 
    # this appends last entity table may be infirm power
    dfs_list.append(pd.DataFrame(df.iloc[start_idx:] ) )
    count=0
    infirm_table=[]
    infirm_table_df=pd.DataFrame([])
    final_states_gen_list=pd.DataFrame([])
    del dfs_list[2] # removing pumped storage
    for in_df in dfs_list:
      # drop NaN columns specially for InterRegional df
      in_df = in_df.dropna(axis=1,how='all') # Specify 'how' parameter to 'all' to drop columns containing all NaN values
      #*****Now this is for state and generators
      # States Part
      
      if count == 0:
        in_df.columns =removeSpaceDf(in_df)
        # Drop rows with NaN values in 'PayableToPool/ReceviableFromPool' column
        # names changes from Entityt:E, UnderdrawlCharges(Rs):U ,OverdrawlCharges(Rs):O
        try:
          in_df.columns=['E','U','O','Po','F','P']
        except : 
          in_df.columns=['E','F','P']
        
        in_df = in_df.dropna(subset=['P'])
        in_df=in_df[['E','F','P']]
        # rename the columns and append to dataframe
        in_df.rename(columns={'F':'DevFinal' ,'P':'PayRcv'},inplace=True)
      elif count == 1:
        # CGS Part
        # changing the header 
        in_df.columns = in_df.iloc[0] 
        # skipping the first row , because it contains header only that we moved up
        in_df=in_df.iloc[1: ]
        in_df.columns = removeSpaceDf(in_df)
        # names changes from Entityt:E, UnderdrawlCharges(Rs):U ,OverdrawlCharges(Rs):O
        in_df.columns=['E','O','U','C','F','P']
        # Drop rows with NaN values in 'PayableToPool/ReceviableFromPool' column
        in_df = in_df.dropna(subset=['P'])
        in_df=in_df[['E','F','P']]
        # rename the columns and append to dataframe
        in_df.rename(columns={'F':'DevFinal' ,'P':'PayRcv'},inplace=True)
      elif count == 2:
      
        # Interregional Part
        # changing the header 
        in_df.columns = in_df.iloc[0] 
        # skipping the first row , because it contains header only that we moved up
        in_df=in_df.iloc[1: ]
        in_df.columns = removeSpaceDf(in_df)
        # names changes from Entityt:E, UnderdrawlCharges(Rs):U ,OverdrawlCharges(Rs):O
        try:
          in_df.columns=['E','U','O','D','F','P']
        except:
          in_df.columns=['E','F','P']
        # Drop rows with NaN values in 'Payable/Receviable' column
        in_df = in_df.dropna(subset=['P'])
        in_df=in_df[['E','F','P']]
        
        # rename the columns and append to dataframe
        in_df.rename(columns={'F':'DevFinal' ,'P':'PayRcv'},inplace=True)
        # remove space from df rows
        in_df['E'] = in_df['E'].str.replace(' ', '')
        # calculate the WRSR and ERSR amounts then store in it temporary table
        wrsr_str_tofloat=float( in_df[in_df['E'] == 'WesternRegiontoSouthernRegion' ]['DevFinal'].iloc[0] .replace(',','') )
        srwr_str_tofloat=float(in_df[in_df['E'] == 'SouthernRegiontoWesternRegion' ]['DevFinal'].iloc[0] .replace(',',''))

        WRSR = wrsr_str_tofloat - srwr_str_tofloat

        ersr_str_tofloat=float( in_df[in_df['E'] == 'EasternRegiontoSouthernRegion' ]['DevFinal'].iloc[0] .replace(',','') )
        srer_str_tofloat=float(in_df[in_df['E'] == 'SouthernRegiontoEasternRegion' ]['DevFinal'].iloc[0] .replace(',',''))

        ERSR = ersr_str_tofloat - srer_str_tofloat
        # check if already exists then skip
        
        temp_ir_qry=TemporaryInterRegional.objects.filter(Fin_year=fin_year,Week_no=week_no)
        
        if temp_ir_qry.count() < 1:
          TemporaryInterRegional.objects.filter(Fin_year=fin_year,
                Week_no=week_no).delete()
          # now store in the temporary_interregional table
          TemporaryInterRegional(
                Fin_year=fin_year,
                Week_no=week_no,WRSR=WRSR,
                ERSR=ERSR,WR_Revision_no=0,ER_Revision_no=0 ).save()
          
      elif count == 3:
        # Infirm drawl power
        in_df.columns = in_df.iloc[0] 
        # skipping the first row , because it contains header only that we moved up
        in_df=in_df.iloc[1: ]
        in_df.columns = removeSpaceDf(in_df)
        # names changed Entity:E ,DeviationEnergy:D , FinalCharges(Rs):F ..
        in_df.columns = ['E', 'D', 'F', 'P']
        # Drop rows with NaN values in 'Payable/Receviable' column
        in_df = in_df.dropna(subset=['P'])
        in_df=in_df[['E','F','P']]
        # rename the columns and append to dataframe
        in_df.rename(columns={'F':'DevFinal' ,'P':'PayRcv'},inplace=True)
        in_df['DevFinal']=in_df['DevFinal'].apply(lambda x:x.replace(',',''))
        # dont push to database if DevFinal contains 0 , **simply drop it
        in_df['DevFinal'] = pd.to_numeric(in_df['DevFinal'], errors='coerce')
        # Drop rows where 'DevFinal' column contains 0
        in_df = in_df[in_df['DevFinal'] != 0]
        # replace values also 
        in_df['PayRcv'] = in_df['PayRcv'].replace('Payable to Pool', 'Payable')
        in_df['PayRcv'] = in_df['PayRcv'].replace('Receivable from Pool', 'Receivable')
        
        # assign infirm drawl entities to infirm_table_df for temporarily
        infirm_table_df=in_df.copy()
        infirm_table_df=infirm_table_df.fillna(0)
      else:
        pass

      if count!=2 and count <=3: # skip interregional part
        if count!= 3:  #count ==3 is infirm drawl
          # dont add infirm drawl to main_df has to dealt separately
          final_states_gen_list=pd.concat([final_states_gen_list ,in_df]) 
      count+=1
    
    
    # now do the mapping of each states and generator , if not mapped send to user for manual mapping
    # get all users 
    all_users=Registration.objects.filter(Q(end_date__isnull=True)|Q(end_date__gte=timezone.now()))
    # get already mapped entities
    mapped_entities_qry=TemporaryMatched.objects.filter(Acc_type=acc_type,Fin_year=fin_year,Week_no=week_no)
    not_mapped_entities=[]
    mapped_entities=[] 
    # now rename columns to original names
    final_states_gen_list.rename(columns={'E':'Entity'},inplace=True)
    infirm_table_df.rename(columns={'E':'Entity'},inplace=True)
    final_states_gen_list=final_states_gen_list.fillna(0)

    for _ , row in final_states_gen_list.iterrows():
      check_ent_exists = all_users.filter( Q(fees_charges_name=row['Entity']) | Q(dsm_name=row['Entity']) | Q(sras_name=row['Entity']) | Q(tras_name=row['Entity']) | Q(react_name=row['Entity']))

      if  check_ent_exists.count() :
        # map the corresponding fin_code also
        fin_code_fees_charges_qry=list(check_ent_exists.values_list('fin_code','fees_charges_name'))
        temp_dict=row.to_dict()
        # assign fin_code , if no fin_code then empty
        temp_dict=updateFinCodeFCName(temp_dict,fin_code_fees_charges_qry)
        mapped_entities.append(temp_dict)

      elif mapped_entities_qry.filter(Entity=row['Entity']).count():
        # not found initially but mapped by user later
        pass
      else:
        not_mapped_entities.append(row.to_dict())

    mapped_df=pd.DataFrame(mapped_entities)
    
    # add three more columns like acc_type , fin_year and week_no
    # create blank columns with length of dataframe
    mapped_df = _create_columns(mapped_df, ['Acc_type', 'Fin_year', 'Week_no'])
    mapped_df['Acc_type'] =acc_type
    mapped_df['Fin_year'] =fin_year
    mapped_df['Week_no'] =week_no
    # default revision 0
    mapped_df['Revision_no'] = 0
    # Define the desired column order
    desired_order = ['Acc_type', 'Fin_year', 'Week_no','Entity','Fin_code','DevFinal','PayRcv','Revision_no']
    # Reorder columns using reindex
    mapped_df = mapped_df.reindex(columns=desired_order)
    
    #delete existing records (if user reuploads the file again)
    for entity in mapped_df['Entity'].unique():
      TemporaryMatched.objects.filter(Acc_type=acc_type,Fin_year=fin_year,Week_no=week_no , Entity=entity).delete()

    if not mapped_df.empty:
      with engine.connect() as connection:
        mapped_df.to_sql('temporary_matched', connection, if_exists='append',index=False)
      
    # now return the not matched entities to user
    for _ , in_row in infirm_table_df.iterrows():
      if mapped_entities_qry.filter(Entity=in_row['Entity']).count() <1:
            # no record found so send for user mapping
            infirm_table.append(in_row.to_dict())
      else:pass
    
    # here True means no erros occured
    return not_mapped_entities,infirm_table,True
  
  except Exception as err:
    extractdb_errormsg(err)
    return str(err),[],False


def readSRASFile(path,acc_type,fin_year,week_no):
  try:
    # reading DSM File , srpc_file_names (is a global variable declared in common.py)
    df=pd.read_csv(path+'\\Zip_Data\\'+srpc_file_names[acc_type])
    # Find the rows where 'Total' is in any of the row's values
    total_rows = df[df.apply(lambda row: 'Total' in row.values, axis=1)]
    # Check if total_rows is not empty before accessing the index
    if not total_rows.empty:
        total_index = total_rows.index[0]
        # Slice the DataFrame up to the row containing 'Total'
        sras_df = df.iloc[:total_index]
    else:
        sras_df=df.copy()
    sras_df.columns = removeSpaceDf(sras_df)
    mapping = {'Payable by SRAS Provider': 'Payable', 'Receivable to SRAS Provider': 'Receivable'}
    # Replace values in the rows using the dictionary
    final_df=sras_df.copy()
    try:
      final_df.columns=['SNo', 'S', 'SRAS-Up(MWHr)(A)', 'SRAS-Down(MWHr)(B)',
        'NetEnergy(MWh)(C)=(A)-(B)', 'EnergyCharges/Compensationcharges(Rs)(D)',
        'ActualPerformance(%)', 'IncentiveRate(paise/kWh)', 'Incentive(Rs)(E)',
        'T','P']
    except:
      final_df.columns = ['S' ,'T' ,'P']
    # Remove trailing spaces from the 'P' column
    final_df['P'] = final_df['P'].str.strip()
    # rename the columns
    final_df.rename(columns={'S':'Entity','T':'DevFinal','P':'PayRcv'},inplace=True)
    
    final_df.iloc[:] = final_df.iloc[:].replace(mapping)

    # convert to numeric 
    final_df['DevFinal']=final_df['DevFinal'].apply(lambda x: x.replace(',',''))
    # convert to numeric 
    final_df['DevFinal'] = pd.to_numeric(final_df['DevFinal'] , errors='coerce')
    # ignore if contains 0 values
    final_df = final_df[final_df['DevFinal'] != 0]
    final_df=final_df[['Entity','DevFinal','PayRcv']]
    # Replace '\r' and '\n' with spaces
    final_df['Entity'] = final_df['Entity'].apply(lambda y: y.replace('\r', '').replace('\n', ' '))
    # get all users 
    all_users=Registration.objects.filter(end_date__isnull=True)
    not_mapped_entities=[]
    mapped_entities=[]
    # get already mapped entities
    mapped_entities_qry=TemporaryMatched.objects.filter(Acc_type=acc_type,Fin_year=fin_year,Week_no=week_no)
    
    for _,row in final_df.iterrows():
      check_ent_exists=checkEntityExists(all_users,row['Entity'])
    
      if check_ent_exists.count() :

        # map the corresponding fin_code also
        fin_code_fees_charges_qry=list(check_ent_exists.values_list('fin_code','fees_charges_name'))
        temp_dict=row.to_dict()
        # assign fin_code , if no fin_code then empty
        # assign fin_code , if no fin_code then empty
        temp_dict=updateFinCodeFCName(temp_dict,fin_code_fees_charges_qry)

        mapped_entities.append(temp_dict)

      elif mapped_entities_qry.filter(Entity=row['Entity']).count():
        # not found initially but mapped by user later
        pass
      else:
        not_mapped_entities.append(row.to_dict())

    mapped_df=pd.DataFrame(mapped_entities)
    # add three more columns like acc_type , fin_year and week_no
    # create blank columns with length of dataframe
    mapped_df = _create_columns(mapped_df, ['Acc_type', 'Fin_year', 'Week_no'])
    mapped_df['Acc_type'] =acc_type
    mapped_df['Fin_year'] =fin_year
    mapped_df['Week_no'] =week_no
    # default revision 0
    mapped_df['Revision_no'] = 0
    # Define the desired column order
    desired_order = ['Acc_type', 'Fin_year', 'Week_no','Entity','Fin_code','DevFinal','PayRcv','Revision_no']
    # Reorder columns using reindex
    mapped_df = mapped_df.reindex(columns=desired_order)
    #delete existing records (if user reuploads the file again)
    for entity in mapped_df['Entity'].unique():
      TemporaryMatched.objects.filter(Acc_type=acc_type,Fin_year=fin_year,Week_no=week_no ,Entity=entity).delete()
    
    if not mapped_df.empty:
      with engine.connect() as connection:
        mapped_df.to_sql('temporary_matched', connection, if_exists='append',index=False)
    return not_mapped_entities,True
  except Exception as e:
    extractdb_errormsg(e)
    return str(e),False
  
def readTRASFile(path,acc_type,fin_year,week_no):
  try:
    # reading DSM File , srpc_file_names (is a global variable declared in common.py)
    df=pd.read_csv(path+'\\Zip_Data\\'+srpc_file_names[acc_type])
    # Find the rows where 'Total' is in any of the row's values
    total_rows = df[df.apply(lambda row: 'Total' in row.values, axis=1)]
    # Check if total_rows is not empty before accessing the index
    if not total_rows.empty:
        total_index = total_rows.index[0]
        # Slice the DataFrame up to the row containing 'Total'
        tras_df = df.iloc[:total_index]
    else:
        tras_df=df.copy()
    tras_df.columns = removeSpaceDf(tras_df)
    mapping = {'Payable by TRAS Provider': 'Payable', 'Receivable to TRAS Provider': 'Receivable'}
    # Replace values in the rows using the dictionary
    final_df=tras_df.copy()
    try:
      final_df.columns=['S.No', 'T',
        'EnergyscheduledunderShortfall/EmergencyTRAS-Up(MWh)(A)',
        'Totalcharges/Compensationchargesforshortfall/EmergencyTRAS-Up(Rs)(B)',
        'EnergyscheduledunderShortfall/EmergencyTRAS-Down(MWh)(C)',
        'Totalcharges/Compensationchargesforshortfall/EmergencyTRAS-DowntobepaidbacktoPool(Rs)(D)',
        'N','P' ]
    except:
      final_df.columns = ['T' ,'N' ,'P']
    # rename the columns
    # Remove trailing spaces from the 'P' column
    final_df['P'] = final_df['P'].str.strip()
    final_df.rename(columns={'T':'Entity','N':'DevFinal','P':'PayRcv'},inplace=True)
    
    final_df.iloc[:] = final_df.iloc[:].replace(mapping)

    # drop rows that contains values as 0
    # convert to numeric 
    final_df['DevFinal']=final_df['DevFinal'].apply(lambda x: x.replace(',',''))
    # convert to numeric 
    final_df['DevFinal'] = pd.to_numeric(final_df['DevFinal'] , errors='coerce')
    # ignore if contains 0 values
    final_df = final_df[final_df['DevFinal'] != 0]
    final_df=final_df[['Entity','DevFinal','PayRcv']]
    # Replace '\r' and '\n' with spaces
    final_df['Entity'] = final_df['Entity'].apply(lambda y: y.replace('\r', '').replace('\n', ' '))
    # get all users 
    all_users=Registration.objects.filter(end_date__isnull=True)
    not_mapped_entities=[]
    mapped_entities=[]
    # get already mapped entities
    mapped_entities_qry=TemporaryMatched.objects.filter(Acc_type=acc_type,Fin_year=fin_year,Week_no=week_no)
    
    for _,row in final_df.iterrows():
      check_ent_exists=checkEntityExists(all_users,row['Entity'])
    
      if check_ent_exists.count() :
        # map the corresponding fin_code also
        fin_code_fees_charges_qry=list(check_ent_exists.values_list('fin_code','fees_charges_name'))
        temp_dict=row.to_dict()
        # assign fin_code , if no fin_code then empty
        temp_dict=updateFinCodeFCName(temp_dict,fin_code_fees_charges_qry)

        mapped_entities.append(temp_dict)
      elif mapped_entities_qry.filter(Entity=row['Entity']).count():
        # not found initially but mapped by user later
        pass
      else:
        not_mapped_entities.append(row.to_dict())

    mapped_df=pd.DataFrame(mapped_entities)
    # add three more columns like acc_type , fin_year and week_no
    # create blank columns with length of dataframe
    mapped_df = _create_columns(mapped_df, ['Acc_type', 'Fin_year', 'Week_no'])
    mapped_df['Acc_type'] =acc_type
    mapped_df['Fin_year'] =fin_year
    mapped_df['Week_no'] =week_no
    # default revision 0
    mapped_df['Revision_no'] = 0
    # Define the desired column order
    desired_order = ['Acc_type', 'Fin_year', 'Week_no','Entity','Fin_code','DevFinal','PayRcv','Revision_no']
    # Reorder columns using reindex
    mapped_df = mapped_df.reindex(columns=desired_order)
    #delete existing records (if user reuploads the file again)
    for entity in mapped_df['Entity'].unique():
      TemporaryMatched.objects.filter(Acc_type=acc_type,Fin_year=fin_year,Week_no=week_no ,Entity=entity).delete()
    
    if not mapped_df.empty:
      with engine.connect() as connection:
        mapped_df.to_sql('temporary_matched', connection, if_exists='append',index=False)
    return not_mapped_entities,True
  except Exception as e:
    extractdb_errormsg(e)
    return str(e),False
  
def readSCUCFile(path,acc_type,fin_year,week_no):
  try:
    # reading DSM File , srpc_file_names (is a global variable declared in common.py)
    df=pd.read_csv(path+'\\Zip_Data\\'+srpc_file_names[acc_type])
    # Find the rows where 'Total' is in any of the row's values
    total_rows = df[df.apply(lambda row: 'Total' in row.values, axis=1)]
    # Check if total_rows is not empty before accessing the index
    if not total_rows.empty:
        total_index = total_rows.index[0]
        # Slice the DataFrame up to the row containing 'Total'
        scuc_df = df.iloc[:total_index]
    else:
        scuc_df=df.copy()
    scuc_df.columns = removeSpaceDf(scuc_df)
    mapping = {'Receivable by Pool Account': 'Payable', 'Payable from Pool Account': 'Receivable'}
    # Replace values in the rows using the dictionary
    final_df=scuc_df.copy()
    try:
      final_df.columns=['S.No', 'S',
        'EnergyscheduledunderShortfall/EmergencyTRAS-Up(MWh)(A)',
        'Totalcharges/Compensationchargesforshortfall/EmergencyTRAS-Up(Rs)(B)',
        'EnergyscheduledunderShortfall/EmergencyTRAS-Down(MWh)(C)',
        'Totalcharges/Compensationchargesforshortfall/EmergencyTRAS-DowntobepaidbacktoPool(Rs)(D)',
        'N','P' ]
    except:
      final_df.columns = ['S' ,'N' ,'P']
    # Remove trailing spaces from the 'P' column
    final_df['P'] = final_df['P'].str.strip()
    # rename the columns
    final_df.rename(columns={'S':'Entity','N':'DevFinal','P':'PayRcv'},inplace=True)
    final_df.iloc[:] = final_df.iloc[:].replace(mapping)
    # drop rows that contains values as 0
    # convert to numeric 
    final_df['DevFinal']=final_df['DevFinal'].apply(lambda x: x.replace(',',''))
    # convert to numeric 
    final_df['DevFinal'] = pd.to_numeric(final_df['DevFinal'] , errors='coerce')
    # ignore if contains 0 values
    final_df = final_df[final_df['DevFinal'] != 0]
    final_df=final_df[['Entity','DevFinal','PayRcv']]
    # Replace '\r' and '\n' with spaces
    final_df['Entity'] = final_df['Entity'].apply(lambda y: y.replace('\r', '').replace('\n', ' '))
    # get all users 
    all_users=Registration.objects.filter(end_date__isnull=True)
    not_mapped_entities=[]
    mapped_entities=[]
    # get already mapped entities
    mapped_entities_qry=TemporaryMatched.objects.filter(Acc_type=acc_type,Fin_year=fin_year,Week_no=week_no)
    
    for _,row in final_df.iterrows():
      check_ent_exists=checkEntityExists(all_users,row['Entity'])
    
      if check_ent_exists.count() :
        # map the corresponding fin_code also
        fin_code_fees_charges_qry=list(check_ent_exists.values_list('fin_code','fees_charges_name'))
        temp_dict=row.to_dict()
        # assign fin_code , if no fin_code then empty
        temp_dict=updateFinCodeFCName(temp_dict,fin_code_fees_charges_qry)

        mapped_entities.append(temp_dict)
      elif mapped_entities_qry.filter(Entity=row['Entity']).count():
        # not found initially but mapped by user later
        pass
      else:
        not_mapped_entities.append(row.to_dict())

    mapped_df=pd.DataFrame(mapped_entities)
    # add three more columns like acc_type , fin_year and week_no
    # create blank columns with length of dataframe
    mapped_df = _create_columns(mapped_df, ['Acc_type', 'Fin_year', 'Week_no'])
    mapped_df['Acc_type'] =acc_type
    mapped_df['Fin_year'] =fin_year
    mapped_df['Week_no'] =week_no
    # default revision 0
    mapped_df['Revision_no'] = 0
    # Define the desired column order
    desired_order = ['Acc_type', 'Fin_year', 'Week_no','Entity','Fin_code','DevFinal','PayRcv','Revision_no']
    # Reorder columns using reindex
    mapped_df = mapped_df.reindex(columns=desired_order)
    #delete existing records (if user reuploads the file again)
    for entity in mapped_df['Entity'].unique():
      TemporaryMatched.objects.filter(Acc_type=acc_type,Fin_year=fin_year,Week_no=week_no ,Entity=entity).delete()
    
    if not mapped_df.empty:
      with engine.connect() as connection:
        mapped_df.to_sql('temporary_matched', connection, if_exists='append',index=False)
    return not_mapped_entities,True
  except Exception as e:
    extractdb_errormsg(e)
    return str(e),False
  
def readCONGFile(path,acc_type,fin_year,week_no):
  try:
    # reading Congestion File , srpc_file_names (is a global variable declared in common.py)
    df=pd.read_csv(path+'\\Zip_Data\\'+srpc_file_names[acc_type])
    # Find the rows where 'Total' is in any of the row's values
    total_rows = df[df.apply(lambda row: 'Total' in row.values, axis=1)]
    # Check if total_rows is not empty before accessing the index
    if not total_rows.empty:
        total_index = total_rows.index[0]
        # Slice the DataFrame up to the row containing 'Total'
        cong_df = df.iloc[:total_index]
    else:
        cong_df=df.copy()
    cong_df.columns = removeSpaceDf(cong_df)
    mapping = {'Receivable from Pool': 'Receivable', 'Payable to Pool': 'Payable'}
    # Replace values in the rows using the dictionary
    final_df=cong_df.copy()
    try:
      final_df = final_df.loc[:, ~final_df.columns.str.contains('^Unnamed')]
      final_df.columns=['S.No', 'Entity','TotalDeviation','N','P' ]
    except:
      final_df.columns = ['Entity' ,'N' ,'P']
    
    # Remove trailing spaces from the 'P' column
    final_df['P'] = final_df['P'].str.strip()
    # rename the columns
    final_df.rename(columns={'N':'DevFinal','P':'PayRcv'},inplace=True)
    final_df.iloc[:] = final_df.iloc[:].replace(mapping)
    # drop rows that contains values as 0
    # convert to numeric 
    final_df['DevFinal']=final_df['DevFinal'].apply(lambda x: x.replace(',','') if type(x) == type('str') else x )
    # convert to numeric 
    final_df['DevFinal'] = pd.to_numeric(final_df['DevFinal'] , errors='coerce')
    # ignore if contains 0 values
    final_df = final_df[final_df['DevFinal'] != 0]
    final_df=final_df[['Entity','DevFinal','PayRcv']]
    # Replace '\r' and '\n' with spaces
    final_df['Entity'] = final_df['Entity'].apply(lambda y: y.replace('\r', '').replace('\n', ' '))
    # get all users 
    all_users=Registration.objects.filter(Q(end_date__isnull=True)|Q(end_date__gte=datetime.today()))
    not_mapped_entities=[]
    mapped_entities=[]
    # get already mapped entities
    mapped_entities_qry=TemporaryMatched.objects.filter(Acc_type=acc_type,Fin_year=fin_year,Week_no=week_no)
    
    for _,row in final_df.iterrows():
      check_ent_exists=checkEntityExists(all_users,row['Entity'])
    
      if check_ent_exists.count() :
        # map the corresponding fin_code also
        fin_code_fees_charges_qry=list(check_ent_exists.values_list('fin_code','fees_charges_name'))
        temp_dict=row.to_dict()
        # assign fin_code , if no fin_code then empty
        temp_dict=updateFinCodeFCName(temp_dict,fin_code_fees_charges_qry)

        mapped_entities.append(temp_dict)
      elif mapped_entities_qry.filter(Entity=row['Entity']).count():
        # not found initially but mapped by user later
        pass
      else:
        not_mapped_entities.append(row.to_dict())

    mapped_df=pd.DataFrame(mapped_entities)
    # add three more columns like acc_type , fin_year and week_no
    # create blank columns with length of dataframe
    mapped_df = _create_columns(mapped_df, ['Acc_type', 'Fin_year', 'Week_no'])
    mapped_df['Acc_type'] =acc_type
    mapped_df['Fin_year'] =fin_year
    mapped_df['Week_no'] =week_no
    # default revision 0
    mapped_df['Revision_no'] = 0
    # Define the desired column order
    desired_order = ['Acc_type', 'Fin_year', 'Week_no','Entity','Fin_code','DevFinal','PayRcv','Revision_no']
    # Reorder columns using reindex
    mapped_df = mapped_df.reindex(columns=desired_order)
    #delete existing records (if user reuploads the file again)
    for entity in mapped_df['Entity'].unique():
      TemporaryMatched.objects.filter(Acc_type=acc_type,Fin_year=fin_year,Week_no=week_no ,Entity=entity).delete()
    
    if not mapped_df.empty:
      with engine.connect() as connection:
        mapped_df.to_sql('temporary_matched', connection, if_exists='append',index=False)
    return not_mapped_entities,True
  except Exception as e:
    extractdb_errormsg(e)
    return str(e),False
  

def readMBASFile(path,acc_type,fin_year,week_no):
  try:
    # reading DSM File , srpc_file_names (is a global variable declared in common.py)
    df=pd.read_csv(path+'\\Zip_Data\\'+srpc_file_names[acc_type])
    # Find the rows where 'Total' is in any of the row's values
    total_rows = df[df.apply(lambda row: 'Total' in row.values, axis=1)]
    # Check if total_rows is not empty before accessing the index
    if not total_rows.empty:
        total_index = total_rows.index[0]
        # Slice the DataFrame up to the row containing 'Total'
        mbas_df = df.iloc[:total_index]
    else:
        mbas_df=df.copy()
    mbas_df.columns = removeSpaceDf(mbas_df)
    # Replace values in the rows using the dictionary
    final_df=mbas_df.copy()
    try:
      final_df.columns=['S.No', 'T', 'DAMTRAS-UpCleared(MWHr)(A)',
        'DAMTRAS-UpEnergyScheduled(MWHr)(B)', 'DAMTRASUpEnergyCharges(Rs.)(C)',
        'DAMTRASUpCommitmentCharges(Rs.)(D)', 'RTMTRAS-UpCleared(MWHr)(E)',
        'RTMTRAS-UpEnergyScheduled(MWHr)(F)', 'RTMTRASUpEnergyCharges(Rs.)(G)',
        'RTMTRASUpCommitmentCharges(Rs.)(H)',
        'TotalCharges/compensationchargeforTRASUp(Rs)(I)=(C)+(D)+(G)+(H)',
        'DAMTRAS-DownEnergyScheduled(MWHr)(J)',
        'DAMTRAS-DownChargestobepaidbacktopool(Rs)(K)',
        'RTMTRAS-DownEnergyScheduled(MWHr)(L)',
        'RTMTRAS-DownChargestobepaidbacktopool(Rs)(M)',
        'N','P']
    except:
      final_df.columns = ['T' ,'N' ,'P']
    # Remove trailing spaces from the 'P' column
    final_df['P'] = final_df['P'].str.strip()
    mapping = {'Receivable to Pool from TRAS Provider': 'Payable', 'Payable from Pool to TRAS Provider': 'Receivable'}
    final_df.iloc[:] = final_df.iloc[:].replace(mapping)
    # rename the columns
    final_df.rename(columns={'T':'Entity','N':'DevFinal','P':'PayRcv'},inplace=True)
    # drop rows that contains values as 0
    # convert to numeric 
    try :
      final_df['DevFinal']=final_df['DevFinal'].apply(lambda x: x.replace(',',''))
    except :
      final_df['DevFinal']=final_df['DevFinal']
    
    # convert to numeric 
    final_df['DevFinal'] = pd.to_numeric(final_df['DevFinal'] , errors='coerce')
    # ignore if contains 0 values
    final_df = final_df[final_df['DevFinal'] != 0]

    final_df=final_df[['Entity','DevFinal','PayRcv']]
    # Replace '\r' and '\n' with spaces
    final_df['Entity'] = final_df['Entity'].apply(lambda y: y.replace('\r', '').replace('\n', ' '))
    # get all users 
    all_users=Registration.objects.filter(end_date__isnull=True)
    not_mapped_entities=[]
    mapped_entities=[]
    # get already mapped entities
    mapped_entities_qry=TemporaryMatched.objects.filter(Acc_type=acc_type,Fin_year=fin_year,Week_no=week_no)
    
    for _,row in final_df.iterrows():
      check_ent_exists=checkEntityExists(all_users,row['Entity'])
    
      if check_ent_exists.count() :
        # map the corresponding fin_code also
        fin_code_fees_charges_qry=list(check_ent_exists.values_list('fin_code','fees_charges_name'))
        temp_dict=row.to_dict()
        # assign fin_code , if no fin_code then empty
        temp_dict=updateFinCodeFCName(temp_dict,fin_code_fees_charges_qry)

        mapped_entities.append(temp_dict)
      elif mapped_entities_qry.filter(Entity=row['Entity']).count():
        # not found initially but mapped by user later
        pass
      else:
        not_mapped_entities.append(row.to_dict())

    mapped_df=pd.DataFrame(mapped_entities)
    # add three more columns like acc_type , fin_year and week_no
    # create blank columns with length of dataframe
    mapped_df = _create_columns(mapped_df, ['Acc_type', 'Fin_year', 'Week_no'])
    mapped_df['Acc_type'] =acc_type
    mapped_df['Fin_year'] =fin_year
    mapped_df['Week_no'] =week_no
    # default revision 0
    mapped_df['Revision_no'] = 0
    # Define the desired column order
    desired_order = ['Acc_type', 'Fin_year', 'Week_no','Entity','Fin_code','DevFinal','PayRcv','Revision_no']
    # Reorder columns using reindex
    mapped_df = mapped_df.reindex(columns=desired_order)
    #delete existing records (if user reuploads the file again)
    for entity in mapped_df['Entity'].unique():
      TemporaryMatched.objects.filter(Acc_type=acc_type,Fin_year=fin_year,Week_no=week_no ,Entity=entity).delete()
    
    if not mapped_df.empty:
      with engine.connect() as connection:
        mapped_df.to_sql('temporary_matched', connection, if_exists='append',index=False)
    return not_mapped_entities,True
  except Exception as e:
    extractdb_errormsg(e)
    return str(e),False
  
def readREACFile(path,acc_type,fin_year,week_no):
  try:
      # reading DSM File , srpc_file_names (is a global variable declared in common.py)
      df=pd.read_csv(path+'\\Zip_Data\\'+srpc_file_names[acc_type])
      df.columns = removeSpaceDf(df)
      try:
        df.columns=['Entity', 'MVAR_H', 'MVAR_L', 'NETMVAR', 'A','P']
      except:
        df.columns=['Entity', 'A','P']

      reac_df = df.dropna(subset=['P'])
      mapping = {'Receivable From Pool': 'Receivable', 'Payable To Pool': 'Payable'}
      
      # Replace values in the rows using the dictionary
      final_df=reac_df.copy()
      # Remove trailing spaces from the 'P' column
      final_df['P'] = final_df['P'].str.strip()
      # rename the columns
      final_df.rename(columns={'P':'PayRcv' ,'A':'DevFinal'},inplace=True)
      
      final_df.iloc[:] = final_df.iloc[:].replace(mapping)
      # drop rows that contains values as 0
      # convert to numeric 
      final_df['DevFinal']=final_df['DevFinal'].apply(lambda x: x.replace(',',''))
      # convert to numeric 
      final_df['DevFinal'] = pd.to_numeric(final_df['DevFinal'] , errors='coerce')
      # ignore if contains 0 values
      final_df = final_df[final_df['DevFinal'] != 0]

      final_df=final_df[['Entity','DevFinal','PayRcv']]
      # Replace '\r' and '\n' with spaces
      final_df['Entity'] = final_df['Entity'].apply(lambda y: y.replace('\r', '').replace('\n', ' '))
      # remove trailing spaces from the string
      final_df['Entity'] = final_df['Entity'].str.strip()

      # get all users 
      all_users=Registration.objects.filter(end_date__isnull=True)
      not_mapped_entities=[]
      mapped_entities=[]
      # get already mapped entities
      mapped_entities_qry=TemporaryMatched.objects.filter(Acc_type=acc_type,Fin_year=fin_year,Week_no=week_no)
      
      for _,row in final_df.iterrows():
        check_ent_exists=checkEntityExists(all_users,row['Entity'])
        if check_ent_exists.count() :
          # map the corresponding fin_code also
          fin_code_fees_charges_qry=list(check_ent_exists.values_list('fin_code','fees_charges_name'))
          temp_dict=row.to_dict()
          # assign fin_code , if no fin_code then empty
          temp_dict=updateFinCodeFCName(temp_dict,fin_code_fees_charges_qry)

          mapped_entities.append(temp_dict)
        elif mapped_entities_qry.filter(Entity=row['Entity']).count():
          # not found initially but mapped by user later
          pass
        else:
          not_mapped_entities.append(row.to_dict())

      mapped_df=pd.DataFrame(mapped_entities)
      # add three more columns like acc_type , fin_year and week_no
      # create blank columns with length of dataframe
      mapped_df = _create_columns(mapped_df, ['Acc_type', 'Fin_year', 'Week_no'])
      mapped_df['Acc_type'] =acc_type
      mapped_df['Fin_year'] =fin_year
      mapped_df['Week_no'] =week_no
      # default revision 0
      mapped_df['Revision_no'] = 0
      # Define the desired column order
      desired_order = ['Acc_type', 'Fin_year', 'Week_no','Entity','Fin_code','DevFinal','PayRcv','Revision_no']
      # Reorder columns using reindex
      mapped_df = mapped_df.reindex(columns=desired_order)
      
      #delete existing records (if user reuploads the file again)
      for entity in mapped_df['Entity'].unique():
        TemporaryMatched.objects.filter(Acc_type=acc_type,Fin_year=fin_year,Week_no=week_no ,Entity=entity).delete()
      
      if not mapped_df.empty:
        with engine.connect() as connection:
          mapped_df.to_sql('temporary_matched', connection, if_exists='append',index=False)
      
      
      return not_mapped_entities,True
  except Exception as e:
    extractdb_errormsg(e)
    return str(e),False
