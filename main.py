# Copyright 2022 Nathaniel Tracy-Amoroso
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the "Software"), to deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the
# Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
# WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS
# OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from typing import List, Set
import pygraphviz
import networkx as nx
import sys
import yaml
import os
import subprocess
from sys import platform


def usage():
    print("Usage: ./azure-dag file1.yml file2.yml ....")
    sys.exit(-1)


def display_file(path):
    norm_path = os.path.normpath(path)
    if platform == "linux" or platform == "linux2":
        print(f"Please open the image @ ${path}")
    elif platform == "darwin":
        # thank you: https://stackoverflow.com/questions/3520493/python-show-in-finder
        subprocess.call(["open", "-R", norm_path])
    elif platform == "win32":
        # thank you:  https://www.codegrepper.com/code-examples/python/how+to+open+file+explorer+in+python
        filebrowser_path = os.path.join(os.getenv('WINDIR'), 'explorer.exe')
        subprocess.run([filebrowser_path, '/select,', os.path.normpath(norm_path)])


def search_yaml(yaml_obj, graph: nx.DiGraph, templates_found: List[str]):
    if isinstance(yaml_obj, dict):
        for (key, val) in yaml_obj.items():
            if key == "template":
                if isinstance(val, str) and not str(val).lstrip().startswith("${{"):
                    templates_found.append(val.replace("\\", "/"))
                    return
            search_yaml(val, graph, templates_found)
    elif isinstance(yaml_obj, list):
        for item in yaml_obj:
            search_yaml(item, graph, templates_found)
    else:
        return


def remove_common_prefix(src, dest, remove_prefix=None):
    if remove_prefix is not None:
        ret = os.path.realpath(src).removeprefix(remove_prefix), os.path.realpath(dest).removeprefix(remove_prefix)
    else:
        ret = src, dest
    return ret


def analyze_file(path, graph: nx.DiGraph, seen: Set[str], remove_prefix=None):
    with open(path, "r") as stream:
        try:
            yaml_content = yaml.safe_load(stream)
            templates_found = []
            search_yaml(yaml_content, graph, templates_found)
            for template in templates_found:
                template_path = os.path.join(os.path.dirname(path), template)
                src, dest = remove_common_prefix(path, template_path, remove_prefix)
                if dest not in seen:
                    graph.add_node(dest)
                    graph.add_edge(src, dest)
                    seen.add(dest)
                    analyze_file(template_path, graph, seen, remove_prefix=remove_prefix)
                else:
                    graph.add_edge(src, dest)

        except yaml.YAMLError as exc:
            print(f"Something went wrong parsing the YAML in this file '{path}'\nError: {exc}")
            sys.exit(-1)


def build_graph(entry_points: List[str], remove_prefix=None) -> nx.DiGraph:
    seen = set()
    graph = nx.DiGraph()

    for entry in entry_points:
        analyze_file(entry, graph, seen, remove_prefix=remove_prefix)
    return graph


if len(sys.argv) < 2:
    usage()

entry_points = [os.path.realpath(path) for path in sys.argv[1:]]

first_graph = build_graph(entry_points)
if len(first_graph.nodes) <= 1:
    print(f"There is only one file found in this tree: {entry_points}, we can't make a meaningful graph out of that.")
    sys.exit(0)
common_prefix = os.path.realpath(os.path.commonprefix(list(first_graph.nodes)))
final_graph = build_graph(entry_points, remove_prefix=common_prefix)

A = nx.nx_agraph.to_agraph(final_graph)
A.edge_attr.update(minlen='3')
A.layout('dot', args='-Elen=50 -Nfontsize=20 -Nwidth=".2" -Nheight=".2" -Nmargin=0 -Gfontsize=20', )

output_png = 'py-azure-dag.png'
A.draw(output_png)
display_file(output_png)
