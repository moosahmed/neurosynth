import os
import pandas as pd
import numpy as np
import glob
import re

# SET PATHS
neuro_path = '/mnt/max/shared/projects/neurosynth/roi_selection/'
sub_path = '/mnt/max/shared/data/study/ADHD/HCP/processed/ADHD_NoFMNoT2/'
out_path = '/mnt/max/shared/projects/neurosynth/network_csvs/average_nonzero_1.97_threshold/'

# Read The neurosynth csv and fully covered csv; then compute which regions have more than 50% voxels covered
# only use those regions

neuro_voxel = pd.read_csv(os.path.join(neuro_path, 'average_nonzero_HCP_neurosynth_networks_concat.csv'), header=None)
# neuro_voxel = pd.read_csv(os.path.join(neuro_path, 'nonzero_HCP_neurosynth_networks_concat.csv'), header=None)
# total_voxel = pd.read_csv(os.path.join(neuro_path, 'nonzero_HCP_10050-2_FNL_preproc_Atlas.csv'), header=None)

# total_voxel = total_voxel.iloc[:, 0]
# percentage_covered = neuro_voxel.div(total_voxel, axis=0)
# use_regions = percentage_covered > 0.5
use_regions = neuro_voxel > 1.97

# Create a list of subject IDs from the ADHD cohort

sub_list =[]
for (dirpath, dirnames, filenames) in os.walk(sub_path):
    sub_list.extend(dirnames)
    break
print sub_list
# trim_list = sub_list[:3]

# Loop Through each network's region selection using the use_regions variable

# network_list = range(1)
network_list = range(11)
for network in network_list:
    print network
    # This part creates a dataframe with the regions only; the for loop will feed into this df.

    # Grabs the full path for all subjects controlling for multiple visit dates
    wild_path_0 = sub_path + sub_list[0] + '/*/HCP_release_20161027/' + sub_list[0] + \
                  '/analyses_v2/timecourses/HCP.subcortical.32k_fs_LR.csv'
    full_path_0 = glob.glob(wild_path_0)
    # print full_path_0

    # reads in the HCP timecourse
    timecourse = pd.read_csv(full_path_0[0], header=None)
    timecourse = timecourse.T

    # Trimming regions in the timecourse file to only include the regions specified in use_regions for every network
    trimmed_timecourse = timecourse.loc[use_regions.iloc[:, network], :]

    # Computes Correlation matrix for the remaining regions
    corr_matrix = trimmed_timecourse.T.corr()

    # Taking the upper-triangle of the dataframe and vectorizing it into a new data frame
    utri = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(np.bool))

    in_df = utri.stack().reset_index()
    in_df.columns = ['Region_1', 'Region_2', 'sub_id']
    # Creating Dataframe with only the selected region pairs per network; loop below will feed into this
    in_df = in_df.drop('sub_id', axis=1)
    # print in_df

    # Loops through each subject/timepoint and feeds in the correlation values in to the dataframe created above

    for sub_id in sub_list:
        # Grabs the full path for all subjects controling for multiple visit dates
        wild_path = sub_path + sub_id + '/*/HCP_release_20161027/' + sub_id + '/analyses_v2/timecourses/HCP.subcortical.32k_fs_LR.csv'
        full_path = glob.glob(wild_path)
        #print full_path
        for path in full_path:
            # Extracting Visit date from path
            find = sub_id + '/(.+?)-SIEMENS'
            m = re.search(find, path)
            if m:
                visit = m.group(1)
            subject = sub_id + '_' + visit

            # reads in the HCP timecourse
            timecourse = pd.read_csv(path, header=None)
            timecourse = timecourse.T

            # Trimming regions in the timecourse file to only include the regions specified in use_regions for every
            # network
            trimmed_timecourse = timecourse.loc[use_regions.iloc[:, network], :]

            # Computes Correlation matrix for the remaining regions
            corr_matrix = trimmed_timecourse.T.corr()

            # Taking the upper-triangle of the dataframe and vectorizing it into a new data frame
            utri = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(np.bool))

            sub_df = utri.stack().reset_index()
            sub_df.columns = ['Region_1', 'Region_2', subject]
            # Merging each subjects connectivity values into the df created in the previous part
            in_df = pd.merge(in_df, sub_df, 'inner', on=['Region_1', 'Region_2'])

    # This Part preps the df to be saved

    in_df['Region_1'] += 1  # Adding one to region names to account for 0-indexing
    in_df['Region_2'] += 1  # Adding one to region names to account for 0-indexing
    # Deleting Cerebellum_left and right and Diencephalon_ventral_left and right and brain stem
    in_df = in_df[in_df.Region_1 != 361]
    in_df = in_df[in_df.Region_1 != 366]
    in_df = in_df[in_df.Region_1 != 370]
    in_df = in_df[in_df.Region_1 != 371]
    in_df = in_df[in_df.Region_1 != 379]
    in_df = in_df[in_df.Region_2 != 361]
    in_df = in_df[in_df.Region_2 != 366]
    in_df = in_df[in_df.Region_2 != 370]
    in_df = in_df[in_df.Region_2 != 371]
    in_df = in_df[in_df.Region_2 != 379]
    # Concatenating the region pairs into a single value
    in_df['Region_pairs'] = '[' + in_df['Region_1'].astype(str) + ',' + in_df['Region_2'].astype(str) + ']'
    reg_p = in_df['Region_pairs']
    in_df.drop(['Region_1', 'Region_2', 'Region_pairs'], axis=1, inplace=True)
    in_df.insert(0, 'Region_pairs', reg_p)
    in_df['Region_pairs'].astype(str)

    # print in_df

    # Naming the networks and saving it out subjects down rows; region pairs across columns
    if network == 0:
        save_name = 'amygdala_insula.csv'
    elif network == 1:
        save_name = 'arousal.csv'
    elif network == 2:
        save_name = 'attentional_control.csv'
    elif network == 3:
        save_name = 'default_network.csv'
    elif network == 4:
        save_name = 'dorsal_attention.csv'
    elif network == 5:
        save_name = 'monetary_reward.csv'
    elif network == 6:
        save_name = 'response_inhibition.csv'
    elif network == 7:
        save_name = 'reward_anticipation.csv'
    elif network == 8:
        save_name = 'selective_attention.csv'
    elif network == 9:
        save_name = 'verbal_working.csv'
    else:
        save_name = 'working_memory.csv'
    print save_name
    in_df.T.to_csv(os.path.join(out_path, save_name), header=False)
    print in_df.T
