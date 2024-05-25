
# Imports of Python Bibs for the Script
import numpy as np
import pandas as pd
import os
import glob

# Exctract node coordinates and element definitions from the Abaqus-Input file
directory = os.getcwd()
inp_folder = directory+'\\lib'
result_folder = inp_folder+'\\Results'
os.chdir(inp_folder)

# Search for the *.inp-file in the current directory
inp_filename = glob.glob('*.inp')
inp_filename = inp_filename[0]

# Open the *.inp file
with open(inp_filename, 'r') as file:
    lines = file.readlines()

# Define Variables for the node and element definitions
node_coordinates = []
element_definition = []

# Extract node coordinates from the lines of the *.inp file
for line in lines:
    # Search for lines with node coordinates
    if '*Node' in line:
        next_line = lines[lines.index(line) + 1]
        while ',' in next_line and not next_line.startswith('*'):
            # Extract values for the nodes
            node_id, x, y, z = next_line.strip().split(',')[0:4]
            node_coordinates.append([node_id, x, y, z])
            next_line = lines[lines.index(next_line) + 1]

# Write data into a data frame
df_node_coordinates = pd.DataFrame(node_coordinates)
df_node_coordinates.columns = ['Node', 'X', 'Y', 'Z']
df_node_coordinates = df_node_coordinates.astype({"Node": int, "X": float, "Y": float, "Z": float})
os.chdir(result_folder)
np.savetxt('Node_Coordinates.txt', df_node_coordinates, delimiter=',')
os.chdir(inp_folder)

# Search for the section with element definition by their nodes in the *.inp file
found_elements = False
for line in lines:
    # Search the start of the section of the file with the definition of element types
    if '*Element, type=S4R' in line:
        found_elements = True
    # Search end of the section with element definitions
    elif found_elements and line.startswith('*'):
        found_elements = False
    # Extract the elements and their definition by the nodes
    elif found_elements:
        data = line.strip().split(',')
        element_id = data[0]
        node_ids = data[1:]
        element_definition.append([element_id] + node_ids)

# Write data of element definition into a data frame
df_element_definition = pd.DataFrame(element_definition)
df_element_definition.columns = ['Element', 'Node1', 'Node2', 'Node3', 'Node4']
df_element_definition = df_element_definition.astype(int)

# Load the already extracted element strain data

# Get and load the file and write its data into a data frame
inp_filename = inp_filename.replace('.inp', '')
strain_file_name = 'E_'+inp_filename+'.txt'

# Move the displacement data into the results folder for use in calculation with Ko's displacement theory
disp_data_file = 'U_'+inp_filename+'.txt'
os.replace(inp_folder + '\\' + disp_data_file, result_folder + '\\' + disp_data_file)
del disp_data_file

df_strains = pd.read_csv(strain_file_name, delimiter=',', header=None)
df_strains.columns = ['Element', 'SEC_PT', 'E11', 'E22', 'E33', 'E12']
# Bring list with element definition in the same size as the list of strain results with two section points
df_element_definition2 = pd.concat([df_element_definition]*2, ignore_index=True)
df_strains = df_strains.astype({"Element": int, "SEC_PT": int, "E11": float, "E22": float, "E33": float, "E12": float})

df_Elements_Nodes_Strains = pd.concat([df_element_definition2, df_strains['SEC_PT'], df_strains['E11'],
                                       df_strains['E22'], df_strains['E33'], df_strains['E12']], axis=1)
os.chdir(result_folder)
np.savetxt('Elements_Nodes_Strains.txt', df_Elements_Nodes_Strains, delimiter=',')
os.chdir(inp_folder)

# Delete the file with the strain information
os.unlink(strain_file_name)

# Delete not further necessary variables
del df_strains, strain_file_name, df_element_definition, df_element_definition2

## Perform region analysis

# Create list with the node numbers
required_columns = ['Node1', 'Node2', 'Node3', 'Node4']
unique_nodes = df_Elements_Nodes_Strains[required_columns].values.flatten()
unique_nodes = np.unique(unique_nodes)

