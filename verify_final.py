import json, subprocess, urllib.parse

TOKEN = open('/home/hermes/.sonar_token').readline().strip()
BASE = 'https://sast.thempra.net/api'


def get(url):
    out = subprocess.run(['curl', '-s', '-u', f'{TOKEN}:', url],
                         capture_output=True, text=True).stdout
    return json.loads(out)


m = get(BASE + '/measures/component?component=qzero&metricKeys=coverage,bugs,code_smells,vulnerabilities,security_hotspots,reliability_rating,security_rating')
for mm in m['component']['measures']:
    print(mm['metric'], '=', mm['value'])

rel = get(BASE + '/issues/search?componentKeys=qzero&resolved=false&impactSeverities=HIGH,MEDIUM,LOW&impactSoftwareQualities=RELIABILITY&ps=1')
print('issues impacto RELIABILITY abiertos:', rel['paging']['total'])
if rel['issues']:
    d = get(BASE + '/issues/search?componentKeys=qzero&resolved=false&impactSeverities=HIGH,MEDIUM,LOW&impactSoftwareQualities=RELIABILITY&ps=20')
    for i in d['issues']:
        print(' -', i['rule'], i['component'].split(':', 1)[-1], 'line', i['line'], '|', i['message'][:70])

q = get(BASE + '/qualitygates/project_status?projectKey=qzero')
print('GATE:', q['projectStatus']['status'])
