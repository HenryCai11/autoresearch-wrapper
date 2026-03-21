# AutoResearch Wrapper Features

As said in its name, this skill implements wrappers over parts in a repo that are optimizable. I want to keep all the things simple, so let's just define simple things.

1. For parts (probly modules) that codex think are optimizable should be in one of the following situations/status:
    1. surely optimizable, which means it is clear how this part can be improved with all the things clear, i.e., candidates and metrics
    2. probably optimizable, which means there may be candidates but several parts are unclear, e.g., the metric is unclear
2. Before jumping into an optimization loop, remember to
    1. make sure everything's clear, e.g., status of eahc part and so on


maybe:
- `/autoresearch-wrapper` understands the repo structure and list the situation/status of each part, and then wait for user's choice of which part to optimize
    - once the part has been decided and everything is clear, i.e.
        - parts for optimization
        - metrics for each part
        - run sequentially or in parallel
        - number of rounds, time? metric? or by certain rules
        then write corresponding run scripts, test and run
    - this command should be as interactive as possible
- `/autoresearch-wrapper:status` shows the status