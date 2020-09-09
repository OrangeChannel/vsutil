# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.

import os
import sys

sys.path.insert(0, os.path.abspath('..'))


# -- Project information -----------------------------------------------------

project = 'vsutil'
copyright = '2020, Irrational Encoding Wizardry'
author = 'Irrational Encoding Wizardry'

# The full version, including alpha/beta/rc tags
version = release = '0.5.0'


# -- General configuration ---------------------------------------------------

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.todo',
    'sphinx.ext.viewcode',
    'sphinx_autodoc_typehints',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

html_css_files = [
    'css/theme_overrides.css'
]

html_style = 'css/theme_overrides.css'

autosummary_generate = True
autodoc_mock_imports = ['vapoursynth']
smartquotes = True
html_show_sphinx = False
# add_module_names = False
pygments_style = 'sphinx'

from docutils import nodes


class releasechange_node(nodes.Structural, nodes.Element):
    pass


from collections import namedtuple
from typing import Any, Dict, List
from typing import cast

from docutils import nodes
from docutils.nodes import Node

from sphinx import addnodes
from sphinx.domains import Domain
from sphinx.locale import _
from sphinx.util.docutils import SphinxDirective


versionlabels = {
    'versionadded2':   _('New in release R%s'),
    'versionchanged2': _('Changed in release R%s'),
    'deprecated2':     _('Deprecated since release R%s'),
}

versionlabel_classes = {
    'versionadded2':     'added2',
    'versionchanged2':   'changed2',
    'deprecated2':       'deprecated2',
}


# TODO: move to typing.NamedTuple after dropping py35 support (see #5958)
ChangeSet = namedtuple('ChangeSet',
                       ['type', 'docname', 'lineno', 'module', 'descname', 'content'])


class VersionChange(SphinxDirective):
    """
    Directive to describe a change/addition/deprecation in a specific version.
    """
    has_content = True
    required_arguments = 1
    optional_arguments = 1
    final_argument_whitespace = True
    option_spec = {}  # type: Dict

    def run(self) -> List[Node]:
        node = addnodes.versionmodified()
        node.document = self.state.document
        self.set_source_info(node)
        node['type'] = self.name
        node['version'] = self.arguments[0]
        text = versionlabels[self.name] % self.arguments[0]
        if len(self.arguments) == 2:
            inodes, messages = self.state.inline_text(self.arguments[1],
                                                      self.lineno + 1)
            para = nodes.paragraph(self.arguments[1], '', *inodes, translatable=False)
            self.set_source_info(para)
            node.append(para)
        else:
            messages = []
        if self.content:
            self.state.nested_parse(self.content, self.content_offset, node)
        classes = ['versionmodified', versionlabel_classes[self.name]]
        if len(node):
            if isinstance(node[0], nodes.paragraph) and node[0].rawsource:
                content = nodes.inline(node[0].rawsource, translatable=True)
                content.source = node[0].source
                content.line = node[0].line
                content += node[0].children
                node[0].replace_self(nodes.paragraph('', '', content, translatable=False))

            para = cast(nodes.paragraph, node[0])
            para.insert(0, nodes.inline('', '%s: ' % text, classes=classes))
        else:
            para = nodes.paragraph('', '',
                                   nodes.inline('', '%s.' % text,
                                                classes=classes),
                                   translatable=False)
            node.append(para)

        domain = cast(ChangeSetDomain2, self.env.get_domain('changeset'))
        domain.note_changeset(node)

        ret = [node]  # type: List[Node]
        ret += messages
        return ret


class ChangeSetDomain2(Domain):
    """Domain for changesets."""

    name = 'changeset2'
    label = 'changeset2'

    initial_data = {
        'changes': {},      # version -> list of ChangeSet
    }  # type: Dict

    @property
    def changesets(self) -> Dict[str, List[ChangeSet]]:
        return self.data.setdefault('changes', {})  # version -> list of ChangeSet

    def note_changeset(self, node: addnodes.versionmodified) -> None:
        version = node['version']
        module = self.env.ref_context.get('py:module')
        objname = self.env.temp_data.get('object')
        changeset = ChangeSet(node['type'], self.env.docname, node.line,
                              module, objname, node.astext())
        self.changesets.setdefault(version, []).append(changeset)

    def clear_doc(self, docname: str) -> None:
        for version, changes in self.changesets.items():
            for changeset in changes[:]:
                if changeset.docname == docname:
                    changes.remove(changeset)

    def merge_domaindata(self, docnames: List[str], otherdata: Dict) -> None:
        # XXX duplicates?
        for version, otherchanges in otherdata['changes'].items():
            changes = self.changesets.setdefault(version, [])
            for changeset in otherchanges:
                if changeset.docname in docnames:
                    changes.append(changeset)

    def process_doc(self, env: "BuildEnvironment", docname: str, document: nodes.document) -> None:  # NOQA
        pass  # nothing to do here. All changesets are registered on calling directive.

    def get_changesets_for(self, version: str) -> List[ChangeSet]:
        return self.changesets.get(version, [])


def setup(app) -> Dict[str, Any]:
    app.add_domain(ChangeSetDomain2)
    app.add_directive('deprecated2', VersionChange)
    app.add_directive('versionadded2', VersionChange)
    app.add_directive('versionchanged2', VersionChange)

    return {
        'version': 'builtin',
        'env_version': 1,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }



# -- Extension configuration -------------------------------------------------

todo_include_todos = True
