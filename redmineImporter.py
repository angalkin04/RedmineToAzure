
import json
from redmineItem import RedmineItem
from configuration import Configuration
from redmine import Redmine


class RedmineImporter:
    def __init__(self, dump_dir: str = Configuration.redmineDumpDir):
        self.issues: list[str] = []
        self.dumpDir: str = dump_dir

    def list_issues(self, total_limit: int = 1e6) -> bool:
        """
        get list of issues for the project in configuration
        :param total_limit: optional argument to limit the output list size (for test purposes)
        :return: True if success
        """
        offset = 0

        while True:
            limit = (total_limit - offset) if 0 < (total_limit - offset) < 100 else 100
            js = Redmine.get(f'/projects/{Configuration.redmineProject}/issues.json',
                             f'status_id=*;limit={limit};offset={offset}')
            data = json.loads(js.content)
            try:
                self.issues.extend([f'{issue["id"]}' for issue in data["issues"]])
                offset = len(self.issues)
                print(f"New length = {offset}")
                total_count = data['total_count']
                if offset >= total_limit or offset >= total_count:
                    break
            except KeyError as e:
                print(f"Error: Redmine: Exception at offset={offset}\n{e}")
                return False

        return True

    def dump(self):
        """
        Dump all the information from Redmine to disc
        :return: void
        """
        for i in self.issues:
            ri = RedmineItem(i)
            ri.dump(self.dumpDir)


if __name__ == '__main__':
    # for test purposes
    x = RedmineImporter()
    x.list_issues() # instead of getting all the issues can use a specific ID's for test purposes in form: x.issues = ['197370']
    x.dump()
