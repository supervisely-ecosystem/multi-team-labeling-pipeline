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
from typing import Optional, Dict
from supervisely.app.singleton import Singleton
from supervisely.api.user_api import UserInfo

ACTIVE_STEPS = [1]
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
        self._active = self.step_number in ACTIVE_STEPS
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
        if not self.active:
            self.confirm_button.disable()

        self.summary_text = Text()

        @self.confirm_button.click
        def validate_on_click():
            res = self.validate_inputs()
            if res:
                next_step = self.step_number + 1
                sly.logger.info(
                    f"Workflow Step {self.step_number} validated successfully. "
                    f"Proceeding to Step {next_step}."
                )
                # self.active = False # TODO: Replace text button.
                Workflow().set_active_step(next_step)

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

    @property
    def active(self) -> bool:
        """Check if the workflow step is active.

        :return: True if the step is active, False otherwise.
        :rtype: bool
        """
        return self._active

    @active.setter
    def active(self, value: bool) -> None:
        """Set the active status of the workflow step.

        :param value: True to activate the step, False to deactivate.
        :type value: bool
        """
        print("--------------------------------")
        self._active = value
        if value:
            self.confirm_button.enable()
            sly.logger.info(f"Workflow Step {self.step_number} is now active.")
        else:
            self.confirm_button.disable()

    def validate_inputs(self) -> bool:
        """Validate all required inputs and display appropriate feedback.

        :return: True if all inputs are valid, False otherwise.
        :rtype: bool
        """
        self.summary_text.text = ""
        errors = []

        # Validate workspace selection
        workspace_id = self.workspace_selector.get_selected_id()
        sly.logger.debug(f"Validating workspace ID: {workspace_id}")
        if not workspace_id:
            errors.append("Workspace is not selected")

        # Validate class selection
        selected_classes = self.class_selector.get_selected_class()
        sly.logger.debug(f"Selected classes: {[cls.name for cls in selected_classes]}")
        if not selected_classes:
            errors.append("At least one class must be selected")

        # Validate reviewer selection
        selected_reviewers = self.reviewer_selector.get_selected_user()
        sly.logger.debug(
            f"Selected reviewers: {[user.login for user in selected_reviewers]}"
        )
        if not selected_reviewers:
            errors.append("At least one reviewer must be selected")

        # Validate labeler selection
        selected_labelers = self.labeler_selector.get_selected_user()
        sly.logger.debug(
            f"Selected labelers: {[user.login for user in selected_labelers]}"
        )
        if not selected_labelers:
            errors.append("At least one labeler must be selected")

        # Display validation results
        if errors:
            self.summary_text.text = ". ".join(errors) + "."
            self.summary_text.status = "error"
            return False

        summary = (
            f"Selected classes: {self.class_names_to_str(selected_classes)} | "
            f"Assigned reviewers: {self.user_logins_to_str(selected_reviewers)} | "
            f"Assigned labelers: {self.user_logins_to_str(selected_labelers)}"
        )

        self.summary_text.text = summary
        self.summary_text.status = "success"
        return True

    @staticmethod
    def user_logins_to_str(user_list: list[UserInfo]) -> str:
        """Convert a list of UserInfo objects to a comma-separated string of user logins.

        :param user_list: List of UserInfo objects.
        :type user_list: list[UserInfo]
        :return: Comma-separated string of user logins.
        :rtype: str
        """
        return ", ".join([user.login for user in user_list])

    @staticmethod
    def class_names_to_str(class_list: list[sly.ObjClass]) -> str:
        """Convert a list of ObjClass objects to a comma-separated string of class names.

        :param class_list: List of ObjClass objects.
        :type class_list: list[sly.ObjClass]
        :return: Comma-separated string of class names.
        :rtype: str
        """
        return ", ".join([cls.name for cls in class_list])

    @property
    def content(self) -> Optional[Widget]:
        return self._content


class Workflow(metaclass=Singleton):
    def __init__(self):
        self.steps: Dict[int, WorkflowStep] = {}
        widgets: list[Widget] = []
        for step_number in range(1, DEBUG_NUMBER_OF_TEAMS + 1):
            workflow_step = WorkflowStep(step_number)
            self.steps[step_number] = workflow_step
            if workflow_step.content:
                widgets.append(workflow_step.content)

        self.stepper = Stepper(
            titles=[f"Team {i}" for i in range(1, DEBUG_NUMBER_OF_TEAMS + 1)],
            widgets=widgets,
            active_step=1,
        )
        self._layout = Card(
            title="Multi-Team Labeling Workflow",
            content=Container(widgets=[self.stepper]),
        )

    def get_layout(self):
        return self._layout

    def set_active_step(self, step_number: int) -> None:
        """Set the active step in the workflow stepper.

        :param step_number: The step number to set as active.
        :type step_number: int
        """
        if step_number < 1 or step_number > DEBUG_NUMBER_OF_TEAMS:
            sly.logger.warning(f"Step number {step_number} is out of range.")
            return None
        sly.logger.info(f"Setting active workflow step to: {step_number}")
        self.stepper.set_active_step(step_number)
        self.steps[step_number].active = True
