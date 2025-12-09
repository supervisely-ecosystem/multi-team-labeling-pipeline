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
    Empty,
    Modal,
    ActivityFeed,
    Checkbox,
)
import src.globals as g
from typing import Optional, Dict, Any, List, Tuple
from supervisely.app.singleton import Singleton
from supervisely.api.user_api import UserInfo
from supervisely.api.labeling_queue_api import LabelingQueueInfo
from time import sleep
import threading


class WorkflowSettings(metaclass=Singleton):
    PROJECT_INFO: Optional[sly.ProjectInfo] = None
    DATASET_INFO: Optional[sly.DatasetInfo] = None

    def get_project_name(self) -> Optional[str]:
        if self.PROJECT_INFO:
            return self.PROJECT_INFO.name
        return None

    def get_dataset_name(self) -> Optional[str]:
        if self.DATASET_INFO:
            return self.DATASET_INFO.name
        return None


MULTITEAM_LABELING_WORKFLOW_TITLE = "multi_team_labeling_workflow"
MULTITEAM_LABELING_WORKFLOW_MARKER = "MTLWQ"
WAIT_TIME = 5  # seconds
MONITORING_INTERVAL = 10  # seconds between checks

RESET_ICON = "zmdi zmdi-close"
UPDATE_ICON = "zmdi zmdi-refresh"


class WorkflowMonitor(metaclass=Singleton):
    """Manages background monitoring of workflow status."""

    def __init__(self):
        self.active = False
        self.thread = None

    def start(self):
        """Start the monitoring loop."""
        if self.active:
            self.stop()

        sly.logger.info("Starting workflow monitoring")
        update_workflow_status()

        self.active = True
        self.thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop the monitoring loop."""
        if not self.active:
            return

        sly.logger.info("Stopping workflow monitoring")
        self.active = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)
        sly.logger.info("Workflow monitoring stopped")

    def _monitoring_loop(self):
        """Background loop that periodically updates workflow status."""
        while self.active:
            try:
                update_workflow_status()
                sly.logger.debug(f"Status updated, waiting {MONITORING_INTERVAL}s")

                # Sleep in small increments to allow quick stop
                for _ in range(MONITORING_INTERVAL):
                    if not self.active:
                        break
                    sleep(1)
            except Exception as e:
                sly.logger.error(f"Error in monitoring loop: {e}")
                sleep(MONITORING_INTERVAL)


status_texts = {
    step_number: Text("Loading...") for step_number in range(1, g.NUMBER_OF_TEAMS + 1)
}

feed_items = {
    step_number: ActivityFeed.Item(
        content=status_texts[step_number],
        status="pending",
        number=step_number,
    )
    for step_number in range(1, g.NUMBER_OF_TEAMS + 1)
}

activity_feed = ActivityFeed(items=list(feed_items.values()))

workflow_modal = Modal("Workflow Overview", widgets=[activity_feed])

select_project = SelectProject(
    default_id=g.PROJECT_ID, workspace_id=g.WORKSPACE_ID, compact=True
)
select_dataset = SelectDataset(
    default_id=g.DATASET_ID, project_id=g.PROJECT_ID, compact=True
)
require_classes_checkbox = Checkbox(content="Classes labeling is required")
require_tags_checkbox = Checkbox(content="Tags labeling is required")

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
    content=Container(
        widgets=[
            select_project,
            select_dataset,
            require_classes_checkbox,
            require_tags_checkbox,
            workflow_modal,
        ]
    ),
    content_top_right=buttons_flexbox,
)


@reset_workflow_button.click
def reset_workflow():
    sly.logger.info(
        f"Reset/Update workflow button clicked. Icon: {reset_workflow_button.icon}"
    )
    if UPDATE_ICON in reset_workflow_button.icon:
        sly.logger.info("Update button clicked - refreshing workflow status.")
        update_dataset(select_dataset.get_selected_id())
        reset_workflow_button.icon = RESET_ICON
    elif RESET_ICON in reset_workflow_button.icon:
        sly.logger.info("Resetting workflow configuration via button click.")
        Workflow().reset_workflow()
        reset_workflow_button.icon = UPDATE_ICON


def get_existing_workflow_config(project_id: int) -> Dict[int, Dict[str, Any]]:
    project_custom_data = g.api.project.get_custom_data(project_id)
    existing_workflow_config = project_custom_data.get(
        MULTITEAM_LABELING_WORKFLOW_TITLE, {}
    )
    return existing_workflow_config


def process_workflow_step(
    step_number: int,
    step_dataset_info: Optional[sly.DatasetInfo],
    step_labeling_queue_info: Optional[LabelingQueueInfo],
    move_forward_needed: bool,
) -> Tuple[str, Optional[LabelingQueueInfo], bool]:
    """Process a single workflow step and return its status.

    Returns:
        Tuple of (item_status, updated_queue_info, new_move_forward_flag)
    """
    sly.logger.info(
        f"Step {step_number} - Dataset: {step_dataset_info.id if step_dataset_info else 'N/A'}, "
        f"Queue: {step_labeling_queue_info.name if step_labeling_queue_info else 'N/A'}, "
        f"Move forward: {move_forward_needed}"
    )

    # Handle existing labeling queue
    if step_labeling_queue_info:
        return handle_existing_queue(step_number, step_labeling_queue_info)

    # Handle missing labeling queue
    return handle_missing_queue(step_number, step_dataset_info, move_forward_needed)


def handle_existing_queue(
    step_number: int, queue_info: LabelingQueueInfo
) -> Tuple[str, LabelingQueueInfo, bool]:
    """Handle a step that already has a labeling queue."""
    queue_status = queue_info.status
    sly.logger.info(f"Step {step_number} queue status: {queue_status}")

    if queue_status == "completed":
        sly.logger.info(f"Step {step_number} completed - ready to move forward")
        return "completed", queue_info, True
    else:
        sly.logger.info(f"Step {step_number} in progress - waiting")
        return "in_progress", queue_info, False


def handle_missing_queue(
    step_number: int,
    dataset_info: Optional[sly.DatasetInfo],
    move_forward_needed: bool,
) -> Tuple[str, Optional[LabelingQueueInfo], bool]:
    """Handle a step that doesn't have a labeling queue yet."""
    # First step with existing dataset
    if dataset_info and step_number == 1:
        sly.logger.info(f"Step {step_number} - creating initial queue")
        queue_info = Workflow().steps[step_number].create_labeling_queue()
        if queue_info:
            sly.logger.info(f"Step {step_number} - queue created successfully")
            return "in_progress", queue_info, False
        return "pending", None, False

    # Subsequent steps waiting for previous completion
    if move_forward_needed:
        sly.logger.info(f"Step {step_number} - moving forward from previous step")
        queue_info = Workflow().steps[step_number].move_forward()
        if queue_info:
            sly.logger.info(f"Step {step_number} - moved forward successfully")
            return "in_progress", queue_info, False
        else:
            raise RuntimeError(f"Failed to move forward for Step {step_number}")

    return "pending", None, False