# Check if column 'Node2' exists DataFrame
if 'Node2' not in df_Elements_Nodes_Strains.columns:
    # Add column 'Node2' with standard values
    df_Elements_Nodes_Strains['Node2'] = None

# Check if column 'Node3' exists DataFrame
if 'Node3' not in df_Elements_Nodes_Strains.columns:
    # Add column 'Node3' with standard values
    df_Elements_Nodes_Strains['Node3'] = None

# Check if column 'Node4' exists DataFrame
if 'Node4' not in df_Elements_Nodes_Strains.columns:
    # Add column 'Node4' with standard values
    df_Elements_Nodes_Strains['Node4'] = None

# Check if all required columns exist
missing_columns = [col for col in required_columns if col not in df_Elements_Nodes_Strains.columns]

# Add missing columns with standard values
for col in missing_columns:
    df_Elements_Nodes_Strains[col] = None

# Create empty column 'Contact' in the DataFrame
df_Elements_Nodes_Strains['Contact'] = False

def optimized_region_growing(df_sec_pt, unique_nodes, neighbor_type, tolerance, max_percent_deviation):
    regions = []
    for index in range(len(df_sec_pt)):
        row = df_sec_pt.iloc[index]
        if row['Region'] is None:
            region_elements = [row['Element']]
            region_values_e11 = [row['E11']]
            region_values_e12 = [row['E12']]
            region_values_e22 = [row['E22']]
            region_mean_e11 = [row['E11']]
            region_mean_e12 = [row['E12']]
            region_mean_e22 = [row['E22']]

            seed_index = index
            df_sec_pt.at[index, 'Region'] = len(regions) + 1

            while True:
                if neighbor_type == '4':
                    neighbors = df_sec_pt[(abs(df_sec_pt['E22'] - df_sec_pt.at[seed_index, 'E22']) < tolerance) &
                                          (abs(df_sec_pt['E11'] - df_sec_pt.at[seed_index, 'E11']) < tolerance) &
                                          (abs(df_sec_pt['E12'] - df_sec_pt.at[seed_index, 'E12']) < tolerance) &
                                          (df_sec_pt['Region'].isnull())]
                elif neighbor_type == '8':
                    neighbors = df_sec_pt[(abs(df_sec_pt['E22'] - df_sec_pt.at[seed_index, 'E22']) < tolerance) &
                                          (abs(df_sec_pt['E11'] - df_sec_pt.at[seed_index, 'E11']) < tolerance) &
                                          (abs(df_sec_pt['E12'] - df_sec_pt.at[seed_index, 'E12']) < tolerance) &
                                          (df_sec_pt['Region'].isnull())]

                if len(neighbors) > 0:
                    seed_index = neighbors.index[0]
                else:
                    break

                valid_neighbors = []
                for n_index in range(len(neighbors)):
                    neighbor = neighbors.iloc[n_index]
                    deviation_percent_e11 = (neighbor['E11'] - np.mean(region_mean_e11)) / np.mean(region_mean_e11) * 100
                    deviation_percent_e12 = (neighbor['E12'] - np.mean(region_mean_e12)) / np.mean(region_mean_e12) * 100
                    deviation_percent_e22 = (neighbor['E22'] - np.mean(region_mean_e22)) / np.mean(region_mean_e22) * 100

                    if abs(deviation_percent_e11) <= max_percent_deviation and \
                            abs(deviation_percent_e12) <= max_percent_deviation and \
                            abs(deviation_percent_e22) <= max_percent_deviation:
                        valid_neighbors.append(n_index)

                if len(valid_neighbors) == 0:
                    break

                for n_index in valid_neighbors:
                    neighbor = neighbors.iloc[n_index]
                    if neighbor_type == '4':
                        neighbor_nodes = df_Elements_Nodes_Strains.loc[
                            df_Elements_Nodes_Strains['Element'] == neighbor['Element'], ['Node1', 'Node2', 'Node3', 'Node4']].values.flatten()
                        common_nodes = np.intersect1d(unique_nodes, neighbor_nodes)
                        if len(common_nodes) >= 2:
                            df_sec_pt.at[neighbor.name, 'Region'] = len(regions) + 1
                            region_elements.append(neighbor['Element'])
                            region_values_e11.append(neighbor['E11'])
                            region_values_e12.append(neighbor['E12'])
                            region_values_e22.append(neighbor['E22'])
                            region_mean_e11.append(np.mean(region_values_e11))
                            region_mean_e12.append(np.mean(region_values_e12))
                            region_mean_e22.append(np.mean(region_values_e22))
                    elif neighbor_type == '8':
                        df_sec_pt.at[neighbor.name, 'Region'] = len(regions) + 1
                        region_elements.append(neighbor['Element'])
                        region_values_e11.append(neighbor['E11'])
                        region_values_e12.append(neighbor['E12'])
                        region_values_e22.append(neighbor['E22'])
                        region_mean_e11.append(np.mean(region_values_e11))
                        region_mean_e12.append(np.mean(region_values_e12))
                        region_mean_e22.append(np.mean(region_values_e22))

            if len(region_elements) > 1:
                deviation_percent_e11 = (max(region_mean_e11) - min(region_mean_e11)) / np.mean(region_mean_e11) * 100
                deviation_percent_e12 = (max(region_mean_e12) - min(region_mean_e12)) / np.mean(region_mean_e12) * 100
                deviation_percent_e22 = (max(region_mean_e22) - min(region_mean_e22)) / np.mean(region_mean_e22) * 100

                if deviation_percent_e11 > max_percent_deviation or \
                        deviation_percent_e12 > max_percent_deviation or \
                        deviation_percent_e22 > max_percent_deviation:
                    region_elements = []

            if len(region_elements) > 0:
                regions.append({'Region': len(regions) + 1, 'Elements': region_elements,
                                'E11': region_values_e11, 'E12': region_values_e12, 'E22': region_values_e22})

    return regions

