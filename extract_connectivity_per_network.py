import glob
import os
import re
import subprocess
import sys

import pandas as pd
import numpy as np
import yaml


def cifti_parcelate(cifti, parcellation):
    """
    this wraps the wb_command bash utility to be used in python
    """
    parc_name = '.'.join(parcellation.split('/')[-1].split('.')[:-3])
    parcelated_cifti = '.'.join(cifti.split('.')[:-3])+'.'+parc_name+'.pscalar.nii'
    if os.path.isfile(parcelated_cifti):
        # ...
        print('%s exists. skipping parcellation step.' % parcelated_cifti, file=sys.stdout)
    else:
        cmd = ['/usr/local/bin/wb_command', '-cifti-parcellate', cifti, parcellation, 'COLUMN', parcelated_cifti]
        subprocess.call(cmd)
    return parcelated_cifti


def cifti_convert_to_text(cifti):
    """
    this wraps the wb_command bash utility to be used in python
    """
    path2txt = '.'.join(cifti.split('.')[:-2])+'.txt'
    if os.path.isfile(path2txt):
        # ...
        print('%s exists. skipping conversion step.' % path2txt, file=sys.stdout)
    else:
        cmd = ['/usr/local/bin/wb_command', '-cifti-convert', '-to-text', cifti, path2txt]
        subprocess.call(cmd)
    return path2txt


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


def make_vectorized_df(path, network, use_regions):
    """
    takes in the path to a subjects parcellated timecourse, network assignment, and the regions being used.
    trims the timecourse to only contain regions being used
    computes a correlation matrix of the remaining regions
    returns a vectorized upper triangle of the corr matrix
    """
    timecourse = pd.read_csv(path, header=None)
    timecourse = timecourse.T
    trimmed_timecourse = timecourse.loc[use_regions.iloc[:, network], :]
    corr_matrix = trimmed_timecourse.T.corr()
    utri = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(np.bool))
    return utri.stack().reset_index()


def interface(neuro_path, sub_path, out_path, z_threshold, timecourse_csv, network_files,
              morph_target_file=None, parcellation=None):
    print(neuro_path, sub_path, out_path, network_files, file=sys.stdout)
    neuro_voxel = pd.read_csv(neuro_path, header=None)
    use_regions = neuro_voxel > z_threshold  # Use only the regions that have a z-score > 1.97
    sub_list = make_sublist(sub_path)

    for network, save_name in enumerate(network_files):
        print(network)
        # TODO: Remove this for release
        if network == 0:
            continue

        full_path_0 = get_scanpaths(sub_path, sub_list[0], timecourse_csv)
        if not full_path_0:
            print(sub_list[0], "glob target for full_path_0 doesn't exist", file=sys.stderr)
            continue

        in_df = make_vectorized_df(full_path_0[0], network, use_regions)
        in_df.columns = ['Region_1', 'Region_2', 'sub_id']
        in_df.drop('sub_id', axis=1, inplace=True)  # creating df with use region pairs; loop below will feed into this

        if morph_target_file:
            morph_df = pd.DataFrame()

        for sub_id in sub_list:
            full_path = get_scanpaths(sub_path, sub_id, timecourse_csv)
            if not full_path:
                print(sub_id, "glob target for full_path doesn't exist", file=sys.stderr)
                continue

            for path in full_path:  # looping through each timepoint
                subject = get_scanid(sub_id, path)
                sub_df = make_vectorized_df(path, network, use_regions)
                sub_df.columns = ['Region_1', 'Region_2', subject]

                # Merging each subjects connectivity values into the df created in the previous part
                in_df = pd.merge(in_df, sub_df, 'inner', on=['Region_1', 'Region_2'])

            if morph_target_file:
                all_morph_paths = get_scanpaths(sub_path, sub_id, sub_id+'.'+morph_target_file, do='morphology')
                if not all_morph_paths:
                    print(sub_id, "glob target for all_morph_paths doesn't exist", file=sys.stderr)
                    continue

                for morph_path in all_morph_paths:
                    morph_subject = get_scanid(sub_id, morph_path)
                    cifti_txt = cifti_convert_to_text(cifti_parcelate(morph_path, parcellation))
                    if not os.path.isfile(cifti_txt):
                        print(morph_subject, 'Not able to parcellate dscalar', file=sys.stderr)
                        continue

                    cifti_df = pd.read_table(cifti_txt, header=None)

                    # Trimming morphology df to only contain use_regions
                    morph_sub_df = cifti_df.loc[use_regions.iloc[:, network], :]
                    morph_sub_df.columns = [morph_subject]

                    # Concatenating each subjects connectivity values into main empty
                    morph_df = pd.concat([morph_df, morph_sub_df], axis=1)  # concatenating each
        # Adding one to region names to account for 0-indexing
        in_df['Region_1'] += 1
        in_df['Region_2'] += 1
        if morph_target_file:
            morph_df.index += 1

        # Deleting Cerebellum_left and right, Diencephalon_ventral_left and right and brain stem
        censored_regions = [361, 366, 370, 371, 379]
        for key in censored_regions:
            in_df = in_df[in_df.Region_1 != key]
            in_df = in_df[in_df.Region_2 != key]

        # Creating region pair connectivity headers
        reg_p = '[' + in_df['Region_1'].astype(str) + ',' + in_df['Region_2'].astype(str) + ']'
        in_df.drop(['Region_1', 'Region_2'], axis=1, inplace=True)
        in_df.insert(0, 'Region_pairs', reg_p)
        in_df['Region_pairs'].astype(str)
        print(in_df.T)

        # Saving it out subjects down rows; region pairs across columns
        # in_df.T.to_csv(os.path.join(out_path, save_name), header=False)
        if morph_target_file:
            morph_save_name = '.'.join(save_name.split('.')[:-1])+'_'+morph_target_file.split('.')[0]+'.csv'
            print(morph_save_name)
            print(morph_df.T)
            # morph_df.T.to_csv(os.path.join(out_path, morph_save_name))


def cli_interface():
    try:
        yaml_config = sys.argv[1]
    except:
        print("usage: {}  <yaml_config>".format(sys.argv[0]))
        sys.exit(1)
    with open(yaml_config, 'r') as f:
        args = yaml.load(f)
    interface(**args)


if __name__ == '__main__':
    cli_interface()
