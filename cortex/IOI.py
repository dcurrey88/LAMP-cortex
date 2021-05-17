import pandas as pd
from cortex.raw.gps import gps
from cortex.raw.accelerometer import accelerometer

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
        self.time_constraint = None
        self.get_gps_df()
        self.get_acc_df()
        
        
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
        
    
    def set_temporal():
        pass