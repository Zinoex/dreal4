#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
"""Generates a PEP 503 "simple" package index from GitHub release assets.

Every `.whl` / `.tar.gz` attached to any release of the repository is listed,
linking to its GitHub download URL (with its sha256 when GitHub provides one).
The output directory is meant to be deployed to GitHub Pages, so that

    pip install dreal --extra-index-url https://<owner>.github.io/<repo>/simple/

picks the right wheel for the platform automatically.

Usage: make_index.py <owner/repo> <output-dir>
Uses $GITHUB_TOKEN (optional, avoids API rate limits).
"""
import html
import json
import os
import sys
import urllib.request

PROJECT = 'dreal'
REQUIRES_PYTHON = '>=3.8'


def _releases(repo):
    url = 'https://api.github.com/repos/{}/releases?per_page=100'.format(repo)
    headers = {'Accept': 'application/vnd.github+json'}
    if os.environ.get('GITHUB_TOKEN'):
        headers['Authorization'] = 'Bearer ' + os.environ['GITHUB_TOKEN']
    while url:
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request) as response:
            yield from json.load(response)
            url = None
            for part in response.headers.get('Link', '').split(','):
                if 'rel="next"' in part:
                    url = part[part.index('<') + 1:part.index('>')]


def _page(title, links):
    body = '\n'.join('    {}<br/>'.format(link) for link in links)
    return ('<!DOCTYPE html>\n<html>\n  <head>\n'
            '    <meta name="pypi:repository-version" content="1.0">\n'
            '    <title>{0}</title>\n  </head>\n  <body>\n'
            '    <h1>{0}</h1>\n{1}\n  </body>\n</html>\n').format(
                html.escape(title), body)


def main():
    repo, out = sys.argv[1], sys.argv[2]
    files = {}
    for release in _releases(repo):
        if release.get('draft'):
            continue
        for asset in release['assets']:
            name = asset['name']
            if name.startswith(PROJECT + '-') and \
                    name.endswith(('.whl', '.tar.gz')):
                files.setdefault(name, asset)  # Newest release wins.
    if not files:
        sys.exit('No {} wheels or sdists found in releases of {}.'.format(
            PROJECT, repo))

    links = []
    for name in sorted(files):
        asset = files[name]
        url = asset['browser_download_url']
        digest = asset.get('digest') or ''
        if digest.startswith('sha256:'):
            url += '#sha256=' + digest[len('sha256:'):]
        links.append('<a href="{}" data-requires-python="{}">{}</a>'.format(
            html.escape(url), html.escape(REQUIRES_PYTHON),
            html.escape(name)))

    os.makedirs(os.path.join(out, 'simple', PROJECT), exist_ok=True)
    with open(os.path.join(out, 'simple', PROJECT, 'index.html'), 'w') as f:
        f.write(_page('Links for ' + PROJECT, links))
    with open(os.path.join(out, 'simple', 'index.html'), 'w') as f:
        f.write(_page('Simple index', [
            '<a href="{0}/">{0}</a>'.format(PROJECT)]))

    owner, name = repo.split('/')
    index_url = 'https://{}.github.io/{}/simple/'.format(owner.lower(), name)
    with open(os.path.join(out, 'index.html'), 'w') as f:
        f.write(_page('dReal wheels', [
            'pip install dreal --extra-index-url {}'.format(
                html.escape(index_url)),
            '<a href="simple/">simple/</a> ({} files)'.format(len(files)),
        ]))
    print('Wrote index with {} files to {}'.format(len(files), out))


if __name__ == '__main__':
    main()
