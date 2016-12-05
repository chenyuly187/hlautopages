# -*- coding: utf-8 -*-

import os
import yaml
import time
import copy
import json
import tempfile
import shutil
import random
import urllib2
import xmltodict
from xlrd import open_workbook
import logging
from logging.handlers import RotatingFileHandler
from selenium import webdriver
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support.expected_conditions import presence_of_element_located, visibility_of_element_located
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary


CONFIG = 'config.yaml'
DATA = 'data.xlsx'
proxysheet = 'proxy'
ACTIONS = ['click', 'clear', 'sendkeys', 'submit', 'select']


class Logger(object):
    """自定义日志类，读取配置，并以配置为准进行日志输出，分别到console和log file里。
        methods:
            __init__(logger_name='root')
                读入配置文件，进行配置。logger_name默认为root。
            get_logger()
                读取配置，添加相应handler，返回logger。
    """

    def __init__(self, logger_name='root', console_level='DEBUG', file_level='DEBUG'):
        self.logger = logging.getLogger(logger_name)
        logging.root.setLevel(logging.NOTSET)
        self.log_file_name = 'AutoRun.log'
        self.console_log_level = console_level
        self.file_log_level = file_level
        self.console_output = True
        self.file_output = True
        self.formatter = logging.Formatter('%(asctime)s %(message)s')

    def get_logger(self):
        """在logger中添加日志句柄并返回，如果logger已有句柄，则直接返回"""
        if not self.logger.handlers:  # 避免重复日志
            if self.console_output:
                console_handler = logging.StreamHandler()
                console_handler.setFormatter(self.formatter)
                console_handler.setLevel(self.console_log_level)
                self.logger.addHandler(console_handler)
            else:
                pass

            if self.file_output:
                file_handler = RotatingFileHandler(os.path.abspath(self.log_file_name))
                file_handler.setFormatter(self.formatter)
                file_handler.setLevel(self.file_log_level)
                self.logger.addHandler(file_handler)
            else:
                pass
        return self.logger

logger = Logger().get_logger()
selenium_logger = Logger('selenium.webdriver.remote.remote_connection', console_level='ERROR', file_level='ERROR').get_logger()


class ExcelReader(object):
    def __init__(self, sheet):
        """Read workbook

        :param sheet: index of sheet or sheet name.
        """
        self.book_name = os.path.abspath(DATA)
        self.sheet_locator = sheet

        self.book = self._book()
        self.sheet = self._sheet()

    def _book(self):
        try:
            return open_workbook(self.book_name)
        except IOError as e:
            print u'[Error] 打开excel出错'
            logger.exception(e)
            os._exit(0)

    def _sheet(self):
        """Return sheet"""
        try:
            return self.book.sheet_by_name(self.sheet_locator)  # by name
        except Exception as e:
            print u'[Error] sheet {} 不存在'.format(self.sheet_locator)
            logger.exception(e)
            os._exit(0)

    @property
    def title(self):
        """First row is title."""
        try:
            return self.sheet.row_values(0)
        except IndexError as e:
            print u'[Error] sheet中没有数据'
            logger.exception(e)

    @property
    def data(self):
        """Return data in specified type:

            [{row1:row2},{row1:row3},{row1:row4}...]
        """
        sheet = self.sheet
        title = self.title
        data = list()

        # zip title and rows
        for col in range(1, sheet.nrows):
            s1 = sheet.row_values(col)
            s2 = [unicode(s).encode('utf-8') for s in s1]  # utf-8 encoding
            data.append(dict(zip(title, s2)))
        return data

    @property
    def nums(self):
        """Return the number of cases."""
        return len(self.data)


class YamlReader:
    """Read yaml file"""
    def __init__(self):
        self.yaml = os.path.abspath(CONFIG)

    @property
    def data(self):
        with open(self.yaml, 'r') as f:
            al = yaml.safe_load_all(f)
            y = [x for x in al]
            return y


