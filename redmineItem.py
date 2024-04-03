import os
import json
from bs4 import BeautifulSoup
from redmine import Redmine


class RedmineItem:

    def __init__(self, redmine_id: str):
        self.id = redmine_id
        self.tracker = ""
        self.status = ""
        self.priority = ""
        self.assignee = ""
        self.targetVersion = ""
        self.subProject = ""
        self.title = ""
        self.description = ""
        self.createdBy = ""
        self.createdOn = ""
        self.closedOn = ""
        self.attachments = []
        self.related = []
        self.children = []
        self.parent = ''
        self.notes_info = []
        self.notes_content = []

    def __parse_subproj(self, issue) -> str:
        subproj = ''
        try:
            cf = issue['custom_fields']
            a = next(q for q in cf if q['name'] == 'Sub project')
            subproj = a['value']
        except KeyError as e:
            print(f"Error: {self.id}: No subproject attribute [{e}]")

        return subproj

    def __parse_relations(self, issue) -> list[str]:
        id_list = []
        try:
            relations = issue['relations']
            for r in relations:
                rid = f"{r['issue_id']}"
                if rid == self.id:
                    rid = f"{r['issue_to_id']}"
                id_list.append(rid)
        except KeyError as e:
            print(f"Warning: {self.id}: No relation found [{e}]")

        return id_list

    def __parse_attachments(self, issue) -> list[dict]:
        att_list = []
        try:
            attachments = issue['attachments']
            att_list = [{"id": f"{r['id']}", "filename": r['filename'], "url": r['content_url']} for r in attachments]
        except KeyError as e:
            print(f"Warning: {self.id}: No attachment found [{e}]")

        return att_list

    def __parse_children(self, issue) -> list[str]:
        id_list = []
        try:
            children = issue['children']
            id_list = [f'{r["id"]}' for r in children]
        except KeyError as e:
            print(f"Warning: {self.id}: No children found [{e}]")

        return id_list

    def __parse_description(self, html_soup):
        try:
            d = html_soup.body.find('div', attrs={'class': 'description'})

            if bool(d):
                d.find('div', {'class': 'contextual'}).decompose()

            return d
        except Exception as e:
            print(f"Warning: {self.id}: No children found [{e}]")

    def __parse_notes_info(self, issue) -> list[dict]:
        notes_info = []
        journals = issue.get("journals")
        for j in journals or []:
            note = j.get("notes")
            if note:
                try:
                    notes_info.append({
                        "id": j["id"],
                        "author": j["user"]["name"],
                        "created_on": j["created_on"]
                    })
                except KeyError as e:
                    print(f"Error: {self.id}: failed to get note")

        return notes_info

    def __parse_notes_content(self, html_soup) -> dict[str,str]:
        notes_list = {}
        history_block = html_soup.body.find("div", "tab-content")
        for n in self.notes_info:
            message = history_block.find("div", id=f"journal-{n['id']}-notes")
            notes_list[n["id"]] = message

        return notes_list

    def __parse_field1(self, issue, name) -> str:
        field = ''
        try:
            field = issue[name]
        except KeyError:
            print(f"Error: {self.id}: cannot get value for [{name}] field")

        return f"{field}"

    def __parse_field2(self, issue, name1, name2) -> str:
        field = ''
        try:
            field = issue[name1][name2]
        except KeyError:
            print(f"Error: {self.id}: cannot get value for [{name1}][{name2}] field")

        return f"{field}"

    def fill(self) -> bool:
        try:
            # parse from json
            js = Redmine.get(f"/issues/{self.id}.json", "include=relations,children,attachments,journals")
            data = json.loads(js.content)

            issue = data['issue']
            self.tracker = self.__parse_field2(issue, 'tracker', 'name')
            self.createdBy = self.__parse_field2(issue, 'author', 'name')
            self.status = self.__parse_field2(issue, 'status', 'name')
            self.priority = self.__parse_field2(issue, 'priority', 'name')
            self.assignee = self.__parse_field2(issue, 'assigned_to', 'name')
            self.targetVersion = self.__parse_field2(issue, 'fixed_version', 'name')
            self.parent = self.__parse_field2(issue, 'parent', 'id')
            self.title = self.__parse_field1(issue, 'subject')
            self.createdOn = self.__parse_field1(issue, 'created_on')
            self.closedOn = self.__parse_field1(issue, 'closed_on')
            self.subProject = self.__parse_subproj(issue)
            self.related = self.__parse_relations(issue)
            self.children = self.__parse_children(issue)
            self.attachments = self.__parse_attachments(issue)
            self.notes_info = self.__parse_notes_info(issue)

            # parse from html
            html = Redmine.get(f"/issues/{self.id}.html?include=journals")
            html_soup = BeautifulSoup(html.content, 'html.parser')
            self.description = self.__parse_description(html_soup)
            self.notes_content = self.__parse_notes_content(html_soup)
            return True
        except Exception as e:
            print(f"Error: {self.id}: cannot fill data [{e}]")

        return False

    def dump(self, root_dir: str) -> bool:

        rid = f"{self.id}"
        issue_path = os.path.join(root_dir, rid)
        attachments_path = os.path.join(issue_path, "attachments")
        history_path = os.path.join(issue_path, "history")

        # create directory, exit if exists
        try:
            os.makedirs(attachments_path, exist_ok=False)
            os.makedirs(history_path, exist_ok=False)
        except OSError as e:
            print(f"Error: {self.id}: failed to dump work item, can't create output directories [{e}]")
            return False

        if not self.fill():
            return False

        d = {
            "id": self.id,
            "tracker": self.tracker,
            "status": self.status,
            "priority": self.priority,
            "assignee": self.assignee,
            "targetVersion": self.targetVersion,
            "subProject": self.subProject,
            "title": self.title,
            "createdBy": self.createdBy,
            "createdOn": self.createdOn,
            "closedOn": self.closedOn,
            "parent": self.parent,
            "relations": self.related,
            "children": self.children,
            "attachments": self.attachments,
            "notes": self.notes_info
        }

        # save general data
        try:
            with open(os.path.join(issue_path, 'data.json'), "w") as json_file:
                json.dump(d, json_file, indent=4)
        except Exception as e:
            print(f"Error: {self.id}: failed to dump json [{e}]")

        # save html content for description
        try:
            with open(os.path.join(issue_path, 'description.htm'), "w", encoding="utf-8") as descr_file:
                descr_file.write(f"{self.description}")
        except Exception as e:
            print(f"Error: {self.id}: failed to dump description [{e}]")

        # save html content for notes
        for note_id in self.notes_content:
            try:
                with open(os.path.join(history_path, f"{note_id}.htm"), 'w', encoding="utf-8") as h_file:
                    h_file.write(f"{self.notes_content[note_id]}")
            except Exception as e:
                print(f"Error: {self.id}: failed to dump history element #{note_id} [{e}]")

        # download attachments
        for idx, a in enumerate(self.attachments):
            try:
                Redmine.get_file(a['url'], os.path.join(attachments_path, a['filename']))
            except Exception as e:
                print(f"Error: {self.id}: failed to dump attachment #{idx} [{e}]")

