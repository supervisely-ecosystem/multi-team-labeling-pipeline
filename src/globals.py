import os
import shutil

import supervisely as sly

from dotenv import load_dotenv

if sly.is_development():
    load_dotenv("local.env")
    load_dotenv(os.path.expanduser("~/supervisely.env"))

api = sly.Api.from_env(ignore_task_id=True)

TEAM_ID = sly.env.team_id()
WORKSPACE_ID = sly.env.workspace_id()

PROJECT_ID = sly.env.project_id(raise_not_found=False)
DATASET_ID = sly.env.dataset_id(raise_not_found=False)
sly.logger.info(
    f"Team ID: {TEAM_ID}, Workspace ID: {WORKSPACE_ID}, "
    f"Project ID: {PROJECT_ID}, Dataset ID: {DATASET_ID}"
)

number_of_teams = os.environ.get("modal.state.numberOfTeams")
if not number_of_teams:
    raise ValueError("Environment variable 'modal.state.numberOfTeams' is not set.")
NUMBER_OF_TEAMS = int(number_of_teams)
sly.logger.info(f"Number of teams: {NUMBER_OF_TEAMS}")
