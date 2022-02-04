import os
import sys

import pandas as pd

results = {}
if __name__ == "__main__":
    root_folder = sys.argv[1]
    for config_folder in os.scandir(root_folder):
        results[config_folder.name] = []
        config_results = {}
        for run_folder in os.scandir(config_folder):
            for log in os.scandir(run_folder):
                with open(log.path, 'r') as file:
                    instance_name = log.name.split('.')[0]
                    with open(log.path, 'r') as file:
                        last_line = file.readlines()[-1]
                        if last_line.startswith('Costs:'):
                            objective = int(last_line.split(':')[1])
                        # else:
                        #     objective = None
                            if log.name not in config_results:
                                config_results[log.name] = [objective]
                            else:
                                config_results[log.name] = config_results[log.name] + [objective]  
                                
                                            
        for instance in config_results:
            try:
                maximum = max(config_results[instance])
                minimum = min(config_results[instance])
                average = sum(config_results[instance])/len((config_results[instance]))
            except:
                maximum = None
                minimum = None
                average = None
                
            
            
            results[config_folder.name] = results[config_folder.name] + [(instance, (average, minimum, maximum))]

instances = []
for config in results:
    for result in results[config]:
        if result[0].split('.')[0] not in instances:
            instances.append(result[0].split('.')[0])

for config in results:
    results[config] = [(average, minimum, maximum) for (_, (average, minimum, maximum)) in results[config]]

#pd.set_option("display.max_rows", None, "display.max_columns", None)
df = pd.DataFrame(data=results, index=instances)
print(df)
