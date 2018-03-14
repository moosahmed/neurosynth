import glob
import os
import re
import subprocess
import sys

import pandas as pd
import numpy as np

# SET PATHS
neuro_path = '/mnt/max/shared/projects/neurosynth/roi_selection/average_nonzero_HCP_neurosynth_networks_concat.csv'
sub_path = '/mnt/max/shared/data/study/ADHD/HCP/processed/ADHD_NoFMNoT2/'
out_path = '/mnt/max/shared/projects/neurosynth/network_csvs/average_nonzero_1.97_threshold/'
z_threshold = 1.97
target_file = 'thickness.32k_fs_LR.dscalar.nii'
network_files = [
    'amygdala_insula_thickness.csv',
    'arousal_thickness.csv',
    'attentional_control_thickness.csv',
    'default_network_thickness.csv',
    'dorsal_attention_thickness.csv',
    'monetary_reward_thickness.csv',
    'response_inhibition_thickness.csv',
    'reward_anticipation_thickness.csv',
    'selective_attention_thickness.csv',
    'verbal_working_thickness.csv',
    'working_memory_thickness.csv'
]
parcellation = '/mnt/max/shared/ROI_sets/Surface_schemes/Human/HCP/fsLR/HCP.32k_fs_LR.dlabel.nii'


def cifti_parcelate(cifti, parcellation):
    parc_name = '.'.join(parcellation.split('/')[-1].split('.')[:-3])
    parcelated_cifti = '.'.join(cifti.split('.')[:-3])+'.'+parc_name+'.pscalar.nii'
    if os.path.isfile(parcelated_cifti):
        print('%s exists. skipping parcellation step.' % parcelated_cifti, file=sys.stdout)
    else:
        cmd = ['/usr/local/bin/wb_command', '-cifti-parcellate', cifti, parcellation, 'COLUMN', parcelated_cifti]
        subprocess.call(cmd)
    return parcelated_cifti


def cifti_convert_to_text(cifti):
    path2txt = '.'.join(cifti.split('.')[:-2])+'.txt'
    if os.path.isfile(path2txt):
        print('%s exists. skipping conversion step.' % path2txt, file=sys.stdout)
    else:
        cmd = ['/usr/local/bin/wb_command', '-cifti-convert', '-to-text', cifti, path2txt]
        subprocess.call(cmd)
    return path2txt

def interface(neuro_path, sub_path, out_path, z_threshold, target_file, network_files):
    # Read The neurosynth csv and fully covered csv; then compute which regions have a z-score more than 1.97
    # only use those regions
    neuro_voxel = pd.read_csv(neuro_path, header=None)
    use_regions = neuro_voxel > z_threshold

    # Create a list of subject IDs from the ADHD cohort
    sub_list = []
    for (dirpath, dirnames, filenames) in os.walk(sub_path):
        sub_list.extend(dirnames)
        break
    print(sub_list)

    # Loop Through each network's region selection using the use_regions variable
    for network, save_name in enumerate(network_files):
        print(network)
        in_df = pd.DataFrame()
        for sub_id in sub_list:
            # Grabs the full path for all subjects controlling for multiple visit dates
            wild_path = os.path.join(sub_path + sub_id, '*', '*', sub_id,
                                     'MNINonLinear', 'fsaverage_LR32k', sub_id+'.'+target_file)
            full_path = glob.glob(wild_path)

            if not full_path:
                print(sub_id, "glob target: %s doesn't exist" % wild_path, file=sys.stderr)
                continue

            for path in full_path:
                # Extracting Visit date from path
                find = sub_id + '/(.+?)-SIEMENS'
                m = re.search(find, path)
                if m:
                    visit = m.group(1)
                subject = sub_id + '_' + visit

                cifti_txt = cifti_convert_to_text(cifti_parcelate(path, parcellation))

                if not os.path.isfile(cifti_txt):
                    print(subject, 'Not able to parcellate dscalar', file=sys.stderr)
                    continue

                cifti_df = pd.read_table(cifti_txt, header=None)

                # Trimming regions in the timecourse file to only include the regions specified in use_regions for every
                # network
                sub_df = cifti_df.loc[use_regions.iloc[:, network], :]
                sub_df.columns = [subject]

                # Merging each subjects connectivity values into the df created in the previous part
                in_df = pd.concat([in_df, sub_df], axis=1)
        in_df.index += 1
        print(in_df)
        # Saving it out subjects down rows; region pairs across columns
        in_df.T.to_csv(os.path.join(out_path, save_name))

if __name__ == '__main__':
    # cli_interface()
    interface(neuro_path, sub_path, out_path, z_threshold, target_file, network_files)