def update_step_display(
    step_number: int,
    dataset_info: Optional[sly.DatasetInfo],
    queue_info: Optional[LabelingQueueInfo],
    item_status: str,
) -> None:
    """Update the UI display for a workflow step."""
    dataset_id = str(dataset_info.id) if dataset_info else "N/A"
    queue_id = str(queue_info.id) if queue_info else "N/A"
    queue_status = queue_info.status if queue_info else "N/A"

    summary_text = (
        f"Dataset ID: {dataset_id} | "
        f"Queue ID: {queue_id} | "
        f"Status: {queue_status}"
    )

    status_texts[step_number].text = summary_text
    activity_feed.set_status(number=step_number, status=item_status)


def update_workflow_status():
    """Update workflow status for all steps."""
    move_forward_needed = False

    for step_number, (dataset_info, queue_info) in enumerate(
        Workflow().all_steps_queues(), start=1
    ):
        item_status, updated_queue_info, move_forward_needed = process_workflow_step(
            step_number, dataset_info, queue_info, move_forward_needed
        )

        update_step_display(
            step_number, dataset_info, updated_queue_info or queue_info, item_status
        )


@workflow_modal.value_changed
def handle_modal_state(is_open: bool):
    """Handle modal open/close events."""
    if is_open:
        WorkflowMonitor().start()
    else:
        WorkflowMonitor().stop()


