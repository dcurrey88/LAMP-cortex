import pandas as pd
from cortex.raw.gps import gps
from cortex.raw.accelerometer import accelerometer

class IOI:

    def __init__(self, participant_id, start, end):
        '''
        Constructor
        Inputs:
          participant_id (str)
          start (int)
          end (int)
          
        '''

        self.id = participant_id
        self.start = start 
        self.end = end
        self.gps_df = None
        self.acc_df = None
        self.get_gps_df
        self.get_acc_df
        self.time_constraint

    def get_gps_df(self):
        '''    
        Gets df of raw GPS data
        '''
        self.gps_df = gps(id=self.id, start=self.start, end=self.end)
        
    def get_acc_df(self):
        '''    
        Gets df of raw accelerometer data
        '''
        self.acc_df = accelerometer(id=self.id, start=self.start, end=self.end)
        
    
    def set_temporal():
        pass