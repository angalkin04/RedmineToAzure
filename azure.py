import requests
import base64
from configuration import Configuration


class Azure:
    __token64 = base64.b64encode((":" + Configuration.azureToken).encode()).decode()

    create_item_template = """[
        {{
            'op': 'add',
            'path': '/fields/System.CreatedDate',
            'value': '{created_date}'
        }},
        {{
            'op': 'add',
            'path': '/fields/System.Title',
            'value': '{title}'
        }},
        {{
            'op': 'add',
            'path': '/fields/System.CreatedBy',
            'value': '{created_by}'
        }},
        {{
            'op': 'add',
            'path': '/fields/System.Tags',
            'value': '{tags}'
        }},
        {{
            'op': 'add',
            'path': '/fields/Microsoft.VSTS.Common.Priority',
            'value': '{priority}'
        }},
        {{
            'op': 'add',
            'path': '/fields/System.AssignedTo',
            'value': '{assignee}'
        }},
        {{
            'op': 'add',
            'path': '/fields/System.State',
            'value': '{status}'
        }}
        ]"""

    patch_attachment_template = """[
        {{
            'op': 'add',
            'path': '/relations/-',
            'value': 
            {{
                'rel': 'AttachedFile',
                'url': '{url}',
                'attributes': 
                {{
                    'comment': ''
                }}
            }}
        }}
        ]"""

    patch_closed_date_template = """[
        {{
            'op': 'replace',
            'path': '/fields/Microsoft.VSTS.Common.ClosedDate',
            'value': '{date}'
        }}
        ]"""

    patch_description_template = """[
        {{
            'op': 'replace',
            'path': '/fields/System.Description',
            'value': '{description}'
        }}
        ]"""

    patch_repro_steps_template = """[
        {{
            'op': 'replace',
            'path': '/fields/Microsoft.VSTS.TCM.ReproSteps',
            'value': '{description}'
        }}
        ]"""

    patch_add_comment_template = """[
        {{
            'op': 'add',
            'path': '/fields/System.History',
            'value': '{html}'
        }},
        {{
            'op': 'add',
            'path': '/fields/System.ChangedBy',
            'value': '{author}'
        }},
        {{
            'op': 'add',
            'path': '/fields/System.createdDate',
            'value': '{date}'
        }}
        ]"""

    patch_add_related_template = f"""[
    {{{{
        'op': 'add',
        'path': '/relations/-',
        'value': 
        {{{{
            'rel': 'System.LinkTypes.Related',
            'url': 
            '{Configuration.azureAddress}/{Configuration.azureOrganization}/{Configuration.azureProject}/workItems/{{id}}',
            'attributes': 
            {{{{
                'isLocked': false,
                'name': 'Related'
            }}}}
        }}}}
    }}}}
    ]"""

    patch_add_parent_template = f"""[
    {{{{
        'op': 'add',
        'path': '/relations/-',
        'value': 
        {{{{
            'rel': 'System.LinkTypes.Hierarchy-Reverse',
            'url': 
            '{Configuration.azureAddress}/{Configuration.azureOrganization}/{Configuration.azureProject}/workItems/{{id}}',
            'attributes': 
            {{{{
                'isLocked': false,
                'name': 'Parent'
            }}}}
        }}}}
    }}}}
    ]"""

    @staticmethod
    def address(path: str, args: str = ''):
        return f"{Configuration.azureAddress}/{Configuration.azureOrganization}/{Configuration.azureProject}"\
               f"/_apis/wit{path}?{args}api-version={Configuration.azureApiVersion}"

    @staticmethod
    def header(app_content: str = 'json-patch+json'):
        return {
            "Authorization": f"Basic {Azure.__token64}",
            "Content-type": f"application/{app_content}"
        }
