import supervisely as sly
from supervisely.app.widgets import (
    SelectTeam,
    SelectWorkspace,
    SelectUser,
    SelectClass,
    SelectTag,
    Container,
    Widget,
    Card,
    Button,
    Text,
    SelectProject,
    SelectDataset,
    Field,
    Flexbox,
)
import src.globals as g
from typing import Optional, Dict, Any
from supervisely.app.singleton import Singleton
from supervisely.api.user_api import UserInfo

MULTITEAM_LABELING_WORKFLOW_TITLE = "multi_team_labeling_workflow"

select_project = SelectProject(
    default_id=g.PROJECT_ID, workspace_id=g.WORKSPACE_ID, compact=True
)
select_dataset = SelectDataset(
    default_id=g.DATASET_ID, project_id=g.PROJECT_ID, compact=True
)
if g.DATASET_ID:
    sly.logger.info(f"Setting selected dataset ID: {g.DATASET_ID}")
    select_dataset.set_dataset_id(g.DATASET_ID)

save_workflow_button = Button(
    "",
    icon="zmdi zmdi-save",
    icon_gap=0,
    button_size="large",
)
reset_workflow_button = Button(
    "",
    icon="zmdi zmdi-close",
    icon_gap=0,
    button_type="info",
    # button_size="large",
    plain=True,
)
launch_workflow_button = Button(
    "Launch Workflow",
    button_type="success",
    # button_size="large",
    icon="zmdi zmdi-play",
    icon_gap=10,
)
launch_workflow_button.disable()

buttons_flexbox = Flexbox(
    widgets=[reset_workflow_button, save_workflow_button, launch_workflow_button],
    gap=0,
)

settings_card = Card(
    title="Settings",
    description="Select the project and dataset to configure the multi-team labeling workflow.",
    content=Container(widgets=[select_project, select_dataset]),
    content_top_right=buttons_flexbox,
)


def get_existing_workflow_config(project_id: int) -> Dict[int, Dict[str, Any]]:
    project_custom_data = g.api.project.get_custom_data(project_id)
    existing_workflow_config = project_custom_data.get(
        MULTITEAM_LABELING_WORKFLOW_TITLE, {}
    )
    return existing_workflow_config


@save_workflow_button.click
def save_workflow():
    project_id = select_project.get_selected_id()
    sly.logger.info(f"Selected project ID for saving workflow: {project_id}")
    dataset_id = select_dataset.get_selected_id()
    sly.logger.info(f"Selected dataset ID for saving workflow: {dataset_id}")
    if not project_id or not dataset_id:
        sly.logger.warning("Project or Dataset not selected. Cannot save workflow.")
        return

    project_custom_data = g.api.project.get_custom_data(project_id)
    existing_workflow_config = project_custom_data.get(
        MULTITEAM_LABELING_WORKFLOW_TITLE, {}
    )
    if not existing_workflow_config:
        sly.logger.info("No existing workflow configuration found. Creating new one.")

    workflow_data = Workflow().to_json()
    existing_workflow_config[dataset_id] = workflow_data
    project_custom_data[MULTITEAM_LABELING_WORKFLOW_TITLE] = existing_workflow_config
    g.api.project.update_custom_data(project_id, project_custom_data)
    sly.logger.info("Workflow configuration saved successfully.")


@select_dataset.value_changed
def on_dataset_change(dataset_id: int):
    sly.logger.info(f"Dataset changed to ID: {dataset_id}")
    project_id = select_project.get_selected_id()
    sly.logger.info(
        f"Loading workflow for Project ID: {project_id}, Dataset ID: {dataset_id}"
    )
    existing_workflow_config = get_existing_workflow_config(project_id)
    dataset_workflow_data = existing_workflow_config.get(str(dataset_id), {})
    if dataset_workflow_data:
        sly.logger.info("Existing workflow configuration found. Loading...")
        Workflow().from_json(dataset_workflow_data)
    else:
        sly.logger.info("No existing workflow configuration for this dataset.")


