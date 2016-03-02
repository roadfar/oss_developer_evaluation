__author__ = 'houxiang'


from sqlalchemy.ext.declarative import declarative_base
import pymysql
import csv
from git import *
base = declarative_base()
import os
import cPickle as pickle
import logging
import time
import getpass
from copy import deepcopy



logging.basicConfig(level=logging.DEBUG,
                     format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S',
                    filename = 'myapp.log',
                    filemode='w')


base_path = '/Users/dreamteam/Documents/git_repos/'

#connect the mysql
githubDB={"host":'localhost',"user":'root',"passwd":'891028',"port":3306,"DB":'github'}
conn = pymysql.connect(host=githubDB["host"],user=githubDB["user"],passwd=githubDB["passwd"],port=githubDB["port"])

sonarDB={"host":"localhost","user":"root","passwd":"891028","port":3306,"DB":"github"}
sonarconn = pymysql.connect(host=sonarDB["host"],user=sonarDB["user"],passwd=sonarDB["passwd"],port=sonarDB["port"],db="sonar")

log_indexs = list()

def projectIssueFinder(seed_file):
    with open(seed_file) as seed:
        reader = csv.reader(seed)
        next(reader, None)
        for line in reader:
            global project_id,repo_name,project_lang
            project_id = line[0]
            repo_name = line[1]
            project_lang = line[3]
            conn.select_db('github')
            cursor = conn.cursor()
            sql = "select fix_sha , fix_line ,fix_file, buggy_sha , buggy_file , buggy_line from szz_raw where proj_id = "+ project_id
            cursor.execute(sql)
            result = cursor.fetchall()
            buggy_commits = {}
            buggy_file_line ={}
            fix_commits = {}
            fix_file_line ={}
            for line in result:
                fix_sha = line[0]
                fix_line = line[1]
                fix_file = line[2]
                buggy_sha = line[3]
                buggy_file = line[4]
                buggy_line = line[5]

                #use the hash dict to orginize the data format by hx
                if buggy_sha in buggy_commits.keys():
                    exists_buggy_file_line = buggy_commits[buggy_sha]
                    if buggy_file in exists_buggy_file_line.keys():
                        exists_buggy_file_line[buggy_file].append(buggy_line)
                    else:
                        exists_buggy_file_line[buggy_file]=[buggy_line,]
                else:
                    buggy_file_line[buggy_file] = [buggy_line,]
                    new_file_line = deepcopy(buggy_file_line)
                    buggy_commits[buggy_sha] = new_file_line
                    buggy_file_line.clear()

                if fix_sha in fix_commits.keys():
                    exists_fix_file_line = fix_commits[fix_sha]
                    if fix_file in exists_fix_file_line.keys():
                        exists_fix_file_line[fix_file].append(fix_line)
                    else:
                        exists_fix_file_line[fix_file] = [fix_line,]
                else:
                    fix_file_line[fix_file] = [fix_line,]
                    new_file_line = deepcopy(fix_file_line)
                    fix_commits[fix_sha] = new_file_line
                    fix_file_line.clear()

            #print buggy_commits
            path = base_path+repo_name
            repo = Repo(path)
            g=repo.git
            sel_sql = 'select line,rule_id,severity,message,author_login,technical_debt,tags from issues'
            for buggy_sha in buggy_commits.keys():
                logging.info(buggy_sha)

                gitstatus=g.reset('--hard',buggy_sha)
                print gitstatus+"++++++++++++++++++++++++++++++++++"+buggy_sha

                files = buggy_commits[buggy_sha]
                print files
                cur = sonarconn.cursor()
                #first empty the table
                cur.execute("truncate table issues")
                for buggy_files in files.keys():
                    print buggy_files
                    simple_file_path = './'+buggy_files
                    buggy_file_lines = files[buggy_files]
                    sonar_cmd = 'sonar-runner -Dsonar.projectKey=my:'+str(project_id)+'n_buggy'+' -Dsonar.projectName='+str(project_id)+'_buggy'+' -Dsonar.projectVersion=1.0 -Dsonar.sources='+str(simple_file_path)+' -Dsonar.sourceEncoding=UTF-8 -Dsonar.language'+langugeHandler(project_lang)
                    oshandler(path,sonar_cmd)
                    cur.execute(sel_sql)
                    buggy_intro_issue = cur.fetchall()
                    for line in buggy_intro_issue:
                        issue_line = line[0]
                        if issue_line in buggy_file_lines:
                            print "find one issue related buggy "
                            item =(int(line[1]),line[2],line[3],line[4],int(line[5]),line[6],int(line[0]),buggy_files)
                            update_sql="update szz_raw set intro_rule_id = %s,intro_severity = %s,intro_message = %s,intro_author_login = %s,intro_technical_debt=%s, intro_tags = %s where buggy_line = %s and buggy_file = %s"
                            if cursor.execute(update_sql,item):
                                print "update successfully ! "
                cur.execute("truncate table issues")

            for fix_sha in fix_commits.keys():
                print fix_sha
                logging.info(fix_sha)
                gitstatus = g.reset('--hard',fix_sha)
                files_and_lines = fix_commits[fix_sha]

                cur = sonarconn.cursor()
                #first empty the table
                cur.execute("truncate table issues")
                for fix_files in files_and_lines.keys():
                    print "fix_files:"
                    print fix_files
                    simple_file_path = './'+fix_files
                    fix_file_lines = files_and_lines[fix_files]
                    sonar_cmd = 'sonar-runner -Dsonar.projectKey=my:'+str(project_id)+'n_fixed'+' -Dsonar.projectName='+str(project_id)+'_fix'+' -Dsonar.projectVersion=1.0 -Dsonar.sources='+str(simple_file_path)+' -Dsonar.sourceEncoding=UTF-8 -Dsonar.language'+langugeHandler(project_lang)
                    oshandler(path,sonar_cmd)
                    cur.execute(sel_sql)
                    fix_exists_issue = cur.fetchall()
                    for line in fix_exists_issue:
                        issue_line = line[0]
                        if issue_line in fix_file_lines:
                            print "find one issue related fix "
                            item =(int(line[1]),line[2],line[3],line[4],int(line[5]),line[6],int(line[0]),fix_files)
                            update_sql="update szz_raw set fix_rule_id = %s,fix_severity = %s,fix_message = %s,fix_author_login = %s,fix_technical_debt = %s,fix_tags=%s where fix_line = %s and fix_file= %s"
                            if cursor.execute(update_sql,item):
                                print "update successfully !"
                cur.execute("truncate table issues")

