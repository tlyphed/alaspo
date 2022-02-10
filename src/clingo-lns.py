import random
import sys
import os
import argparse
import signal
from collections import namedtuple
import solver
from lns import ClingoLNS
import initial
import strategy
import config
import json_config
import relax
import search
logger = config.setup_logger('root')


def print_model(atoms):
    for a in atoms:
        print(a, end=' ')
    print(" ")


def main(program, initial_operator, relax_operators, search_operators, strategy, internal_solver, global_timeout):
    solver = ClingoLNS(internal_solver, program, initial_operator, relax_operators, search_operators, strategy)

    solution = solver.solve(global_timeout)
    if solution is not None:
        print_model(solution.model.shown)
        print("Costs: " + str(solution.cost))
    else:
        print("No solution found!")


if __name__ == '__main__':

    def signal_handler(sig, frame):
        sys.stderr.flush()
        sys.stdout.flush()
        input('Search interrupted! Press ENTER to continue ...')

        # print('Search interrupted!')
        # if vlns.best_solution is not None:
        #    print_model(vlns.best_solution.atoms)
        #    print("Costs: " + str(vlns.best_solution.cost))
        # else:
        #     print("No solution found!")
        # sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)


    def existing_files(argument):
        if os.path.exists(argument) and os.path.isfile(argument):
            return argument
        else:
            raise argparse.ArgumentTypeError('File not found!')

    def valid_rate(argument):
        argument = float(argument)
        if 0 <= argument <= 1:
            return argument
        else:
            raise argparse.ArgumentTypeError('0 <= <n> <= 1 required!')

    def valid_quick_config(argument):
        conf = argument.split(',')
        if len(conf) != 3:
            raise argparse.ArgumentTypeError('config string is not correct!')
        rate = float(conf[1])
        if not (0 <= rate <= 1):
            raise argparse.ArgumentTypeError('0 <= rate <= 1 required!')
        
        time = int(conf[2])
        if not (0 < time):
            raise argparse.ArgumentTypeError('timeout > 0 required!')
        
        return argument

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter, description='ASP + Large-Neighborhood Search')

    parser.add_argument('-i', '--input', type=existing_files, metavar='file', default=None, nargs='+',
                        help='input ASP files')

    parser.add_argument('-gt', '--time-limit', type=int, metavar='<n>', default=300,
                        help='time limit for the lns search')

    group = parser.add_mutually_exclusive_group()

    group.add_argument("-c", "--config-file", type=existing_files, metavar='<file>',
                        help='the config file specifying the relax and search operators')

    group.add_argument("-q", "--quick-config", type=valid_quick_config, metavar='<config>',
                        help='a config string containing a neighborhood type ("randomAtoms", "randomConstaints" or "declarative"), a relaxation rate, and a move timeout seperated by comma')

    parser.add_argument('-st', '--solver-type', type=str, choices=['clingo', 'clingo-dl', 'clingcon'],
                        metavar='<arg>', default='clingo',
                        help='the ASP solver ("clingo", "clingo-dl", "clingcon") to be used')

    parser.add_argument('-mv', '--minimize-variable', type=str, metavar='<var>', default=None,
                        help='an integer variable to minimize (only useful with solver type "clingo-dl")')

    parser.add_argument('-sa', '--solver-arguments', type=str, metavar='<args>', default='',
                        help='command-line argument string for the ASP solver ' 
                             '(separated by space)')

    parser.add_argument('-pt', '--pre-optimize-timeout', type=int, metavar='<n>', default=0,
                        help='let ASP solver optimize for <n> seconds before lns loop starts')

    parser.add_argument('-sd', '--seed', type=int, metavar='SEED', default=None,
                        help='seed for random numbers')

    parser.add_argument('-f', '--forget-on-shot', action='store_true',
                        help='whether or not the previous state should be forgotten on each new lns iteration')
    parser.set_defaults(forget_on_shot=False)

   
    args = parser.parse_args()

    if args.seed is None:
        seed_value = random.randrange(sys.maxsize)
    else:
        seed_value = args.seed

    logger.info('Seed value: %i' % seed_value)

    random.seed(seed_value)

    parsed_options = None
    if args.solver_arguments:
        parsed_options = args.solver_arguments.split(' ')

    program = ''
    if args.input is not None:
        for asp_file in args.input:
            with open(asp_file, 'r') as f:
                program += f.read()
    else:
        program += sys.stdin.read()

    internal_solver = None
    if args.solver_type == 'clingo':
        internal_solver = solver.Clingo(options=parsed_options, seed=seed_value, forget_on_shot=args.forget_on_shot)
    elif args.solver_type == 'clingo-dl':
        internal_solver = solver.ClingoDl(options=parsed_options, minimize_variable=args.minimize_variable,
                                          seed=seed_value, forget_on_shot=args.forget_on_shot)
    elif args.solver_type == 'clingcon':
        internal_solver = solver.Clingcon(options=parsed_options, seed=seed_value, forget_on_shot=args.forget_on_shot)
    else:
        assert False, "Not a valid solver type!"

    initial_operator = initial.ClingoInitialOperator(internal_solver, args.time_limit,
                                                     pre_opt_time=args.pre_optimize_timeout)

    strat = None
    relax_operators = None
    search_operators = None

    if args.config_file != None:
        with open(args.config_file, 'r') as f:
            con = f.read()
            strat, relax_operators, search_operators = json_config.parse_config(con, internal_solver)
    elif args.quick_config != None:
        conf_string = args.quick_config.split(',')
        op_name = conf_string[0].strip()
        rate = float(conf_string[1].strip())
        mt = int(conf_string[2].strip())

        strat = strategy.RandomStrategy(supports_intensification=True)
        relax_operators = [ relax.get_operator(op_name, { 'sizes': [ rate ] }) ]
        search_operators = [ search.get_operator('default', { 'timeouts': [ mt ] }, internal_solver) ]
    else:
        strat, relax_operators, search_operators = json_config.parse_config(json_config.DEFAULT_CONFIG, internal_solver)

    main(
        program=program,
        initial_operator=initial_operator,
        relax_operators=relax_operators,
        search_operators=search_operators,
        strategy=strat,
        internal_solver=internal_solver,
        global_timeout=args.time_limit
    )
