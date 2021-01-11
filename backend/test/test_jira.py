from jira import JIRA
import getpass

def main():
    host = 'https://jira.teko.vn'
    username = 'binh.nt'
    projectKey = 'DI'
    password = getpass.getpass()
    jira = JIRA(host, auth=(username, password))
    issues_in_proj = jira.search_issues('project={} and assignee = currentUser() order by priority desc'.format(projectKey))
    for issue in issues_in_proj:
        print('{}: {}'.format(issue.key, issue.fields.summary))
        if issue.key == 'DI-9':
            sub_issue_dict = {
                'project': {'key': projectKey},
                'summary': 'Test create subtask from python',
                'description': 'Test create subtask from python',
                'issuetype' : { 'name' : 'Sub-task' },
                'parent' : { "id" : issue.key },
            }
            child = jira.create_issue(fields=sub_issue_dict)
            print("created child: " + child.key)
            
if __name__== "__main__":
  main()
