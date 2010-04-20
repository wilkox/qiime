#!/usr/bin/env python
# File created on 09 Feb 2010
#file make_3d_plots.py

from __future__ import division

__author__ = "Jesse Stombaugh"
__copyright__ = "Copyright 2010, The QIIME project"
__credits__ = ["Jesse Stombaugh", "Rob Knight", "Micah Hamady", "Dan Knights",
    "Justin Kuczynski"]
__license__ = "GPL"
__version__ = "1.0.0-dev"
__maintainer__ = "Jesse Stombaugh"
__email__ = "jesse.stombaugh@colorado.edu"
__status__ = "Development"
 

from qiime.util import parse_command_line_parameters, get_options_lookup, create_dir
from optparse import make_option
from qiime.make_3d_plots import generate_3d_plots
from qiime.parse import parse_coords,group_by_field,group_by_fields
import shutil
import os
from qiime.colors import sample_color_prefs_and_map_data_from_options
from random import choice
from time import strftime
from qiime.util import get_qiime_project_dir
from qiime.make_3d_plots import get_coord,get_map,remove_unmapped_samples, \
                                get_custom_coords, \
                                process_custom_axes, process_coord_filenames, \
                                remove_nans, scale_custom_coords
from qiime.biplots import get_taxa,get_taxa_coords,get_taxa_prevalence,\
    remove_rare_taxa, make_mage_taxa
from cogent.util.misc import get_random_directory_name
import numpy as np

options_lookup = get_options_lookup()

#make_3d_plots.py
script_info={}
script_info['brief_description']="""Make 3D PCoA plots"""
script_info['script_description']="""This script automates the construction of 3D plots (kinemage format) from the PCoA output file generated by principal_coordinates.py (e.g. P1 vs. P2 vs. P3, P2 vs. P3 vs. P4, etc., where P1 is the first component)."""
script_info['script_usage']=[]
script_info['script_usage'].append(("""Default Usage:""","""If you just want to use the default output, you can supply the principal coordinates file (i.e., resulting file from principal_coordinates.py) and a user-generated mapping file, where the default coloring will be based on the SampleID as follows:""","""%prog -i beta_div_coords.txt -m Mapping_file.txt"""))
script_info['script_usage'].append(("","""To include taxa in the plot (i.e.: a biplot), use the -t option along with an otu table / output from summarize_taxa.py""",""))
script_info['script_usage'].append(("","""Additionally, the user can supply their mapping file ("-m") and a specific category to color by ("-b") or any combination of categories. When using the -b option, the user can specify the coloring for multiple mapping labels, where each mapping label is separated by a comma, for example: -b 'mapping_column1,mapping_column2'. The user can also combine mapping labels and color by the combined label that is created by inserting an '&&' between the input columns, for example: -b 'mapping_column1&&mapping_column2'.""",""))
script_info['script_usage'].append(("","""If the user would like to color all categories in their metadata mapping file, they can pass 'ALL' to the '-b' option, as follows:""","""%prog -i beta_div_coords.txt -m Mapping_file.txt -b ALL"""))
script_info['script_usage'].append(("","""As an alternative, the user can supply a preferences (prefs) file, using the -p option. The prefs file allows the user to give specific samples their own columns within a given mapping column. This file also allows the user to perform a color gradient, given a specific mapping column.

If the user wants to color by using the prefs file (e.g. prefs.txt), they can use the following code:""","""%prog -i beta_div_coords.txt -m Mapping_file.txt -p prefs.txt
"""))
script_info['script_usage'].append(("""Output Directory:""","""If you want to give an specific output directory (e.g. "3d_plots"), use the following code:""","""%prog -i principal_coordinates-output_file --o 3d_plots/"""))
script_info['script_usage'].append(("""Background Color Example:""","""If the user would like to color the background white they can use the '-k' option as follows:""","""%prog -i beta_div_coords.txt -m Mapping_file.txt -b ALL -k white"""))

