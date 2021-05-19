import pandas as pd
import numpy as np
from cortex.raw.gps import gps
from cortex.raw.accelerometer import accelerometer
from cortex.raw.survey import survey
import similaritymeasures as sm
import time
from fastdtw import fastdtw
from scipy.spatial.distance import euclidean


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
        self.baseline_trajectories = None
        
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
        #else:
            #df_list = [group[1] for group in df.groupby(df.index.dayofweek)]
        
    def get_baseline_trajectories(self):
        '''
        Get Baseline Trajectories
        '''
        self.baseline_trajectories = []
        for key in self.traj_dict.keys():
            start = time.time()
            traj_list = self.traj_dict[key]
            baseline = self.get_matrix(traj_list)
            self.baseline_trajectories.append(baseline)
            print(time.time() - start)
            

    def similarity_measure(self, df1, df2, frechet=True):
        '''
        Calculate similarity metric between two df's - Frechet for now (else FastDTW)
        '''
        # TODO add other similarity measures as options
        arr1 = df1[['latitude', 'longitude']].to_numpy()
        arr2 = df2[['latitude', 'longitude']].to_numpy()
        if frechet:
            return sm.frechet_dist(arr1, arr2)
        else:
            fastDTW_score, _ = fastdtw(arr1, arr2, dist=euclidean)
            return fastDTW_score

    def get_matrix(self, traj_list):
        n = len(traj_list)
        a = np.zeros(shape=(n,n))
        for i in range(n):
            for j in range(n):
                if i == j:
                    a[i][j] = np.inf
                else:
                    if a[i][j] == 0:
                        val = self.similarity_measure(traj_list[i], traj_list[j])
                        print(val)
                        a[i][j] = val
                        a[j][i] = val
                    else:
                        pass
        return a
        
    def set_temporal():
        pass