# Ask the user which iteration point approach should be used
while True:
    neighbor_type = input("Should the 4- or 8-neighbor-approach be applied? Type 4 or 8: ")
    if neighbor_type == '4' or neighbor_type == '8':
        print("You have chosen the " + neighbor_type + "-neighbor-approach.")
        break
    else:
        print("Error, please type '4' or '8'.")


# Ask the user for tolerance criterion for region analysis (e. g. tolerance = 0.009)
while True:
    tolerance = input("What is the measuring tolerance of the strain gages used? Please type in: ")
    if len(tolerance) != 0:
        print("Sensor tolerance is " + tolerance)
        break
    else:
        print("Error, please type a value for the sensor tolerance.")

tolerance = float(tolerance)

# Ask the user for max. deviation criterion for region analysis (max_percent_deviation=10)
while True:
    max_percent_deviation = input("What is the maximal tolerable deviation of region average in percent? "
                                   "Please type in: ")
    if len(max_percent_deviation) != 0:
        print("Tolerable deviation of region average is " + max_percent_deviation + " %")
        break
    else:
        print("Error, please type a value for the maximal tolerable deviation of region average.")

max_percent_deviation = float(max_percent_deviation)

# Create Numpy-Array with clear and precise SEC_PT values
sec_pt_values = np.array([1])


# Create column 'Region'
df_Elements_Nodes_Strains['Region'] = None

