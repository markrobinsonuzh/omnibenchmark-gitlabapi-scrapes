## ----------------------------------------
## Variables to set: 

# N.B.: gitlab token must be stored (alone) in a file called `.token`.

# Renku gitlab URL
gitlab_url = 'https://renkulab.io/gitlab/'
# namespace ID of the omnibenchmark subgroup to look at
namespace_id = '72048'
# ...alternatively, (list of) projects to look at.
# Leave empty [] if the modifications needs to affect all projects in that namespace id
search_term = []

## Vars to define what we want to scrape
target = "requirements.txt"
target_path = "."
target_branches = ["master","main"]

# Package to update (if target == requriements)
target_pkg = "omniValidator"

# New version for the specified package
new_version = '0.0.19'

# Dry run which will show the projects identified by the search
# and show the modifications that it will bring.
dry_run = True

## -----------------------------------------
import os
import base64
import gitlab
import pandas as pd
import re
from dfply import *
import yaml
from datetime import datetime
import requests



# GET THE PROJECT FROM NAMESPACE ID -----------
# Set your GitLab instance URL and namespace ID

if len(search_term) == 0: 
    # Set the API endpoint
    api_url = f'{gitlab_url}/api/v4/projects'

    # Make the API request
    response = requests.get(api_url, params={'namespace_id': namespace_id})

    # Make the initial API request
    params = {'namespace_id': namespace_id, 'page': 1, 'per_page': 100}
    response = requests.get(api_url, params=params)

    # Check if the request was successful
    if response.status_code == 200:
        projects = response.json()
        projects = [project for project in projects if project['namespace']['id'] == int(namespace_id)]
        project_names = [project['name'] for project in projects]

        # Retrieve subsequent pages until the maximum number of pages is reached
        page = 2  # Start with the second page
        max_pages = 20  # Set the maximum number of pages to retrieve (adjust as needed)
        while 'next' in response.links and page <= max_pages:
            response = requests.get(response.links['next']['url'], params=params)
            if response.status_code == 200:
                projects = response.json()
                projects = [project for project in projects if project['namespace']['id'] == int(namespace_id)]
                project_names.extend([project['name'] for project in projects])
                page += 1
            else:
                print(f"Error: {response.status_code} - {response.text}")
                break

    else:
        print(f"Error: {response.status_code} - {response.text}")

    search_term = list(set(project_names))
    print('Detected projects:')
    print(search_term)

# CREATE COMMITS---------------------------

# N.B.: gitlab token must be stored (alone) in a file called `.token`.
tf = open(".token", "r")
token = tf.read().rstrip()
tf.close()
n = len(token)
print("Token:")
print(token[0:5], "...", token[n-5:n], sep="")



# datetime object containing current date and time
now = datetime.now()
print("now =", now)
dt_string = now.strftime("%d/%m/%Y %H:%M:%S")

## Grab a set of projects according to search terms
gl = gitlab.Gitlab(url='https://renkulab.io/gitlab',private_token=token)
print(gl.api_url)

for SEARCH in search_term: 
    p = gl.projects.list(get_all=True, search=SEARCH,
                        order_by="last_activity_at", per_page=100)
                                
    len(p)
    p = p[0]
    print("\nReading project:")
    print("project_id:"+ str(p.get_id()) + "    namespace_name:"+p.name_with_namespace )
    bs = p.branches.list(get_all=True)
    bb = [b.name for b in bs if b.name in target_branches]
    if len(bb) == 0: 
        continue
    br = bb[0]

    fs = p.repository_tree(path=target_path, ref=br, all=True)


    cy = [f["path"] for f in fs if f["path"] == target]
    cy = ''.join(cy)

    url = p.http_url_to_repo.replace("https://renkulab.io/gitlab/","")
    url = re.sub(".git$","", url)


    f = p.files.get(file_path=target, ref=br)
    fc = base64.b64decode(f.content).decode("utf-8")
    # manipulate version numbers
    fcs = [pkg.split("==") for pkg in fc.split("\n")]

    for i in range(len(fcs)):
        print(fcs[i][0])
        if(fcs[i][0] == target_pkg):
            fcs[i][1] = new_version
        
    fc_adj = "\n".join(["==".join(ii) for ii in fcs])

    print("Actual requirements:")
    print(fc)
    print("Modified requirements:")
    print(fc_adj)
    if fc == fc_adj: 
        print("Nothing to change, continuing to next one...")
        continue

    data = {
        'branch': br,
        'commit_message': 'adjust version of '+ target_pkg + ' in ' +target + ': ' + dt_string,
        'actions': [
            {
                'action': 'update',
                'file_path': cy,
                'content': fc_adj, # NOTE: local file

            }
        ]
    }
    if not dry_run: 
        commit = p.commits.create(data)
        print("Commit ID:")
        print(commit.id)

    # Prints last 3 commits
    #comms = p.commits.list(ref_name=br, get_all=True)[0:3]
    #for i in range(len(comms)):
    #    c = comms[i]
    #    print(c.short_id, "\t", c.message)  
    #print(p.http_url_to_repo)




















