import requests
import re
import json
import file_util
from flask import Flask, escape, request, render_template, jsonify
from flask_apscheduler import APScheduler
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask("xdu_electricity_balance")

server_chan = ''


class EnergySession(requests.Session):
    BASE = 'http://10.168.55.50:8088'

    def __init__(self, username, password, *args, **kwargs):
        super(EnergySession, self).__init__(*args, **kwargs)
        self.get(self.BASE + "/searchWap/Login.aspx")
        self.post(
            self.BASE + "/ajaxpro/SearchWap_Login,App_Web_fghipt60.ashx",
            json={
                "webName": username,
                "webPass": password
            }, headers={
                "AjaxPro-Method": "getLoginInput",
                'Origin': self.BASE
            }
        )


def crawl(username, password):
    ses = EnergySession(username, password)
    balance_page = ses.get(
        'http://10.168.55.50:8088/searchWap/webFrm/met.aspx'
    ).text
    pattern_name = re.compile('表名称：(.*?)  ', re.S)
    name = re.findall(pattern_name, balance_page)
    pattern_balance = re.compile('剩余量：(.*?) </td>', re.S)
    balance = re.findall(pattern_balance, balance_page)
    s = ''
    kede_s = ''
    for n, b in zip(name, balance):
        s_n = str(n).replace('\r', '').replace('\n', '')
        s += f'表名: {s_n}剩余量: {float(b)}\n'
        if '科德' in n:
            kede_s = float(b)
    return s, kede_s


@app.route('/api/me', methods=['get'])
def me():
    global server_chan
    js = file_util.read_all_text('config.json')
    js = json.loads(js)

    res, kede = crawl(js['username'], js['password'])
    requests.get(
        f'https://sc.ftqq.com/{server_chan}.send?text=电表剩余量{kede}&desp={res}')

    return res


class APSchedulerJobConfig(object):
    SCHEDULER_API_ENABLED = True
    SCHEDULER_TIMEZONE = 'Asia/Shanghai'
    JOBS = [
        {
            'id': 'me',
            'func': me,
            'args': '',
            'trigger': {
                'type': 'cron',
                'day_of_week': "0-6",
                'hour': '0-23',
                'minute': '0',
                'second': '0'
            }
        }
    ]


def init():
    global server_chan
    js = file_util.read_all_text('config.json')
    js = json.loads(js)
    server_chan = js['serverchan']

    # 初始化Flask-APScheduler，定时任务
    scheduler = APScheduler(BackgroundScheduler(timezone="Asia/Shanghai"))
    scheduler.init_app(app)
    scheduler.start()


def main():
    init()
    app.run(host='0.0.0.0', port='80')


if __name__ == "__main__":
    main()
