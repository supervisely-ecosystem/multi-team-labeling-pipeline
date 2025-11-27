# Multi-Team Labeling Pipeline

The app creates an automated sequential labeling pipeline where a manager configures multiple teams, uploads a project/dataset, and assigns specific classes to each team. The system then automatically creates labeling tasks for Team 1 with their assigned class, monitors task completion and review status, and upon finishing, copies the annotated project to Team 2 to continue with their specific class.
This process repeats sequentially through all configured teams until the final team completes their labeling work, resulting in a fully annotated project/dataset with all classes labeled by different specialized teams. The app provides a real-time monitoring dashboard showing pipeline progress, team status, and completion metrics, eliminating manual project copying and task management between teams while ensuring each team only works on their designated classes.
The end result is a streamlined, automated workflow that transforms a single-class labeling project into a multi-class annotated dataset through coordinated team collaboration, with full visibility and control for the project manager.


## Getting Started

Step 1: Initial Setup and Configuration with Project Metadata (Detailed)
Supervisely API Client Initialization:
•	Use supervisely.Api() with server address and API token
•	Establish connection to specific Supervisely instance
•	Test connection with api.server_address and api.user.get_info()
Team Discovery and Validation:
•	Use api.team.get_list() to retrieve all available teams
•	Allow manager to select teams from dropdown/list interface
•	Validate team permissions using api.team.get_info(team_id)
•	Check if current user has admin/manager rights for selected teams
Project/Dataset Source Handling:
•	Option 1: Upload new project using api.project.upload()
•	Option 2: Select existing project with api.project.get_list(workspace_id)
•	Retrieve project metadata: classes, tags, annotation statistics
•	Use api.project.get_meta(project_id) to get ontology information
Project Metadata Collection:
•	Extract project classes using api.project.get_meta() - get all object classes defined
•	Retrieve existing tags from project meta - system tags and custom tags
•	Get dataset structure - number of images, folder organization
•	Collect annotation statistics - existing labeled items, completion rates
•	Store project settings - image formats, resolution requirements, labeling guidelines
Configuration Data Structure:
•	Store team sequence, team IDs, assigned classes per team
•	Map specific classes to teams (Team 1: "person", Team 2: "vehicle", etc.)
•	Define labeling task templates with class-specific instructions
•	Set notification preferences and automation triggers for each team
•	Create metadata tracking structure for pipeline progress
Permission and Access Verification:
•	Check project copying permissions across teams using api.project.clone()
•	Verify labeling job creation rights with api.labeling_job.create()
•	Ensure teams have appropriate dataset access levels
•	Test API rate limits and quota availability
•	Validate that each team can access assigned classes and modify project ontology
