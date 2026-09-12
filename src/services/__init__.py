"""Per-domain-task business logic, one module per implemented task.

Convention: a new domain task's own node function and any task-specific
constants/helpers go in their own src/services/<task_id>.py module, with
a matching tests/services/test_<task_id>.py. src/workflow.py only imports
the node function by name and wires it into the graph via
src/domain_tasks.py's registry -- it should never contain task-specific
business logic itself.
"""
