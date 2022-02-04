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

submit_log = 'wsc_submit.log'

program_path = os.path.abspath('../weighted_strategic_companies/weighted_strategic_companies.lp')
script_path = os.path.abspath('../../clingo-lns.py')
n_runs = 5
mem_limit = 20480

configs = {
    'baseline' : '-gt 180 -mt 30 -r 0.8',
    'reverse' : '-gt 180 -mt 30 -r 0.2',
    'random' : '-gt 180 -mt 30',
    'reinforce' : '-gt 180 -mt 30 -aa RL',
}

sub = ''
        
for config_name, config_args in configs.items():   
    for instance in os.scandir('../weighted_strategic_companies/instances/weighted_instances/'):
        if instance.path.endswith('.asp') or instance.path.endswith('.lp'):
            for r in range(n_runs):
                log_folder = '../weighted_strategic_companies/logs/%s/run%i' % (config_name, r)
                os.makedirs(log_folder, exist_ok=True)
                arguments = script_path
                arguments += ' -i %s %s ' % (program_path, os.path.abspath(instance.path))
                arguments += config_args
                sub += create_sub_string(os.path.abspath('./run_python.sh'), arguments, submit_log, os.path.abspath(log_folder) + '/' + instance.name + '.out', mem_limit)
                sub += '\n'

with open('wstratcomp.sub', 'w') as file:
    file.write(sub)
