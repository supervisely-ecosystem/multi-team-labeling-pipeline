# Multi-Team Labeling Workflow

## Overview

The Multi-Team Labeling Workflow is a Supervisely application that automates sequential labeling workflows across multiple teams. This app eliminates the need for manual project copying and task management between teams, enabling each team to focus on their specialized classes or tags. By allowing annotators to focus on their areas of expertise, it significantly increases the quality of labeling while providing managers with an easy-to-use system to oversee and manage the entire annotation process.

The app creates an automated workflow where:

1. A manager configures multiple teams and assigns specific classes/tags if needed to each team
2. The system automatically creates labeling queues for every team with their assigned classes/tags
3. Upon completion and review, the annotated project automatically copies to the next team
4. This process repeats sequentially through all configured teams
5. The final result is a fully annotated dataset with contributions from all specialized teams

Key features include:

- **Automated workflow progression**: Automatic project copying and queue creation between teams
- **Real-time monitoring**: Live dashboard showing workflow progress and team status
- **Flexible configuration**: Support for class-based and tag-based labeling requirements
- **Team specialization**: Each team works only on their designated classes/tags
- **Persistent workflow state**: Save and resume workflows across sessions
- **Quality control**: Built-in review process for each team's work

## How To Run

### Step 1: Launch the Application

You can launch the Multi-Team Labeling Workflow in three ways:

1. **From Ecosystem** (Create new workflow):

   - Navigate to the Ecosystem in your Supervisely instance
   - Find "Multi-Team Labeling Workflow" app
   - Click "Run" and specify the number of teams in the modal dialog
   - Click "Run" to launch the app

2. **From Project Context Menu** (Configure workflow for existing project):

   - Right-click on the project in your workspace
   - Select "Run App" → "Multi-Team Labeling Workflow"
   - Specify the number of teams in the modal dialog
   - The app will launch with the project pre-selected

3. **From Dataset Context Menu** (Configure workflow for specific dataset):
   - Right-click on any dataset within an images project
   - Select "Run App" → "Multi-Team Labeling Workflow"
   - Specify the number of teams in the modal dialog
   - The app will launch with both project and dataset pre-selected

### Step 2: Configure Settings

In the **Settings** card at the top of the application:

1. **Select Project**: Choose the source project containing the data you want to label

2. **Select Dataset**: Choose the specific dataset within the project to be labeled

3. **Labeling Requirements** (optional):
   - Check **"Classes labeling is required"** if teams must label at least one class
   - Check **"Tags labeling is required"** if teams must label at least one tag

### Step 3: Configure Each Team's Workflow Step

For each team (from Team 1 to Team N), you need to configure:

#### 3.1 Team and Workspace

- **Team**: Select the team that will work on this step
- **Workspace**: Select the workspace where the project will be copied for this team
  - For Team 1, you may use the same workspace as the source project
  - For subsequent teams, you typically select different workspaces to keep work separated

#### 3.2 Labelers and Reviewers

- **Labelers**: Select one or more users who will perform the labeling work
  - Users must have "annotator" or "reviewer" roles
- **Reviewers**: Select one or more users who will review the labeled data
  - Users must have "annotator", "reviewer", or "manager" roles

#### 3.3 Classes and Tags (if you checked "Classes labeling is required" or/and "Tags labeling is required")

- **Classes**: Select which object classes this team should label
  - You can select multiple classes for labeling
  - Different teams can work on different classes
- **Tags**: Select which tags this team should label
  - You can select multiple tags
  - Tags can be image-level or object-level metadata

**Important**: Each team's configuration determines what they will see and label in their labeling queue. Only the selected classes and tags will be available for annotation.

### Step 4: Save the Workflow Configuration

Once you've configured all teams:

1. Click the **Save** button (disk icon) in the Settings card
2. The workflow configuration will be saved
3. This allows you to:
   - Resume the workflow later
   - Modify team configurations before launching
   - Use the same workflow for multiple datasets in the same project

**Note**: The workflow configuration is saved per dataset. If you select a different dataset, you'll need to configure and save a new workflow or load an existing one.

### Step 5: Launch the Workflow

After configuring and saving the workflow:

1. The **"Launch Workflow"** button will become enabled (it's disabled until all teams are fully configured)
2. Click **"Launch Workflow"** to open the monitoring dashboard
3. The Workflow Overview modal will appear, showing:
   - All workflow steps (one per team)
   - Current status of each step (pending, in progress, or completed)
   - Real-time status updates

### Step 6: Monitor Workflow Progress

The Workflow Overview provides real-time monitoring:

- **Pending**: Step is waiting for the previous step to complete
- **In Progress**: Labeling queue is active, team is working
- **Completed**: Team has finished labeling and review is done

**Automated Progression**:

- When Team 1 completes their work, the app automatically copies the project to Team 2's workspace
- A new labeling queue is created for Team 2 with their assigned classes/tags
- This continues sequentially through all teams
- No manual intervention is required between teams

### Step 7: Reset or Update Workflow

You have two options with the reset/update button:

1. **Reset Workflow** (X icon):

   - Clears all team configurations
   - Useful for starting fresh or fixing configuration errors
   - After reset, the button changes to an restore icon

2. **Restore** (refresh icon):
   - Resrore the workflow status from the server
   - Updates the monitoring dashboard with latest information
   - After update, the button changes back to reset icon

## Workflow Automation Details

### How the Workflow Works

1. **Initial Setup** (Team 1):

   - When you launch the workflow, a labeling queue is created for Team 1
   - The queue uses the source dataset and selected classes/tags
   - Team 1 begins labeling immediately

2. **Sequential Progression** (Teams 2-N):

   - The app monitors each team's labeling queue status
   - When a queue is marked as "completed" (all items labeled and reviewed):
     - The app automatically clones the project to the next team's workspace
     - A new labeling queue is created with the next team's configuration
     - The next team can begin work immediately
   - This process repeats until all teams complete their work

### Workflow State Persistence

The app saves workflow configurations in the project's custom data:

- Configurations are stored per dataset
- You can have different workflows for different datasets in the same project
- Saved configurations include all team settings, selected classes, tags, users, etc.
- When you reload the app with the same project/dataset, the configuration is automatically restored

## Important Notes

- **Queue Completion**: A labeling queue is only considered "completed" when all items are labeled AND reviewed. Make sure to complete the review process for each team to enable automatic progression.
