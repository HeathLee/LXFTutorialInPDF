import os
import logging
import pickle
from weasyprint import HTML
from urllib import request
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

INDEX_URL = ('http://www.liaoxuefeng.com/wiki/'
             '0014316089557264a6b348958f449949df42a6d3a2e542c000')
BASE_URL = 'http://www.liaoxuefeng.com'
TRY_LIMIT = 5


# 配置日志模块，同时输出到屏幕和文件
logger = logging.getLogger('pdf_logger')
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %('
                              'message)s')
fh = logging.FileHandler('../log/pdf.log')
sh = logging.StreamHandler()
fh.setFormatter(formatter)
sh.setFormatter(formatter)
logger.addHandler(fh)
logger.addHandler(sh)

# 配置浏览器，提高抓取速度
cap = dict(DesiredCapabilities.PHANTOMJS)
cap['phantomjs.page.settings.loadImages'] = False  # 禁止加载图片
cap['phantomjs.page.settings.userAgent'] = ('Mozilla/5.0 (Windows NT 10.0; '
                                            'WOW64) AppleWebKit/537.36 ('
                                            'KHTML, like Gecko) '
                                            'Chrome/45.0.2454.101 '
                                            'Safari/537.36')  # 设置useragent
cap['phantomjs.page.settings.diskCache'] = True  # 设置浏览器开启缓存
browser = webdriver.PhantomJS(desired_capabilities=cap)
browser.set_page_load_timeout(180)  # 超时时间


def fetch_url_list():
    """
    从教程主页获取需要抓取页面的URL列表
    :return: 分析后的URL列表
    """
    try:
        with request.urlopen(INDEX_URL) as page:
            content = page.read().decode()
            soup = BeautifulSoup(content, 'lxml')
            url_list = [item['href'] for item in soup.select('.uk-nav-side > '
                                                             'li > a')]
            return url_list
    except Exception as e:
        logger.error('fetch url list failed')
        logger.error(e)


def fetch_page(url, index):
    """
    根据给定的URL抓取页面
    :param url: 要抓取的页面地址
    :param index: 页面地址在URL列表种的索引位置，调试用
    :return: 返回抓到的页面源代码，失败返回None
    """
    try:
        browser.get(url)
        return browser.page_source
    except Exception as e:
        logger.warning('get page %d %s failed' % (index, url))
        logger.warning(e)
        return None


def build_content():
    """
    处理爬到的页面，写入文件
    :return: None
    """
    url_list = fetch_url_list()
    output = []
    logger.info('there are %s pages' % len(url_list))

    for url_index in range(len(url_list)):
        # 爬页面时可能会因为网络等原因而失败，失败后可以尝试重新抓取，最多五次
        try_count = 0  # 尝试次数
        html = fetch_page(BASE_URL + url_list[url_index], url_index)
        while try_count < TRY_LIMIT and html is None:
            html = fetch_page(BASE_URL + url_list[url_index], url_index)
            try_count += 1

        try:
            if html is not None:
                soup = BeautifulSoup(html, 'lxml')
                title = soup.select('.x-content > h4')[0].get_text()
                title = '<h1>' + title + '</h1>'
                output.append(title + str(soup.select('.x-wiki-content')
                                          [0]).replace(
                    'src="/', 'src="http://www.liaoxuefeng.com/'))
                logger.info('get page %s success' % url_index)
            # 页面抓取比较耗时，且中途失败的几率较大，每抓取到页面可以把迄今为止的结果
            # 序列化存储，程序异常退出后前面的结果不会丢失，可以反序列化后接着使用
            with open('output.dump', 'wb') as f:
                pickle.dump(output, f)
        except Exception as e:
            logger.warning('deal page %s %s failed' % (url_index,
                                                       url_list[url_index]))
            logger.warning(e)

    with open('../html/pages.html', 'w') as f:
        f.write('<head><meta charset="utf-8"/></head><body>' + ''.join(
            output) + '</body>')


if not os.path.exists('../html/pages.html'):
    build_content()

if browser:
    browser.quit()

css = [
    '../css/codemirror.css',
    '../css/highlight.css',
    '../css/itranswarp.css'
]
HTML('../html/pages.html').write_pdf('../廖雪峰Python教程.pdf', stylesheets=css)
