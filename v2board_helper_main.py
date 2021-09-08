#coding: utf-8
# +-------------------------------------------------------------------
# | 宝塔Linux面板 x3
# +-------------------------------------------------------------------
# | Copyright (c) 2015-2017 宝塔软件(http://bt.cn) All rights reserved.
# +-------------------------------------------------------------------
# | Rewrite author: v2board
# +-------------------------------------------------------------------

import public,json,os,time,sys
from BTPanel import session
class obj: id=0;
class v2board_helper_main:
    __setupPath = 'plugin/v2board_helper';
    __tmp = 'plugin/v2board_helper/tmp';
    __panelPath = '/www/server/panel';
    logPath = 'plugin/v2board_helper/speed.json'
    timeoutCount = 0;
    oldTime = 0;
    
    #下载文件
    def DownloadFile(self,url,filename):
        try:
            path = os.path.dirname(filename)
            if not os.path.exists(path): os.makedirs(path)
            import urllib,socket
            socket.setdefaulttimeout(10)
            self.pre = 0
            self.oldTime = time.time()
            if sys.version_info[0] == 2:
                urllib.urlretrieve(url,filename=filename,reporthook= self.DownloadHook)
            else:
                urllib.request.urlretrieve(url,filename=filename,reporthook= self.DownloadHook)
            self.WriteLogs(json.dumps({'name':'Download File','total':0,'used':0,'pre':0,'speed':0}))
        except:
            if self.timeoutCount > 5: return
            self.timeoutCount += 1
            time.sleep(5)
            self.DownloadFile(url,filename)
            
    #下载文件进度回调  
    def DownloadHook(self,count, blockSize, totalSize):
        used = count * blockSize
        pre1 = int((100.0 * used / totalSize))
        if self.pre != pre1:
            dspeed = used / (time.time() - self.oldTime);
            speed = {'name':public.GetMsg("DOWNLOAD_FILE"),'total':totalSize,'used':used,'pre':self.pre,'speed':dspeed}
            self.WriteLogs(json.dumps(speed))
            self.pre = pre1
    
    #写输出日志
    def WriteLogs(self,logMsg):
        fp = open(self.logPath,'w+');
        fp.write(logMsg)
        fp.close()
    
    #一键安装网站程序
    #param string name 程序名称
    #param string site_name 网站名称
    #param string php_version PHP版本
    def SetupPackage(self,get):
        name = get.dname
        site_name = get.site_name
        php_version = get.php_version
        #取基础信息
        find = public.M('sites').where('name=?',(site_name,)).field('id,path,name').find()
        if not  'path' in find:
            return public.returnMsg(False, 'Site not exist!')
        path = find['path']
        if path.replace('//','/') == '/': return public.returnMsg(False,'Dangerous website root directory!')

        #下载Helper
        pack_path = self.__setupPath + '/package'
        if not os.path.exists(pack_path): os.makedirs(pack_path,384)
        helperZip =  pack_path + '/v2board-aapanel-master.zip'
        self.DownloadFile('https://github.com/v2board/v2board-aapanel/archive/refs/heads/master.zip', helperZip)
        if not os.path.exists(helperZip): return public.returnMsg(False,'File download failed!' + helperZip)

        #设置pinfo
        pinfo = self.set_temp_file(helperZip,path)
        if not pinfo: return public.returnMsg(False,'Cannot find [aaPanel Auto Deployment Configuration File] in the installation package')

        #下载V2board
        v2boardZip =  pack_path + '/v2board-master.zip'
        self.DownloadFile('https://github.com/v2board/v2board/archive/refs/heads/master.zip', v2boardZip)
        if not os.path.exists(v2boardZip): return public.returnMsg(False,'File download failed!' + v2boardZip)
        public.ExecShell('unzip -o '+v2boardZip+' -d ' + self.__tmp)
        public.ExecShell('mv ' + self.__tmp + '/v2board-master/{.,}* ' + path)

        #设置权限
        self.WriteLogs(json.dumps({'name':'Setting permissions','total':0,'used':0,'pre':0,'speed':0}))
        public.ExecShell('chmod -R 755 ' + path)
        public.ExecShell('chown -R www.www ' + path)
        if pinfo['chmod']:
            for chm in pinfo['chmod']:
                public.ExecShell('chmod -R ' + str(chm['mode']) + ' ' + (path + '/' + chm['path']).replace('//','/'))

        #安装PHP扩展
        self.WriteLogs(json.dumps({'name':'Install the necessary PHP extensions','total':0,'used':0,'pre':0,'speed':0}))
        import files
        mfile = files.files();
        if type(pinfo['php_ext']) != list : pinfo['php_ext'] = pinfo['php_ext'].strip().split(',')
        for ext in pinfo['php_ext']:
            if ext == 'pathinfo':
                import config
                con = config.config()
                get.version = php_version
                get.type = 'on'
                con.setPathInfo(get)
            else:
                get.name = ext
                get.version = php_version
                get.type = '1'
                mfile.InstallSoft(get)

        #解禁PHP函数
        if 'enable_functions' in pinfo:
            try:
                if type(pinfo['enable_functions']) == str : pinfo['enable_functions'] = pinfo['enable_functions'].strip().split(',')
                php_f = public.GetConfigValue('setup_path') + '/php/' + php_version + '/etc/php.ini'
                php_c = public.readFile(php_f)
                rep = "disable_functions\s*=\s{0,1}(.*)\n"
                tmp = re.search(rep,php_c).groups()
                disable_functions = tmp[0].split(',')
                for fun in pinfo['enable_functions']:
                    fun = fun.strip()
                    if fun in disable_functions: disable_functions.remove(fun)
                disable_functions = ','.join(disable_functions)
                php_c = re.sub(rep, 'disable_functions = ' + disable_functions + "\n", php_c)
                public.writeFile(php_f,php_c)
                public.phpReload(php_version)
            except:pass


        #执行额外shell进行依赖安装
        self.WriteLogs(json.dumps({'name':'Execute extra SHELL','total':0,'used':0,'pre':0,'speed':0}))
        if os.path.exists(path+'/install.sh'):
            public.ExecShell('cd '+path+' && bash ' + 'install.sh ' + find['name'] + " &> install.log")
            public.ExecShell('rm -f ' + path+'/install.sh')

        #是否执行Composer
        if os.path.exists(path + '/composer.json'):
            self.WriteLogs(json.dumps({'name':'Execute Composer','total':0,'used':0,'pre':0,'speed':0}))
            if not os.path.exists(path + '/composer.lock'):
                execPHP = '/www/server/php/' + php_version +'/bin/php'
                if execPHP:
                    if public.get_url().find('125.88'):
                        public.ExecShell('cd ' +path+' && '+execPHP+' /usr/bin/composer config repo.packagist composer https://packagist.phpcomposer.com')
                    import panelSite
                    phpini = '/www/server/php/' + php_version + '/etc/php.ini'
                    phpiniConf = public.readFile(phpini)
                    phpiniConf = phpiniConf.replace('proc_open,proc_get_status,','')
                    public.writeFile(phpini,phpiniConf)
                    public.ExecShell('nohup cd '+path+' && '+execPHP+' /usr/bin/composer install -vvv > /tmp/composer.log 2>&1 &')

        #写伪静态
        self.WriteLogs(json.dumps({'name':'Set URL rewrite','total':0,'used':0,'pre':0,'speed':0}))
        swfile = path + '/nginx.rewrite'
        if os.path.exists(swfile):
            rewriteConf = public.readFile(swfile)
            dwfile = self.__panelPath + '/vhost/rewrite/' + site_name + '.conf'
            public.writeFile(dwfile,rewriteConf)

        swfile = path + '/.htaccess'
        if os.path.exists(swfile):
            swpath = (path + '/'+ pinfo['run_path'] + '/.htaccess').replace('//','/')
            if pinfo['run_path'] != '/' and not os.path.exists(swpath):
                public.writeFile(swpath, public.readFile(swfile))

                
        #删除伪静态文件
        public.ExecShell("rm -f " + path + '/*.rewrite')

        #删除多余文件
        rm_file = path + '/index.html'
        if os.path.exists(rm_file):
            rm_file_body = public.readFile(rm_file)
            if rm_file_body.find('panel-heading') != -1: os.remove(rm_file)

        #设置运行目录
        self.WriteLogs(json.dumps({'name':'Set the run directory','total':0,'used':0,'pre':0,'speed':0}))
        if pinfo['run_path'] != '/':
            import panelSite
            siteObj = panelSite.panelSite()
            mobj = obj()
            mobj.id = find['id']
            mobj.runPath = pinfo['run_path']
            siteObj.SetSiteRunPath(mobj)

        #导入数据
        self.WriteLogs(json.dumps({'name':'Import database','total':0,'used':0,'pre':0,'speed':0}))
        if os.path.exists(path+'/import.sql'):
            databaseInfo = public.M('databases').where('pid=?',(find['id'],)).field('username,password').find()
            if databaseInfo:
                public.ExecShell('/www/server/mysql/bin/mysql -u' + databaseInfo['username'] + ' -p' + databaseInfo['password'] + ' ' + databaseInfo['username'] + ' < ' + path + '/import.sql')
                public.ExecShell('rm -f ' + path + '/import.sql')
                siteConfigFile = (path + '/' + pinfo['db_config']).replace('//','/')
                if os.path.exists(siteConfigFile):
                    siteConfig = public.readFile(siteConfigFile)
                    siteConfig = siteConfig.replace('BT_DB_USERNAME',databaseInfo['username'])
                    siteConfig = siteConfig.replace('BT_DB_PASSWORD',databaseInfo['password'])
                    siteConfig = siteConfig.replace('BT_DB_NAME',databaseInfo['username'])
                    public.writeFile(siteConfigFile,siteConfig)

        #清理文件和目录
        self.WriteLogs(json.dumps({'name':'清理多余的文件','total':0,'used':0,'pre':0,'speed':0}))
        if type(pinfo['remove_file']) == str : pinfo['remove_file'] = pinfo['remove_file'].strip().split(',')
        print(pinfo['remove_file'])
        for f_path in pinfo['remove_file']:
            if not f_path: continue
            filename = (path + '/' + f_path).replace('//','/')
            if os.path.exists(filename):
                if not os.path.isdir(filename):
                    if f_path.find('.user.ini') != -1:
                        public.ExecShell("chattr -i " + filename)
                    os.remove(filename)
                else:
                    public.ExecShell("rm -rf " + filename)

        public.serviceReload()
        self.WriteLogs(json.dumps({'name':'Ready to deploy','total':0,'used':0,'pre':0,'speed':0}))
        return public.returnMsg(True,pinfo)
    
    #获取进度
    def GetSpeed(self,get):
        try:
            if not os.path.exists(self.logPath): public.returnMsg(False,'NO_DEPLOYMENT');
            return json.loads(public.readFile(self.logPath));
        except:
            return {'name':public.GetMsg("READY_DEPLOY"),'total':0,'used':0,'pre':0,'speed':0}

    #处理临时文件
    def set_temp_file(self,filename,path):
        if not os.path.exists(self.__tmp): os.makedirs(self.__tmp,384)
        public.ExecShell("rm -rf " + self.__tmp + '/*')
        self.WriteLogs(json.dumps({'name':'Unpacking the package...','total':0,'used':0,'pre':0,'speed':0}))
        public.ExecShell('unzip -o '+filename+' -d ' + self.__tmp)
        public.ExecShell('mv ' + self.__tmp + '/v2board-aapanel-master/ext/{.,}* ' + path)
        auto_config = 'v2board-aapanel-master/auto_install.json'
        p_info = self.__tmp + '/' + auto_config
        p_tmp = self.__tmp
        p_config = None
        if not os.path.exists(p_info):
            d_path = None
            for df in os.walk(self.__tmp):
                if len(df[2]) < 3: continue
                if not auto_config in df[2]: continue
                if not os.path.exists(df[0] + '/' + auto_config): continue
                d_path = df[0]
            if d_path:
                tmp_path = d_path
                auto_file = tmp_path + '/' + auto_config
                if os.path.exists(auto_file):
                    p_info = auto_file
                    p_tmp = tmp_path
        if os.path.exists(p_info):
            try:
                p_config = json.loads(public.readFile(p_info))
                os.remove(p_info)
                i_ndex_html = path + '/index.html'
                if os.path.exists(i_ndex_html): os.remove(i_ndex_html)
                if not self.copy_to(p_tmp,path): public.ExecShell(("\cp -arf " + p_tmp + '/. ' + path + '/').replace('//','/'))
            except: pass
        public.ExecShell("rm -rf " + self.__tmp + '/*')
        return p_config


    def copy_to(self,src,dst):
        try:
            if src[-1] == '/': src = src[:-1]
            if dst[-1] == '/': dst = dst[:-1]
            if not os.path.exists(src): return False
            if not os.path.exists(dst): os.makedirs(dst)
            import shutil
            for p_name in os.listdir(src):
                f_src = src + '/' + p_name
                f_dst = dst + '/' + p_name
                if os.path.isdir(f_src):
                    print(shutil.copytree(f_src,f_dst))
                else:
                    print(shutil.copyfile(f_src,f_dst))
            return True
        except: return False