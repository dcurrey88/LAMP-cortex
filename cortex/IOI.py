import pandas as pd
from cortex.raw.gps import gps
from cortex.raw.accelerometer import accelerometer
from cortex.raw.survey import survey

class IOI:

    def __init__(self, id, start, end):
        '''
        Constructor
        Inputs:
          participant_id (str)
          start (int)
          end (int)
        '''

        self.id = id
        self.start = start
        self.end = end        
        self.gps_df = None
        self.acc_df = None
        self.survey_df = None
        self.time_constraint = None
        self.get_gps_df()
        self.get_acc_df()
        self.get_survey_df()
        self.get_trajectories()
        
        
    def get_gps_df(self):
        '''    
        Gets df of raw GPS data
        '''
        self.gps_df = pd.DataFrame.from_dict(list(reversed(gps(id=self.id, 
                                                         start=self.start, 
                                                         end=self.end)
                                              ['data'])))
        if self.gps_df.empty:
            print('No GPS data')
        else:
            self.gps_df['timestamp'] = pd.to_datetime(self.gps_df['timestamp'], unit='ms')
        
    def get_acc_df(self):
        '''    
        Gets df of raw accelerometer data
        '''
        self.acc_df = pd.DataFrame.from_dict(list(reversed(accelerometer(id=self.id, 
                                                         start=self.start, 
                                                         end=self.end)
                                              ['data'])))
        if self.acc_df.empty:
            print('No Accelerometer data')
        else:
            self.acc_df['timestamp'] = pd.to_datetime(self.acc_df['timestamp'], unit='ms')
    
    def get_survey_df(self):
        '''    
        Gets df of raw survey data
        '''
        self.survey_df = pd.DataFrame.from_dict(list(reversed(survey(id=self.id, 
                                                         start=self.start, 
                                                         end=self.end)
                                              ['data'])))
        if self.survey_df.empty:
            print('No Survey data')
        else:
            self.survey_df['timestamp'] = pd.to_datetime(self.survey_df['timestamp'], unit='ms')
        
    def get_df(id, start, end, sensor, to_datetime=True):
        '''
        Auxiliary 
        Returns a Pandas DataFrame of waw Cortex sensor data

                Parameters:
                        id (str): id of participant
                        start (int): timestamp in epoch time
                        end (int): timestamp in epoch time
                        sensor (str): type of sensor  
                        to_datetime (bool): default converts 'timestamp' column from epoch to datetime 
                Returns:
                        df (Pandas DataFrame): DataFrame containing sensor-specific data
                Example: get_df(id='A123', start=0, end=1618074315000, sensor='gps')
        '''
        get_sensor =  getattr(cortex.raw, sensor)
        get_sensor = getattr(get_sensor, sensor)
        df = pd.DataFrame.from_dict(list(reversed(get_sensor(id=id, 
                                                             start=start, 
                                                             end=end)
                                                  ['data'])))
        if df.empty:
            print('No '+ sensor +' data')
            return None

        else:
            if to_datetime:
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

        return df

    
    def get_trajectories(self, sensor='gps', dayofweek=True):
        '''
        Get all the trajectories based on some time interval
        '''
        if dayofweek:
            df = self.gps_df.copy()
            df.index = df['timestamp']
            d = {}
            df_list = [group[1] for group in df.groupby(df.index.dayofweek)]
            for i in range(len(df_list)):
                d[df_list[i].index[0].dayofweek] = [group[1] for group in df_list[i].groupby(df_list[i].index.date)]
            self.traj_dict = d
        
    def get_baseline_trajectory(self):
        '''
        Get Baseline Trajectory 
        '''
        return baseline
            
            
    def set_temporal():
        pass