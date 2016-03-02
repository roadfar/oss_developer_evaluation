# coding: UTF-8
import urllib2
import sys
import codecs
import json
import MySQLdb
class Commits:
    def __init__(self,conn,cur,repo_id,repo_fullname):
        self.conn = conn
        self.cur = cur
        self.repo_id = repo_id
        self.repo_fullname = repo_fullname

    def get_commits(self,page_num):
        print "***************** getting commits of " + self.repo_fullname
        try:
            for number in range(page_num,10000):
                url = "https://api.github.com/repos/%s/commits?per_page=100&page=%d&access_token=adaccd3708619221656a9e13fc77bd8e5270c70a"%(self.repo_fullname,number)
                print number
                request_content = urllib2.Request(url)
                issue_content = urllib2.urlopen(request_content).read()
                if issue_content=="[]":
                    break
                else:
                    issues = json.loads(issue_content)
                    for issue in issues:
                        sha = issue['sha']
                        commit = issue['commit']
                        url = issue['url']
                        html_url = issue['html_url']
                        comments_url = issue['comments_url']
                        author = issue['author']
                        committer = issue['committer']
                        message = issue['commit']['message'].encode("utf-8")
                        parents = issue['parents']

                        value = (str(self.repo_id),str(sha),str(commit),str(url),str(html_url),str(comments_url),str(author),str(committer),str(message),str(parents))
                        try:
                            self.cur.execute("insert into commits (repo_id,sha,commit,url,html_url,comments_url,author,committer,message,parents) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",value)
                            self.conn.commit()
                        except MySQLdb.Error, e:
                            print "Mysql Error!", e;
                            print value
                    if len(issues) < 100:
                        print len(issues)
                        break
        except Exception as e:
            print e

    def get_commit_comments(self,page_num):
        print "***************** getting commit comments of" + self.repo_fullname
        try:
            for number in range(page_num, 10000):
                url = "https://api.github.com/repos/%s/comments?per_page=100&page=%d&access_token=adaccd3708619221656a9e13fc77bd8e5270c70a" % (self.repo_fullname, number)
                print number
                request_content = urllib2.Request(url)
                issue_content = urllib2.urlopen(request_content).read()
                if issue_content == "[]":
                    break
                else:
                    issues = json.loads(issue_content)
                    for issue in issues:
                        body = issue['body'].encode("utf-8")
                        path = issue['path']
                        position = issue['position']
                        line = issue['line']
                        commit_id = issue['id']
                        user = issue['user']
                        created_at = issue['created_at'].replace("T", " ").replace("Z", "")
                        updated_at = issue['updated_at'].replace("T", " ").replace("Z", "")
                        value = (str(body),str(path),str(position),str(line),str(commit_id),str(user),str(created_at),str(updated_at),str(self.repo_id))
                        try:
                            self.cur.execute("insert into commit_comments (body,path,position,line,commit_id,user,created_at,updated_at,repo_id) values (%s,%s,%s,%s,%s,%s,%s,%s,%s)",value)
                            self.conn.commit()
                        except MySQLdb.Error, e:
                            print "Mysql Error!", e;
                            print value
                    if len(issues) < 100:
                        print len(issues)
                        break
        except Exception as e:
            print e

