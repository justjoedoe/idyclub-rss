# idyclub 电影精华 RSS

非官方 RSS，抓取 [idyclub.com 电影精华](https://www.idyclub.com/thread-1?tab=digest)（无需登录）。

**订阅地址：** https://justjoedoe.github.io/idyclub-rss/feed.xml

GitHub Actions 每小时整点生成 `feed.xml`，校验通过后发布到 GitHub Pages。也可以在 Actions 里手动运行 “Publish RSS feed”。抓取失败、没有条目，或 XML 不合法时，本次不会发布，线上仍保留上一次成功的 feed。

## 本地生成

只需 Python 3 标准库。完整跑一遍大约 45 秒（请求间隔 1 秒）。

```bash
python3 make_feed.py -o feed.xml
python3 make_feed.py --pages 2 --details 10
python3 make_feed.py --fid 18 -o tv.xml
```

- `--pages` 列表页数，默认 `1`
- `--details` 拉取详情的条数（英文名、年份、评分、简介），默认 `30`，`0` 表示不拉详情
- `--fid` 板块：`1` 电影，`18` 剧集
