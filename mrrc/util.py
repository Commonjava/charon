import os

def write_file(file_path:str, content:str):
    if not os.path.isfile(file_path):
        with open(file_path, mode='a'): 
            pass
    with open(file_path, mode='w') as f:
        f.write(content)