@launch_workflow_button.click
def launch_workflow():
    """Launch the multi-team labeling workflow."""
    sly.logger.info("Launching workflow...")
    workflow_modal.show()


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


@select_project.value_changed
def on_project_change(project_id: int):
    select_dataset.set_project_id(project_id)
    update_dataset(select_dataset.get_selected_id())

    # Get project metadata from API
    project_meta_json = g.api.project.get_meta(project_id)
    project_meta = sly.ProjectMeta.from_json(project_meta_json)

    # Get step 1 to populate widgets for classes and tags
    workflow_step_1 = Workflow().steps.get(1)
    if workflow_step_1:
        workflow_step_1.team_selector.set_team_id(g.TEAM_ID)
        workflow_step_1.workspace_selector.set_ids(
            team_id=g.TEAM_ID, workspace_id=g.WORKSPACE_ID
        )
        # workflow_step_1.workspace_selector.enable()

        # Initialize user selectors with the team_id
        workflow_step_1.reviewer_selector.set_team_id(g.TEAM_ID)
        workflow_step_1.labeler_selector.set_team_id(g.TEAM_ID)

        # Set classes from project meta
        if project_meta.obj_classes:
            workflow_step_1.class_selector.set(list(project_meta.obj_classes))

        # Set tags from project meta
        if project_meta.tag_metas:
            workflow_step_1.tag_selector.set(list(project_meta.tag_metas))


@select_dataset.value_changed
def on_dataset_change(dataset_id: int):
    update_dataset(dataset_id)


