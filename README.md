# RedmineToAzure
# Description
Migration includes transfer of Bugs, Tasks, User Stories data with these attributes:
- title with added prefix referenced to Redmine ID
- created by
- created date
- status
- assignee
- priority
- date of closing (for closed issues)
- attachments
- user notes from the history
- images and formatting for description and notes
- parents and related issues
- custom fields, target version as Azure tags

# Configuration
Edit configuration.py to customize Redmine project name, access tokens, Azure organization etc.

# Migration
Data migration happens in the following steps:
1. Fill configuration data in configuration.py
2. Run RedmineImporter.py to dump all the data of Redmine project to local disk
3. Analyze correctness of of dump
4. Run azureExporter.py to upload the data to Azure Devops board
