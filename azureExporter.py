import os
import json
from configuration import Configuration
from azureItem import AzureItem


class AzureExporter:

    def __init__(self,
                 redmine_dir: str = Configuration.redmineDumpDir,
                 working_dir: str = Configuration.azureWorkingDir):

        os.makedirs(working_dir, exist_ok=True)

        self.redmineDir: str = redmine_dir
        self.workingDir: str = working_dir
        self.azureItems: list[AzureItem] = []
        self.redmineToAzureMap: dict[str, str] = {}

    def load(self, wish_list: list = None):
        print(f"Start loading Redmine tickets from {self.redmineDir}...")
        rids = os.listdir(self.redmineDir)
        for d in rids:
            rid_path = os.path.join(self.redmineDir, d)
            wid_path = os.path.join(self.workingDir, d)
            if os.path.isdir(rid_path) and True if wish_list is None else d in wish_list:
                ai = AzureItem(rid_path, wid_path)
                ai.load()
                self.azureItems.append(ai)
                print(d)

        print(f"Loaded {len(self.azureItems)} items.")

    def create(self) -> bool:

        if bool(self.redmineToAzureMap):
            print("Error: cannot do create second time")
            return False

        print(f"Start creating Azure work items...")

        redmine2azure_path = os.path.join(self.workingDir, "redmine2azure.json")
        try:
            # go to self.workingDir and find if there is a stored map of Redmine->Azure items
            # we should skip creating items which are in map
            with open(redmine2azure_path, "r") as data:
                self.redmineToAzureMap = json.load(data)
        except Exception as e:
            print(f'Info: redmine2azure not found, clean run [{e}]')

        for idx, a in enumerate(self.azureItems):
            aid = self.redmineToAzureMap.get(f"{a.rid}")
            if aid:
                print(f"Warning: {a.rid} already created, skip")
                a.id = aid
            elif a.create_workitem():
                self.redmineToAzureMap[a.rid] = f"{a.id}"

            print(f"Finished with #{idx} from #{len(self.azureItems)}")

        # save updated map
        with open(redmine2azure_path, "w+") as data:
            json.dump(self.redmineToAzureMap, data, indent=4)

    def attachments(self) -> bool:
        print(f"Start creating Azure attachments...")
        for idx, a in enumerate(self.azureItems):
            a.create_attachments()
            print(f"Finished with attachments for #{idx} from #{len(self.azureItems)}")

        return True

    def patch(self) -> bool:
        print(f"Start patching Azure work items...")
        for idx, a in enumerate(self.azureItems):
            a.patch(self.redmineToAzureMap)
            print(f"Finished with patching for #{idx} from #{len(self.azureItems)}")

        return True


if __name__ == '__main__':

    az = AzureExporter()
    az.load()   # specific Redmine ticket can be given for test purposes in form: az.load(['149714'])
    az.create()
    az.attachments()
    az.patch()


