"""
doit-related helper functions.
"""

from typing import List
from scripts.dodolib._types import TaskFuncT, ActionT


def actions_of(*task_funcs: TaskFuncT) -> List[ActionT]:
    """Extract, stack together and return all actions of given task functions.

    :param task_funcs: list - task functions to extract actions from
    :return: list - all stacked actions
    """
    result: list = []
    for task_fn in task_funcs:
        result.extend(task_fn()['actions'])
    return result
