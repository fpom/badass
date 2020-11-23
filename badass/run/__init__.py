"""
firejail --name=test --quiet --overlay-tmpfs --allow-debuggers /bin/sh

firejail --quiet --ls=test .
firejail --quiet --get=test test/a.out

"""
