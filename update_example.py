from file_update import bulk_file_update
import re

### ---------------------- Specify parameter -------------------- ### 

# Path to the file that shall be modified:
file_path = "requirements.txt"

# Regular expression to what shall be replaced:
target_search = 'git+https://github.com/omnibenchmark/omnibenchmark-py'
search_str = re.compile(r'^' + re.escape(target_search) + r'.*', re.MULTILINE)
#target_str = 'git+https://github.com/omnibenchmark/omnibenchmark-py@353d76961d2bb7ca565a29ac7c60784a1f06c015'
#search_str = re.escape(target_str)

# Replacement in the file:
replace_str= "omnibenchmark==0.0.46"

# Namespace of all projects that shall be replaced (alternatively use 'projects_with_namespace'):
namespace = 'omnibenchmark/iris_example'

# Check first:
dry_run = True

# Commit message for all changes:
commit_msg = "update to omnibenchmark-py 0.0.46"

# Specify token as parameter or store in.token 

### ------------------------------------------------------------- ###

if __name__ == "__main__":
    bulk_file_update(file_path = file_path, 
                     replace_str = replace_str,
                     search_str = search_str,
                     namespace = namespace,
                     dry_run = dry_run,
                     commit_msg = commit_msg)