# Sort SEC_PT values and call the adapted region growing algorithm
for sec_pt_value in sec_pt_values:
    # Filter SEC_PT values
    df_sec_pt = df_Elements_Nodes_Strains[df_Elements_Nodes_Strains['SEC_PT'] == sec_pt_value]

    # Add column 'Region'
    df_Elements_Nodes_Strains.loc[df_Elements_Nodes_Strains['SEC_PT'] == sec_pt_value, 'Region'] = None

    # Create list to add empty regions
    regionen = []

    # Call the adapted Region Growing Algorithm
    regionen = optimized_region_growing(df_sec_pt, unique_nodes, neighbor_type, tolerance, max_percent_deviation)


    if sec_pt_value == 1:
        filename_e11 = 'result_e11_sec_pt_1.txt'
        filename_e12 = 'result_e12_sec_pt_1.txt'
        filename_e22 = 'result_e22_sec_pt_1.txt'
    elif sec_pt_value == 5:
        filename_e11 = 'ergebnis_e11_sec_pt_5.txt'
        filename_e12 = 'ergebnis_e12_sec_pt_5.txt'
        filename_e22 = 'ergebnis_e22_sec_pt_5.txt'

    with open(filename_e11, 'w') as file_e11:
        for region in regionen:
            file_e11.write(f"Region: {region['Region']}\n")
            for element, Value in zip(region['Elements'], region['E11']):
                file_e11.write(f"Element: {element}, Value E11: {Value}\n")
            file_e11.write('\n')

    with open(filename_e12, 'w') as file_e12:
        for region in regionen:
            file_e12.write(f"Region: {region['Region']}\n")
            for element, Value in zip(region['Elements'], region['E12']):
                file_e12.write(f"Element: {element}, Value E12: {Value}\n")
            file_e12.write('\n')

    with open(filename_e22, 'w') as file_e22:
        for region in regionen:
            file_e22.write(f"Region: {region['Region']}\n")
            for element, Value in zip(region['Elements'], region['E22']):
                file_e22.write(f"Element: {element}, Value E22: {Value}\n")
            file_e22.write('\n')


# Read in the *.txt-files and compare the considered values of strain direction.

# Import and read 'result_e11_sec_pt_1.txt' and 'result_e22_sec_pt_1.txt'
with open("result_e11_sec_pt_1.txt", "r") as file_e11, open("result_e22_sec_pt_1.txt", "r") as file_e22:
    regions_e11_sec_pt_1 = file_e11.read()
    regions_e22_sec_pt_1 = file_e22.read()

# Write results into 'Results_E11_E22_SEC_PT_1.txt' with summarized E11 und E22 for the first SEC_PT
with open("Results_E11_E22_SEC_PT_1.txt", "w") as file:
    file.write("Results of result_e11_sec_pt_1.txt:\n\n")
    file.write(regions_e11_sec_pt_1)
    file.write("\n\n")
    file.write("Results of result_e22_sec_pt_1.txt:\n\n")
    file.write(regions_e22_sec_pt_1)

# Import and read 'Results_E11_E22_SEC_PT_1.txt'
with open("Results_E11_E22_SEC_PT_1.txt", "r") as file:
    regions_combined_sec_pt_1 = file.read()

# Define the maximal difference between different element numbers
max_differenz = None

# Function for the combination of regions based on their size and position as well as included elements
def merge_regions(region_list):
    merged_regions = []

    for region in region_list:
        if not region.strip():
            continue

        region_lines = region.strip().split('\n')
        region_number_line = region_lines[0].split(':')
        if len(region_number_line) != 2:
            continue

        region_number = region_number_line[1].strip()
        if not region_number.isdigit():
            continue

        element_lines = region_lines[1:]

        merged = False

        for merged_region in merged_regions:
            merged_elements = merged_region['Elements']

            # Check for the same region size
            if len(element_lines) == len(merged_elements):
                if all(element_line.split(', ')[0] == merged_element_line.split(', ')[0] for element_line, merged_element_line in zip(element_lines, merged_elements)):
                    merged_region['Elements'].extend(element_lines)
                    merged = True
                    break

        if not merged:
            merged_regions.append({'Region': int(region_number), 'Elements': element_lines})

    return merged_regions


## Filter for empty regions
regions_combined_filtered_sec_pt_1 = [region for region in regions_combined_sec_pt_1.split('\n\n') if region.strip()]

# Call function to combine regions of the same size
merged_regions_sec_pt_1 = merge_regions(regions_combined_filtered_sec_pt_1)

# Update the content of the file 'Results_E11_E22_SEC_PT_1_NEU.txt'
with open("Results_E11_E22_SEC_PT_1_NEU.txt", "w") as file:
    sorted_regions = sorted(merged_regions_sec_pt_1, key=lambda x: x['Region'])
    for i, region in enumerate(sorted_regions, start=1):
        file.write(f"Region: {i}\n")
        for element_line in region['Elements']:
            file.write(f"{element_line}\n")
        file.write("\n")


