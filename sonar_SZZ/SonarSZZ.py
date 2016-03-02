# _*_coding:utf-8 _*_
'''
Created on 2015.05.25

@author: Fisher Yu
'''

import csv
import datetime
import os
import re
import time
import sys
import git
import pymysql
from unidiff import PatchSet
reload(sys)
sys.setdefaultencoding('utf-8')
import MyTools


#path = 'D:/doi/rcode'
# log_path = path + r'\log.txt'
sha_p = r'commit [a-fA-F0-9]{32,32}'
diff_p = r'diff --git '

#log_base = 'G:/doi/log/'
path_base = '/Users/dreamteam/Documents/git_repos/Java'
proj_lang = ''
repo_name = ''
proj_id = ''
n_blame_error = 0
#mysql connection
conn = pymysql.connect(host='127.0.0.1', port=3306, 
                       user='root', passwd='891028',
                       db='github',charset="utf8")
inner = conn.cursor()
deadline = "2016-1-1 00:00:00"

def MySzzMySql(seed_file):    
    with open(seed_file) as seed:
        reader = csv.reader(seed)
        next(reader, None)
        for line in reader:
            global proj_id, repo_name, proj_lang
            proj_id = line[0]
            repo_name = line[1]
            proj_lang = line[11]
            print(proj_id, repo_name, proj_lang)
            #diff文件的路径
            diff_path = path_base + '/' + repo_name + '/logfile'
            #项目路径
            proj_path = path_base + '/' + repo_name
            cur = conn.cursor()
            sql = "select commits.sha, commits.issue_id, issues.created_at from commits, issues \
                where commits.repo_id=%d and issues.repo_id =%d and \
                commits.issue_id is not null and commits.issue_id=issues.number and issues.created_at<'%s';" \
                % (int(proj_id), int(proj_id), deadline)
            cur.execute(sql)
            fix_com_map = {}
            for row in cur:
                fix_sha = row[0]
                issue_id = row[1]
                issue_open_date = row[2]
                #issue的id及报告时间
                fix_com_map[fix_sha] = (issue_id, issue_open_date)   
            if len(fix_com_map)>0:
                MyGitLogParser(proj_path, diff_path, fix_com_map)

'''
Parse all fix_commits of a given project
'''                    
def MyGitLogParser(proj_path, log_path, fix_commit_map):
    with open(log_path) as log_diff:
        #for line in log_diff:
        line = log_diff.readline()
        while line:
            if re.match(sha_p, line):
                #形如"commit 6ba67f73d5f1b5db04c9e9fb65e2ea55f6126a63", remove 'commit ' and \n
                fix_sha = line[7:-1]
                #遍历log日志
                if len(fix_commit_map)<1:
                    print('All fix commits are finded: ' + log_path)
                    return
                if fix_sha in fix_commit_map:
                    print("find: ", fix_sha)
                    diff = []
                    #继续寻找下一行,直到匹配
                    while 1:
                        next_line = log_diff.readline()                   
                        #find diff structure
                        if re.match(diff_p, next_line):
                            #get the content around diff structure
                            #将直到下一个commit之间的log行取出,放入diff数组中
                            while re.match(sha_p, next_line) == None and next_line:
                                diff.append(next_line)
                                next_line = log_diff.readline()
                            break
                    #extract diff information
                    line = next_line
                    #解析刚取到的diff数组,name_file_line:文件名对应的便更改的代码行(非注释)
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
                        #通过blame取到代码行的前一个版本,并插入数据库
                        buggy_set = MyblameExtrator(proj_path, fix_sha, 
                                         issue_open_date, name_file_line, issue_id)
                        if n_blame_error > 1000000:
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
        sql = "insert into fix_no_buggy_commits_log(proj_id,fix_sha) \
        values ('%d', '%s')" % (int(proj_id), fix_sha)
        print("inserting...........fix_no_buggy_commits_log")
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
                for line in hunk:
                    if line.is_removed:
                        #判断修改的类型,如果是修改的代码,酒添加到line_set
                        code_type = MyTools.MychangeCodeJudger(line.value)
                        if code_type == MyTools.CG_CODE:
                            line_set.append(line.source_line_no)
            if len(line_set)>0:
                file_line[fname]=line_set                    
    return file_line

