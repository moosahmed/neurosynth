import glob
import os
import re
import sys

import pandas as pd
import numpy as np

# SET PATHS
neuro_path = '/mnt/max/shared/projects/neurosynth/roi_selection/average_nonzero_HCP_neurosynth_networks_concat.csv'
sub_path = '/mnt/max/shared/data/study/ADHD/HCP/processed/ADHD_NoFMNoT2/'
out_path = '/mnt/max/shared/projects/neurosynth/network_csvs/average_nonzero_1.97_threshold/'
z_threshold = 1.97
timecourse_csv = 'HCP.subcortical.32k_fs_LR.csv'
network_files = [
    'amygdala_insula.csv',
    'arousal.csv',
    'attentional_control.csv',
    'default_network.csv',
    'dorsal_attention.csv',
    'monetary_reward.csv',
    'response_inhibition.csv',
    'reward_anticipation.csv',
    'selective_attention.csv',
    'verbal_working.csv',
    'working_memory.csv'
]


def get_scanid(sub_id, path):
    """
    Extracting visit date and creating unique scan_id
    from full path to a subjects directory.
    """
    find = sub_id + '/(.+?)-SIEMENS'
    m = re.search(find, path)
    if m:
        visit = m.group(1)
    return sub_id + '_' + visit


def get_scanpaths(sub_path, sub_id, end_file, do='connectivity'):
    """
    takes in subjects path, subjects id, and the end file being looked at
    returns a list of full paths to that end file for all visits of that subject.
    """
    lookup = {'connectivity': ('analyses_v2', 'timecourses'), 'morphology': ('MNINonLinear', 'fsaverage_LR32k')}
    folder = lookup[do]
    wild_path = os.path.join(sub_path + sub_id, '*', '*', sub_id,
                               folder[0], folder[1], end_file)
    return glob.glob(wild_path)


def make_sublist(sub_path):
    """
    given a path to a study directory
    make a list of all subjects in that directory
    """
    sub_list = []
    for (dirpath, dirnames, filenames) in os.walk(sub_path):
        sub_list.extend(dirnames)
        break
    print(sub_list)
    return sub_list


def make_vectorized_df(path):
    """

    :param path:
    :return:
    """
    timecourse = pd.read_csv(path, header=None)
    timecourse = timecourse.T
    trimmed_timecourse = timecourse.loc[use_regions.iloc[:, network], :]  # timecourse contains only use_regions
    corr_matrix = trimmed_timecourse.T.corr()  # computes correlation matrix of only the use_regions
    utri = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(np.bool))
    return utri.stack().reset_index()  # vectorizing the upper triangle of the corr_matrix

def interface(neuro_path, sub_path, out_path, z_threshold, timecourse_csv, network_files):
    neuro_voxel = pd.read_csv(neuro_path, header=None)
    use_regions = neuro_voxel > z_threshold  # Use only the regions that have a z-score > 1.97
    sub_list = make_sublist(sub_path)

    for network, save_name in enumerate(network_files):
        print(network)
        # This part creates a dataframe with the regions only; the for loop will feed into this df.
        full_path_0 = get_scanpaths(sub_path, sub_list[0], timecourse_csv)
        if not full_path_0:
            print(sub_list[0], "glob %s: target doesn't exist" % wild_path_0, file=sys.stderr)
            continue

        in_df = make_vectorized_df(full_path_0[0])
        in_df.columns = ['Region_1', 'Region_2', 'sub_id']
        in_df.drop('sub_id', axis=1, inplace=True)  # creating df with use region pairs; loop below will feed into this

        for sub_id in sub_list:
            full_path = get_scanpaths(sub_path, sub_id, timecourse_csv)
            if not full_path_0:
                print(sub_id, "glob %s: target doesn't exist" % wild_path_0, file=sys.stderr)
                continue

            for path in full_path:  # looping through each timepoint
                subject = get_scanid(sub_id, path)
                sub_df = make_vectorized_df(path)
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
        print(in_df)

        # Saving it out subjects down rows; region pairs across columns
        in_df.T.to_csv(os.path.join(out_path, save_name), header=False)


# def cli_interface():
#     try:
#         neuro_path, sub_path, out_path, z_threshold, timecourse_csv = sys.argv[1:5]
#         network_files = sys.argv[6:]
#     except:
#         print("usage: {}  <neuro_path> <sub_path> <out_path> <z_threshold> <timecourse_csv> <network_files>"
#               .format(sys.argv[0]))
#         sys.exit(1)
#     interface(neuro_path, sub_path, out_path, z_threshold, timecourse_csv, network_files)


if __name__ == '__main__':
    # cli_interface()
    interface(neuro_path, sub_path, out_path, z_threshold, timecourse_csv, network_files)