originalInpFileName = inp_filename
## Return data for Abaqus *.inp-files of the resulting regions
def replace_between_keywords(output_filename_inp):
    # Read content from the replacement file
    with open(output_filename, 'r') as replacement_file:
        replacement_content = replacement_file.read()

    # Read content from the source file
    with open(originalInpFileName+'.inp', 'r') as source_file:
        source_content = source_file.read()

    # Find the start and end positions of the region to be replaced
    start_keyword = '*Nset'
    end_keyword = '*End Part'
    start_index = source_content.find(start_keyword)
    end_index = source_content.find(end_keyword, start_index)

    # Check if both start and end keywords are found
    if start_index != -1 and end_index != -1:
        # Extract the content before and after the region to be replaced
        before_region = source_content[:start_index + len(start_keyword)]
        after_region = source_content[end_index:]

        # Combine the content with the replacement content
        new_content = before_region + replacement_content + "\n" + after_region

        # Write the result to the output file
        with open(output_filename_inp, 'w') as output_file:
            output_file.write(new_content)

        print("Replacement successful. Output written to", output_filename)
    else:
        print("Error: Couldn't find both start and end keywords in the source file.")

del inp_filename


# Data of combined regions
inp_filename = 'Results_E11_E22_SEC_PT_1_NEU.txt'
output_filename = 'Output_E11_E22_combined.txt'

# Open the *.txt file
with open(inp_filename, 'r') as file:
    lines = file.readlines()

output_content = []

current_region = None
elset_counter = 1
current_elements = []

# Extract the information of each region and write it to the output list
for line in lines:
    if 'Region:' in line:
        if current_region is not None:
            output_content.append(f"*Elset, elset=Region_{elset_counter}, generate")
            for element_number in current_elements:
                output_content.append(f"{element_number}, {element_number}, 1")
            output_content.append(f"*Shell Section, elset=Region_{elset_counter}, material=Aluminium")
            output_content.append("4., 5")
            output_content.append("")  # Empty line for clear distinguishing of the regions
            elset_counter += 1
            current_elements = []

        current_region = f"Region_{line.split()[-1]}"
    elif 'Element:' in line and current_region is not None:
        element_number = line.strip().split(',')[0].split()[-1]
        current_elements.append(element_number)

# Write information for the last region
if current_region is not None:
    output_content.append(f"*Elset, elset=Region_{elset_counter}, generate")
    for element_number in current_elements:
        output_content.append(f"{element_number}, {element_number}, 1")
    output_content.append(f"*Shell Section, elset=Region_{elset_counter}, material=Aluminium")
    output_content.append("4., 5")

# Save the information in the output file
with open(output_filename, 'w') as txt_file:
    txt_file.write(", nset=Section-Set, generate\n")
    txt_file.write(f"    1,  {max(unique_nodes)},     1\n")
    txt_file.write("*Elset, elset=Section-Set, generate\n")
    txt_file.write(f"    1,  {max(df_Elements_Nodes_Strains['Element'])},     1\n")
    txt_file.write("\n".join(output_content))

# Save the data into the form of an *.inp-file for Abaqus
output_filename_inp = originalInpFileName+'_E11_E22.inp'
replace_between_keywords(output_filename_inp)
os.replace(inp_folder + '\\' + output_filename_inp, result_folder + '\\' + output_filename_inp)

del inp_filename, output_filename, lines, output_content, current_region, elset_counter, current_elements
del line, element_number, txt_file

# Data of E11 regions
inp_filename = 'result_e11_sec_pt_1.txt'
output_filename = 'Output_E11.txt'

# Open the *.txt file
with open(inp_filename, 'r') as file:
    lines = file.readlines()

output_content = []

current_region = None
elset_counter = 1
current_elements = []

# Extract the information of each region and write it to the output list
for line in lines:
    if 'Region:' in line:
        if current_region is not None:
            output_content.append(f"*Elset, elset=Region_{elset_counter}, generate")
            for element_number in current_elements:
                output_content.append(f"{element_number}, {element_number}, 1")
            output_content.append(f"*Shell Section, elset=Region_{elset_counter}, material=Aluminium")
            output_content.append("4., 5")
            output_content.append("")  # Empty line for clear distinguishing of the regions
            elset_counter += 1
            current_elements = []

        current_region = f"Region_{line.split()[-1]}"
    elif 'Element:' in line and current_region is not None:
        element_number = line.strip().split(',')[0].split()[-1]
        current_elements.append(element_number)