class WorkflowStep:

    def __init__(self, step_number: int):
        self.step_number = step_number
        self.team_id: Optional[int] = None
        self.workspace_id: Optional[int] = None
        self.team_id: Optional[int] = None
        self.project_id: Optional[int] = None
        self.dataset_id: Optional[int] = None
        self._content: Optional[Card] = None
        self._add_content()

    def to_json(self) -> Dict[str, Any]:
        selected_classes = self.class_selector.get_selected_class() or []
        classes_json = [sly_class.to_json() for sly_class in selected_classes]
        reviewer_ids = [user.id for user in self.reviewer_selector.get_selected_user()]
        labeler_ids = [user.id for user in self.labeler_selector.get_selected_user()]
        data = {
            "step_number": self.step_number,
            "team_id": self.team_id,
            "workspace_id": self.workspace_id,
            "project_id": self.project_id,
            "dataset_id": self.dataset_id,
            "selected_classes": classes_json,
            "reviewer_ids": reviewer_ids,
            "labeler_ids": labeler_ids,
        }
        return data

    def update_from_json(self, data: Dict[str, Any]) -> None:
        self.step_number = data.get("step_number")
        self.team_id = data.get("team_id")
        self.workspace_id = data.get("workspace_id")
        self.project_id = data.get("project_id")
        self.dataset_id = data.get("dataset_id")
        sly.logger.info(
            f"Updating Workflow Step {self.step_number} from JSON data."
            f"Team ID: {self.team_id}, Workspace ID: {self.workspace_id}, "
            f"Project ID: {self.project_id}, Dataset ID: {self.dataset_id}"
        )
        self.workspace_selector.set_ids(self.team_id, self.workspace_id)
        classes_json = data.get("selected_classes", [])
        classes = [sly.ObjClass.from_json(cls_json) for cls_json in classes_json]
        class_names = [cls.name for cls in classes]
        self.class_selector.set(classes)
        self.class_selector.set_value(class_names)
        reviewer_ids = data.get("reviewer_ids", [])
        labeler_ids = data.get("labeler_ids", [])
        self.reviewer_selector.set_team_id(self.team_id)
        self.labeler_selector.set_team_id(self.team_id)
        self.reviewer_selector.set_selected_users_by_ids(reviewer_ids)
        self.labeler_selector.set_selected_users_by_ids(labeler_ids)

    def _add_content(self) -> None:
        self.team_selector = SelectTeam(show_label=False)
        team_field = Field(
            self.team_selector,
            title="Team",
        )
        self.workspace_selector = SelectWorkspace(compact=True, show_label=False)
        workspace_field = Field(
            self.workspace_selector,
            title="Workspace",
        )

        team_workspace_flexbox = Flexbox(
            [team_field, workspace_field],
        )

        self.class_selector = SelectClass(multiple=True)
        class_field = Field(
            self.class_selector,
            title="Classes",
        )

        self.tag_selector = SelectTag(multiple=True)
        tag_field = Field(
            self.tag_selector,
            title="Tags",
        )

        class_tag_flexbox = Flexbox(
            [class_field, tag_field],
        )

        self.reviewer_selector = SelectUser(
            roles=["annotator", "reviewer", "manager"], multiple=True
        )
        reviewer_field = Field(
            self.reviewer_selector,
            title="Reviewers",
        )

        self.labeler_selector = SelectUser(
            roles=["annotator", "reviewer"], multiple=True
        )
        labeler_field = Field(
            self.labeler_selector,
            title="Labelers",
        )

        users_container = Flexbox(
            [reviewer_field, labeler_field],
        )

        self.summary_text = Text()

        @self.workspace_selector.value_changed
        def on_selection_change(workspace_id: int):
            team_id = self.workspace_selector.get_team_id()
            self.reviewer_selector.set_team_id(team_id)
            self.labeler_selector.set_team_id(team_id)

            self.team_id = team_id
            self.workspace_id = workspace_id
            sly.logger.info(
                f"Workflow Step {self.step_number} - "
                f"Selected Team ID: {team_id}, Workspace ID: {workspace_id}"
            )

        content = Container(
            widgets=[
                team_workspace_flexbox,
                users_container,
                class_tag_flexbox,
                self.summary_text,
            ],
        )

        self._content = Card(
            title=f"Workflow step for Team {self.step_number}",
            content=content,
        )

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
    def content(self) -> Optional[Card]:
        return self._content


class Workflow(metaclass=Singleton):
    def __init__(self):
        self.steps: Dict[int, WorkflowStep] = {}
        widgets: list[Card] = []
        for step_number in range(1, g.NUMBER_OF_TEAMS + 1):
            workflow_step = WorkflowStep(step_number)
            self.steps[step_number] = workflow_step
            if workflow_step.content:
                widgets.append(workflow_step.content)

        self._layout = Container(
            widgets=widgets,
        )

    def to_json(self) -> Dict[int, Dict[str, Any]]:
        data = {}
        for step_number, workflow_step in self.steps.items():
            data[step_number] = workflow_step.to_json()
        return data

    def from_json(self, data: Dict[int, Dict[str, Any]]) -> None:
        sly.logger.info(f"Loading {len(data)} workflow steps from JSON data.")
        for step_number, step_data in data.items():
            step_number = int(step_number)
            if step_number in self.steps:
                sly.logger.info(f"Loading data for Workflow Step {step_number}")
                self.steps[step_number].update_from_json(step_data)

    def get_layout(self):
        return Container(widgets=[settings_card, self._layout])
