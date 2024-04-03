import requests
from configuration import Configuration


class Redmine:
    __header = {"X-Redmine-API-Key": f"{Configuration.redmineToken}"}

    @staticmethod
    def get(path, args=''):
        if args:
            p = f"{Configuration.redmineAddress}{path}?{args}"
        else:
            p = f"{Configuration.redmineAddress}{path}"

        return requests.get(p, headers=Redmine.__header)

    @staticmethod
    def get_file(url, file_path):
        r = requests.get(url, stream=True, headers=Redmine.__header)
        with open(file_path, 'wb') as output:
            output.write(r.content)


