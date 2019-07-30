import scrapy
from datetime import date,timedelta
import glob
import os
from scrapy_splash  import SplashRequest
from scrapy.selector import Selector
import pymongo


class Spider(scrapy.Spider):
    name = 'spider'
    allowed_domains = ['cctv.com']
    PATH = 'xwlb/'
    myclient = pymongo.MongoClient("mongodb://192.168.1.8:27017/")#change to your mongo server ip
    mydb = myclient["db_xwlb"]
    db_summary = mydb["db_summary"]
    db_detail = mydb["db_detail"]
    #读取已经抓取过的页面
    if not os.path.exists(PATH):
        os.mkdir(PATH),os.mkdir(PATH+'details/'),os.mkdir(PATH+'summarys/')  
    olds = set(glob.glob(PATH + '*.shtml'))
    #初始化持久化文件
    if os.path.exists('detail_error.txt'):
        detail_error_urls=set(open('detail_error.txt','r').readlines())  
    else:
        detail_error_urls=set()
    if os.path.exists('sumary_error.txt'):
        sumary_error_urls=set(open('sumary_error.txt','r').readlines())  
    else:
        sumary_error_urls=set()
    writer_sumary_error = open('sumary_error.txt', 'w')
    writer_detail_error = open('detail_error.txt', 'w')
    headers = {'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36',  'Accept':'text / html, application / xhtml + xml, application / xml;q = 0.9,image/webp, * / *;q = 0.8'}

    def start_requests(self):
        #先解析上次解析失败的页面
        for url in self.detail_error_urls:
            yield SplashRequest(url[:-1], callback=(self.parse_detail), endpoint='render.html', args={'wait':2, 'http_method':'GET'}, headers=(self.headers))
        for url in self.sumary_error_urls:
            yield SplashRequest(url[:-1], callback=(self.parse_sumary), endpoint='render.html', args={'wait':2, 'http_method':'GET'}, headers=(self.headers))
        #然后依次解析
        start_day =date.today()
        days = start_day - date(2016, 2, 3)
        for day in range(days.days):
            curday = start_day - timedelta(days=day)
            if f'xwlb/{curday.strftime("%Y%m%d")}.shtml' in self.olds:
                continue
            url = f"http://tv.cctv.com/lm/xwlb/day/{curday.strftime('%Y%m%d')}.shtml"
            yield SplashRequest(url, callback=(self.parse), endpoint='render.html', args={'wait':2, 'http_method':'GET'}, headers=(self.headers))

        days = date(2016, 2, 2) - date(2011, 4, 6)
        for day in range(days.days):
            curday = date(2016, 2, 2) - timedelta(days=day)
            if f"xwlb/{curday.strftime('%Y%m%d')}.shtml" in self.olds:
                continue
            url = f"http://cctv.cntv.cn/lm/xinwenlianbo/{curday.strftime('%Y%m%d')}.shtml"
            yield SplashRequest(url, callback=(self.parse), endpoint='render.html', args={'wait':2,  'http_method':'GET'}, headers=(self.headers))

        days = date(2011, 4, 5) - date(2009, 6, 26)
        for day in range(days.days):
            curday = date(2011, 4, 5) - timedelta(days=day)
            if f"xwlb/{curday.strftime('%Y%m%d')}.shtml" in self.olds:
                continue
            url = f"http://news.cntv.cn/program/xwlb/{curday.strftime('%Y%m%d')}.shtml"
            yield SplashRequest(url, callback=(self.parse), endpoint='render.html', args={'wait':2,  'http_method':'GET'}, headers=(self.headers))

        days = date(2009, 6, 25) - date(2002, 9, 8)
        for day in range(days.days):
            curday = date(2009, 6, 25) - timedelta(days=day)
            if f"xwlb/{curday.strftime('%Y%m%d')}.shtml" in self.olds:
                continue
            url = f"http://www.cctv.com/news/xwlb/{curday.strftime('%Y%m%d')}/index.shtml"
            yield SplashRequest(url, callback=(self.parse), endpoint='render.html', args={'wait':2,  'http_method':'GET'}, headers=(self.headers))

    def parse(self, response):
        file_name =self.PATH + response.url.split('/')[-1] if 'index' not in response.url else self.PATH + response.url.split('/')[-2] + '.shtml'
        with open(file_name, 'wb') as (writer):
            writer.write(response.body)
        html = response.xpath('//div[@id="contentELMT1368521805488378"]').get()
        lis=None
        if html is None:
            lis = response.xpath('//li/a').getall()
        else:
            lis = Selector(text=html).xpath('//li/a').getall()
        for li in [lis[0]]:
            try:
                url = Selector(text=li).xpath('//a[@href]').attrib['href']
                for url in [url]:
                    url = 'http://www.cctv.com' + url if url[0] == '/' else url
                    url = url.replace('news.cntv.cn', 'tv.cctv.com')
                    yield SplashRequest(url, callback=(self.parse_sumary), endpoint='render.html', args={'wait':2,  'http_method':'GET'}, headers=(self.headers))
            except Exception:
                continue

        for li in lis[1:]:
            try:
                url = Selector(text=li).xpath('//a[@href]').attrib['href']
                for url in [url]:
                    url = 'http://www.cctv.com' + url if url[0] == '/' else url
                    url = url.replace('news.cntv.cn', 'tv.cctv.com')
                    yield SplashRequest(url, callback=(self.parse_detail), endpoint='render.html', args={'wait':2, 'http_method':'GET'}, headers=(self.headers))
            except Exception as e:
                continue

    def parse_sumary(self, response):
        filename=''.join(response.url.split('/')[3:])
        with open(self.PATH + 'summarys/' + ''.join(filename) + '.shtml', 'wb') as (writer):
                writer.write(response.body)
        try:#http://tv.cctv.com/2019/05/28/VIDEmk8iqcsIBR6ZmpYaPN5F190528.shtml
            html = response.xpath('//div[@class="mtab_con"]').get()
            items = Selector(text=html).xpath('//p/text()').getall()
            self.db_summary.insert_one({'_id':f'{items[1]}',"content":f'{items[2]}'})
        except Exception :
                self.writer_sumary_error.write(response.url+'\n')    

    def parse_detail(self, response):
        try:
            if 'http://tv.cctv.com' or 'http://news.cntv.cn/' or 'http://www.cctv.com/' in response.url:
                if 'http://news.cntv.cn/program' in response.url:
                    itime = ''.join(response.url.split('/')[5:])
                    with open(self.PATH + 'details/' + ''.join(itime) , 'wb') as (writer):
                        writer.write(response.body)
                    content = Selector(text=(response.xpath('//div[@class="cnt_bd"]').get())).xpath('//p[not(@*)]/text()').getall()
                    content=''.join(content)
                    self.db_detail.insert_one({'_id':f'{itime}',"content":f'{content}'})
                    return
                itime = ''.join(response.url.split('/')[3:])
                with open(self.PATH + 'details/' + ''.join(itime) , 'wb') as (writer):
                    writer.write(response.body)
                content = Selector(text=(response.xpath('//div[@class="cnt_bd"]').get())).xpath('//p[not(@*)]/text()').getall()
                content=''.join(content)
                self.db_detail.insert_one({'_id':f'{itime}',"content":f'{content}'})
            if 'http://news.cntv.cn/china' in response.url:
                return
        except Exception :
                self.writer_detail_error.write(response.url+'\n')