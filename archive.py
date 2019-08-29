import argparse
import os
import sys

import requests


def read_to_be_archived():
    with open(args.filename) as f:
        repos = f.read().splitlines()
    return set(repos)


def print_unarchivable_repos(namespace):
    # finds repos planned to be archived which are *not* in namespace
    opendev_repos = list_opendev_repos(namespace)
    to_be_archived = read_to_be_archived()
    unarchiveable = to_be_archived - opendev_repos
    for repo in unarchiveable:
        print(f'not archived: {repo}')


def find_archivable_repos(namespace):
    # finds repos planned to be archived which are also in namespace
    opendev_repos = list_opendev_repos(namespace)
    to_be_archived = read_to_be_archived()
    return to_be_archived.intersection(opendev_repos)


def list_opendev_repos(namespace):
    data = requests.get(
        f'https://opendev.org/api/v1/orgs/{namespace}/repos').json()
    repos = [r['name'] for r in data]
    return set(repos)


def count_direct_matches():
    # count how many repos in our list are found in the x namespace
    repos = find_archivable_repos('x')
    return len(repos)


def archive_openstack_repo(namespace, repo, github_org):
    url = f'https://api.github.com/repos/{github_org}/{repo}'
    headers = {'Authorization': 'token %s' % TOKEN}
    payload = {
        'description': f'MOVED: now at https://opendev.org/{namespace}/{repo}',
        'archived': True,
    }

    if not args.dryrun:
        res = requests.patch(url, headers=headers, json=payload)
        data = res.json()
    print(f'archived: {repo}')


def archive_repos_in_namespace(namespace):
    github_org = 'openstack'
    repos = find_archivable_repos(namespace)
    for repo in repos:
        archive_openstack_repo(namespace, repo, github_org)


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
    if args.dryrun:
        print('Running in dry run mode, no action will be actually taken')

    TOKEN = os.environ['GITHUB_TOKEN']
    target_namespace = 'x'
    archive_repos_in_namespace(target_namespace)
    print_unarchivable_repos(target_namespace)


if __name__ == '__main__':
    main()
