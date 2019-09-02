import argparse
import os
import sys

import requests


def read_to_be_archived(filename):
    with open(filename) as f:
        repos = f.read().splitlines()
    return repos


def find_archivable_repos(filename):
    opendev_repos = {}
    archivable_repos = []
    to_be_archived = read_to_be_archived(filename)

    for reponame in to_be_archived:
        ns, repo = reponame.split('/')
        if ns not in opendev_repos:
            data = requests.get(
                f'https://opendev.org/api/v1/orgs/{ns}/repos').json()
            opendev_repos[ns] = [r['name'] for r in data]
        if repo not in opendev_repos[ns]:
            print(f'not archived: {repo} (not in opendev {ns}/ namespace)')
        else:
            archivable_repos.append((ns, repo))

    return archivable_repos


def archive_openstack_repo(token, namespace, repo, github_org):
    # Specific hack to handle openstack/stx-foo -> starlingx/foo rename
    if namespace == 'starlingx':
        url = f'https://api.github.com/repos/{github_org}/stx-{repo}'
    else:
        url = f'https://api.github.com/repos/{github_org}/{repo}'
    headers = {'Authorization': 'token %s' % token}
    payload = {
        'description': f'MOVED: now at https://opendev.org/{namespace}/{repo}',
        'archived': True,
    }
    if token:
        res = requests.patch(url, headers=headers, json=payload)
        data = res.json()

    print(f'archived: {github_org}/{repo} (moved to {namespace}/ on opendev)')


def main(args=sys.argv[1:]):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'filename',
        help='file detailing the moves')
    parser.add_argument(
        '--dryrun',
        default=False,
        help='do not actually do anything',
        action='store_true')
    args = parser.parse_args(args)

    try:
        token = os.environ['GITHUB_TOKEN']
    except KeyError:
        token = None
        print('Missing GITHUB_TOKEN, no action will be actually taken')

    if args.dryrun:
        token = None
        print('Running in dry run mode, no action will be actually taken')

    github_org = 'openstack'
    repos = find_archivable_repos(args.filename)
    for namespace, repo in repos:
        archive_openstack_repo(token, namespace, repo, github_org)


if __name__ == '__main__':
    main()
