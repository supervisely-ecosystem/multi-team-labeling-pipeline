import supervisely as sly
from supervisely.app.widgets import (
    SelectWorkspace,
    Select,
    ClassesListSelector,
    Container,
    Widget,
    Card,
    Stepper,
)
from typing import Optional
from supervisely.app.singleton import Singleton

DEBUG_NUMBER_OF_TEAMS = 8


class WorkflowStep:

    def __init__(self, step_number: int):
        self.step_number = step_number
        self.team_id: Optional[int] = None
        self.workspace_id: Optional[int] = None
        self.team_id: Optional[int] = None
        self.project_id: Optional[int] = None
        self.dataset_id: Optional[int] = None
        self._content: Optional[Widget] = None
        self._add_content()

    def _add_content(self) -> None:

        self.workspace_selector = SelectWorkspace()
        self.class_selector = ClassesListSelector(multiple=True)
        self.reviewer_selector = Select([], multiple=True)
        self.labler_selector = Select([], multiple=True)

        self._content = Container(
            widgets=[
                self.workspace_selector,
                self.class_selector,
                self.reviewer_selector,
                self.labler_selector,
            ],
            # direction="horizontal",
        )

    @property
    def content(self) -> Optional[Widget]:
        return self._content


class Workflow(metaclass=Singleton):
    def __init__(self):
        content: list[Widget] = []
        for step_number in range(1, DEBUG_NUMBER_OF_TEAMS + 1):
            workflow_step = WorkflowStep(step_number)
            workflow_content = workflow_step.content
            if workflow_content:
                content.append(workflow_content)

        stepper = Stepper(
            titles=[f"Team {i}" for i in range(1, DEBUG_NUMBER_OF_TEAMS + 1)],
            widgets=content,
            active_step=1,
        )
        self._layout = Card(
            title="Multi-Team Labeling Workflow", content=Container(widgets=[stepper])
        )

    def get_layout(self):
        return self._layout