WEBDRIVER_PREFERENCES = """
{
  "frozen": {
    "app.update.auto": false,
    "app.update.enabled": false,
    "browser.displayedE10SNotice": 4,
    "browser.download.manager.showWhenStarting": false,
    "browser.EULA.override": true,
    "browser.EULA.3.accepted": true,
    "browser.link.open_external": 2,
    "browser.link.open_newwindow": 2,
    "browser.offline": false,
    "browser.reader.detectedFirstArticle": true,
    "browser.safebrowsing.enabled": false,
    "browser.safebrowsing.malware.enabled": false,
    "browser.search.update": false,
    "browser.selfsupport.url" : "",
    "browser.sessionstore.resume_from_crash": false,
    "browser.shell.checkDefaultBrowser": false,
    "browser.tabs.warnOnClose": false,
    "browser.tabs.warnOnOpen": false,
    "datareporting.healthreport.service.enabled": false,
    "datareporting.healthreport.uploadEnabled": false,
    "datareporting.healthreport.service.firstRun": false,
    "datareporting.healthreport.logging.consoleEnabled": false,
    "datareporting.policy.dataSubmissionEnabled": false,
    "datareporting.policy.dataSubmissionPolicyAccepted": false,
    "devtools.errorconsole.enabled": true,
    "dom.disable_open_during_load": false,
    "extensions.autoDisableScopes": 10,
    "extensions.blocklist.enabled": false,
    "extensions.checkCompatibility.nightly": false,
    "extensions.logging.enabled": true,
    "extensions.update.enabled": false,
    "extensions.update.notifyUser": false,
    "javascript.enabled": true,
    "network.manage-offline-status": false,
    "network.http.phishy-userpass-length": 255,
    "offline-apps.allow_by_default": true,
    "prompts.tab_modal.enabled": false,
    "security.csp.enable": false,
    "security.fileuri.origin_policy": 3,
    "security.fileuri.strict_origin_policy": false,
    "security.warn_entering_secure": false,
    "security.warn_entering_secure.show_once": false,
    "security.warn_entering_weak": false,
    "security.warn_entering_weak.show_once": false,
    "security.warn_leaving_secure": false,
    "security.warn_leaving_secure.show_once": false,
    "security.warn_submit_insecure": false,
    "security.warn_viewing_mixed": false,
    "security.warn_viewing_mixed.show_once": false,
    "signon.rememberSignons": false,
    "toolkit.networkmanager.disable": true,
    "toolkit.telemetry.prompted": 2,
    "toolkit.telemetry.enabled": false,
    "toolkit.telemetry.rejected": true,
    "xpinstall.signatures.required": false,
    "xpinstall.whitelist.required": false
  },
  "mutable": {
    "browser.dom.window.dump.enabled": true,
    "browser.laterrun.enabled": false,
    "browser.newtab.url": "about:blank",
    "browser.newtabpage.enabled": false,
    "browser.startup.page": 0,
    "browser.startup.homepage": "about:blank",
    "browser.usedOnWindows10.introURL": "about:blank",
    "dom.max_chrome_script_run_time": 30,
    "dom.max_script_run_time": 30,
    "dom.report_all_js_exceptions": true,
    "javascript.options.showInConsole": true,
    "network.http.max-connections-per-server": 10,
    "startup.homepage_welcome_url": "about:blank",
    "startup.homepage_welcome_url.additional": "about:blank",
    "webdriver_accept_untrusted_certs": true,
    "webdriver_assume_untrusted_issuer": true
  }
}
"""


class FirefoxProfile(webdriver.FirefoxProfile):
    def __init__(self, profile_directory=None):
        """
        Initialises a new instance of a Firefox Profile

        :args:
         - profile_directory: Directory of profile that you want to use.
           This defaults to None and will create a new
           directory when object is created.
        """
        if not FirefoxProfile.DEFAULT_PREFERENCES:
            FirefoxProfile.DEFAULT_PREFERENCES = json.loads(WEBDRIVER_PREFERENCES)

        self.default_preferences = copy.deepcopy(
            FirefoxProfile.DEFAULT_PREFERENCES['mutable'])
        self.native_events_enabled = True
        self.profile_dir = profile_directory
        self.tempfolder = None
        if self.profile_dir is None:
            self.profile_dir = self._create_tempfolder()
        else:
            self.tempfolder = tempfile.mkdtemp()
            newprof = os.path.join(self.tempfolder, "webdriver-py-profilecopy")
            shutil.copytree(self.profile_dir, newprof,
                            ignore=shutil.ignore_patterns("parent.lock", "lock", ".parentlock"))
            self.profile_dir = newprof
            self._read_existing_userjs(os.path.join(self.profile_dir, "user.js"))
        self.extensionsDir = os.path.join(self.profile_dir, "extensions")
        self.userPrefs = os.path.join(self.profile_dir, "user.js")

    def update_preferences(self):
        for key, value in self.DEFAULT_PREFERENCES['frozen'].items():
            self.default_preferences[key] = value
        self._write_user_prefs(self.default_preferences)

    def add_extension(self, extension=os.path.abspath('webdriver.xpi')):
        self._install_extension(extension)


