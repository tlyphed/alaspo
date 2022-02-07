
import json
import strategy
import relax
import search
import solver

DEFAULT_CONFIG = """
{
    "strategy": "random",
    "relaxOperators": [
        {
            "type": "randomAtoms",
            "sizes": [ 0.2, 0.4, 0.6, 0.8 ],
            "initialSize": 0.2
        },
        {
            "type": "randomConstants",
            "sizes": [ 0.1, 0.2, 0.3, 0.5 ],
            "initialSize": 0.2
        }
    ],
    "searchOperators": [
        {
            "type": "default",
            "timeouts": [ 5, 15, 30 ],
            "initialTimeout": 15,
            "solverArguments": ""
        }
    ]
}
"""

def parse_config(config, internal_solver):
    json_config = json.loads(config)
    strategy_op = strategy.get_strategy(json_config['strategy'])
    
    relax_operators = []
    for json_relax in json_config['relaxOperators']:
        relax_type = json_relax['type']
        relax_args = { k:v for k,v in json_relax.items() if k != 'type' }
        relax_operators += [ relax.get_operator(relax_type, relax_args) ]

    search_operators = []
    for json_search in json_config['searchOperators']:
        search_type = json_search['type']
        search_args = { k:v for k,v in json_search.items() if k != 'type' }
        search_operators += [ search.get_operator(search_type, search_args, internal_solver) ]

    return strategy_op, relax_operators, search_operators

