'''
Created on 2015.05.25

@author: Fisher Yu
'''

import csv
import datetime
import os
import re
import sys
import time

import git
import pymysql
from unidiff import PatchSet

import MyTools

path = r'C:\Users\Fisher\Desktop\rails'
#path = 'D:/doi/rcode'
log_path = path + r'\log.txt'
sha_p = r'commit [a-fA-F0-9]{32,32}'
diff_p = r'diff --git '

#log_base = 'G:/doi/log/'
path_base = 'G:/doi/'
proj_lang = ''
repo_name = ''
proj_id = ''
n_blame_error = 0
#mysql connection
conn = pymysql.connect(host='127.0.0.1', port=3306,
                       user='root', passwd='influx1234',
                       db='github',charset="utf8")
inner = conn.cursor()
deadline = "2014-11-10 00:00:00"

def MySzzMySql(seed_file):
    with open(seed_file) as seed:
        reader = csv.reader(seed)
        next(reader, None)
        for line in reader:
            global proj_id, repo_name, proj_lang
            proj_id = line[0]
            repo_name = line[1]
            proj_lang = line[3]
            print(proj_id, repo_name, proj_lang)
            diff_path = path_base + '/logall/' + repo_name + '~' + proj_id
            proj_path = path_base + '/projects/' + proj_id
            cur = conn.cursor()
            sql = "select sha, issue_id, pi.created_at from commit_details_all cd, pr_issue_crawler pi \
                where cd.proj_id=%d and pi.proj_id =%d and pr_diff='null' and \
                issue_id is not null and issue_id=github_id and pi.created_at<'%s' and bug_tag=1 \
                and n_dels>0 and n_dels<=10000 and n_adds<=10000;" \
                % (int(proj_id), int(proj_id), deadline)
            cur.execute(sql)
            fix_com_map = {}
            for row in cur:
                fix_sha = row[0]
                issue_id = row[1]
                issue_open_date = row[2]
                fix_com_map[fix_sha] = (issue_id, issue_open_date)
            if len(fix_com_map)>0:
                MyGitLogParser(proj_path, diff_path, fix_com_map)

'''
Parse all fix_commit of a given project
'''
def MyGitLogParser(proj_path, log_path, fix_commit_map):
    with open(log_path, encoding='ISO-8859-1') as log_diff:
        #for line in log_diff:
        line = log_diff.readline()
        while line:
            if re.match(sha_p, line):
                #remove 'commit ' and \n
                fix_sha = line[7:-1]
                if len(fix_commit_map)<1:
                    print('All fix commits are finded: ' + log_path)
                    return
                if fix_sha in fix_commit_map:
                    print("find: ", fix_sha)
                    diff = []
                    while 1:
                        next_line = log_diff.readline()
                        #find diff structure
                        if re.match(diff_p, next_line):
                            #get the content around diff structure
                            while re.match(sha_p, next_line) == None and next_line:
                                diff.append(next_line)
                                next_line = log_diff.readline()
                                #ignore too hug hunk <=5000 lines of code.
                                #if len(diff) > 5000:
                                #    print("Too big: ", fix_sha)
                                #    break
                            #out diff structure loop
                            break
                    #extract diff information
                    line = next_line
                    name_file_line = MydiffParser(diff)
                    #clean memory
                    del diff[:]
                    if len(name_file_line) > 0:
                        #find suspicious file and line
                        #try:
                        #    print(name_file_line)
                        #except:
                        #    print("file line name error")
                        #get buggy provenance annotation
                        issue_id = fix_commit_map[fix_sha][0]
                        issue_open_date = fix_commit_map[fix_sha][1]
                        buggy_set = MyblameExtrator(proj_path, fix_sha,
                                         issue_open_date, name_file_line, issue_id)
                        if n_blame_error > 100:
                            print("Too many blame error, exit!")
                            os._exit(1)
                        '''
                        if len(buggy_set)>0:
                            global proj_id, repo_name, proj_lang
                            BuggyToMysql(buggy_set, fix_sha, fix_commit_map[fix_sha])
                            #clean memory
                            del buggy_set[:]
                            gc.collect()
                        else:
                            print(fix_sha,': no buggy set')
                        '''
                        if buggy_set==0:
                            print(fix_sha,': no buggy set')
                    else:
                        print(fix_sha,': have no delete buggy_line')
                    #delete this fix_sha from map
                    del fix_commit_map[fix_sha]
                    print(proj_id, 'remove: ' + fix_sha, len(fix_commit_map))
                else:
                    line = log_diff.readline();
            else:
                line = log_diff.readline();
    #log unmatch sha and see why
    if len(fix_commit_map)>0:
        print("fix_sha no match: ", len(fix_commit_map))
        InsertLog(fix_commit_map)
    log_diff.close()

def InsertLog(fix_commit_map):
    global proj_id
    ist = conn.cursor()
    for fix_sha in fix_commit_map:
        sql = "insert into szz_raw_log(proj_id,fix_sha) \
        values ('%d', '%s')" % (int(proj_id), fix_sha)
        ist.execute(sql)
    ist.close();

