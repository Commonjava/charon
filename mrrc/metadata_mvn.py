from .util import write_file
from typing import Dict, List, Tuple, Union
from jinja2 import Template
from datetime import datetime
import os

class MavenMetadata(object):
    """ This MavenMetadata will represent a maven-metadata.xml data content which will be
        used in jinja2 or other places
    """
    def __init__(self, group_id: str, artifact_id: str):
        self.group_id = group_id
        self.artifact_id = artifact_id
        self.last_upd_time = datetime.now().strftime('%Y%m%d%H%M%S')

    def generate_meta_file_content(self) -> str:
        template = Template(get_mvn_template())
        return template.render(meta=self)

    def versions(self, *vers: str):
        self.vers=list(vers)
        return self
    
    def latest_version(self, latest_version: str):
        self.latest_ver = latest_version
        return self
    
    def release_version(self, release_version: str):
        self.release_ver = release_version
        return self
    
    def __str__(self) -> str:
        return f'{self.group_id}:{self.artifact_id}\n{self.vers}\n\n'


def get_mvn_template() -> str:
    """Gets the jinja2 template file content for maven-metadata.xml generation
    """
    DEFAULT_MVN_TEMPLATE = os.path.join(os.environ['HOME'], '.mrrc/template/maven-metadata.xml.j2')
    with open(DEFAULT_MVN_TEMPLATE) as file_:
        return file_.read()

def scan_for_poms(full_path: str) -> List[str]:
    """Scan a file path and finds all pom files absolute paths
    """
    # collect poms
    all_pom_paths = list()
    for (dir,_,names) in os.walk(full_path):
        single_pom_paths=[os.path.join(dir,n) for n in names if n.endswith('.pom')]
        all_pom_paths.extend(single_pom_paths)
    return all_pom_paths

def parse_ga(full_ga_path: str, root="/") -> Tuple[str, str]:
    """Parse maven groupId and artifactId from a standard path in a local maven repo.
       e.g: org/apache/maven/plugin/maven-plugin-plugin -> (org.apache.maven.plugin, maven-plugin-plugin)
       root is like a prefix of the path which is not part of the maven GAV
    """
    slash_root = root
    if not root.endswith("/"):
        slash_root = slash_root + '/'
    
    ga_path = full_ga_path
    if ga_path.startswith(slash_root):
        ga_path = ga_path[len(slash_root):]
    if ga_path.endswith("/"):
        ga_path = ga_path[:-1]
    
    items = ga_path.split("/")
    artifact = items[len(items)-1]
    group=".".join(items[:-1])
    
    return group, artifact


def __parse_gav(full_artifact_path: str, root="/") -> Tuple[str, str, str]:
    """Parse maven groupId, artifactId and version from a standard path in a local maven repo.
       e.g: org/apache/maven/plugin/maven-plugin-plugin/1.0.0/maven-plugin-plugin-1.0.0.pom 
       -> (org.apache.maven.plugin, maven-plugin-plugin, 1.0.0)
       root is like a prefix of the path which is not part of the maven GAV
    """
    slash_root = root
    if not root.endswith("/"):
        slash_root = slash_root + '/'
    
    ver_path = full_artifact_path
    if ver_path.startswith(slash_root):
        ver_path = ver_path[len(slash_root):]
    if ver_path.endswith("/"):
        ver_path = ver_path[:-1]
    
    items = ver_path.split("/")
    version = items[-2]
    artifact = items[-3]
    group=".".join(items[:-3])
    
    return group, artifact, version

def parse_gavs(pom_paths:list, root='/') -> Dict[str, Dict[str, List[str]]]:  
    """Give a list of paths with pom files and parse the maven groupId, artifactId and version 
       from them. The result will be a dict like {groupId: {artifactId: [versions list]}}.
       Root is like a prefix of the path which is not part of the maven GAV
    """
    gavs = dict()
    for pom in pom_paths:
        (g, a, v) = __parse_gav(pom, root)
        avs = gavs.get(g, dict())
        vers = avs.get(a, list())
        vers.append(v)
        avs[a] = vers
        gavs[g] = avs
    return gavs

def gen_meta_content(g,a: str, vers: list) -> MavenMetadata:  
    sorted_vers = sorted(vers, key=ver_cmp_key())
    meta = MavenMetadata(g,a)
    meta.latest_version(sorted_vers[-1]).release_version(sorted_vers[-1]).versions(*sorted_vers)
    return meta

def gen_meta_file(g, a: str, vers:list, root="/"):
    content = gen_meta_content(g, a, vers).generate_meta_file_content()
    g_path = '/'.join(g.split("."))
    final_meta_path = os.path.join(root, g_path, a, 'maven-metadata.xml')
    try:
        write_file(final_meta_path, content)
    except FileNotFoundError:
        print(f'Can not create file {final_meta_path} because of some missing folders')
    
def ver_cmp_key():
    'Used as key function for version sorting'
    class K:
        def __init__(self, obj):
            self.obj = obj
        def __lt__(self, other):
            return self.__compare(other) < 0
        def __gt__(self, other):
            return self.__compare(other) > 0
        def __eq__(self, other):
            return self.__compare(other) == 0
        def __compare(self, other) -> int:
            xitems = self.obj.split(".")
            yitems = other.obj.split(".")
            big = max(len(xitems), len(yitems))
            for i in range(big):
                xitem, yitem=None, None
                try: 
                    xitem = xitems[i]
                except IndexError:
                    return -1
                try: 
                    yitem = yitems[i]
                except IndexError:
                    return 1
                if xitem.isnumeric() and yitem.isnumeric():
                    xitem = int(xitem)
                    yitem = int(yitem)
                if xitem > yitem:
                    return 1
                elif xitem < yitem:
                    return -1
                else:
                    continue
            return 0
    return K

