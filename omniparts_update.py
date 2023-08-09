## ----------------------------------------
## Variables to set: 

# N.B.: gitlab token must be stored (alone) in a file called `.token`.

# Renku gitlab URL
gitlab_url = 'https://gitlab.renkulab.io/'
# namespace ID of the omnibenchmark subgroup to look at
namespace_id = '72048'
# ...alternatively, (list of) projects to look at.
# Leave empty [] if the modifications needs to affect all projects in that namespace id
search_term = []

# Commit message
commit_msg = "omb version update"

## Vars to define what we want to scrape
target = ".gitlab-ci.yml" 
target_path = "."
target_branches = ["master","main"]

## Search term in the target file
target_search = '/builds/gitlab/'
## Replacement to bring to the search term
target_modified = '/builds/'


# Dry run which will show the projects identified by the search
# and show the modifications that it will bring.
dry_run = False

## -----------------------------------------
import os
import base64
import gitlab
import pandas as pd
import re
from dfply import *
import yaml
from datetime import datetime
import difflib
from difflib import ndiff
import sys as sys


## utils function to print context around changes
def print_context(string, pattern):
    lines = string.split("\n")
    print("---[TRUNCATED] -----")
    for i, line in enumerate(lines):
        if pattern in line:
            start_index = max(0, i - 5)
            end_index = min(len(lines), i + 6)
            context_lines = lines[start_index:end_index]
            print("\n".join(context_lines))
            break
    print("---[TRUNCATED] -----")



# CREATE COMMITS---------------------------

# N.B.: gitlab token must be stored (alone) in a file called `.token`.
tf = open(".token", "r")
token = tf.read().rstrip()
tf.close()
n = len(token)
print("Token (truncated):")
print(token[0:5], "...", token[n-5:n], sep="")


if search_term == ['']: 
    sys.exit('search_term not empty ([''] instead of [])')
if len(search_term) == 0: 
    gl = gitlab.Gitlab(url="https://gitlab.renkulab.io", private_token=token)
    # query project from namespace group
    group = gl.groups.get(namespace_id, lazy=True)
    group.projects.list(get_all = True)

    proj_iterat = group.projects.list(iterator = True)
    projects = [x.attributes for x in proj_iterat]
    projects = [x['name'] for x in projects]
    print('Detected projects:')
    print(projects)


# datetime object containing current date and time
now = datetime.now()
print("\nnow =", now)
dt_string = now.strftime("%d/%m/%Y %H:%M:%S")

## Grab a set of projects according to search terms
#gl = gitlab.Gitlab(url='https://gitlab.renkulab.io',private_token=token)
#print(gl.api_url)

for SEARCH in projects: 
    p = gl.projects.list(get_all=True, search=SEARCH,
                        order_by="last_activity_at", per_page=100)
                                
    len(p)
    p = p[0]
    print("\n\nReading project:")
    print("project_id:"+ str(p.get_id()) + "    namespace_name:"+p.name_with_namespace )
    bs = p.branches.list(get_all=True)
    bb = [b.name for b in bs if b.name in target_branches]
    if len(bb) == 0: 
        continue
    br = bb[0]

    fs = p.repository_tree(path=target_path, ref=br, all=True)


    cy = [f["path"] for f in fs if f["path"] == target]
    cy = ''.join(cy)

    url = p.http_url_to_repo.replace("https://gitlab.renkulab.io/","")
    url = re.sub(".git$","", url)


    f = p.files.get(file_path=target, ref=br)
    fc = base64.b64decode(f.content).decode("utf-8")

    fc_adj = re.sub(target_search, target_modified, fc)

    # Show modifications (and continue, if none)
    if fc == fc_adj: 
        print("Nothing to change, continuing to next one...")
        continue
    diff = ndiff(fc_adj.splitlines(keepends=True),
            fc.splitlines(keepends=True))
    diff_out = ''.join(diff)
    pattern = r"\?\s*[-+]"
    #pattern = r"(\+|-).*\n(\+|-)"

    diff_lines = re.findall(pattern, diff_out)
    if diff_lines == []: 
        print(diff_out)
    else: 
        x = [i for i in range(1, (len(diff_lines) )) if i%2!=0]
        if x == []: 
            x = range(0, 1)
        print("MODIFICATIONS TO:\n"+f.file_name)
        for xi in x: 
            print_context(diff_out, diff_lines[xi])

    #print("Actual file (truncated):")
    #print(fc)
    #print("Modified file (truncated):")
    #print(fc_adj)

    data = {
        'branch': br,
        'commit_message': '[bulk update]:' + commit_msg,
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




















