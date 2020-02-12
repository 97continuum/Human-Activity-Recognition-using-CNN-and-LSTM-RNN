import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from scipy import interpolate

import pickle # to serialise objects
from scipy import stats
import seaborn as sns
from sklearn import metrics
from sklearn.model_selection import train_test_split

sns.set(style='whitegrid', palette='muted', font_scale=1.5)
RANDOM_SEED = 42

dataset_train = pd.read_csv('final_training_set_8people.csv')
training_set = pd.DataFrame(dataset_train.iloc[:,:].values)
training_set.columns = ["User","Activity", "Timeframe", "X axis", "Y axis", "Z axis"]

X = training_set.iloc[:, 3]
X = X.astype(float)
X = (X*1000000).astype('int64')

Y = training_set.iloc[:, 4]
Y = Y.astype(float)
Y = (Y*1000000).astype('int64')

Z = training_set.iloc[:, 5]
Z = Z.astype(float)
Z = (Z*1000000).astype('int64')

Old_T = (training_set.iloc[:, 2]).astype(float)
Old_T = (Old_T * 1000000)
Old_T = Old_T.astype('int64')

New_T = np.arange(0, 12509996000, 50000)
New_T = New_T.astype('int64')

# find interpolation function
interpolate_function = interpolate.interp1d(Old_T, X, axis = 0, fill_value="extrapolate")
X_Final = interpolate_function((New_T))

interpolate_function = interpolate.interp1d(Old_T, Y, axis = 0, fill_value="extrapolate")
Y_Final = interpolate_function((New_T))

interpolate_function = interpolate.interp1d(Old_T, Z, axis = 0, fill_value="extrapolate")
Z_Final = interpolate_function((New_T))

#Combining data into one pandas dataframe
Dataset = pd.DataFrame()

Dataset['X_Final'] = X_Final
Dataset['Y_Final'] = Y_Final
Dataset['Z_Final'] = Z_Final

Dataset['New_Timeframe'] = New_T
Dataset = Dataset/1e6
Dataset = Dataset[['New_Timeframe', 'X_Final', 'Y_Final', 'Z_Final']]
Dataset['New_Activity'] = ""
#Dataset = Dataset.astype('int64')
Dataset = Dataset[['New_Activity', 'New_Timeframe', 'X_Final', 'Y_Final', 'Z_Final']]


#function to fill in new dataset with related activity
Dataset = Dataset.to_numpy()
training_set = training_set.to_numpy()

time = 0
temp = training_set[0][1]
var_to_assign = ""
last_row = 0
new_row = 0
for i in range(len(training_set)-1):
    if(training_set[i][1] == temp):
        continue
    
    if (training_set[i][1] != temp):
        var_to_assign = temp
        temp = training_set[i][1]
        time = training_set[i][2]
        
        a1 = [x for x in Dataset[:, 1] if x <= time]
        new_row = len(a1)
        
        Dataset[last_row:new_row+1, 0] = var_to_assign
        last_row = new_row
        continue


#converting both arrays back to Dataframes
Dataset = pd.DataFrame(Dataset)
Dataset.columns = ['New_Activity', 'New_Timeframe', 'X_Final', 'Y_Final', 'Z_Final']
    
training_set = pd.DataFrame(training_set)   
training_set.columns = ["User","Activity", "Timeframe", "X axis", "Y axis", "Z axis"]

#Filling empty Dataset values
#Checking to see which index values are empty
df_missing = pd.DataFrame()
df_missing = Dataset[Dataset.isnull().any(axis=1)]

#Filling all empty values with preceding values
Dataset['New_Activity'].fillna(method = 'ffill', inplace = True)


#Combining smaller classes into larger/main classes

Dataset = Dataset.to_numpy()

for i in range(0, len(Dataset)-1): 
    if Dataset[i][0] == "a_loadwalk" or Dataset[i][0] == "a_jump":
        Dataset[i][0] = "a_walk"
    if Dataset[i][0] == "p_squat" or Dataset[i][0] == "p_kneel" or Dataset[i][0] == "p_lie" or Dataset[i][0] == "t_lie_sit" or Dataset[i][0] == "t_sit_lie" or Dataset[i][0] == "t_sit_stand":
        Dataset[i][0] = "p_sit"
    if Dataset[i][0] == "p_bent" or Dataset[i][0] == "t_bend" or Dataset[i][0] == "t_kneel_stand" or Dataset[i][0] == "t_stand_kneel" or Dataset[i][0] == "t_stand_sit" or Dataset[i][0] == "t_straighten" or Dataset[i][0] == "t_turn":
        Dataset[i][0] = "p_stand"


Dataset = pd.DataFrame(Dataset)
Dataset.columns = ['New_Activity', 'New_Timeframe', 'X_Final', 'Y_Final', 'Z_Final']







#Feature Generation and Data Transformation
TIME_STEPS = 200
N_FEATURES = 3
STEP = 20

segments = []
labels = []

for i in range(0, len(Dataset) - TIME_STEPS, STEP): #To give the starting point of each batch
    xs = Dataset['X_Final'].values[i: i + TIME_STEPS]
    ys = Dataset['Y_Final'].values[i: i + TIME_STEPS]
    zs = Dataset['Z_Final'].values[i: i + TIME_STEPS]
    label = stats.mode(Dataset['New_Activity'][i: i + TIME_STEPS]) #this statement returns mode and count
    label = label[0][0] #to ge value of mode
    segments.append([xs, ys, zs])
    labels.append(label)
     
