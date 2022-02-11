# ALASPO

An (adaptive) LNS framework for the for ASP systems. Currently, the system only supports solvers based on [clingo](https://potassco.org/). 

The folder `src` contains the LNS implementation as well as simple problem-independent relaxation operators and adaption strategies. 
Examples for portfolio config files can be found in the èxamples` folder.

It should work out-of-the-box in a conda env after running the following command:
```
conda install -c potassco/label/dev clingo clingo-dl clingcon
```

The command-line options of the problem-independent LNS can be shown as follows:
```
python src/clingo-lns.py -h
```


This software is distributed under the [MIT License](./LICENSE.md).