class Config:
    def __init__(self, conf):
        self.browser = conf['browser'].lower() if 'browser' in conf else 'firefox'
        self.location = conf['location'] if 'location' in conf else None
        self.delay_submit = conf['delay_submit'] if 'delay_submit' in conf else 5
        self.wait_before_if = conf['if_wait'] if 'if_wait' in conf else 3
        self.random_agent = conf['random_agent_spoofer'] if 'random_agent_spoofer' in conf else 'random-agent-spoofer.xpi'
        self.loop = conf['loop'] if 'loop' in conf else False
        self.proxytool = conf['proxytool'] if 'proxytool' in conf else None
        self.ipchecker = conf['ipchecker'] if 'ipchecker' in conf else None


class ProxyToolConfigException(Exception):
    pass


class IPCheckerConfigException(Exception):
    pass


class Browser:

    def __init__(self, conf):
        self.driver = None
        self.conf = conf
        self.browser = conf.browser
        self.location = conf.location
        # self.delay_submit = conf.delay_submit
        # self.wait_before_if = conf.wait_before_if
        self.random_agent = conf.random_agent
        # self.loop = conf.loop

        self.kill_proc()

        proxydata = ExcelReader(proxysheet)
        self.proxies = proxydata.data
        self.num_proxy = proxydata.nums
        self.country = None
        self.state = None
        self.proxy_log = os.path.abspath(proxysheet + '.log')

    def change_proxy(self):
        if self.conf.proxytool:

            if os.path.exists(self.proxy_log):
                with open(self.proxy_log, 'rb') as f:
                    num_used = len(f.read())
            else:
                num_used = 0
            logger.info(u'[Info] 检测到已调用 {} 次代理API'.format(num_used))

            if num_used >= self.num_proxy:
                logger.error(u'[Error] Excel中没有可用代理')
                raise ProxyToolConfigException()
            else:
                proxy = self.proxies[num_used]
                self.country = proxy['country']
                self.state = proxy['state']
                self.call_api()
                time.sleep(20)
        else:
            logger.error(u'[Error] 未配置proxytool路径，无法切换代理')
            raise ProxyToolConfigException()

    def log_proxy(self):
        with open(self.proxy_log, 'a') as f:
            f.write('1')
            time.sleep(1)

    def call_api(self):
        logger.info(u'[Info] 调用代理 country: {0} state: {1}'.format(self.country, self.state))
        os.system(self.conf.proxytool + ' -changeproxy/' + self.country + '/' + self.state)

    def check_ip(self):
        """check ip, """
        if self.conf.ipchecker:
            while True:
                for i in range(6):
                    # 使用同一个country和state切换6次
                    try:
                        ip_info_xml = urllib2.urlopen(self.conf.ipchecker).read()
                    except urllib2.URLError as e:
                        # if getip api down, raise error
                        logger.error(u'[Error] 接口访问出错')
                        logger.error(e)
                        raise IPCheckerConfigException()

                    try:
                        ip_info_dict = xmltodict.parse(ip_info_xml)
                        ip = ip_info_dict['IpInfo']['ip']
                        country = ip_info_dict['IpInfo']['country']
                        region = ip_info_dict['IpInfo']['region']
                        logger.info(u'[Info] 检查IP - IP: {0}  country: {1} region： {2}'.format(ip, country, region))
                    except:
                        # if response format does not right, raise error
                        logger.exception(u'[Error] 接口返回的数据格式不正确')
                        raise IPCheckerConfigException()

                    if self.country == country:
                        logger.info(u'[Info] 切换代理成功')
                        return True
                    else:
                        logger.warning(u'[Warning] 实际country并非期望值')
                        if i < 5:
                            logger.info(u'[Info] 重新切换代理')
                            self.call_api()
                            time.sleep(20)

                logger.error(u'[Error] 6次切换代理均失败，读取下一行代理数据')
                self.log_proxy()
                self.change_proxy()
        else:
            logger.error(u'[Error] 未配置IP检测接口，无法检测IP是否正确切换')
            raise IPCheckerConfigException()

    def kill_proc(self):
        """kill firefox process"""
        logger.info(u'[Info] 清理残留firefox进程')
        os.system('taskkill /F /IM firefox.exe')
        time.sleep(2)

    def open(self):
        if self.browser == 'firefox':
            try:
                binary = FirefoxBinary(self.location)
                profile = FirefoxProfile()
                if self.random_agent:
                    profile.add_extension(os.path.abspath(self.random_agent))
                self.driver = webdriver.Firefox(firefox_binary=binary, firefox_profile=profile)
                logger.info(u'[Info] 打开浏览器  firefox')
                return self
            except:
                logger.error(u'[Error] 打开firefox 浏览器失败')
                raise
        elif self.browser == 'chrome':
            try:
                option = webdriver.ChromeOptions()
                option.binary_location = self.location

                self.driver = webdriver.Chrome(executable_path='chromedriver.exe', chrome_options=option)
                logger.info(u'[Info] 打开浏览器  chrome')
                return self
            except:
                logger.error(u'[Error] 打开chrome浏览器失败')
                raise
        else:
            logger.error(u'[Error] 不支持的浏览器类型')
            os._exit(0)

    def get(self, url):
        try:
            self.driver.get(url)
            logger.info(u'[Info] 打开URL  {}'.format(url))
            return self.driver
        except:
            logger.error(u'[Error] 打开URL失败，请检查配置')
            raise

    def quit(self):
        self.driver.quit()
        logger.info(u'[Info] 关闭浏览器')


