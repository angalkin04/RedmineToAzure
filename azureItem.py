import os
import requests
import json
from azure import Azure


def escape_text(text: str):
    return (text
            .encode('unicode_escape')
            .decode()
            .replace("'", r"\'")
            .replace(r'\x', r'\u00'))


class AzureItem:
    def __init__(self, redmine_dir: str, azure_dir: str):
        self.redmineDir = redmine_dir
        self.azureDir = azure_dir

        self.redmineData = {}
        self.rid = ''
        self.id = ''

        # data for step #1: to create work item
        self.type = ''  # "Bug", "Task", "User Story", "Test Case"
        self.title = ''
        self.tags = []
        self.assignee = ''
        self.createdBy = ''
        self.createdDate = ''
        self.closedDate = ''
        self.priority = ''
        # data to complete work item configuration by patching
        # Bug: 'New', 'Active', 'Closed'
        # Task: 'New', 'Active', 'Closed', 'Removed'
        # User Story: 'New', 'Active', 'Resolved', 'Closed', 'Removed'
        # Test Case: 'Design', 'Ready', 'Closed'
        self.status = ''

        # data for step #2: add attachments
        self.attachments = {}

        # data for step #3: patch
        self.description = ''
        self.related = []
        self.children = []
        self.parent = ''
        self.history = []

    def load(self) -> bool:

        try:
            data_json = os.path.join(self.redmineDir, "data.json")
            with open(data_json, "r") as data:
                self.redmineData = json.load(data)

            self.rid = self.redmineData['id']

            # add Epic\Test Case\etc. if these type needs to be processed
            self.type = {
                "Bug": "bug",
                "Task": "task",
                "User Story": "user%20story"
            }[self.redmineData['tracker']]

            self.title = f"[REDMINE{self.rid}] {self.redmineData['title']}"
            self.tags = f"{self.redmineData['targetVersion']};{self.redmineData['subProject']}"
            self.assignee = self.redmineData['assignee']
            self.createdBy = self.redmineData['createdBy']
            self.createdDate = self.redmineData['createdOn']
            self.closedDate = self.redmineData['closedOn']
            self.priority = {
                "Low": "4",
                "Normal": "3",
                "High": "2",
                "Urgent": "1",
                "Immediate": "1"
            }[self.redmineData['priority']]

            self.status = {
                "New": "New",
                "Ready for Review": "Active",
                "In Review": "Active",
                "In Progress": "Active",
                "Ready for Testing": "Active",
                "In Testing": "Active",
                "Resolved": "Resolved",
                "Reopened": "Active",
                "Closed": "Closed"
            }[self.redmineData['status']]

            if self.status == "Resolved" and self.type == "task":
                self.status = "Active"

        except Exception as e:
            print(f"Error: 0({self.rid}): cannot load data with type {self.redmineData.get('tracker')} [{e}]")
            return False

        return True

    def create_workitem(self) -> bool:
        try:
            if self.type:
                d = Azure.create_item_template.format(created_date=self.createdDate,
                                                      title=escape_text(self.title),
                                                      created_by=self.createdBy,
                                                      assignee=self.assignee,
                                                      tags=self.tags,
                                                      priority=self.priority,
                                                      status=self.status)

                ad = Azure.address(path=f'/workitems/${self.type}', args='bypassRules=true&')
                response = requests.post(ad, headers=Azure.header(), data=d)
                if not response.ok:
                    raise Exception(f"Server responded False [{response.text}]")
                
                json_resp = json.loads(response.content)
                self.id = json_resp['id']
        except Exception as e:
            print(f"Error: 0({self.rid}): cannot create work item for {self.rid} [{e}]")
            return False

        return True

    def create_attachments(self):
        os.makedirs(self.azureDir, exist_ok=True)

        # get attachments info stored in working directory not to upload any file twice
        azure_attachments = os.path.join(self.azureDir, "attachments.json")
        try:
            with open(azure_attachments, "r") as data:
                self.attachments = json.load(data)
        except Exception as e:
            print(f"Info: {self.id}({self.rid}): no attachment has been uploaded yet {e}")

        redmine_attachments = self.redmineData.get("attachments")

        for a in redmine_attachments:
            try:
                name = a["filename"]
                if self.attachments.get(name):
                    print(f"Info: attachment {name} has been already uploaded to azure")
                else:
                    a_path = os.path.join(self.redmineDir, "attachments", name)
                    with open(a_path, 'rb') as file:
                        name_mod = name.replace('#', 'n')
                        ad = Azure.address(path=f'/attachments', args=f'fileName={name_mod}&')
                        response = requests.post(ad, headers=Azure.header('octet-stream'), data=file)
                        if not response.ok:
                            raise Exception(f"Server responded False [{response.text}]")
                        resp = json.loads(response.content)
                        self.attachments[name] = {"id": resp.get("id"), "url": resp.get("url")}
            except Exception as e:
                print(f"Error: {self.id}({self.rid}): failed to upload attachment [{e}]")

        with open(azure_attachments, "w") as json_file:
            json.dump(self.attachments, json_file, indent=4)

    def replace_attachments_urls(self, html: str):
        redmine_attachments = self.redmineData.get("attachments")
        for a in redmine_attachments:
            try:
                name = a['filename']
                aid = a['id']
                html = html.replace(f"/attachments/download/{aid}/{name}", self.attachments[name]["url"])
            except Exception as e:
                print(f"Error: {self.id}({self.rid}): cannot find Azure attachment for Redmine [{e}]")

        return html

    def patch_description(self) -> bool:
        # description
        descr = os.path.join(self.redmineDir, "description.htm")
        text = ''
        with open(descr, 'r', encoding="utf-8") as descr_text:
            text = descr_text.read()

        text = escape_text(text)
        self.description = self.replace_attachments_urls(text)

        try:
            if self.type == "bug":
                patch = Azure.patch_repro_steps_template.format(description=self.description)
            else:
                patch = Azure.patch_description_template.format(description=self.description)

            response = requests.patch(Azure.address(path=f'/workitems/{self.id}'),
                                      headers=Azure.header(),
                                      data=f"{patch}")
            if not response.ok:
                raise Exception(f"Server responded False [{response.text}]")
        except Exception as e:
            print(f"Error: {self.id}({self.rid}): cannot patch description [{e}]")
            return False

        with open(os.path.join(self.azureDir, "description.htm"), "w", encoding="utf-8") as htm_file:
            htm_file.write(self.description)

        return True

    def patch_attachments(self):
        for a in self.attachments:
            try:
                patch_att = Azure.patch_attachment_template.format(url=self.attachments[a]["url"])

                ad = Azure.address(path=f'/workitems/{self.id}')
                response = requests.patch(ad, headers=Azure.header(), data=patch_att)
                # json_resp = json.loads(response.content)
                if not response.ok:
                    raise Exception(f"Server responded False [{response.text}]")
            except Exception as e:
                print(f"Error: {self.id}({self.rid}): cannot assign attachment to work item [{e}]")
        pass

    def patch_closedate(self):
        # closed date should be set to avoid further validation failures
        # set fixed fake close date
        if self.status == "Closed":
            try:
                closed_date = self.closedDate if len(self.closedDate) > 5 else "2024-03-30T00:00:00Z"
                patch = Azure.patch_closed_date_template.format(date=closed_date)
                response = requests.patch(Azure.address(path=f'/workitems/{self.id}' args='bypassRules=true&'),
                                          headers=Azure.header(),
                                          data=patch)
                if not response.ok:
                    raise Exception(f"Server responded False [{response.text}]")

            except Exception as e:
                print(f"Error: {self.id}({self.rid}): cannot set close date [{e}]")

    def patch_notes(self):
        notes = self.redmineData.get("notes")
        notes.sort(key=lambda el: el["id"])

        history_path = os.path.join(self.azureDir, "history")
        os.makedirs(history_path, exist_ok=True)

        for n in notes:
            try:
                content_path = os.path.join(self.redmineDir, "history", f"{n['id']}.htm")
                with open(content_path, 'r', encoding="utf-8") as c:
                    content = c.read()

                content = escape_text(content)
                content = self.replace_attachments_urls(content)
                # add author\date info
                content = f"<p>Added by {n['author']} on {n['created_on']}</p>" + content
                patch = Azure.patch_add_comment_template.format(html=content,
                                                                author=n["author"],
                                                                date=n["created_on"])
                response = requests.patch(Azure.address(path=f'/workitems/{self.id}', args='bypassRules=true&'),
                                          headers=Azure.header(),
                                          data=patch)
                if not response.ok:
                    raise Exception(f"Server responded False [{response.text}]")

                with open(os.path.join(history_path, f"{n['id']}.htm"), "w", encoding="utf-8") as htm_file:
                    htm_file.write(content)
            except Exception as e:
                print(f"Error: {self.id}({self.rid}): cannot add comment [{e}]")

    def patch_relations(self, redmine2azure: dict[str, str]):
        # set parent
        try:
            redmine_parent = self.redmineData["parent"]
            if redmine_parent:
                self.parent = redmine2azure[redmine_parent]
                if self.parent:
                    patch = Azure.patch_add_parent_template.format(id=self.parent)
                    response = requests.patch(Azure.address(path=f'/workitems/{self.id}'),
                                              headers=Azure.header(),
                                              data=patch)
                    if not response.ok:
                        raise Exception(f"Server responded False [{response.text}]")

        except Exception as e:
            print(f"Error: {self.id}({self.rid}): Failed to set parent [{e}]")

        # set related
        redmine_relations = self.redmineData["relations"]
        for r in redmine_relations or []:
            try:
                azure_id = redmine2azure[f"{r}"]
                if azure_id:
                    patch = Azure.patch_add_related_template.format(id=azure_id)
                    response = requests.patch(Azure.address(path=f'/workitems/{self.id}'),
                                              headers=Azure.header(),
                                              data=patch)
                    if not response.ok:
                        raise Exception(f"Server responded False [{response.text}]")

            except Exception as e:
                print(f"Error: {self.id}({self.rid}): Failed to add related item [{e}]")

    def patch(self, redmine2azure: dict[str, str]):
        if self.id:
            self.patch_closedate()
            self.patch_attachments()
            self.patch_description()
            self.patch_notes()
            self.patch_relations(redmine2azure)
            return True

        return False
