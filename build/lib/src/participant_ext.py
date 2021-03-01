import pandas as pd 
import numpy as np
import datetime
import os
import math
import LAMP
import itertools
from functools import reduce
from tzwhere import tzwhere
import pytz
from dateutil.tz import tzlocal



class ParticipantExt():
    """
    Create participant dataframe
    """
    def __init__(self, 
                 id, 
                 domains=None, 
                 age=None, 
                 race=None, 
                 sex=None, 
                 df_props={}):

        self.id = id
        self.domains = domains
        self.age = age
        self.race = race
        self.sex = sex

        self.df = self.create_df(**df_props)

        self.impute_status = False
        self.bin_status = False
        self.normalize_status = False	

    @property
    def id(self):
        return self._id

    @property
    def age(self):
        return self._age

    @property
    def race(self):
        return self._race

    @property
    def sex(self):
        return self._sex

    @id.setter
    def id(self, value):
        self._id = value

    @age.setter
    def age(self, value):
        self._age = value

    @race.setter
    def race(self, value):
        self._race = value

    @sex.setter
    def sex(self, value):
        self._sex = value

    def reset(self):
        """
        Resets the participant's df to be the original version
        """
        self.df = self.create_df()
        self.impute_status, self.bin_status, self.normalize_status = False, False, False

    def domain_check(self, domains):
        """
        If domains is passed in, just return it.
        Else, see if domains is set as object attribute
        """
        if domains is None:
            if not hasattr(self, 'domains'):
                raise AttributeError('Domains were not set for cohort and were not provided.')
            domains = self.domains
        return domains

    def sensor_results(self, participant=None):
        """
        Get dictionary of sensor data
        """

        def get_sensor_events(sensor_events, subj, origin, to=None):
            """
            Recursively get sensor events
            
            results: list containing all sensor event results up to that point
            """
            if to is None:results = sorted(LAMP.SensorEvent.all_by_participant(subj, origin=origin)['data'], key=lambda x: x['timestamp'])
            else: results = sorted(LAMP.SensorEvent.all_by_participant(subj, origin=origin, to=to)['data'], key=lambda x: x['timestamp'])
                
            sensor_events += results
            if len(results) < 1000: #done
                return sensor_events
    
            new_to = results[0]['timestamp']
            
            return get_sensor_events(sensor_events, subj, origin, to=new_to)

        lamp_sensors = ["lamp.accelerometer", "lamp.accelerometer.motion", #"lamp.analytics", 
                        "lamp.blood_pressure", "lamp.bluetooth", "lamp.calls", "lamp.distance",
                        "lamp.flights", "lamp.gps", "lamp.gps.contextual", "lamp.gyroscope",
                        "lamp.heart_rate", "lamp.height", "lamp.magnetometer", "lamp.respiratory_rate",
                        "lamp.screen_state","lamp.segment", "lamp.sleep", "lamp.sms", "lamp.steps",
                        "lamp.weight", "lamp.wifi"]

        if participant is None:
            participant = self.id

        participant_sensors = {}
        for sensor in lamp_sensors:
            s_results = sorted([{'UTC_timestamp':res['timestamp'], **res['data']} for res in get_sensor_events([], participant, origin=sensor)], key=lambda x: x['UTC_timestamp'])
            
            if len(s_results) > 0:
                participant_sensors[sensor] = pd.DataFrame.from_dict(s_results).drop_duplicates(subset='UTC_timestamp') #remove duplicates

        return participant_sensors



    def survey_results(self, participant=None, question_categories=None):
        """
        Get survey events for participant
        
        :param participant (str): the LAMP ID for participant. If not provided, then take participant id
        :param question_categories (dict): maps text in active event responses to a domain (str) and reverse_scoring parameter (bool)
        """

        if participant is None:
            participant = self.id

        participant_activities = LAMP.Activity.all_by_participant(participant)['data']
        participant_activities_surveys = [activity for activity in participant_activities if activity['spec'] == 'lamp.survey']
        participant_activities_surveys_ids = [survey['id'] for survey in participant_activities_surveys]        

        #NOTE: bug here, as if len(results) > 1000, not all results will be returned
        participant_results = [result for result in LAMP.ActivityEvent.all_by_participant(participant)['data'] if 'activity' in result and result['activity'] in participant_activities_surveys_ids and len(result['temporal_slices']) > 0]

        
        participant_surveys = {} #maps survey_type to occurence of scores 
        for result in participant_results:
            #Check if it's a survey event
            if result['activity'] not in participant_activities_surveys_ids or len(result['temporal_slices']) == 0: 
                continue
            
            activity = LAMP.Activity.view(result['activity'])['data'][0]
            result_settings = activity['settings']

            survey_time = result['timestamp']
            survey_result = {} #maps question domains to scores
            for event in result['temporal_slices']: #individual questions in a survey
                question = event['item']
                
                question_exists = False
                for i in range(len(result_settings)) : #match question info to question
                    if result_settings[i]['text'] == question: 
                        current_question_info=result_settings[i]
                        exists = True
                        break

                
                if not exists: #question text is different from the activity setting; skip
                    continue
                    
                #score based on question type:
                event_value = event.get('value') #safely get event['value'] to protect from missing keys
                
                if event_value == 'NULL': continue # invalid (TO-DO: change these events to ensure this is not being returned)
                
                elif current_question_info['type'] == 'likert' and event_value != None:
                    score = float(event_value)
                        
                elif current_question_info['type'] == 'boolean':
                    if event_value == 'no': score = 0.0 #no is healthy in standard scoring
                    elif event_value == 'yes' : score = 3.0 # yes is healthy in reverse scoring

                elif current_question_info['type'] == 'list' :
                    for option_index in range(len(current_question_info['options'])) :
                        if event_value == current_question_info['options'][option_index] :
                            score = option_index * 3 / (len(current_question_info['options'])-1)

                elif current_question_info['type'] == 'text':  #skip
                    continue
                
                else: continue #no valid score to be used
                    
                #add event to a category, either user-defined or default activity
                if question_categories:
                    if question not in question_categories: #See if there is an extra space in the string
                        if question[:-1] in question_categories:
                            question = question[:-1]
                        else:
                            continue

                    event_category = question_categories[question]['category']
                    #flip score if necessary
                    if question_categories[question]['reverse_scoring']: 
                        score = 3.0 - score

                    if event_category in survey_result: survey_result[event_category].append(score) 
                    else: survey_result[event_category] = [score]

                else:
                    if activity['name'] not in survey_result:
                        survey_result[activity['name']] = []
                    survey_result[activity['name']].append(score)
                    

            #add mean to each cat to master dictionary           
            for category in survey_result: 
                survey_result[category] = np.mean(survey_result[category])
                if category not in participant_surveys: 
                    participant_surveys[category] = [[survey_time, survey_result[category]]]
                else: 
                    participant_surveys[category].append([survey_time, survey_result[category]])

        #Sort surveys by time
        for activity_category in participant_surveys:
            participant_surveys[activity_category] = pd.DataFrame(data=sorted(participant_surveys[activity_category], key=lambda x: x[0]),
                                                                  columns=['UTC_timestamp', 'score'])
        return participant_surveys
        

    def create_df(self, days_cap=120, day_first=None, day_last=None, resolution=datetime.timedelta(days=1), start_monday=False, start_morning=True, time_centered=False, question_categories=None):
        """
        Create participant dataframe
        :param day_first (datetime.Date)
        """
        def collate_surveys(surveys, df, day_first, day_last):
            """
            Convert survey scores into dense representation ("df")
            
            :param surveys
            :param df
            :param day_first
            :param day_last
            """
            #Parse surveys
            for dom in surveys:
                if dom not in domains and domains is not None:
                    continue

                #Based on resolution, match each survey event to its closest date
                dates = [date for date in surveys[dom]['local_datetime'] if day_first <= date <= day_last] 
                #Choose closest date if "time centered"; else, choose preceding date
                if time_centered: rounded_dates = [df.loc[df.index[(date - df['Date']).abs().sort_values().index[0]], 'Date'] for date in dates]
                else: rounded_dates = [df.loc[df.index[(date - df['Date'])[(date - df['Date']) >= datetime.timedelta(0)].sort_values().index[0]], 'Date'] for date in dates]

                results = surveys[dom].loc[(day_first <= surveys[dom]['local_datetime']) & (surveys[dom]['local_datetime'] <= day_last), 'score']

                dom_results = pd.DataFrame({'Date':dates, 'Rounded Date':rounded_dates, 'Result':results})
                for date, date_df in dom_results.groupby('Rounded Date'):                    
                    df.loc[df['Date'] == date.to_pydatetime(), dom] = np.mean(date_df['Result']) 

            return df
        
        
        surveys = self.survey_results(question_categories=question_categories) #survey ActivityEvents
        sensors = self.sensor_results() # sensor SensorEvents
        
        results = {**sensors, **surveys} # **passive_features, **attachment_features}
        
        #Convert timestamps to appropriate local time; use GPS if it exists
        for dom in results:
            if 'lamp.gps' in results:
                if 'timezone' not in results['lamp.gps'].columns: #Generate timezone for every gps readings and convert timestamps
                    tz = tzwhere.tzwhere(forceTZ=True) #force timezone if ambigiuous
                    results['lamp.gps'].loc[:, 'timezone'] = results['lamp.gps'].apply(lambda x: tz.tzNameAt(x['latitude'], 
                                                                                                             x['longitude'], 
                                                                                                             forceTZ=True), 
                                                                                       axis=1)

                    gps_converted_datetimes = pd.Series([datetime.datetime.fromtimestamp(t/1000, tz=pytz.timezone(results['lamp.gps']['timezone'][idx])) for idx, t in results['lamp.gps']['UTC_timestamp'].iteritems()])
                    gps_converted_timestamps = gps_converted_datetimes.apply(lambda t: t.timestamp() * 1000)
                    
                    results['lamp.gps']['timezone'].to_csv('/home/ryan/TESTEST3.csv')
                    results['lamp.gps'].loc[:, 'local_timestamp'] = gps_converted_timestamps.values
                    #BUG HERE: local_datetime not being read as datetime object (even though they all are)
                    try:
                        results['lamp.gps'].loc[:, 'local_datetime'] = gps_converted_datetimes.dt.tz_localize(None).values
                    except:
                        results['lamp.gps'].loc[:, 'local_datetime'] = pd.Series([dt.replace(tzinfo=None) for dt in gps_converted_datetimes.values])
            
                if dom == 'lamp.gps': continue
                    
                matched_gps_readings = results[dom]['UTC_timestamp'].apply(lambda t: results['lamp.gps'].loc[(results['lamp.gps']['UTC_timestamp'] - t).idxmin, 'timezone'])
                converted_datetimes = pd.Series([datetime.datetime.fromtimestamp(t/1000, tz=pytz.timezone(matched_gps_readings[idx])) for idx, t in results[dom]['UTC_timestamp'].iteritems()])

            else:
                tz = pytz.timezone(datetime.datetime.now(tzlocal()).tzname()) #pytz.timezone('America/New_York')
                matched_gps_readings = pd.Series([tz] * len(results[dom]))
                converted_datetimes = results[dom]['UTC_timestamp'].apply(lambda t: datetime.datetime.fromtimestamp(t/1000, tz=tz))


            converted_timestamps = converted_datetimes.apply(lambda t: t.timestamp() * 1000)
            
            results[dom].loc[:, 'timezone'] = matched_gps_readings
            results[dom].loc[:, 'local_timestamp'] = converted_timestamps.values
            results[dom].loc[:, 'local_datetime'] = converted_datetimes.dt.tz_localize(None).values
  
        #passive_features = self.passive_feature_results(resolution=resolution) #beiewe.passive_features
        #attachment_features = self.attachment_results() #static attachment features  
        
        if len(results) == 0:
            return None

        #Find the first, last date
        concat_datetimes = pd.concat([results[dom] for dom in results])['local_datetime'].sort_values()
        if day_first is None: day_first = concat_datetimes.min()
        else: day_first = datetime.datetime.combine(day_first, datetime.time.min) #convert to datetime

        if day_last is None: day_last = concat_datetimes.max()
        else: day_last = datetime.datetime.combine(day_last, datetime.time.min) #convert to datetime

        #Clip days based on morning and weekday parameters
        if start_monday:
            if day_first.weekday() > 0: 
                day_first += datetime.timedelta(days = - day_first.weekday())

        if start_morning: 
            day_first, day_last = day_first.replace(hour=9, minute=0, second=0), day_last.replace(hour=9, minute=0, second=0)
            
        days_elapsed = (day_last - day_first).days 
        
        #Create based on resolution
        date_list = [day_first + (resolution * x) for x in range(0, math.ceil(min(days_elapsed, days_cap) * datetime.timedelta(days=1) / resolution))]

        #Create dateframe for the number of time units that have data; limited by days; cap at 'days_cap' if this number is large
        df = pd.DataFrame({'Date': date_list, 'id':self.id})

        #Add empty survey columns
        domains = [dom for dom in surveys]
        for dom in domains: 
            df[dom] = np.nan

        ### Featurize result events and add to df
        
        #Surveys
        surveyDf = collate_surveys(surveys, df, day_first, day_last)
        
        #Parse sensors and convert them into passive features

        #Single sensor features
        callTextDf = LAMP.analysis.call_text_features.all(results, date_list, resolution=resolution)
        accelDf = LAMP.analysis.accelerometer_features.all(results, date_list, resolution=resolution)
        #screenDf = LAMP.analysis.screen_features.all(sensors, df, resolution)
        #gpsDf = LAMP.analysis.gps_features.all(sensors, date_list, resolution=resolution)
        #Merge dfs
        df = reduce(lambda left, right: pd.merge(left, right, on=["Date"], how='left'), 
                    [surveyDf, accelDf, callTextDf, gpsDf]) #gpsDf, screenDf])

        #Trim columns if there are predetermined domains
        if self.domains is not None: 
            df = df.loc[:, ['id', 'Date'] + [d for d in self.domains if d in df.columns.values]]
            
        #Save data
        self.survey_events = surveys
        self.sensor_events = sensors
        self.result_events = results

        return df

 
    def impute(self, domains):
        """
        Get value for each column for each window
        """
        if self.impute_status:
            print('Dataframe already imputed.')
            return

        weighted_dict = [0.05, 0.20, 0.40, 1.5, 0.4, 0.20, 0.05]

        #Get indices of all middle bin values; add them to new df
        for dom in domains:
            if dom not in self.df:
                continue

            dom_values = []

            for ind in range(len(self.df.index)):

                #Get indices
                middle_weight_index = 3
                starting_index = max(ind -3, 0)
                ending_index = min(ind + 4, 90)

                #Get slice values
                subj_slice = self.df.iloc[starting_index:ending_index]

                #Remove na
                subj_slice_no_nan = subj_slice[dom].dropna()
                slice_indices = subj_slice_no_nan.index

                if len(slice_indices) == 0:
                    dom_values.append(np.nan)
                    continue

                #Match slice index with weight index
                weighted_dict_vals = [weighted_dict[middle_weight_index - (ind - slice_i)] for slice_i in slice_indices]

                #Find total in bin
                slice_val = sum(subj_slice_no_nan * [val / sum(weighted_dict_vals) for val in weighted_dict_vals])
                dom_values.append(slice_val)

            self.df[dom] = dom_values

        self.impute_status = True


    def bin(self, domains, window_size=3, shift=0):
        """
        Bin dataframe
        :param domains (list): the domains to bin 
        :window_size (int): the size of the bins (in days)
        :shift (int): the day of the week to start the binning on (Monday == 0)
        """

        #domains = self.domain_check(domains)
        domains = self.df.columns.drop(['Date', 'id'])
        
        #Shift until Monday
        df_copy = self.df.copy()
        if shift is not None:
            try:
                dow = df_copy.iloc[0]['Date'].weekday()
                if dow > 0 and len(df_copy) > dow:
                    df_copy = df_copy.shift(shift - dow)
            except:
                print(self.id, df_copy)
        df_copy['bin'] = np.floor(df_copy.index / window_size )
        bins = df_copy.groupby('bin')
        subj_bin_df = pd.DataFrame(columns=['Bin Start Date', 'Bin End Date'] + domains.values.tolist())
        for b in bins:
            bin_values = []
            #Add bin start/end dates
            
            start_date, end_date = b[1].iloc[0]['Date'], b[1].iloc[-1]['Date']
            bin_values.extend((start_date, end_date))
            for dom in domains:
                if dom in b[1].columns:
                    bin_dom_value = b[1][dom].mean()
                    bin_values.append(bin_dom_value)
                else:
                    bin_values.append(np.nan)

            #Add date range
            subj_bin_df.loc[b[0]] = bin_values    

        subj_bin_df['id'] = self.id
        
        self.bins = subj_bin_df
        
    def impute_bins(self, domains):
        """
        Try to impute bin objects
        """
        assert self.bins is not None
        
        for d in domains:
            for index, row in self.bins.iterrows():
                if 0 < index < len(self.bins.index) - 1:
                    index = int(index)
                    if pd.isnull(self.bins.iloc[index][d]) and not pd.isnull(self.bins.iloc[index-1][d]) and not pd.isnull(self.bins.iloc[index+1][d]):                        
                        self.bins.at[index,d] = np.mean([self.bins.iloc[index-1][d], self.bins.iloc[index+1][d]])


    def normalize(self, domains, domain_means={}, domain_vars={}):
        """
        Normalize columns values to 0 mean/ unit variance
        :param domain_means (dict): the mean for each column value
        :param domain_vars (dict): the variance for each column value
        If mean/var not provided, resort to in-sample normalization
        """
        if self.normalize_status: return
 
        domains = self.domain_check(domains)
        if domain_means == {} and domain_vars == {}:
            for dom in domains:
                if dom in self.df.columns:
                    domain_means[dom] = self.df[dom].mean()
                    domain_vars[dom] = self.df[dom].std()

        for dom in domains:
            if dom in self.df.columns and dom in domain_means and dom in domain_vars:
                self.df[dom] = (self.df[dom] - domain_means[dom]) / domain_vars[dom]

            self.normalize_status = True

    def create_transition_dict(self, level):
        """
        Create nested dictionary structure 
        :param level (int): the level dictionary structure. Must be >= 0
        """
        trans_dict = {}
        for comb in itertools.product(('out', 'in'), repeat=level):
            trans_dict[comb] = {comb2:0 for comb2 in itertools.product(('out', 'in'), repeat=level)}
        return trans_dict


    def assign_transition_dict(self, trans_dict, row, row2):
        """
        Increment transition dict
        """
        label1 = tuple(['in' if col < 1.0 else 'out' for col in row])
        label2 = tuple(['in' if col < 1.0 else 'out' for col in row2])
        trans_dict[label1][label2] += 1

    def get_transitions(self, domains=None, joint_size=1):
        """
        Count transition events for each col in subj_df
        """
        domains = self.domain_check(domains)
        all_trans_dict = {}
        for dom_group in itertools.combinations(domains, r=joint_size):

            #Create trans dictionary
            group_dict = self.create_transition_dict(level=joint_size)

            #Find bins with values for each group
            good_bins = self.bins[list(dom_group)].dropna()

            #Assign
            row_iterator = good_bins.iterrows()
            try:
                last_i, last = next(row_iterator)
            except StopIteration:
                continue
            for index, row in row_iterator:
                if int(index) - int(last_i) <= 3:
                    self.assign_transition_dict(group_dict, last, row)
                last_i, last = index, row

            all_trans_dict[dom_group] = group_dict

        return all_trans_dict

    def domain_bouts(self, domains=None):
        """
        """
        def parse_bout_list(bout_list, state, low_bouts, high_bouts):
            """
            Helper function to parse bout list at end of bout
            """
            if len(bout_list) == 1: bout_list.append(bout_list[-1] + 3) #edge case where last domain event is only one in its bout

            if state: low_bouts.append(float(bout_list[-1]) - float(bout_list[0]))
            else: high_bouts.append(float(bout_list[-1]) - float(bout_list[0]))
            return low_bouts, high_bouts

        domains = self.domain_check(domains)
        bout_dict = {}
        for dom in domains:
            if dom not in self.df:
                continue

            bout_list = [] #temporary list that contains times of current bout
            subj_dom = self.df.loc[self.df[dom].notnull(), dom]
            row_iterator = subj_dom.iteritems()
            try:
                last_day, last_val = next(row_iterator)
                bout_list.append(last_day)
                if last_val < 1.0: last_state = True #set this back on first val
                else: last_state = False
            except StopIteration:
                continue

            bout_dict[dom] = {}
            low_bouts, high_bouts = [], [] #duration of all in-range bouts
            low_bouts_end, high_bouts_end = 0, 0 #counter the keep track of # of ended bout things
            for day, val in row_iterator:
                if val < 1.0: state = True
                else: state = False

                if last_state == state and day - last_day <= 6: #continue bout
                    bout_list.append(day)

                else: #discontinue bout
                    if day - last_day > 8: 
                        bout_list.append(last_day + 3) #If adjacent rows are day outside threshold, discontinue bout;cap last bout at 3 days past last activity	
                        if last_state: low_bouts_end += 1
                        else: high_bouts_end += 1
                    else: bout_list.append(day) #then normal switch

                    low_bouts, high_bouts = parse_bout_list(bout_list, last_state, low_bouts, high_bouts)
                    bout_list = [day]

                last_day, last_val = day, val
                last_state = state

            low_bouts, high_bouts = parse_bout_list(bout_list, last_state, low_bouts, high_bouts) #parse last bout
            bout_dict[dom]['low'], bout_dict[dom]['high'] = [float(b) for b in low_bouts], [float(b) for b in high_bouts]
            bout_dict[dom]['low ends'], bout_dict[dom]['high ends'] = low_bouts_end, high_bouts_end

        return bout_dict