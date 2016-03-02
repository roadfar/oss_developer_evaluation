# coding: UTF-8
import sys
import codecs
import json
import MySQLdb
import datetime
import urllib2
import re
import git
import sys
reload(sys)

sys.setdefaultencoding( "utf-8" )

class Users:
    def __init__(self,conn,cur,repo_id,repo_fullname,deadline):
        self.conn = conn
        self.cur = cur
        self.repo_id = repo_id
        self.repo_fullname = repo_fullname
        self.deadline = deadline

    def getAllGithubUsers(self):

        self.cur.execute("select distinct user from commit_comments where repo_id = '%d' and created_at < '%s';" % (self.repo_id,self.deadline))
        commit_comment_authors = self.cur.fetchall()
        results = []
        for author in commit_comment_authors:
            temp = eval(author[0])
            results.append(temp['login'])

        self.cur.execute("select distinct author_login from issue_comments where repo_id = '%d' and created_at < '%s';" % (self.repo_id,self.deadline))
        issue_comment_authors = self.cur.fetchall()
        for author in issue_comment_authors:
            if author[0] not in results:
                results.append(author[0])

        self.cur.execute("select distinct user from issues where repo_id = '%d' and created_at < '%s';" % (self.repo_id,self.deadline))
        issue_authors = self.cur.fetchall()
        results = []
        for author in issue_authors:

            temp = eval(str(author[0]))
            if str(temp['login']) not in results:
                results.append(str(temp['login']))

        self.cur.execute("select commit, author from commits where repo_id = '%d' ;" % self.repo_id)
        commit_authors = self.cur.fetchall()
        for author in commit_authors:
            if author[1] != 'None':
                #pay attention to the unicode of commit message
                # commit = json.loads(unicode(str(author[0]),"ISO-8859-1"))
                # author = json.loads(str(author[1]))
                commit = eval(str(author[0]))
                author = eval(str(author[1]))
                deadline = datetime.datetime.strptime(str(self.deadline), '%Y-%m-%d %H:%M:%S')
                commit_time = datetime.datetime.strptime(str(commit['author']['date']).replace("T"," ").replace("Z",""), '%Y-%m-%d %H:%M:%S')
                if (deadline - commit_time).total_seconds() > 0 and author['login'] not in results:
                    results.append(author['login'])
        return results

    def updateUsers(self):
        authors = self.getAllGithubUsers()
        print "**************** updating github users: " + self.repo_fullname
        for author in authors:
            url = "https://api.github.com/users/%s?access_token=adaccd3708619221656a9e13fc77bd8e5270c70a" % str(author)
            request_content = urllib2.Request(url)
            author_url = urllib2.urlopen(request_content).read()
            if author_url != "[]":
                author_json = json.loads(author_url)
                login = author_json['login'].encode("utf-8")
                user_id = author_json['id']
                type = author_json['type']
                name = author_json['name']
                company = author_json['company']
                blog = author_json['blog']
                location = author_json['location']
                email = author_json['email']
                hireable = author_json['hireable']
                bio = author_json['bio']
                created_at = author_json['created_at'].replace("T"," ").replace("Z","")
                value = (str(self.repo_id),str(login),str(user_id),str(type),str(name),str(company),str(blog),str(location),str(email),str(hireable),str(bio),str(created_at))
                print value
                try:
                    self.cur.execute("insert into users (repo_id,login,user_id,type,name,company,blog,location,email,hireable,bio,created_at) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",value)
                    self.conn.commit()
                except MySQLdb.Error, e:
                    print "Mysql Error!", e;