script_info['output_description']="""By default, the script will plot the first three dimensions in your file. Other combinations can be viewed using the "Views:Choose viewing axes" option in the KiNG viewer (Chen, Davis, & Richardson, 2009), which may require the installation of kinemage software. The first 10 components can be viewed using "Views:Paralled coordinates" option or typing "/". The mouse can be used to modify display parameters, to click and rotate the viewing axes, to select specific points (clicking on a point shows the sample identity in the low left corner), or to select different analyses (upper right window). Although samples are most easily viewed in 2D, the third dimension is indicated by coloring each sample (dot/label) along a gradient corresponding to the depth along the third component (bright colors indicate points close to the viewer)."""
script_info['required_options']=[\
make_option('-i', '--coord_fname', dest='coord_fname', \
help='This is the path to the principal coordinates file (i.e., resulting \
file from principal_coordinates.py), or to a directory containing multiple coord files \
for averaging (e.g. resulting files from multiple_rarefactions_even_depth.py, \
followed by multiple beta_diversity.py, followed by multiple principal_coordinates.py).'), \
make_option('-m', '--map_fname', dest='map_fname', \
     help='This is the metadata mapping file  [default=%default]'), \
]
script_info['optional_options']=[\
 make_option('-b', '--colorby', dest='colorby',\
     help='This is the categories to color by in the plots from the \
user-generated mapping file. The categories must match the name of a column \
header in the mapping file exactly and multiple categories can be list by \
comma separating them without spaces. The user can also combine columns in the \
mapping file by separating the categories by "&&" without spaces \
[default=%default]'),
 make_option('-a', '--custom_axes',help='This is the category from the \
user-generated mapping file to use as a custom axis in the plot.  For instance,\
there is a pH category and would like to seethe samples plotted on that axis \
instead of PC1, PC2, etc., one can use this option.  It is also useful for \
plotting time-series data [default: %default]'),
 make_option('-p', '--prefs_path',help='This is the user-generated preferences \
file. NOTE: This is a file with a dictionary containing preferences for the \
analysis [default: %default]'),
 make_option('-k', '--background_color',help='This is the background color to \
use in the plots (Options are \'black\' or \'white\'. [default: %default]'),
 options_lookup['output_dir'],

# summary plot stuff
 make_option('--ellipsoid_smoothness',help='The level of smoothness used in \
plotting ellipsoids for a summary plot (i.e. using a directory of coord files \
instead of a single coord file). Valid range is 0-3. A value of 0 produces \
very coarse "ellipsoids" but is fast to render. A value of 3 produces very \
smooth ellipsoids but will be very slow to render if you have more than a \
few data points.', default=2),
 make_option('--ellipsoid_opacity',help='Used when plotting ellipsoids for \
a summary plot (i.e. using a directory of coord files instead of a single coord \
file). Valid range is 0-3. A value of 0 produces completely transparent \
(invisible) ellipsoids. A value of 1 produces completely opaque ellipsoids.', \
default=0.33),
 make_option('--ellipsoid_method',help='Used when plotting ellipsoids for \
a summary plot (i.e. using a directory of coord files instead of a single coord \
file). Valid values are "IQR" and "sdev".',default="IQR"),
     
#biplot stuff
 make_option('-t', '--taxa_fname',help='If you wish to perform a biplot, ' +\
 'where taxa are plotted along with samples, supply an otu table format file.'+\
 '  Typically this is the output from summarize_taxa.py.', default=None),
 make_option('--n_taxa_keep',help='If performing a biplot, the number of taxa \
to display; use -1 to \
display all. [default: %default]',default=10),
 make_option('--master_pcoa',help='If performing averaging on multiple coord \
files, the other coord files will be aligned to this one through procrustes \
analysis. This master file will not be included in the averaging. \
If this master coord file is not provided, one of the other coord files will \
be chosen arbitrarily as the target alignment. [default: %default]',default=None),
]

script_info['version'] = __version__