#pratice the pickle
def persistData(seed_file):
    with open(seed_file) as seed:
        reader = csv.reader(seed)
        next(reader, None)
        for line in reader:
            global project_id,repo_name,project_lang
            project_id = line[0]
            repo_name = line[1]
            project_lang = line[3]
            conn.select_db('github')
            cursor = conn.cursor()
            sql = "select fix_sha , fix_line ,fix_file, buggy_sha , buggy_file , buggy_line from szz_raw where proj_id = "+ project_id + " limit 30 "
            cursor.execute(sql)
            result = cursor.fetchall()
            buggy_commits = {}
            buggy_file_line ={}
            fix_commits = {}
            fix_file_line ={}
            for line in result:
                fix_sha = line[0]
                fix_line = line[1]
                fix_file = line[2]
                buggy_sha = line[3]
                buggy_file = line[4]
                buggy_line = line[5]

                #use the hash dict to orginize the data format by hx
                if buggy_sha in buggy_commits.keys():
                    exists_buggy_file_line = buggy_commits[buggy_sha]
                    if buggy_file in buggy_file_line.keys():
                        buggy_file_line[buggy_file].append(buggy_line)
                    else:
                        buggy_file_line[buggy_file]=[buggy_line,]
                    exists_buggy_file_line.update(buggy_file_line)
                else:
                    buggy_file_line.clear()
                    buggy_file_line[buggy_file] = [buggy_line,]
                    buggy_commits[buggy_sha] = buggy_file_line.copy()
                if fix_sha in fix_commits.keys():
                    exists_fix_file_line = fix_commits[fix_sha]
                    if fix_file in fix_file_line.keys():
                        fix_file_line[fix_file].append(fix_line)
                    else:
                        fix_file_line[fix_file]=[fix_line,]
                    exists_fix_file_line.update(fix_file_line)
                else:
                    fix_file_line.clear()
                    fix_file_line[fix_file] =[fix_line,]
                    fix_commits[fix_sha] = fix_file_line.copy()

            file_name = project_id+'_'+repo_name
            buggy_info_path = './persistdata/'+file_name+"buggy_info"
            fix_info_path = './persistdata/'+file_name+"fix_info"
            buggy_file = file(buggy_info_path,'wb')
            fix_file = file(fix_info_path,'wb')
            pickle.dump(buggy_commits,buggy_file,True)
            pickle.dump(fix_commits,fix_file,True)



def test(seed_file):
    with open(seed_file) as seed:
        reader = csv.reader(seed)
        next(reader, None)
        for line in reader:
            project_id = line[0]
            repo_name = line[1]

            file_name = project_id+'_'+repo_name
            buggy_info_path = './persistdata/'+file_name+"buggy_info"
            fix_info_path = './persistdata/'+file_name+"fix_info"
            buggy_file = file(buggy_info_path,'rb')
            fix_file = file(fix_info_path,'rb')
            buggy_commits = pickle.load(buggy_file)
            fix_commits = pickle.load(fix_file)
            print buggy_commits
            print fix_commits



def updateSql(sql):
    pass

def sqlHandler(sql):
    pass

#change the language to the way of sonar
def langugeHandler(project_lang):
    if project_lang == 'JavaScript':
        return 'js'
    elif project_lang == 'Python':
        return 'py'
    elif project_lang == 'Ruby':
        return 'rb'
    elif project_lang == 'Java':
        return 'java'


def oshandler(path,sonar_cmd):
    if os.path.isdir(path):
        try:
            os.chdir(path)
            os.system(sonar_cmd)
            time.sleep(5)
        except:
            logging.debug('sonar-runner failed !')
    else:
        logging.debug(path+' the path of file is wrong! please check again ')


if __name__ == '__main__':
    #fix_log_finder()
    projectIssueFinder('/Users/dreamteam/Documents/study/sonar/script/negative_contributor_measurement/project_samples.csv')
    # persistData('/Users/houxiang/Desktop/houxiang/seed_88.csv')
    # test('/Users/houxiang/Desktop/houxiang/seed_88.csv')