'''
return a hashmap:
file_name,suspicious_line_id
'''
def MydiffParser(diff):
    file_line = {}
    try:
        patch_set = PatchSet(diff)
    except:
        print('patch init error!')
        return file_line
    for pt in patch_set:
        #only analyze first 100 files
        #if len(file_line) >= 100:
        #    break;
        if pt.removed>0:
            fname = pt.source_file
            #remove 'a/'
            index = fname.find('/')
            if index != -1:
                fname = fname[index+1:] #add a pisition of '/'
            else:
                print('file path type error!')
                #os.system("pause")
            file_type = MyTools.MyfiletypeJudger(pt.source_file, proj_lang, repo_name)
            #ignore doc file
            if file_type == MyTools.DOC_FILE:
                continue
            line_set = []
            for hunk in pt:
                #if len(line_set)>500:
                #    break
                for line in hunk:
                    if line.is_removed:
                        code_type = MyTools.MychangeCodeJuder(line.value)
                        if code_type == MyTools.CG_CODE:
                            line_set.append(line.source_line_no)
                            #only anaylze first 500 change lines in one files (hunk)
                            #if over 500 probably come from the same commits.
                            #if len(line_set)>500:
                            #    break
            if len(line_set)>0:
                file_line[fname]=line_set
    return file_line

'''
use blame to get buggy provenance annotation
return an tuple_set which can easy to insert into mysql
(fix_file,fix_line,buggy_sha,buggy_file,buggy_line)
'''
def MyblameExtrator(proj_path, fix_sha, issue_open_date, buggy_set, issue_id):
    global n_blame_error
    #buggy_tuple_set = []
    buggy_tuple_set = 0
    g = git.Repo(proj_path)
    for fix_file in buggy_set:
        for fix_line in buggy_set[fix_file]:
            try:
                blame_info = g.git.blame('--abbrev=40', fix_sha+'^', \
                                     '-w', '-M', '-C', '-C', '-n', '-f', \
                                     '-L {0},+1'.format(fix_line), '--', fix_file)
            except Exception:
                print ('git blame error')
                n_blame_error = n_blame_error + 1
                time.sleep(2)
                continue
            #print (blame_info)
            #buggy_SHA_date = re.findall(r'\d{4}-\d{2}-\d{2}', blame_info)[0]
            try:
                buggy_SHA_date = re.findall(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} [\+\-]\d{4}', blame_info)[0]
            except:
                print('SHA_date extract error!')
                continue
            b_date = datetime.datetime.strptime(buggy_SHA_date, "%Y-%m-%d %H:%M:%S %z")
            i_date = datetime.datetime.strptime(issue_open_date+' -0700', "%Y-%m-%d %H:%M:%S %z") #davis time zone
            innocent = 0;
            if b_date > i_date:
                innocent = 1
                #print ('find a innocent code!')
            buggy_line = blame_info.split('(')[0].split()[-1]
            try:
                buggy_line_num = int(buggy_line)
            except:
                buggy_line_num = 0
            buggy_SHA = blame_info.split()[0][-40:]
            buggy_file_path = ' '.join(blame_info.split('(')[0].split()[1:-1])
            #print (buggy_SHA_date, buggy_line_num)
            #buggy_tuple_set.append((fix_file,fix_line,buggy_SHA,
            #                        buggy_file_path,int(buggy_line_num),innocent))
            '''
            Change to use insert into database each blame result
            '''
            buggy_tuple = (fix_file,fix_line,buggy_SHA,\
                           buggy_file_path,int(buggy_line_num),innocent)
            EachBlameBuggyToMysql(buggy_tuple,issue_id,fix_sha)
            buggy_tuple_set = buggy_tuple_set + 1
    return buggy_tuple_set

'''
Insert raw data each blame.
'''
def EachBlameBuggyToMysql(buggy, issue_id, fix_sha):
    global proj_id, repo_name, proj_lang, inner
    file_type = MyTools.MyfiletypeJudger(buggy[0], proj_lang, repo_name)
    item = (int(proj_id),issue_id,fix_sha,file_type,)+buggy
    in_sql = ("insert into szz_raw(proj_id, issue_id, \
            fix_sha, file_type, fix_file, fix_line, \
            buggy_sha, buggy_file, buggy_line, innocent) values \
            ('%d','%d','%s', '%d','%s','%d','%s','%s','%d', '%d')" % item)
    try:
        inner.execute(in_sql)
    except:
        print('insert buggy item error')
        print(in_sql)
    #print (proj_id,issue_id,fix_sha,buggy[0],buggy[1])
    #print (proj_id,issue_id,buggy[1])

'''
Insert raw structure data to Mysql database
'''
def BuggyToMysql(buggy_set, fix_sha, fix_tuple):
    global proj_id, repo_name, proj_lang, inner
    for buggy in buggy_set:
        file_type = MyTools.MyfiletypeJudger(buggy[0], proj_lang, repo_name)
        #item = (int(proj_id),issue_id,fix_sha,file_type,)+buggy
        item = (int(proj_id),fix_tuple[0],fix_sha,file_type,)+buggy
        in_sql = ("insert into szz_raw(proj_id, issue_id, \
                fix_sha, file_type, fix_file, fix_line, \
                buggy_sha, buggy_file, buggy_line, innocent) values \
                ('%d','%d','%s', '%d','%s','%d','%s','%s','%d', '%d')" % item)
        try:
            inner.execute(in_sql)
        except:
            print('insert buggy item error')
            print(in_sql)
            #os.system("pause")

#davis is utc -0700
# def TimeZoneFormat(str_time):
#     dt = datetime.datetime.strptime(str_time, "%Y-%m-%d %H:%M:%S %z")
#     print (dt)

if __name__ == "__main__":
#     MyblameExtrator()
    #MySzzMySql('D:/doi/seed_2.csv')
    MySzzMySql(sys.argv[1])
    #MyGitLogParser(log_path, '04b40b3debebc24e11a1d9c81ea313125500185b')