class Element:
    def __init__(self, driver, elem_info, params):
        self.driver = driver
        try:
            self.locator = (elem_info[0], elem_info[1])
            self.element = WebDriverWait(self.driver, 15, 0.5).until(presence_of_element_located(self.locator))
            self.action = elem_info[2].lower()
            self.element_name = elem_info[3]
            self.params = params
            logger.info(u'[Info] 元素已找到  {}'.format(str(elem_info)))
        except TimeoutException:
            logger.info(u'[Error] 未找到元素  {}'.format(str(elem_info)))

    def do_its_work(self, delay_submit):
        if self.element:
            if self.action == 'click':
                self.element.click()
            elif self.action == 'clear':
                self.element.clear()
            elif self.action == 'submit':
                time.sleep(delay_submit)
                self.element.submit()
            elif self.action == 'sendkeys':
                self.element.send_keys(self.pick_value())
            elif self.action == 'select':
                if self.element_name == 'random':
                    nums = len(Select(self.element).options)
                    logger.info(u'[Info] 随机从网页选择')
                    Select(self.element).select_by_index(random.choice(range(1, nums)))
                elif isinstance(self.element_name, list):
                    logger.info(u'[Info] 从指定选项中随机选择： {}'.format(str(self.element_name)))
                    Select(self.element).select_by_value(random.choice(self.element_name))
                else:
                    Select(self.element).select_by_value(self.pick_value())
            else:
                logger.error(u"[Error] 不支持的action {}".format(self.action))

    def pick_value(self):
        value = self.params[self.element_name]
        logger.info(u'[Info] 从Excel中取得值 {}'.format(value))
        return value


class NoMoreTaskException(Exception):
    pass