#reshaping our data
reshaped_segments = np.asarray(segments, dtype = np.float32).reshape(-1, TIME_STEPS, N_FEATURES)
#reshaped_segments.shape

#Using one hot encoding
l = pd.DataFrame(labels)
l_one_hot = pd.get_dummies(l)

labels_columns = l_one_hot.idxmax(axis = 1)

labels = np.asarray(pd.get_dummies(labels), dtype = np.float32) 

#labels.shape

X_train = reshaped_segments
y_train = labels

#Building the LSTM RNN Model
from keras.models import Sequential
from keras.layers import Dense
from keras.layers import LSTM
from keras.layers import Dropout

#Initialising the RNN
regressor = Sequential()

# Adding the first LSTM layer and some Dropout regularisation
regressor.add(LSTM(units = 100, return_sequences = True, input_shape = (X_train.shape[1], 3)))
regressor.add(Dropout(0.2))

# Adding a second LSTM layer and some Dropout regularisation
regressor.add(LSTM(units = 100, return_sequences = True))
regressor.add(Dropout(0.2))

# Adding a third LSTM layer and some Dropout regularisation
regressor.add(LSTM(units = 100, return_sequences = True))
regressor.add(Dropout(0.2))

# Adding a fourth LSTM layer and some Dropout regularisation
regressor.add(LSTM(units = 100))
regressor.add(Dropout(0.2))

# Adding the output layer
regressor.add(Dense(units = 5))

# Compiling the RNN
regressor.compile(optimizer = 'adam', loss = 'mean_squared_error')

# Fitting the RNN to the Training set
regressor.fit(X_train, y_train, epochs = 100, batch_size = 32)



#Importing Test DataSet
Test_set = pd.read_csv('final_test_set_2people.csv')
Test_set.drop(['Unnamed: 0'], axis = 1, inplace = True)





#combing smaller classes to bigger classes

Test_set = Test_set.to_numpy()
for i in range(0, len(Test_set)-1):
    if Test_set[i][1] == "a_loadwalk" or Test_set[i][1] == "a_jump":
        Test_set[i][1] = "a_walk"
    if Test_set[i][1] == "p_squat" or Test_set[i][1] == "p_kneel" or Test_set[i][1] == "p_lie" or Test_set[i][1] == "t_lie_sit" or Test_set[i][1] == "t_sit_lie" or Test_set[i][1] == "t_sit_stand":
        Test_set[i][1] = "p_sit"
    if Test_set[i][1] == "p_bent" or Test_set[i][1] == "t_bend" or Test_set[i][1] == "t_kneel_stand" or Test_set[i][1] == "t_stand_kneel" or Test_set[i][1] == "t_stand_sit" or Test_set[i][1] == "t_straighten" or Test_set[i][1] == "t_turn":
        Test_set[i][1] = "p_stand"


Test_set = pd.DataFrame(Test_set)
Test_set.columns = ["User","Activity", "Timeframe", "X axis", "Y axis", "Z axis"]




TEST_TIME_STEPS = 200
TEST_N_FEATURES = 3
TEST_STEP = 20

test_segments = []
test_labels = []

for i in range(0, len(Test_set) - TEST_TIME_STEPS, TEST_STEP): #To give the starting point of each batch
    t_xs = Test_set['X axis'].values[i: i + TEST_TIME_STEPS]
    t_ys = Test_set['Y axis'].values[i: i + TEST_TIME_STEPS]
    t_zs = Test_set['Z axis'].values[i: i + TEST_TIME_STEPS]
    test_label = stats.mode(Test_set['Activity'][i: i + TEST_TIME_STEPS]) #this statement returns mode and count
    test_label = test_label[0][0] #to ge value of mode
    test_segments.append([t_xs, t_ys, t_zs])
    test_labels.append(test_label)
    
#reshaping our data

test_reshaped_segments = np.asarray(test_segments, dtype = np.float32).reshape(-1, TEST_TIME_STEPS, TEST_N_FEATURES)
#reshaped_segments.shape

#Using one hot encoding
#test_labels = np.asarray(pd.get_dummies(test_labels), dtype = np.float32)

X_test = test_reshaped_segments
y_test = test_labels
test_df = pd.DataFrame(y_test)

y_pred = regressor.predict(X_test)
y_pred = (y_pred > 0.5)

y_pred = pd.DataFrame(y_pred)
y_pred.columns = l_one_hot.columns

#Converting y_pred from boolean to table
y_pred_list = y_pred.idxmax(axis = 1)
y_pred_list = pd.DataFrame(y_pred_list)
y_pred_list.columns = ["Activity"]
y_pred_list['Activity'] = y_pred_list['Activity'].str[2:]


y_test = pd.DataFrame(y_test)
y_test.columns = ["Activity"]



def accuracy(y_test,y_pred_list):
    tot = 0
    correct = 0
    y_test = y_test.to_numpy()
    y_pred_list = y_pred_list.to_numpy()
    for i in range(0, len(y_test)):
        if y_test[i][0] == y_pred_list[i][0]:
            correct += 1
            tot += 1
        else:
            tot += 1
    y_test = pd.DataFrame(y_test)
    y_test.columns = ["Activity"]
    y_pred_list = pd.DataFrame(y_pred_list)
    y_pred_list.columns = ["Activity"]
    answer = (correct/tot)*100
    print(round(answer, 2))
    
accuracy(y_test, y_pred_list)





