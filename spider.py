import re
import os
from concurrent.futures import ThreadPoolExecutor
import requests
from retrying import retry

# 每次21个视频信息，可改 可翻页
count = 21


def retry_if_no_videos(result):
    is_retry = True if not result else False
    return is_retry


class Douyin(object):
    """
    获取抖音用户下的视频信息
    """
    headers = {"User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) \
                 AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149\
                Mobile Safari/537.36",
               "sec-fetch-mode": "cors",
               "sec-fetch-site": "same-origin",
               "accept": "application/json",
               "accept-encoding": "gzip, deflate",
               "accept-language": "zh-CN,zh;q=0.9"
               }
    basepath = os.path.dirname(__file__)
    videos_path = os.path.join(basepath, "downloads")
    os.makedirs(videos_path, exist_ok=True)

    def __init__(self, *args, **kwargs):
        # self.t = ThreadPoolExecutor(max_workers=21)
        self.session = requests.Session()
        self.url = kwargs.get("url", "")
        if not self.url:
            exit(1)

        pass

    def get_sign(self,html,uid):
        """
        得到签名参数：_signature 走现有接口
        :return:
        """
        tac = re.search(r"tac='([\s\S]*?)'</script>", html).group(1)
        data = {
            "tac": tac.split("|")[0],
            'user_id': uid,
        }
        signature = requests.post('http://49.233.200.77:5001', data=data).json()
        signature = signature.get("signature")
        return signature

    def get_params(self, ):
        """
        ('sec_uid', 'MS4wLjABAAAAPSUIwDDx6dTo4321hA-WqxIDcu_D4z0GlGCQZEnUdoU'),
        ('count', '21'),
        ('max_cursor', '0'),
        ('aid', '1128'),
        ('_signature', 'o8bT9BAY.VfQMNmbn-lt6aPG0-'),
        ('dytk', '8')
        """
        res = self.fetch(url=self.url, headers=self.headers)
        html = res.text
        uid = re.findall('uid: "(.*?)"', html)[0]
        sec_uid = ''.join(re.findall(r"sec_uid=(.*?)&", res.url))
        dytk = ''.join(re.findall("dytk:\s+'(.*?)'", html))
        signature = self.get_sign(html,uid)
        return {"sec_uid": sec_uid, "count": count, "_signature": signature, "max_cursor": "0", "aid": "1128",
                "dytk": dytk}  # "user_id": uid,

    def fetch(self, **kwargs):
        res = self.session.get(**kwargs)
        assert res.status_code == 200, f"Response code is not  200! {res.text}"
        return res

    @retry(stop_max_attempt_number=500, retry_on_result=retry_if_no_videos, wait_fixed=1000)
    def get_videos(self):
        """
        接口数据时而有时而无，故 retrying 500
        :return:
        """
        params = self.get_params()
        print(f"params is: {params}")
        url = "https://www.iesdouyin.com/web/api/v2/aweme/post/"
        res = self.fetch(url=url, params=params, headers=self.headers)
        result = res.json()
        videos = (self.extract_play_addr(result))
        return videos

    def download(self, videos):
        """
        待改进 多线程
        :param videos:
        :return:
        """
        for i in videos:
            with open(os.path.join(self.videos_path, "{}.mp4".format(i.get("desc"))), "wb") as f:
                video = self.fetch(url=i.get("play_addr"), headers=self.headers)
                f.write(video.content)


    @staticmethod
    def extract_play_addr(data):
        """
        视频其他信息:
        {
        "statistics": {
            "share_count": 429,
            "forward_count": 59,
            "aweme_id": "6813897645778652428",
            "comment_count": 2520,
            "digg_count": 35000,
            "play_count": 0
            }
        }
        并未提取
        :param data:
        :return:
        """
        videos = [{"desc": i.get("desc"), "play_addr": i.get("video", {}).get("play_addr", {}).get("url_list", [])[0]}
                  for i in data.get("aweme_list", [])]
        return videos

    def main(self):
        videos = self.get_videos()
        self.download(videos)


if __name__ == "__main__":
    douyin = Douyin(url="http://v.douyin.com/vHHhXh/")
    douyin.main()
