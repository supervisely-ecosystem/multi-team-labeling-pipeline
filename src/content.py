import supervisely as sly
from supervisely.app.widgets import (
    SelectWorkspace,
    SelectUser,
    SelectClass,
    Container,
    Widget,
    Card,
    Stepper,
    Button,
    Text,
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
        self.class_selector = SelectClass(multiple=True)
        self.reviewer_selector = SelectUser(
            roles=["annotator", "reviewer", "manager"], multiple=True
        )
        self.labeler_selector = SelectUser(
            roles=["annotator", "reviewer"], multiple=True
        )

        self.confirm_button = Button("Confirm Selection")

        self.summary_text = Text()

        @self.confirm_button.click
        def validate_on_click():
            self.validate_inputs()

        @self.workspace_selector.value_changed
        def on_workspace_change(workspace_id: int):
            team_id = self.workspace_selector.get_team_id()
            self.reviewer_selector.set_team_id(team_id)
            self.labeler_selector.set_team_id(team_id)

        self._content = Container(
            widgets=[
                self.workspace_selector,
                self.class_selector,
                self.reviewer_selector,
                self.labeler_selector,
                self.summary_text,
                self.confirm_button,
            ],
            # direction="horizontal",
        )

    def validate_inputs(self) -> bool:
        self.summary_text.text = ""
        text = ""
        workspace_id = self.workspace_selector.get_selected_id()
        print("Validating inputs for workspace ID:", workspace_id)
        if not workspace_id:
            text += "Workspace is not selected. "
        selected_classes = self.class_selector.get_selected_class()
        print("Selected classes:", [cls.name for cls in selected_classes])
        if not selected_classes:
            text += "At least one class must be selected. "
        selected_reviewers = self.reviewer_selector.get_selected_user()
        print("Selected reviewers:", [user.login for user in selected_reviewers])
        if not selected_reviewers:
            text += "At least one reviewer must be selected. "
        selected_labelers = self.labeler_selector.get_selected_user()
        print("Selected labelers:", [user.login for user in selected_labelers])
        if not selected_labelers:
            text += "At least one labeler must be selected. "
        if text:
            self.summary_text.text = text
            self.summary_text.status = "error"
            return False
        summary = (
            f"The following classes were selected: {', '.join([cls.name for cls in selected_classes])}. "
            f"Selected reviewers: {', '.join([user.login for user in selected_reviewers])}. "
            f"Selected labelers: {', '.join([user.login for user in selected_labelers])}."
        )
        self.summary_text.text = summary
        self.summary_text.status = "success"
        return True

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
            title="Multi-Team Labeling Workflow",
            content=Container(widgets=[stepper]),
        )

    def get_layout(self):
        return self._layout
