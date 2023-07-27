from typing import Optional, List, Union
import warnings
import os
import base64
import gitlab
import re
from difflib import ndiff
import sys as sys


## utils function to print context around changes
def print_context(string, pattern):
    lines = string.split("\n")
    print("\n---[TRUNCATED] -----\n")
    for i, line in enumerate(lines):
        if pattern in line:
            start_index = max(0, i - 5)
            end_index = min(len(lines), i + 6)
            context_lines = lines[start_index:end_index]
            print("\n".join(context_lines))
            break
    print("---[TRUNCATED] -----")


def get_projects(
    projects_with_namespace: Optional[List[str]] = None,
    namespace: Optional[str] = None,
    git_url: str = "https://renkulab.io/gitlab",
    token: Optional[str] = None,
) -> List:
    projects: List = []

    if projects_with_namespace is None and namespace is None:
        raise ValueError("Please specify one 'projects_with_namespace' or 'namespace'.")

    if token is None:
        if not os.path.exists(".token"):
            raise ValueError(
                "Can not find gitlab token.\n Please specify 'token' or provide a '.token' file"
            )
        tf = open(".token", "r")
        token = tf.read().rstrip()
        tf.close()
    gl = gitlab.Gitlab(url=git_url, private_token=token)

    if namespace is not None:
        group = gl.groups.get(namespace)
        group_projects = [project for project in group.projects.list()]
        projects = projects + [
            gl.projects.get(project.id) for project in group_projects
        ]

    if projects_with_namespace is not None:
        projects = projects + [
            gl.projects.get(project) for project in projects_with_namespace
        ]

    if len(projects) == 0:
        warnings.warn("Couldn't find any project matching input criteria", UserWarning)

    return projects


def get_files(
    file_path: Union[List, str],
    project: any,
    target_branches: Union[List[str], str] = ["main", "master"],
) -> List:
    files: List = []
    if isinstance(target_branches, str):
        target_branches = [target_branches]
    if isinstance(file_path, str):
        file_path = [file_path]

    bs = project.branches.list(get_all=True)
    bb = [b.name for b in bs if b.name in target_branches]
    if len(bb) == 0:
        warnings.warn(
            f'Could not find branch matching: "{target_branches}" ', UserWarning
        )
        return
    for branch in bb:
        for fi in file_path:
            file = project.files.get(file_path=fi, ref=branch)
            files.append(file)

    if len(files) == 0:
        warnings.warn(f'Could not find any file matching: "{file_path}" ', UserWarning)

    return files


def replace_file_content(
    file: any,
    replace_str: str,
    search_str: re.Pattern,
):
    file_content = base64.b64decode(file.content).decode("utf-8")
    new_file_content = re.sub(search_str, replace_str, file_content)
    return new_file_content


def commit_file(
    project: any,
    file_path: str,
    content: str,
    branch: str,
    action: str = "update",
    commit_msg: str = "new file content",
):
    if action not in ["update", "add"]:
        raise ValueError("Chose one of 'update' or 'add' as commit action.")
    data = {
        "branch": branch,
        "commit_message": "[bulk update]:" + commit_msg,
        "actions": [
            {
                "action": action,
                "file_path": file_path,
                "content": content,
            }
        ],
    }
    commit = project.commits.create(data)
    print(f"Commit ID: \n {commit.id}")


def bulk_file_update(
    file_path: Union[List, str],
    replace_str: str,
    search_str: Optional[str] = None,
    projects_with_namespace: Optional[List[str]] = None,
    namespace: Optional[str] = None,
    dry_run: bool = True,
    commit_msg: str = "modify file content",
    git_url: str = "https://renkulab.io/gitlab",
    token: Optional[str] = None,
    target_branches: Union[List[str], str] = ["main", "master"],
):
    projects = get_projects(
        projects_with_namespace=projects_with_namespace,
        namespace=namespace,
        git_url=git_url,
        token=token,
    )

    print(f'Checking {len(projects)} projects for file updates.')

    for project in projects:
        print("\n\nReading project:")
        print(
            "project_id:"
            + str(project.get_id())
            + "    namespace_name:"
            + project.name_with_namespace
        )
        files = get_files(
            file_path=file_path, project=project, target_branches=target_branches
        )
        for file in files:
            file_mod = replace_file_content(
                file=file,
                replace_str=replace_str,
                search_str=search_str,
            )

            file_content = base64.b64decode(file.content).decode("utf-8")
            if file_content == file_mod:
                print("Nothing to change, continuing to next one...")
                continue
            diff = ndiff(
                file_content.splitlines(keepends=True),
                file_mod.splitlines(keepends=True),
            )
            differences = "".join(diff)
            pattern = r"[-+]\s.*"
            diff_lines = re.findall(pattern, differences)
            x = [i for i in range(1, (len(diff_lines))) if i % 2 != 0]
            print("MODIFICATIONS TO:\n" + file.file_name + "\n at branch: " + file.ref)
            for xi in x:
                print_context(differences, diff_lines[xi])

            if not dry_run:
                commit_file(
                    project=project,
                    file_path=file.file_path,
                    content=file_mod,
                    branch=file.ref,
                    commit_msg=commit_msg,
                )


def bulk_file_add(
    file_path: Union[List, str],
    projects_with_namespace: Optional[List[str]] = None,
    namespace: Optional[str] = None,
    dry_run: bool = True,
    commit_msg: str = "modify file content",
    git_url: str = "https://renkulab.io/gitlab",
    token: Optional[str] = None,
    target_branches: Union[List[str], str] = ["main", "master"],
):
    projects = get_projects(
        projects_with_namespace=projects_with_namespace,
        namespace=namespace,
        git_url=git_url,
        token=token,
    )

    print(f'Adding {file_path} to {len(projects)} projects.')

    for project in projects:
        print("\n\nReading project:")
        print(
            "project_id:"
            + str(project.get_id())
            + "    namespace_name:"
            + project.name_with_namespace
        )

        for branch in target_branches:
            print("ADD NEW FILE:\n" + file_path + "\n at branch: " + branch)
            if not dry_run:
                commit_file(
                    project=project,
                    file_path=file_path,
                    content=open(file_path).read(),
                    branch=branch,
                    action="add",
                    commit_msg=commit_msg,
                )
