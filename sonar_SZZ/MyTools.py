# _*_coding:utf-8 _*_
import sys
'''
Created on 2015.06.01

@author: Fisher Yu
'''
import re
reload(sys)
sys.setdefaultencoding('utf-8')
#import pymysql

#file type
SRC_CODE_FILE = 0
TEST_CODE_FILE = 1
CONFIG_BUILD_FILE = 2
DOC_FILE = 3
OTHERS_FILE = 4

#detect signal
MEDIA_PATH_SIGNAL = ['/media/', '/pic/', '/img/', '/.svn/']
DOC_PATH_SIGNAL = ['/doc', 'doc/', 'docs/', '/log', 'document', 'manual', 'usage', 'changelog']
CONFIG_PATH_SIGNAL = ['/config', '-conf', 'conf-', 'config-', '_conf', 'conf_', 'config_', \
                       '/ini/', '/build', '_build', 'build_', '-bulid', 'build-', 'travis.yml']
TEST_SIGNAL = ['unittest', 'unit_test', 'unit-test', '/t/', \
        '/test', '_test', '-test', 'test/', 'tests/', \
        'test_', 'testing_', 'tests_', 'tests-', 'testing-', 'tests-' \
        '/spec/', '/specs/', '_spec', '-spec', \
        'spec_', 'specs_',  'spec-', 'specs-', \
        '/grunt', '/ci/']

DOC_NAME_SIGNAL = [".rdoc",".doc",".md",".tex",".txt",".pdf"]


#code change type in diff
CG_CODE = 0
CG_NOTE = 1

# conn = pymysql.connect(host='127.0.0.1', port=3306, 
#                        user='root', passwd='influx1234', 
#                        db='github',charset="utf8")

def MychangeCodeJudger(changed_code):
    #判断注释航的正则表达式是否有问题?
    NOTE_PT = r'^([ \t]*(#|(\\\*)|(\*\*)|(//)|(/\*))|[ \t]*$)'
    pt = re.compile(NOTE_PT)
    match = pt.match(changed_code)
    if match:
        return CG_NOTE
    else:
        return CG_CODE

def MyfiletypeJudger(file_name, language, repo_name):
    lang = language
    fn = file_name.lower()
    fn = fn.replace('\\', '/')
    fn = fn.replace('~', '/')
    #print(fn)
    fn_elements = fn.split('/')
    last_name = fn_elements[len(fn_elements)-1]
    index = fn_elements[len(fn_elements)-1].rfind('.')
    if index != -1:
        last_name = fn_elements[len(fn_elements)-1][index:]
    standard = ''
    if lang == 'Ruby':
        standard = ".rb"
    if lang=="Python":
        standard = ".py"
    if lang=="JavaScript":
        standard = ".js"
    if lang=="Java":
        standard = ".java"
    if lang=="PHP":
        standard = ".php"
    if lang=="Scala":
        standard = ".scala" 
    
    # 1) find obvious doc and media signal
    for signal in MEDIA_PATH_SIGNAL:
        if fn.find(signal) != -1:
            ret_type = DOC_FILE
            return ret_type
    for signal in DOC_PATH_SIGNAL:
        if fn.find(signal) != -1:
            ret_type = DOC_FILE
            return ret_type
    if last_name in DOC_NAME_SIGNAL:
        ret_type = DOC_FILE
        return ret_type        
    if last_name in [".svg",".png",".jpg",".jar", '.sql', '.csv']:
        ret_type = DOC_FILE
        return ret_type
    if last_name in ["USAGE","README","COPYING","usage"]:
        ret_type = DOC_FILE
        return ret_type
    
    # 2) find config signal
    for signal in CONFIG_PATH_SIGNAL:
        if fn.find(signal) != -1:
            ret_type = CONFIG_BUILD_FILE
            return ret_type
    if last_name in ['rakefile','gemfile','makefile'] \
        or last_name in ['.gemspec','.gitmodules','.settings', '.sh', \
        ".yardopts",".rake",".builder",".conf",".ini",".in", ".bat", ".cmake"]:
        ret_type = CONFIG_BUILD_FILE
        return ret_type
    
    # 3) find test signal    
    for signal in TEST_SIGNAL:
        if fn.find(signal) != -1:
            ret_type = TEST_CODE_FILE
            return ret_type
        
    # 4) find src signal
    for signal in ['/src/', repo_name]:
        if fn.find(signal) != -1:
            ret_type = SRC_CODE_FILE
            return ret_type
    # 5) last thing is judge the file_type
    if lang in ["C++","C"]:
        if last_name in [".h", ".c", '.cpp', '.cc']: 
            ret_type = SRC_CODE_FILE
            return ret_type
    if last_name==standard:
        ret_type = SRC_CODE_FILE
        return ret_type
    else:
        ret_type = OTHERS_FILE
        return ret_type
    
import os 
def TestMethod(rootDir,language,repo_name): 
    for lists in os.listdir(rootDir): 
        path = os.path.join(rootDir, lists) 
        if path.find('.git') == -1:
            ty = MyfiletypeJudger(path,language,repo_name)
            print (path, ty) 
        if os.path.isdir(path): 
            TestMethod(path,language,repo_name)
            
# def UpdateSzzFileType(seed_file):
#     cur = conn.cursor()
#     upcur = conn.cursor()             
#     with open(seed_file) as seed:
#         reader = csv.reader(seed)
#         next(reader, None)
#         for line in reader:
#             proj_id = int(line[0])
#             repo_name = line[1]
#             proj_lang = line[3]                
#             sql = "select Id, fix_file, buggy_file from szz_raw \
#                 where proj_id = %d;" % proj_id   
#             cur.execute(sql)
#             for row in cur:
#                 index = int(row[0])
#                 fix_file = "a/" + row[1]
#                 bug_file = "a/" + row[2]
#                 fix_ty = MyfiletypeJudger(fix_file,proj_lang,repo_name)
#                 bug_ty = MyfiletypeJudger(bug_file,proj_lang,repo_name) 
#                 upsql = "update szz_raw set file_type=%d, bug_file_type=%d \
#                     where Id=%d;" % (fix_ty, bug_ty, index)
#                 upcur.execute(upsql)
#                 print(proj_id, index)

import csv
if __name__ == "__main__":
    #UpdateSzzFileType('D:/doi/seed_tag.csv')
    
    #a = MychangeCodeJuder('  // adsfad')
    #print(a)
    #a = MyfiletypeJudger('libs/CSS3PIE/LICENSE-2.0', 'aa', 'bb')
    #print(a)
    '''
    with open('D:/doi/seed_ci.csv') as seed:
        reader = csv.reader(seed)
        next(reader, None)
        for line in reader:
            proj_id = line[0]
            repo_name = line[1]
            proj_lang = line[3]
            path = "G:/doi/projects/"+proj_id;
            TestMethod(path,proj_lang,repo_name)
    '''        
            
            
    #MyfiletypeJudger('Rakefile')