import argparse
import os
import sys
import yaml


def build_map(filenames, nsfrom):
    new_to_old = {}
    for fn in filenames:
        renames = yaml.safe_load(open(fn, 'r'))
        for repo in renames['repos']:
            old = repo['old']
            new = repo['new']
            if old in new_to_old:
                # Transitive move. Handle:
                # - old: openstack/pyeclib
                #   new: x/pyeclib
                # - old: x/pyeclib
                #   new: openstack/pyeclib
                old_old = new_to_old[old]
                del new_to_old[old]

                new_to_old[new] = old_old
            else:
                new_to_old[new] = old

    # Now we have the whole list, pick out things starting with opendev/
    return {
        old: new for new, old in new_to_old.items()
        if old.startswith(f'{nsfrom}/') and not new.startswith(f'{nsfrom}/')
    }


def main(args=sys.argv[1:]):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'filename',
        nargs='+',
        help='infra rename files to process')
    parser.add_argument(
        '--from_ns',
        default='openstack',
        help='Only consider projects that were renamed from this namespace')
    args = parser.parse_args(args)
    mapping = build_map(args.filename, args.from_ns)
    yaml.dump(mapping, sys.stdout, default_flow_style=False)


if __name__ == '__main__':
    main()
