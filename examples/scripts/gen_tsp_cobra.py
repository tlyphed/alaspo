import os
import string

submit_template = '''
executable              = ${executable} 
input                   = /dev/null
arguments               = ${arguments}
log                     = ${submit_log}
output                  = ${output_log}
error                   = ${output_log}
should_transfer_files   = Yes
when_to_transfer_output = ON_EXIT
request_cpus            = 1
request_memory          = ${request_memory}
requirements            = (TARGET.Machine != "cobra-node03.kr.tuwien.ac.at")

queue 
'''

def create_sub_string(executable, arguments, submit_log, output_log, request_memory):
    t = string.Template(submit_template)
    return t.substitute(executable=executable, arguments=arguments, submit_log=submit_log, output_log=output_log, request_memory=request_memory)

submit_log = 'tsp_submit.log'

program_path = os.path.abspath('../tsp/tsp.lp')
script_path = os.path.abspath('../../src/clingo-lns.py')
n_runs = 5
mem_limit = 20480

configs = {
    #'baseline': "-gt 300 -mt 5 -r 0.7",
    #'reverse': "-gt 300 -mt 5 -r 0.3",
    'random': "-gt 300 -mt 5 -c ../../examples/configs/default.json",
    'roulette': "-gt 300 -mt 5 -c ../../examples/configs/roulette.json",
}

sub = ''
        
for config_name, config_args in configs.items():   
    for instance in os.scandir('../tsp/instances/'):
        if instance.path.endswith('.asp') or instance.path.endswith('.lp'):
            for r in range(n_runs):
                log_folder = '../tsp/logs/%s/run%i' % (config_name, r)
                os.makedirs(log_folder, exist_ok=True)
                arguments = script_path
                arguments += ' -i %s %s ' % (program_path, os.path.abspath(instance.path))
                arguments += config_args
                sub += create_sub_string(os.path.abspath('./run_python.sh'), arguments, submit_log, os.path.abspath(log_folder) + '/' + instance.name + '.out', mem_limit)
                sub += '\n'

with open('tsp.sub', 'w') as file:
    file.write(sub)
