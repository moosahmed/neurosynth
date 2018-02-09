import glob
import os
import re
import sys

import pandas as pd
import numpy as np

# SET PATHS
# neuro_path = '/mnt/max/shared/projects/neurosynth/roi_selection/average_nonzero_HCP_neurosynth_networks_concat.csv'
# sub_path = '/mnt/max/shared/data/study/ADHD/HCP/processed/ADHD_NoFMNoT2/'
# out_path = '/mnt/max/shared/projects/neurosynth/network_csvs/average_nonzero_1.97_threshold/'
# z_threshold = 1.97
# timecourse_csv = 'HCP.subcortical.32k_fs_LR.csv'
# network_files = [
#     'amygdala_insula.csv',
#     'arousal.csv',
#     'attentional_control.csv',
#     'default_network.csv',
#     'dorsal_attention.csv',
#     'monetary_reward.csv',
#     'response_inhibition.csv',
#     'reward_anticipation.csv',
#     'selective_attention.csv',
#     'verbal_working.csv',
#     'working_memory.csv'
# ]

def interface(neuro_path,sub_path,out_path,z_threshold,timecourse_csv,network_files):
    ## Archived code due to change of use regions from 50% coverage metric to z_score metric
    # neuro_voxel = pd.read_csv(os.path.join(neuro_path, 'nonzero_HCP_neurosynth_networks_concat.csv'), header=None)
    # total_voxel = pd.read_csv(os.path.join(neuro_path, 'nonzero_HCP_10050-2_FNL_preproc_Atlas.csv'), header=None)
    # total_voxel = total_voxel.iloc[:, 0]
    # percentage_covered = neuro_voxel.div(total_voxel, axis=0)
    # use_regions = percentage_covered > 0.5
    ##

    # Read The neurosynth csv and fully covered csv; then compute which regions have a z-score more than 1.97
    # only use those regions
    neuro_voxel = pd.read_csv(neuro_path, header=None)
    use_regions = neuro_voxel > z_threshold

    # Create a list of subject IDs from the ADHD cohort
    sub_list = []
    for (dirpath, dirnames, filenames) in os.walk(sub_path):
        sub_list.extend(dirnames)
        break
    print sub_list

    # Loop Through each network's region selection using the use_regions variable
    for network, save_name in enumerate(network_files):
        print network
        # This part creates a dataframe with the regions only; the for loop will feed into this df.
        # Grabs the full path for all subjects controlling for multiple visit dates
        wild_path_0 = os.path.join(sub_path + sub_list[0], '*', '*', sub_list[0],
                                   'analyses_v2', 'timecourses', timecourse_csv)
        full_path_0 = glob.glob(wild_path_0)

        if not full_path_0:
            print >> sys.stderr, sub_list[0], "glob %s: target doesn't exist" % wild_path_0
            continue

        # reads in the parcellation timecourse
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

        # Loops through each subject/timepoint and feeds in the correlation values in to the dataframe created above
        for sub_id in sub_list:
            # Grabs the full path for all subjects controlling for multiple visit dates
            wild_path = os.path.join(sub_path + sub_id, '*', '*', sub_id,
                                     'analyses_v2', 'timecourses', timecourse_csv)
            full_path = glob.glob(wild_path)

            if not full_path_0:
                print >> sys.stderr, sub_id, "glob %s: target doesn't exist" % wild_path_0
                continue

            for path in full_path:
                # Extracting Visit date from path
                find = sub_id + '/(.+?)-SIEMENS'
                m = re.search(find, path)
                if m:
                    visit = m.group(1)
                subject = sub_id + '_' + visit

                # reads in the parcellation timecourse
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
        censored_regions = [361, 366, 370, 371, 379]
        for key in censored_regions:
            in_df = in_df[in_df.Region_1 != key]
            in_df = in_df[in_df.Region_2 != key]

        # Concatenating the region pairs into a single value
        reg_p = '[' + in_df['Region_1'].astype(str) + ',' + in_df['Region_2'].astype(str) + ']'
        in_df.drop(['Region_1', 'Region_2'], axis=1, inplace=True)
        in_df.insert(0, 'Region_pairs', reg_p)
        in_df['Region_pairs'].astype(str)

        # Saving it out subjects down rows; region pairs across columns
        in_df.T.to_csv(os.path.join(out_path, save_name), header=False)

def cli_interface():
    try:
        neuro_path, sub_path, out_path, z_threshold, timecourse_csv, network_files = sys.argv[1:]
    except:
        print("usage: {}  <neuro_path> <sub_path> <out_path> <z_threshold> <timecourse_csv> <network_files>".format(sys.argv[0]))
        sys.exit(1)
    interface(neuro_path, sub_path, out_path, z_threshold, timecourse_csv, network_files)

if __name__ == '__main__':
    cli_interface()