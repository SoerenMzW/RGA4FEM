
import numpy as np
import os
import glob
from abaqus import *
from abaqusConstants import *
from odbAccess import *
import regionToolset

#######################################################################################################################
## Get the strain data from the *.odb-file with the displacements 2024-03-04_WingBox-Demonstrator_15m.odb

# Definition of empty variables for later use in the data storage
element_labels = []
sectionPoint = []
E11 = []
E22 = []
E33 = []
E12 = []
node_labels = []
U1 = []
U2 = []
U3 = []

# Find the *.odb-file in the current directory
odb_file = glob.glob('*.odb')
odb_file = odb_file[0]
# Get the current directory and combine it with the *.odb-file name
directory = os.getcwd()
directory = directory.replace('\\', '/')
file = directory+'/'+odb_file

result_folder = directory.replace('\\lib', '\\Results')

# Open the *.obd-file
odb = session.openOdb(name=file)

# Extract the strain values
E = odb.steps['Load-Step'].frames[-1].fieldOutputs['E'].values
# Write the extracted strain data with element ID, strains in the different directions and section points into variables
for element_data in E:
    element_labels.append(element_data.elementLabel)
    sectionPoint.append(element_data.sectionPoint.number)
    E11.append(element_data.data[0])
    E22.append(element_data.data[1])
    E33.append(element_data.data[2])
    E12.append(element_data.data[3])
# Combine strain-dependent variables in a list
E_data_list = np.column_stack((element_labels, sectionPoint, E11, E22, E33, E12))
# Save the "strain list" as a *.txt-file
name_job, _ = os.path.splitext(odb_file)
np.savetxt('E_' + name_job + '.txt', E_data_list, delimiter=',')

del element_labels, sectionPoint, E11, E22, E33, E12

# Extract the displacement values
U = odb.steps['Load-Step'].frames[-1].fieldOutputs['U'].values
# Write the extracted displacement data with node ID and displacements in the different directions into variables
for node_data in U:
    node_labels.append(node_data.nodeLabel)
    U1.append(node_data.data[0])
    U2.append(node_data.data[1])
    U3.append(node_data.data[2])
#Combine node IDs and displacement data into a list and save it as a *.txt-file
U_data_list = np.column_stack((node_labels, U1, U2, U3))
np.savetxt('U_' + name_job + '.txt', U_data_list, delimiter=',')

del U1, U2, U3, node_labels

#######################################################################################################################
## Import the *.inp-file to get the element midpoints written out

# Open the *.inp-file
name_job = name_job[:38]  # Name of the model can only have 38 characters
mdb.ModelFromInputFile(name=name_job, inputFileName=directory+'/'+name_job+'.inp')
a = mdb.models[name_job].rootAssembly
name_inst = a.instances
name = name_inst.keys()
name = str(name)
name = name.replace('[', '')
name = name.replace(']', '')
name = name.strip('\'')
elements = a.instances[name].elements

# Define empty variables
centroid_list = []
element_labels = []
element_connectivity = []

# Loop over the elements and write the data into the list-variables
for i, el in enumerate(elements):
    element_labels.append(elements[i].label)
    connectivity = elements[i].connectivity
    connectivity = [j+1 for j in connectivity]
    element_connectivity.append(connectivity)
    region = regionToolset.Region(elements=elements[i:i+1])
    properties = a.getMassProperties(regions=region)
    centroid_list.append(list(properties['volumeCentroid']))
    connectivity = []


element_data_list = np.column_stack((element_labels, element_connectivity, centroid_list))

np.savetxt('Element_Nodes_Midpoints.txt', element_data_list, delimiter=',')

del file, directory, centroid_list, element_labels, element_connectivity