'''
use blame to get buggy provenance annotation
return an txxxxxxxple_set which can easy to insert into mysql
(fix_file,fix_line,buggy_sha,buggy_file,buggy_line)
'''
def MyblameExtrator(proj_path, fix_sha, issue_open_date, buggy_set, issue_id):
    global n_blame_error
    #buggy_tuple_set = []
    buggy_tuple_set = 0
    g = git.Repo(proj_path)
    #对每一行进行blame
    for fix_file in buggy_set:
        for fix_line in buggy_set[fix_file]:
            try:

                blame_info = g.git.blame('--abbrev=40', fix_sha+'^', \
                                     '-w', '-M', '-C', '-C', '-n', '-f', \
                                     '-L {0},+1'.format(fix_line), '--', fix_file)
            except Exception:
                print ('git blame error')
                # n_blame_error = n_blame_error + 1
                n_blame_error = 0

                time.sleep(2)
                continue
            #print (blame_info)
            #buggy_SHA_date = re.findall(r'\d{4}-\d{2}-\d{2}', blame_info)[0]
            try:
                buggy_SHA_date = re.findall(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} [\+\-]\d{4}', blame_info)[0]
            except:
                print('SHA_date extract error!')
                continue
            #时区转化
            splited_buggy_SHA_date = buggy_SHA_date.split()
            buggy_SHA_date = datetime.datetime.strptime(buggy_SHA_date, "%Y-%m-%d %H:%M:%S "+splited_buggy_SHA_date[2])
            delta_time_zone = divmod(int(splited_buggy_SHA_date[2]),100)[0]
            if delta_time_zone > 0 and divmod(abs(delta_time_zone),10)[0]==0:
                #形如+0800
                b_date = buggy_SHA_date-datetime.timedelta(hours=divmod(abs(delta_time_zone),10)[1])
            if delta_time_zone > 0 and divmod(abs(delta_time_zone),10)[0]>0:
                #形如+1000
                b_date = buggy_SHA_date-datetime.timedelta(hours=delta_time_zone)
            if delta_time_zone < 0 and divmod(abs(delta_time_zone),10)[0]==0:
                #形如-0100
                b_date = buggy_SHA_date+datetime.timedelta(hours=divmod(abs(delta_time_zone),10)[1])
            if delta_time_zone < 0 and divmod(abs(delta_time_zone),10)[0]>0:
                #形如-1000
                b_date = buggy_SHA_date+datetime.timedelta(hours=abs(delta_time_zone))
            else:
                b_date = buggy_SHA_date
            i_date = datetime.datetime.strptime(issue_open_date, "%Y-%m-%d %H:%M:%S")
            innocent = 0;
            buggy_SHA = blame_info.split()[0][-40:]
            #如果bug的时期在issue报告日期之后,找到无辜的代码
            pr_merged_at=judgeCommitIsPR(buggy_SHA)
            if pr_merged_at==0 or pr_merged_at==None:
                if b_date > i_date:
                    innocent = 1
                    print ('find a innocent code!')
            else:
                print('find a pr commit')
                merged_date = datetime.datetime.strptime(pr_merged_at, "%Y-%m-%d %H:%M:%S")
                if merged_date>i_date:
                    print('find a innocent PR!')
                    innocent = 1
            buggy_line = blame_info.split('(')[0].split()[-1]
            try:
                buggy_line_num = int(buggy_line)
            except:
                buggy_line_num = 0
            buggy_file_path = ' '.join(blame_info.split('(')[0].split()[1:-1])
            '''
            Change to use insert into database each blame result
            '''
            buggy_tuple = (fix_file,fix_line,buggy_SHA,\
                           buggy_file_path,int(buggy_line_num),innocent)
            EachBlameBuggyToMysql(buggy_tuple,issue_id,fix_sha)
            buggy_tuple_set = buggy_tuple_set + 1         
    return buggy_tuple_set                                 

def judgeCommitIsPR(sha):
    sql = "select pull_requests.merged_at from commits, pull_requests where commits.sha = '"+sha+"' and commits.pull_id =\
    pull_requests.number;"
    inner.execute(sql)
    for row in inner:
        if type(row[0])!= None:
            print row[0]
            return row[0]
        else:
            return 0
    return 0

'''
Insert raw data each blame.
'''
def EachBlameBuggyToMysql(buggy, issue_id, fix_sha):
    global proj_id, repo_name, proj_lang, inner
    file_type = MyTools.MyfiletypeJudger(buggy[0], proj_lang, repo_name)
    temp=(int(proj_id),issue_id,fix_sha,file_type,)
    item = temp+buggy
    in_sql = ("insert into szz_raw(proj_id, issue_id, \
            fix_sha, file_type, fix_file, fix_line, \
            buggy_sha, buggy_file, buggy_line, innocent) values \
            ('%d','%d','%s','%d','%s','%d','%s','%s','%d','%d')" % item)
    try:
        # print("inserting............."+item)
        inner.execute(in_sql)
        conn.commit()
    except Exception as e:
        print('insert buggy item error')
        print e;

'''
Insert raw structure data to Mysql database
'''
def BuggyToMysql(buggy_set, fix_sha, fix_tuple):
    global proj_id, repo_name, proj_lang, inner
    for buggy in buggy_set:
        file_type = MyTools.MyfiletypeJudger(buggy[0], proj_lang, repo_name)
        #item = (int(proj_id),issue_id,fix_sha,file_type,)+buggy
        item = (int(proj_id),fix_tuple[0],fix_sha,file_type,)+buggy
        in_sql = ("insert into szz_raw(proj_id, issue_id, fix_sha, file_type, fix_file, fix_line, \
                buggy_sha, buggy_file, buggy_line, innocent) values ('%d','%d','%s', '%d','%s','%d','%s','%s','%d', '%d')" % item)
        #sometimes happen because file name is too long
        # #have fixed in Database, make it longers
        try:
            inner.execute(in_sql)
        except pymysql.error,e:
            print('insert buggy item error')
            print e

#os.system("pause")
#  davis is utc -0700
# def TimeZoneFormat(str_time):
#     dt = datetime.datetime.strptime(str_time, "%Y-%m-%d %H:%M:%S %z")
#     print (dt)

if __name__ == "__main__":
    #MySzzMySql('D:/doi/seed_2.csv')
    MySzzMySql('/Users/dreamteam/Documents/study/sonar/script/negative_contributor_measurement/java_top10.csv')