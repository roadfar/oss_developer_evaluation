import urllib2
import sys
import codecs
import json
import MySQLdb
from issues import Issues
from commits import Commits
from users import Users
import commits
import issues
from selenium import webdriver

def run(conn,cur,repo_id,repo_fullname,deadline):
    try:
        mIssues = Issues(conn,cur,repo_id,repo_fullname)
        mIssues.get_issues(1)
        mIssues.get_issue_comments(113)
        mCommits = Commits(conn,cur,repo_id,repo_fullname)
        mCommits.get_commits(1)
        mCommits.get_commit_comments(1)
        mUsers = Users(conn,cur,repo_id,repo_fullname,deadline)
        mUsers.updateUsers()
    except MySQLdb.Error, e:
        print "Mysql Error!", e;
    cur.close()
    conn.close()

if __name__ == '__main__':

    conn = MySQLdb.connect(host='127.0.0.1',user='root',passwd='891028',db='github')
    cur = conn.cursor()
    run(conn,cur,4164482,"django/django","2016-01-01 00:00:00")