def update_dataset(dataset_id: int):
    sly.logger.info(f"Dataset changed to ID: {dataset_id}")
    if not dataset_id:
        sly.logger.warning("No dataset selected. Cannot load workflow.")
        return
    project_id = select_project.get_selected_id()
    WorkflowSettings().PROJECT_INFO = g.api.project.get_info_by_id(project_id)
    WorkflowSettings().DATASET_INFO = g.api.dataset.get_info_by_id(dataset_id)
    sly.logger.info(
        f"Updated WorkflowSettings with Project name: {WorkflowSettings().PROJECT_INFO.name}, "
        f"Dataset name: {WorkflowSettings().DATASET_INFO.name}"
    )

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

    if Workflow().all_steps_filled():
        launch_workflow_button.enable()


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

    def is_filled(self) -> bool:
        # TODO: Refactor me
        if not self.team_selector.get_selected_id():
            return False
        if not self.workspace_selector.get_selected_id():
            return False
        if (
            not self.class_selector.get_selected_class()
            and require_classes_checkbox.is_checked()
        ):
            return False
        if (
            not self.tag_selector.get_selected_tag()
            and require_tags_checkbox.is_checked()
        ):
            return False
        if not self.reviewer_selector.get_selected_user():
            return False
        if not self.labeler_selector.get_selected_user():
            return False
        return True

    def is_dataset_exists(self) -> bool:
        team_id = self.team_selector.get_selected_id()
        if not team_id:
            sly.logger.warning("Cannot check dataset existence: team ID is missing.")
            return False

        self.team_id = team_id

        workspace_id = self.workspace_selector.get_selected_id()
        project_name = WorkflowSettings().get_project_name()
        if not workspace_id or not project_name:
            sly.logger.warning(
                "Cannot check dataset existence: workspace ID or project name is missing."
            )
            return False

        self.workspace_id = workspace_id
        project_info = g.api.project.get_info_by_name(workspace_id, project_name)
        if not project_info:
            sly.logger.info(
                f"Project {project_name} does not exist in workspace ID {workspace_id}."
            )
            return False

        self.project_id = project_info.id

        dataset_name = WorkflowSettings().get_dataset_name()
        if not dataset_name:
            sly.logger.warning(
                "Cannot check dataset existence: dataset name is missing."
            )
            return False
        dataset_info = g.api.dataset.get_info_by_name(project_info.id, dataset_name)
        if not dataset_info:
            sly.logger.info(
                f"Dataset {dataset_name} does not exist in project ID {project_info.id}."
            )
            return False

        self.dataset_id = dataset_info.id

        return True

    def create_labeling_queue(self) -> Optional[LabelingQueueInfo]:
        if not self.dataset_id:
            sly.logger.warning("Cannot create labeling queue: dataset ID is missing.")
            return None

        self.update_project_meta()
        sly.logger.info(
            f"Meta updated, creating labeling queue for Dataset ID {self.dataset_id}."
        )
        queue_name = self.get_labeling_queue_name()

        annotor_ids = [
            user.id for user in self.labeler_selector.get_selected_user() or []
        ]
        reviewer_ids = [
            user.id for user in self.reviewer_selector.get_selected_user() or []
        ]

        if not annotor_ids or not reviewer_ids:
            sly.logger.warning(
                "Cannot create labeling queue: annotator or reviewer IDs are missing."
            )
            return None

        queue_id = g.api.labeling_queue.create(
            name=queue_name,
            user_ids=annotor_ids,
            reviewer_ids=reviewer_ids,
            dataset_id=self.dataset_id,
            classes_to_label=[
                sly_class.name
                for sly_class in self.class_selector.get_selected_class() or []
            ],
            tags_to_label=[
                tag.name for tag in self.tag_selector.get_selected_tag() or []
            ],
            # TODO: Labeler sees figures: Edit only own (add to SDK).
        )
        queue_info = g.api.labeling_queue.get_info_by_id(queue_id)

        sly.logger.info(
            f"Labeling queue {queue_name} created successfully for Dataset ID {self.dataset_id}."
        )

        return queue_info

    def update_project_meta(self) -> None:
        if not self.project_id:
            sly.logger.warning("Cannot update project meta: project ID is missing.")
            return

        project_meta = sly.ProjectMeta.from_json(
            g.api.project.get_meta(self.project_id)
        )
        sly.logger.info(
            f"Updating project meta for project ID {self.project_id} in workflow step {self.step_number}."
        )

        selected_classes = self.class_selector.get_selected_class() or []
        for sly_class in selected_classes:
            if not project_meta.get_obj_class(sly_class.name):
                sly.logger.info(f"Adding class {sly_class.name} to project meta.")
                project_meta = project_meta.add_obj_class(sly_class)

        sly.logger.info(
            f"Added {len(selected_classes)} classes to project meta for project ID {self.project_id}."
        )

        selected_tags = self.tag_selector.get_selected_tag() or []
        for tag in selected_tags:
            if not project_meta.get_tag_meta(tag.name):
                sly.logger.info(f"Adding tag {tag.name} to project meta.")
                project_meta = project_meta.add_tag_meta(tag)

        sly.logger.info(
            f"Added {len(selected_tags)} tags to project meta for project ID {self.project_id}."
        )

        g.api.project.update_meta(self.project_id, project_meta.to_json())
        sly.logger.info(
            f"Project meta updated successfully for project ID {self.project_id}."
        )

    def move_forward(self) -> Optional[LabelingQueueInfo]:
        if not self.is_dataset_exists():
            sly.logger.info(
                "Dataset does not exist; copying dataset from previous step."
            )
            self.copy_dataset_from_previous_step()
            sly.logger.info(
                f"Waiting {WAIT_TIME} seconds for dataset to be available..."
            )
            sleep(WAIT_TIME)
            sly.logger.info("Rechecking dataset existence...")

        if not self.is_dataset_exists():
            sly.logger.warning(
                "Dataset still does not exist after attempting to copy from previous step."
            )
            return

        queue_info = self.create_labeling_queue()
        if queue_info:
            sly.logger.info(
                f"Labeling queue created for Workflow Step {self.step_number}: {queue_info}"
            )
            return queue_info
        else:
            sly.logger.warning(
                f"Failed to create labeling queue for Workflow Step {self.step_number}."
            )
            return

    def copy_dataset_from_previous_step(self) -> None:
        if self.step_number <= 1:
            sly.logger.info(
                "This is the first workflow step; no previous step to copy dataset from."
            )
            return
        previous_step = Workflow().steps.get(self.step_number - 1)
        workspace_id = self.workspace_selector.get_selected_id()
        if not previous_step or not workspace_id:
            sly.logger.warning(
                "Cannot copy dataset: previous step or current workspace ID is missing."
            )
            return

        previous_project_id = previous_step.project_id
        previous_dataset_id = previous_step.dataset_id
        if not previous_project_id or not previous_dataset_id:
            sly.logger.warning(
                "Cannot copy dataset: previous step's project ID or dataset ID is missing."
            )
            return

        dst_project_name = WorkflowSettings().get_project_name()
        dst_dataset_name = WorkflowSettings().get_dataset_name()

        sly.logger.info(
            f"Copying dataset ID {previous_dataset_id} from project ID {previous_project_id} "
            f"to workspace ID {workspace_id} with project name {dst_project_name} "
            f"and dataset name {dst_dataset_name} for workflow step {self.step_number}."
        )

        # Get the project meta from the previous step to copy classes and tags
        previous_project_meta_json = g.api.project.get_meta(previous_project_id)
        previous_project_meta = sly.ProjectMeta.from_json(previous_project_meta_json)

        # Create new project in the target workspace with the same type and meta
        new_project_info = g.api.project.create(
            workspace_id,
            dst_project_name,
        )
        new_project_id = new_project_info.id

        # Set the project meta (classes and tags)
        g.api.project.update_meta(new_project_id, previous_project_meta.to_json())

        # Copy the dataset to the new project
        new_dataset_info = g.api.dataset.copy(
            new_project_id,
            previous_dataset_id,
            new_name=dst_dataset_name,
            with_annotations=True,
        )

        # Update this step's project_id and dataset_id
        self.project_id = new_project_id
        if new_dataset_info:
            self.dataset_id = new_dataset_info.id

        sly.logger.info(
            f"Copied dataset ID {previous_dataset_id} from project ID {previous_project_id} "
            f"to new project ID {new_project_id} in workspace ID {workspace_id} "
            f"with name {dst_dataset_name} for workflow step {self.step_number}."
        )

    @staticmethod
    def is_labeling_queue_from_app() -> bool:
        pass

    def get_labeling_queue_name(self) -> str:
        return (
            f"{MULTITEAM_LABELING_WORKFLOW_MARKER}_Dataset_{self.dataset_id}"
            f"_Team_{self.team_id}_Step_{self.step_number}"
        )

    def get_labeling_queue(self) -> Optional[LabelingQueueInfo]:
        queue_infos = g.api.labeling_queue.get_list(
            self.team_id, dataset_id=self.dataset_id
        )
        if not queue_infos:
            sly.logger.info(
                f"No labeling queues found for Dataset ID {self.dataset_id} in Team ID {self.team_id}."
            )
            return None

        matching_queues = []
        for queue_info in queue_infos:
            if queue_info.dataset_id == self.dataset_id:
                if MULTITEAM_LABELING_WORKFLOW_MARKER in queue_info.name:
                    matching_queues.append(queue_info)

        if not matching_queues:
            sly.logger.info(
                f"No labeling queue with marker found for Dataset ID {self.dataset_id}."
            )
            return None

        if len(matching_queues) > 1:
            raise RuntimeError(
                f"Multiple labeling queues with marker found for Dataset ID {self.dataset_id}."
            )

        return matching_queues[0]

    def to_json(self) -> Dict[str, Any]:
        selected_classes = self.class_selector.get_selected_class() or []
        classes_json = [sly_class.to_json() for sly_class in selected_classes]

        selected_tags = self.tag_selector.get_selected_tag() or []
        tags_json = [tag.to_json() for tag in selected_tags]

        reviewer_ids = [user.id for user in self.reviewer_selector.get_selected_user()]
        labeler_ids = [user.id for user in self.labeler_selector.get_selected_user()]

        data = {
            "step_number": self.step_number,
            "team_id": self.team_selector.get_selected_id(),
            "workspace_id": self.workspace_selector.get_selected_id(),
            "project_id": self.project_id,
            "dataset_id": self.dataset_id,
            "selected_classes": classes_json,
            "selected_tags": tags_json,
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

        # Set team and workspace
        if self.team_id:
            self.team_selector.set_team_id(self.team_id)
        if self.workspace_id:
            # self.workspace_selector.set_team_id(self.team_id)
            # self.workspace_selector.set_workspace_id(self.workspace_id)
            self.workspace_selector.set_ids(
                team_id=self.team_id, workspace_id=self.workspace_id
            )

        # Set classes
        classes_json = data.get("selected_classes", [])
        if classes_json:
            classes = [sly.ObjClass.from_json(cls_json) for cls_json in classes_json]
            class_names = [cls.name for cls in classes]
            self.class_selector.set(classes)
            self.class_selector.set_value(class_names)

        # Set tags
        tags_json = data.get("selected_tags", [])
        if tags_json:
            tags = [sly.TagMeta.from_json(tag_json) for tag_json in tags_json]
            tag_names = [tag.name for tag in tags]
            self.tag_selector.set(tags)
            self.tag_selector.set_value(tag_names)

        # Set reviewers and labelers
        reviewer_ids = data.get("reviewer_ids", [])
        labeler_ids = data.get("labeler_ids", [])
        if self.team_id:
            self.reviewer_selector.set_team_id(self.team_id)
            self.labeler_selector.set_team_id(self.team_id)
        if reviewer_ids:
            self.reviewer_selector.set_selected_users_by_ids(reviewer_ids)
        if labeler_ids:
            self.labeler_selector.set_selected_users_by_ids(labeler_ids)

    def _add_content(self) -> None:
        self.team_selector = SelectTeam(show_label=False)
        team_with_empty = Container(widgets=[Empty(), self.team_selector])
        team_field = Field(
            team_with_empty,
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

        @self.team_selector.value_changed
        def on_team_change(team_id: int):
            self.team_id = team_id
            self.workspace_selector.set_team_id(team_id)
            self.reviewer_selector.set_team_id(team_id)
            self.labeler_selector.set_team_id(team_id)
            Workflow().all_steps_filled()

        @self.workspace_selector.value_changed
        def on_selection_change(workspace_id: int):
            self.workspace_id = workspace_id
            sly.logger.info(
                f"Workflow Step {self.step_number} - Workspace ID: {workspace_id}"
            )
            Workflow().all_steps_filled()

        checkable_widgets = [
            self.class_selector,
            self.tag_selector,
            self.reviewer_selector,
            self.labeler_selector,
        ]

        for widget in checkable_widgets:

            @widget.value_changed
            def on_value_change(*args):
                Workflow().all_steps_filled()

        content = Container(
            widgets=[
                team_workspace_flexbox,
                users_container,
                class_tag_flexbox,
            ],
        )

        self._content = Card(
            title=f"Workflow step for Team {self.step_number}",
            content=content,
        )

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

    def all_steps_filled(self) -> bool:
        for step_number, workflow_step in self.steps.items():
            if not workflow_step.is_filled():
                sly.logger.info(f"Workflow Step {step_number} is not fully filled.")
                launch_workflow_button.disable()
                return False
        sly.logger.info("All workflow steps are fully filled.")
        launch_workflow_button.enable()
        return True

    def all_steps_queues(
        self,
    ) -> List[Tuple[Optional[sly.DatasetInfo], Optional[LabelingQueueInfo]]]:
        pairs = []
        for step_number, workflow_step in self.steps.items():
            dataset_exists = workflow_step.is_dataset_exists()
            if not dataset_exists:
                sly.logger.info(
                    f"Workflow Step {step_number} dataset does not exist. Cannot get labeling queue."
                )
                pairs.append((None, None))
                continue

            dataset_info = g.api.dataset.get_info_by_id(workflow_step.dataset_id)
            labeling_queue_info = workflow_step.get_labeling_queue()
            pairs.append((dataset_info, labeling_queue_info))
        return pairs

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

    def reset_workflow(self):
        sly.logger.info("Resetting workflow configuration.")
        for step_number, workflow_step in self.steps.items():
            sly.logger.info(f"Resetting Workflow Step {step_number}")

            workflow_step.team_selector.set_team_id(None)
            workflow_step.workspace_selector.set_workspace_id(None)
            workflow_step.class_selector.set_value([])
            workflow_step.tag_selector.set_value([])
            workflow_step.reviewer_selector.set_value([])
            workflow_step.labeler_selector.set_value([])
        launch_workflow_button.disable()

    def get_layout(self):
        return Container(widgets=[settings_card, self._layout])


if g.DATASET_ID:
    sly.logger.info(f"Setting selected dataset ID: {g.DATASET_ID}")
    select_dataset.set_dataset_id(g.DATASET_ID)
    update_dataset(g.DATASET_ID)
