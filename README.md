Utility that takes in output from the neurosynth meta analysis.
http://neurosynth.org/

For a neurosynth network the data needs to be extracted onto a csv and
parcellated. This give an average z-score for that network for every region of
the parcellation.

This Utility takes in that csv and a study directory. Trims the timecourse for
every subject, to only include regions deemed significant by neurosynth.

Calculates a connectivity matrix for only those use regions, it then outputs
every region pair and it's connectivity value for every subject and for every
network. this is presented in an organised csv and saved in your out put folder.

Optional arguments:

This Utility can also extract morphology metrics for those use regions. It needs
to parcellate the dscalars, so path to your wb_command and parcellation will
also be required.

There are in line documentations as well.