# Write information of the regions into the format required in the *.inp-file
if current_region is not None:
    output_content.append(f"*Elset, elset=Region_{elset_counter}, generate")
    for element_number in current_elements:
        output_content.append(f"{element_number}, {element_number}, 1")
    output_content.append(f"*Shell Section, elset=Region_{elset_counter}, material=Aluminium")
    output_content.append("4., 5")

# Save information in an Output-file
with open(output_filename, 'w') as txt_file:
    txt_file.write(", nset=Section-Set, generate\n")
    txt_file.write(f"    1,  {max(unique_nodes)},     1\n")
    txt_file.write("*Elset, elset=Section-Set, generate\n")
    txt_file.write(f"    1,  {max(df_Elements_Nodes_Strains['Element'])},     1\n")
    txt_file.write("\n".join(output_content))

# Save the data into the form of an *.inp-file for Abaqus
output_filename_inp = originalInpFileName+'_E11.inp'
replace_between_keywords(output_filename_inp)
os.replace(inp_folder + '\\' + output_filename_inp, result_folder + '\\' + output_filename_inp)

del inp_filename, output_filename, lines, output_content, current_region, elset_counter, current_elements
del line, element_number, txt_file

# Data of E22 regions
inp_filename = 'result_e22_sec_pt_1.txt'
output_filename = 'Output_E22.txt'

# Open the *.txt file
with open(inp_filename, 'r') as file:
    lines = file.readlines()

output_content = []

current_region = None
elset_counter = 1
current_elements = []

# Extract the information of each region and write it to the output list
for line in lines:
    if 'Region:' in line:
        if current_region is not None:
            output_content.append(f"*Elset, elset=Region_{elset_counter}, generate")
            for element_number in current_elements:
                output_content.append(f"{element_number}, {element_number}, 1")
            output_content.append(f"*Shell Section, elset=Region_{elset_counter}, material=Aluminium")
            output_content.append("4., 5")
            output_content.append("")  # Empty line for clear distinguishing of the regions
            elset_counter += 1
            current_elements = []

        current_region = f"Region_{line.split()[-1]}"
    elif 'Element:' in line and current_region is not None:
        element_number = line.strip().split(',')[0].split()[-1]
        current_elements.append(element_number)

# Write information of the regions into the format required in the *.inp-file
if current_region is not None:
    output_content.append(f"*Elset, elset=Region_{elset_counter}, generate")
    for element_number in current_elements:
        output_content.append(f"{element_number}, {element_number}, 1")
    output_content.append(f"*Shell Section, elset=Region_{elset_counter}, material=Aluminium")
    output_content.append("4., 5")

# Save information in an Output-file
with open(output_filename, 'w') as txt_file:
    txt_file.write(", nset=Section-Set, generate\n")
    txt_file.write(f"    1,  {max(unique_nodes)},     1\n")
    txt_file.write("*Elset, elset=Section-Set, generate\n")
    txt_file.write(f"    1,  {max(df_Elements_Nodes_Strains['Element'])},     1\n")
    txt_file.write("\n".join(output_content))

# Save the data into the form of an *.inp-file for Abaqus
output_filename_inp = originalInpFileName+'_E22.inp'
replace_between_keywords(output_filename_inp)
os.replace(inp_folder + '\\' + output_filename_inp, result_folder + '\\' + output_filename_inp)

del inp_filename, output_filename, lines, output_content, current_region, elset_counter, current_elements
del line, element_number, txt_file

# Delete files with no further use
#os.unlink('result_e11_sec_pt_1.txt')
#os.unlink('result_e12_sec_pt_1.txt')
#os.unlink('result_e22_sec_pt_1.txt')
#os.unlink('Results_E11_E22_SEC_PT_1.txt')
#os.unlink('Results_E11_E22_SEC_PT_1_NEU.txt')
#os.unlink('Output_E11.txt')
#os.unlink('Output_E22.txt')
#os.unlink('Output_E11_E22_combined.txt')

os.chdir(directory)
