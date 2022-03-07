#!/usr/bin/env python3

import os
import subprocess
import re
import sys
import json
import datetime
import getpass

# Declare globals
lic_files = 'license_files.txt'
snps_lic = os.environ.get('SNPSLMD_LICENSE_FILE', '27020@cn-asic-01.cornelisnetworks.com')
lmutil = os.environ.get('SCL_ROOT', '/nfs/shares/asic/tools/synopsys/scl/2021.03') + '/linux64/bin/lmutil'
log_path = '/home/' + getpass.getuser() + '/lmstat_poll_logs/'

my_env = os.environ.copy()
my_env['SNPSLMD_LICENSE_FILE'] = snps_lic

# Get the list of license files from accompanying license_files.txt
lic_files_l = []
with open(lic_files) as f:
    lic_files_l = [line.rstrip() for line in f]

lic_usage_l = {}

# Check if the lmstat/lmutil tool exists
if not os.path.exists(lmutil):
    sys.exit('lmutil executable not found!!')


# Lmstat per license file
def run_lmstat(lic_file = ''):

    if(lic_file):
        lmstat_capture = subprocess.check_output([lmutil, 'lmstat', '-a', '-c', lic_file]).decode(sys.stdout.encoding).strip()
    else:
        lmstat_capture = subprocess.check_output([lmutil, 'lmstat', '-a'], env=my_env).decode(sys.stdout.encoding).strip()
    # Verify the captured output for valid markers
    capture_valid = re.search(r'lmutil.*All Rights Reserved', lmstat_capture)
    if not capture_valid:
        sys.exit('lmutil returned unexpected string. Looking for `lmutil - Copyright (c) Flexera. All Rights Reserved.`')
    
    # Get Server informaton
    srv_status = re.search(r'License server status:(.+)', lmstat_capture).group(1)
    
    # Get license file information
    lic_file = re.search(r'License file.+:(.+):', lmstat_capture).group(1)
    
    # Get each feature
    ff = re.split(r'Users of', lmstat_capture)
    ff.pop(0)
    
    # For each feature
    for f in ff:
        fle = list(map(str.lstrip, list(filter(None, f.splitlines())) ));
        
        # Total licenses avail & Licenses in use
        l1 = re.search(r'(.+):.+\(Total of (\d+) licenses? issued;  Total of (\d+) licenses? in use\)', fle[0])
        lic_usage_l[l1.group(1)] = {'total' : l1.group(2), 'used' : l1.group(3), 'users' : []}
    
        # In use by User
        if len(fle) > 1:
            l2 = re.search(r' (v.+?), vendor: (.+?), expiry: (.+)', fle[1])
            lic_usage_l[l1.group(1)]['version'] = l2.group(1)
            lic_usage_l[l1.group(1)]['vendor'] = l2.group(2)
            lic_usage_l[l1.group(1)]['expiry'] = l2.group(3)
    
            l3 = re.search(r'vendor_string: (.+)', fle[2])
    
            for l in fle[4:]:
                lx = re.search(r'(^\w+?) (.+?) .+ \((v.+?)\) \(.+? \d+?\), start (.+)', l)
                lic_usage_l[l1.group(1)]['users'].append([lx.group(1), lx.group(2), lx.group(3), lx.group(4)])
    
# Run lmstat for each license file and append an object to result dictonary
for lfile in lic_files_l:
    run_lmstat(lfile)
run_lmstat()

# Write the results to a JSON file. Create a new file every week (Monday)
if not os.path.isdir(log_path):
    os.makedirs(log_path)

monday = datetime.datetime.today() + datetime.timedelta(days=-datetime.datetime.today().weekday())
logfile = log_path + str(monday.date()) + '.json'

if os.path.isfile(logfile):
    with open(logfile) as rfile:
        data = json.load(rfile)
        #data[str(datetime.datetime.now())] = lic_usage_l
    data.update({ str(datetime.datetime.now()) : lic_usage_l ,})
    
    with open(logfile, 'w') as wfile:
        json.dump(data, wfile)
else:
    with open(logfile, 'w') as outfile:
        json.dump({ str(datetime.datetime.now()) : lic_usage_l ,}, outfile)

