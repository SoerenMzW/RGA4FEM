
###############################################################
"""
This code and the belonging data published at GitHub are used in the publication
entitled "Reliability Assessment of Wireless Sensor Networks by Strain-based 
Region Analysis for Redundancy Estimation in Measurements on the Example of an 
Aircraft Wing Box" in the MDPI Journal of Sensors.

The code consists of two sub-scripts:
1. 01_Strain_Export, which is used for the export of strain and displacement data
   from Abaqus CAE
2. 02_RGA4FEM, which includes the adapted Region Growing Algorithm for strain 
   measurements presented in the above mentioned paper
   
This code is developed by Sören Meyer zu Westerhausen and Thorben-Hendrik Lauth.
For information and details, please contact Sören Meyer zu Westerhausen via
meyer-zu-westerhausen@ipeg.uni-hannover.de
"""
###############################################################

# Imports for the main
import subprocess
import os

# Definition of global variables
directory = os.getcwd()
inp_folder = directory+'\\lib'

# Create a result folder to store the results after the extraction
# from the *.odb-file in Abaqus
folder = 'Results'
path = os.path.join(inp_folder, folder)
os.mkdir(path)

## Call the Abaqus function for the strain export in cmd
os.chdir(inp_folder)
os.system('cmd /C "abaqus cae noGUI=01_Strain_Export.py"')
os.system('exit cmd')
os.unlink('abaqus.rpy')
os.chdir(directory)

###############################################################

## Call the subprocess for the region analysis
subprocess.run(['python', inp_folder+'\\02_RGA4FEM.py', inp_folder])