def main():
    option_parser, opts, args = parse_command_line_parameters(**script_info)

    prefs, data, background_color, label_color= \
                            sample_color_prefs_and_map_data_from_options(opts)

    # Potential conflicts
    if not opts.custom_axes is None and os.path.isdir(opts.coord_fname):
        # can't do averaged pcoa plots _and_ custom axes in the same plot
        option_parser.error("Please supply either custom axes or multiple coordinate \
files, but not both.")
    # check that smoothness is an integer between 0 and 3
    try:
        ellipsoid_smoothness = int(opts.ellipsoid_smoothness)
    except:
        option_parser.error("Please supply an integer ellipsoid smoothness \
value.")
    if ellipsoid_smoothness < 0 or ellipsoid_smoothness > 3:
        option_parser.error("Please supply an ellipsoid smoothness value \
between 0 and 3.")
    # check that opacity is a float between 0 and 1
    try:
        ellipsoid_alpha = float(opts.ellipsoid_opacity)
    except:
        option_parser.error("Please supply a number for ellipsoid opacity.")
    if ellipsoid_alpha < 0 or ellipsoid_alpha > 1:
        option_parser.error("Please supply an ellipsoid opacity value \
between 0 and 1.")
    # check that ellipsoid method is valid
    ellipsoid_methods = ['IQR','sdev']
    if not opts.ellipsoid_method in ellipsoid_methods:
        option_parser.error("Please supply a valid ellipsoid method. \
Valid methods are: " + ', '.join(ellipsoid_methods) + ".")
  
    # gather ellipsoid drawing preferences
    ellipsoid_prefs = {}
    ellipsoid_prefs["smoothness"] = ellipsoid_smoothness
    ellipsoid_prefs["alpha"] = ellipsoid_alpha
        
    #Open and get coord data
    data['coord'] = get_coord(opts.coord_fname, opts.ellipsoid_method)
    
    # remove any samples not present in mapping file
    remove_unmapped_samples(data['map'],data['coord'])

    if opts.taxa_fname != None:
        # get taxonomy counts
        # get list of sample_ids that haven't been removed
        sample_ids = data['coord'][0]
        # get taxa summaries for all sample_ids
        lineages, taxa_counts = get_taxa(opts.taxa_fname, sample_ids)
        data['taxa'] = {}
        data['taxa']['lineages'] = lineages
        data['taxa']['counts'] = taxa_counts

        # get average relative abundance of taxa
        data['taxa']['prevalence'] = get_taxa_prevalence(data['taxa']['counts'])
        remove_rare_taxa(data['taxa'],nkeep=opts.n_taxa_keep)
        # get coordinates of taxa (weighted mean of sample scores)
        data['taxa']['coord'] = get_taxa_coords(data['taxa']['counts'],
            data['coord'][1])
    

    # process custom axes, if present.
    custom_axes = None
    if opts.custom_axes:
        custom_axes = process_custom_axes(opts.custom_axes)
        get_custom_coords(custom_axes, data['map'], data['coord'])
        remove_nans(data['coord'])
        scale_custom_coords(custom_axes,data['coord'])

    if opts.output_dir:
        create_dir(opts.output_dir,False)
        dir_path=opts.output_dir
    else:
        dir_path='./'
    
    qiime_dir=get_qiime_project_dir()

    jar_path=os.path.join(qiime_dir,'qiime/support_files/jar/')

    data_dir_path = get_random_directory_name(output_dir=dir_path,
                                              return_absolute_path=False)    
    
    try:
        os.mkdir(data_dir_path)
    except OSError:
        pass

    data_file_path=data_dir_path

    jar_dir_path = os.path.join(dir_path,'jar')
    
    try:
        os.mkdir(jar_dir_path)
    except OSError:
        pass
    
    shutil.copyfile(os.path.join(jar_path,'king.jar'), os.path.join(jar_dir_path,'king.jar'))

    filepath=opts.coord_fname
    if os.path.isdir(filepath):
        coord_files = [fname for fname in os.listdir(filepath) if not \
                           fname.startswith('.')]
        filename = os.path.split(coord_files[0])[-1]
        print os.listdir(filepath)
    else:
        filename = os.path.split(filepath)[-1]

    try:
        action = generate_3d_plots
    except NameError:
        action = None

    print filename
    #Place this outside try/except so we don't mask NameError in action
    if action:
        action(prefs,data,custom_axes,background_color,label_color,dir_path, \
                data_file_path,filename,ellipsoid_prefs=ellipsoid_prefs)


if __name__ == "__main__":
    main()