class Task:
    def __init__(self, task):
        self.url = task.pop(0)['url']
        self.sheet = task.pop(0)['sheet']
        self.log = os.path.abspath(os.curdir) + '\\' + self.sheet + '.log'

        if os.path.exists(self.log):
            with open(self.log, 'rb') as f:
                self.num = len(f.read())
        else:
            self.num = 0
        logger.info(u'[Info] 检测到已执行 {} 次该任务'.format(self.num))

        xls = ExcelReader(sheet=self.sheet)
        self.loop_times = xls.nums
        self.data = xls.data
        self.task = task

    def run(self, b):
        if self.num < self.loop_times:
            for t in range(self.num, self.loop_times):
                params = self.data[t]
                logger.info(u'[Info] Sheet: "{0}"  Line: "{1}" 开始执行'.format(self.sheet, self.num + 2))
                logger.info(u'[Info] ======  任务开始  =======')
                driver = b.open().get(self.url)
                used = 0  # data行使用标志
                error_page = 0  # error标志
                for page in self.task:
                    # 如果上次任务执行是error page，则这次执行前刷新下代理
                    if error_page == 2:
                        try:
                            b.change_proxy()
                            error_page = 0  # 重新把error标志置为0
                        except:
                            pass
                    # 如果是Error Page，刷新一次，若仍失败，退出
                    for i in range(1, 3):
                        try:
                            WebDriverWait(driver, 3, 0.5).until(visibility_of_element_located(('id', 'errorPageContainer')))
                            error_page = i
                            logger.error(u'[Error] 得到Error Page')
                            if error_page < 2:
                                time.sleep(3)
                                logger.info(u'[Info] 刷新页面')
                                driver.refresh()
                                time.sleep(10)
                        except TimeoutException:
                            break
                    if error_page == 2:
                        logger.error(u'[Error] 两次得到Error Page，任务失败')
                        break

                    done = 0
                    for element in page['elements']:
                        if isinstance(element, dict):
                            if 'if' in element:
                                time.sleep(b.conf.wait_before_if)
                                if element['if'] in driver.current_url:
                                    logger.info(u'[Info] URL为期待值，任务成功')
                                    done = 1
                                    break
                            elif 'wait' in element:
                                logger.info(u'[Info] wait {}s'.format(element['wait']))
                                time.sleep(element['wait'])
                        else:
                            try:
                                Element(driver, element, params).do_its_work(b.conf.delay_submit)
                            except:
                                logger.warning(u'[Warning] 元素执行失败，跳过该元素')
                            time.sleep(1)
                    # 程序执行完第一个elements，则标记为已执行，写入日志
                    if used == 0:
                        with open(self.log, 'a') as f:
                            f.write('1')
                            used = 1
                        b.log_proxy()  # 执行完第一个elements，写入代理日志，算这个代理已使用过
                    if done == 1:
                        break
                    time.sleep(5)
                logger.info(u'[Info] 当前网页URL： {}'.format(driver.current_url))
                b.quit()
                logger.info(u'[Info] ======  任务结束  =======')
                logger.info(u'[Info] Sheet: "{0}"  Line: "{1}" 执行结束\n'.format(self.sheet, self.num + 2))
                if not b.conf.loop:
                    return
        else:
            logger.warning(u'[Warning] data中没有更多的数据了')
            raise NoMoreTaskException()


def main():
    # 循环执行大任务（配置中所有任务节）
    while True:
        try:
            tasks = YamlReader().data
            conf = Config(tasks.pop(0))
        except:
            logger.error(u'[Error] 读取配置文件出错')
        else:
            browser = Browser(conf)
            try:
                browser.change_proxy()
            except ProxyToolConfigException:
                break

            try:
                browser.check_ip()  # if exception, stop program
            except IPCheckerConfigException:
                break
            try:

                for task in tasks:
                    try:
                        logger.info(u'[Info] 执行任务  {}'.format(str(task)))
                        try:
                            t = Task(task)
                        except:
                            logger.error(u'[Error] 初始化任务出错，请检查配置或数据文件，确认填写无误并且变量名与列名对应')
                            raise
                        else:
                            try:
                                t.run(browser)
                            except NoMoreTaskException:
                                raise
                            except:
                                logger.error(u'[Error] 执行任务出错，请检查配置与页面是否对应')
                                raise
                    except NoMoreTaskException:
                        raise
                    except:
                        try:
                            logger.info(u'[Info] 当前网页URL： {}'.format(browser.driver.current_url))
                            browser.quit()
                        except:
                            pass
                        return
            except NoMoreTaskException:
                break
    logger.info(u'[Info] 所有任务执行结束，请处理数据后重新启动程序\n')


if __name__ == '__main__':
    main()