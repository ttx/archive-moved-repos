import argparse
import os
import sys
import tempfile
import yaml

import requests


def load_mapping(token, filename):
    mapping = yaml.safe_load(open(filename, 'r'))

    opendev_repos = {}
    checked_mapping = {}
    print("Validating proposed renames...")

    # Check that repos are really where we think they are
    for old, new in mapping.items():
        nsold, repoold = old.split('/')
        ns, repo = new.split('/')

        # Check old repository is still in github (and in openstack namespace)
        url = f'https://api.github.com/repos/{nsold}/{repoold}'
        if token:
            headers = {'Authorization': 'token %s' % token}
            res = requests.get(url, headers=headers)
        else:
            res = requests.get(url)
        if res.status_code == 403:
            print(f'Hitting GitHub ratelimits, consider using a token')
            sys.exit(1)
        if res.status_code != 200:
            print(f'skipping {nsold}/{repoold} (not found in github)')
            continue
        data = res.json()
        if data['archived']:
            print(f'skipping {nsold}/{repoold} (already archived in github)')
            continue
        if not data['full_name'].startswith('openstack/'):
            print(f'skipping {nsold}/{repoold} (not openstack/ org on github)')
            continue

        # Check new repository is in opendev (and not in openstack namespace)
        if ns not in opendev_repos:
            # Cache opendev org repo lists for performance
            data = requests.get(
                f'https://opendev.org/api/v1/orgs/{ns}/repos').json()
            opendev_repos[ns] = [r['name'] for r in data]
        if repo not in opendev_repos[ns]:
            print(f'skipping {repo} (not found in opendev {ns}/ namespace)')
            continue
        if ns == 'openstack':
            print(f'skipping {repo} (found in opendev openstack/ namespace)')
            continue

        checked_mapping[old] = new

    return checked_mapping


def push_clean_commit(token, nsgh, repo, nsnew, reponew):
    previous_dir = os.getcwd()
    with tempfile.TemporaryDirectory() as tmpdirname:
        os.chdir(tmpdirname)
        os.system(f"git clone git@github.com:{nsgh}/{repo} .")
        os.system("git rm -r * $(find . -maxdepth 1 -path './\.??*' -not -path './\.git')")
        with open('README.md', 'w') as readme:
            readme.write("# This repo has moved to OpenDev\n\n")
            readme.write(f"It can now be found at [https://opendev.org/{nsnew}/{reponew}](https://opendev.org/{nsnew}/{reponew})\n")
        os.system("git add README.md")
        os.system("git commit -m'Retire github mirror, repo moved to opendev'")
        if token:
            os.system("git push origin")
        os.chdir(previous_dir)
    print(f'pushed clean commit on GitHub for: {nsgh}/{repo}')


def archive_openstack_repo(token, nsgh, repo, nsnew, reponew):
    url = f'https://api.github.com/repos/{nsgh}/{repo}'
    headers = {'Authorization': 'token %s' % token}
    payload = {
        'description': f'MOVED: now at https://opendev.org/{nsnew}/{reponew}',
        'archived': True,
    }
    if token:
        res = requests.patch(url, headers=headers, json=payload)
        data = res.json()

    print(f'archived: {nsgh}/{repo} (moved to {nsnew}/ on opendev)')


def main(args=sys.argv[1:]):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'mappingfile',
        help='mapping file detailing the moves')
    parser.add_argument(
        '--dryrun',
        default=False,
        help='do not actually do anything',
        action='store_true')
    parser.add_argument(
        '--only-validate',
        default=False,
        help='Only validate proposed renames',
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

    mapping = load_mapping(token, args.mappingfile)
    if not args.only_validate:
        for old, new in mapping.items():
            nsold, repoold = old.split('/')
            nsnew, reponew = new.split('/')
            push_clean_commit(token, nsold, repoold, nsnew, reponew)
            archive_openstack_repo(token, nsold, repoold, nsnew, reponew)


if __name__ == '__main__':
    main()
