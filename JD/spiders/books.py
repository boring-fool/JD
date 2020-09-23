import scrapy
import json
from JD.items import JdItem
from scrapy_redis.spiders import RedisSpider
class BooksSpider(RedisSpider):
    # name = 'books'
    # allowed_domains = ['jd.com','p.3.cn']
    # start_urls = ['https://pjapi.jd.com/book/sort?source=bookSort&callback=jsonp_1600832639310_95065']
    redis_key = 'py'
    def __init__(self, *args, **kwargs):
        domain = kwargs.pop('domain', '')
        self.allowed_domains = list(filter(None, domain.split(',')))
        super(BookSpider, self).__init__(*args, **kwargs)

    def parse(self, response):
        # 获取所有图书大分类节点列表
        temp = {}
        datas = json.loads(response.text.lstrip('jsonp_1600832639310_95065(').rstrip(')'))['data']
        for data in datas:
            big_node_list = data['categoryName']
            big_node_list_link = 'https://list.jd.com/' + str(data['fatherCategoryId']).rstrip('.0') + '-' + str(data['categoryId']).rstrip('.0') + '.html'
            for small_node in data['sonList']:
                small_node_list = small_node['categoryName']
                small_node_list_link = big_node_list_link.rstrip('.html') + '-' + str(small_node['categoryId']).rstrip('.0') + '.html'
                temp['big_category'] = big_node_list
                temp['big_category_link'] = big_node_list_link
                temp['small_category'] = small_node_list
                temp['small_category_link'] = big_node_list_link


                # 模拟点击小分类链接
                yield scrapy.Request(
                    url=temp['small_category_link'],
                    callback=self.parse_book_list,
                    meta={"temp": temp}
                )

    def parse_book_list(self, response):
        temp = response.meta['temp']

        book_list = response.xpath('//*[@id="J_goodsList"]/ul/li/div')


        for book in book_list:
            item = JdItem()

            item['big_category'] = temp['big_category']
            item['big_category_link'] = temp['big_category_link']
            item['small_category'] = temp['small_category']
            item['small_category_link'] = temp['small_category_link']

            item['bookname'] = book.xpath(
                './div[3]/a/em/text()|./div/div[2]/div[2]/div[3]/a/em/text()').extract_first().strip()
            item['author'] = book.xpath(
                './div[4]/span[1]/span/a/text()|./div/div[2]/div[2]/div[4]/span[1]/span[1]/a/text()').extract_first().strip()
            item['link'] = book.xpath('./div[1]/a/@href|./div/div[2]/div[2]/div[1]/a/@href').extract_first()

            # 获取图书编号
            skuid = book.xpath('.//@data-sku').extract_first()
            # skuid = book.xpath('./@data-sku').extract_first()
            # print("skuid:",skuid)
            # 拼接图书价格低至
            pri_url = 'https://p.3.cn/prices/mgets?skuIds=J_' + skuid
            yield scrapy.Request(url=pri_url, callback=self.parse_price, meta={'meta_1': item})

    def parse_price(self, response):
        item = response.meta['meta_1']

        dict_data = json.loads(response.body)

        item['price'] = dict_data[0]['p']
        yield item
