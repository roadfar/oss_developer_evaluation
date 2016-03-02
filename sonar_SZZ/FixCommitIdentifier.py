import csv
import re
import time

import pymysql

space = r'[# \?\t:\-\(\[\_]*'
prf = r'(fix|clos|resolv|see)(e[ds]|ing)?'
mid = r'(issu|bug|ticket|address)e?s?'
end = r'([0-9]+)'

string_id = r'(#|(gh\-))' + end
string_link = r'/issues/' + end
string_fix = prf + space + r'('+ mid + r')*' + space + end
string_bug = r'('+ prf + r')*' + space + mid + space + end

#string_fix = r'fix(e[ds]|ing)?[# \t]*(issue|bug)*[# \t]*([0-9]+)'
#string_close = r'close([ds]|ing)?[# \t]*(issue|bug)*[# \t]*([0-9]+)'
#string_resolve = r'resolve[ds]?|resolving[# \t]*(issue)*[# \t]*[0-9]+'

conn = pymysql.connect(host='127.0.0.1', port=3306,
                       user='root', passwd='891028',
                       db='github',charset="utf8")

def issueMatch(message):
    buf = message.lower()
    pattern_fix = re.compile(string_fix)
    pattern_bug = re.compile(string_bug)
    pattern_link = re.compile(string_link)
    pattern_id = re.compile(string_id)
    #print(string_fix, string_bug)
    match = pattern_fix.search(buf)
    if match:
        #print (match)
        return match
    else:
        match = pattern_bug.search(buf)
        if match:
            return match
        else:
            match = pattern_link.search(buf)
            if match:
                return match
            else:
                match = pattern_id.search(buf)
                if match:
                    return match
                else:
                    return -1;

def updateIssueId(conn, index, issue_id):
    cur = conn.cursor()
    sql = "update commits set issue_id={0} \
        where id={1}".format(issue_id, index)
    #print(sql)
    try:
        cur.execute(sql)
    except Exception:
        print('update database error')

def issueUpdate(seed_file):
    with open(seed_file) as seed:
        reader = csv.reader(seed)
        next(reader, None)
        for line in reader:
            print (line)
            cur = conn.cursor()
            sql = "select id, message from commits where repo_id="+line[0]+";"
            cur.execute(sql)
            for row in cur:
                #print(row)
                id = row[0]
                #message = row[1].replace('-',' ')
                message = row[1]
                #issue_id = row[2]
                #print('commit: ' + message)
                m = issueMatch(message)
                if m != -1:
                    print('commit: ' + message)
                    pts = m.groups()
                    issue_id = pts[len(pts)-1]
                    print('issue_id:' + issue_id)
                    updateIssueId(conn, id, issue_id)
            cur.close()
    seed.close()
    conn.close()

if __name__ == "__main__":
    #updateCISkip('D:/doi/seed_tag.csv')

    issueUpdate('/Users/dreamteam/Documents/study/sonar/script/negative_contributor_measurement/ruby_top10.csv')
    # print issueMatch("Merge pull request #312 from msabramo/patch-5 tox.ini: Use pytest-httpbin>=0.0.6")